"""Where each published value stands in the text the record card displays.

The pipeline maps the raw offsets a parser holds into the displayed text
(lib/value_spans.py, knowledge/data.md#value-positions). The unit cases use
complete source texts from tests/record_sources.json; the invariants run
over the published data and the stage intermediates.
"""

from __future__ import annotations

import importlib
import json
from functools import cache
from pathlib import Path

import pytest
from lib.publications import (
    build_page_publications,
    load_attested_places,
    publication_values,
)
from lib.translations import translation_statements
from lib.value_spans import (
    GAP_REASONS,
    RECORD_LIST_FIELDS,
    RECORD_SCALAR_FIELDS,
    Display,
    display_form,
    entry_holds,
    locate,
    record_evidence,
)
from lib.vocabulary import language_to_iso
from lib.wiki_parser import extract_categories

PUBLICATIONS_DIR = (
    Path(__file__).resolve().parents[1] / "docs" / "data" / "publications"
)
parser = importlib.import_module("03_parse_entries")


@pytest.fixture(scope="module")
def attested():
    return load_attested_places()


def _publications(record_sources, attested, page_id):
    entry = record_sources[page_id]
    categories, _ = extract_categories(entry["text"])
    layer = build_page_publications(
        page_id, entry["text"], entry["page_title"], categories, attested
    )
    return layer["publications"]


def _displayed(record_sources, page_id):
    return display_form(record_sources[page_id]["text"]).text


# The displayed text and its map.


def test_the_map_reproduces_the_delivered_text_of_every_page(classified_rows):
    """display_form replays stage 03's removal steps, so its text is the
    delivered text of every page and its offsets run in source order."""
    for row in classified_rows:
        if not row["raw_content"] or row["is_redirect"] in ("True", "true"):
            continue
        display = display_form(row["raw_content"])
        assert display.text == row["clean_content"], row["page_id"]
        assert len(display.index) == len(display.text)
        assert list(display.index) == sorted(display.index), row["page_id"]


# Publication values (lib/publications.py).


def test_a_title_maps_onto_its_own_displayed_words(record_sources, attested):
    (first, *_) = _publications(record_sources, attested, 17)
    (title,) = first["valueSpans"]["title"]
    assert title == {"value": "Brasilien. Ein Land der Zukunft", **_span(title)}
    text = _displayed(record_sources, 17)
    assert text[title["textStart"] : title["textEnd"]] == first["title"]
    assert "locator" not in title


def _span(entry):
    return {"textStart": entry["textStart"], "textEnd": entry["textEnd"]}


def test_a_value_inside_its_passage_is_located_there(record_sources, attested):
    """The publisher is the part of the header's imprint the split rule
    names; its position is its one occurrence inside that imprint."""
    (first, *_) = _publications(record_sources, attested, 17)
    (publisher,) = first["valueSpans"]["publisher"]
    assert publisher["locator"] == "region"
    text = _displayed(record_sources, 17)
    assert text[publisher["textStart"] : publisher["textEnd"]] == (
        "Bermann-Fischer Verlag"
    )
    pages = [
        entry
        for entry in first["valueSpans"]["contributions"]
        if entry["part"] in {"pages", "pageStart", "pageEnd"}
    ][:3]
    assert [text[e["textStart"] : e["textEnd"]] for e in pages] == ["(9)-21", "9", "21"]


def test_a_block_the_page_states_twice_keeps_its_own_positions(
    record_sources, attested
):
    """Page 24 sets the same 1964 block twice. A search would give both
    publications the first occurrence; the map gives each its own."""
    first, second = _publications(record_sources, attested, 24)[:2]
    assert first["sourceSlice"]["sha256"] == second["sourceSlice"]["sha256"]
    text = _displayed(record_sources, 24)
    assert first["sourceSlice"]["textStart"] < second["sourceSlice"]["textStart"]
    for publication in (first, second):
        block = publication["sourceSlice"]
        name = publication["valueSpans"]["credits"][0]
        assert block["textStart"] <= name["textStart"] < block["textEnd"]
        assert text[name["textStart"] : name["textEnd"]] == "Richard Friedenthal"


