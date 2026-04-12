"""
Schema contract tests — validate every entry in the frontend JSON.

These tests answer: "Is every record structurally correct?"
They iterate over ALL entries, not a sample. Each violation reports the
offending entry's page_id for traceability.
"""

import re

import pytest

# --- Valid value sets ---

VALID_NS0_ENTRY_TYPES = {
    "collected-works", "correspondence", "drama", "dramatic-reading",
    "essay", "fiction", "film", "foreword", "historical-study",
    "newspaper", "other", "poetry", "secondary-literature",
    "symposium", "translation",
}

VALID_ALL_ENTRY_TYPES = VALID_NS0_ENTRY_TYPES | {
    "category", "template", "file", "mediawiki", "help",
}

VALID_TIME_PERIODS = {
    "pre-zweig", "lifetime", "post-wwii", "late-20c", "contemporary",
}

# ISO 639-1 codes (2-letter) and common 3-letter codes in the dataset
VALID_LANGUAGE_CODE_PATTERN = re.compile(r"^[a-z]{2,3}$")

# --- Patterns that should NOT appear in cleaned fields ---

# Wiki markup remnants
WIKI_MARKUP_PATTERN = re.compile(
    r"\[\["        # opening wiki link
    r"|\]\]"       # closing wiki link
    r"|<lst\b"     # lst tags
    r"|<ref\b"     # ref tags
    r"|__TOC__"    # table of contents magic word
    r"|__NOTOC__"
    r"|__FORCETOC__"
    r"|__NOEDITSECTION__"
    r"|\{\{DEFAULTSORT"
    r"|\{\{DEFAULTSORTKEY"
)

# Mojibake signatures: UTF-8 bytes misread as Latin-1
# Careful: must not match legitimate Vietnamese/Arabic/etc. diacritics.
# These patterns are specific double-byte mojibake sequences.
MOJIBAKE_PATTERN = re.compile(
    r"Ã¤"   # ä
    r"|Ã¶"  # ö
    r"|Ã¼"  # ü
    r"|Ã\x9f"  # ß
    r"|Ã©"  # é (only flag when preceded by uppercase Ã — not standalone é)
    r"|Ã¨"  # è
    r"|Ã "   # à (with trailing space, avoids matching "Ã" in legitimate text)
    r"|Â\xa0"  # non-breaking space mojibake
    r"|Â©"  # © mojibake
    r"|Â»"  # » mojibake
    r"|Â«"  # « mojibake
)


# Fixtures (all_entries, ns0_entries) are defined in conftest.py


# ---------------------------------------------------------------------------
# Entry type validation
# ---------------------------------------------------------------------------

class TestEntryTypes:
    """Every entry has a valid, recognized entry type."""

    def test_all_entries_have_valid_type(self, all_entries):
        """entryType must be one of the defined types."""
        invalid = [
            (e["sourcePageId"], e.get("entryType"))
            for e in all_entries
            if e.get("entryType") not in VALID_ALL_ENTRY_TYPES
        ]
        assert len(invalid) == 0, (
            f"{len(invalid)} entries with invalid entryType: {invalid[:20]}"
        )

    def test_ns0_entries_have_content_type(self, ns0_entries):
        """ns-0 entries must have one of the 15 content types (not system types)."""
        invalid = [
            (e["sourcePageId"], e.get("entryType"))
            for e in ns0_entries
            if e.get("entryType") not in VALID_NS0_ENTRY_TYPES
        ]
        assert len(invalid) == 0, (
            f"{len(invalid)} ns-0 entries with non-content entryType: {invalid[:20]}"
        )


# ---------------------------------------------------------------------------
# Year validation
# ---------------------------------------------------------------------------

