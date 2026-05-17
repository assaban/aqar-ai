"""
Aqar.ai - Property Service
===========================
Business logic for property CRUD, search, and statistics.
Routes delegate to this service; no business logic in controllers.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from models.base import (
    Location,
    ProcessingJob,
    ProcessingStatus,
    Property,
    VideoSource,
)

# ═══════════════════════════════════════
# DTOs (Data Transfer Objects)
# ═══════════════════════════════════════


class PropertyUpdateDTO(BaseModel):
    """Fields that can be manually updated by admin."""

    title_generated: str | None = None
    description_generated: str | None = None
    property_type: str | None = None
    listing_type: str | None = None
    price: float | None = None
    price_currency: str | None = None
    area_sqm: float | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    floors: int | None = None
    floor_number: int | None = None
    has_garage: bool | None = None
    has_garden: bool | None = None
    has_elevator: bool | None = None
    legal_status: str | None = None
    is_published: bool | None = None
    needs_review: bool | None = None


class PropertyFilterDTO(BaseModel):
    """Filter parameters for property listing."""

    property_type: str | None = None
    listing_type: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    area_min: float | None = None
    area_max: float | None = None
    rooms_min: int | None = None
    neighborhood: str | None = None
    lat: float | None = None
    lng: float | None = None
    radius_km: float | None = None
    needs_review: bool | None = None
    page: int = 1
    per_page: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"


# ═══════════════════════════════════════
# Service Functions
# ═══════════════════════════════════════


async def get_property_by_id(db: AsyncSession, property_id: uuid.UUID) -> Property | None:
    """Fetch a single property with its location."""
    result = await db.execute(
        select(Property).options(joinedload(Property.location)).where(Property.id == property_id)
    )
    return result.unique().scalar_one_or_none()


async def list_properties(
    db: AsyncSession, filters: PropertyFilterDTO
) -> tuple[list[Property], int]:
    """List properties with filtering, pagination, and optional spatial query."""
    query = (
        select(Property).options(joinedload(Property.location)).where(Property.is_published == True)  # noqa: E712
    )

    if filters.property_type:
        query = query.where(Property.property_type == filters.property_type)
    if filters.listing_type:
        query = query.where(Property.listing_type == filters.listing_type)
    if filters.price_min is not None:
        query = query.where(Property.price >= filters.price_min)
    if filters.price_max is not None:
        query = query.where(Property.price <= filters.price_max)
    if filters.area_min is not None:
        query = query.where(Property.area_sqm >= filters.area_min)
    if filters.area_max is not None:
        query = query.where(Property.area_sqm <= filters.area_max)
    if filters.rooms_min is not None:
        query = query.where(Property.rooms >= filters.rooms_min)
    if filters.needs_review is not None:
        query = query.where(Property.needs_review == filters.needs_review)
    if filters.neighborhood:
        query = query.join(Property.location).where(
            Location.neighborhood.ilike(f"%{filters.neighborhood}%")
        )

    # Spatial query
    if filters.lat is not None and filters.lng is not None and filters.radius_km is not None:
        from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID

        radius_m = filters.radius_km * 1000
        search_point = ST_SetSRID(ST_MakePoint(filters.lng, filters.lat), 4326)
        query = query.join(Property.location).where(
            ST_DWithin(
                cast(Location.geom, Location.geom.type), search_point, radius_m, use_spheroid=True
            )
        )

    # Count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    # Sort
    sort_col = getattr(Property, filters.sort_by, Property.created_at)
    query = query.order_by(sort_col.desc() if filters.sort_order == "desc" else sort_col.asc())

    # Paginate
    offset = (filters.page - 1) * filters.per_page
    query = query.offset(offset).limit(filters.per_page)

    result = await db.execute(query)
    return result.unique().scalars().all(), total


async def update_property(
    db: AsyncSession,
    property_id: uuid.UUID,
    updates: PropertyUpdateDTO,
) -> Property | None:
    """Update a property with the given fields. Only non-None fields are applied."""
    prop = await get_property_by_id(db, property_id)
    if not prop:
        return None

    update_data = updates.model_dump(exclude_none=True)
    for field_name, value in update_data.items():
        setattr(prop, field_name, value)

    prop.updated_at = datetime.now(UTC)
    await db.flush()
    return prop


async def get_recent_properties(db: AsyncSession, limit: int = 10) -> list[Property]:
    """Fetch the most recently published properties (for homepage)."""
    result = await db.execute(
        select(Property)
        .options(joinedload(Property.location))
        .where(Property.is_published == True)  # noqa: E712
        .order_by(Property.created_at.desc())
        .limit(limit)
    )
    return result.unique().scalars().all()


async def get_stats(db: AsyncSession) -> dict:
    """Calculate system-wide statistics."""
    videos = (await db.execute(select(func.count(VideoSource.id)))).scalar_one()
    properties = (await db.execute(select(func.count(Property.id)))).scalar_one()
    published = (
        await db.execute(
            select(func.count(Property.id)).where(Property.is_published == True)  # noqa: E712
        )
    ).scalar_one()
    pending = (
        await db.execute(
            select(func.count(ProcessingJob.id)).where(
                ProcessingJob.status == ProcessingStatus.PENDING
            )
        )
    ).scalar_one()
    failed = (
        await db.execute(
            select(func.count(ProcessingJob.id)).where(
                ProcessingJob.status == ProcessingStatus.FAILED
            )
        )
    ).scalar_one()
    completed = (
        await db.execute(
            select(func.count(ProcessingJob.id)).where(
                ProcessingJob.status == ProcessingStatus.COMPLETED
            )
        )
    ).scalar_one()
    avg_conf = (
        await db.execute(
            select(func.avg(Property.extraction_confidence)).where(
                Property.extraction_confidence.isnot(None)
            )
        )
    ).scalar_one()

    # Type breakdowns
    type_rows = await db.execute(
        select(cast(Property.property_type, String), func.count(Property.id)).group_by(
            Property.property_type
        )
    )
    listing_rows = await db.execute(
        select(cast(Property.listing_type, String), func.count(Property.id)).group_by(
            Property.listing_type
        )
    )

    return {
        "total_videos": videos,
        "total_properties": properties,
        "total_published": published,
        "processing_pending": pending,
        "processing_failed": failed,
        "processing_completed": completed,
        "avg_extraction_confidence": avg_conf,
        "property_types": {r[0]: r[1] for r in type_rows.all()},
        "listing_types": {r[0]: r[1] for r in listing_rows.all()},
    }


async def get_neighborhood_stats(db: AsyncSession) -> list[dict]:
    """Per-neighborhood property statistics."""
    rows = await db.execute(
        select(
            Location.neighborhood,
            func.count(Property.id).label("count"),
            func.avg(Property.price).label("avg_price"),
            func.min(Property.price).label("min_price"),
            func.max(Property.price).label("max_price"),
        )
        .join(Property, Location.property_id == Property.id)
        .where(Location.neighborhood.isnot(None), Location.neighborhood != "")
        .group_by(Location.neighborhood)
        .order_by(func.count(Property.id).desc())
    )
    return [
        {
            "neighborhood": r[0],
            "property_count": r[1],
            "avg_price": round(r[2], 0) if r[2] else None,
            "min_price": r[3],
            "max_price": r[4],
        }
        for r in rows.all()
    ]
