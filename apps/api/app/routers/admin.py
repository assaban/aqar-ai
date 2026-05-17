"""
Aqar.ai - Pipeline Admin Routes
================================
Administrative endpoints for managing the processing pipeline.
Allows operators to diagnose, retry, and cancel stuck/failed jobs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.database import get_db
from models.base import ProcessingJob, ProcessingStatus, VideoSource

logger = structlog.get_logger()
router = APIRouter()

# A job is considered "stuck" if it has been in a non-terminal state
# for longer than this threshold
STUCK_THRESHOLD_MINUTES = 30


@router.get("/pipeline/admin/diagnostics")
async def pipeline_diagnostics(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Pipeline health diagnostics.

    Returns counts by status, stuck jobs, and queue health information.
    Useful for quickly understanding why jobs are not progressing.
    """
    # Count by status
    status_counts = {}
    for status in ProcessingStatus:
        result = await db.execute(select(ProcessingJob).where(ProcessingJob.status == status))
        jobs = result.scalars().all()
        status_counts[status.value] = len(jobs)

    # Find stuck jobs (non-terminal, not updated recently)
    threshold = datetime.now(UTC) - timedelta(minutes=STUCK_THRESHOLD_MINUTES)
    stuck_result = await db.execute(
        select(ProcessingJob).where(
            ProcessingJob.status.notin_(
                [
                    ProcessingStatus.COMPLETED,
                    ProcessingStatus.FAILED,
                    ProcessingStatus.SKIPPED,
                    ProcessingStatus.PENDING,
                ]
            ),
            ProcessingJob.updated_at < threshold,
        )
    )
    stuck_jobs = stuck_result.scalars().all()

    stuck_details = []
    for job in stuck_jobs:
        video_result = await db.execute(
            select(VideoSource).where(VideoSource.id == job.video_source_id)
        )
        video = video_result.scalar_one_or_none()
        stuck_details.append(
            {
                "job_id": str(job.id),
                "status": job.status.value,
                "current_stage": job.current_stage,
                "video_title": video.title if video else "Unknown",
                "video_url": video.url if video else "",
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "retry_count": job.retry_count,
                "error_message": job.error_message,
            }
        )

    return {
        "status_counts": status_counts,
        "stuck_jobs": stuck_details,
        "stuck_count": len(stuck_details),
        "stuck_threshold_minutes": STUCK_THRESHOLD_MINUTES,
    }


@router.post("/pipeline/admin/retry/{job_id}")
async def retry_job(
    db: Annotated[AsyncSession, Depends(get_db)],
    job_id: uuid.UUID,
    from_stage: str | None = Query(
        None,
        description="Restart from a specific stage: ingestion, audio_extraction, transcription, extraction, geocoding",
    ),
):
    """
    Retry a specific job.

    Resets the job to PENDING and optionally specifies which stage to restart from.
    Then dispatches the appropriate Celery task.
    """
    job = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
    job_record = job.scalar_one_or_none()

    if not job_record:
        raise HTTPException(status_code=404, detail="Job not found")

    video = await db.execute(
        select(VideoSource).where(VideoSource.id == job_record.video_source_id)
    )
    video_record = video.scalar_one_or_none()

    if not video_record:
        raise HTTPException(status_code=404, detail="Video source not found")

    # Reset job status
    job_record.status = ProcessingStatus.PENDING
    job_record.error_message = None
    job_record.error_stage = None
    job_record.error_traceback = None
    job_record.retry_count += 1
    job_record.updated_at = datetime.now(UTC)
    await db.flush()

    # Dispatch the appropriate task based on from_stage
    stage = from_stage or "ingestion"

    if stage == "ingestion":
        from aqar_pipeline.stages.ingestion import ingest_video

        ingest_video.delay(video_record.url, job_id=str(job_record.id))
    elif stage == "audio_extraction":
        from aqar_pipeline.stages.audio_extraction import extract_audio

        extract_audio.delay(str(video_record.id))
    elif stage == "transcription":
        from aqar_pipeline.utils.audio import get_audio_path

        audio_path = get_audio_path(video_record.external_id)
        from aqar_pipeline.stages.transcription import transcribe_audio

        transcribe_audio.delay(str(video_record.id), audio_path)
    elif stage == "extraction":
        from aqar_pipeline.stages.extraction import extract_properties

        extract_properties.delay(str(video_record.id))
    elif stage == "geocoding":
        from aqar_pipeline.stages.geocoding import geocode_properties

        geocode_properties.delay(str(video_record.id))
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown stage: {stage}. Valid: ingestion, audio_extraction, transcription, extraction, geocoding",
        )

    logger.info(
        "Job retried",
        job_id=str(job_id),
        from_stage=stage,
        video_url=video_record.url,
    )

    return {
        "status": "retried",
        "job_id": str(job_id),
        "from_stage": stage,
        "video_url": video_record.url,
    }


