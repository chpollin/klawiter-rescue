"""
Real-data round-trip tests for the Klawiter extraction pipeline.
Each test runs extraction functions on hand-labeled entries from
data/intermediate/test_sample_20.json and checks against known values.

The "existing" field in fixtures contains values from the pipeline's
actual output. Fields listed in "needed" are gaps the LLM step fills.
We test: fields NOT in "needed" should match the existing values.
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


# Entries where fixture data doesn't align with what's extractable from truncated text
_SKIP_PAGE_COUNT = {162, 1999}  # existing page_count is from pp. ranges, not total
_SKIP_LANGUAGE = {162, 4376, 4445, 5746}  # language category missing in truncated text


class TestLocationExtractionReal:
    def test_location(self, real_entry):
        expected = real_entry["existing"].get("location", "")
        result = extract_location(real_entry["text"])

        if expected and "location" not in real_entry.get("needed", []):
            assert result == expected, (
                f"[page {real_entry['page_id']}] "
                f"Expected '{expected}', got '{result}'"
            )


class TestPublisherExtractionReal:
    def test_publisher(self, real_entry):
        expected = real_entry["existing"].get("publisher", "")
        result = extract_publisher(real_entry["text"])

        if expected and "publisher" not in real_entry.get("needed", []):
            assert result == expected, (
                f"[page {real_entry['page_id']}] "
                f"Expected '{expected}', got '{result}'"
            )


class TestTranslatorExtractionReal:
    def test_translator(self, real_entry):
        expected = real_entry["existing"].get("translator", "")
        result = extract_translator(real_entry["text"])

        if expected and "translator" not in real_entry.get("needed", []):
            assert result == expected, (
                f"[page {real_entry['page_id']}] "
                f"Expected '{expected}', got '{result}'"
            )


class TestPageCountExtractionReal:
    def test_page_count(self, real_entry):
        if real_entry["page_id"] in _SKIP_PAGE_COUNT:
            pytest.skip("page_count in fixture is a page range, not total count")

        expected = real_entry["existing"].get("page_count", "")
        result = extract_page_count(real_entry["text"])

        if expected and "page_count" not in real_entry.get("needed", []):
            assert result == int(expected), (
                f"[page {real_entry['page_id']}] "
                f"Expected {expected}, got {result}"
            )


class TestLanguageDetectionReal:
    def test_language(self, real_entry):
        if real_entry["page_id"] in _SKIP_LANGUAGE:
            pytest.skip("Truncated text doesn't contain expected language category")

        expected = real_entry["existing"].get("language", "")
        cats, _ = extract_categories(real_entry["text"])
        result = extract_language_from_category(cats)

        if expected:
            assert result == expected, (
                f"[page {real_entry['page_id']}] "
                f"Expected '{expected}', got '{result}'"
            )


class TestStructuredDataReal:
    def test_not_redirect(self, real_entry):
        data = extract_structured_data(real_entry["text"])
        assert data.get("is_redirect") is False

    def test_has_clean_content(self, real_entry):
        data = extract_structured_data(real_entry["text"])
        assert "clean_content" in data
        assert len(data["clean_content"]) > 0

    def test_categories_extracted(self, real_entry):
        data = extract_structured_data(real_entry["text"])
        if "[[Category:" in real_entry["text"]:
            assert "categories" in data
            assert len(data["categories"]) > 0
