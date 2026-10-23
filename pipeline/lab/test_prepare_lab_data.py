"""Tests of the lab rules on small fixtures cut from the real data.

The fixtures are snippets of the published source text and decision records
(page 448, pages 54 and 7460, location-decisions.json); expectations follow
the specification in knowledge/lab-frontend.md, not the current output.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from lab_rules import (
    Passage,
    boundary_check,
    classify_bracket,
    find_occurrences,
    first_bracket_after_title,
    link_sentence,
    parse_translations_section,
    parse_zweig_author_types,
    producer_label,
    split_parts,
    strip_page_suffixes,
    title_key,
    value_occurrences,
    variant_key,
)

ROOT = Path(__file__).resolve().parents[2]

# Source text of page 448 as published in docs/data/klawiter.json.
TEXT_448 = (
    "[1968]: Svoboda, Praha [Prague]\n\nNetrpělivost srdce [Ungeduld des Herzens]. "
    "Translated by Božena Koseková. 326/(2)p. \n\n[1976]: Práce, Praha [Prague]\n\n"
    "Netrpělivost srdce [Ungeduld des Herzens]. Translated by Božena Koseková. "
    "2nd edition. 348p.\n\n[1998]: Český klub,Praha [Prague]\n\nNetrpělivost srdce "
    "[Ungeduld des Herzens]. Translated by Božena Koselová. 327p. \n\n[2006]: Edice "
    "Deniku Lidové Noviny, Praha [Prague]\n \nNetrpělivost srdce [Ungeduld des "
    "Herzens]. Translated by Božena Koselová. 333/(2)p. [Světová literatura]"
)
PASSAGES_448 = [
    Passage("klawiter:publication/448-1968-a", 1968, 0, 116),
    Passage("klawiter:publication/448-1976-a", 1976, 119, 242),
    Passage("klawiter:publication/448-1998-a", 1998, 244, 358),
    Passage("klawiter:publication/448-2006-a", 2006, 361, 518),
]
TRANSLATOR_448 = "Božena Koseková, Božena Koseková, Božena Koselová"


def test_word_boundary_matching():
    assert find_occurrences("Svoboda, Praha [Prague]", "Praha") == [(9, 14)]
    assert find_occurrences("Prahaus", "Praha") == []
    assert find_occurrences("Praha/Prague", "Praha") != []
    # A number is bounded by digits only, so it matches inside "348p.".
    assert len(find_occurrences(TEXT_448, "348")) == 1
    assert find_occurrences("1348p.", "348") == []
    assert find_occurrences(TEXT_448, "Koselov") == []


def test_comma_parts_are_matched_separately_and_deduplicated():
    assert split_parts(TRANSLATOR_448) == ["Božena Koseková", "Božena Koselová"]
    assert split_parts(348) == ["348"]
    assert split_parts(None) == []


def test_own_passage_occurrence_comes_first():
    own = {"klawiter:publication/448-1998-a"}
    result = value_occurrences(TEXT_448, "Praha", PASSAGES_448, own)
    first = result["parts"][0]["occurrences"][0]
    assert first["own"] and first["publicationId"] == "klawiter:publication/448-1998-a"
    missing = value_occurrences(TEXT_448, "Prag", PASSAGES_448, own)
    assert missing["noExactOccurrence"] is True


def test_boundary_check_names_the_publication_holding_the_value():
    check = boundary_check(
        TEXT_448,
        1968,
        PASSAGES_448,
        {"translator": TRANSLATOR_448, "pageCount": 348, "publisher": "Svoboda"},
    )
    assert check["run"]
    parts = {p["part"]: p for p in check["fields"]["translator"]["parts"]}
    assert parts["Božena Koseková"]["result"] == "pass"
    assert parts["Božena Koselová"]["result"] == "fires"
    held = {h["year"] for h in parts["Božena Koselová"]["heldBy"]}
    assert held == {1998, 2006}
    assert check["fields"]["pageCount"]["fires"]
    assert check["fields"]["pageCount"]["parts"][0]["heldBy"][0]["year"] == 1976
    assert not check["fields"]["publisher"]["fires"]


def test_boundary_check_shared_year_passes_in_any_of_them():
    passages = [
        Passage("a", 1976, 0, 116),
        Passage("b", 1976, 119, 242),
        Passage("c", 1998, 244, 358),
    ]
    check = boundary_check(TEXT_448, 1976, passages, {"pageCount": 348})
    assert check["sharedYear"]
    assert check["fields"]["pageCount"]["parts"][0]["result"] == "pass"


def test_boundary_check_does_not_run_without_matching_year_or_breakdown():
    check = boundary_check(TEXT_448, 1950, PASSAGES_448, {"publisher": "Svoboda"})
    assert check == {
        "run": False,
        "reason": "record-year-matches-no-publication",
        "fields": {},
    }
    assert (
        boundary_check(TEXT_448, 1968, [], {})["reason"] == "no-publication-breakdown"
    )
    assert boundary_check(TEXT_448, None, PASSAGES_448, {})["reason"] == (
        "record-has-no-year"
    )


def test_bracket_normalisation_and_suffixes():
    suffixes = frozenset({"volume", "german"})
    assert title_key("Ungeduld des Herzens (VIST)") == "ungeduld des herzens"
    assert title_key("Ungeduld des Herzens. Roman") == "ungeduld des herzens"
    assert title_key("Buchmendel (Eine Erzählung) (VIST)") == "buchmendel"
    assert title_key("Praterfrühling. Eine Novelle (VIST)") == "praterfrühling"
    assert title_key("Schachnovelle / Volume", suffixes) == "schachnovelle"
    assert title_key("Ein Mensch, den man nicht vergißt") == (
        "ein mensch, den man nicht vergisst"
    )
    assert title_key("Die Legende der dritten Taube") == "die legende der dritten taube"
    assert strip_page_suffixes("Novela de ajedrez / Una partida", suffixes) == (
        "Novela de ajedrez / Una partida"
    )
    # Variants surface as possibly the same title and are never merged.
    assert title_key("Der Brief einer Unbekannten") != title_key(
        "Brief einer Unbekannten"
    )
    assert variant_key(title_key("Der Brief einer Unbekannten")) == variant_key(
        title_key("Brief einer Unbekannten")
    )
    assert title_key("Erasmus’ Tod") == title_key("ERASMUS' TOD")


def test_first_bracket_after_title():
    found = first_bracket_after_title(TEXT_448, ["Netrpělivost srdce"])
    assert found["content"] == "Ungeduld des Herzens"
    subtitle = "Magelan i negovija podvig [Magellan. Der Mann und seine Tat]"
    assert first_bracket_after_title(subtitle, ["Magelan"])["content"].startswith(
        "Magellan"
    )
    container = '"Hydepark" in Neue Freie Presse [Wien], 1 May 1912'
    assert first_bracket_after_title(container, ["Hydepark"]) is None
    glued = "Amoka. Translated by N[arahara] K[āśīnātha]"
    assert first_bracket_after_title(glued, ["Amoka"]) is None


def test_bracket_exclusion_classes():
    places = frozenset({"berlin", "paris"})
    assert classify_bracket("1927", places) == "year-or-number"
    assert classify_bracket("Der versiegelte Zug. Lenin, 9. April 1917", places) == (
        "year-or-number"
    )
    assert classify_bracket(
        "Schachnovelle * Angst * Brief einer Unbekannten", places
    ) == ("several-titles")
    assert classify_bracket("Berlin", places) == "place"
    assert classify_bracket("The Burnt Heart Cries Out: Novellas, Legends", places) == (
        "english-gloss"
    )
    assert classify_bracket(
        "Brennendes Geheimnis. Translated by E. Ter-Minasian", places
    ) == ("title")
    assert classify_bracket("Ungeduld des Herzens", places) == "title"


def test_translations_section_by_language_with_german_apart():
    text = (
        "Film script:\n\nX\n\nTranslations:\n\nAlbanian: Padurimi i zemrës. Roman "
        "[Tiranë/Tirana, 1997 / 2014]. Translated by Jorgi Doksani\n\n"
        'Belorussian/Belarusian: "Shakhmatnaia navela" [Minsk, 1994]\n\n'
        "German:\nUngeduld des Herzens [Wien, 1953]\n\nSecondary Literature:\n\n"
        "Buloff, Joseph"
    )
    words = frozenset({"albanian", "belorussian", "german"})
    parsed = parse_translations_section(text, words)
    assert [e["language"] for e in parsed["languages"]] == [
        "Albanian",
        "Belorussian/Belarusian",
    ]
    assert parsed["german"][0]["text"] == "Ungeduld des Herzens [Wien, 1953]"
    assert "Buloff" not in str(parsed)


def test_producer_labels_including_fixture_demotion():
    fixture = {
        "action": "confirm",
        "qid": "Q1085",
        "decidedBy": "repository-ground-truth-fixture",
        "evidence": ["tests/wikidata_ground_truth.json"],
    }
    label = producer_label(fixture)
    assert label == {
        "state": "proposed",
        "producer": "test fixture of twenty places, no source occurrence",
        "link": False,
    }
    assert link_sentence("Q1085", label) == (
        "Wikidata link Q1085: proposed, by test fixture of twenty places, "
        "no source occurrence"
    )
    agent = {
        "action": "confirm",
        "decidedBy": "independent-verification-agent",
        "evidence": ["klawiter:sourceOccurrence/location/5053/60928/1"],
    }
    assert producer_label(agent)["producer"].startswith("independent agents")
    low = {
        "action": "correct",
        "decidedBy": "independent-verification-agent",
        "evidence": ["data/output/reconciliation/location-low-score-review.json#x"],
    }
    assert producer_label(low)["producer"] == "agent review, no source occurrence"
    main = {"action": "confirm", "decidedBy": "main-instance", "evidence": []}
    assert producer_label(main)["producer"] == "main agent under operator delegation"
    reject = {"action": "reject", "decidedBy": "main-instance", "evidence": []}
    assert producer_label(reject)["state"] is None
    assert not producer_label(reject)["link"]
    open_claim = {"action": "unresolved", "decidedBy": "independent-verification-agent"}
    assert producer_label(open_claim)["state"] == "contested"


def test_zweig_author_types_follow_the_js_derivation():
    js = (ROOT / "docs" / "js" / "constants.js").read_text(encoding="utf-8")
    types = parse_zweig_author_types(js)
    assert "foreword" not in types and "collected-works" in types
    assert "secondary-literature" not in types


def test_no_local_print_data_is_tracked():
    tracked = subprocess.run(
        ["git", "ls-files", "docs/lab/local"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert tracked == "", f"tracked files under docs/lab/local: {tracked}"
