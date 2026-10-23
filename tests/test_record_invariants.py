"""Record-level invariants over the published data.

Each test states a property every published record must have. Known
exceptions are page-id allowlists, each with the reason the source gives;
a new violation fails, and a fixed case fails too until its id leaves the
list, so an allowlist can only shrink by review.
"""

from __future__ import annotations

import importlib
import json
import re
from functools import cache
from pathlib import Path

import pytest
from lib.config import SQL_DUMP_PATH
from lib.encoding import value_in_content
from lib.llm_extract import occurs_in_source, page_count_in_source
from lib.patterns import ABSENCE_MARKS, publisher_shape_ok
from lib.wiki_parser import (
    _LANGUAGE_HEAD,
    _TRANSLATIONS_HEAD,
    _wiki_section,
    remove_wiki_markup,
)

PROJECT_ROOT = Path(__file__).parent.parent
PUBLICATIONS_DIR = PROJECT_ROOT / "docs" / "data" / "publications"
LOCATION_NORMALIZE = PROJECT_ROOT / "pipeline" / "data" / "location_normalize.json"

# Zweig's first publications appeared in 1897/1898; a flat year before that is
# a date the text mentions, not the year of the publication the page records.
EARLIEST_PUBLICATION_YEAR = 1897


@cache
def _publication_layers() -> dict[int, dict]:
    layers = {}
    for path in PUBLICATIONS_DIR.glob("*.json"):
        document = json.loads(path.read_text(encoding="utf-8"))
        layers[document["sourcePageId"]] = document
    return layers


@pytest.fixture(scope="module")
def publication_layers():
    return _publication_layers()


def _check_allowlist(violations: dict[int, str], allowlist: dict[int, str]) -> None:
    """Violations must equal the allowlist: no new case, no stale entry."""
    new = {pid: detail for pid, detail in violations.items() if pid not in allowlist}
    stale = sorted(set(allowlist) - set(violations))
    assert not new, f"New violations: {dict(sorted(new.items()))}"
    assert not stale, f"Fixed cases still allowlisted, remove them: {stale}"


# (a) Every model value occurs in its source.

LLM_OCCURRENCE_ALLOWLIST: dict[int, str] = {}


def test_every_llm_value_occurs_whole_word_in_its_source(ns0_entries):
    violations = {}
    for entry in ns0_entries:
        provenance = entry.get("_provenance") or {}
        source = entry.get("fullBibliographicEntry", "")
        for field in ("publisher", "location", "translator"):
            value = entry.get(field)
            if provenance.get(field) == "llm" and value:
                if not occurs_in_source(value, source):
                    violations[entry["sourcePageId"]] = f"{field}={value!r}"
        count = entry.get("pageCount")
        if provenance.get("pageCount") == "llm" and count:
            if not page_count_in_source(count, source):
                violations[entry["sourcePageId"]] = f"pageCount={count!r}"
    _check_allowlist(violations, LLM_OCCURRENCE_ALLOWLIST)


# (b) The flat fields describe the first publication where a layer exists.

# 03c rejects an extent above 2000 pages or one that reads as a year; the flat
# field is then empty although the publication states the notation.
_MAX_PLAUSIBLE_PAGE_COUNT = 2000
_YEAR_LIKE = range(1800, 2031)

FLAT_PUBLICATION_ALLOWLIST: dict[int, str] = {}


def _expected_flat(first: dict) -> dict:
    numbered = (first.get("extent") or {}).get("numbered")
    if numbered and (numbered > _MAX_PLAUSIBLE_PAGE_COUNT or numbered in _YEAR_LIKE):
        numbered = None
    publisher = first.get("publisher") if first.get("places") else None
    if first.get("places") and not publisher:
        mark = " ".join((first.get("imprint") or "").split(",")[0].split())
        publisher = mark if mark in ABSENCE_MARKS else None
    return {"year": first.get("year"), "pageCount": numbered, "publisher": publisher}


def test_flat_fields_belong_to_the_first_publication(ns0_entries, publication_layers):
    violations = {}
    for entry in ns0_entries:
        layer = publication_layers.get(entry["sourcePageId"])
        if not layer or not layer["publications"]:
            continue
        expected = _expected_flat(layer["publications"][0])
        for field, value in expected.items():
            if entry.get(field) != value:
                violations[entry["sourcePageId"]] = (
                    f"{field}: flat {entry.get(field)!r}, first publication {value!r}"
                )
    _check_allowlist(violations, FLAT_PUBLICATION_ALLOWLIST)


# (c) A flat publisher has the shape of a name.

# Header imprints in the source's own wording; the rules read them from the
# publication header, not from prose.
PUBLISHER_SHAPE_ALLOWLIST: dict[int, str] = {
    153: "header imprint 'Im Verlag der Internationalen Stefan-Zweig-Gesellschaft'",
    257: "header imprint 'Im Verlag der Internationalen Stefan-Zweig-Gesellschaft'",
    268: "header imprint 'Im Bertelsmann Lesering', the book club's own wording",
    3317: "header imprint 'zweigheft 06', the periodical's lowercase name",
    3568: "header imprint 'marixverlag', the publisher's lowercase name",
    6830: "header imprint 'ibidem-Verlag', the publisher's lowercase name",
}


def test_flat_publisher_has_the_shape_of_a_name(ns0_entries):
    violations = {
        entry["sourcePageId"]: entry["publisher"]
        for entry in ns0_entries
        if entry.get("publisher")
        and entry["publisher"] not in ABSENCE_MARKS
        and not publisher_shape_ok(entry["publisher"])
    }
    _check_allowlist(violations, PUBLISHER_SHAPE_ALLOWLIST)


