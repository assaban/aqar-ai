"""
Aqar.ai: Google Maps Geocoding Provider
=========================================
High-accuracy geocoding via Google Maps Geocoding API.
Requires GOOGLE_MAPS_API_KEY. Used as last-resort fallback.
"""

from __future__ import annotations

import logging
import os

import httpx

from aqar_pipeline.providers.geocoding.base import GeocodingProvider, GeocodingResult

logger = logging.getLogger(__name__)

GOOGLE_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")


class GoogleMapsProvider(GeocodingProvider):
    """
    Google Maps geocoding provider.

    High accuracy but requires API key and costs per request.
    Only used when gazetteer and Nominatim both fail.
    """

    @property
    def name(self) -> str:
        return "google"

    def geocode(self, location_text: str, city_hint: str = "Tangier") -> GeocodingResult | None:
        """Geocode using Google Maps API with Morocco bias."""
        if not GOOGLE_API_KEY:
            logger.debug("Google Maps API key not configured, skipping")
            return None

        if not location_text:
            return None

        query = f"{location_text}, {city_hint}, Morocco"

        params = {
            "address": query,
            "key": GOOGLE_API_KEY,
            "region": "ma",
            "language": "fr",  # French for Moroccan addresses
        }

        try:
            with httpx.Client(timeout=15) as client:
                response = client.get(GOOGLE_GEOCODING_URL, params=params)
                response.raise_for_status()

            data = response.json()

            if data.get("status") != "OK" or not data.get("results"):
                logger.debug(f"Google Maps: no results for '{query}' (status={data.get('status')})")
                return None

            top = data["results"][0]
            geometry = top.get("geometry", {}).get("location", {})
            components = self._parse_address_components(top.get("address_components", []))

            # Map Google's location_type to confidence
            location_type = top.get("geometry", {}).get("location_type", "APPROXIMATE")
            confidence = {
                "ROOFTOP": 0.95,
                "RANGE_INTERPOLATED": 0.85,
                "GEOMETRIC_CENTER": 0.75,
                "APPROXIMATE": 0.6,
            }.get(location_type, 0.5)

            return GeocodingResult(
                latitude=geometry.get("lat", 0.0),
                longitude=geometry.get("lng", 0.0),
                address_formatted=top.get("formatted_address", ""),
                neighborhood=components.get("neighborhood", components.get("sublocality", "")),
                city=components.get("locality", city_hint),
                region=components.get("administrative_area_level_1", "Tangier-Tetouan-Al Hoceima"),
                country=components.get("country_code", "MA"),
                confidence=confidence,
                provider=self.name,
                raw_response=top,
            )

        except Exception as e:
            logger.error(f"Google Maps geocoding error for '{location_text}': {e}")
            return None

    @staticmethod
    def _parse_address_components(components: list[dict]) -> dict:
        """Parse Google's address_components into a flat dict."""
        result = {}
        for comp in components:
            types = comp.get("types", [])
            name = comp.get("long_name", "")
            short = comp.get("short_name", "")

            if "neighborhood" in types:
                result["neighborhood"] = name
            elif "sublocality" in types or "sublocality_level_1" in types:
                result["sublocality"] = name
            elif "locality" in types:
                result["locality"] = name
            elif "administrative_area_level_1" in types:
                result["administrative_area_level_1"] = name
            elif "country" in types:
                result["country_code"] = short

        return result
