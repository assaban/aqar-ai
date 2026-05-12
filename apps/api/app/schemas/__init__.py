"""
Aqar.ai - API Schemas
====================
Pydantic models for request/response validation.
Separate from DB models to control what's exposed via API.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ═══════════════════════════════════════
# Property Schemas
# ═══════════════════════════════════════


class LocationResponse(BaseModel):
    """Location data in API responses."""

    latitude: float
    longitude: float
    address_formatted: str | None = None
    neighborhood: str | None = None
    city: str = "Tangier"
    region: str = "Tangier-Tetouan-Al Hoceima"

    model_config = {"from_attributes": True}


class PropertyBase(BaseModel):
    """Shared property fields."""

    property_type: str = "other"
    listing_type: str = "unknown"
    price: float | None = None
    price_currency: str = "MAD"
    area_sqm: float | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    legal_status: str = "unknown"
    title_generated: str | None = None
    description_generated: str | None = None


class PropertyResponse(PropertyBase):
    """Full property response with all fields."""

    id: uuid.UUID
    video_source_id: uuid.UUID
    floors: int | None = None
    has_garage: bool | None = None
    has_garden: bool | None = None
    has_elevator: bool | None = None
    floor_number: int | None = None
    extraction_confidence: float | None = None
    video_timestamp_start: float | None = None
    is_published: bool = False
    is_verified: bool = False
    location: LocationResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertyListResponse(BaseModel):
    """Paginated property list."""

    items: list[PropertyResponse]
    total: int
    page: int = 1
    per_page: int = 20
    has_next: bool = False


class PropertySearchQuery(BaseModel):
    """Search/filter parameters for properties."""

    q: str | None = Field(None, description="Free-text search query")
    property_type: str | None = None
    listing_type: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    area_min: float | None = None
    area_max: float | None = None
    rooms_min: int | None = None
    neighborhood: str | None = None
    city: str | None = None
    lat: float | None = Field(None, description="Center latitude for radius search")
    lng: float | None = Field(None, description="Center longitude for radius search")
    radius_km: float | None = Field(None, description="Search radius in kilometers")
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
    sort_by: str = "created_at"
    sort_order: str = "desc"


# ═══════════════════════════════════════
# Search Schemas
# ═══════════════════════════════════════


class SearchHit(BaseModel):
    """A single search result from Meilisearch."""

    id: str
    property_type: str = "other"
    listing_type: str = "unknown"
    title_generated: str = ""
    description_generated: str = ""
    price: float | None = None
    area_sqm: float | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    neighborhood: str = ""
    city: str = "Tangier"
    legal_status: str = "unknown"


class SearchResponse(BaseModel):
    """Full-text search response from Meilisearch."""

    hits: list[SearchHit]
    query: str
    total: int = 0
    processing_time_ms: int = 0
    page: int = 1
    per_page: int = 20


# ═══════════════════════════════════════
# Video Source Schemas
# ═══════════════════════════════════════


class VideoSourceResponse(BaseModel):
    """Video source in API responses."""

    id: uuid.UUID
    url: str
    platform: str
    title: str | None = None
    channel_name: str | None = None
    duration_seconds: int | None = None
    thumbnail_url: str | None = None
    published_at: datetime | None = None
    properties_count: int = 0

    model_config = {"from_attributes": True}


class VideoDetailResponse(VideoSourceResponse):
    """Video detail with transcript and properties."""

    transcript_text: str | None = None
    transcript_language: str | None = None
    transcript_confidence: float | None = None
    properties: list[PropertyResponse] = []
    processing_status: str | None = None
    processing_stage: str | None = None
    stage_timings: dict | None = None


class VideoListResponse(BaseModel):
    """Paginated video list."""

    items: list[VideoSourceResponse]
    total: int
    page: int = 1
    per_page: int = 20
    has_next: bool = False


# ═══════════════════════════════════════
# Pipeline Schemas
# ═══════════════════════════════════════


class PipelineSubmitRequest(BaseModel):
    """Request to submit a video URL for processing."""

    url: str = Field(..., description="YouTube video URL")


class PipelineStatusResponse(BaseModel):
    """Pipeline processing status."""

    job_id: uuid.UUID
    video_url: str
    status: str
    current_stage: str | None = None
    retry_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    stage_timings: dict | None = None

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════
# Health & Stats
# ═══════════════════════════════════════


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "0.1.0"
    environment: str = "development"
    services: dict[str, str] = {}


class NeighborhoodStat(BaseModel):
    """Statistics for a single neighborhood."""

    neighborhood: str
    property_count: int = 0
    avg_price: float | None = None
    min_price: float | None = None
    max_price: float | None = None


class StatsResponse(BaseModel):
    """System statistics."""

    total_videos: int = 0
    total_properties: int = 0
    total_published: int = 0
    processing_pending: int = 0
    processing_failed: int = 0
    processing_completed: int = 0
    avg_extraction_confidence: float | None = None
    avg_pipeline_time_seconds: float | None = None
    property_types: dict[str, int] = {}
    listing_types: dict[str, int] = {}


class NeighborhoodStatsResponse(BaseModel):
    """Per-neighborhood statistics."""

    neighborhoods: list[NeighborhoodStat]
    total_neighborhoods: int = 0
