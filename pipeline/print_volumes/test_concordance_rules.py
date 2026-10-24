"""Concordance rules of p07 on invented wiki lines and objects, never print text.

Each case pins one rule of the field route: a short single-word title read on
into its subtitle, no field matching for a collection header without address,
a second field that a frequent token alone does not carry, sought in the
matched wiki item only and named by field, and the relation a match states.
"""

from collections import defaultdict

from _viewer_data import object_meta, project
from p07_concordance import (
    _field_matches,
    _host_position,
    _line_index,
    _rare_limit,
    _relation,
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


def wiki(pages, rare_limit=10**9, slices=None):
    """pages: {page: (title, [line, ...])} -> the arguments of _field_matches;
    slices: {page: [(first line, end line, publication id)]}."""
    latest = {p: [_tokens(line) for line in lines] for p, (_, lines) in pages.items()}
    raw = {p: list(lines) for p, (_, lines) in pages.items()}
    titles = {p: " ".join(_tokens(t)) for p, (t, _) in pages.items()}
    title_pages = defaultdict(set)
    for p, t in titles.items():
        for token in t.split():
            title_pages[token].add(p)
    return latest, _line_index(latest), title_pages, titles, rare_limit, raw, slices


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
    assert match["second_field"] == ["place"]
    assert match["second_field_values"] == ["ortheim"]
    rare = _field_matches(item, *wiki(pages, rare_limit=10))[0]
    assert rare["kind"] == "field"


TITLE = ["das", "stille", "haus"]


def test_the_second_field_names_the_field_and_keeps_its_token_apart():
    pages = {1: ("Sammelband", ["Das stille Haus. Ortheim: Quellbach, 1950."])}
    item = obj("Das stille Haus", 1950, None, "Quellbach", "Ortheim")
    match = _field_matches(item, *wiki(pages))[0]
    assert match["kind"] == "field"
    assert match["second_field"] == ["place", "publisher"]
    assert match["second_field_values"] == ["ortheim", "quellbach"]


def test_a_neighbouring_items_imprint_does_not_agree():
    lines = ["Das stille Haus, 1950.", "Anderes Buch. Ortheim: Quellbach, 1951."]
    item = obj("Das stille Haus", 1950, None, "Quellbach", "Ortheim")
    match = _field_matches(item, *wiki({1: ("Sammelband", lines)}))[0]
    assert (match["kind"], match["second_field"]) == ("title-year", [])
    # The head of the verified publication slice the match stands in counts.
    head = ["[1950]: Quellbach, Ortheim", "Das stille Haus. 200p."]
    slices = {1: [(0, 2, "klawiter:publication/1-1950-a")]}
    pages = {1: ("Sammelband", head)}
    match = _field_matches(item, *wiki(pages, slices=slices))[0]
    assert match["kind"] == "field"


def test_a_line_naming_the_title_as_host_states_containment():
    assert _host_position("[[Das stille Haus]] [Ortheim, 1950], No. 3", TITLE)
    assert _host_position("\"Ein Gedicht\" in ''Das stille Haus''. 1950", TITLE)
    assert not _host_position("''Das stille Haus''. Ortheim: Quellbach, 1950", TITLE)
    # The title stands first as the item, only then inside a host.
    assert not _host_position(
        '"Das stille Haus" in [[Das stille Haus und mehr]]', TITLE
    )
    volume = {"title": {"value": "Das stille Haus"}}
    reprint = {"hosts": [{"title": {"value": "Das stille Haus"}}]}
    host, item = {"role": "host"}, {"role": "item"}
    assert _relation(volume, host, False) == "contains"
    assert _relation(volume, item, True) == "containedIn"
    assert _relation(volume, item, False) == "samePublicationAs"
    assert _relation(reprint, item, False) == "containedIn"


def test_the_overlap_report_counts_each_object_once_by_its_strongest_route():
    from p07b_overlap import overlap

    def rec(rid, kind="entry", **o):
        return {
            "id": rid,
            "volume": "I",
            "part": "A",
            "kind": kind,
            "objects": [{"id": f"{rid}#1", "address": "A 1", **o}],
        }

    def claim(subject, predicate, target):
        return {
            "id": f"{subject}{predicate}",
            "subject": subject,
            "predicate": predicate,
            "object": target,
            "evidence": {},
            "state": "proposed",
        }

    records = [rec("I/A/1"), rec("I/A/2"), rec("I/A/3"), rec("I/A/4", "reference")]
    claims = [
        claim("I/A/1", "textAlignedWith", "klawiter:entry/5"),
        claim("I/A/1#1", "candidateFor", "klawiter:entry/6"),
        claim("I/A/2#1", "containedIn", "klawiter:publication/7-1950-a"),
        claim("I/A/2#1", "candidateFor", "klawiter:entry/8"),
    ]
    pubs = {"klawiter:publication/7-1950-a", "klawiter:publication/9-1951-a"}
    out = overlap(records, claims, pubs, {5, 6, 7, 8, 9})
    rows = {r["route"]: r["objects"] for r in out["print"]["I"]["A"]}
    assert rows == {
        "text": 1,
        "field:containedIn": 1,
        "none": 1,
        "not matched: cross-reference": 1,
    }
    assert {r["state"] for r in out["print"]["I"]["A"]} == {"proposed"}
    assert out["wiki"]["publications"]["named by no claim"] == 1
    assert out["wiki"]["pages"]["named only by a title-year block"] == 2