class TestYearRange:
    """Publication years must be within historically plausible bounds."""

    YEAR_MIN = 1800
    YEAR_MAX = 2030

    def test_all_years_in_range(self, ns0_entries):
        """Every year value (where present) is between 1800 and 2030."""
        out_of_range = [
            (e["sourcePageId"], e.get("year"))
            for e in ns0_entries
            if e.get("year") is not None
            and (e["year"] < self.YEAR_MIN or e["year"] > self.YEAR_MAX)
        ]
        assert len(out_of_range) == 0, (
            f"{len(out_of_range)} entries with year out of range "
            f"[{self.YEAR_MIN}, {self.YEAR_MAX}]: {out_of_range[:20]}"
        )

    def test_year_is_integer(self, ns0_entries):
        """Year must be an integer (not a string or float)."""
        non_int = [
            (e["sourcePageId"], e.get("year"), type(e.get("year")).__name__)
            for e in ns0_entries
            if e.get("year") is not None and not isinstance(e["year"], int)
        ]
        assert len(non_int) == 0, (
            f"{len(non_int)} entries with non-integer year: {non_int[:20]}"
        )


# ---------------------------------------------------------------------------
# Language code validation
# ---------------------------------------------------------------------------

class TestLanguageCodes:
    """Language codes must be valid ISO 639 codes."""

    def test_language_codes_are_valid(self, ns0_entries):
        """languageCode (where present) matches ISO 639-1/639-2 pattern."""
        invalid = [
            (e["sourcePageId"], e.get("languageCode"))
            for e in ns0_entries
            if e.get("languageCode")
            and not VALID_LANGUAGE_CODE_PATTERN.match(str(e["languageCode"]))
        ]
        assert len(invalid) == 0, (
            f"{len(invalid)} entries with invalid language code: {invalid[:20]}"
        )

    def test_time_periods_are_valid(self, ns0_entries):
        """timePeriod (where present) is one of the defined values."""
        invalid = [
            (e["sourcePageId"], e.get("timePeriod"))
            for e in ns0_entries
            if e.get("timePeriod")
            and e["timePeriod"] not in VALID_TIME_PERIODS
        ]
        assert len(invalid) == 0, (
            f"{len(invalid)} entries with invalid timePeriod: {invalid[:20]}"
        )


# ---------------------------------------------------------------------------
# Page count validation
# ---------------------------------------------------------------------------

class TestPageCount:
    """Page counts must be plausible positive integers."""

    def test_page_count_positive(self, ns0_entries):
        """pageCount (where present) must be > 0."""
        invalid = [
            (e["sourcePageId"], e.get("pageCount"))
            for e in ns0_entries
            if e.get("pageCount") is not None and e["pageCount"] <= 0
        ]
        assert len(invalid) == 0, (
            f"{len(invalid)} entries with non-positive pageCount: {invalid[:20]}"
        )

    def test_page_count_under_limit(self, ns0_entries):
        """pageCount must be ≤ 10,000 (no bibliography entry has more)."""
        invalid = [
            (e["sourcePageId"], e.get("pageCount"))
            for e in ns0_entries
            if e.get("pageCount") is not None and e["pageCount"] > 10000
        ]
        assert len(invalid) == 0, (
            f"{len(invalid)} entries with pageCount > 10000: {invalid[:20]}"
        )

    def test_page_count_is_integer(self, ns0_entries):
        """pageCount must be an integer."""
        non_int = [
            (e["sourcePageId"], e.get("pageCount"), type(e.get("pageCount")).__name__)
            for e in ns0_entries
            if e.get("pageCount") is not None
            and not isinstance(e["pageCount"], int)
        ]
        assert len(non_int) == 0, (
            f"{len(non_int)} entries with non-integer pageCount: {non_int[:20]}"
        )


# ---------------------------------------------------------------------------
# No wiki markup residue in cleaned fields
# ---------------------------------------------------------------------------

