"""
Aqar.ai: Ingestion Stage
=========================
Celery tasks for discovering and ingesting YouTube videos.

Tasks:
  - discover_videos: Scans configured channels for new videos (scheduled).
  - ingest_video: Processes a single video URL (manual or chained).
  - retry_failed_jobs: Retries failed processing jobs (scheduled).
"""

from __future__ import annotations

import logging
import os

from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from models.base import Platform, ProcessingJob, ProcessingStatus, VideoSource

logger = logging.getLogger(__name__)

# Max video duration in minutes (from env, default 30)
MAX_DURATION_MINUTES = int(os.getenv("MAX_VIDEO_DURATION_MINUTES", "30"))
MAX_DURATION_SECONDS = MAX_DURATION_MINUTES * 60

# Sync DB URL for Celery tasks (Celery does not support async)
DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://aqar:aqar_dev_password@db:5432/aqar_db",
)


def _get_sync_session() -> Session:
    """Create a sync SQLAlchemy session for use in Celery tasks."""
    engine = create_engine(DATABASE_URL_SYNC, pool_pre_ping=True)
    return Session(engine)


@shared_task(
    name="aqar_pipeline.stages.ingestion.discover_videos",
    queue="ingestion",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def discover_videos(self, region: str = "tangier-tetouan", config_path: str | None = None):
    """
    Discover new videos from all configured YouTube channels.
    Scans both the hardcoded YAML file and approved channels from the database.
    """
    from aqar_pipeline.config.loader import ChannelConfig, load_channels_config
    from aqar_pipeline.stages.audio_extraction import extract_audio
    from aqar_pipeline.utils.youtube import fetch_channel_videos

    logger.info(f"Starting video discovery for region: {region}")

    # 1. Load channels from YAML config
    yaml_channels = []
    try:
        config = load_channels_config(config_path)
        if config.region == region:
            yaml_channels = config.channels
    except (FileNotFoundError, ValueError) as e:
        logger.warning(f"Could not load YAML channel config: {e}")

    # 2. Load approved channels from database
    db_channels = []
    session_for_channels = _get_sync_session()
    try:
        from models.base import ChannelRegistration
        from models.base import ChannelStatus as ChStatus

        result = session_for_channels.execute(
            select(ChannelRegistration).where(
                ChannelRegistration.status == ChStatus.APPROVED,
                ChannelRegistration.region == region,
            )
        )
        for ch in result.scalars().all():
            db_channels.append(
                ChannelConfig(
                    name=ch.channel_name or "DB Channel",
                    channel_url=ch.channel_url,
                    description=ch.description or "",
                    max_videos=ch.max_videos,
                )
            )
        logger.info(f"Loaded {len(db_channels)} approved channels from database")
    except Exception as e:
        logger.error(f"Error loading channels from database: {e}")
    finally:
        session_for_channels.close()

    # 3. Combine and dedup sources by URL
    seen_urls = set()
    all_channels = []
    for ch in yaml_channels + db_channels:
        if ch.channel_url not in seen_urls:
            seen_urls.add(ch.channel_url)
            all_channels.append(ch)

    if not all_channels:
        logger.info("No channels to scan")
        return {"status": "completed", "channels_scanned": 0, "new_videos": 0}

    # Statistics tracking
    total_discovered = 0
    total_skipped_existing = 0
    total_skipped_duration = 0
    total_errors = 0
    ids_to_process = []

    session = _get_sync_session()
    try:
        for channel in all_channels:
            logger.info(f"Scanning channel: {channel.name}")
            try:
                videos = fetch_channel_videos(channel.channel_url, max_videos=channel.max_videos)
                for video in videos:
                    if video.duration_seconds > MAX_DURATION_SECONDS:
                        total_skipped_duration += 1
                        continue

                    existing = session.execute(
                        select(VideoSource).where(
                            VideoSource.external_id == video.external_id,
                            VideoSource.platform == Platform.YOUTUBE,
                        )
                    ).scalar_one_or_none()

                    if existing:
                        # Ensure job exists for existing video if it was stuck
                        job = session.execute(
                            select(ProcessingJob).where(
                                ProcessingJob.video_source_id == existing.id
                            )
                        ).scalar_one_or_none()
                        if job and job.status == ProcessingStatus.PENDING:
                            ids_to_process.append(str(existing.id))
                        total_skipped_existing += 1
                        continue

                    # Register new video
                    video_source = VideoSource(
                        url=video.url,
                        platform=Platform.YOUTUBE,
                        external_id=video.external_id,
                        channel_name=video.channel_name,
                        title=video.title,
                        duration_seconds=video.duration_seconds,
                        published_at=video.published_at,
                        raw_metadata=video.raw_metadata,
                    )
                    session.add(video_source)
                    session.flush()

                    session.add(
                        ProcessingJob(
                            video_source_id=video_source.id, status=ProcessingStatus.PENDING
                        )
                    )
                    ids_to_process.append(str(video_source.id))
                    total_discovered += 1

            except Exception as e:
                logger.error(f"Error scanning channel {channel.name}: {e}")
                total_errors += 1
                continue

        session.commit()

        # Trigger extraction for new/pending videos
        for vid_id in ids_to_process:
            extract_audio.delay(vid_id)

    except Exception as e:
        session.rollback()
        raise self.retry(exc=e) from e
    finally:
        session.close()

    summary = {
        "status": "completed",
        "channels_scanned": len(all_channels),
        "new_videos": total_discovered,
        "skipped_existing": total_skipped_existing,
        "skipped_duration": total_skipped_duration,
        "errors": total_errors,
    }
    logger.info(f"Discovery complete: {summary}")
    return summary


@shared_task(
    name="aqar_pipeline.stages.ingestion.ingest_video",
    queue="ingestion",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def ingest_video(self, video_url: str, job_id: str | None = None):
    """
    Ingest a single video URL.
    Logic updated to fix ValueError and handle existing videos properly.
    """
    from aqar_pipeline.stages.audio_extraction import extract_audio
    from aqar_pipeline.utils.job_manager import JobManager
    from aqar_pipeline.utils.youtube import extract_youtube_id, fetch_video_metadata

    video_id = extract_youtube_id(video_url)
    session = _get_sync_session()

    try:
        # 1. Check existing VideoSource
        existing = session.execute(
            select(VideoSource).where(
                VideoSource.external_id == video_id,
                VideoSource.platform == Platform.YOUTUBE,
            )
        ).scalar_one_or_none()

        video_source = existing

        if not video_source:
            # 2. Fetch metadata if new video
            metadata = fetch_video_metadata(video_url)
            if not metadata:
                return {"status": "error", "message": "Metadata fetch failed"}

            if metadata.duration_seconds > MAX_DURATION_SECONDS:
                return {"status": "skipped", "reason": "too_long"}

            video_source = VideoSource(
                url=metadata.url,
                platform=Platform.YOUTUBE,
                external_id=metadata.external_id,
                title=metadata.title,
                duration_seconds=metadata.duration_seconds,
                raw_metadata=metadata.raw_metadata,
            )
            session.add(video_source)
            session.flush()

            # 3. Ensure a ProcessingJob exists
            job = session.execute(
                select(ProcessingJob).where(ProcessingJob.video_source_id == video_source.id)
            ).scalar_one_or_none()

            if not job:
                job = ProcessingJob(
                    video_source_id=video_source.id, status=ProcessingStatus.PENDING
                )
                session.add(job)

            # ── CRITICAL FIX: COMMIT HERE ──
            # This ensures the record is visible to the JobManager's query
            session.commit()

            # 4. Initialize Manager AFTER commit
            manager = JobManager(session, str(video_source.id))

            if manager.start_stage("ingestion"):
                manager.complete_stage(metadata={"title": video_source.title})
                extract_audio.delay(str(video_source.id))
                return {"status": "ingested", "video_id": str(video_source.id)}
        else:
            return {"status": "skipped", "reason": "already_processed", "video_id": video_id}

    except Exception as e:
        session.rollback()
        logger.error(f"Ingestion error for {video_url}: {e}")
        raise self.retry(exc=e) from e
    finally:
        session.close()


@shared_task(
    name="aqar_pipeline.stages.ingestion.retry_failed_jobs",
    queue="ingestion",
)
def retry_failed_jobs():
    """Retry FAILED jobs that haven't hit max retries."""
    session = _get_sync_session()
    try:
        failed_jobs = (
            session.execute(
                select(ProcessingJob).where(
                    ProcessingJob.status == ProcessingStatus.FAILED,
                    ProcessingJob.retry_count < ProcessingJob.max_retries,
                )
            )
            .scalars()
            .all()
        )

        retried = 0
        for job in failed_jobs:
            job.status = ProcessingStatus.PENDING
            job.retry_count += 1
            job.error_message = None
            retried += 1

        session.commit()
        return {"status": "completed", "retried": retried}
    except Exception as e:
        session.rollback()
        logger.error(f"Error retrying jobs: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        session.close()
