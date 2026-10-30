"""Record-level invariants over the published data.

Each test states a property every published record must have. Known
exceptions are page-id allowlists, each with the reason the source gives;
a new violation fails, and a fixed case fails too until its id leaves the
list, so an allowlist can only shrink by review.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import re
from functools import cache
from pathlib import Path

import pytest
from lib.config import SQL_DUMP_PATH
from lib.encoding import unescape_dump_quotes, value_in_content
from lib.llm_extract import occurs_in_source, page_count_in_source
from lib.patterns import ABSENCE_MARKS, publisher_shape_ok
from lib.publications import unbound_flat_fields
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


def test_an_llm_label_names_the_value_the_frozen_cache_holds(frontend_data):
    """A value labelled llm is the value the frozen enrichment cache holds for
    that page and field, or its byte repair, which the record then flags as
    encoding-repaired. Occurrence in the source alone cannot tell a regex
    value relabelled llm from an enrichment value."""
    from inject_provenance import TRACKED_FIELDS, load_provenance_cache
    from lib.encoding import repair_value_encoding

    cache = load_provenance_cache("frozen")
    violations = {}
    for entry in frontend_data["entries"]:
        page_id = entry["sourcePageId"]
        repaired = {
            flag["field"]
            for flag in entry.get("reviewFlags", [])
            if flag["code"] == "encoding-repaired"
        }
        for field, label in (entry.get("_provenance") or {}).items():
            if label != "llm":
                continue
            held = cache.get(str(page_id), {}).get(TRACKED_FIELDS[field])
            value = str(entry.get(field))
            if held is None or (
                str(held) != value
                and (field not in repaired or repair_value_encoding(str(held)) != value)
            ):
                violations[page_id] = f"{field}={value!r}, cache {held!r}"
    _check_allowlist(violations, {})


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


# (f) On a page without a publication header, a rule-read place, publisher
# or translator stands in the first statement of the page, in a position a
# rule binds to the described publication; otherwise the field is a gap.

UNBOUND_FLAT_ALLOWLIST: dict[int, str] = {}


def test_headerless_flat_values_are_bound_to_the_first_statement(
    source_rows, ns0_by_id
):
    violations = {}
    for row in source_rows:
        entry = ns0_by_id.get(int(row["page_id"]))
        if entry is None or entry.get("publicationCount"):
            continue
        provenance = entry.get("_provenance") or {}
        for field in ("location", "publisher", "translator"):
            value = entry.get(field)
            if not value or provenance.get(field, "regex") != "regex":
                continue
            spellings = {value}
            if field == "location":
                spellings |= _normalized_variants().get(value, set())
            if all(
                unbound_flat_fields(row["content"], {field: spelling})
                for spelling in spellings
            ):
                violations[entry["sourcePageId"]] = f"{field}={value!r}"
    _check_allowlist(violations, UNBOUND_FLAT_ALLOWLIST)


# (g) Every structured translation statement is bound to its passage: each
# value is the text of its span, the span lies in the statement's source
# slice or its translation's head, and every language heading yields one.

TRANSLATION_STATEMENT_ALLOWLIST: dict[int, str] = {}


def test_translation_statements_are_bound_to_their_passages(source_rows, ns0_by_id):
    violations = {}
    for row in source_rows:
        entry = ns0_by_id.get(int(row["page_id"]))
        if entry is None:
            continue
        text = row["content"]
        statements = entry.get("translationStatements") or []
        block = _wiki_section(text, _TRANSLATIONS_HEAD, _LANGUAGE_HEAD)
        if block and not statements:
            violations[entry["sourcePageId"]] = "section without statements"
            continue
        headings = {
            remove_wiki_markup(match.group(0)).strip(" :'").split(" (")[0]
            for match in _HEADING_RE.finditer(block.group(1) if block else "")
        }
        read = {
            statement.get("language", "").split(" (")[0] for statement in statements
        }
        if headings - read:
            violations[entry["sourcePageId"]] = (
                f"headings without a statement {headings - read}"
            )
        for statement in statements:
            source_slice = statement["sourceSlice"]
            passage = text[source_slice["start"] : source_slice["end"]]
            if (
                hashlib.sha256(passage.encode("utf-8")).hexdigest()
                != source_slice["sha256"]
            ):
                violations[entry["sourcePageId"]] = "slice hash"
            for field, (start, end) in statement["spans"].items():
                value = " ".join(unescape_dump_quotes(text[start:end]).split())
                if field != "language" and str(statement[field]) != value:
                    violations[entry["sourcePageId"]] = f"{field}={statement[field]!r}"
    _check_allowlist(violations, TRANSLATION_STATEMENT_ALLOWLIST)


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


# (h) A value with a letter whose bytes were lost is a gap with a hint; a flat
# value carries no whitespace run; a field a rule emptied says so.

_FLAT_VALUE_KEYS = (
    "title",
    "originalTitle",
    "publisher",
    "location",
    "translator",
    "language",
    "allLocations",
    "translations",
    "contentItems",
    "reprints",
    "seeAlso",
)


def _flat_values(entry):
    for key in _FLAT_VALUE_KEYS:
        value = entry.get(key)
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, str):
                yield key, item


def test_no_published_value_keeps_a_damaged_letter(frontend_data, publication_layers):
    """Every string of every record and side file except the delivered source
    text, which is the source itself (page 7432 ends in U+FFFD there)."""
    from lib.encoding import has_damaged_letter

    violations = {}
    for entry in frontend_data["entries"]:
        for key, value in entry.items():
            if key == "fullBibliographicEntry":
                continue
            for text in _strings(value):
                if has_damaged_letter(text):
                    violations[entry["sourcePageId"]] = f"{key}={text!r}"
    for page_id, layer in publication_layers.items():
        for text in _strings(layer):
            if has_damaged_letter(text):
                violations[page_id] = repr(text)
    _check_allowlist(violations, {})


def _encoding_damage(text: str) -> bool:
    from lib.encoding import has_damaged_letter, has_mojibake

    return has_mojibake(text) or has_damaged_letter(text)


def _texts(value):
    """Every string of a JSON value, dictionary keys included."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _texts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _texts(item)


