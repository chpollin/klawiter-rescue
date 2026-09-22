"""Publication- and contribution-scoped facts, checked against the source.

The reviewed expectations in ``tests/publication_cases.json`` are the operator
specification of 2026-09-08 for the four owner-worksheet cases. They are never
parser output: every literal is a slice of the source text delivered in
``knowledge/evaluations/2026-09-05/source-only.json``, and each case carries the
SHA-256 of the text it was written against, so a changed source invalidates the
expectation instead of silently passing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from lib.publications import (
    PAGE_KINDS,
    ROLE_VOCABULARY,
    build_page_publications,
    imprint_publisher,
    load_attested_places,
)

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "tests" / "publication_cases.json"
SOURCE_ONLY_PATH = ROOT / "knowledge/evaluations/2026-09-05/source-only.json"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


CASES = _load_json(CASES_PATH)
SOURCE_TEXTS = {entry["page_id"]: entry for entry in _load_json(SOURCE_ONLY_PATH)}


def _case_ids() -> list[str]:
    return [f"page_{case['page_id']}" for case in CASES]


@pytest.fixture(scope="module")
def attested_places() -> set[str]:
    return load_attested_places()


@pytest.fixture(scope="module", params=CASES, ids=_case_ids())
def case(request) -> dict:
    return request.param


@pytest.fixture(scope="module")
def source_text(case) -> str:
    page_id = case["page_id"]
    entry = SOURCE_TEXTS[page_id]
    text = entry["text"]
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert digest == case["textSha256"], (
        f"page {page_id}: the reviewed expectation was written against a "
        "different source text; re-review before updating the hash"
    )
    return text


@pytest.fixture(scope="module")
def built(case, source_text, attested_places) -> dict:
    entry = SOURCE_TEXTS[case["page_id"]]
    return build_page_publications(
        page_id=case["page_id"],
        text=source_text,
        page_title=entry["page_title"],
        categories=_categories(source_text),
        attested_places=attested_places,
    )


def _categories(text: str) -> list[str]:
    from lib.wiki_parser import extract_categories

    return extract_categories(text)[0]


# --- Page-level shape -------------------------------------------------------


def test_page_kind_and_count_are_carried_by_the_record(case, built) -> None:
    """The card labels from these fields; it derives nothing from categories."""
    assert built["pageKind"] == case["pageKind"]
    assert built["pageKind"] in PAGE_KINDS
    assert built["publicationCount"] == case["publicationCount"]
    assert built["publicationCount"] == len(built["publications"])


def test_facet_fields_carry_every_publication_value(case, built) -> None:
    """A multi-publication page must be findable under every publication's
    year, place and language, never only under one publication's value."""
    assert built["publicationYears"] == case["publicationYears"]
    assert built["publicationPlaces"] == case["publicationPlaces"]
    assert built["publicationLanguages"] == case["publicationLanguages"]


def test_publication_identifiers_and_order(case, built) -> None:
    assert [p["id"] for p in built["publications"]] == [
        p["id"] for p in case["publications"]
    ]


def test_every_publication_is_anchored_in_the_source(built, source_text) -> None:
    for publication in built["publications"]:
        slice_ = publication["sourceSlice"]
        start, end = slice_["start"], slice_["end"]
        assert 0 <= start < end <= len(source_text)
        block = source_text[start:end]
        assert hashlib.sha256(block.encode("utf-8")).hexdigest() == slice_["sha256"]


def test_every_reported_field_carries_its_provenance_class(built) -> None:
    structural = {"id", "provenance", "sourceSlice", "reviewFlags"}
    for publication in built["publications"]:
        reported = set(publication) - structural
        assert set(publication["provenance"]) == reported
        assert set(publication["provenance"].values()) == {"regex"}


# --- Publication-scoped facts ----------------------------------------------


SCALAR_FIELDS = (
    "year",
    "yearRaw",
    "title",
    "imprint",
    "publisher",
    "language",
    "languageCode",
    "editionStatement",
    "series",
    "seriesVolume",
    "note",
)


def test_publication_scalar_fields(case, built) -> None:
    for expected, actual in zip(
        case["publications"], built["publications"], strict=True
    ):
        for field in SCALAR_FIELDS:
            assert actual.get(field) == expected.get(field), (
                f"{expected['id']} field {field}: "
                f"expected {expected.get(field)!r}, got {actual.get(field)!r}"
            )


def test_publication_places_keep_the_source_wording(case, built) -> None:
    for expected, actual in zip(
        case["publications"], built["publications"], strict=True
    ):
        assert actual.get("places", []) == expected.get("places", [])


def test_publication_extent_keeps_the_original_notation(case, built) -> None:
    for expected, actual in zip(
        case["publications"], built["publications"], strict=True
    ):
        assert actual.get("extent") == expected.get("extent")


def test_publication_container_and_online_location(case, built) -> None:
    for expected, actual in zip(
        case["publications"], built["publications"], strict=True
    ):
        assert actual.get("container") == expected.get("container")
        assert actual.get("online") == expected.get("online")


def test_publication_credits_carry_role_and_source_label(case, built) -> None:
    for expected, actual in zip(
        case["publications"], built["publications"], strict=True
    ):
        assert actual.get("credits", []) == expected["credits"]
        for credit in actual.get("credits", []):
            assert credit["role"] in ROLE_VOCABULARY


def test_contributions_carry_their_own_roles_and_scope(case, built) -> None:
    for expected, actual in zip(
        case["publications"], built["publications"], strict=True
    ):
        assert actual.get("contributions", []) == expected["contributions"]