def test_a_whitespace_run_is_a_declared_derivation(record_sources, attested):
    """The credit keeps the dump's two spaces, the display shows one."""
    (first, *_) = _publications(record_sources, attested, 384)
    (name,) = [e for e in first["valueSpans"]["credits"] if e["part"] == "name"]
    assert name["value"] == "A.  Druktenis"
    assert name["derivedFrom"] == "A. Druktenis"
    assert name["derivation"] == "whitespace"
    text = _displayed(record_sources, 384)
    assert text[name["textStart"] : name["textEnd"]] == name["derivedFrom"]


def test_a_language_read_from_a_category_gives_the_raw_link(record_sources, attested):
    """Category links leave the displayed text; the value names the raw
    range of the one link it was read from."""
    (first, *_) = _publications(record_sources, attested, 17)
    for field in ("language", "languageCode"):
        (entry,) = first["valueSpans"][field]
        assert entry["gap"] == "category-markup"
        raw = record_sources[17]["text"][entry["rawStart"] : entry["rawEnd"]]
        assert raw == "[[Category:Historical Studies / Volumes (German)]]"


def test_a_language_heading_is_located_and_its_code_derived(record_sources, attested):
    publication = _publications(record_sources, attested, 279)[101]
    (language,) = publication["valueSpans"]["language"]
    (code,) = publication["valueSpans"]["languageCode"]
    assert language["value"] == "Dutch" and "derivation" not in language
    assert code == {
        "value": "nl",
        **_span(language),
        "derivedFrom": "Dutch",
        "derivation": "language-code",
    }


def test_a_value_repeated_in_its_passage_is_a_gap_not_a_first_match(
    record_sources, attested
):
    """ "Moskva" stands twice in the imprint "AST, Vostok-Zapad, AST Moskva,
    Moskva"; the value names how often instead of taking one."""
    publication = _publications(record_sources, attested, 279)[49]
    assert publication["places"] == ["Moskva"]
    assert publication["valueSpans"]["places"] == [
        {"value": "Moskva", "gap": "repeated", "count": 2}
    ]


def test_every_publication_value_has_a_span_or_a_gap(record_sources, attested):
    for page_id in record_sources:
        text = _displayed(record_sources, page_id)
        categories, _ = extract_categories(record_sources[page_id]["text"])
        layer = build_page_publications(
            page_id,
            record_sources[page_id]["text"],
            record_sources[page_id]["page_title"],
            categories,
            attested,
        )
        for publication in layer.get("publications", []):
            _assert_complete(publication, text, page_id)


def _assert_complete(publication, text, where):
    """The spans list exactly the published values, in order, and each holds."""
    listed = [
        (field, entry.get("part"), entry["value"])
        for field, entries in publication["valueSpans"].items()
        for entry in entries
    ]
    published = [
        (field, part, value)
        for field, part, _, value in publication_values(publication)
    ]
    assert listed == published, where
    for entries in publication["valueSpans"].values():
        for entry in entries:
            assert entry_holds(entry, text), (where, entry)


# Translation statements (lib/translations.py).


def test_a_translation_statement_names_its_displayed_passage(record_sources):
    """Each value of a statement keeps its raw span; the statement names where
    its passage stands in the displayed text, and every value of the passage
    that is displayed lies inside it (a title or credit the translation's
    head supplies stands before it)."""
    for page_id in (7166, 7224):
        raw = record_sources[page_id]["text"]
        display = display_form(raw)
        statements = translation_statements(raw)
        assert statements
        for statement in statements:
            start, end = statement["textStart"], statement["textEnd"]
            block = statement["sourceSlice"]
            for field, (raw_start, raw_end) in statement["spans"].items():
                if not block["start"] <= raw_start < block["end"]:
                    continue
                shown_start, shown_end = display.span(raw_start, raw_end)
                if shown_start < shown_end:
                    assert start <= shown_start and shown_end <= end, (page_id, field)


