"""Regression checks for page-level parsing decisions."""

import importlib

import pytest
from lib.config import STEP_02_OUTPUT, load_csv


@pytest.fixture(scope="module")
def parser():
    return importlib.import_module("03_parse_entries")


def _row(**overrides):
    row = {
        "page_id": "2979",
        "page_namespace": "0",
        "page_title": "",
        "text_id": "",
        "blob_id": "",
        "content": "",
    }
    row.update(overrides)
    return row


def test_blanked_page_keeps_its_title(parser) -> None:
    parsed = parser.process_entry(_row(page_title="A unidade espiritual do mundo"))
    assert parsed["title"] == "A unidade espiritual do mundo"
    assert parsed["raw_content"] == ""


def test_blanked_page_without_title_stays_empty(parser) -> None:
    assert parser.process_entry(_row())["title"] == ""


def test_blanked_page_title_wiki_markup_is_stripped(parser) -> None:
    assert parser.process_entry(_row(page_title="''A unidade''"))["title"] == (
        "A unidade"
    )


@pytest.mark.usefixtures("required_intermediates")
def test_approximate_year_header_is_not_used_as_title() -> None:
    parser = importlib.import_module("03_parse_entries")
    row = next(item for item in load_csv(STEP_02_OUTPUT) if item["page_id"] == "54")
    parsed = parser.process_entry(row)
    assert parsed["title"] == "Ungeduld des Herzens (VIST)"


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        ('"Buchmendel". See: Book-Mendel', "cross-reference"),
        (
            '"Ist die Geschichte gerecht?" See: Etwas über Macht und Moral',
            "cross-reference",
        ),
        (
            "Translated by Eugen Relgis. 248p. Bucureşti: Editura Ştiinţifică, 1996 "
            "(Ardealul). [See H 670, G 131 & H 490, G 445. See G 201, 491, 492]",
            "cross-reference",
        ),
        (
            '"Die Monotonisierung der Welt" in Neue Freie Presse [Wien], '
            "31 January 1925, pp. (1)-4",
            "citation",
        ),
        (
            '"Huatielu jueding shengfu de yi shun" [Die Weltminute von Waterloo] in:',
            "citation",
        ),
        ("in Leipziger Volkszeitung [Leipzig], 18 July 1996 [Kultur]", "citation"),
        ("Aufbau / Reconstruction [New York]. Zweig references, 1942-1966", "citation"),
        ("Translated by Jaan Kross. 285/(3)p. Tallinn: Eesti Raamat, 1988", "credit"),
        ("(8)p. Amsterdam: Uitgeverji Allert de Lange, (1939) [100 copies]", "extent"),
        ("No. 63. Jerusalem: Jüdischer Verlag, 1982", "imprint"),
        ("[No date indicated]: Latino Americana, Ciudad de México", "header"),
        ("[1]. 1934: Herbert Reichner Verlag, Wien", "header"),
        ("[I].", "header"),
        ("Volume:", "label"),
        ("Correspondence", "label"),
        ("[Magellan. Der Mann und seine Tat]", "bracket"),
        ('"Widerstand der Wirklichkeit" [Individual story]', "annotation"),
        ('"Deutschlands Janusantlitz". A ca. 1939 typescript', "annotation"),
    ],
)
def test_non_title_lines_are_classified(parser, candidate, expected) -> None:
    assert parser.non_title_class(candidate) == expected


@pytest.mark.parametrize(
    "title",
    [
        "Der Flüchtling. Episode vom/am Genfer See (VIST)",
        "Stefan Zweig, Leben und Werk",
        "Stefan Zweig: Farewell to Europe",
        '"Der große Europäer" Stefan Zweig. Ein Dichter als Mittler zwischen den Kulturen',
        "Amerigo / Amerigo. Die Geschichte eines historischen Irrtums",
        "Stefan Zweig, 1881-1942. Centenary Symposium",
        "Riverdale [pseudonym]",
    ],
)
def test_titles_are_not_classified_as_statements(parser, title) -> None:
    assert parser.non_title_class(title) is None


def test_a_cross_reference_line_gives_way_to_the_page_title(parser) -> None:
    """Page 586 opens with the quoted title and a See reference."""
    row = _row(
        page_id="586",
        page_title="Buchmendel",
        content='\\"Buchmendel\\". See: [[Book-Mendel]]\n\n[[Category:Fiction]]',
    )
    assert parser.process_entry(row)["title"] == "Buchmendel"


def test_a_section_heading_is_not_a_title(parser) -> None:
    """Page 185 opens with a wiki heading above its list."""
    row = _row(
        page_id="185",
        page_title="Casanova. (A Study in Self-Portraiture)",
        content="==Essays (English)==\n'''[1945]: Pushkin, London'''\n",
    )
    assert parser.process_entry(row)["title"] == (
        "Casanova. (A Study in Self-Portraiture)"
    )


@pytest.mark.usefixtures("required_intermediates")
def test_restored_page_takes_its_page_title() -> None:
    """Page 5839 is published from its last human revision, whose first line is
    the quoted title with a See reference."""
    parser = importlib.import_module("03_parse_entries")
    row = next(item for item in load_csv(STEP_02_OUTPUT) if item["page_id"] == "5839")
    assert parser.process_entry(row)["title"] == "La poesía de Goethe"
