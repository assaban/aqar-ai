"""
Aqar.ai - Database Models
========================
Core entities: VideoSource, Transcript, Property, Location, ProcessingJob
Uses SQLAlchemy 2.0+ with async support and PostGIS for geospatial data.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    type_annotation_map = {
        uuid.UUID: UUID(as_uuid=True),
        dict: JSONB,
    }


# ═══════════════════════════════════════
# Enums
# ═══════════════════════════════════════


class Platform(str, enum.Enum):
    """Supported video platforms."""

    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"


class ProcessingStatus(str, enum.Enum):
    """Pipeline processing status."""

    PENDING = "pending"
    INGESTING = "ingesting"
    TRANSCRIBING = "transcribing"
    EXTRACTING = "extracting"
    GEOCODING = "geocoding"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PropertyType(str, enum.Enum):
    """Real estate property types."""

    APARTMENT = "apartment"
    HOUSE = "house"
    VILLA = "villa"
    LAND = "land"
    COMMERCIAL = "commercial"
    GARAGE = "garage"
    OTHER = "other"


class ListingType(str, enum.Enum):
    """Sale or rent."""

    SALE = "sale"
    RENT = "rent"
    UNKNOWN = "unknown"


class LegalStatus(str, enum.Enum):
    """Moroccan property legal status types."""

    MELKIA = "melkia"  # Traditional ownership
    TABOU = "tabou"  # Registered title (titre foncier)
    RASM = "rasm"  # Tax registration
    UNKNOWN = "unknown"


# ═══════════════════════════════════════
# Models
# ═══════════════════════════════════════


class VideoSource(Base):
    """
    A video discovered from a social media platform.
    One video may contain tours of multiple properties.
    """

    __tablename__ = "video_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)
    external_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Platform-specific video ID"
    )
    channel_id: Mapped[str | None] = mapped_column(String(255))
    channel_name: Mapped[str | None] = mapped_column(String(500))
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    thumbnail_url: Mapped[str | None] = mapped_column(String(2048))
    view_count: Mapped[int | None] = mapped_column(Integer)

    # Metadata
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    transcript: Mapped[Transcript | None] = relationship(
        back_populates="video_source", cascade="all, delete-orphan"
    )
    properties: Mapped[list[Property]] = relationship(
        back_populates="video_source", cascade="all, delete-orphan"
    )
    processing_job: Mapped[ProcessingJob | None] = relationship(
        back_populates="video_source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_video_sources_platform", "platform"),
        Index("ix_video_sources_external_id", "external_id"),
        Index("ix_video_sources_channel_id", "channel_id"),
        Index("ix_video_sources_published_at", "published_at"),
    )

    def __repr__(self) -> str:
        return f"<VideoSource(id={self.id}, platform={self.platform}, title={self.title[:50] if self.title else 'N/A'})>"


class Transcript(Base):
    """
    Transcription of a video's audio content.
    Stores both full text and timestamped segments.
    """

    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    video_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("video_sources.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="Detected language code (ar, fr, etc.)"
    )
    confidence: Mapped[float | None] = mapped_column(
        Float, comment="Overall transcription confidence 0-1"
    )
    segments: Mapped[dict | None] = mapped_column(
        JSONB,
        comment="Timestamped segments: [{start, end, text, confidence}]",
    )
    whisper_model: Mapped[str | None] = mapped_column(
        String(50), comment="Whisper model version used"
    )
    processing_time_seconds: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    video_source: Mapped[VideoSource] = relationship(back_populates="transcript")

    __table_args__ = (Index("ix_transcripts_language", "language"),)

    def __repr__(self) -> str:
        return f"<Transcript(id={self.id}, lang={self.language}, confidence={self.confidence})>"


class Property(Base):
    """
    A real estate property extracted from a video.
    Core entity of the system — what users search for.
    """

    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    video_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("video_sources.id", ondelete="CASCADE"), nullable=False
    )

    # ── Core Fields ──
    property_type: Mapped[PropertyType] = mapped_column(
        Enum(PropertyType), default=PropertyType.OTHER
    )
    listing_type: Mapped[ListingType] = mapped_column(
        Enum(ListingType), default=ListingType.UNKNOWN
    )
    price: Mapped[float | None] = mapped_column(Float, comment="Price in MAD")
    price_currency: Mapped[str] = mapped_column(String(3), default="MAD")
    price_raw: Mapped[str | None] = mapped_column(
        String(255), comment="Original price text from video"
    )

    # ── Property Details ──
    area_sqm: Mapped[float | None] = mapped_column(Float, comment="Area in square meters")
    rooms: Mapped[int | None] = mapped_column(Integer)
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[int | None] = mapped_column(Integer)
    floors: Mapped[int | None] = mapped_column(Integer)
    has_garage: Mapped[bool | None] = mapped_column(Boolean)
    has_garden: Mapped[bool | None] = mapped_column(Boolean)
    has_elevator: Mapped[bool | None] = mapped_column(Boolean)
    floor_number: Mapped[int | None] = mapped_column(
        Integer, comment="Which floor (for apartments)"
    )

    # ── Legal ──
    legal_status: Mapped[LegalStatus] = mapped_column(
        Enum(LegalStatus), default=LegalStatus.UNKNOWN
    )

    # ── Description ──
    title_generated: Mapped[str | None] = mapped_column(
        String(500), comment="LLM-generated title"
    )
    description_generated: Mapped[str | None] = mapped_column(
        Text, comment="LLM-generated description"
    )

    # ── Extraction Metadata ──
    extraction_confidence: Mapped[float | None] = mapped_column(
        Float, comment="Overall extraction confidence 0-1"
    )
    field_confidences: Mapped[dict | None] = mapped_column(
        JSONB, comment="Per-field confidence: {price: 0.95, area: 0.8, ...}"
    )
    video_timestamp_start: Mapped[float | None] = mapped_column(
        Float, comment="Where in the video this property tour starts (seconds)"
    )
    video_timestamp_end: Mapped[float | None] = mapped_column(Float)
    prompt_version: Mapped[str | None] = mapped_column(
        String(50), comment="Which prompt version extracted this data"
    )
    extras: Mapped[dict | None] = mapped_column(
        JSONB, comment="Flexible field for additional extracted data"
    )

    # ── Flags ──
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_review: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Flagged for human review (low confidence)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    video_source: Mapped[VideoSource] = relationship(back_populates="properties")
    location: Mapped[Location | None] = relationship(
        back_populates="property", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_properties_type", "property_type"),
        Index("ix_properties_listing_type", "listing_type"),
        Index("ix_properties_price", "price"),
        Index("ix_properties_area", "area_sqm"),
        Index("ix_properties_published", "is_published"),
        Index("ix_properties_needs_review", "needs_review"),
        Index("ix_properties_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Property(id={self.id}, type={self.property_type}, price={self.price} {self.price_currency})>"


class Location(Base):
    """
    Geocoded location for a property.
    Uses PostGIS geometry for spatial queries (nearby, within radius, etc.)
    """

    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # ── Coordinates ──
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    geom = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=False),  # Added spatial_index=False
        comment="PostGIS point geometry for spatial queries",
    )

    # ── Address Components ──
    address_raw: Mapped[str | None] = mapped_column(
        Text, comment="Original location text from video"
    )
    address_formatted: Mapped[str | None] = mapped_column(Text)
    neighborhood: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(255), default="Tangier")
    region: Mapped[str] = mapped_column(String(255), default="Tangier-Tetouan-Al Hoceima")
    country: Mapped[str] = mapped_column(String(2), default="MA")

    # ── Geocoding Metadata ──
    geocoding_provider: Mapped[str | None] = mapped_column(
        String(50), comment="nominatim | google | local_gazetteer"
    )
    geocoding_confidence: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    property: Mapped[Property] = relationship(back_populates="location")

    __table_args__ = (
        Index("ix_locations_city", "city"),
        Index("ix_locations_neighborhood", "neighborhood"),
        Index("idx_locations_geom", "geom", postgresql_using="gist"),  # Stick to 'idx_' prefix
    )

    def __repr__(self) -> str:
        return f"<Location(id={self.id}, neighborhood={self.neighborhood}, city={self.city})>"


class ProcessingJob(Base):
    """
    Tracks the pipeline processing status for each video.
    Enables retries, monitoring, and debugging.
    """

    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    video_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("video_sources.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus), default=ProcessingStatus.PENDING
    )
    current_stage: Mapped[str | None] = mapped_column(
        String(50), comment="Current pipeline stage name"
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # ── Timing ──
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ── Error Tracking ──
    error_message: Mapped[str | None] = mapped_column(Text)
    error_stage: Mapped[str | None] = mapped_column(String(50))
    error_traceback: Mapped[str | None] = mapped_column(Text)

    # ── Stage Metadata ──
    stage_timings: Mapped[dict | None] = mapped_column(
        JSONB,
        comment="Timing per stage: {ingestion: 12.3, transcription: 45.6, ...}",
    )
    stage_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        comment="Per-stage metadata: {transcription: {wer: 0.15}, extraction: {tokens_used: 1200}}",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    video_source: Mapped[VideoSource] = relationship(back_populates="processing_job")

    __table_args__ = (
        Index("ix_processing_jobs_status", "status"),
        Index("ix_processing_jobs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ProcessingJob(id={self.id}, status={self.status}, stage={self.current_stage})>"
