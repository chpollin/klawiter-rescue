"""Tests of the lab rules on small fixtures cut from the real data.

The fixtures are snippets of the published source text and decision records
(page 448, pages 54 and 7460, location-decisions.json); expectations follow
the specification in knowledge/lab-frontend.md, not the current output.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from lab_rules import (
    SAMPLE_REVIEW_PRODUCER,
    Passage,
    boundary_check,
    classify_bracket,
    decision_date,
    edition_assignment,
    evidence_label,
    find_occurrences,
    first_bracket_after_title,
    fold_search,
    has_source_occurrence,
    parse_translations_section,
    parse_zweig_author_types,
    plain_wiki_text,
    producer_label,
    section_of,
    split_parts,
    strip_page_suffixes,
    title_key,
    value_occurrences,
    variant_key,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

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


def test_producer_labels_name_llm_agents_and_no_person():
    agent = {
        "action": "confirm",
        "decidedBy": "independent-verification-agent",
        "evidence": ["klawiter:sourceOccurrence/location/5053/60928/1"],
    }
    label = producer_label(agent)
    assert label["state"] == "confirmed" and label["warning"] is None
    assert label["producer"].startswith("independent LLM agents")
    assert label["producer"].endswith("no person")
    assert label["producerShort"] == "LLM agent, delegated"
    low = {
        "action": "correct",
        "decidedBy": "independent-verification-agent",
        "evidence": ["data/output/reconciliation/location-low-score-review.json#x"],
    }
    assert producer_label(low)["producer"] == (
        "LLM agent review, no source occurrence, no person"
    )
    assert producer_label(low)["warning"] == "no source occurrence"
    main = {"action": "confirm", "decidedBy": "main-instance", "evidence": []}
    assert producer_label(main)["producer"] == (
        "main LLM agent under operator delegation, no person"
    )
    reject = {"action": "reject", "decidedBy": "main-instance", "evidence": []}
    assert producer_label(reject)["state"] is None
    assert not producer_label(reject)["link"]
    open_claim = {"action": "unresolved", "decidedBy": "independent-verification-agent"}
    assert producer_label(open_claim)["state"] == "contested"
    assert "LLM agent" in producer_label(open_claim)["producer"]


def test_data_contract_agent_producers_say_llm_agent_and_no_person():
    """Coordinator ruling of 2026-10-23, run on every stored place decision."""
    path = ROOT / "data" / "reconciliation" / "location-decisions.json"
    decisions = json.loads(path.read_text(encoding="utf-8"))["decisions"]
    assert decisions
    for decision in decisions:
        label = producer_label(decision)
        if label["person"]:
            continue
        assert "LLM agent" in label["producer"], decision["decisionId"]
        assert "LLM agent" in label["producerShort"], decision["decisionId"]
        assert "no person" in label["producer"], decision["decisionId"]
        if label["state"] == "confirmed" and not has_source_occurrence(
            decision.get("evidence") or []
        ):
            assert label["warning"] == "no source occurrence", decision["decisionId"]


def test_data_contract_on_the_prepared_pages():
    """The written page files keep the ruling for places and edition assignments."""
    pages = sorted((ROOT / "docs" / "lab" / "data" / "pages").glob("*.json"))
    if not pages:
        pytest.skip("no prepared lab data; run prepare_lab_data.py first")
    for path in pages:
        page = json.loads(path.read_text(encoding="utf-8"))
        decisions = [page["placeDecision"]] + [
            d for p in page["publications"] for d in p["placeDecisions"]
        ]
        for d in decisions:
            if not d or not d["decision"] or d["person"]:
                continue
            assert "LLM agent" in d["producer"], (path.name, d["place"])
            assert "no person" in d["producer"], (path.name, d["place"])
            assert d["producerShort"] == "LLM agent, delegated", path.name
        for pub in page["publications"]:
            ea = pub["editionAssignment"]
            if ea["state"] == "confirmed":
                assert ea["producer"] == "producer not recorded" or (
                    "LLM agent" in ea["producer"] and "no person" in ea["producer"]
                ), (path.name, pub["id"])


def test_edition_assignment_names_the_sample_review_or_says_not_recorded():
    case = {"edition_id": "klawiter:edition/54-1939-a", "disposition": "confirm"}
    ea = edition_assignment("confirmed", case["edition_id"], case, "2026-08-21", None)
    assert ea["producer"] == SAMPLE_REVIEW_PRODUCER and ea["date"] == "2026-08-21"
    claim = {
        "reviewHistory": [
            {
                "outcome": "unresolved",
                "reviewer": "klawiter:agent/reconciliation-verifier",
            },
            {
                "outcome": "confirm",
                "reviewer": "klawiter:agent/main-instance",
                "date": "2026-09-22",
            },
        ]
    }
    decided = edition_assignment("confirmed", "e", None, None, claim)
    assert decided["producerShort"] == "LLM agent, delegated"
    assert decided["date"] == "2026-09-22"
    unknown = edition_assignment("confirmed", "e", None, None, None)
    assert unknown["producer"] == "producer not recorded"
    proposed = edition_assignment(None, None, None, None, None)
    assert proposed["state"] == "proposed" and not proposed["inEditionModel"]


def test_decision_date_falls_back_to_the_basis_sentence():
    basis = (
        "reviewed by independent agents against the source and Wikidata on "
        "2026-09-23 and adjudicated by the main instance"
    )
    assert decision_date(None, basis) == {
        "date": "2026-09-23",
        "dateSource": "basis text",
    }
    assert decision_date("2026-09-22T10:00:00Z", basis)["date"] == "2026-09-22"
    assert decision_date(None, None) == {"date": None, "dateSource": None}


def test_evidence_and_markup_in_reader_terms():
    occ = evidence_label("klawiter:sourceOccurrence/location/90/59814/1")
    assert occ["pageId"] == 90 and occ["textId"] == 59814
    low = evidence_label("data/output/reconciliation/location-low-score-review.json#x")
    assert low["label"] == "LLM agent review of low-scoring Wikidata candidates"
    dated = evidence_label(
        "data/reconciliation/location-agent-review-2026-09-23.json#M"
    )
    assert dated["label"] == "LLM agent review of 2026-09-23"
    line = "'''[1993]: l'Université de Rouen - Haute Normandie, Saint-Aignan'''"
    assert plain_wiki_text(line) == (
        "[1993]: l'Université de Rouen - Haute Normandie, Saint-Aignan"
    )
    assert plain_wiki_text("see [[Amok|Der Amokläufer]]") == "see Der Amokläufer"


def test_section_of_names_where_an_outside_value_stands():
    text = (
        "[1939]: X, Wien\n\nTitle. 443p.\n\nTranslations:\n\nAlbanian: Padurimi "
        "i zemrës. Translated by Jorgi Doksani\n\nContents:\n\nAyrogh "
        "[Brennendes Geheimnis. Translated by E. Ter-Minasian], pp. 5-113"
    )
    doksani = section_of(text, text.index("Jorgi"))
    assert doksani == {"section": "Translations", "lineLabel": "Albanian"}
    minasian = section_of(text, text.index("E. Ter"))
    assert minasian == {"section": "Contents", "lineLabel": None}
    assert section_of(text, 3) == {"section": None, "lineLabel": None}


def test_fold_samples_shared_with_the_browser_fold():
    """fold() in docs/lab/js/lab.js is checked against the same file by node."""
    samples = json.loads((HERE / "fold_samples.json").read_text(encoding="utf-8"))
    for row in samples["samples"]:
        assert fold_search(row["input"]) == row["expected"], row["input"]


def test_browser_rules_with_node():
    """The node test of the browser modules, when node is installed."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    result = subprocess.run(
        [node, str(HERE / "test_lab_js.mjs")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


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


def test_search_folding_strips_diacritics_and_folds_umlauts():
    assert fold_search("Netrpělivost srdce") == "netrpelivost srdce"
    assert fold_search("Müller") == fold_search("Mueller") == "muller"
    assert fold_search("Straße") == fold_search("Strasse") == "strasse"
    assert fold_search("ʿĀṣifah fī ʾl-jannah") == "asifah fi l jannah"
    assert fold_search("Yayıları, İstanbul") == "yayilari istanbul"
    # Substring matching survives the digraph step on both sides.
    assert fold_search("ungeduld") in fold_search("Ungeduld des Herzens (VIST)")
    assert fold_search("Netrpelivost") in fold_search("Netrpělivost srdce")


def test_search_index_keeps_title_publication_title_and_bracket_apart():
    from prepare_lab_data import search_index

    pages = {
        448: {
            "title": "Netrpělivost srdce",
            "entryType": "fiction",
            "language": "Czech",
        },
        90: {
            "title": "Odabrana djela Stefana Zweiga",
            "entryType": "collected-works",
            "language": "Croatian",
            "year": 1965,
            "allYears": [1965, 1966],
        },
    }
    pubs = {
        448: [
            {
                "id": "klawiter:publication/448-1968-a",
                "year": 1968,
                "language": "Czech",
                "imprint": "Svoboda, Praha",
                "title": "Netrpělivost srdce",
            }
        ]
    }
    works = [
        {
            "workId": "lab-work/54",
            "title": "Ungeduld des Herzens",
            "anchor": {
                "pageId": 54,
                "vist": True,
                "members": [{"pageId": 54, "title": "Ungeduld des Herzens (VIST)"}],
            },
            "union": {"count": 45},
        }
    ]
    brackets = {448: {"content": "Ungeduld des Herzens", "class": "title"}}
    membership = {448: [{"workId": "lab-work/54"}, {"workId": "lab-work/54"}]}
    index = search_index(pages, pubs, works, brackets, membership)
    by_id = {r["id"]: r for r in index["pages"]}
    assert by_id[448]["kb"] == "ungeduld des herzens"
    assert "kp" not in by_id[448]  # publication title equals the page title
    assert by_id[448]["w"] == ["lab-work/54"]
    assert by_id[448]["p"] == [
        ["klawiter:publication/448-1968-a", 1968, "Czech", "Svoboda, Praha"]
    ]
    assert by_id[90]["p"] is None and by_id[90]["y"] == [1965, 1966]
    assert index["works"][0]["k"].startswith("ungeduld des herzens")
