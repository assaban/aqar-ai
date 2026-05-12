"""
Aqar.ai: Local Gazetteer Geocoding Provider
=============================================
Fastest and most accurate geocoding for known Tangier-Tetouan neighborhoods.
Uses fuzzy string matching to handle Darija spelling variations.
"""

from __future__ import annotations

import difflib
import json
import logging
import os
from dataclasses import dataclass

from aqar_pipeline.providers.geocoding.base import GeocodingProvider, GeocodingResult

logger = logging.getLogger(__name__)

# Minimum similarity ratio for fuzzy matching (0.0 to 1.0)
# FUZZY_THRESHOLD = 0.65
FUZZY_THRESHOLD = 0.7

# Path to the gazetteer JSON
GAZETTEER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "tangier_gazetteer.json"
)


@dataclass
class GazetteerEntry:
    """A single neighborhood entry from the gazetteer."""

    id: str
    names: list[str]
    latitude: float
    longitude: float
    city: str
    entry_type: str


class GazetteerProvider(GeocodingProvider):
    """
    Local gazetteer for Tangier-Tetouan neighborhoods.

    Loaded once from JSON, supports fuzzy matching for Darija
    spelling variations. Fastest provider (no network calls).
    """

    def __init__(self, gazetteer_path: str | None = None):
        self._entries: list[GazetteerEntry] = []
        self._name_index: dict[str, GazetteerEntry] = {}
        self._load(gazetteer_path or GAZETTEER_PATH)

    @property
    def name(self) -> str:
        return "local_gazetteer"

    def _load(self, path: str) -> None:
        """Load the gazetteer from JSON file."""
        if not os.path.exists(path):
            logger.warning(f"Gazetteer file not found: {path}")
            return

        with open(path) as f:
            data = json.load(f)

        for entry_data in data.get("neighborhoods", []):
            entry = GazetteerEntry(
                id=entry_data["id"],
                names=entry_data["names"],
                latitude=entry_data["latitude"],
                longitude=entry_data["longitude"],
                city=entry_data.get("city", "Tangier"),
                entry_type=entry_data.get("type", "residential"),
            )
            self._entries.append(entry)

            # Build name index (lowercased, stripped)
            for name_variant in entry.names:
                normalized = name_variant.strip().lower()
                self._name_index[normalized] = entry

        logger.info(
            f"Gazetteer loaded: {len(self._entries)} neighborhoods, {len(self._name_index)} name variants"
        )

    def geocode(self, location_text: str, city_hint: str = "Tangier") -> GeocodingResult | None:
        """
        Look up a location in the local gazetteer.

        Tries exact match first, then fuzzy matching.
        """
        if not location_text or not self._entries:
            return None

        cleaned = location_text.strip().lower()

        # 1. Exact match
        if cleaned in self._name_index:
            entry = self._name_index[cleaned]
            return self._to_result(entry, confidence=1.0)

        # 2. Substring match (location text contains a neighborhood name)
        for name_key, entry in self._name_index.items():
            if name_key in cleaned or cleaned in name_key:
                return self._to_result(entry, confidence=0.9)

        # 3. Fuzzy match (Darija spelling variations)
        best_match = self._fuzzy_match(cleaned)
        if best_match:
            return best_match

        return None

    def _fuzzy_match(self, text: str) -> GeocodingResult | None:
        """Find the best fuzzy match in the gazetteer."""
        all_names = list(self._name_index.keys())
        matches = difflib.get_close_matches(text, all_names, n=1, cutoff=FUZZY_THRESHOLD)

        if matches:
            entry = self._name_index[matches[0]]
            # Calculate similarity ratio for confidence
            ratio = difflib.SequenceMatcher(None, text, matches[0]).ratio()
            return self._to_result(entry, confidence=round(ratio, 2))

        return None

    def _to_result(self, entry: GazetteerEntry, confidence: float) -> GeocodingResult:
        """Convert a gazetteer entry to a GeocodingResult."""
        return GeocodingResult(
            latitude=entry.latitude,
            longitude=entry.longitude,
            neighborhood=entry.names[0],  # Primary name
            city=entry.city,
            confidence=confidence,
            provider=self.name,
        )

    def search(self, query: str, limit: int = 5) -> list[GeocodingResult]:
        """Search the gazetteer for matching neighborhoods (for autocomplete)."""
        query_lower = query.strip().lower()
        results = []

        for name_key, entry in self._name_index.items():
            if query_lower in name_key:
                results.append(self._to_result(entry, confidence=0.9))
                if len(results) >= limit:
                    break

        return results
