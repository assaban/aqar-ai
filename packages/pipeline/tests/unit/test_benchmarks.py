"""
Unit tests for benchmark utilities: WER calculation and extraction accuracy.
"""

from aqar_pipeline.benchmarks.wer import calculate_wer
from aqar_pipeline.benchmarks.extraction_accuracy import (
    score_extraction,
    _values_match,
)


# ═══════════════════════════════════════
# WER Calculator
# ═══════════════════════════════════════


class TestCalculateWER:
    """Tests for Word Error Rate calculation."""

    def test_identical_text(self):
        result = calculate_wer("hello world", "hello world")
        assert result.wer == 0.0
        assert result.substitutions == 0
        assert result.insertions == 0
        assert result.deletions == 0

    def test_one_substitution(self):
        result = calculate_wer("the cat sat", "the dog sat")
        assert result.substitutions == 1
        assert result.wer > 0

    def test_one_insertion(self):
        result = calculate_wer("hello world", "hello big world")
        assert result.insertions == 1

    def test_one_deletion(self):
        result = calculate_wer("hello big world", "hello world")
        assert result.deletions == 1

    def test_empty_reference(self):
        result = calculate_wer("", "some words")
        assert result.wer == 1.0

    def test_empty_hypothesis(self):
        result = calculate_wer("some words", "")
        assert result.wer == 1.0

    def test_both_empty(self):
        result = calculate_wer("", "")
        assert result.wer == 0.0

    def test_case_insensitive(self):
        result = calculate_wer("Hello World", "hello world")
        assert result.wer == 0.0

    def test_arabic_text(self):
        ref = "شقة في طنجة"
        hyp = "شقة في طنجة"
        result = calculate_wer(ref, hyp)
        assert result.wer == 0.0

    def test_arabic_with_errors(self):
        ref = "شقة كبيرة في حي إيبيريا"
        hyp = "شقة في حي إيبيريا"
        result = calculate_wer(ref, hyp)
        assert result.wer > 0
        assert result.deletions >= 1

    def test_reference_id_stored(self):
        result = calculate_wer("hello", "hello", reference_id="test_001")
        assert result.reference_id == "test_001"


# ═══════════════════════════════════════
# Extraction Accuracy
# ═══════════════════════════════════════


class TestValuesMatch:
    """Tests for field value comparison."""

    def test_exact_string_match(self):
        assert _values_match("property_type", "apartment", "apartment")

    def test_case_insensitive_match(self):
        assert _values_match("property_type", "Apartment", "apartment")

    def test_string_mismatch(self):
        assert not _values_match("property_type", "apartment", "villa")

    def test_numeric_exact_match(self):
        assert _values_match("price", 750000, 750000)

    def test_numeric_within_tolerance(self):
        # 5% tolerance for price
        assert _values_match("price", 750000, 740000)

    def test_numeric_outside_tolerance(self):
        assert not _values_match("price", 750000, 500000)

    def test_area_within_tolerance(self):
        # 10% tolerance for area
        assert _values_match("area_sqm", 100, 95)

    def test_both_none(self):
        assert _values_match("rooms", None, None)

    def test_one_none(self):
        assert not _values_match("rooms", 3, None)


class TestScoreExtraction:
    """Tests for extraction scoring."""

    def test_perfect_extraction(self):
        expected = {
            "property_type": "apartment",
            "price": 750000,
            "rooms": 4,
        }
        actual = {
            "property_type": "apartment",
            "price": 750000,
            "rooms": 4,
        }
        score = score_extraction(expected, actual, case_id="test_001")
        assert score.overall_accuracy == 1.0

    def test_all_wrong(self):
        expected = {
            "property_type": "apartment",
            "listing_type": "sale",
        }
        actual = {
            "property_type": "villa",
            "listing_type": "rent",
        }
        score = score_extraction(expected, actual, case_id="test_002")
        assert score.overall_accuracy == 0.0

    def test_missing_field(self):
        expected = {"property_type": "apartment", "rooms": 4}
        actual = {"property_type": "apartment"}
        score = score_extraction(expected, actual)
        # property_type correct (1.0), rooms missing (0.0), avg = 0.5
        assert score.overall_accuracy == 0.5

    def test_empty_expected(self):
        score = score_extraction({}, {"property_type": "villa"})
        assert score.overall_accuracy == 0.0
