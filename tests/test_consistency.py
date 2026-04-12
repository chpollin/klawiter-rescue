"""
Cross-field consistency tests — validate that fields make sense together.

These tests answer: "Does each record tell a coherent story?"
They test relationships BETWEEN fields, not individual field values.
Fixtures (ns0_entries, all_titles, redirect_targets) are defined in conftest.py.
"""

import pytest


# ---------------------------------------------------------------------------
# German entries should not have translators (with known exceptions)
# ---------------------------------------------------------------------------

class TestGermanTranslator:
    """German-language originals should not have a translator field.
    Exceptions: Collected works that include translations, or entries where
    the 'translator' field was incorrectly extracted (false positives)."""

    # Current known FP count — update when pipeline improves
    KNOWN_GERMAN_TRANSLATOR_FP = 111

    def test_german_translator_false_positives_bounded(self, ns0_entries):
        """Count of German entries with translator must not increase."""
        german_with_translator = [
            (e["sourcePageId"], e.get("translator"), str(e.get("title", ""))[:50])
            for e in ns0_entries
            if e.get("language") == "German" and e.get("translator")
        ]
        assert len(german_with_translator) <= self.KNOWN_GERMAN_TRANSLATOR_FP, (
            f"German entries with translator increased from "
            f"{self.KNOWN_GERMAN_TRANSLATOR_FP} to {len(german_with_translator)}. "
            f"New cases:\n"
            + "\n".join(
                f"  page {pid}: translator='{tr}', title='{t}'"
                for pid, tr, t in german_with_translator[:10]
            )
        )
        if german_with_translator and len(german_with_translator) < self.KNOWN_GERMAN_TRANSLATOR_FP:
            import warnings
            warnings.warn(
                f"German translator FPs decreased from {self.KNOWN_GERMAN_TRANSLATOR_FP} "
                f"to {len(german_with_translator)} — update KNOWN_GERMAN_TRANSLATOR_FP",
                UserWarning, stacklevel=1,
            )


# ---------------------------------------------------------------------------
# Films should not have page counts (with exceptions for screenplays)
# ---------------------------------------------------------------------------

class TestFilmPageCount:
    """Film entries typically don't have page counts. Screenplays may be exceptions."""

    KNOWN_FILM_PAGECOUNT = 10

    def test_film_pagecount_bounded(self, ns0_entries):
        """Count of film entries with pageCount must not increase."""
        films_with_pages = [
            (e["sourcePageId"], e.get("pageCount"), str(e.get("title", ""))[:50])
            for e in ns0_entries
            if e.get("entryType") == "film" and e.get("pageCount")
        ]
        assert len(films_with_pages) <= self.KNOWN_FILM_PAGECOUNT, (
            f"Film entries with pageCount increased from "
            f"{self.KNOWN_FILM_PAGECOUNT} to {len(films_with_pages)}"
        )


# ---------------------------------------------------------------------------
# Publisher and location should not be identical
# ---------------------------------------------------------------------------

class TestPublisherLocationDistinct:
    """Publisher and location should be different values."""

    KNOWN_PUB_EQ_LOC = 1

    def test_publisher_not_equal_location(self, ns0_entries):
        """Publisher and location fields should not contain the same value."""
        same = [
            (e["sourcePageId"], e.get("publisher"))
            for e in ns0_entries
            if e.get("publisher") and e.get("location")
            and e["publisher"] == e["location"]
        ]
        assert len(same) <= self.KNOWN_PUB_EQ_LOC, (
            f"Publisher == Location increased from {self.KNOWN_PUB_EQ_LOC} "
            f"to {len(same)}: {same[:10]}"
        )


# ---------------------------------------------------------------------------
# Year and timePeriod must be consistent
# ---------------------------------------------------------------------------

class TestYearPeriodConsistency:
    """The timePeriod classification must match the year."""

    PERIOD_RANGES = {
        "pre-zweig": (None, 1880),
        "lifetime": (1881, 1942),
        "post-wwii": (1943, 1980),
        "late-20c": (1981, 2000),
        "contemporary": (2001, None),
    }

    def test_year_matches_period(self, ns0_entries):
        """Every entry with both year and timePeriod has a consistent pair."""
        inconsistent = []
        for entry in ns0_entries:
            year = entry.get("year")
            period = entry.get("timePeriod")
            if year is None or period is None:
                continue
            if period not in self.PERIOD_RANGES:
                inconsistent.append(
                    (entry["sourcePageId"], year, period, "unknown period")
                )
                continue
            lo, hi = self.PERIOD_RANGES[period]
            if lo is not None and year < lo:
                inconsistent.append(
                    (entry["sourcePageId"], year, period,
                     f"year {year} < {lo}")
                )
            if hi is not None and year > hi:
                inconsistent.append(
                    (entry["sourcePageId"], year, period,
                     f"year {year} > {hi}")
                )

        assert len(inconsistent) == 0, (
            f"{len(inconsistent)} entries have year/period mismatch:\n"
            + "\n".join(
                f"  page {pid}: year={y}, period={p} ({reason})"
                for pid, y, p, reason in inconsistent[:20]
            )
        )


# ---------------------------------------------------------------------------
# seeAlso referential integrity
# ---------------------------------------------------------------------------

class TestSeeAlsoIntegrity:
    """Cross-references should point to entries that exist."""

    # Known count of broken references — high due to formatted reference strings
    # like "Clarissa (IS) / Spanish" that include language suffixes
    KNOWN_BROKEN_REFS = 1140

    def test_broken_references_bounded(self, ns0_entries, all_titles, redirect_targets):
        """Count of broken seeAlso references must not increase."""
        broken = []
        for entry in ns0_entries:
            for ref in (entry.get("seeAlso") or []):
                if ref not in all_titles and ref not in redirect_targets:
                    broken.append((entry["sourcePageId"], ref))

        assert len(broken) <= self.KNOWN_BROKEN_REFS, (
            f"Broken seeAlso references increased from {self.KNOWN_BROKEN_REFS} "
            f"to {len(broken)}. Sample:\n"
            + "\n".join(
                f"  page {pid} → '{ref}'"
                for pid, ref in broken[:10]
            )
        )
        if broken and len(broken) < self.KNOWN_BROKEN_REFS:
            import warnings
            warnings.warn(
                f"Broken seeAlso references decreased from {self.KNOWN_BROKEN_REFS} "
                f"to {len(broken)} — update KNOWN_BROKEN_REFS",
                UserWarning, stacklevel=1,
            )

    def test_see_also_not_self_referencing(self, ns0_entries):
        """No entry references itself."""
        self_refs = [
            (e["sourcePageId"], e.get("title"))
            for e in ns0_entries
            if e.get("seeAlso") and e.get("title") in (e.get("seeAlso") or [])
        ]
        assert len(self_refs) == 0, (
            f"{len(self_refs)} entries reference themselves: {self_refs[:10]}"
        )
