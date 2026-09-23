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


# --- Imprint, series, contents and pagination repairs -----------------------
# Header and body lines quoted from the delivered wiki text of the page named
# in each test.


def test_a_co_imprint_keeps_every_publisher_and_place(attested_places) -> None:
    """Page 1725: two publishers with their own seats. Only the last seat used
    to survive, and the first seat was read into the publisher."""
    publication = _single_publication(
        "'''[1966]: Nauka i izkustvo, Sofija / DPK St. Dobrev-Strandzhata, Varna'''"
        "\n''Magelan'' [Magellan. Der Mann und seine Tat]. 220/(2)p.\n",
        attested_places,
    )
    assert publication["publisher"] == "Nauka i izkustvo"
    assert publication["places"] == ["Sofija", "Varna"]
    assert publication["imprints"] == [
        {"publisher": "Nauka i izkustvo", "place": "Sofija"},
        {"publisher": "DPK St. Dobrev-Strandzhata", "place": "Varna"},
    ]
    assert "reviewFlags" not in publication


@pytest.mark.parametrize(
    ("header", "publisher", "places"),
    [
        # Page 4269: a country qualifies the place before it.
        ("'''[2001]: Inko, Tyresö, Sweden'''", "Inko", ["Tyresö, Sweden"]),
        # Page 249: a USPS state code.
        (
            "'''[2008]: The Project Gutenberg Ebook, Salt Lake City, UT'''",
            "The Project Gutenberg Ebook",
            ["Salt Lake City, UT"],
        ),
        # Page 2524: the Mexican Distrito Federal.
        (
            "'''[1952]: Editorial Diana, México, D.F.'''",
            "Editorial Diana",
            ["México, D.F."],
        ),
        # Page 217: a legal-form suffix belongs to the publisher.
        (
            "'''[1963]: Editorial Juventud, S. A., Barcelona'''",
            "Editorial Juventud, S. A.",
            ["Barcelona"],
        ),
        # Page 1949: the imprint follows the closing bold.
        (
            "'''[2010]:''' The Continuum International Publishing Group, New York",
            "The Continuum International Publishing Group",
            ["New York"],
        ),
        # Page 4251: a bracket after a comma supplies the place.
        (
            "'''[1971]: Milliyet Yayınları, [Istanbul]'''",
            "Milliyet Yayınları",
            ["[Istanbul]"],
        ),
    ],
)
def test_the_place_keeps_its_qualifier_in_source_wording(
    header: str, publisher: str, places: list[str], attested_places
) -> None:
    publication = _single_publication(f"{header}\n''Title''. 64p.\n", attested_places)
    assert publication["publisher"] == publisher
    assert publication["places"] == places
    assert "reviewFlags" not in publication


def test_a_single_attested_place_is_no_publisher(attested_places) -> None:
    """Page 5057 names only the place; the location stock attests Oslo."""
    assert "Oslo" in attested_places
    publication = _single_publication(
        "'''[1930]: Oslo'''\n''Joseph Fouché''. 261p. Illustrated\n", attested_places
    )
    assert "publisher" not in publication
    assert publication["places"] == ["Oslo"]


def test_an_absence_mark_is_no_value(attested_places) -> None:
    """Page 4269: "[s.n.], [s.l.]" says that publisher and place are unknown."""
    publication = _single_publication(
        "'''[ca. 1996]: [s.n.], [s.l.]'''\n''La ŝaknovelo''. 39 leaves\n",
        attested_places,
    )
    assert "publisher" not in publication
    assert "places" not in publication
    assert "series" not in publication
    assert [flag["code"] for flag in publication["reviewFlags"]] == ["missing-location"]


def test_an_undecidable_boundary_stays_flagged(attested_places) -> None:
    """Page 2151: "New York" can be the state or the city, so the boundary
    between a publisher name with commas and the place stays open."""
    publication = _single_publication(
        "'''[1993]: Reed Library, State University College, Fredonia, New York'''"
        "\n''Title''. 12p.\n",
        attested_places,
    )
    assert [flag["code"] for flag in publication["reviewFlags"]] == [
        "imprint-segments-unresolved"
    ]


def test_a_body_imprint_under_a_date_only_header(attested_places) -> None:
    """Page 2569 states the imprint in the citation form under the header."""
    publication = _single_publication(
        "'''[1935]'''\n''Stuart Mária. Skót Királyö''.  Translated by Ferenc Kelen "
        "and Zoltán Horváth. Verses translated by György Rónay. 350p. Illustrated. "
        "Budapest: Rózsavölgyi, Athenaeum Kiadó, 1935\n",
        attested_places,
    )
    assert publication["publisher"] == "Rózsavölgyi, Athenaeum Kiadó"
    assert publication["places"] == ["Budapest"]
    assert "imprint" not in publication
    assert "reviewFlags" not in publication


