"""Concordance rules of p07 on invented wiki lines and objects, never print text.

Each case pins one rule of the field route: a short single-word title read on
into its subtitle, no field matching for a collection header without address,
and a second field that a frequent token alone does not carry.
"""

from collections import defaultdict

from _viewer_data import object_meta, project
from p07_concordance import (
    _field_matches,
    _line_index,
    _rare_limit,
    _second_field_agrees,
    _stands_for_items,
    _title_key,
    _tokens,
)


def obj(title, year, subtitle=None, publisher="", place="", **extra):
    imprint = {"year": {"value": year}}
    if publisher:
        imprint["publisher"] = {"value": publisher}
    if place:
        imprint["place"] = {"value": place}
    o = {
        "id": "X/A/1#1",
        "title": {"value": title},
        "imprints": [imprint],
        "text": f"{title}. {place}: {publisher}, {year}.",
        **extra,
    }
    if subtitle:
        o["subtitle"] = {"value": subtitle}
    return o


def wiki(pages, rare_limit=10**9):
    """pages: {page: (title, [line, ...])} -> the arguments of _field_matches."""
    latest = {p: [_tokens(line) for line in lines] for p, (_, lines) in pages.items()}
    titles = {p: " ".join(_tokens(t)) for p, (t, _) in pages.items()}
    title_pages = defaultdict(set)
    for p, t in titles.items():
        for token in t.split():
            title_pages[token].add(p)
    return latest, _line_index(latest), title_pages, titles, rare_limit


def test_a_short_single_word_title_reads_on_into_its_subtitle():
    assert _title_key("Zorn", "Eine Erzählung") == ["zorn", "eine", "erzahlung"]
    assert _title_key("Zorn") == []
    assert _title_key("Zornesglut") == ["zornesglut"]
    assert _title_key("Der lange Zorn", "Roman") == ["der", "lange", "zorn"]


def test_a_short_title_with_subtitle_finds_a_line_on_another_page():
    pages = {
        1: ("Sammelband", ["Zorn. Erzählung. Ortheim: Quellbach, 1950."]),
        2: ("Zorn", ["Zweite Ausgabe, 1950"]),
    }
    with_subtitle = obj("Zorn", 1950, "Erzählung", "Quellbach", "Ortheim")
    found = {m["page"]: m["kind"] for m in _field_matches(with_subtitle, *wiki(pages))}
    assert found == {1: "field", 2: "title-year"}
    # Without the subtitle only the page titled exactly that word is reached.
    alone = obj("Zorn", 1950, None, "Quellbach", "Ortheim")
    assert [m["page"] for m in _field_matches(alone, *wiki(pages))] == [2]


def test_a_collection_header_without_address_is_not_matched():
    header = {"id": "X/A/2#1", "address": "", "types": [{"value": "collection"}]}
    addressed = {**header, "address": {"value": "A 2"}}
    volume = {"id": "X/A/3#1", "types": [{"value": "edition"}]}
    assert _stands_for_items(header)
    assert not _stands_for_items(addressed)
    assert not _stands_for_items(volume)
    # The viewer projection skips the same objects; p07 now emits none of them.
    records = [
        {"id": o["id"][:-2], "sha256": "h", "kind": "entry", "objects": [o]}
        for o in (header, addressed, volume)
    ]
    meta, _ = object_meta(records)
    assert {o["id"]: meta[o["id"]]["skip"] for o in (header, addressed, volume)} == {
        o["id"]: _stands_for_items(o) for o in (header, addressed, volume)
    }


def test_the_viewer_projection_works_without_collection_claims():
    records = [
        {
            "id": "X/A/3",
            "sha256": "h",
            "kind": "entry",
            "objects": [{"id": "X/A/3#1", "address": "A 3"}],
        }
    ]
    meta, hashes = object_meta(records)
    claim = {
        "id": "c1",
        "subject": "X/A/3#1",
        "predicate": "candidateFor",
        "object": "klawiter:entry/8",
        "evidence": {"print": {"record": "X/A/3", "sha256": "h"}, "wiki_page": 8},
        "producer": {"class": "editorial", "method": "rule", "rule": "p07.x"},
        "state": "proposed",
    }
    out = project([claim], [], meta, hashes, {}, {})
    assert "claims_skipped_collection" not in out["counts"]
    assert out["links"]["X/A/3#1"]["cand"][0]["claim"] == "c1"


def test_a_frequent_token_alone_does_not_carry_a_field_match():
    index = {"ortheim": set(range(50)), "quellbach": {1}, "weiler": set(range(80))}
    assert not _second_field_agrees(["ortheim"], index, 10)
    assert _second_field_agrees(["quellbach"], index, 10)
    assert _second_field_agrees(["ortheim", "weiler"], index, 10)
    assert not _second_field_agrees([], index, 10)
    # 1000 lines, a five-line window, one percent chance: two lines at most.
    assert _rare_limit({1: [[]] * 600, 2: [[]] * 400}) == 2


def test_a_lone_frequent_place_leaves_a_title_year_block_with_its_token():
    lines = [f"Anderes Buch. Ortheim: Verlag {n}, 1950." for n in range(5)]
    pages = {1: ("Sammelband", ["Das stille Haus. Ortheim, 1950."] + [""] * 5 + lines)}
    item = obj("Das stille Haus", 1950, None, "Quellbach", "Ortheim")
    match = _field_matches(item, *wiki(pages, rare_limit=3))[0]
    assert match["kind"] == "title-year"
    assert match["second_field"] == ["ortheim"]
    rare = _field_matches(item, *wiki(pages, rare_limit=10))[0]
    assert rare["kind"] == "field"
