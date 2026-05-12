"""
Unit tests for Meilisearch sync utility.

Tests cover: document creation, field mapping, and geo formatting.
Does NOT test actual Meilisearch API calls (those need integration tests).
"""

from aqar_pipeline.utils.meilisearch_sync import property_to_document


class TestPropertyToDocument:
    """Tests for property_to_document()."""

    def test_basic_document(self):
        doc = property_to_document(
            property_id="abc-123",
            property_type="apartment",
            listing_type="sale",
            title="Bel appartement",
            description="Au centre ville",
            price=750000,
            area_sqm=85,
            rooms=4,
            bedrooms=2,
            neighborhood="Iberia",
            city="Tangier",
            legal_status="tabou",
        )
        assert doc["id"] == "abc-123"
        assert doc["property_type"] == "apartment"
        assert doc["price"] == 750000
        assert doc["neighborhood"] == "Iberia"
        assert doc["is_published"] is True

    def test_with_geo_coordinates(self):
        doc = property_to_document(
            property_id="abc-123",
            property_type="villa",
            listing_type="sale",
            title="Villa",
            description="Belle villa",
            price=2000000,
            area_sqm=200,
            rooms=6,
            bedrooms=4,
            neighborhood="Marshan",
            city="Tangier",
            legal_status="melkia",
            latitude=35.787,
            longitude=-5.818,
        )
        assert "_geo" in doc
        assert doc["_geo"]["lat"] == 35.787
        assert doc["_geo"]["lng"] == -5.818

    def test_without_geo_coordinates(self):
        doc = property_to_document(
            property_id="abc-123",
            property_type="land",
            listing_type="sale",
            title="Terrain",
            description="Terrain a vendre",
            price=500000,
            area_sqm=300,
            rooms=None,
            bedrooms=None,
            neighborhood="Boukhalef",
            city="Tangier",
            legal_status="unknown",
        )
        assert "_geo" not in doc

    def test_null_price_and_area(self):
        doc = property_to_document(
            property_id="abc-123",
            property_type="other",
            listing_type="unknown",
            title=None,
            description=None,
            price=None,
            area_sqm=None,
            rooms=None,
            bedrooms=None,
            neighborhood=None,
            city="Tangier",
            legal_status="unknown",
        )
        assert doc["price"] is None
        assert doc["area_sqm"] is None
        assert doc["title_generated"] == ""
        assert doc["neighborhood"] == ""

    def test_unpublished_property(self):
        doc = property_to_document(
            property_id="abc-123",
            property_type="apartment",
            listing_type="rent",
            title="Appartement a louer",
            description="Description",
            price=3000,
            area_sqm=60,
            rooms=3,
            bedrooms=1,
            neighborhood="Centre Ville",
            city="Tangier",
            legal_status="tabou",
            is_published=False,
        )
        assert doc["is_published"] is False