# Page-level values (stage 03 field_spans, lib/value_spans.record_evidence).


def _record(record_sources, page_id):
    entry = record_sources[page_id]
    row = parser.process_entry(
        {
            "page_id": str(page_id),
            "page_namespace": "0",
            "page_title": entry["page_title"],
            "text_id": "",
            "blob_id": "",
            "content": entry["text"],
        },
        load_attested_places(),
    )
    return row, json.loads(row["field_spans"] or "{}")


def test_stage_03_carries_the_span_of_a_headerless_value(record_sources):
    """Page 720 names Paris in four brackets and the location rule reads the
    first, "[Paris, 1937]"; the flat location carries that span, where a
    search of the displayed text finds the place repeated."""
    row, spans = _record(record_sources, 720)
    raw = record_sources[720]["text"]
    start, end = spans["location"]
    assert raw[start:end] == row["location"] == "Paris"
    assert raw[start - 1 : end + 7] == "[Paris, 1937]"
    display = display_form(raw)
    evidence = record_evidence({"location": "Paris"}, spans, display)
    (located,) = evidence["location"]
    assert display.text[located["textStart"] : located["textEnd"]] == "Paris"
    assert display.text[located["textEnd"] : located["textEnd"] + 7] == ", 1937]"
    assert locate("Paris", display, None)["gap"] == "repeated"


def test_page_level_evidence_holds_for_the_fixture_records(record_sources):
    for page_id, source in record_sources.items():
        row, spans = _record(record_sources, page_id)
        entry = {
            "title": row["title"],
            "location": row["location"],
            "translator": row["translator"],
            "language": row["language"],
            "categories": json.loads(row["categories"] or "[]"),
        }
        display = display_form(source["text"])
        evidence = record_evidence(entry, spans, display, source["page_title"])
        for field, entries in evidence.items():
            for item in entries:
                assert entry_holds(item, display.text), (page_id, field, item)
        for category in evidence.get("categories", []):
            raw = source["text"][category["rawStart"] : category["rawEnd"]]
            assert raw.startswith("[[Category:"), page_id


def test_a_value_without_a_parser_region_is_a_labelled_search():
    display = display_form("''Title''. Translated by Anna Berg. Wien: Verlag, 1950")
    assert locate("Anna Berg", display, None) == {
        "value": "Anna Berg",
        "textStart": 21,
        "textEnd": 30,
        "locator": "search",
    }
    assert locate("1950", display_form("1950. Reprinted 1950"), None) == {
        "value": "1950",
        "gap": "repeated",
        "count": 2,
    }


# Invariants over the published data.


@cache
def _side_file(page_id: int) -> dict:
    return json.loads(
        (PUBLICATIONS_DIR / f"{page_id}.json").read_text(encoding="utf-8")
    )


def test_every_published_publication_value_has_a_span_or_a_gap(all_entries):
    for entry in all_entries:
        if not entry.get("publicationCount"):
            continue
        text = entry.get("fullBibliographicEntry", "")
        for publication in _side_file(entry["sourcePageId"])["publications"]:
            _assert_complete(publication, text, publication["id"])


def test_every_published_record_value_has_a_span_or_a_gap(all_entries):
    """Every page-level value stage 03 reads has one evidence entry per value,
    in the record's order; a field the source or a rule leaves empty has
    none."""
    for entry in all_entries:
        text = entry.get("fullBibliographicEntry", "")
        evidence = entry.get("fieldEvidence", {})
        provenance = entry.get("_provenance", {})
        for field in RECORD_SCALAR_FIELDS:
            value = entry.get(field)
            if value in (None, ""):
                assert field not in evidence, (entry["@id"], field)
                continue
            assert [item["value"] for item in evidence[field]] == [str(value)]
        for field in RECORD_LIST_FIELDS:
            values = [str(value) for value in entry.get(field) or []]
            assert [item["value"] for item in evidence.get(field, [])] == values
        for field, entries in evidence.items():
            assert provenance.get(field) not in {"missing", "rule-gap"}
            for item in entries:
                assert entry_holds(item, text), (entry["@id"], field, item)


