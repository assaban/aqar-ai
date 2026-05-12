"""
Aqar.ai: LLM Extraction Stage
================================
Celery task that extracts structured property data from transcriptions
using LLMs via the Strategy Pattern (Ollama/OpenAI/Anthropic).

Tasks:
  - extract_properties: Extracts properties from a transcript using an LLM.
"""

from __future__ import annotations

import logging
import os

from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from models.base import (
    LegalStatus,
    ListingType,
    Property,
    PropertyType,
    Transcript,
    VideoSource,
)

logger = logging.getLogger(__name__)

DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://aqar:aqar_dev_password@db:5432/aqar_db",
)

# Default prompt version
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1")

# Confidence threshold for flagging manual review
CONFIDENCE_THRESHOLD = float(os.getenv("EXTRACTION_CONFIDENCE_THRESHOLD", "0.6"))


def _get_sync_session() -> Session:
    engine = create_engine(DATABASE_URL_SYNC, pool_pre_ping=True)
    return Session(engine)


def _safe_enum(enum_cls, value: str | None, default):
    """Safely convert a string to an enum, returning default on failure."""
    if not value:
        return default
    try:
        return enum_cls(value.lower())
    except (ValueError, KeyError):
        return default


def _create_property_from_data(
    video_source_id: str,
    data: dict,
    prompt_version: str,
    provider_name: str,
    model_name: str,
) -> Property:
    """
    Create a Property ORM instance from extracted data dict.

    Maps LLM output fields to the Property model, handling type
    conversion and enum validation.
    """
    # Extract confidence scores
    confidence_scores = data.get("confidence_scores", {})
    overall_confidence = confidence_scores.get("overall", 0.0)

    # Flag for review if low confidence
    needs_review = overall_confidence < CONFIDENCE_THRESHOLD

    return Property(
        video_source_id=video_source_id,
        property_type=_safe_enum(PropertyType, data.get("property_type"), PropertyType.OTHER),
        listing_type=_safe_enum(ListingType, data.get("listing_type"), ListingType.UNKNOWN),
        price=data.get("price"),
        price_currency=data.get("price_currency", "MAD"),
        price_raw=data.get("price_raw"),
        area_sqm=data.get("area_sqm"),
        rooms=data.get("rooms"),
        bedrooms=data.get("bedrooms"),
        bathrooms=data.get("bathrooms"),
        floors=data.get("floors"),
        floor_number=data.get("floor_number"),
        has_garage=data.get("has_garage"),
        has_garden=data.get("has_garden"),
        has_elevator=data.get("has_elevator"),
        legal_status=_safe_enum(LegalStatus, data.get("legal_status"), LegalStatus.UNKNOWN),
        title_generated=data.get("title_generated"),
        description_generated=data.get("description_generated"),
        extraction_confidence=overall_confidence,
        field_confidences=confidence_scores,
        prompt_version=prompt_version,
        needs_review=needs_review,
        is_published=not needs_review,  # Auto-publish high-confidence extractions
        extras={
            "provider": provider_name,
            "model": model_name,
            "location_raw": data.get("location_raw"),
            "neighborhood_hint": data.get("neighborhood"),
            "video_timestamp_hint": data.get("video_timestamp_hint"),
            "agent_name": data.get("agent_name"),
            "agent_phone": data.get("agent_phone"),
        },
    )


@shared_task(
    name="aqar_pipeline.stages.extraction.extract_properties",
    queue="extraction",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def extract_properties(
    self,
    video_source_id: str,
    provider_name: str | None = None,
    model: str | None = None,
    prompt_version: str | None = None,
):
    """
    Extract structured property data from a transcript using an LLM.

    Uses the Strategy Pattern to select the LLM provider at runtime.
    Supports Ollama (Gemma), OpenAI (GPT-4o), and Anthropic (Claude).

    Args:
        video_source_id: UUID string of the VideoSource record.
        provider_name: Override the default LLM provider.
        model: Override the default model for the provider.
        prompt_version: Override the default prompt version.

    Returns:
        Dict with extraction results and metadata.
    """
    from aqar_pipeline.providers import get_provider
    from aqar_pipeline.utils.job_manager import JobManager
    from aqar_pipeline.utils.prompt_loader import render_prompt

    version = prompt_version or PROMPT_VERSION

    logger.info(
        f"Starting property extraction for video: {video_source_id} "
        f"(provider={provider_name or 'default'}, prompt={version})"
    )

    session = _get_sync_session()

    try:
        # Load transcript
        video = session.execute(
            select(VideoSource).where(VideoSource.id == video_source_id)
        ).scalar_one_or_none()

        if not video:
            logger.error(f"VideoSource not found: {video_source_id}")
            return {"status": "error", "message": "Video not found"}

        transcript = session.execute(
            select(Transcript).where(Transcript.video_source_id == video.id)
        ).scalar_one_or_none()

        if not transcript:
            logger.error(f"Transcript not found for video: {video_source_id}")
            return {"status": "error", "message": "Transcript not found"}

        # Initialize JobManager
        manager = JobManager(session, video_source_id)
        manager.start_stage("extraction")

        # Get LLM provider (Strategy Pattern)
        provider = get_provider(provider_name, model)
        logger.info(f"Using provider: {provider.name} ({provider.model})")

        # Render prompt
        system_prompt, user_prompt = render_prompt(transcript.full_text, version)

        # Call LLM
        result = provider.extract(system_prompt, user_prompt)

        if not result.success:
            manager.fail(
                stage="extraction",
                message=f"LLM extraction failed: {result.error_message}",
            )
            raise self.retry(
                exc=RuntimeError(f"LLM extraction failed: {result.error_message}"),
            )

        # Create Property records from extracted data
        properties_created = 0
        for prop_data in result.properties:
            prop = _create_property_from_data(
                video_source_id=video.id,
                data=prop_data,
                prompt_version=version,
                provider_name=provider.name,
                model_name=provider.model,
            )
            session.add(prop)
            properties_created += 1

        session.flush()

        # Complete the stage
        manager.complete_stage(
            metadata={
                "provider": provider.name,
                "model": provider.model,
                "prompt_version": version,
                "properties_extracted": properties_created,
                "tokens_used": result.tokens_used,
                "processing_time_seconds": result.processing_time_seconds,
            }
        )

        logger.info(
            f"Extraction complete: {properties_created} properties from {provider.name} "
            f"({result.tokens_used} tokens, {result.processing_time_seconds}s)"
        )

        # TODO [Sprint 5]: Chain to geocoding
        # from aqar_pipeline.stages.geocoding import geocode_properties
        # geocode_properties.delay(video_source_id)

        return {
            "status": "completed",
            "video_source_id": video_source_id,
            "properties_extracted": properties_created,
            "provider": provider.name,
            "model": provider.model,
            "prompt_version": version,
            "tokens_used": result.tokens_used,
            "processing_time_seconds": result.processing_time_seconds,
        }

    except self.MaxRetriesExceededError:
        logger.error(f"Max retries exceeded for extraction: {video_source_id}")
        try:
            manager = JobManager(session, video_source_id)
            manager.fail(
                stage="extraction",
                message="Max retries exceeded for LLM extraction",
            )
        except Exception:
            pass
        return {"status": "failed", "message": "Max retries exceeded"}

    except Exception as e:
        session.rollback()
        logger.error(f"Extraction error for {video_source_id}: {e}")
        raise self.retry(exc=e) from e

    finally:
        session.close()