def test_no_published_string_carries_mojibake_or_a_damaged_letter(
    frontend_data, publication_layers
):
    """One sweep over every string of the dataset and the side files, keys
    included: no misread UTF-8 run a repair would restore, no lost byte. The
    delivered source text is the source itself and exempt (page 7432 ends in
    U+FFFD there); the redirect keys are checked apart below."""
    rest = {k: v for k, v in frontend_data.items() if k not in {"entries", "redirects"}}
    violations = [("dataset", text) for text in _texts(rest) if _encoding_damage(text)]
    for entry in frontend_data["entries"]:
        shown = {k: v for k, v in entry.items() if k != "fullBibliographicEntry"}
        violations += [
            (entry["sourcePageId"], text)
            for text in _texts(shown)
            if _encoding_damage(text)
        ]
    for page_id, layer in publication_layers.items():
        violations += [
            (page_id, text) for text in _texts(layer) if _encoding_damage(text)
        ]
    assert not violations, violations[:20]


@pytest.mark.xfail(
    strict=True,
    reason="1 redirect key, page 2364 alias 'Estasi di libertÃ', the page "
    "title the dump lost a byte of, measured 2026-10-30",
)
def test_no_redirect_key_carries_mojibake_or_a_damaged_letter(frontend_data):
    damaged = [key for key in frontend_data["redirects"] if _encoding_damage(key)]
    assert not damaged, damaged


def test_every_damage_hint_names_an_empty_field(frontend_data, classified_rows):
    rows = {int(row["page_id"]): row for row in classified_rows}
    hinted = {}
    for entry in frontend_data["entries"]:
        for flag in entry.get("reviewFlags", []):
            if flag["code"] == "encoding-damaged":
                assert not entry.get(flag["field"]), entry["sourcePageId"]
                hinted.setdefault(entry["sourcePageId"], set()).add(flag["field"])
    emptied = {
        int(pid): set(json.loads(row["encoding_damaged_fields"]))
        for pid, row in rows.items()
        if row.get("encoding_damaged_fields") and row["is_redirect"] != "True"
    }
    assert emptied
    assert emptied == hinted


def test_no_flat_value_keeps_a_whitespace_run(ns0_entries):
    violations = {}
    for entry in ns0_entries:
        for key, value in _flat_values(entry):
            if value != " ".join(value.split()):
                violations[entry["sourcePageId"]] = f"{key}={value!r}"
    _check_allowlist(violations, {})


def test_a_field_a_rule_emptied_is_a_rule_gap(ns0_entries, classified_rows):
    """Each unbound field of stage 03 is a rule gap with its rule, labelled
    rule-gap and never missing, in the interface record."""
    rows = {int(row["page_id"]): row for row in classified_rows}
    checked = 0
    for entry in ns0_entries:
        row = rows[entry["sourcePageId"]]
        unbound = set(json.loads(row["unbound_fields"] or "[]"))
        gaps = {gap["gapField"]: gap["gapRule"] for gap in entry.get("ruleGaps", [])}
        assert {f for f, r in gaps.items() if r == "statement-bindings"} == unbound
        for field in gaps:
            assert not entry.get(field), (entry["sourcePageId"], field)
            if field in entry["_provenance"]:
                assert entry["_provenance"][field] == "rule-gap"
        checked += bool(gaps)
    assert checked


