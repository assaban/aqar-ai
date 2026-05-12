"""
Aqar.ai: Geocoding Provider Registry
======================================
Tiered fallback geocoding: Gazetteer -> Nominatim -> Google Maps.
"""

from __future__ import annotations

import logging

from aqar_pipeline.providers.geocoding.base import GeocodingResult
from aqar_pipeline.providers.geocoding.gazetteer import GazetteerProvider
from aqar_pipeline.providers.geocoding.google_maps import GoogleMapsProvider
from aqar_pipeline.providers.geocoding.nominatim import NominatimProvider

logger = logging.getLogger(__name__)

# Singleton instances
_gazetteer: GazetteerProvider | None = None


def _get_gazetteer() -> GazetteerProvider:
    """Get or create the gazetteer provider (singleton)."""
    global _gazetteer
    if _gazetteer is None:
        _gazetteer = GazetteerProvider()
    return _gazetteer


def geocode_location(
    location_text: str,
    city_hint: str = "Tangier",
) -> GeocodingResult | None:
    """
    Geocode a location string using tiered fallback.

    Order:
      1. Local Gazetteer (instant, best for Tangier neighborhoods)
      2. Nominatim/OSM (free, 1 req/sec rate limit)
      3. Google Maps (paid, high accuracy)

    Args:
        location_text: Raw location text from LLM extraction.
        city_hint: City context for external providers.

    Returns:
        GeocodingResult if any provider succeeds, None otherwise.
    """
    if not location_text or not location_text.strip():
        return None

    text = location_text.strip()

    # Tier 1: Local Gazetteer
    gazetteer = _get_gazetteer()
    result = gazetteer.geocode(text, city_hint)
    if result:
        logger.info(f"Geocoded via gazetteer: '{text}' -> ({result.latitude}, {result.longitude})")
        return result

    # Tier 2: Nominatim
    nominatim = NominatimProvider()
    result = nominatim.geocode(text, city_hint)
    if result:
        logger.info(f"Geocoded via Nominatim: '{text}' -> ({result.latitude}, {result.longitude})")
        return result

    # Tier 3: Google Maps
    google = GoogleMapsProvider()
    result = google.geocode(text, city_hint)
    if result:
        logger.info(f"Geocoded via Google: '{text}' -> ({result.latitude}, {result.longitude})")
        return result

    logger.warning(f"All geocoding providers failed for: '{text}'")
    return None
