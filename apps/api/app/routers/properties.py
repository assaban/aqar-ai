"""
Aqar.ai - Properties Routes
===========================
CRUD and search endpoints for real estate properties.
Includes PostGIS spatial queries and enhanced statistics.
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.api.app.core.database import get_db
from apps.api.app.schemas import (
    NeighborhoodStat,
    NeighborhoodStatsResponse,
    PropertyListResponse,
    PropertyResponse,
    StatsResponse,
)
from models.base import Location, ProcessingJob, ProcessingStatus, Property, VideoSource

logger = structlog.get_logger()
router = APIRouter()


@router.get("/properties", response_model=PropertyListResponse)
async def list_properties(
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
    lat: float | None = Query(None, description="Center latitude for radius search"),
    lng: float | None = Query(None, description="Center longitude for radius search"),
    radius_km: float | None = Query(None, description="Search radius in kilometers"),
    needs_review: bool | None = Query(None, description="Filter by review status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    """
    List and filter properties.

    Supports pagination, filtering by type/price/area, spatial queries
    (lat, lng, radius_km), and review status filtering.
    """
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
    if needs_review is not None:
        query = query.where(Property.needs_review == needs_review)
    if neighborhood:
        query = query.join(Property.location).where(
            Location.neighborhood.ilike(f"%{neighborhood}%")
        )

    # Spatial query: find properties within radius
    if lat is not None and lng is not None and radius_km is not None:
        radius_m = radius_km * 1000
        search_point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
        query = query.join(Property.location).where(
            ST_DWithin(
                cast(Location.geom, Location.geom.type),
                search_point,
                radius_m,
                use_spheroid=True,
            )
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
    db: Annotated[AsyncSession, Depends(get_db)],
    property_id: uuid.UUID,
):
    """Get a single property by ID with full details."""
    query = (
        select(Property).options(joinedload(Property.location)).where(Property.id == property_id)
    )
    result = await db.execute(query)
    prop = result.unique().scalar_one_or_none()

    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    return PropertyResponse.model_validate(prop)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Get system-wide statistics.

    Includes counts, averages, property/listing type breakdowns,
    and pipeline performance metrics.
    """
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
    completed = await db.execute(
        select(func.count(ProcessingJob.id)).where(
            ProcessingJob.status == ProcessingStatus.COMPLETED
        )
    )
    avg_conf = await db.execute(
        select(func.avg(Property.extraction_confidence)).where(
            Property.extraction_confidence.isnot(None)
        )
    )

    # Property type breakdown
    type_rows = await db.execute(
        select(
            cast(Property.property_type, String),
            func.count(Property.id),
        ).group_by(Property.property_type)
    )
    property_types = {row[0]: row[1] for row in type_rows.all()}

    # Listing type breakdown
    listing_rows = await db.execute(
        select(
            cast(Property.listing_type, String),
            func.count(Property.id),
        ).group_by(Property.listing_type)
    )
    listing_types = {row[0]: row[1] for row in listing_rows.all()}

    return StatsResponse(
        total_videos=videos.scalar_one(),
        total_properties=properties.scalar_one(),
        total_published=published.scalar_one(),
        processing_pending=pending.scalar_one(),
        processing_failed=failed.scalar_one(),
        processing_completed=completed.scalar_one(),
        avg_extraction_confidence=avg_conf.scalar_one(),
        property_types=property_types,
        listing_types=listing_types,
    )


@router.get("/stats/neighborhoods", response_model=NeighborhoodStatsResponse)
async def get_neighborhood_stats(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Get per-neighborhood statistics.

    Returns property count and price statistics for each neighborhood
    that has at least one property.
    """
    rows = await db.execute(
        select(
            Location.neighborhood,
            func.count(Property.id).label("count"),
            func.avg(Property.price).label("avg_price"),
            func.min(Property.price).label("min_price"),
            func.max(Property.price).label("max_price"),
        )
        .join(Property, Location.property_id == Property.id)
        .where(
            Location.neighborhood.isnot(None),
            Location.neighborhood != "",
        )
        .group_by(Location.neighborhood)
        .order_by(func.count(Property.id).desc())
    )

    neighborhoods = []
    for row in rows.all():
        neighborhoods.append(
            NeighborhoodStat(
                neighborhood=row[0],
                property_count=row[1],
                avg_price=round(row[2], 0) if row[2] else None,
                min_price=row[3],
                max_price=row[4],
            )
        )

    return NeighborhoodStatsResponse(
        neighborhoods=neighborhoods,
        total_neighborhoods=len(neighborhoods),
    )
