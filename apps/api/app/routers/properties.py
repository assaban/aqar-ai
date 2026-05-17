"""
Aqar.ai - Properties Controller
================================
Thin controller layer. All business logic is in services/property_service.py.
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.database import get_db
from apps.api.app.schemas import (
    NeighborhoodStat,
    NeighborhoodStatsResponse,
    PropertyListResponse,
    PropertyResponse,
    StatsResponse,
)
from apps.api.app.services.property_service import (
    PropertyFilterDTO,
    PropertyUpdateDTO,
    get_neighborhood_stats,
    get_property_by_id,
    get_recent_properties,
    get_stats,
    list_properties,
    update_property,
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("/properties", response_model=PropertyListResponse)
async def list_properties_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    property_type: str | None = None,
    listing_type: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    area_min: float | None = None,
    area_max: float | None = None,
    rooms_min: int | None = None,
    neighborhood: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float | None = None,
    needs_review: bool | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    """List and filter properties with pagination and spatial queries."""
    filters = PropertyFilterDTO(
        property_type=property_type,
        listing_type=listing_type,
        price_min=price_min,
        price_max=price_max,
        area_min=area_min,
        area_max=area_max,
        rooms_min=rooms_min,
        neighborhood=neighborhood,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        needs_review=needs_review,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    properties, total = await list_properties(db, filters)
    offset = (page - 1) * per_page

    return PropertyListResponse(
        items=[PropertyResponse.model_validate(p) for p in properties],
        total=total,
        page=page,
        per_page=per_page,
        has_next=(offset + per_page) < total,
    )


@router.get("/properties/recent", response_model=list[PropertyResponse])
async def recent_properties_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(10, ge=1, le=50),
):
    """Get the most recently published properties (for homepage)."""
    properties = await get_recent_properties(db, limit)
    return [PropertyResponse.model_validate(p) for p in properties]


@router.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    property_id: uuid.UUID,
):
    """Get a single property by ID."""
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return PropertyResponse.model_validate(prop)


@router.patch("/properties/{property_id}", response_model=PropertyResponse)
async def update_property_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    property_id: uuid.UUID,
    updates: PropertyUpdateDTO,
):
    """
    Admin: update property fields manually.
    Only provided (non-null) fields are updated.
    """
    prop = await update_property(db, property_id, updates)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    logger.info("Property updated", property_id=str(property_id))
    return PropertyResponse.model_validate(prop)


@router.get("/stats", response_model=StatsResponse)
async def stats_endpoint(db: Annotated[AsyncSession, Depends(get_db)]):
    """System-wide statistics."""
    data = await get_stats(db)
    return StatsResponse(**data)


@router.get("/stats/neighborhoods", response_model=NeighborhoodStatsResponse)
async def neighborhood_stats_endpoint(db: Annotated[AsyncSession, Depends(get_db)]):
    """Per-neighborhood property statistics."""
    neighborhoods = await get_neighborhood_stats(db)
    return NeighborhoodStatsResponse(
        neighborhoods=[NeighborhoodStat(**n) for n in neighborhoods],
        total_neighborhoods=len(neighborhoods),
    )
