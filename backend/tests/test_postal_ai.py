"""Unit tests for Postal AI NLP, multi-script language detection,
colonial alias expansion, and PIN extraction algorithms.
"""

import pytest
from app.services.postal_ai import (
    PIN_PATTERN,
    detect_language,
    extract_entities,
    extract_pin,
    normalize_address,
)


def test_pin_extraction_valid():
    assert extract_pin("Ambattur, Chennai - 600053") == "600053"
    assert extract_pin("PIN CODE 560001, GPO Bengaluru") == "560001"
    assert extract_pin("Delhi 110001 near Connaught Place") == "110001"


def test_pin_extraction_invalid_and_masked():
    # 6000XX has masked characters, should not match strict 6-digit PIN regex
    assert extract_pin("PIN 6000XX") is None
    # 012345 starts with 0 (Indian PINs start with 1-9)
    assert extract_pin("Invalid PIN 012345") is None


def test_language_detection():
    assert detect_language("अंबात्तूर एसबीआई बैंक के पास, चेन्नई 600053") == "Hindi / Devanagari (हिन्दी)"
    assert detect_language("அம்பத்தூர் எஸ்பிஐ வங்கி அருகில், சென்னை 600053") == "Tamil (தமிழ்)"
    assert detect_language("Ambattur near SBI bank, opp bus stand") == "English / Romanized"
    assert detect_language("Bengaluru GPO post office") == "English / Romanized"


def test_alias_expansion_via_normalize():
    """Alias expansion (Madras->Chennai, Ambathur->Ambattur) happens inside normalize_address."""
    expanded = normalize_address("Old Madras road near Ambathur station, Bangalore")
    assert "chennai" in expanded.lower()
    assert "ambattur" in expanded.lower()
    assert "bengaluru" in expanded.lower()


def test_address_normalization():
    norm = normalize_address("Ambathur near   SBI bank,, opp bus stand... pin: 600053")
    assert "Ambattur" in norm
    assert ",," not in norm
    assert "  " not in norm


def test_entity_extraction():
    entities = extract_entities(
        "Ambathur near SBI bank, opp bus stand, Chennai 600053",
        "Ambattur Near SBI Bank, Opp Bus Stand, Chennai 600053"
    )
    assert entities["extracted_pin"] == "600053"
    assert entities["landmark"] is not None