# (d) A year lies between Zweig's first publication and the dump.


@pytest.fixture(scope="module")
def latest_revision_year() -> int:
    extract = importlib.import_module("01_extract")
    with open(SQL_DUMP_PATH, "rb") as handle:
        revisions = extract.load_revisions(handle.read().decode("latin-1"))
    return max(int(revision["timestamp"][:4]) for revision in revisions.values())


EARLY_YEAR_ALLOWLIST: dict[int, str] = {
    6416: "header 1857: the first edition of Les Fleurs du mal, the edition "
    "Zweig's Baudelaire translations quote; a publication year",
}
# The source announces the volumes of the Zsolnay edition of 2017-2023 before
# they appeared; the last revision of the dump is of 2021.
LATE_YEAR_ALLOWLIST: dict[int, str] = {
    40: "header [2017-2023] and 'Vol. VII [2023]' announce forthcoming volumes",
    6808: "header [2017-2023] and volumes dated 2022 and 2023 announced",
    6965: "'[Wien, 2017-2023]. 7 volumes' announces the forthcoming volumes",
}


def test_latest_revision_year_is_read_from_the_dump(latest_revision_year):
    assert latest_revision_year == 2021


def test_year_is_a_plausible_publication_year(ns0_entries, latest_revision_year):
    early, late = {}, {}
    for entry in ns0_entries:
        years = [entry["year"]] if entry.get("year") else []
        years += entry.get("allYears") or []
        if entry.get("year") and entry["year"] < EARLIEST_PUBLICATION_YEAR:
            early[entry["sourcePageId"]] = entry["year"]
        beyond = [year for year in years if year > latest_revision_year]
        if beyond:
            late[entry["sourcePageId"]] = beyond
    _check_allowlist(early, EARLY_YEAR_ALLOWLIST)
    _check_allowlist(late, LATE_YEAR_ALLOWLIST)


# (e) Every language heading of a translations block yields its items.

TRANSLATIONS_ALLOWLIST: dict[int, str] = {}

_HEADING_RE = re.compile(rf"(?m)^'''{_LANGUAGE_HEAD}")


def test_translations_cover_every_language_heading(source_rows, ns0_by_id):
    violations = {}
    for row in source_rows:
        entry = ns0_by_id.get(int(row["page_id"]))
        if entry is None:
            continue
        block = _wiki_section(row["content"], _TRANSLATIONS_HEAD, _LANGUAGE_HEAD)
        if not block:
            continue
        headings = len(_HEADING_RE.findall(block.group(1)))
        items = len(entry.get("translations") or [])
        if headings > items:
            violations[entry["sourcePageId"]] = f"{headings} headings, {items} items"
    _check_allowlist(violations, TRANSLATIONS_ALLOWLIST)


# Source fidelity: a rule-read value is in the source, and no escape survives.


@cache
def _normalized_variants() -> dict[str, set[str]]:
    """Canonical place -> the source spellings the mapping table folds into it."""
    variants: dict[str, set[str]] = {}
    for spelling, canonical in json.loads(
        LOCATION_NORMALIZE.read_text(encoding="utf-8")
    ).items():
        variants.setdefault(canonical, set()).add(spelling)
    return variants


ROUND_TRIP_ALLOWLIST: dict[int, str] = {}


def test_rule_read_values_occur_in_the_dump_text(source_rows, ns0_by_id):
    """The documented normalisations are the comparison of value_in_content
    (whitespace, case, quote folding, the encoding repair table), the wiki
    markup the extractors strip, and the place table of 03c."""
    violations = {}
    for row in source_rows:
        entry = ns0_by_id.get(int(row["page_id"]))
        if entry is None:
            continue
        provenance = entry.get("_provenance") or {}
        texts = (row["content"], remove_wiki_markup(row["content"]))
        for field in ("publisher", "location", "translator", "originalTitle"):
            value = entry.get(field)
            if not value or provenance.get(field, "regex") != "regex":
                continue
            spellings = {value}
            if field == "location":
                spellings |= _normalized_variants().get(value, set())
            if not any(value_in_content(s, t) for s in spellings for t in texts):
                violations[entry["sourcePageId"]] = f"{field}={value!r}"
    _check_allowlist(violations, ROUND_TRIP_ALLOWLIST)


_ESCAPE_RE = re.compile(r'\\["\'\\]|\ufffd|[\x00-\x08\x0b\x0c\x0e-\x1f]')

ESCAPE_ALLOWLIST: dict[int, str] = {
    7432: "the delivered text itself ends in U+FFFD (bytes EF BF BD), a "
    "character the wiki had already lost",
}


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def test_no_published_string_carries_an_escape_or_a_lost_byte(
    frontend_data, publication_layers
):
    violations = {}
    for entry in frontend_data["entries"]:
        for text in _strings(entry):
            match = _ESCAPE_RE.search(text)
            if match:
                violations[entry["sourcePageId"]] = repr(match.group(0))
    for key, page_id in frontend_data["redirects"].items():
        match = _ESCAPE_RE.search(key)
        if match:
            violations[page_id] = f"redirect key {key!r}"
    for page_id, layer in publication_layers.items():
        for text in _strings(layer):
            match = _ESCAPE_RE.search(text)
            if match:
                violations[page_id] = repr(match.group(0))
    _check_allowlist(violations, ESCAPE_ALLOWLIST)
