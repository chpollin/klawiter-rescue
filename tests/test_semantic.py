"""
Semantic accuracy tests — compare pipeline output against wiki-verified ground truth.

Each entry in wiki_ground_truth.json was manually checked against the live wiki at
klawiter.stefanzweig.digital. Tests verify that the pipeline extracts the correct
values, not just structurally valid ones.

The per-field tests are red by design: they document the known fidelity gap
(mostly multi-edition pages, see knowledge/testing.md category F) and are
deselected by default. Run them with: pytest -m semantic
The unmarked bounded test below runs in the default suite and fails only when
the published dataset gets semantically worse than the frozen state.
"""

import json
import warnings
from pathlib import Path

import pytest

_GROUND_TRUTH_PATH = Path(__file__).parent / "wiki_ground_truth.json"
_FIELDS = ("title", "year", "publisher", "location", "language", "translator", "pageCount")


def _find_entry(ns0_entries, page_id):
    """Find entry by page_id in ns0 entries."""
    for e in ns0_entries:
        if e.get("sourcePageId") == page_id:
            return e
    return None


def _field_ok(field, expected, entry):
    """Mirror the per-field comparison semantics of the tests below."""
    if field == "title":
        actual = entry.get("title", "")
        if expected is None:
            return not actual
        return actual == expected or actual.startswith(expected)
    if field in ("year", "pageCount"):
        return entry.get(field) == expected
    return (entry.get(field) or None) == expected


def _mismatches(wiki_entries, ns0_entries):
    bad = []
    for w in wiki_entries:
        entry = _find_entry(ns0_entries, w["page_id"])
        if entry is None:
            bad.extend((w["page_id"], f) for f in _FIELDS)
            continue
        bad.extend((w["page_id"], f) for f in _FIELDS
                   if not _field_ok(f, w["expected"][f], entry))
    return bad


def test_ground_truth_mismatches_bounded(ns0_entries, baseline):
    """Regression bound for the semantic fidelity gap.

    The marked per-field tests are opt-in diagnosis; this bound keeps the
    default suite green while catching a dataset that got worse. Lower is
    better — when the work/edition model lands, ratchet the baseline down.
    """
    if not _GROUND_TRUTH_PATH.exists():
        pytest.skip("wiki_ground_truth.json not found")
    with open(_GROUND_TRUTH_PATH, encoding="utf-8") as f:
        wiki_entries = json.load(f)
    limit = baseline["known_issues"]["semantic_field_mismatches"]
    bad = _mismatches(wiki_entries, ns0_entries)
    assert len(bad) <= limit, (
        f"Semantic mismatches vs wiki ground truth grew: {len(bad)} > {limit}\n"
        f"{sorted(bad)}"
    )
    if len(bad) < limit:
        warnings.warn(
            f"Semantic mismatches improved to {len(bad)} — lower "
            f"known_issues.semantic_field_mismatches in baseline-metrics.json"
        )


def _msg(wiki_entry, field, expected, actual):
    """Build a clear assertion message."""
    pid = wiki_entry["page_id"]
    title = wiki_entry["page_title"]
    notes = wiki_entry.get("notes", "")
    return (
        f"\npid={pid} ({title}): {field}\n"
        f"  expected: {expected!r}\n"
        f"  actual:   {actual!r}\n"
        f"  notes:    {notes}"
    )


@pytest.mark.semantic
class TestSemanticAccuracy:
    """Compare pipeline output against wiki-verified ground truth."""

    def test_title(self, wiki_entry, ns0_entries):
        entry = _find_entry(ns0_entries, wiki_entry["page_id"])
        assert entry is not None, f"Entry {wiki_entry['page_id']} not found"
        expected = wiki_entry["expected"]["title"]
        actual = entry.get("title", "")
        if expected is None:
            assert not actual, _msg(wiki_entry, "title", None, actual)
        else:
            # Title should match or start with expected (some titles are legitimately longer)
            assert actual.startswith(expected) or actual == expected, \
                _msg(wiki_entry, "title", expected, actual)

    def test_year(self, wiki_entry, ns0_entries):
        entry = _find_entry(ns0_entries, wiki_entry["page_id"])
        assert entry is not None
        expected = wiki_entry["expected"]["year"]
        actual = entry.get("year")
        if expected is None:
            assert actual is None, _msg(wiki_entry, "year", None, actual)
        else:
            assert actual == expected, _msg(wiki_entry, "year", expected, actual)

    def test_publisher(self, wiki_entry, ns0_entries):
        entry = _find_entry(ns0_entries, wiki_entry["page_id"])
        assert entry is not None
        expected = wiki_entry["expected"]["publisher"]
        actual = entry.get("publisher") or None
        if expected is None:
            assert actual is None, _msg(wiki_entry, "publisher", None, actual)
        else:
            assert actual == expected, _msg(wiki_entry, "publisher", expected, actual)

    def test_location(self, wiki_entry, ns0_entries):
        entry = _find_entry(ns0_entries, wiki_entry["page_id"])
        assert entry is not None
        expected = wiki_entry["expected"]["location"]
        actual = entry.get("location") or None
        if expected is None:
            assert actual is None, _msg(wiki_entry, "location", None, actual)
        else:
            assert actual == expected, _msg(wiki_entry, "location", expected, actual)

    def test_language(self, wiki_entry, ns0_entries):
        entry = _find_entry(ns0_entries, wiki_entry["page_id"])
        assert entry is not None
        expected = wiki_entry["expected"]["language"]
        actual = entry.get("language") or None
        if expected is None:
            assert actual is None, _msg(wiki_entry, "language", None, actual)
        else:
            assert actual == expected, _msg(wiki_entry, "language", expected, actual)

    def test_translator(self, wiki_entry, ns0_entries):
        entry = _find_entry(ns0_entries, wiki_entry["page_id"])
        assert entry is not None
        expected = wiki_entry["expected"]["translator"]
        actual = entry.get("translator") or None
        if expected is None:
            assert actual is None, _msg(wiki_entry, "translator", None, actual)
        else:
            assert actual == expected, _msg(wiki_entry, "translator", expected, actual)

    def test_page_count(self, wiki_entry, ns0_entries):
        entry = _find_entry(ns0_entries, wiki_entry["page_id"])
        assert entry is not None
        expected = wiki_entry["expected"]["pageCount"]
        actual = entry.get("pageCount")
        if expected is None:
            assert actual is None, _msg(wiki_entry, "pageCount", None, actual)
        else:
            assert actual == expected, _msg(wiki_entry, "pageCount", expected, actual)
