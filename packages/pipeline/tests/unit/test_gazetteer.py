"""
Unit tests for the Tangier neighborhood gazetteer.

Tests cover: loading, exact matching, fuzzy matching,
substring matching, and Darija spelling variants.
"""

from aqar_pipeline.providers.geocoding.gazetteer import GazetteerProvider


class TestGazetteerLoading:
    """Tests for gazetteer data loading."""

    def test_loads_default_gazetteer(self):
        gaz = GazetteerProvider()
        assert len(gaz._entries) > 0

    def test_has_at_least_50_neighborhoods(self):
        gaz = GazetteerProvider()
        assert len(gaz._entries) >= 50

    def test_name_index_populated(self):
        gaz = GazetteerProvider()
        assert len(gaz._name_index) > len(gaz._entries)  # Multiple names per entry


class TestGazetteerExactMatch:
    """Tests for exact name matching."""

    def test_french_name(self):
        gaz = GazetteerProvider()
        result = gaz.geocode("Iberia")
        assert result is not None
        assert result.confidence == 1.0
        assert result.provider == "local_gazetteer"

    def test_arabic_name(self):
        gaz = GazetteerProvider()
        result = gaz.geocode("إيبيريا")
        assert result is not None
        assert result.neighborhood == "Iberia"

    def test_case_insensitive(self):
        gaz = GazetteerProvider()
        result = gaz.geocode("iberia")
        assert result is not None

    def test_marshan(self):
        gaz = GazetteerProvider()
        result = gaz.geocode("Marshan")
        assert result is not None
        assert abs(result.latitude - 35.787) < 0.01

    def test_medina(self):
        gaz = GazetteerProvider()
        result = gaz.geocode("المدينة القديمة")
        assert result is not None


class TestGazetteerSubstringMatch:
    """Tests for substring matching."""

    def test_neighborhood_in_longer_text(self):
        gaz = GazetteerProvider()
        result = gaz.geocode("شقة في iberia طنجة")
        assert result is not None
        assert result.confidence == 0.9

    def test_partial_name(self):
        gaz = GazetteerProvider()
        result = gaz.geocode("boukhalef")
        assert result is not None


class TestGazetteerFuzzyMatch:
    """Tests for fuzzy matching (Darija spelling variants)."""

    def test_slight_misspelling(self):
        gaz = GazetteerProvider()
        result = gaz.geocode("Ibéria")
        assert result is not None

    def test_unknown_location_returns_none(self):
        gaz = GazetteerProvider()
        result = gaz.geocode("Planet Mars")
        assert result is None

    def test_empty_string_returns_none(self):
        gaz = GazetteerProvider()
        result = gaz.geocode("")
        assert result is None


class TestGazetteerTetouan:
    """Tests for Tetouan region entries."""

    def test_martil(self):
        gaz = GazetteerProvider()
        result = gaz.geocode("مرتيل")
        assert result is not None
        assert result.city == "Martil"

    def test_mdiq(self):
        gaz = GazetteerProvider()
        result = gaz.geocode("المضيق")
        assert result is not None

    def test_chefchaouen(self):
        gaz = GazetteerProvider()
        result = gaz.geocode("شفشاون")
        assert result is not None


class TestGazetteerSearch:
    """Tests for the search (autocomplete) method."""

    def test_search_returns_results(self):
        gaz = GazetteerProvider()
        results = gaz.search("iberia")
        assert len(results) >= 1

    def test_search_with_limit(self):
        gaz = GazetteerProvider()
        results = gaz.search("al", limit=3)
        assert len(results) <= 3

    def test_search_empty_query(self):
        gaz = GazetteerProvider()
        results = gaz.search("")
        # Empty query matches nothing with substring search
        assert isinstance(results, list)
