"""
Unit tests for pipeline/lib/encoding.py.
Tests mojibake detection/repair and HTML entity handling.
"""

import unicodedata

from lib.encoding import (
    fix_mojibake,
    fix_html_entities,
    fix_encoding,
    has_mojibake,
)


class TestHasMojibake:
    def test_detects_common_mojibake_patterns(self):
        assert has_mojibake("SchÃ¤fer") is True      # ä
        assert has_mojibake("MÃ¼ller") is True       # ü
        assert has_mojibake("Text\xc2\xa0here") is True  # nbsp

    def test_rejects_clean_text(self):
        assert has_mojibake("Schäfer und Müller") is False
        assert has_mojibake("Hello World") is False
        assert has_mojibake("") is False
        assert has_mojibake(None) is False


class TestFixMojibake:
    def test_fixes_umlauts(self, mojibake_text, mojibake_fixed):
        assert fix_mojibake(mojibake_text) == mojibake_fixed

    def test_preserves_clean_text(self, clean_utf8_text):
        assert fix_mojibake(clean_utf8_text) == clean_utf8_text

    def test_line_by_line_isolation(self):
        """Only corrupted lines are fixed; clean lines stay intact."""
        text = "Clean line here\nSchÃ¤fer on this line\nAnother clean line"
        result = fix_mojibake(text)
        assert "Schäfer" in result
        assert "Clean line here" in result
        assert "Another clean line" in result

    def test_nfc_normalization(self):
        result = fix_mojibake("SchÃ¤fer")
        assert result == unicodedata.normalize('NFC', result)

    def test_none_passthrough(self):
        assert fix_mojibake(None) is None


class TestFixHtmlEntities:
    def test_all_named_entities(self, html_entity_text, html_entity_fixed):
        """Single test covering nbsp, mdash, amp, and combined entities."""
        assert fix_html_entities(html_entity_text) == html_entity_fixed

    def test_numeric_entities(self):
        assert fix_html_entities("&#65;&#x3B1;") == "Aα"

    def test_passthrough(self):
        assert fix_html_entities("Plain text") == "Plain text"
        assert fix_html_entities(None) is None


class TestFixEncoding:
    def test_fixes_both_mojibake_and_entities(self):
        text = "SchÃ¤fer &amp; MÃ¼ller"
        result = fix_encoding(text)
        assert result == "Schäfer & Müller"

    def test_clean_text_unchanged(self):
        assert fix_encoding("Schäfer und Müller") == "Schäfer und Müller"

    def test_passthrough(self):
        assert fix_encoding(None) is None
        assert fix_encoding("") == ""
