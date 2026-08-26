"""
Unit tests for pipeline/lib/encoding.py.
Tests mojibake detection/repair and HTML entity handling.
"""

import unicodedata

from lib.encoding import (
    fix_encoding,
    fix_html_entities,
    fix_mojibake,
    has_mojibake,
)


class TestHasMojibake:
    def test_detects_common_mojibake_patterns(self):
        assert has_mojibake("SchÃ¤fer") is True  # ä
        assert has_mojibake("MÃ¼ller") is True  # ü
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
        assert result == unicodedata.normalize("NFC", result)

    def test_none_passthrough(self):
        assert fix_mojibake(None) is None


def corrupt(s):
    """Reproduce the original corruption: UTF-8 bytes read back as Latin-1.
    fix_mojibake must invert this, restoring the source string."""
    return s.encode("utf-8").decode("latin-1")


class TestMojibakeTransliteration:
    """The broadened repair recovers the Latin Extended diacritics of
    transliterated titles (validation.md error class 3), not only umlauts."""

    def test_latin_extended_a(self):
        # Arabic, Slavic, Turkish, Baltic romanization: macrons, carons, cedillas.
        for word in [
            "al-Qāhira",
            "Athēna",
            "ūmūr",
            "Mektuplaşmalar",
            "Książki",
            "Muž",
            "čovek",
            "Tōkyō",
        ]:
            assert fix_mojibake(corrupt(word)) == word

    def test_latin_extended_additional(self):
        # Arabic and Indic romanization with dots below.
        for word in ["ḥadīth", "ṭabaqāt", "ṣaḥīfa", "Ḥusayn"]:
            assert fix_mojibake(corrupt(word)) == word

    def test_double_encoded_smart_quotes(self):
        assert fix_mojibake(corrupt("Izdatel’stvo “AST”")) == "Izdatel’stvo “AST”"

    def test_clean_german_unchanged(self):
        # Accented letters followed by ASCII are not a mojibake run.
        for word in [
            "Amokläufer",
            "Erzählungen",
            "Dämon",
            "Hölderlin",
            "Büchern",
            "Aufsätze",
            "Größe",
            "Straße",
        ]:
            assert fix_mojibake(word) == word

    def test_clean_accent_before_guillemet_not_corrupted(self):
        # Catalan "nació»": the byte signature matches but is not valid UTF-8
        # once re-encoded, so the run is left untouched (self-validation).
        text = "una altra nació» ens mostren"
        assert fix_mojibake(text) == text
        assert has_mojibake(text) is False

    def test_idempotent(self):
        once = fix_mojibake(corrupt("al-Qāhira und Schäfer"))
        assert fix_mojibake(once) == once

    def test_mixed_line_repairs_only_corrupt_part(self):
        # Clean text and a corrupt token on one line: only the token is repaired.
        text = "Edited by " + corrupt("Książki") + " in Wien"
        assert fix_mojibake(text) == "Edited by Książki in Wien"


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
