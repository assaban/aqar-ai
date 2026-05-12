"""
Aqar.ai: Audio Extraction Stage
================================
Celery task that downloads audio from YouTube videos and converts
to WAV format (16kHz mono) for Whisper transcription.

Tasks:
  - extract_audio: Downloads and converts audio for a single video.
  - cleanup_audio: Removes audio file after successful transcription.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import UTC, datetime

from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from models.base import ProcessingJob, ProcessingStatus, VideoSource

logger = logging.getLogger(__name__)

DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://aqar:aqar_dev_password@db:5432/aqar_db",
)


def _get_sync_session() -> Session:
    """Create a sync SQLAlchemy session for use in Celery tasks."""
    engine = create_engine(DATABASE_URL_SYNC, pool_pre_ping=True)
    return Session(engine)


@shared_task(
    name="aqar_pipeline.stages.audio_extraction.extract_audio",
    queue="ingestion",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def extract_audio(self, video_source_id: str):
    """
    Download audio from a YouTube video and convert to WAV.

    This task is triggered after a video is discovered or submitted.
    It downloads the audio stream, converts it to 16kHz mono WAV
    (optimal for Whisper), and updates the processing job status.

    Args:
        video_source_id: UUID string of the VideoSource record.

    Returns:
        Dict with status, audio_path, and duration info.
    """
    from aqar_pipeline.utils.audio import (
        ensure_download_dir,
        get_audio_path,
        validate_wav_file,
    )
    from aqar_pipeline.utils.youtube import download_audio

    logger.info(f"Starting audio extraction for video: {video_source_id}")
    start_time = time.time()

    session = _get_sync_session()

    try:
        # Load the video source
        video = session.execute(
            select(VideoSource).where(VideoSource.id == video_source_id)
        ).scalar_one_or_none()

        if not video:
            logger.error(f"VideoSource not found: {video_source_id}")
            return {"status": "error", "message": "Video not found"}

        # Load the processing job
        job = session.execute(
            select(ProcessingJob).where(ProcessingJob.video_source_id == video.id)
        ).scalar_one_or_none()

        if not job:
            logger.error(f"ProcessingJob not found for video: {video_source_id}")
            return {"status": "error", "message": "Processing job not found"}

        # Update status to INGESTING
        job.status = ProcessingStatus.INGESTING
        job.current_stage = "audio_extraction"
        job.started_at = job.started_at or datetime.now(UTC)
        session.commit()

        # Prepare download directory
        ensure_download_dir()
        audio_path = get_audio_path(video.external_id)

        # Skip if already downloaded (e.g. retry after partial failure)
        if os.path.exists(audio_path):
            audio_info = validate_wav_file(audio_path)
            if audio_info and audio_info.duration_seconds > 0:
                logger.info(f"Audio already exists, skipping download: {audio_path}")
                _update_job_success(session, job, start_time)
                return {
                    "status": "completed",
                    "audio_path": audio_path,
                    "cached": True,
                    "duration_seconds": audio_info.duration_seconds,
                }

        # Download and convert audio
        logger.info(f"Downloading audio: {video.url}")
        success = download_audio(
            video_url=video.url,
            output_path=audio_path,
            sample_rate=16000,
        )

        if not success:
            _update_job_failure(
                session,
                job,
                stage="audio_extraction",
                message=f"Failed to download audio from {video.url}",
            )
            raise self.retry(
                exc=RuntimeError(f"Audio download failed for {video.url}"),
            )

        # Validate the downloaded file
        audio_info = validate_wav_file(audio_path)
        if not audio_info:
            _update_job_failure(
                session,
                job,
                stage="audio_extraction",
                message=f"Downloaded file is not a valid WAV: {audio_path}",
            )
            raise self.retry(
                exc=RuntimeError(f"Invalid WAV file: {audio_path}"),
            )

        # Update job status to ready for transcription
        _update_job_success(session, job, start_time)

        elapsed = time.time() - start_time
        logger.info(
            f"Audio extraction complete: {audio_path} "
            f"(duration={audio_info.duration_seconds}s, "
            f"size={audio_info.file_size_bytes / (1024 * 1024):.1f}MB, "
            f"elapsed={elapsed:.1f}s)"
        )

        return {
            "status": "completed",
            "video_source_id": video_source_id,
            "audio_path": audio_path,
            "duration_seconds": audio_info.duration_seconds,
            "file_size_mb": round(audio_info.file_size_bytes / (1024 * 1024), 2),
            "sample_rate": audio_info.sample_rate,
            "channels": audio_info.channels,
            "elapsed_seconds": round(elapsed, 2),
        }

    except self.MaxRetriesExceededError:
        logger.error(f"Max retries exceeded for video: {video_source_id}")
        _update_job_failure(
            session,
            job,
            stage="audio_extraction",
            message="Max retries exceeded for audio extraction",
        )
        return {"status": "failed", "message": "Max retries exceeded"}

    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error in audio extraction: {e}")
        raise self.retry(exc=e) from e  # Added 'from e'

    finally:
        session.close()


@shared_task(
    name="aqar_pipeline.stages.audio_extraction.cleanup_audio",
    queue="ingestion",
)
def cleanup_audio(video_external_id: str, download_dir: str | None = None):
    """
    Remove an audio file after successful transcription.

    Called by the transcription stage after processing is complete.

    Args:
        video_external_id: YouTube video ID (used for filename).
        download_dir: Override download directory.

    Returns:
        Dict with cleanup status.
    """
    from aqar_pipeline.utils.audio import cleanup_audio_file, get_audio_path

    audio_path = get_audio_path(video_external_id, download_dir)
    success = cleanup_audio_file(audio_path)

    return {
        "status": "cleaned" if success else "failed",
        "path": audio_path,
    }


def _update_job_success(session: Session, job: ProcessingJob, start_time: float):
    """Update job status after successful audio extraction."""
    elapsed = time.time() - start_time
    job.status = ProcessingStatus.TRANSCRIBING
    job.current_stage = "transcription"

    # Update stage timings
    timings = job.stage_timings or {}
    timings["audio_extraction"] = round(elapsed, 2)
    job.stage_timings = timings

    session.commit()


def _update_job_failure(
    session: Session,
    job: ProcessingJob,
    stage: str,
    message: str,
    traceback_str: str | None = None,
):
    """Update job status after a failure."""
    job.status = ProcessingStatus.FAILED
    job.error_stage = stage
    job.error_message = message
    job.error_traceback = traceback_str
    session.commit()
