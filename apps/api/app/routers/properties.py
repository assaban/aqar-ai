"""
Aqar.ai - Properties Routes
===========================
CRUD and search endpoints for real estate properties.
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
    PropertyListResponse,
    PropertyResponse,
    StatsResponse,
)
from packages.db.models import Location, ProcessingJob, ProcessingStatus, Property, VideoSource

logger = structlog.get_logger()
router = APIRouter()


@router.get("/properties", response_model=PropertyListResponse)
async def list_properties(  # Move the dependency to the start to satisfy Python syntax and B008
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = None,
    property_type: str | None = None,
    listing_type: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    area_min: float | None = None,
    area_max: float | None = None,
    rooms_min: int | None = None,
    neighborhood: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    """
    List and filter properties.
    Supports pagination, filtering by type/price/area, and sorting.
    """
    # Build query
    query = (
        select(Property).options(joinedload(Property.location)).where(Property.is_published == True)  # noqa: E712
    )

    # Apply filters
    if property_type:
        query = query.where(Property.property_type == property_type)
    if listing_type:
        query = query.where(Property.listing_type == listing_type)
    if price_min is not None:
        query = query.where(Property.price >= price_min)
    if price_max is not None:
        query = query.where(Property.price <= price_max)
    if area_min is not None:
        query = query.where(Property.area_sqm >= area_min)
    if area_max is not None:
        query = query.where(Property.area_sqm <= area_max)
    if rooms_min is not None:
        query = query.where(Property.rooms >= rooms_min)
    if neighborhood:
        query = query.join(Property.location).where(
            Location.neighborhood.ilike(f"%{neighborhood}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()

    # Sort
    sort_col = getattr(Property, sort_by, Property.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    properties = result.unique().scalars().all()

    return PropertyListResponse(
        items=[PropertyResponse.model_validate(p) for p in properties],
        total=total,
        page=page,
        per_page=per_page,
        has_next=(offset + per_page) < total,
    )


@router.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a single property by ID with full details."""
    query = (
        select(Property).options(joinedload(Property.location)).where(Property.id == property_id)
    )
    result = await db.execute(query)
    property = result.unique().scalar_one_or_none()

    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    return PropertyResponse.model_validate(property)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: Annotated[AsyncSession, Depends(get_db)]):
    """Get system-wide statistics."""
    videos = await db.execute(select(func.count(VideoSource.id)))
    properties = await db.execute(select(func.count(Property.id)))
    published = await db.execute(
        select(func.count(Property.id)).where(Property.is_published == True)  # noqa: E712
    )
    pending = await db.execute(
        select(func.count(ProcessingJob.id)).where(ProcessingJob.status == ProcessingStatus.PENDING)
    )
    failed = await db.execute(
        select(func.count(ProcessingJob.id)).where(ProcessingJob.status == ProcessingStatus.FAILED)
    )
    avg_conf = await db.execute(
        select(func.avg(Property.extraction_confidence)).where(
            Property.extraction_confidence.isnot(None)
        )
    )

    return StatsResponse(
        total_videos=videos.scalar_one(),
        total_properties=properties.scalar_one(),
        total_published=published.scalar_one(),
        processing_pending=pending.scalar_one(),
        processing_failed=failed.scalar_one(),
        avg_extraction_confidence=avg_conf.scalar_one(),
    )