def test_a_second_publisher_shares_the_place_before_it(attested_places) -> None:
    """Page 2569 names two publishers at one place under its 1957 header."""
    publication = _single_publication(
        "'''[1957]'''\n''Stuart Mária. Skót Királyö''. 343p. Illustrated. "
        "Budapest: Könnyvkiadó Franklin / Gondolat Kiadó, 1957 [Kelen translated "
        "pp. 1-163]\n",
        attested_places,
    )
    assert publication["publisher"] == "Könnyvkiadó Franklin"
    assert publication["places"] == ["Budapest"]


def test_the_imprint_after_the_closing_bold_is_read(attested_places) -> None:
    """Page 279 sets the whole statement on the header line; a label such as
    "First printing:" opens no imprint of its own."""
    publication = _single_publication(
        "'''[1942]'''. First printing: ''Schachnovelle''. 97p. 3 illustrations. "
        "Buenos Aires: Verlag Pigmalion, 1942\n",
        attested_places,
    )
    assert publication["publisher"] == "Verlag Pigmalion"
    assert publication["places"] == ["Buenos Aires"]
    assert "reviewFlags" not in publication


def test_a_parenthesized_year_matches_the_header(attested_places) -> None:
    """Page 279 gives an inferred date in parentheses, "(2002)"."""
    publication = _single_publication(
        "'''[2002]'''.  \\\"Die Schachnovelle\\\" in ''Wort und Sinn''. Edited by "
        "Peter Mettenleiter. Paderborn: Schöningh Verlag, (2002), pp. 288-290\n",
        attested_places,
    )
    assert publication["places"] == ["Paderborn"]


def test_the_header_line_may_end_in_the_imprint_without_its_year(
    attested_places,
) -> None:
    """Page 793 closes the header line with "Place: Publisher"; the bold states
    the year."""
    publication = _single_publication(
        "'''[1857]:''' ''Les Fleurs du mal''. 248p. Paris: Poulet-Malassis et de "
        "Broise\n",
        attested_places,
    )
    assert publication["publisher"] == "Poulet-Malassis et de Broise"
    assert publication["places"] == ["Paris"]


def test_a_yearless_imprint_followed_by_more_statements_stays_unread(
    attested_places,
) -> None:
    """Page 793 follows the 1868 imprint with a reprint of 1886; without the
    year the statement is read only as the last one on the header line."""
    publication = _single_publication(
        "'''[1868]:'''  ''Les Fleurs du Mal''. 411p. Paris: Michel Lévy Frères, "
        "Libraires Éditeurs. Reprinted: Paris: Calmann-Lévy, Éditeurs, 1886. "
        "References to the numbers of each poem are taken from the Michel Lévy "
        "edition\n",
        attested_places,
    )
    assert "places" not in publication
    assert [flag["code"] for flag in publication["reviewFlags"]] == ["missing-location"]


def test_an_imprint_in_prose_after_the_bold_stays_unread(attested_places) -> None:
    """Page 279 names the 1977 recording's publisher inside a sentence."""
    publication = _single_publication(
        "'''[1977]'''. ''Schachnovelle''. A CD recorded in 1977. Curd Jürgens "
        "reads a shortened version of the novella published by the S. Fischer "
        "Verlag, Frankfurt am Main. This is a recording\n",
        attested_places,
    )
    assert "places" not in publication


def test_a_page_locator_header_is_no_publication(attested_places) -> None:
    """Page 3757 sorts letters under year headings with the page range they
    occupy inside the one book the page describes."""
    built = build_page_publications(
        page_id=1,
        text=(
            "'''[2016]: Vittorio Klostermann Verlag, Frankfurt am Main'''\n"
            "''Thomas Mann - Stefan Zweig''. 464p.\n\n"
            "'''[1911]''', p. 12\n<lst type=bracket start=1>\nLetter, p. 12\n</lst>\n"
        ),
        page_title="Test",
        categories=[],
        attested_places=attested_places,
    )
    assert [p["id"] for p in built["publications"]] == ["klawiter:publication/1-2016-a"]


def test_an_unbalanced_series_bracket_keeps_name_and_gloss_apart(
    attested_places,
) -> None:
    """Page 5039 closes the gloss bracket with a parenthesis."""
    publication = _single_publication(
        "'''[1976]: Slovenský spisovateľ, Bratislava'''\n''Amok: novely vášní'' "
        "[Amok. Novellen einer Leidenschaft]. Translated by Eva Rosenbaumová. "
        "1st edition. 474p. [Tvorba národov [The Formation of Nations)]\n",
        attested_places,
    )
    assert publication["series"] == "Tvorba národov"
    assert publication["seriesGloss"] == "The Formation of Nations"
    assert "seriesVolume" not in publication


def test_the_series_volume_is_a_value_of_its_own(attested_places) -> None:
    """Page 1685 closes the series with a stray parenthesis after the volume;
    the series name must not end in the volume a consumer prints again."""
    publication = _single_publication(
        "'''[1998]: Dār al-Bashīr, Bayrūt/Dimashq'''\n\\\"Al-Armalah al-ʿāshiqah\\\" "
        "in ''ʿĀshiqāt fī ʾl-kharīf'' [Lovers in Autumn]. Translated by Ḥilmī "
        "Murād. 140p. [Series: Rawāʾiʿ al-adab al-ʿālamī (Masterpieces of World "
        "Literature), 14)]\n",
        attested_places,
    )
    assert publication["series"] == (
        "Rawāʾiʿ al-adab al-ʿālamī (Masterpieces of World Literature)"
    )
    assert publication["seriesVolume"] == "14"