def test_only_a_value_without_a_parser_region_is_searched(all_entries):
    """The labelled search locates the enrichment's values and the places a
    normalisation table renamed; a rule-read value always has its region."""
    for entry in all_entries:
        provenance = entry.get("_provenance", {})
        for field, entries in entry.get("fieldEvidence", {}).items():
            for item in entries:
                if item.get("locator") == "search":
                    assert provenance.get(field) == "llm" or field == "allLocations"


def test_category_gaps_name_raw_category_links(source_rows, ns0_by_id):
    checked = 0
    for row in source_rows:
        entry = ns0_by_id.get(int(row["page_id"]))
        if entry is None:
            continue
        for entries in entry.get("fieldEvidence", {}).values():
            for item in entries:
                if item.get("gap") == "category-markup" and "rawStart" in item:
                    raw = row["content"][item["rawStart"] : item["rawEnd"]]
                    assert raw.startswith("[[Category:") and raw.endswith("]]")
                    checked += 1
    assert checked


def _blocks(entry):
    """Each publication of a page with the displayed passage that is its own:
    from its block's start to the start of the next block, the text after a
    header up to the next header (contents lists run past textEnd)."""
    publications = _side_file(entry["sourcePageId"])["publications"]
    starts = sorted({p["sourceSlice"]["textStart"] for p in publications})
    text_end = len(entry.get("fullBibliographicEntry", ""))
    for publication in publications:
        start = publication["sourceSlice"]["textStart"]
        end = next((s for s in starts if s > start), text_end)
        yield publication, start, end


def test_every_publication_value_stands_in_its_own_block(all_entries):
    """A value located in another publication's block is the other
    publication's value. A language heading of a translations section stands
    before the blocks it heads, so its language and code are exempt."""
    outside = []
    for entry in all_entries:
        if not entry.get("publicationCount"):
            continue
        for publication, start, end in _blocks(entry):
            for field, entries in publication["valueSpans"].items():
                for item in entries:
                    if "textStart" not in item:
                        continue
                    if start <= item["textStart"] and item["textEnd"] <= end:
                        continue
                    heading = field in {"language", "languageCode"}
                    if heading and item["textEnd"] <= start:
                        continue
                    outside.append((publication["id"], field, item["value"]))
    assert not outside, outside[:20]


def _occurrences(value: str, text: str) -> int:
    """How often a value stands in the text under the rule locate uses (whole
    word, then the declared whitespace, number and markup forms). The search
    reads only the text of the Display, so the raw side stays empty."""
    found = locate(value, Display("", text, ()), None)
    return 1 if "textStart" in found else found.get("count", 0)


@cache
def _place_table() -> dict[str, str]:
    path = Path(__file__).resolve().parents[1] / "pipeline/data/location_normalize.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _evidence(all_entries, layer):
    """(where, field, item, displayed text) of every value of one layer:
    record-scalar, record-list or publication."""
    for entry in all_entries:
        text = entry.get("fullBibliographicEntry", "")
        if layer == "publication":
            if entry.get("publicationCount"):
                for publication in _side_file(entry["sourcePageId"])["publications"]:
                    for field, entries in publication["valueSpans"].items():
                        for item in entries:
                            yield publication["id"], field, item, text
            continue
        lists = layer == "record-list"
        for field, entries in entry.get("fieldEvidence", {}).items():
            if (field in RECORD_LIST_FIELDS) == lists:
                for item in entries:
                    yield entry["@id"], field, item, text