@router.post("/pipeline/admin/retry-all-stuck")
async def retry_all_stuck(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Find all stuck jobs and retry them from their current stage.

    A job is "stuck" if it has been in a processing state (INGESTING,
    TRANSCRIBING, EXTRACTING, GEOCODING) for longer than the threshold.
    """
    threshold = datetime.now(UTC) - timedelta(minutes=STUCK_THRESHOLD_MINUTES)

    stuck_result = await db.execute(
        select(ProcessingJob).where(
            ProcessingJob.status.notin_(
                [
                    ProcessingStatus.COMPLETED,
                    ProcessingStatus.FAILED,
                    ProcessingStatus.SKIPPED,
                    ProcessingStatus.PENDING,
                ]
            ),
            ProcessingJob.updated_at < threshold,
        )
    )
    stuck_jobs = stuck_result.scalars().all()

    retried = []
    for job in stuck_jobs:
        video = await db.execute(select(VideoSource).where(VideoSource.id == job.video_source_id))
        video_record = video.scalar_one_or_none()
        if not video_record:
            continue

        # Determine which stage to restart from
        stage = _status_to_restart_stage(job.status, job.current_stage)

        job.status = ProcessingStatus.PENDING
        job.error_message = None
        job.error_stage = None
        job.retry_count += 1
        job.updated_at = datetime.now(UTC)

        # Dispatch task
        _dispatch_stage(stage, video_record, job)

        retried.append(
            {
                "job_id": str(job.id),
                "from_stage": stage,
                "video_url": video_record.url,
            }
        )

    await db.flush()

    logger.info(f"Retried {len(retried)} stuck jobs")
    return {"retried_count": len(retried), "jobs": retried}


@router.post("/pipeline/admin/cancel/{job_id}")
async def cancel_job(
    db: Annotated[AsyncSession, Depends(get_db)],
    job_id: uuid.UUID,
):
    """
    Cancel a job by marking it as SKIPPED.

    This does not revoke running Celery tasks, but prevents the
    job from being retried.
    """
    job = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
    job_record = job.scalar_one_or_none()

    if not job_record:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_record.status in (ProcessingStatus.COMPLETED, ProcessingStatus.SKIPPED):
        raise HTTPException(
            status_code=400,
            detail=f"Job is already {job_record.status.value}, cannot cancel",
        )

    job_record.status = ProcessingStatus.SKIPPED
    job_record.error_message = "Cancelled by admin"
    job_record.updated_at = datetime.now(UTC)
    await db.flush()

    logger.info("Job cancelled", job_id=str(job_id))
    return {"status": "cancelled", "job_id": str(job_id)}


@router.post("/pipeline/admin/reset-failed")
async def reset_all_failed(db: Annotated[AsyncSession, Depends(get_db)]):
    """Reset all FAILED jobs back to PENDING for retry."""
    result = await db.execute(
        select(ProcessingJob).where(
            ProcessingJob.status == ProcessingStatus.FAILED,
            ProcessingJob.retry_count < ProcessingJob.max_retries,
        )
    )
    failed_jobs = result.scalars().all()

    count = 0
    for job in failed_jobs:
        job.status = ProcessingStatus.PENDING
        job.error_message = None
        job.error_stage = None
        job.error_traceback = None
        job.retry_count += 1
        job.updated_at = datetime.now(UTC)
        count += 1

    await db.flush()

    logger.info(f"Reset {count} failed jobs to PENDING")
    return {"reset_count": count}


def _status_to_restart_stage(status: ProcessingStatus, current_stage: str | None) -> str:
    """Map a stuck status to the stage it should restart from."""
    if current_stage:
        return current_stage

    mapping = {
        ProcessingStatus.INGESTING: "audio_extraction",
        ProcessingStatus.TRANSCRIBING: "transcription",
        ProcessingStatus.EXTRACTING: "extraction",
        ProcessingStatus.GEOCODING: "geocoding",
    }
    return mapping.get(status, "ingestion")


def _dispatch_stage(stage: str, video, job):
    """Dispatch the appropriate Celery task for a stage."""
    video_id = str(video.id)

    if stage == "ingestion":
        from aqar_pipeline.stages.ingestion import ingest_video

        ingest_video.delay(video.url, job_id=str(job.id))
    elif stage == "audio_extraction":
        from aqar_pipeline.stages.audio_extraction import extract_audio

        extract_audio.delay(video_id)
    elif stage == "transcription":
        from aqar_pipeline.utils.audio import get_audio_path

        audio_path = get_audio_path(video.external_id)
        from aqar_pipeline.stages.transcription import transcribe_audio

        transcribe_audio.delay(video_id, audio_path)
    elif stage == "extraction":
        from aqar_pipeline.stages.extraction import extract_properties

        extract_properties.delay(video_id)
    elif stage == "geocoding":
        from aqar_pipeline.stages.geocoding import geocode_properties

        geocode_properties.delay(video_id)


@router.post("/pipeline/admin/scan-channel")
async def trigger_channel_scan(
    db: Annotated[AsyncSession, Depends(get_db)],
    channel_id: uuid.UUID | None = None,
    channel_url: str | None = None,
):
    """
    Admin: trigger an immediate discovery scan for a specific channel.
    Provide either channel_id (from DB) or channel_url (direct).
    """
    from models.base import ChannelRegistration

    url_to_scan = channel_url

    if channel_id:
        result = await db.execute(
            select(ChannelRegistration).where(ChannelRegistration.id == channel_id)
        )
        ch = result.scalar_one_or_none()
        if not ch:
            raise HTTPException(status_code=404, detail="Channel not found")
        url_to_scan = ch.channel_url

    if not url_to_scan:
        raise HTTPException(status_code=400, detail="Provide channel_id or channel_url")

    # Trigger the ingestion for each video found in the channel
    from aqar_pipeline.stages.ingestion import ingest_video
    from aqar_pipeline.utils.youtube import fetch_channel_videos

    try:
        videos = fetch_channel_videos(url_to_scan, max_videos=10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Channel scan failed: {str(e)}") from e

    submitted = 0
    for video in videos:
        ingest_video.delay(video.url)
        submitted += 1

    logger.info(f"Channel scan triggered: {submitted} videos from {url_to_scan}")
    return {
        "status": "scan_triggered",
        "channel_url": url_to_scan,
        "videos_submitted": submitted,
    }


@router.post("/pipeline/admin/discover-now")
async def trigger_discovery(region: str = "tangier-tetouan"):
    """Admin: trigger the full discovery task immediately (all approved channels)."""
    from aqar_pipeline.stages.ingestion import discover_videos

    discover_videos.delay(region=region)
    logger.info(f"Full discovery triggered for region: {region}")
    return {"status": "discovery_triggered", "region": region}


@router.get("/channels/{channel_id}/browse-videos")
async def browse_channel_videos(
    db: Annotated[AsyncSession, Depends(get_db)], channel_id: uuid.UUID, limit: int = 15
):
    """Fetch un-ingested videos from a channel to select them for manual processing."""
    from models.base import ChannelRegistration

    result = await db.execute(
        select(ChannelRegistration).where(ChannelRegistration.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel tracking record not found")

    from aqar_pipeline.utils.youtube import fetch_channel_videos

    try:
        videos = fetch_channel_videos(channel.channel_url, max_videos=limit)

        # Check against existing elements to add an intake safety flag
        processed_details = []
        for v in videos:
            existing = await db.execute(
                select(VideoSource).where(VideoSource.external_id == v.external_id)
            )
            processed_details.append(
                {
                    "external_id": v.external_id,
                    "title": v.title,
                    "url": v.url,
                    "duration_seconds": v.duration_seconds,
                    "published_at": v.published_at.isoformat() if v.published_at else None,
                    "already_listed": existing.scalar_one_or_none() is not None,
                }
            )
        return processed_details
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to scan channel targets: {str(e)}"
        ) from e
