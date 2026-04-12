"""
Heuristic semantic validators — catch known error patterns on ALL entries.

These tests don't require ground truth. They detect values that are structurally
valid but semantically suspicious: section headers as titles, years as page counts,
metadata text as publishers. Each test bounds the violation count; when extraction
bugs are fixed, the threshold is lowered to prevent regressions.

To run: pytest tests/test_heuristic.py -v
"""

import re

import pytest

# --- Bounded thresholds (lower = better; update when extraction improves) ---

# Titles that are wiki section headers like "Contents:", "Volumes:", "German:"
# Fixed in Session 14: section headers rejected, fallback to page_title (812 → 0)
KNOWN_SECTION_HEADER_TITLES = 0

# Titles longer than 200 characters (likely full citation text, not a title)
# Fixed in Session 14: long titles rejected, fallback to page_title (387 → 0)
KNOWN_LONG_TITLES = 0

# PageCount values that look like years (1800-2030)
# Reduced by parenthesized lookahead fix and N/(M)p. pattern (27 → 11)
KNOWN_YEAR_AS_PAGECOUNT = 11

# Publisher fields containing wiki markup ('')
# Fixed in Session 14: wiki markup stripped from publisher (20 → 0)
KNOWN_PUBLISHER_MARKUP = 0

# Publisher fields containing metadata phrases instead of publisher names
# Fixed in Session 14: metadata phrases rejected (10 → 0)
KNOWN_PUBLISHER_METADATA = 0


# --- Patterns ---

SECTION_HEADER_RE = re.compile(
    r'^(Contents|Volumes|German|Italian|French|English|Spanish|Russian|Chinese|'
    r'Japanese|Arabic|Hebrew|Portuguese|Dutch|Swedish|Norwegian|Danish|Finnish|'
    r'Polish|Czech|Hungarian|Romanian|Bulgarian|Croatian|Serbian|Turkish|Greek|'
    r'Albanian|Catalan|Korean|Slovenian|Slovak|Ukrainian|Georgian|Persian|'
    r'First printing|First edition|Reprinted in|See also|Translations|'
    r'Manuscript|Reviews|Book editions|Excerpts):?\s*$',
    re.IGNORECASE
)

METADATA_PHRASES = [
    'comments concerning',
    'staff of the',
    'see also',
    'contents',
]


# --- Title heuristics ---

class TestTitleHeuristics:

    def test_section_header_titles_bounded(self, ns0_entries):
        """Titles should not be wiki section headers like 'Contents:' or 'German:'.
        Root cause: multi-edition pages where '''Contents:''' or '''German:''' is the
        first bold text, extracted as title by Pattern 1 in extract_title()."""
        bad = [e for e in ns0_entries
               if e.get('title') and SECTION_HEADER_RE.match(e['title'])]
        assert len(bad) <= KNOWN_SECTION_HEADER_TITLES, (
            f"Section header titles: {len(bad)} (threshold {KNOWN_SECTION_HEADER_TITLES}). "
            f"Examples: {[(e['sourcePageId'], e['title']) for e in bad[:5]]}"
        )

    def test_title_length_bounded(self, ns0_entries):
        """Titles over 200 chars are likely the full citation text, not a title.
        Root cause: escaped quotes in raw content prevent Pattern 2 match in
        extract_title(), falling back to Pattern 3 (entire first line)."""
        long = [e for e in ns0_entries
                if e.get('title') and len(e['title']) > 200]
        assert len(long) <= KNOWN_LONG_TITLES, (
            f"Long titles (>200 chars): {len(long)} (threshold {KNOWN_LONG_TITLES}). "
            f"Examples: {[(e['sourcePageId'], len(e['title'])) for e in long[:5]]}"
        )


# --- PageCount heuristics ---

class TestPageCountHeuristics:

    def test_pagecount_not_a_year(self, ns0_entries):
        """PageCount values 1800-2030 are likely years, not page counts.
        Root cause: regex extracts '1948' from '252/(2)p. 1948' where 1948
        is the edition year, not the page count."""
        bad = [e for e in ns0_entries
               if e.get('pageCount') and 1800 <= e['pageCount'] <= 2030]
        assert len(bad) <= KNOWN_YEAR_AS_PAGECOUNT, (
            f"Year-like pageCount: {len(bad)} (threshold {KNOWN_YEAR_AS_PAGECOUNT}). "
            f"Examples: {[(e['sourcePageId'], e['pageCount']) for e in bad[:5]]}"
        )


# --- Publisher heuristics ---

class TestPublisherHeuristics:

    def test_publisher_no_wiki_markup(self, ns0_entries):
        """Publisher field should not contain wiki bold markers ('').
        Root cause: remove_wiki_markup() applied to titles but not consistently
        to publisher extraction in patterns.py."""
        bad = [e for e in ns0_entries
               if e.get('publisher') and "''" in e['publisher']]
        assert len(bad) <= KNOWN_PUBLISHER_MARKUP, (
            f"Publisher with markup: {len(bad)} (threshold {KNOWN_PUBLISHER_MARKUP}). "
            f"Examples: {[(e['sourcePageId'], e['publisher'][:60]) for e in bad[:5]]}"
        )

    def test_publisher_not_metadata(self, ns0_entries):
        """Publisher should not be metadata phrases like 'comments concerning this series'.
        Root cause: regex grabs text after location comma that happens to be
        editorial commentary rather than a publisher name."""
        bad = [e for e in ns0_entries
               if e.get('publisher') and
               any(p in e['publisher'].lower() for p in METADATA_PHRASES)]
        assert len(bad) <= KNOWN_PUBLISHER_METADATA, (
            f"Metadata as publisher: {len(bad)} (threshold {KNOWN_PUBLISHER_METADATA}). "
            f"Examples: {[(e['sourcePageId'], e['publisher'][:60]) for e in bad[:5]]}"
        )