def test_the_canonical_graph_carries_the_rule_gaps(canonical_entries, ns0_by_id):
    for entry in canonical_entries:
        if entry["sourcePageId"] in ns0_by_id:
            expected = ns0_by_id[entry["sourcePageId"]].get("ruleGaps")
            assert entry.get("ruleGaps") == expected


def test_verification_counts_no_rule_gap_as_a_false_negative(ns0_by_id):
    report = json.loads(
        (PROJECT_ROOT / "data/output/verification-report.json").read_text(
            encoding="utf-8"
        )
    )
    for result in report["detailed_results"]:
        entry = ns0_by_id.get(result["page_id"]) or {}
        for gap in entry.get("ruleGaps", []):
            assert f"{gap['gapField']}_false_negative" not in result["fields"]
    for field in ("publisher", "location", "translator"):
        assert "rule_gap" in report["summary"][field]


# (i) References resolve in the main namespace only.


def test_redirects_land_on_main_namespace_records(frontend_data):
    namespace = {
        entry["sourcePageId"]: entry["pageNamespace"]
        for entry in frontend_data["entries"]
    }
    off = {
        key: pid
        for key, pid in frontend_data["redirects"].items()
        if namespace.get(pid) != 0
    }
    assert not off


_REDIRECT_KINDS = {
    "absent-target",
    "chain-into-absent",
    "diacritic-variant",
    "case-variant",
    "loop",
    "self",
}


def test_every_main_namespace_redirect_resolves_or_is_reported(
    classified_rows, frontend_data
):
    from lib.config import OUTPUT_UNRESOLVED_REDIRECTS, SOURCE_REVISION_DECISIONS

    withheld = {
        decision["pageId"]
        for decision in json.loads(
            Path(SOURCE_REVISION_DECISIONS).read_text(encoding="utf-8")
        )["decisions"]
        if decision["action"] == "withhold-redirect-relation"
    }
    report = json.loads(Path(OUTPUT_UNRESOLVED_REDIRECTS).read_text(encoding="utf-8"))
    reported = {item["pageId"]: item for item in report["redirects"]}
    titles = {
        entry["title"]
        for entry in frontend_data["entries"]
        if entry.get("pageNamespace") == 0 and entry.get("title")
    }
    for row in classified_rows:
        if row["page_namespace"] != "0" or row["is_redirect"] != "True":
            continue
        pid = int(row["page_id"])
        if pid in withheld:
            assert pid not in reported
            continue
        own = row["page_title"]
        resolves = own in frontend_data["redirects"] or own in titles
        assert resolves != (pid in reported), (pid, own)
        if pid in reported:
            assert reported[pid]["pageTitle"] == own
            assert reported[pid]["kind"] in _REDIRECT_KINDS


def test_every_redirect_record_keeps_its_own_page_title(
    canonical_entries, classified_rows
):
    titles = {int(row["page_id"]): row["page_title"] for row in classified_rows}
    for entry in canonical_entries:
        if entry.get("isRedirect"):
            assert entry["wikiPageTitle"] == titles[entry["sourcePageId"]]


# (j) Structure pages are no works of Zweig.


def test_no_structure_page_names_an_author(canonical_entries):
    assert not [
        entry["sourcePageId"]
        for entry in canonical_entries
        if entry.get("pageNamespace") != 0 and "author" in entry
    ]


# (k) Edition values leave the dump form, and a locator heading is no edition.


def test_edition_values_leave_the_dump_form():
    from lib.editions import LOCATOR_HEADER_RE

    graph = json.loads(
        (PROJECT_ROOT / "data/output/editions/work-editions.jsonld").read_text(
            encoding="utf-8"
        )
    )
    escape = chr(92) + '"'
    violations = {}
    for edition in graph["editions"]:
        assert not LOCATOR_HEADER_RE.match(edition["klawiter:headerLine"].strip())
        for key in ("schema:publisher", "schema:locationCreated", "schema:description"):
            value = edition.get(key)
            for item in value if isinstance(value, list) else [value]:
                if isinstance(item, dict):
                    item = item.get("schema:name", "")
                if isinstance(item, str) and (
                    escape in item or item != " ".join(item.split())
                ):
                    violations[edition["@id"]] = f"{key}={item!r}"
    assert not violations
