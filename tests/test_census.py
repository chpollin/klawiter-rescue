"""
Census tests — verify completeness of the pipeline output.

These tests answer: "Do we have all the data?"
They run against the actual output files, not against extraction functions.
Fixtures (frontend_data, all_entries, ns0_entries, redirects, baseline)
are defined in conftest.py and shared across all data test files.
"""


# ---------------------------------------------------------------------------
# Entry count exactness
# ---------------------------------------------------------------------------


class TestEntryCounts:
    """Verify exact entry counts match baseline — not just loose minimums."""

    def test_total_entries_exact(self, all_entries, baseline):
        """Total entries within 0.5% of baseline (stricter than old 1% threshold)."""
        # Entries in frontend JSON = non-redirects only
        expected_non_redirects = baseline["summary"]["non_redirects_all"]
        actual = len(all_entries)
        assert actual == expected_non_redirects, (
            f"Expected {expected_non_redirects} entries, got {actual} "
            f"(delta: {actual - expected_non_redirects})"
        )

    def test_ns0_entries_exact(self, ns0_entries, baseline):
        """Main namespace entry count matches baseline exactly."""
        expected = baseline["summary"]["non_redirects_main"]
        actual = len(ns0_entries)
        assert actual == expected, (
            f"Expected {expected} ns-0 entries, got {actual} "
            f"(delta: {actual - expected})"
        )

    def test_redirect_count_stable(self, redirects, baseline):
        """Redirect map has a stable count.

        Note: baseline counts ALL redirects (1546 = total - non-redirects),
        but the frontend JSON redirect map only stores redirect page titles
        that resolve to actual entries. The map is a subset.
        """
        # The frozen reference is ratcheted after intentional title repairs.
        expected = baseline["known_issues"]["redirect_map_size"]
        actual = len(redirects)
        assert actual == expected, (
            f"Expected {expected} redirect map entries, got {actual} "
            f"(delta: {actual - expected})"
        )


# ---------------------------------------------------------------------------
# No duplicate records
# ---------------------------------------------------------------------------


class TestNoDuplicates:
    """Every entry must appear exactly once."""

    def test_no_duplicate_page_ids(self, all_entries):
        """No two entries share the same sourcePageId."""
        page_ids = [e["sourcePageId"] for e in all_entries]
        seen = set()
        duplicates = []
        for pid in page_ids:
            if pid in seen:
                duplicates.append(pid)
            seen.add(pid)
        assert len(duplicates) == 0, (
            f"Found {len(duplicates)} duplicate page_ids: {duplicates[:20]}"
        )

    def test_no_duplicate_ids(self, all_entries):
        """No two entries share the same @id."""
        ids = [e["@id"] for e in all_entries]
        seen = set()
        duplicates = []
        for eid in ids:
            if eid in seen:
                duplicates.append(eid)
            seen.add(eid)
        assert len(duplicates) == 0, (
            f"Found {len(duplicates)} duplicate @ids: {duplicates[:20]}"
        )


# ---------------------------------------------------------------------------
# Known gaps are explicit — no silent data loss
# ---------------------------------------------------------------------------


class TestKnownGaps:
    """Document known missing entries explicitly so new gaps are detectable."""

    # page_id 2979: "A unidade espiritual do mundo" — text_id 18046 not in BLOBs.
    # Decision (2026-06-21): the blanked page is shown with its page-title fallback
    # rather than hidden, so it carries a title but no extractable bibliographic
    # content (no fullBibliographicEntry, publisher, location, year).
    KNOWN_STUB_PAGE_IDS = {2979}

    def test_known_stub_has_fallback_title_but_no_content(self, all_entries):
        """Page 2979 is a content stub: the page-title fallback gives it a title,
        but no bibliographic content was recoverable from the BLOBs."""
        stubs = [
            e for e in all_entries if e["sourcePageId"] in self.KNOWN_STUB_PAGE_IDS
        ]
        assert stubs, "KNOWN_STUB_PAGE_IDS entries not present in dataset"
        for stub in stubs:
            assert (stub.get("title") or "").strip(), (
                f"Stub page {stub['sourcePageId']} lost its page-title fallback; the "
                f"show-with-title decision is not reflected in the data."
            )
            assert not (stub.get("fullBibliographicEntry") or "").strip(), (
                f"Stub page {stub['sourcePageId']} now has bibliographic content — "
                f"content may have been recovered. Update KNOWN_STUB_PAGE_IDS."
            )

    # Note: a former `test_no_new_gaps_in_ns0` (ns-0 count >= baseline) was a strict
    # subset of TestEntryCounts.test_ns0_entries_exact (==, same value) and was removed.


# ---------------------------------------------------------------------------
# Every ns-0 entry has minimum required fields
# ---------------------------------------------------------------------------


class TestRequiredFields:
    """Every bibliography entry must have core identifying fields."""

    def test_every_entry_has_page_id(self, all_entries):
        """Every entry must have a sourcePageId."""
        missing = [i for i, e in enumerate(all_entries) if "sourcePageId" not in e]
        assert len(missing) == 0, (
            f"{len(missing)} entries missing sourcePageId (indices: {missing[:10]})"
        )

    def test_every_entry_has_type(self, all_entries):
        """Every entry must have an entryType."""
        missing = [
            e.get("sourcePageId", "?") for e in all_entries if not e.get("entryType")
        ]
        assert len(missing) == 0, (
            f"{len(missing)} entries missing entryType: {missing[:20]}"
        )

    def test_every_entry_has_ld_type(self, all_entries):
        """Every entry must have an @type array."""
        missing = [
            e.get("sourcePageId", "?") for e in all_entries if not e.get("@type")
        ]
        assert len(missing) == 0, (
            f"{len(missing)} entries missing @type: {missing[:20]}"
        )

    def test_every_entry_has_ld_id(self, all_entries):
        """Every entry must have an @id."""
        missing = [e.get("sourcePageId", "?") for e in all_entries if not e.get("@id")]
        assert len(missing) == 0, f"{len(missing)} entries missing @id: {missing[:20]}"

    def test_every_ns0_entry_has_title(self, ns0_entries):
        """Every ns-0 entry must have a title. The blanked stub 2979 is shown with
        its page-title fallback (decision 2026-06-21), so there are no exceptions."""
        missing = [
            e["sourcePageId"]
            for e in ns0_entries
            if not e.get("title") or str(e["title"]).strip() == ""
        ]
        assert len(missing) == 0, (
            f"{len(missing)} ns-0 entries missing title: {missing[:20]}"
        )


# ---------------------------------------------------------------------------
# Frontend JSON structural integrity
# ---------------------------------------------------------------------------


class TestFrontendStructure:
    """The frontend JSON has the expected top-level shape."""

    def test_has_metadata_fields(self, frontend_data):
        """Top-level metadata fields are present."""
        assert "name" in frontend_data
        assert "entries" in frontend_data
        assert "redirects" in frontend_data
        assert "totalEntries" in frontend_data
        assert "generated" not in frontend_data["_meta"]

    def test_total_entries_matches_array(self, frontend_data):
        """The totalEntries count matches the actual entries array length."""
        declared = frontend_data["totalEntries"]
        actual = len(frontend_data["entries"])
        assert declared == actual, (
            f"totalEntries says {declared} but entries array has {actual}"
        )
