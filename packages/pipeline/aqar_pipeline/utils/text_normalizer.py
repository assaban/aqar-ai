"""
Aqar.ai: Text Normalizer
=========================
Post-transcription normalization for Darija/Arabic text.

Handles:
  - Arabic/Darija number words to digits
  - Common real estate abbreviations
  - French loan words commonly used in Moroccan real estate
  - Whitespace and punctuation cleanup
"""

from __future__ import annotations

import re

# ═══════════════════════════════════════
# Darija Number Words -> Digits
# ═══════════════════════════════════════

DARIJA_NUMBERS: dict[str, str] = {
    # Units
    "واحد": "1",
    "وحدة": "1",
    "زوج": "2",
    "جوج": "2",
    "تلاتة": "3",
    "ثلاثة": "3",
    "ربعة": "4",
    "أربعة": "4",
    "خمسة": "5",
    "ستة": "6",
    "سبعة": "7",
    "تمنية": "8",
    "ثمانية": "8",
    "تسعة": "9",
    "تسعود": "9",
    "عشرة": "10",
    # Tens
    "عشرين": "20",
    "تلاتين": "30",
    "ثلاثين": "30",
    "ربعين": "40",
    "أربعين": "40",
    "خمسين": "50",
    "ستين": "60",
    "سبعين": "70",
    "تمانين": "80",
    "ثمانين": "80",
    "تسعين": "90",
    # Hundreds
    "مية": "100",
    "مائة": "100",
    "ميتين": "200",
    "مئتين": "200",
    "تلت مية": "300",
    "ربع مية": "400",
    "خمس مية": "500",
    # Thousands
    "ألف": "1000",
    "الف": "1000",
    "ألفين": "2000",
    "الفين": "2000",
    # Large numbers (real estate context)
    "مليون": "1000000",
    "مليونين": "2000000",
}

# ═══════════════════════════════════════
# Real Estate Abbreviations / Terms
# ═══════════════════════════════════════

REAL_ESTATE_TERMS: dict[str, str] = {
    # Property types
    "شقة": "شقة",  # apartment (keep as-is, but normalize variants)
    "شقق": "شقة",
    "بارطمة": "شقة",  # Darija for apartment (from French "appartement")
    "بارطما": "شقة",
    "ستوديو": "استوديو",  # studio
    "فيلا": "فيلا",
    "فيلات": "فيلا",
    "كراج": "مرآب",  # garage
    "قراج": "مرآب",
    # Measurements
    "متر مربع": "م²",
    "متر كاري": "م²",  # Darija (from French "carré")
    "ميترو كاري": "م²",
    # Legal terms
    "طابو": "سند ملكية",  # title deed (tabou)
    "تيتر": "سند ملكية",  # titre foncier
    "ملكية": "ملكية",  # traditional ownership
    "رسم": "رسم",  # tax registration
    # Floors
    "الطابق": "الطابق",
    "لطاج": "الطابق",  # Darija for floor (from French "l'étage")
    "ليطاج": "الطابق",
    # Directions
    "واجهة": "واجهة",  # facade/facing
    "فاصاد": "واجهة",  # from French "façade"
}

# ═══════════════════════════════════════
# French Loan Words in Darija
# ═══════════════════════════════════════

FRENCH_LOANS: dict[str, str] = {
    "سالون": "صالون",  # salon/living room
    "كوزينة": "مطبخ",  # cuisine/kitchen
    "شامبر": "غرفة",  # chambre/room
    "دوش": "حمام",  # douche/shower
    "تواليت": "مرحاض",  # toilette
    "بالكون": "شرفة",  # balcon/balcony
    "تيراس": "سطح",  # terrasse/terrace
    "اسانسور": "مصعد",  # ascenseur/elevator
    "بلاصة": "مكان",  # place
    "مارشي": "سوق",  # marché/market
}


def normalize_numbers(text: str) -> str:
    """
    Replace Darija/Arabic number words with digits.

    Processes longer phrases first to avoid partial matches.
    """
    # Sort by length (longest first) to avoid partial replacements
    sorted_numbers = sorted(DARIJA_NUMBERS.items(), key=lambda x: len(x[0]), reverse=True)

    for word, digit in sorted_numbers:
        text = text.replace(word, digit)

    return text


def normalize_real_estate_terms(text: str) -> str:
    """Normalize real estate vocabulary to standard forms."""
    sorted_terms = sorted(REAL_ESTATE_TERMS.items(), key=lambda x: len(x[0]), reverse=True)

    for variant, standard in sorted_terms:
        if variant != standard:  # Skip identity mappings
            text = text.replace(variant, standard)

    return text


def normalize_french_loans(text: str) -> str:
    """Replace French loan words (in Arabic script) with standard Arabic equivalents."""
    for loan, standard in FRENCH_LOANS.items():
        text = text.replace(loan, standard)

    return text


def cleanup_whitespace(text: str) -> str:
    """Normalize whitespace: collapse multiple spaces, strip edges."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_transcript(text: str, apply_terms: bool = True) -> str:
    """
    Apply all normalizations to a transcript text.

    Order matters:
      1. Number words to digits (before term normalization)
      2. Real estate terms (optional)
      3. French loan words
      4. Whitespace cleanup

    Args:
        text: Raw transcript text from Whisper.
        apply_terms: Whether to normalize real estate terms and French loans.
                     Set to False to keep original vocabulary for analysis.

    Returns:
        Normalized text.
    """
    text = normalize_numbers(text)

    if apply_terms:
        text = normalize_real_estate_terms(text)
        text = normalize_french_loans(text)

    text = cleanup_whitespace(text)
    return text
