"""
Real-data round-trip tests for the Klawiter extraction pipeline.
Each test runs extraction functions on hand-labeled entries from
data/intermediate/test_sample_20.json and checks against known values.
"""

import pytest

from lib.patterns import (
    extract_location,
    extract_page_count,
    extract_publisher,
    extract_translator,
    extract_language_from_category,
)
from lib.wiki_parser import extract_categories, extract_structured_data


class TestLocationExtractionReal:
    """Test extract_location against hand-labeled real entries."""

    def test_location(self, real_entry):
        expected = real_entry["existing"].get("location", "")
        result = extract_location(real_entry["text"])

        if expected:
            assert result == expected, (
                f"[page {real_entry['page_id']}] "
                f"Expected location '{expected}', got '{result}'"
            )
        # If expected is empty, we don't assert — the entry may genuinely lack a location


class TestPublisherExtractionReal:
    """Test extract_publisher against hand-labeled entries."""

    def test_publisher(self, real_entry):
        expected = real_entry["existing"].get("publisher", "")
        result = extract_publisher(real_entry["text"])

        if expected and "needed" not in real_entry or "publisher" not in real_entry.get("needed", []):
            # Only assert when publisher was successfully extracted (not in "needed" list)
            if expected:
                assert result is not None, (
                    f"[page {real_entry['page_id']}] "
                    f"Expected publisher '{expected}', got None"
                )


class TestTranslatorExtractionReal:
    """Test extract_translator against hand-labeled entries."""

    def test_translator(self, real_entry):
        expected = real_entry["existing"].get("translator", "")
        result = extract_translator(real_entry["text"])

        if expected and "translator" not in real_entry.get("needed", []):
            # Translator was already extracted by regex — verify it still works
            assert result is not None, (
                f"[page {real_entry['page_id']}] "
                f"Expected translator '{expected}', got None"
            )


class TestPageCountExtractionReal:
    """Test extract_page_count against hand-labeled entries."""

    # Entries where existing page_count reflects pp. ranges, not actual page count
    _SKIP_PAGE_IDS = {162, 1999}

    def test_page_count(self, real_entry):
        if real_entry["page_id"] in self._SKIP_PAGE_IDS:
            pytest.skip("page_count in fixture is a page range, not total count")

        expected = real_entry["existing"].get("page_count", "")
        result = extract_page_count(real_entry["text"])

        if expected and "page_count" not in real_entry.get("needed", []):
            assert result is not None, (
                f"[page {real_entry['page_id']}] "
                f"Expected page_count '{expected}', got None"
            )


class TestLanguageDetectionReal:
    """Test language extraction from categories in real entries."""

    # Entries where truncated text doesn't contain the expected language category
    # (language in fixture was derived from full pipeline context, not the truncated text)
    _SKIP_LANGUAGE_IDS = {162, 4376, 4445, 5746}

    def test_language(self, real_entry):
        if real_entry["page_id"] in self._SKIP_LANGUAGE_IDS:
            pytest.skip("Truncated text doesn't contain expected language category")

        expected = real_entry["existing"].get("language", "")
        cats, _ = extract_categories(real_entry["text"])
        result = extract_language_from_category(cats)

        if expected:
            assert result == expected, (
                f"[page {real_entry['page_id']}] "
                f"Expected language '{expected}', got '{result}'"
            )


class TestStructuredDataReal:
    """Test full extract_structured_data pipeline on real entries."""

    def test_not_redirect(self, real_entry):
        """All test_sample_20 entries are real bibliography entries, not redirects."""
        data = extract_structured_data(real_entry["text"])
        assert data.get("is_redirect") is False, (
            f"[page {real_entry['page_id']}] Unexpected redirect"
        )

    def test_has_clean_content(self, real_entry):
        """All entries should produce clean_content."""
        data = extract_structured_data(real_entry["text"])
        assert "clean_content" in data
        assert len(data["clean_content"]) > 0

    def test_categories_extracted(self, real_entry):
        """Most entries should have categories."""
        data = extract_structured_data(real_entry["text"])
        # Only entries with [[Category:...]] in their text should have categories
        if "[[Category:" in real_entry["text"]:
            assert "categories" in data
            assert len(data["categories"]) > 0
