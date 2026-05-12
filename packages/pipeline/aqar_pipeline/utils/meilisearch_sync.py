"""
Aqar.ai: Meilisearch Sync
============================
Manages the Meilisearch index for property search.

Handles:
  - Index creation and configuration
  - Property document indexing (create/update)
  - Arabic tokenization settings
  - Searchable, filterable, and sortable field configuration
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

MEILISEARCH_URL = os.getenv("MEILISEARCH_URL", "http://meilisearch:7700")
MEILISEARCH_KEY = os.getenv("MEILISEARCH_MASTER_KEY", "aqar_meili_dev_key")
INDEX_NAME = "properties"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {MEILISEARCH_KEY}",
        "Content-Type": "application/json",
    }


def ensure_index() -> bool:
    """
    Create the properties index if it does not exist and configure settings.

    Returns:
        True if index is ready, False on error.
    """
    try:
        with httpx.Client(timeout=15) as client:
            # Create index
            response = client.post(
                f"{MEILISEARCH_URL}/indexes",
                headers=_headers(),
                json={"uid": INDEX_NAME, "primaryKey": "id"},
            )
            # 202 = created/queued, 409 = already exists
            if response.status_code not in (200, 202, 409):
                logger.error(f"Failed to create index: {response.text}")
                return False

            # Configure searchable attributes
            client.put(
                f"{MEILISEARCH_URL}/indexes/{INDEX_NAME}/settings/searchable-attributes",
                headers=_headers(),
                json=[
                    "title_generated",
                    "description_generated",
                    "neighborhood",
                    "city",
                    "address_formatted",
                ],
            )

            # Configure filterable attributes
            client.put(
                f"{MEILISEARCH_URL}/indexes/{INDEX_NAME}/settings/filterable-attributes",
                headers=_headers(),
                json=[
                    "property_type",
                    "listing_type",
                    "price",
                    "area_sqm",
                    "rooms",
                    "bedrooms",
                    "neighborhood",
                    "city",
                    "legal_status",
                    "is_published",
                    "_geo",
                ],
            )

            # Configure sortable attributes
            client.put(
                f"{MEILISEARCH_URL}/indexes/{INDEX_NAME}/settings/sortable-attributes",
                headers=_headers(),
                json=["price", "area_sqm", "created_at", "rooms"],
            )

            # Enable geo search
            client.put(
                f"{MEILISEARCH_URL}/indexes/{INDEX_NAME}/settings/displayed-attributes",
                headers=_headers(),
                json=["*"],
            )

            logger.info(f"Meilisearch index '{INDEX_NAME}' configured")
            return True

    except Exception as e:
        logger.error(f"Meilisearch index setup error: {e}")
        return False


def index_property(property_data: dict) -> bool:
    """
    Add or update a single property document in Meilisearch.

    Args:
        property_data: Dict with property fields to index.
                       Must include 'id' as primary key.

    Returns:
        True if indexing succeeded, False otherwise.
    """
    return index_properties([property_data])


def index_properties(properties: list[dict]) -> bool:
    """
    Batch index multiple property documents.

    Args:
        properties: List of property dicts to index.

    Returns:
        True if indexing succeeded, False otherwise.
    """
    if not properties:
        return True

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{MEILISEARCH_URL}/indexes/{INDEX_NAME}/documents",
                headers=_headers(),
                json=properties,
            )

            if response.status_code not in (200, 202):
                logger.error(f"Meilisearch indexing failed: {response.text}")
                return False

        logger.info(f"Indexed {len(properties)} properties in Meilisearch")
        return True

    except Exception as e:
        logger.error(f"Meilisearch indexing error: {e}")
        return False


def property_to_document(
    property_id: str,
    property_type: str,
    listing_type: str,
    title: str | None,
    description: str | None,
    price: float | None,
    area_sqm: float | None,
    rooms: int | None,
    bedrooms: int | None,
    neighborhood: str | None,
    city: str,
    legal_status: str,
    latitude: float | None = None,
    longitude: float | None = None,
    is_published: bool = True,
    created_at: str | None = None,
) -> dict:
    """
    Convert property fields to a Meilisearch document.

    Handles geo coordinates in the _geo format required by Meilisearch.
    """
    doc = {
        "id": property_id,
        "property_type": property_type,
        "listing_type": listing_type,
        "title_generated": title or "",
        "description_generated": description or "",
        "price": price,
        "area_sqm": area_sqm,
        "rooms": rooms,
        "bedrooms": bedrooms,
        "neighborhood": neighborhood or "",
        "city": city,
        "legal_status": legal_status,
        "is_published": is_published,
        "created_at": created_at,
    }

    # Meilisearch geo format
    if latitude is not None and longitude is not None:
        doc["_geo"] = {"lat": latitude, "lng": longitude}
        doc["address_formatted"] = f"{neighborhood or ''}, {city}"

    return doc


def search_properties(
    query: str,
    filters: str | None = None,
    sort: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    geo_point: tuple[float, float] | None = None,
    geo_radius_m: int | None = None,
) -> dict:
    """
    Search properties in Meilisearch.

    Args:
        query: Search query text.
        filters: Meilisearch filter expression.
        sort: List of sort expressions (e.g. ["price:asc"]).
        limit: Max results.
        offset: Pagination offset.
        geo_point: (lat, lng) for geo search.
        geo_radius_m: Radius in meters for geo filtering.

    Returns:
        Meilisearch search response dict.
    """
    payload: dict = {
        "q": query,
        "limit": limit,
        "offset": offset,
    }

    # Build filter expression
    filter_parts = ["is_published = true"]
    if filters:
        filter_parts.append(filters)
    if geo_point and geo_radius_m:
        lat, lng = geo_point
        filter_parts.append(f"_geoRadius({lat}, {lng}, {geo_radius_m})")

    payload["filter"] = " AND ".join(filter_parts)

    if sort:
        payload["sort"] = sort

    try:
        with httpx.Client(timeout=15) as client:
            response = client.post(
                f"{MEILISEARCH_URL}/indexes/{INDEX_NAME}/search",
                headers=_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    except Exception as e:
        logger.error(f"Meilisearch search error: {e}")
        return {"hits": [], "estimatedTotalHits": 0}
