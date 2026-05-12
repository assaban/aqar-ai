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

    This task runs on a schedule (every 6 hours via Celery beat).
    It scans each channel, deduplicates against existing entries,
    and creates new VideoSource + ProcessingJob records.

    Args:
        region: Region filter (matches channels.yml region field).
        config_path: Optional path to channels.yml. Uses default if None.
    """
    from aqar_pipeline.config.loader import load_channels_config
    from aqar_pipeline.stages.audio_extraction import extract_audio
    from aqar_pipeline.utils.youtube import fetch_channel_videos

    logger.info(f"Starting video discovery for region: {region}")

    try:
        config = load_channels_config(config_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to load channel config: {e}")
        return {"status": "error", "message": str(e)}

    if config.region != region:
        logger.info(f"Config region '{config.region}' does not match '{region}', skipping")
        return {"status": "skipped", "reason": "region_mismatch"}

    # Statistics tracking restored [cite: 17]
    total_discovered = 0
    total_skipped_existing = 0
    total_skipped_duration = 0
    total_errors = 0
    ids_to_process = []

    session = _get_sync_session()

    try:
        for channel in config.channels:
            logger.info(f"Scanning channel: {channel.name} ({channel.channel_url})")

            try:
                videos = fetch_channel_videos(
                    channel_url=channel.channel_url,
                    max_videos=channel.max_videos,
                )
            except Exception as e:
                logger.error(f"Error scanning channel {channel.name}: {e}")
                total_errors += 1
                continue

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
                    # Healer logic: queue existing PENDING jobs
                    job = session.execute(
                        select(ProcessingJob).where(ProcessingJob.video_source_id == existing.id)
                    ).scalar_one_or_none()

                    if job and job.status == ProcessingStatus.PENDING:
                        ids_to_process.append(str(existing.id))

                    total_skipped_existing += 1
                    continue

                # Create records for new video
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

                job = ProcessingJob(
                    video_source_id=video_source.id,
                    status=ProcessingStatus.PENDING,
                )
                session.add(job)

                ids_to_process.append(str(video_source.id))
                total_discovered += 1

        session.commit()

        # Trigger next stage for all identified IDs
        for vid_id in ids_to_process:
            extract_audio.delay(vid_id)

    except Exception as e:
        session.rollback()
        raise self.retry(exc=e) from e
    finally:
        session.close()

    # Original summary dictionary restored [cite: 17]
    summary = {
        "status": "completed",
        "region": region,
        "channels_scanned": len(config.channels),
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
    Accepts job_id to maintain state machine synchronization.
    """
    from aqar_pipeline.stages.audio_extraction import extract_audio
    from aqar_pipeline.utils.job_manager import JobManager
    from aqar_pipeline.utils.youtube import extract_youtube_id, fetch_video_metadata

    video_id = extract_youtube_id(video_url)
    session = _get_sync_session()

    try:
        # 1. Smart Resume: Check existing status
        existing = session.execute(
            select(VideoSource).where(
                VideoSource.external_id == video_id,
                VideoSource.platform == Platform.YOUTUBE,
            )
        ).scalar_one_or_none()

        if existing:
            job = session.execute(
                select(ProcessingJob).where(ProcessingJob.video_source_id == existing.id)
            ).scalar_one_or_none()

            if job and job.status == ProcessingStatus.PENDING:
                logger.info(f"Resuming stuck job for video: {video_id}")
                extract_audio.delay(str(existing.id))
                return {"status": "resumed", "video_id": str(existing.id)}

            return {"status": "skipped", "reason": "already_exists", "video_id": video_id}

        # 2. Standard Ingestion
        metadata = fetch_video_metadata(video_url)
        if not metadata or metadata.duration_seconds > MAX_DURATION_SECONDS:
            return {"status": "skipped", "reason": "invalid_or_too_long"}

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

        job = (
            session.execute(
                select(ProcessingJob).where(ProcessingJob.id == job_id)
            ).scalar_one_or_none()
            if job_id
            else None
        )

        if not job:
            job = ProcessingJob(video_source_id=video_source.id, status=ProcessingStatus.PENDING)
            session.add(job)

        session.commit()

        # State machine handshake
        manager = JobManager(session, str(video_source.id))
        manager.start_stage("ingestion")
        manager.complete_stage(metadata={"title": metadata.title})

        extract_audio.delay(str(video_source.id))
        return {"status": "ingested", "video_id": str(video_source.id)}

    except Exception as e:
        session.rollback()
        raise self.retry(exc=e) from e
    finally:
        session.close()


@shared_task(
    name="aqar_pipeline.stages.ingestion.retry_failed_jobs",
    queue="ingestion",
)
def retry_failed_jobs():
    """
    Retry processing jobs that previously failed.

    Runs hourly via Celery beat. Only retries jobs that have not
    exceeded their max_retries limit.
    """
    session = _get_sync_session()

    try:
        # Find failed jobs that can be retried
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
            job.error_stage = None
            job.error_traceback = None
            retried += 1

            logger.info(f"Retrying job {job.id} (attempt {job.retry_count}/{job.max_retries})")

        session.commit()

        logger.info(f"Retried {retried} failed jobs out of {len(failed_jobs)} eligible")
        return {"status": "completed", "retried": retried, "total_failed": len(failed_jobs)}

    except Exception as e:
        session.rollback()
        logger.error(f"Error retrying failed jobs: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        session.close()
