"""
Heuristic semantic validators — catch known error patterns on ALL entries.

These tests don't require ground truth. They detect values that are structurally
valid but semantically suspicious: section headers as titles, years as page counts,
metadata text as publishers. Each test bounds the violation count; when extraction
bugs are fixed, the threshold is lowered to prevent regressions.

To run: pytest tests/test_heuristic.py -v
"""

import re

# --- Bounded thresholds ---
# Frozen issue counts live in .github/baseline-metrics.json (known_issues) and are
# read via the `baseline` fixture. Lower is better; update there when extraction
# improves. Keys used here:
#   section_header_titles      — wiki section headers as titles (812 → 0)
#   long_titles                — titles >200 chars, encoding-guard cases (387 → 43)
#   encoding_artifact_titles   — 0x80-0x9F bytes from broken page_titles (358 → 345)
#   publisher_wiki_markup      — publisher fields with '' markup (20 → 0)
#   publisher_metadata         — metadata phrases as publisher names (10 → 0)


# --- Patterns ---

SECTION_HEADER_RE = re.compile(
    r"^(Contents|Volumes|Vol\.\s*\d|German|Italian|French|English|Spanish|Russian|Chinese|"
    r"Japanese|Arabic|Hebrew|Portuguese|Dutch|Swedish|Norwegian|Danish|Finnish|"
    r"Polish|Czech|Hungarian|Romanian|Bulgarian|Croatian|Serbian|Turkish|Greek|"
    r"Albanian|Catalan|Korean|Slovenian|Slovak|Ukrainian|Georgian|Persian|"
    r"First printing|First edition|Reprinted in|See also|See:|Note:|Translations|"
    r"Manuscript|Reviews|Book editions|Excerpts|Fischer Editions/Reprints|"
    r"Collected Works / [A-Za-z]+):?\s*",
    re.IGNORECASE,
)

METADATA_PHRASES = [
    "comments concerning",
    "staff of the",
    "see also",
    "contents",
]


# --- Title heuristics ---


class TestTitleHeuristics:
    def test_section_header_titles_bounded(self, ns0_entries, baseline):
        """Titles should not be wiki section headers like 'Contents:' or 'German:'.
        Root cause: multi-edition pages where '''Contents:''' or '''German:''' is the
        first bold text, extracted as title by Pattern 1 in extract_title()."""
        known = baseline["known_issues"]["section_header_titles"]
        bad = [
            e
            for e in ns0_entries
            if e.get("title") and SECTION_HEADER_RE.match(e["title"])
        ]
        assert len(bad) <= known, (
            f"Section header titles: {len(bad)} (threshold {known}). "
            f"Examples: {[(e['sourcePageId'], e['title']) for e in bad[:5]]}"
        )

    def test_title_length_bounded(self, ns0_entries, baseline):
        """Titles over 200 chars are likely the full citation text, not a title.
        Root cause: escaped quotes in raw content prevent Pattern 2 match in
        extract_title(), falling back to Pattern 3 (entire first line)."""
        known = baseline["known_issues"]["long_titles"]
        long = [e for e in ns0_entries if e.get("title") and len(e["title"]) > 200]
        assert len(long) <= known, (
            f"Long titles (>200 chars): {len(long)} (threshold {known}). "
            f"Examples: {[(e['sourcePageId'], len(e['title'])) for e in long[:5]]}"
        )

    def test_no_encoding_artifacts_in_titles(self, ns0_entries, baseline):
        """Titles should not contain raw encoding artifacts (0x80-0x9F bytes).
        Root cause: page_title fallback for Arabic/Cyrillic transliterated titles
        where the page_title has mojibake from the MediaWiki database."""
        known = baseline["known_issues"]["encoding_artifact_titles"]
        bad = [
            e
            for e in ns0_entries
            if e.get("title") and re.search(r"[\x80-\x9f]", e["title"])
        ]
        assert len(bad) <= known, (
            f"Encoding artifacts in titles: {len(bad)} (threshold {known}). "
            f"Examples: {[(e['sourcePageId'], e['title'][:50]) for e in bad[:5]]}"
        )


# --- Publisher heuristics ---


class TestPublisherHeuristics:
    def test_publisher_no_wiki_markup(self, ns0_entries, baseline):
        """Publisher field should not contain wiki bold markers ('').
        Root cause: remove_wiki_markup() applied to titles but not consistently
        to publisher extraction in patterns.py."""
        known = baseline["known_issues"]["publisher_wiki_markup"]
        bad = [e for e in ns0_entries if e.get("publisher") and "''" in e["publisher"]]
        assert len(bad) <= known, (
            f"Publisher with markup: {len(bad)} (threshold {known}). "
            f"Examples: {[(e['sourcePageId'], e['publisher'][:60]) for e in bad[:5]]}"
        )

    def test_publisher_not_metadata(self, ns0_entries, baseline):
        """Publisher should not be metadata phrases like 'comments concerning this series'.
        Root cause: regex grabs text after location comma that happens to be
        editorial commentary rather than a publisher name."""
        known = baseline["known_issues"]["publisher_metadata"]
        bad = [
            e
            for e in ns0_entries
            if e.get("publisher")
            and any(p in e["publisher"].lower() for p in METADATA_PHRASES)
        ]
        assert len(bad) <= known, (
            f"Metadata as publisher: {len(bad)} (threshold {known}). "
            f"Examples: {[(e['sourcePageId'], e['publisher'][:60]) for e in bad[:5]]}"
        )
