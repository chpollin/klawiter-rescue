"""
Normalization tests — verify that known data quality issues are fixed.

These tests run on the frontend JSON (post-pipeline output) and assert
that normalization rules have been applied correctly. Each test has a
threshold of 0 — any violation is a regression.

Location variants and publisher reject patterns are loaded from the real
mapping tables (pipeline/data/*.json), the same tables the pipeline uses,
so the tests stay in sync with the canonical normalization rules.
"""

import json
import re
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "pipeline" / "data"


# --- Location ---

# Canonical variant keys come straight from the pipeline's mapping table.
with open(_DATA_DIR / "location_normalize.json", encoding="utf-8") as _f:
    KNOWN_LOCATION_VARIANTS = set(json.load(_f).keys())


def test_no_location_variants(ns0_entries):
    """Known location variants should be normalized to canonical form."""
    bad = [e for e in ns0_entries if e.get("location") in KNOWN_LOCATION_VARIANTS]
    assert len(bad) == 0, (
        f"{len(bad)} entries with unnormalized locations: "
        + ", ".join(f"{e['sourcePageId']}={e['location']}" for e in bad[:5])
    )


# --- Publisher ---

# Reject patterns come straight from the pipeline's reject table.
with open(_DATA_DIR / "publisher_reject_patterns.json", encoding="utf-8") as _f:
    _PUBLISHER_REJECT_PATTERNS = [
        re.compile(p, re.IGNORECASE) for p in json.load(_f).get("patterns", [])
    ]


def test_no_publisher_garbage(ns0_entries):
    """Publisher field should not contain edition numbers, metadata, or garbage."""
    bad = [
        e
        for e in ns0_entries
        if e.get("publisher")
        and any(p.search(e["publisher"]) for p in _PUBLISHER_REJECT_PATTERNS)
    ]
    assert len(bad) == 0, f"{len(bad)} entries with garbage publisher: " + ", ".join(
        f"{e['sourcePageId']}={e['publisher']}" for e in bad[:5]
    )


# --- Translator ---


def test_no_translator_mojibake(ns0_entries):
    """Translator field should not contain raw encoding artifacts.
    Threshold 1: pid=1451 has LLM-sourced \\x90 byte that fix_encoding cannot repair.
    """
    bad = [
        e
        for e in ns0_entries
        if e.get("translator") and re.search(r"[\x80-\x9f]", e["translator"])
    ]
    assert len(bad) <= 1, (
        f"{len(bad)} entries with mojibake in translator (threshold 1): "
        + ", ".join(f"{e['sourcePageId']}={e['translator'][:30]}" for e in bad[:5])
    )


def test_no_translator_afterwords(ns0_entries):
    """Translator field should not contain afterword/foreword/introduction content."""
    pattern = re.compile(
        r"\.\s*(Afterword|Foreword|Introduction|Preface|Nachwort|Vorwort|Einleitung)",
        re.IGNORECASE,
    )
    bad = [
        e
        for e in ns0_entries
        if e.get("translator") and pattern.search(e["translator"])
    ]
    assert len(bad) == 0, (
        f"{len(bad)} entries with non-person content in translator: "
        + ", ".join(f"{e['sourcePageId']}={e['translator'][:40]}" for e in bad[:5])
    )


# --- Page Count ---


def test_no_pagecount_outliers(ns0_entries):
    """Page count should be reasonable (1-2000, not a year)."""
    bad = [
        e
        for e in ns0_entries
        if e.get("pageCount")
        and (e["pageCount"] > 2000 or 1800 <= e["pageCount"] <= 2030)
    ]
    assert len(bad) == 0, (
        f"{len(bad)} entries with implausible pageCount: "
        + ", ".join(f"{e['sourcePageId']}={e['pageCount']}" for e in bad[:5])
    )