def test_contribution_pages_stop_at_a_cross_reference(attested_places) -> None:
    """Page 141: the pages after "See:" belong to the referenced collection."""
    publication = _single_publication(
        "'''[1951]: Editorial Juventud, Barcelona'''\n''Obras completas''. 600p.\n"
        "'''Contents:'''\n<lst type=bracket start=1>\n"
        "Conocimiento casual de un oficio [Unvermutete Bekanntschaft mit einem "
        "Handwerk], pp. (339)-371. See: [[Gesamtausgabe des erzählerischen "
        "Werkes]] [1936], Vol. 2, No. 14, pp. 7-45\n</lst>\n",
        attested_places,
    )
    assert publication["contributions"] == [
        {
            "title": "Conocimiento casual de un oficio",
            "note": "Unvermutete Bekanntschaft mit einem Handwerk",
            "pages": "(339)-371",
            "pageStart": 339,
            "pageEnd": 371,
        }
    ]


def test_contents_end_at_a_reprint_list(attested_places) -> None:
    """Page 259: the "Reprinted in:" list names other publications."""
    publication = _single_publication(
        "'''[1993]: Fischer Taschenbuch Verlag, Frankfurt am Main'''\n"
        "''Geschichte eines Unterganges''. 72p.\n\n"
        "'''Contents:'''\n<lst type=bracket start=1>\n"
        "Geschichte eines Unterganges, pp. (7)-72\n</lst>\n\n"
        "'''Reprinted in:'''\n<lst type=bracket start=1>\n"
        "''Novellen''. Vol. 23. Wien: Österreichische Journal-Aktiengesellschaft, "
        "1910, pp. 149-192\n</lst>\n",
        attested_places,
    )
    assert [c["title"] for c in publication["contributions"]] == [
        "Geschichte eines Unterganges"
    ]
    assert "reviewFlags" not in publication


def test_contents_of_an_edition_in_another_language_stay_with_it(
    attested_places,
) -> None:
    """Page 2083 describes its French edition under a bold "French edition:"
    label without a year header; its contents are not the German book's."""
    publication = _single_publication(
        "'''[1993]: Residenz Verlag, Salzburg/Wien'''\n\n"
        "Edited by Klemens Renoldner, Hildemar Holl, and Peter Karlhuber. "
        "223/(1)p.\n\n"
        "'''Contents:'''\n<lst type=bracket start=1>\n"
        "Zu diesem Buch [The editors], p. 7\n</lst>\n\n"
        "'''French edition:'''\n\n"
        "'''Stefan Zweig, instants d'une vie. Images, textes, documents'''. "
        "223/(1)p. Illustrated. Paris: Éditions Stock, 1994\n\n"
        "'''Contents:'''\n<lst type=bracket start=153>\n"
        "Page (7): Avant-propos [By the editors]\n</lst>\n\n"
        "'''I. 1881-1914''', pp. 9-(51)\n<lst type=bracket start=154>\n"
        "Pages 18-21: “En souvenir de Theodor Herzl”\n</lst>\n",
        attested_places,
    )
    assert [c["title"] for c in publication["contributions"]] == ["Zu diesem Buch"]


def test_pagination_counts_the_unnumbered_pages(attested_places) -> None:
    """444/(3)p. declares 447 pages, so contents ending at (445) fit (page
    1891); contents that run past both components are flagged."""
    contents = (
        "'''Contents:'''\n<lst type=bracket start=1>\n"
        "Kazanova [Casanova], pp. (371)-(445)\n</lst>\n"
    )
    inside = _single_publication(
        f"'''[1993]: Kavkazskiĭ Krai, Stavropol’'''\n''Title''. 444/(3)p.\n{contents}",
        attested_places,
    )
    assert "reviewFlags" not in inside
    over = _single_publication(
        f"'''[1993]: Kavkazskiĭ Krai, Stavropol’'''\n''Title''. 440/(3)p.\n{contents}",
        attested_places,
    )
    assert [flag["code"] for flag in over["reviewFlags"]] == [
        "contents-pagination-exceeds-extent"
    ]


def test_the_country_list_is_the_vendored_natural_earth_list() -> None:
    """The cited source of the country qualifiers is the vendored topology."""
    from lib.patterns import NATURAL_EARTH_COUNTRY_NAMES

    topology = json.loads(
        (ROOT / "docs/vendor/countries-110m.json").read_text(encoding="utf-8")
    )
    names = {
        geometry["properties"]["name"]
        for geometry in topology["objects"]["countries"]["geometries"]
    }
    assert NATURAL_EARTH_COUNTRY_NAMES == names
