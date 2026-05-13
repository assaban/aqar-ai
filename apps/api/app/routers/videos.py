"""
Aqar.ai - Videos Routes
========================
Endpoints for listing processed videos and their details.
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.api.app.core.database import get_db
from apps.api.app.schemas import (
    PropertyResponse,
    VideoDetailResponse,
    VideoListResponse,
    VideoSourceResponse,
)
from models.base import ProcessingJob, Property, Transcript, VideoSource

logger = structlog.get_logger()
router = APIRouter()


@router.get("/videos", response_model=VideoListResponse)
async def list_videos(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    channel: str | None = None,
):
    """
    List all processed videos with pagination.

    Optionally filter by channel name.
    """
    query = select(VideoSource)

    if channel:
        query = query.where(VideoSource.channel_name.ilike(f"%{channel}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()

    # Paginate
    offset = (page - 1) * per_page
    query = query.order_by(VideoSource.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    videos = result.scalars().all()

    # Get property counts for each video
    items = []
    for video in videos:
        prop_count_result = await db.execute(
            select(func.count(Property.id)).where(Property.video_source_id == video.id)
        )
        prop_count = prop_count_result.scalar_one()

        items.append(
            VideoSourceResponse(
                id=video.id,
                url=video.url,
                platform=video.platform.value if video.platform else "youtube",
                title=video.title,
                channel_name=video.channel_name,
                duration_seconds=video.duration_seconds,
                thumbnail_url=video.thumbnail_url,
                published_at=video.published_at,
                properties_count=prop_count,
            )
        )

    return VideoListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        has_next=(offset + per_page) < total,
    )


@router.get("/videos/{video_id}", response_model=VideoDetailResponse)
async def get_video_detail(
    db: Annotated[AsyncSession, Depends(get_db)],
    video_id: uuid.UUID,
):
    """
    Get full video details including transcript and extracted properties.

    Useful for debugging the pipeline and viewing extraction results.
    """
    video = await db.execute(select(VideoSource).where(VideoSource.id == video_id))
    video_source = video.scalar_one_or_none()

    if not video_source:
        raise HTTPException(status_code=404, detail="Video not found")

    # Load transcript
    transcript_result = await db.execute(
        select(Transcript).where(Transcript.video_source_id == video_source.id)
    )
    transcript = transcript_result.scalar_one_or_none()

    # Load properties with locations
    properties_result = await db.execute(
        select(Property)
        .options(joinedload(Property.location))
        .where(Property.video_source_id == video_source.id)
    )
    properties = properties_result.unique().scalars().all()

    # Load processing job
    job_result = await db.execute(
        select(ProcessingJob).where(ProcessingJob.video_source_id == video_source.id)
    )
    job = job_result.scalar_one_or_none()

    return VideoDetailResponse(
        id=video_source.id,
        url=video_source.url,
        platform=video_source.platform.value if video_source.platform else "youtube",
        title=video_source.title,
        channel_name=video_source.channel_name,
        duration_seconds=video_source.duration_seconds,
        thumbnail_url=video_source.thumbnail_url,
        published_at=video_source.published_at,
        properties_count=len(properties),
        transcript_text=transcript.full_text if transcript else None,
        transcript_language=transcript.language if transcript else None,
        transcript_confidence=transcript.confidence if transcript else None,
        properties=[PropertyResponse.model_validate(p) for p in properties],
        processing_status=job.status.value if job else None,
        processing_stage=job.current_stage if job else None,
        stage_timings=job.stage_timings if job else None,
    )
