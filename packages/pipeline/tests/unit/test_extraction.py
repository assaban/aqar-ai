"""
Unit tests for the extraction stage.

Tests cover: property creation from LLM data, enum mapping,
confidence flagging, and safe enum conversion.
"""

from aqar_pipeline.stages.extraction import _create_property_from_data, _safe_enum
from models.base import LegalStatus, ListingType, PropertyType


# ═══════════════════════════════════════
# Safe Enum Conversion
# ═══════════════════════════════════════


class TestSafeEnum:
    """Tests for _safe_enum() helper."""

    def test_valid_enum_value(self):
        result = _safe_enum(PropertyType, "apartment", PropertyType.OTHER)
        assert result == PropertyType.APARTMENT

    def test_none_returns_default(self):
        result = _safe_enum(PropertyType, None, PropertyType.OTHER)
        assert result == PropertyType.OTHER

    def test_invalid_value_returns_default(self):
        result = _safe_enum(PropertyType, "spaceship", PropertyType.OTHER)
        assert result == PropertyType.OTHER

    def test_empty_string_returns_default(self):
        result = _safe_enum(PropertyType, "", PropertyType.OTHER)
        assert result == PropertyType.OTHER

    def test_listing_type_sale(self):
        result = _safe_enum(ListingType, "sale", ListingType.UNKNOWN)
        assert result == ListingType.SALE

    def test_legal_status_tabou(self):
        result = _safe_enum(LegalStatus, "tabou", LegalStatus.UNKNOWN)
        assert result == LegalStatus.TABOU

    def test_case_insensitive(self):
        """Enum values are lowercased before matching."""
        result = _safe_enum(PropertyType, "VILLA", PropertyType.OTHER)
        assert result == PropertyType.VILLA


# ═══════════════════════════════════════
# Property Creation from LLM Data
# ═══════════════════════════════════════


class TestCreatePropertyFromData:
    """Tests for _create_property_from_data()."""

    def _sample_data(self, **overrides) -> dict:
        base = {
            "property_type": "apartment",
            "listing_type": "sale",
            "price": 750000,
            "price_currency": "MAD",
            "price_raw": "750 mille",
            "area_sqm": 85,
            "rooms": 4,
            "bedrooms": 2,
            "bathrooms": 1,
            "legal_status": "tabou",
            "title_generated": "Appartement 85m2 a Iberia",
            "description_generated": "Bel appartement au centre de Tangier",
            "confidence_scores": {"price": 0.95, "area": 0.9, "overall": 0.85},
        }
        base.update(overrides)
        return base

    def test_creates_property_with_correct_fields(self):
        data = self._sample_data()
        prop = _create_property_from_data(
            video_source_id="test-uuid",
            data=data,
            prompt_version="v1",
            provider_name="ollama",
            model_name="gemma3",
        )
        assert prop.property_type == PropertyType.APARTMENT
        assert prop.listing_type == ListingType.SALE
        assert prop.price == 750000
        assert prop.area_sqm == 85
        assert prop.bedrooms == 2
        assert prop.legal_status == LegalStatus.TABOU
        assert prop.prompt_version == "v1"

    def test_high_confidence_auto_published(self):
        data = self._sample_data(confidence_scores={"overall": 0.9})
        prop = _create_property_from_data(
            video_source_id="test-uuid",
            data=data,
            prompt_version="v1",
            provider_name="ollama",
            model_name="gemma3",
        )
        assert prop.is_published is True
        assert prop.needs_review is False

    def test_low_confidence_flagged_for_review(self):
        data = self._sample_data(confidence_scores={"overall": 0.4})
        prop = _create_property_from_data(
            video_source_id="test-uuid",
            data=data,
            prompt_version="v1",
            provider_name="ollama",
            model_name="gemma3",
        )
        assert prop.needs_review is True
        assert prop.is_published is False

    def test_missing_confidence_defaults_to_review(self):
        data = self._sample_data(confidence_scores={})
        prop = _create_property_from_data(
            video_source_id="test-uuid",
            data=data,
            prompt_version="v1",
            provider_name="ollama",
            model_name="gemma3",
        )
        assert prop.needs_review is True

    def test_extras_captures_provider_info(self):
        data = self._sample_data(
            location_raw="Iberia, Tangier",
            neighborhood="Iberia",
        )
        prop = _create_property_from_data(
            video_source_id="test-uuid",
            data=data,
            prompt_version="v1",
            provider_name="openai",
            model_name="gpt-4o",
        )
        assert prop.extras["provider"] == "openai"
        assert prop.extras["model"] == "gpt-4o"
        assert prop.extras["location_raw"] == "Iberia, Tangier"
        assert prop.extras["neighborhood_hint"] == "Iberia"

    def test_unknown_property_type_defaults(self):
        data = self._sample_data(property_type="spaceship")
        prop = _create_property_from_data(
            video_source_id="test-uuid",
            data=data,
            prompt_version="v1",
            provider_name="ollama",
            model_name="gemma3",
        )
        assert prop.property_type == PropertyType.OTHER

    def test_null_optional_fields(self):
        data = self._sample_data(
            price=None,
            area_sqm=None,
            rooms=None,
            bedrooms=None,
            bathrooms=None,
        )
        prop = _create_property_from_data(
            video_source_id="test-uuid",
            data=data,
            prompt_version="v1",
            provider_name="ollama",
            model_name="gemma3",
        )
        assert prop.price is None
        assert prop.area_sqm is None
        assert prop.rooms is None
