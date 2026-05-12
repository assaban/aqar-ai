"""
Unit tests for the Darija/Arabic text normalizer.

Tests cover: number word conversion, real estate terms,
French loan words, whitespace cleanup, and full pipeline.
"""

from aqar_pipeline.utils.text_normalizer import (
    cleanup_whitespace,
    normalize_french_loans,
    normalize_numbers,
    normalize_real_estate_terms,
    normalize_transcript,
)

# ═══════════════════════════════════════
# Number Word Conversion
# ═══════════════════════════════════════


class TestNormalizeNumbers:
    """Tests for Darija/Arabic number word to digit conversion."""

    def test_basic_unit(self):
        assert "3" in normalize_numbers("تلاتة")

    def test_darija_two(self):
        """جوج is Darija for 2."""
        assert "2" in normalize_numbers("جوج")

    def test_tens(self):
        assert "20" in normalize_numbers("عشرين")
        assert "50" in normalize_numbers("خمسين")

    def test_hundreds(self):
        assert "100" in normalize_numbers("مية")
        assert "200" in normalize_numbers("ميتين")
        assert "300" in normalize_numbers("تلت مية")

    def test_thousands(self):
        assert "1000" in normalize_numbers("ألف")
        assert "2000" in normalize_numbers("ألفين")

    def test_million(self):
        assert "1000000" in normalize_numbers("مليون")

    def test_mixed_text(self):
        """Numbers embedded in a sentence."""
        result = normalize_numbers("الثمن تلاتة مليون")
        assert "3" in result
        assert "1000000" in result

    def test_no_numbers_unchanged(self):
        text = "شقة جميلة في طنجة"
        assert normalize_numbers(text) == text


# ═══════════════════════════════════════
# Real Estate Terms
# ═══════════════════════════════════════


class TestNormalizeRealEstateTerms:
    """Tests for real estate vocabulary normalization."""

    def test_darija_apartment(self):
        """بارطمة (from French appartement) should normalize to شقة."""
        result = normalize_real_estate_terms("بارطمة")
        assert "شقة" in result

    def test_square_meter_darija(self):
        """متر كاري (from French carré) should normalize to م²."""
        result = normalize_real_estate_terms("متر كاري")
        assert "م²" in result

    def test_darija_floor(self):
        """لطاج (from French l'étage) should normalize to الطابق."""
        result = normalize_real_estate_terms("لطاج")
        assert "الطابق" in result

    def test_standard_terms_unchanged(self):
        """Standard Arabic terms should not be altered."""
        text = "شقة في الطابق"
        result = normalize_real_estate_terms(text)
        assert "شقة" in result
        assert "الطابق" in result


# ═══════════════════════════════════════
# French Loan Words
# ═══════════════════════════════════════


class TestNormalizeFrenchLoans:
    """Tests for French loan word normalization."""

    def test_salon(self):
        result = normalize_french_loans("سالون")
        assert "صالون" in result

    def test_kitchen(self):
        result = normalize_french_loans("كوزينة")
        assert "مطبخ" in result

    def test_room(self):
        result = normalize_french_loans("شامبر")
        assert "غرفة" in result

    def test_elevator(self):
        result = normalize_french_loans("اسانسور")
        assert "مصعد" in result

    def test_balcony(self):
        result = normalize_french_loans("بالكون")
        assert "شرفة" in result


# ═══════════════════════════════════════
# Whitespace Cleanup
# ═══════════════════════════════════════


class TestCleanupWhitespace:
    """Tests for whitespace normalization."""

    def test_collapses_multiple_spaces(self):
        assert cleanup_whitespace("hello    world") == "hello world"

    def test_strips_edges(self):
        assert cleanup_whitespace("  hello  ") == "hello"

    def test_handles_newlines_and_tabs(self):
        assert cleanup_whitespace("hello\n\t  world") == "hello world"

    def test_empty_string(self):
        assert cleanup_whitespace("") == ""

    def test_single_word(self):
        assert cleanup_whitespace("  word  ") == "word"


# ═══════════════════════════════════════
# Full Normalization Pipeline
# ═══════════════════════════════════════


class TestNormalizeTranscript:
    """Tests for the full normalization pipeline."""

    def test_combines_all_normalizations(self):
        text = "بارطمة  فيها  جوج  شامبر  و  سالون"
        result = normalize_transcript(text)
        # بارطمة -> شقة, جوج -> 2, شامبر -> غرفة, سالون -> صالون
        assert "شقة" in result
        assert "2" in result
        assert "غرفة" in result
        assert "صالون" in result
        # No double spaces
        assert "  " not in result

    def test_without_term_normalization(self):
        """When apply_terms=False, only numbers and whitespace are normalized."""
        text = "بارطمة فيها جوج شامبر"
        result = normalize_transcript(text, apply_terms=False)
        # Numbers should be converted
        assert "2" in result
        # But terms should stay as-is
        assert "بارطمة" in result
        assert "شامبر" in result

    def test_real_estate_sentence(self):
        """A realistic Darija real estate sentence."""
        text = "هاد الشقة فيها تلاتة ديال الشامبر و سالون كبير في لطاج الثالث"
        result = normalize_transcript(text)
        assert "3" in result
        assert "غرفة" in result
        assert "صالون" in result
        assert "الطابق" in result