def test_review_flags_are_explicit_and_readable(case, built) -> None:
    for expected, actual in zip(
        case["publications"], built["publications"], strict=True
    ):
        assert actual.get("reviewFlags", []) == expected["reviewFlags"]
        for flag in actual.get("reviewFlags", []):
            assert set(flag) == {"code", "detail"}
            assert flag["detail"].strip()


def test_name_variants_stay_unresolved(case, built) -> None:
    assert built.get("nameVariants", []) == case["nameVariants"]
    for variant in built.get("nameVariants", []):
        assert variant["status"] == "unresolved"
        assert variant["name"] != variant["variantOf"]
        assert variant["name"] in variant["sourceContext"]


# --- Rules that must not overreach -----------------------------------------


def test_no_relation_is_asserted_between_publications_of_one_page(built) -> None:
    """Co-occurrence on one source page is the only statement the array makes.
    A translation or edition relation would need separate review evidence."""
    for publication in built["publications"]:
        assert "translationOf" not in publication
        assert "editionOf" not in publication
        assert "exampleOfWork" not in publication


def test_a_page_without_a_publication_header_gets_no_publication_layer(
    attested_places,
) -> None:
    built = build_page_publications(
        page_id=1,
        text="\"Some article title\" in ''Journal'' [Berlin], pp. 3-4",
        page_title="Some article",
        categories=["Essays / Individual Essays (German)"],
        attested_places=attested_places,
    )
    assert built == {}


def test_attested_place_stock_is_available(attested_places) -> None:
    assert "Bloemfontein" in attested_places
    assert "Kaapstad (Capetown)" in attested_places


def test_the_flat_publisher_follows_the_publication_imprint(
    case, source_text, attested_places
) -> None:
    """The flat compatibility field takes the imprint publisher of the first
    publication whose header also names a place, so both layers agree."""
    expected = next(
        (
            publication["publisher"]
            for publication in case["publications"]
            if publication.get("publisher") and publication.get("places")
        ),
        None,
    )
    assert imprint_publisher(source_text, attested_places) == expected


def test_a_country_only_header_yields_no_flat_publisher(attested_places) -> None:
    """A header without a place does not settle whether its single segment is a
    publisher, a place or a country, so it produces no publisher assertion."""
    film = "'''[1984]: Czechoslovakia'''\n\n''Sach mat'' [Schachnovelle]"
    assert imprint_publisher(film, attested_places) is None


# --- Cross-references, sets and chained credits -----------------------------
# Exact source blocks of pages 4916, 818 and 4916 (again), quoted from the
# delivered wiki text.

GRAPHIC_NOVEL_BLOCK = (
    "'''[2016]: Knesebeck GmbH & Co. Verlag, München'''\n\n"
    "''Die Schachnovelle nach Stefan Zweig''. A graphic novel by Thomas Humeau "
    "adapted into German by Anja Kootz. 120p. Hundreds of cColor illustrations. "
    "See: [[Le Joueur d'échecs]] [2015]\n"
)
SET_REFERENCE_BLOCK = (
    "'''[2000]: Lijiang Chubanshe, Guilin''' \n\n"
    "''Da tanxianjia: Maizhelun, Gelunbu'' [Große Abenteuer: Magellan, Columbus, "
    "i.e. Amerigo Vespucci]. Translated by Mingjia Huang and Maoping Wei. 269p. "
    "See: [[Ciweige zhuanji jinghua]]. Vol. 3\n"
)
SERIES_BLOCK = (
    "'''[2016]: Aionas Verlag, Weimar'''\n\n"
    "''Schachnovelle''.  52/(1)p. 1st edition. Paperback edition "
    "[Bibliothek der Weltliteratur]\n"
)


def _single_publication(text: str, attested_places: set[str]) -> dict:
    built = build_page_publications(
        page_id=1,
        text=text,
        page_title="Test",
        categories=[],
        attested_places=attested_places,
    )
    assert built["publicationCount"] == 1
    return built["publications"][0]


def test_a_see_reference_is_not_a_series(attested_places) -> None:
    """The bracket after a "See" link is the target page and its date; reading
    it as a series gave the graphic novel the series of its French original."""
    publication = _single_publication(GRAPHIC_NOVEL_BLOCK, attested_places)
    assert "series" not in publication
    assert "note" not in publication


def test_a_see_reference_to_a_set_with_a_volume_is_the_series(attested_places) -> None:
    publication = _single_publication(SET_REFERENCE_BLOCK, attested_places)
    assert publication["series"] == "Ciweige zhuanji jinghua"
    assert publication["seriesVolume"] == "3"


def test_the_bracket_closing_the_extent_statement_stays_the_series(
    attested_places,
) -> None:
    publication = _single_publication(SERIES_BLOCK, attested_places)
    assert publication["series"] == "Bibliothek der Weltliteratur"


def test_the_graphic_novel_credits_its_author_and_its_translator(
    attested_places,
) -> None:
    """The label "A graphic novel by" credits the publication to its author,
    and the chained "adapted into German by" names the translator instead of
    running on from the first name."""
    publication = _single_publication(GRAPHIC_NOVEL_BLOCK, attested_places)
    assert publication["credits"] == [
        {
            "role": "author",
            "name": "Thomas Humeau",
            "creditLabel": "A graphic novel by",
        },
        {
            "role": "translator",
            "name": "Anja Kootz",
            "creditLabel": "adapted into German by",
        },
    ]
