"""
Aqar.ai: Nominatim Geocoding Provider
=======================================
Free geocoding via OpenStreetMap's Nominatim API.
Rate limited to 1 request per second.
"""

from __future__ import annotations

import logging
import os
import time

import httpx

from aqar_pipeline.providers.geocoding.base import GeocodingProvider, GeocodingResult

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "aqar-ai-dev")

# Rate limiting: track last request time
_last_request_time: float = 0.0


class NominatimProvider(GeocodingProvider):
    """
    Nominatim (OpenStreetMap) geocoding provider.

    Free, no API key required. Rate limited to 1 req/sec per Nominatim policy.
    """

    @property
    def name(self) -> str:
        return "nominatim"

    def geocode(self, location_text: str, city_hint: str = "Tangier") -> GeocodingResult | None:
        """Geocode using Nominatim with Morocco context."""
        global _last_request_time

        if not location_text:
            return None

        # Rate limiting (1 req/sec)
        elapsed = time.time() - _last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        # Build query with city context
        query = f"{location_text}, {city_hint}, Morocco"

        params = {
            "q": query,
            "format": "json",
            "limit": 1,
            "countrycodes": "ma",
            "addressdetails": 1,
        }

        headers = {"User-Agent": USER_AGENT}

        try:
            _last_request_time = time.time()

            with httpx.Client(timeout=15) as client:
                response = client.get(NOMINATIM_URL, params=params, headers=headers)
                response.raise_for_status()

            results = response.json()

            if not results:
                logger.debug(f"Nominatim: no results for '{query}'")
                return None

            top = results[0]
            address = top.get("address", {})

            return GeocodingResult(
                latitude=float(top["lat"]),
                longitude=float(top["lon"]),
                address_formatted=top.get("display_name", ""),
                neighborhood=address.get("suburb", address.get("neighbourhood", "")),
                city=address.get("city", address.get("town", city_hint)),
                region=address.get("state", "Tangier-Tetouan-Al Hoceima"),
                country=address.get("country_code", "ma").upper(),
                confidence=self._importance_to_confidence(float(top.get("importance", 0.0))),
                provider=self.name,
                raw_response=top,
            )

        except Exception as e:
            logger.error(f"Nominatim geocoding error for '{location_text}': {e}")
            return None

    @staticmethod
    def _importance_to_confidence(importance: float) -> float:
        """Convert Nominatim importance score (0-1) to our confidence scale."""
        return round(min(importance * 1.5, 1.0), 2)
