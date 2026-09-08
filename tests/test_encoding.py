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
    is_encoding_damaged,
    repair_value_encoding,
    strip_orphan_arabic_marks,
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


class TestStripOrphanArabicMarks:
    """A stray Arabic combining mark in Latin surroundings is an input
    artifact; genuine Arabic vocalization carries an Arabic base character."""

    def test_real_title_page_4775(self):
        # Journal place of publication inside a Latin bibliographic reference.
        text = (
            "in Al-Ittiḥād [The Union] [ِAbu Dhabi], Vol. ?:No. ? [1 March 2012], pp. ?"
        )
        assert strip_orphan_arabic_marks(text) == (
            "in Al-Ittiḥād [The Union] [Abu Dhabi], Vol. ?:No. ? [1 March 2012], pp. ?"
        )

    def test_real_title_page_5913(self):
        # Mark at string start, no base character at all.
        text = "ِAl-ʿAmrī, Mashāʿil / Alamri, Mashael"
        assert strip_orphan_arabic_marks(text) == "Al-ʿAmrī, Mashāʿil / Alamri, Mashael"

    def test_genuine_arabic_unchanged(self):
        # Source passage from the dump: kasra and shadda on an Arabic base,
        # damma inside the following word. Vocalization is content, not noise.
        text = "أيادٍ خفية تحرِّكنا .. الحياة تُشبه"
        assert strip_orphan_arabic_marks(text) == text

    def test_latin_combining_diacritics_unchanged(self):
        # Decomposed Latin diacritics are outside the Arabic script ranges.
        for word in ["Schäfer", "naïve", "Tokyō", "Zwéig"]:
            assert strip_orphan_arabic_marks(word) == word

    def test_mark_after_latin_letter_is_orphan(self):
        assert strip_orphan_arabic_marks("Abuِ Dhabi") == "Abu Dhabi"

    def test_idempotent_and_passthrough(self):
        once = strip_orphan_arabic_marks("[ِAmman]")
        assert once == "[Amman]"
        assert strip_orphan_arabic_marks(once) == once
        assert strip_orphan_arabic_marks("") == ""
        assert strip_orphan_arabic_marks(None) is None

    def test_applied_by_fix_encoding(self):
        assert fix_encoding("[ِAmman] &amp; [ِAbu Dhabi]") == ("[Amman] & [Abu Dhabi]")


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


class TestValueRepair:
    """Short field values carry both the Latin-1 and the CP1252 misreading, so
    the value repair runs the byte round-trip under both codecs until stable."""

    def test_latin1_misreading_is_undone(self):
        assert repair_value_encoding("Otokar KerÅ¡ovani") == "Otokar Keršovani"

    def test_cp1252_misreading_is_undone(self):
        assert repair_value_encoding("Xiâ€™an") == "Xi’an"

    def test_double_encoding_is_undone(self):
        assert repair_value_encoding("VÅ­zrazhdane") == "Vŭzrazhdane"

    def test_repair_is_idempotent(self):
        once = repair_value_encoding("Mlada zaloÅ¾ba")
        assert repair_value_encoding(once) == once == "Mlada založba"

    def test_clean_text_is_untouched(self):
        for value in ("Kavkazskiĭ Krai", "Insel-Verlag", "Éditions Stock", ""):
            assert repair_value_encoding(value) == value

    def test_damage_detection_covers_both_misreadings(self):
        assert is_encoding_damaged("Otokar KerÅ¡ovani")
        assert is_encoding_damaged("Izdatelâ€™stvo")
        assert not is_encoding_damaged("Kavkazskiĭ Krai")
        assert not is_encoding_damaged("")

    def test_a_lost_byte_stays_detectable(self):
        """The closing quote of this value never reached the cache, so the
        round-trip leaves damage behind and the caller must reject it."""
        assert is_encoding_damaged(repair_value_encoding("Izdatelâ€™stvo â€œPravdaâ€"))
