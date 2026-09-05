"""Complete source fixtures, strict field diagnosis and exact regression checks.

The source expectations never contain parser output. Existing rule failures
are diagnosed under ``-m semantic`` and individually bounded in the default
suite; missing source fields are asserted as None in both layers.
"""

import hashlib
import warnings
from pathlib import Path

import pytest
from lib.patterns import (
    extract_language_from_category,
    extract_location,
    extract_page_count,
    extract_publisher,
    extract_translator,
)
from lib.wiki_parser import extract_structured_data

FIELDS = ("publisher", "location", "translator", "page_count", "language")


@pytest.fixture(scope="module")
def extracted_sample(real_entries):
    results = {}
    for entry in real_entries:
        text = entry["text"]
        structured = extract_structured_data(text)
        results[entry["page_id"]] = {
            "structured": structured,
            "publisher": extract_publisher(text),
            "location": extract_location(text),
            "translator": extract_translator(text),
            "page_count": extract_page_count(text),
            "language": extract_language_from_category(structured["categories"]),
        }
    return results


@pytest.fixture(scope="module")
def known_extraction_mismatches(extraction_baseline):
    records = extraction_baseline["knownMismatches"]
    known = {(r["pageId"], r["field"]): r["actual"] for r in records}
    assert len(known) == len(records), "Duplicate extraction baseline cases"
    return known


def test_extraction_baseline_covers_only_reviewed_cases(
    real_entries, known_extraction_mismatches, extraction_baseline
):
    fixture_path = Path(__file__).with_name("test_sample_20.json")
    assert (
        hashlib.sha256(fixture_path.read_bytes()).hexdigest()
        == extraction_baseline["groundTruthSha256"]
    ), "Changed source expectations require a reviewed baseline update"
    ids = [entry["page_id"] for entry in real_entries]
    assert len(ids) == len(set(ids)) == 20
    cases = {(pid, field) for pid in ids for field in FIELDS}
    assert known_extraction_mismatches.keys() <= cases
    expected = {
        (entry["page_id"], field): value
        for entry in real_entries
        for field, value in entry["expected"].items()
    }
    assert all(
        expected[key] != value for key, value in known_extraction_mismatches.items()
    )


def test_fixture_evidence_and_complete_field_expectations(real_entry):
    text = real_entry["text"]
    assert (
        hashlib.sha256(text.encode("utf-8")).hexdigest()
        == real_entry["source"]["textSha256"]
    )
    assert set(real_entry["expected"]) == set(FIELDS)
    assert set(real_entry["evidence"]) == set(FIELDS)
    assert real_entry["notes"]
    for field, expected in real_entry["expected"].items():
        selector = real_entry["evidence"][field]
        if expected is None:
            assert selector is None
            continue
        start, end = selector["start"], selector["end"]
        assert 0 <= start < end <= len(text)
        assert text[start:end] == selector["exact"]
        assert str(expected) in selector["exact"]
        if field == "language":
            assert selector["exact"].startswith("[[Category:")


@pytest.mark.parametrize("field", FIELDS)
def test_reviewed_field_has_no_new_regression(
    real_entry, extracted_sample, known_extraction_mismatches, field
):
    pid = real_entry["page_id"]
    expected = real_entry["expected"][field]
    actual = extracted_sample[pid][field]
    key = (pid, field)
    if actual == expected:
        if key in known_extraction_mismatches:
            warnings.warn(
                f"Extraction case {key} resolved; review and remove it from "
                "extraction-baseline.json.",
                stacklevel=2,
            )
        return
    assert (
        key in known_extraction_mismatches
        and actual == known_extraction_mismatches[key]
    ), (
        f"New or changed extraction failure on page {pid}, {field}: "
        f"expected {expected!r}, actual {actual!r}. {real_entry['notes']}"
    )


@pytest.mark.semantic
@pytest.mark.parametrize("field", FIELDS)
def test_extracted_field_matches_reviewed_source(real_entry, extracted_sample, field):
    pid = real_entry["page_id"]
    expected = real_entry["expected"][field]
    actual = extracted_sample[pid][field]
    assert actual == expected, (
        f"page {pid} ({real_entry['page_title']}), {field}: "
        f"expected {expected!r}, actual {actual!r}. {real_entry['notes']}"
    )


def test_complete_entry_structure(real_entry, extracted_sample):
    data = extracted_sample[real_entry["page_id"]]["structured"]
    assert data.get("is_redirect") is False
    assert data["clean_content"].strip()
    assert data["categories"]


@pytest.mark.parametrize("page_id,actual", [(2, 425), (1, 426)])
def test_extraction_guard_rejects_replacement_failures(page_id, actual):
    with pytest.raises(AssertionError, match="New or changed extraction failure"):
        test_reviewed_field_has_no_new_regression(
            {"page_id": page_id, "expected": {"page_count": None}, "notes": "Locator"},
            {page_id: {"page_count": actual}},
            {(1, "page_count"): 425},
            "page_count",
        )