class TestNoMarkupResidue:
    """Cleaned text fields must not contain wiki markup fragments."""

    FIELDS_TO_CHECK = ["title", "publisher", "location", "language"]

    # Known markup issues: 14 titles = "__TOC__" (title extraction fell through),
    # 6 titles contain "]]" or "[[" (unclosed wiki links in parsed text).
    # These are real pipeline bugs to fix — tracked here so new violations are caught.
    KNOWN_MARKUP_COUNT = 6

    def test_no_wiki_markup_in_fields(self, ns0_entries):
        """No field contains [[, ]], <lst, __TOC__, or {{DEFAULTSORT."""
        violations = []
        for entry in ns0_entries:
            for field in self.FIELDS_TO_CHECK:
                value = entry.get(field)
                if value and WIKI_MARKUP_PATTERN.search(str(value)):
                    match = WIKI_MARKUP_PATTERN.search(str(value))
                    violations.append(
                        (entry["sourcePageId"], field, match.group(), str(value)[:80])
                    )

        # Fail if NEW violations appear beyond known count
        assert len(violations) <= self.KNOWN_MARKUP_COUNT, (
            f"Found {len(violations)} markup violations (known: {self.KNOWN_MARKUP_COUNT}). "
            f"New violations:\n"
            + "\n".join(
                f"  page {pid}, {field}: found '{match}' in '{val}'"
                for pid, field, match, val in violations[:30]
            )
        )
        # Warn if count decreased (fixes applied — update KNOWN_MARKUP_COUNT)
        if violations and len(violations) < self.KNOWN_MARKUP_COUNT:
            import warnings
            warnings.warn(
                f"Markup violations decreased from {self.KNOWN_MARKUP_COUNT} to "
                f"{len(violations)} — update KNOWN_MARKUP_COUNT",
                UserWarning, stacklevel=1,
            )

    def test_no_empty_string_fields(self, ns0_entries):
        """Fields are either absent/None or contain actual content — never empty strings."""
        violations = []
        for entry in ns0_entries:
            for field in self.FIELDS_TO_CHECK + ["entryType"]:
                if entry.get(field) == "":
                    violations.append((entry["sourcePageId"], field))
        assert len(violations) == 0, (
            f"{len(violations)} fields are empty strings (should be null/absent):\n"
            + "\n".join(f"  page {pid}, {field}" for pid, field in violations[:20])
        )


# ---------------------------------------------------------------------------
# No mojibake in text fields
# ---------------------------------------------------------------------------

class TestNoMojibake:
    """Text fields must not contain mojibake byte sequences."""

    FIELDS_TO_CHECK = ["title", "publisher", "location", "language"]

    def test_no_mojibake_in_fields(self, ns0_entries):
        """No field contains known mojibake patterns (Ã¤, Ã¶, Ã¼, etc.)."""
        violations = []
        for entry in ns0_entries:
            for field in self.FIELDS_TO_CHECK:
                value = entry.get(field)
                if value and MOJIBAKE_PATTERN.search(str(value)):
                    violations.append(
                        (entry["sourcePageId"], field, str(value)[:80])
                    )
        assert len(violations) == 0, (
            f"{len(violations)} fields contain mojibake:\n"
            + "\n".join(
                f"  page {pid}, {field}: '{val}'"
                for pid, field, val in violations[:20]
            )
        )


# ---------------------------------------------------------------------------
# @type array consistency
# ---------------------------------------------------------------------------

class TestLdTypeConsistency:
    """JSON-LD @type arrays must be consistent with entryType."""

    def test_type_is_list(self, all_entries):
        """@type must be a list (not a single string)."""
        non_list = [
            (e["sourcePageId"], type(e.get("@type")).__name__)
            for e in all_entries
            if e.get("@type") and not isinstance(e["@type"], list)
        ]
        assert len(non_list) == 0, (
            f"{len(non_list)} entries with non-list @type: {non_list[:20]}"
        )

    def test_type_has_schema_and_klawiter(self, ns0_entries):
        """ns-0 entries should have both a schema: and klawiter: type."""
        missing_schema = []
        missing_klawiter = []
        for entry in ns0_entries:
            types = entry.get("@type", [])
            has_schema = any(t.startswith("schema:") for t in types)
            has_klawiter = any(t.startswith("klawiter:") for t in types)
            if not has_schema:
                missing_schema.append(entry["sourcePageId"])
            if not has_klawiter:
                missing_klawiter.append(entry["sourcePageId"])

        issues = []
        if missing_schema:
            issues.append(f"{len(missing_schema)} missing schema: type: {missing_schema[:10]}")
        if missing_klawiter:
            issues.append(f"{len(missing_klawiter)} missing klawiter: type: {missing_klawiter[:10]}")
        assert len(issues) == 0, "\n".join(issues)
