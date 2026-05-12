"""
Aqar.ai - Pipeline Routes
=========================
Submit videos for processing and check pipeline status.
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.api.app.core.database import get_db
from apps.api.app.schemas import PipelineStatusResponse, PipelineSubmitRequest
from models.base import Platform, ProcessingJob, ProcessingStatus, VideoSource

logger = structlog.get_logger()
router = APIRouter()


@router.post("/pipeline/submit", response_model=PipelineStatusResponse)
async def submit_video(
    db: Annotated[AsyncSession, Depends(get_db)],
    request: PipelineSubmitRequest,
):
    """
    Submit a video URL for processing through the AI pipeline.
    The pipeline will: ingest -> transcribe -> extract -> geocode.
    """
    url = request.url.strip()

    # Check for duplicates
    existing = await db.execute(select(VideoSource).where(VideoSource.url == url))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="This video URL has already been submitted",
        )

    # Detect platform
    platform = Platform.YOUTUBE  # MVP: YouTube only
    if "tiktok.com" in url:
        raise HTTPException(status_code=400, detail="TikTok support coming in Phase 2")
    if "instagram.com" in url:
        raise HTTPException(status_code=400, detail="Instagram support coming in Phase 2")
    if "youtube.com" not in url and "youtu.be" not in url:
        raise HTTPException(status_code=400, detail="Only YouTube URLs are supported in MVP")

    # Create video source
    video = VideoSource(
        url=url,
        platform=platform,
        external_id=_extract_youtube_id(url),
    )
    db.add(video)
    await db.flush()

    # Create processing job
    job = ProcessingJob(
        video_source_id=video.id,
        status=ProcessingStatus.PENDING,
    )
    db.add(job)
    await db.flush()

    logger.info("Video submitted for processing", video_id=str(video.id), url=url)

    # Dispatch Celery ingestion task with the JOB ID
    from aqar_pipeline.stages.ingestion import ingest_video

    # We pass str(job.id) so the worker knows exactly which record to update
    ingest_video.delay(url, job_id=str(job.id))

    return PipelineStatusResponse(
        job_id=job.id,
        video_url=url,
        status=job.status.value,
        current_stage=None,
    )


@router.get("/pipeline/status/{job_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    job_id: uuid.UUID,
):
    """Check the processing status of a submitted video."""
    query = select(ProcessingJob).where(ProcessingJob.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Processing job not found")

    # Get the video URL
    video = await db.execute(select(VideoSource).where(VideoSource.id == job.video_source_id))
    video_source = video.scalar_one()

    return PipelineStatusResponse(
        job_id=job.id,
        video_url=video_source.url,
        status=job.status.value,
        current_stage=job.current_stage,
        retry_count=job.retry_count,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        stage_timings=job.stage_timings,
    )


def _extract_youtube_id(url: str) -> str:
    """Extract YouTube video ID from URL."""
    import re

    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return url  # Fallback: use full URL as ID


@router.get("/pipeline/jobs", response_model=list[PipelineStatusResponse])
async def list_all_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],  # Annotated pattern
    limit: int = 10,
):
    """Retrieve the most recent processing jobs with their video URLs."""
    # 1. Query ProcessingJob and Eager Load the VideoSource
    result = await db.execute(
        select(ProcessingJob)
        .options(
            joinedload(ProcessingJob.video_source)
        )  # Ensure relationship is defined in your model
        .order_by(ProcessingJob.created_at.desc())
        .limit(limit)
    )
    jobs = result.unique().scalars().all()

    # 2. Map the DB models to the Pydantic schema
    response_items = []
    for job in jobs:
        # Check if the relationship is loaded; if not, we handle the error gracefully
        video_url = job.video_source.url if job.video_source else "Unknown"

        response_items.append(
            PipelineStatusResponse(
                job_id=job.id,
                video_url=video_url,
                status=job.status.value,
                current_stage=job.current_stage,
                retry_count=job.retry_count,
                started_at=job.started_at,
                completed_at=job.completed_at,
                error_message=job.error_message,
                stage_timings=job.stage_timings,
            )
        )

    return response_items


# apps/api/app/routers/pipeline.py
@router.get("/pipeline/jobs", response_model=list[PipelineStatusResponse])
async def _list_all_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 10,
):
    """Retrieve the most recent processing jobs."""
    result = await db.execute(
        select(ProcessingJob).order_by(ProcessingJob.created_at.desc()).limit(limit)
    )
    jobs = result.scalars().all()
    # You would then map these to your response schema
    return jobs
