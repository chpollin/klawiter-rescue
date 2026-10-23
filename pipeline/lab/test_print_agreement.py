"""Tests of the wiki-print agreement rule (S6.2) on snippets of page 448."""

from __future__ import annotations

from pathlib import Path

import pytest
from print_agreement import DEFAULT_OUT, attach_alignment, occurs_in, page_agreement
from split_print_links import REPO, assert_untracked

PASSAGE_1968 = (
    "[1968]: Svoboda, Praha [Prague]\n\nNetrpělivost srdce [Ungeduld des Herzens]. "
    "Translated by Božena Koseková. 326/(2)p. "
)
PASSAGE_1976 = (
    "[1976]: Práce, Praha [Prague]\n\nNetrpělivost srdce [Ungeduld des Herzens]. "
    "Translated by Božena Koseková. 2nd edition. 348p."
)
# Print text as extracted, with the substitute-font defect "ì" for "ě".
PRINT_448 = (
    "Netrpìlivost srdce [Ungeduld des Herzens]. Translated by Božena Koseková. "
    "326/(2)p. Praha: Svoboda, 1968."
)


def _page() -> dict:
    text = PASSAGE_1968 + "\n\n" + PASSAGE_1976

    def pub(pid: str, start: int, end: int, publisher: str, extent: str) -> dict:
        return {
            "id": pid,
            "textStart": start,
            "textEnd": end,
            "fields": {
                "publisher": {"value": publisher},
                "places": [{"value": "Praha"}],
                "translators": [{"value": "Božena Koseková"}],
                "extent": {"value": extent},
            },
        }

    start76 = len(PASSAGE_1968) + 2
    return {
        "pageId": 448,
        "source": {"text": text},
        "publications": [
            pub("p1968", 0, len(PASSAGE_1968), "Svoboda", "326/(2)p."),
            pub("p1976", start76, len(text), "Práce", "348p."),
        ],
    }


def test_alignment_is_attached_to_the_passage_it_covers():
    attached = attach_alignment(
        PRINT_448, {"p1968": PASSAGE_1968, "p1976": PASSAGE_1976}
    )
    assert attached["publicationIds"] == ["p1968"]
    unrelated = attach_alignment("Amok. Leipzig: Insel, 1922.", {"p1968": PASSAGE_1968})
    assert unrelated["publicationIds"] == []


def test_occurrence_rules_of_s21_apply_to_print_text():
    assert occurs_in(PRINT_448, "Svoboda")
    assert occurs_in(PRINT_448, "326/(2)p.")
    assert not occurs_in(PRINT_448, "Svobod")  # word boundary
    assert not occurs_in(
        PRINT_448, "Netrpělivost srdce"
    )  # extraction defect: not found
    assert occurs_in(PRINT_448, "Praha, Svoboda")  # every comma part occurs
    assert not occurs_in(PRINT_448, "Praha, Prague")


def test_agreement_per_value_and_title_year_matches_never_count():
    matches = [
        {"printId": "A2/F/p357l21", "route": "alignment", "text": PRINT_448},
        {
            "printId": "noise",
            "route": "title-year",
            "text": "Práce 348p.",
            "publicationIds": ["p1976"],
        },
    ]
    result = page_agreement(_page(), matches)
    assert result["attachments"]["A2/F/p357l21"]["publicationIds"] == ["p1968"]
    assert "p1976" not in result["publications"]  # no candidate: shows nothing
    pub = result["publications"]["p1968"]
    assert pub["entries"][0]["attachedBy"] == "lab rule"
    found = {(v["field"], v["value"]): v["foundIn"] for v in pub["values"]}
    assert found[("publisher", "Svoboda")] == ["A2/F/p357l21"]
    assert found[("extent", "326/(2)p.")] == ["A2/F/p357l21"]


def test_field_match_names_its_candidate_editions():
    matches = [
        {
            "printId": "I/A/1",
            "route": "field",
            "text": "Svoboda 326/(2)p.",
            "publicationIds": ["p1968", "p1976"],
        }
    ]
    result = page_agreement(_page(), matches)
    entry = result["publications"]["p1976"]["entries"][0]
    assert entry["candidates"] == 2 and entry["attachedBy"] == "print strand"
    values = {
        v["value"]: v["foundIn"] for v in result["publications"]["p1976"]["values"]
    }
    assert values["Práce"] == []  # not in the matched entry, never a disagreement


def test_derived_print_data_stays_under_docs_lab_local():
    assert Path(DEFAULT_OUT).resolve().is_relative_to(REPO / "docs" / "lab" / "local")
    with pytest.raises(SystemExit):
        assert_untracked(REPO / "docs" / "lab" / "data" / "agreement")