def _dishonest(item, text) -> bool:
    """Whether a gap or a derivation claims what the text does not show."""
    value = item["value"]
    if item.get("gap") == "repeated":
        return _occurrences(value, text) < 2
    if item.get("gap") == "not-verbatim":
        return _occurrences(value, text) != 0
    if item.get("derivation") == "normalised":
        source = item["derivedFrom"]
        return value not in source and not any(
            spelling in source and canonical == value
            for spelling, canonical in _place_table().items()
        )
    if item.get("derivation") == "language-code":
        return language_to_iso(item["derivedFrom"]) != value
    return False


# A list value's repeated count is the number of parser readings of that value
# or of the forms it was read under (lib/value_spans._list_entry), not of its
# occurrences: 48 mapped places (Praha read from "Prag" and "Prague"), page
# 2091 "1932" and page 3341 "2008" each stand at most once. Page 2971 reads
# two contribution values starting at a bracket ("[Die Monotonisierung der
# Welt. 1925") that its region misses while the text holds them once.
_LIST_READINGS = "50 list values counted by readings, measured 2026-10-30"
_BRACKETED_CONTRIBUTIONS = "2 bracketed contributions of page 2971, 2026-10-30"


def _not_verbatim(item) -> bool:
    return item.get("gap") == "not-verbatim"


# Each case: the layer read and the values of it the case covers.
_HONESTY_CASES = {
    "record-scalar": ("record-scalar", lambda item: True),
    "record-list": ("record-list", lambda item: True),
    "publication": ("publication", lambda item: not _not_verbatim(item)),
    "publication-not-verbatim": ("publication", _not_verbatim),
}


@pytest.mark.parametrize(
    "case",
    [
        "record-scalar",
        pytest.param(
            "record-list",
            marks=pytest.mark.xfail(strict=True, reason=_LIST_READINGS),
        ),
        "publication",
        pytest.param(
            "publication-not-verbatim",
            marks=pytest.mark.xfail(strict=True, reason=_BRACKETED_CONTRIBUTIONS),
        ),
    ],
)
def test_a_gap_or_derivation_holds_against_the_text(all_entries, case):
    """A repeated gap names a value the text states at least twice, a
    not-verbatim gap one it states nowhere; a normalised value stands in its
    passage or is the place table's form of a spelling there; a language code
    is the code of its passage."""
    layer, covers = _HONESTY_CASES[case]
    dishonest = [
        (where, field, item)
        for where, field, item, text in _evidence(all_entries, layer)
        if covers(item) and _dishonest(item, text)
    ]
    assert not dishonest, dishonest[:20]


def _editor_set(entries) -> bool:
    return [item.get("gap") for item in entries] == ["editor-value"]


def test_published_record_evidence_is_its_recomputation(all_entries, classified_rows):
    """Every record's fieldEvidence equals what stage 05 computes from the
    field_spans stage 03 recorded: the same offsets, locators, derivations
    and gap kinds. A span moved or replaced by a gap fails even where the
    value stands elsewhere on the page. A value an editor patch set carries
    the gap editor-value instead (apply_patches.py) and is left out."""
    stage_05 = importlib.import_module("05_to_jsonld")
    rows = {int(row["page_id"]): row for row in classified_rows}
    differing = []
    for entry in all_entries:
        recomputed = stage_05.field_evidence(dict(rows[entry["sourcePageId"]]), entry)
        published = entry.get("fieldEvidence", {})
        for field in sorted(set(recomputed) | set(published)):
            if _editor_set(published.get(field, [])):
                continue
            if recomputed.get(field) != published.get(field):
                differing.append((entry["sourcePageId"], field))
    assert not differing, differing[:20]


def test_gap_reasons_are_declared():
    assert set(GAP_REASONS) == {
        "repeated",
        "not-verbatim",
        "category-markup",
        "not-displayed",
        "page-title",
        "editor-value",
    }
