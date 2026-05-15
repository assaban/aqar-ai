"""
Aqar.ai: Geocoding Stage
==========================
Celery task that geocodes extracted property locations and indexes
them in Meilisearch.

This is the final pipeline stage. After geocoding, the job is marked
as COMPLETED and properties are published and searchable.

Tasks:
  - geocode_properties: Geocodes all properties for a given video.
"""

from __future__ import annotations

import logging
import os

from celery import shared_task
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from models.base import Location, Property, VideoSource

logger = logging.getLogger(__name__)

DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://aqar:aqar_dev_password@db:5432/aqar_db",
)


def _get_sync_session() -> Session:
    engine = create_engine(DATABASE_URL_SYNC, pool_pre_ping=True)
    return Session(engine)


@shared_task(
    name="aqar_pipeline.stages.geocoding.geocode_properties",
    queue="geocoding",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def geocode_properties(self, video_source_id: str):
    """
    Geocode all properties extracted from a video.

    For each property:
      1. Read location_raw and neighborhood_hint from extras
      2. Geocode using tiered fallback (gazetteer -> Nominatim -> Google)
      3. Create Location record with PostGIS geometry
      4. Index property in Meilisearch

    After all properties are geocoded, marks the pipeline job as COMPLETED.

    Args:
        video_source_id: UUID string of the VideoSource record.
    """
    from aqar_pipeline.providers.geocoding import geocode_location
    from aqar_pipeline.utils.job_manager import JobManager
    from aqar_pipeline.utils.meilisearch_sync import (
        ensure_index,
        property_to_document,
    )

    logger.info(f"Starting geocoding for video: {video_source_id}")

    session = _get_sync_session()

    try:
        # Load video and properties
        video = session.execute(
            select(VideoSource).where(VideoSource.id == video_source_id)
        ).scalar_one_or_none()

        if not video:
            logger.error(f"VideoSource not found: {video_source_id}")
            return {"status": "error", "message": "Video not found"}

        properties = session.execute(
            select(Property).where(Property.video_source_id == video.id)
        ).scalars().all()

        if not properties:
            logger.warning(f"No properties found for video: {video_source_id}")
            manager = JobManager(session, video_source_id)
            if manager.start_stage("geocoding"):
                manager.complete_stage(metadata={"properties_geocoded": 0})
                manager.mark_completed()
            return {"status": "completed", "properties_geocoded": 0}

        # Initialize JobManager
        manager = JobManager(session, video_source_id)

        # Idempotency guard: skip if already completed (Celery re-delivery)
        if not manager.start_stage("geocoding"):
            return {
                "status": "skipped",
                "reason": "already_completed",
                "video_source_id": video_source_id,
            }

        # Ensure Meilisearch index exists
        ensure_index()

        geocoded_count = 0
        failed_count = 0
        meili_docs = []

        for prop in properties:
            # Extract location hints from extras
            extras = prop.extras or {}
            location_raw = extras.get("location_raw", "")
            neighborhood_hint = extras.get("neighborhood_hint", "")

            # Use neighborhood hint first, fall back to raw location
            search_text = neighborhood_hint or location_raw

            if not search_text:
                logger.debug(f"No location text for property {prop.id}, skipping geocoding")
                failed_count += 1
                continue

            # Geocode with tiered fallback
            city_hint = extras.get("city", "Tangier")
            result = geocode_location(search_text, city_hint)

            if result:
                # Create PostGIS geometry
                point = from_shape(Point(result.longitude, result.latitude), srid=4326)

                location = Location(
                    property_id=prop.id,
                    latitude=result.latitude,
                    longitude=result.longitude,
                    geom=point,
                    address_raw=location_raw,
                    address_formatted=result.address_formatted,
                    neighborhood=result.neighborhood or neighborhood_hint,
                    city=result.city,
                    region=result.region,
                    country=result.country,
                    geocoding_provider=result.provider,
                    geocoding_confidence=result.confidence,
                )
                session.add(location)
                geocoded_count += 1

                # Prepare Meilisearch document
                meili_docs.append(property_to_document(
                    property_id=str(prop.id),
                    property_type=prop.property_type.value if prop.property_type else "other",
                    listing_type=prop.listing_type.value if prop.listing_type else "unknown",
                    title=prop.title_generated,
                    description=prop.description_generated,
                    price=prop.price,
                    area_sqm=prop.area_sqm,
                    rooms=prop.rooms,
                    bedrooms=prop.bedrooms,
                    neighborhood=result.neighborhood or neighborhood_hint,
                    city=result.city,
                    legal_status=prop.legal_status.value if prop.legal_status else "unknown",
                    latitude=result.latitude,
                    longitude=result.longitude,
                    is_published=prop.is_published,
                    created_at=prop.created_at.isoformat() if prop.created_at else None,
                ))
            else:
                logger.warning(f"Geocoding failed for property {prop.id}: '{search_text}'")
                failed_count += 1

                # Still index in Meilisearch (without geo coordinates)
                meili_docs.append(property_to_document(
                    property_id=str(prop.id),
                    property_type=prop.property_type.value if prop.property_type else "other",
                    listing_type=prop.listing_type.value if prop.listing_type else "unknown",
                    title=prop.title_generated,
                    description=prop.description_generated,
                    price=prop.price,
                    area_sqm=prop.area_sqm,
                    rooms=prop.rooms,
                    bedrooms=prop.bedrooms,
                    neighborhood=neighborhood_hint,
                    city=city_hint,
                    legal_status=prop.legal_status.value if prop.legal_status else "unknown",
                    is_published=prop.is_published,
                    created_at=prop.created_at.isoformat() if prop.created_at else None,
                ))

        session.flush()

        # Batch index in Meilisearch
        if meili_docs:
            from aqar_pipeline.utils.meilisearch_sync import index_properties
            index_properties(meili_docs)

        # Complete the stage and mark pipeline as done
        manager.complete_stage(metadata={
            "properties_geocoded": geocoded_count,
            "properties_failed": failed_count,
            "properties_total": len(properties),
        })
        manager.mark_completed()

        session.commit()

        logger.info(
            f"Geocoding complete: {geocoded_count}/{len(properties)} geocoded, "
            f"{failed_count} failed, {len(meili_docs)} indexed"
        )

        return {
            "status": "completed",
            "video_source_id": video_source_id,
            "properties_geocoded": geocoded_count,
            "properties_failed": failed_count,
            "properties_indexed": len(meili_docs),
        }

    except self.MaxRetriesExceededError:
        logger.error(f"Max retries exceeded for geocoding: {video_source_id}")
        try:
            manager = JobManager(session, video_source_id)
            manager.fail(stage="geocoding", message="Max retries exceeded")
        except Exception:
            pass
        return {"status": "failed", "message": "Max retries exceeded"}

    except Exception as e:
        session.rollback()
        logger.error(f"Geocoding error for {video_source_id}: {e}")
        raise self.retry(exc=e) from e

    finally:
        session.close()
