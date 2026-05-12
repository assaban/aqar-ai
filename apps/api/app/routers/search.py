"""
Aqar.ai - Search Routes
========================
Full-text search via Meilisearch with Arabic support and geo filtering.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.database import get_db
from apps.api.app.schemas import SearchHit, SearchResponse

logger = structlog.get_logger()
router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search_properties(
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str = Query("", description="Search query (Arabic or French)"),
    property_type: str | None = None,
    listing_type: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    rooms_min: int | None = None,
    neighborhood: str | None = None,
    lat: float | None = Query(None, description="Latitude for geo search"),
    lng: float | None = Query(None, description="Longitude for geo search"),
    radius_km: float | None = Query(None, description="Search radius in km"),
    sort: str | None = Query(None, description="Sort field: price:asc, price:desc, area_sqm:desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """
    Full-text search for properties via Meilisearch.

    Supports:
      - Arabic and French text search
      - Filter by property type, listing type, price range, rooms
      - Geo search: find properties within radius of a point
      - Sorting by price or area
    """
    from aqar_pipeline.utils.meilisearch_sync import search_properties as meili_search

    # Build Meilisearch filter expression
    filter_parts = []
    if property_type:
        filter_parts.append(f'property_type = "{property_type}"')
    if listing_type:
        filter_parts.append(f'listing_type = "{listing_type}"')
    if price_min is not None:
        filter_parts.append(f"price >= {price_min}")
    if price_max is not None:
        filter_parts.append(f"price <= {price_max}")
    if rooms_min is not None:
        filter_parts.append(f"rooms >= {rooms_min}")
    if neighborhood:
        filter_parts.append(f'neighborhood = "{neighborhood}"')

    filter_str = " AND ".join(filter_parts) if filter_parts else None

    # Geo search
    geo_point = (lat, lng) if lat is not None and lng is not None else None
    geo_radius_m = int(radius_km * 1000) if radius_km else None

    # Sort
    sort_list = [sort] if sort else None

    # Pagination offset
    offset = (page - 1) * per_page

    # Execute search
    result = meili_search(
        query=q,
        filters=filter_str,
        sort=sort_list,
        limit=per_page,
        offset=offset,
        geo_point=geo_point,
        geo_radius_m=geo_radius_m,
    )

    # Map Meilisearch hits to response schema
    hits = []
    for hit in result.get("hits", []):
        hits.append(
            SearchHit(
                id=hit.get("id", ""),
                property_type=hit.get("property_type", "other"),
                listing_type=hit.get("listing_type", "unknown"),
                title_generated=hit.get("title_generated", ""),
                description_generated=hit.get("description_generated", ""),
                price=hit.get("price"),
                area_sqm=hit.get("area_sqm"),
                rooms=hit.get("rooms"),
                bedrooms=hit.get("bedrooms"),
                neighborhood=hit.get("neighborhood", ""),
                city=hit.get("city", "Tangier"),
                legal_status=hit.get("legal_status", "unknown"),
            )
        )

    return SearchResponse(
        hits=hits,
        query=q,
        total=result.get("estimatedTotalHits", len(hits)),
        processing_time_ms=result.get("processingTimeMs", 0),
        page=page,
        per_page=per_page,
    )
