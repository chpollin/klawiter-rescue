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
        ('"Preface" to The Jewish Contribution to Civilization.', "contribution"),
        (
            "Kungliga Biblioteket - Sveriges Nationalbiblioteket, Stockholm. "
            "Hultenberg Archive. 2 volumes. Shelf number Acc. 2011/3. Five letters "
            "and one postcard from Stefan Zweig to Hugo Hultenberg",
            "holdings",
        ),
        (
            "Stefan Zweig to Hans Rosenkranz, 26 letters and 6 postcards, 1921-1933. "
            "This correspondence is located in the Jewish National Library in "
            "Jerusalem",
            "holdings",
        ),
        (
            "1 page, undated handwritten text, with Zweig’s signature. In the "
            "Schiller-Nationalmuseum und Deutsches Literaturarchiv, Marbach am "
            "Neckar, A: Gregor-Dellin, Mss. Anderer",
            "holdings",
        ),
        ("Antiquariat Richard Husslein, Postfach 1525, D-82144 Planegg", "address"),
        (
            "''Narrative Textanalyse von Stefan Zweigs 'Schachnovelle'''. "
            "Seminararbeit. Institut für Germanistik, Universität Marburg, "
            "Wintersemester 1986/1987",
            "thesis",
        ),
        (
            "www.ekathimerini.com/248252/article/ekathimerini/whats-on/"
            "leporella-athens-january-11-26",
            "url",
        ),
        ("Taken from the volume Kampf mit dem Dämon.", "note"),
        (
            "The following editions of ''Les Fleurs du mal'' are the ones quoted in "
            "[[Baudelaire, Charles / Individual Poems]]",
            "note",
        ),
        (
            "KH = Kelsea M. Halloran, a junior in the New York State University in "
            "Fredonia, to graduate in 2018",
            "note",
        ),
        (
            "Jacopo da Lentino / Giacomo di Lentini, ca. 1210 - ca. 1260. The sonnet "
            "was written ca. 1230",
            "note",
        ),
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
        'Stefan Zweig - Friderike Zweig. "Wenn einen Augenblick die Wolken '
        'weichen". Briefwechsel 1912-1942',
        "Die Zeit gibt die Bilder, ich spreche nur die Worte dazu. Stefan Zweig "
        "1881-1942",
        "Prolog und Epilog zu Shakespeares Sturm: Quasi und Phantasia",
        "Al-Hurūb ilā ʾllāh : nihāyat uktūbir 1910 : khātimah li-masraḥiyyat "
        'Tūlstūy "Waʾl-Nūr yasṭaʿ fī ʾl-ẓalām"',
    ],
)
def test_titles_are_not_classified_as_statements(parser, title) -> None:
    assert parser.non_title_class(title) is None


@pytest.mark.parametrize(
    ("candidate", "page_title", "categories", "expected"),
    [
        # Page 162 opens with its category as a bold label.
        (
            "Essays / Volumes (German)",
            "Die Monotonisierung der Welt. Aufsätze und Vorträge",
            ["Essays / Volumes (German)"],
            "label",
        ),
        # Page 1855 opens with the language of its first category.
        (
            "Bosnian",
            "Balzak. Romansirana biografija",
            [
                "Historical Studies / Volumes (Bosnian)",
                "Historical Studies / Volumes (Serbo-Croatian)",
            ],
            "label",
        ),
        # Page 6060 opens with the authors of the article below it.
        (
            "Christina-Maria Hochreiter and Armin Eidherr.",
            "Hochreiter, Christina-Maria",
            ["Secondary Literature / Authors (German)"],
            "credit",
        ),
        # The credit rule reads the natural name order only; a name in page-title
        # order is outside it (page 7468).
        (
            "Al-Nimr, Hudā ʿAbd al-Raḥmān",
            "Al-Nimr, H.",
            ["Secondary Literature / Authors (Arabic)"],
            None,
        ),
        # A language label is read only against the page's own categories.
        ("Bosnian", "Balzak", [], None),
    ],
)
def test_candidates_are_read_against_their_page(
    parser, candidate, page_title, categories, expected
) -> None:
    assert parser.non_title_class(candidate, page_title, categories) == expected


def test_a_list_heading_is_not_a_title(parser) -> None:
    """Page 513 opens with the bold italic heading of its first index group."""
    row = _row(
        page_id="513",
        page_title="Index by German Title / Individual Stories (Chinese)",
        content="'''''Der Amokläufer'''''\n<lst type=ul>\n[[Gu]]\n</lst>\n",
    )
    assert parser.process_entry(row)["title"] == (
        "Index by German Title / Individual Stories (Chinese)"
    )


def test_a_category_tail_is_not_a_title(parser) -> None:
    """Page 3923 consists of a broken category link and its tail."""
    row = _row(
        page_id="3923",
        page_title=(
            "1993 February 27 - 28: Stefan Zweig (1881-1942) oder Das Gewissen "
            "gegen die Gewalt"
        ),
        content="[[Category:Symposia and ]]Exhibitions",
    )
    assert parser.process_entry(row)["title"] == row["page_title"]


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
