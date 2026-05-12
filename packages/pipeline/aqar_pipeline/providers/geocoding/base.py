"""
Aqar.ai: Geocoding Provider Base
==================================
Abstract base class for geocoding providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GeocodingResult:
    """Result from a geocoding lookup."""

    latitude: float
    longitude: float
    address_formatted: str = ""
    neighborhood: str = ""
    city: str = "Tangier"
    region: str = "Tangier-Tetouan-Al Hoceima"
    country: str = "MA"
    confidence: float = 0.0
    provider: str = ""
    raw_response: dict | None = None


class GeocodingProvider(ABC):
    """Abstract base class for geocoding providers."""

    @abstractmethod
    def geocode(self, location_text: str, city_hint: str = "Tangier") -> GeocodingResult | None:
        """
        Geocode a location string to coordinates.

        Args:
            location_text: Raw location text (neighborhood name, address, etc.)
            city_hint: City context to improve accuracy.

        Returns:
            GeocodingResult if found, None otherwise.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging and metadata."""
        ...
