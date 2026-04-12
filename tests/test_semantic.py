"""
Semantic accuracy tests — compare pipeline output against wiki-verified ground truth.

Each entry in wiki_ground_truth.json was manually checked against the live wiki at
klawiter.stefanzweig.digital. Tests verify that the pipeline extracts the correct
values, not just structurally valid ones.

To run: pytest tests/test_semantic.py -v
"""

import pytest


def _find_entry(ns0_entries, page_id):
    """Find entry by page_id in ns0 entries."""
    for e in ns0_entries:
        if e.get("sourcePageId") == page_id:
            return e
    return None


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
