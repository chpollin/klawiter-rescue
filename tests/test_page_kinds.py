"""The wiki page kind of a namespace-0 page, read by rule from the source.

Unit cases use verbatim source excerpts of the named pages (dump form, from
data/intermediate/04_classified.csv); the corpus checks run over the published
frontend dataset and the classified source rows.
"""

from __future__ import annotations

import importlib

import pytest
from lib.encoding import unescape_dump_quotes
from lib.page_kinds import WIKI_PAGE_KINDS, classify_wiki_page

# Page 7460, the compiler's note that defines VIST.
VIST_TEXT = (
    "'''Note:'''  VIST = Volumes / Individual Stories / Translations\n\n"
    "'''Volumes:'''\n\n"
    "'''[1922]: Lehmannsche Verlagsbuchhandlung (Lehmann & Schulze Verlag), "
    "Dresden'''\n\n[[Category:Fiction / Volumes (German)]]"
)
# Page 448, one Czech translation with its publications (first header).
EDITION_TEXT = (
    "'''[1968]: Svoboda, Praha [Prague]'''\n\n''Netrpělivost srdce'' "
    "[Ungeduld des Herzens]. Translated by Božena Koseková. 326/(2)p. \n\n"
    "[[Category:Fiction / Volumes (Czech)]]\n"
    "[[Category:Fiction / Individual Stories (Czech)]]"
)
# Page 1148, a secondary-literature author with the article by that author.
AUTHOR_TEXT = (
    '<lst type=bracket start=1>\n\\"Bian houji\\" in [[Ciweige sanwen xuan]] '
    "[Tianjin, 2002], No. 22, pp. 312-317 [Endnotes to a collection of selected "
    "essays by Stefan Zweig]\n</lst>\n\n"
    "[[Category:Secondary Literature / Authors (Chinese)]]"
)
# Page 7459, an (IS) page whose whole body points to the VIST page.
POINTER_TEXT = (
    "'''See:''' [[Brief einer Unbekannten (VIST)]]\n\n\n"
    "[[Category:Fiction / Individual Stories (German)]]"
)


def _kind(title: str, text: str, categories: list[str]) -> dict:
    return classify_wiki_page(title, text, categories)


def test_a_vist_page_is_a_work_hub_with_the_compilers_note() -> None:
    result = _kind(
        "Brief einer Unbekannten (VIST)", VIST_TEXT, ["Fiction / Volumes (German)"]
    )
    assert result["wikiPageKind"] == "work-hub"
    assert result["wikiPageKindRule"] == "vist-title"
    title, note = result["wikiPageKindEvidence"]
    assert title == {"sourceField": "pageTitle", "sourceValue": "(VIST)"}
    assert VIST_TEXT[note["sourceStart"] : note["sourceEnd"]] == note["sourceValue"]
    assert note["sourceValue"] == "VIST = Volumes / Individual Stories / Translations"


def test_a_german_work_page_listing_its_translations_is_a_work_hub() -> None:
    """Page 35, Maria Stuart, lists the translations of the biography."""
    text = (
        "'''[1935]: Bermann-Fischer Verlag, Stockholm / Uitgeverij Allert de "
        "Lange, Amsterdam / Querido Verlag, Amsterdam'''\n\n''Maria Stuart''. "
        "398p. [Forum-Bücher, (4)].\n\n\n'''Translations:'''\n\n'''Bulgarian:''' "
        "[[Mariia Stiuart. Roman]]\n"
    )
    result = _kind(
        "Maria Stuart",
        text,
        ["Collected and Selected Works", "Historical Studies / Volumes (German)"],
    )
    assert result["wikiPageKind"] == "work-hub"
    assert result["wikiPageKindRule"] == "translations-section"
    heading = result["wikiPageKindEvidence"][0]
    assert text[heading["sourceStart"] : heading["sourceEnd"]] == "'''Translations:'''"


def test_a_translations_heading_of_a_secondary_title_makes_no_hub() -> None:
    """Page 2154 transcribes the print volume's contents; its section headed
    Translations lists entry ranges, not translations of a work."""
    text = "'''Translations'''\n<lst>\nAlbanian, 170-171, p. 125\n</lst>\n"
    result = _kind(
        "Stefan Zweig. An International Bibliography",
        text,
        ["Secondary Literature / Titles (English)"],
    )
    assert result["wikiPageKind"] == "edition-page"


def test_one_item_in_one_language_is_an_edition_page() -> None:
    result = _kind(
        "Netrpělivost srdce",
        EDITION_TEXT,
        ["Fiction / Volumes (Czech)", "Fiction / Individual Stories (Czech)"],
    )
    assert result["wikiPageKind"] == "edition-page"
    assert result["wikiPageKindRule"] == "item-category"
    assert {e["sourceValue"] for e in result["wikiPageKindEvidence"]} == {
        "Fiction / Volumes (Czech)",
        "Fiction / Individual Stories (Czech)",
    }


def test_an_authors_category_makes_an_author_page() -> None:
    result = _kind(
        "Qian, Chunqi", AUTHOR_TEXT, ["Secondary Literature / Authors (Chinese)"]
    )
    assert result["wikiPageKind"] == "author-page"
    assert result["wikiPageKindRule"] == "authors-category"


def test_an_author_category_beside_a_work_title_stays_undetermined() -> None:
    """Page 6840 is filed as an author and as a volume of Zweig's essays under
    a title that names no person."""
    result = _kind(
        "Stefan Zweig. L'Esprit européen en exil",
        "'''[2020]: Éditions Bartillat, Paris'''\n\n''Stefan Zweig. L'Esprit "
        "européen en exil: Essais, discours, entretiens (1933-1942)''.",
        ["Essays / Volumes (French)", "Secondary Literature / Authors (French)"],
    )
    assert result["wikiPageKind"] == "undetermined"
    assert result["wikiPageKindRule"] == "conflicting-categories"


def test_a_translated_author_is_an_author_page_and_a_translated_work_is_not() -> None:
    """Page 792 is indexed under the author Zweig translated, page 6425 under
    author and work."""
    author = _kind(
        "Barbusse, Henri",
        "'''[1932]: Rascher Verlag, Zürich/Leipzig/Stuttgart'''\n\n''Die "
        "Schutzflehenden. Der Roman  einer Vorkriegsjugend'' . Translated with an "
        "afterword by Stefan Zweig. 247p.",
        ["Translations by Zweig"],
    )
    assert author["wikiPageKind"] == "author-page"
    assert author["wikiPageKindRule"] == "translated-author"
    work = _kind(
        "Verhaeren, Emile / Rembrandt",
        "'''[1912]: Insel-Verlag, Leipzig'''\n\n''Rembrandt''. 112p.",
        ["Translations by Zweig"],
    )
    assert work["wikiPageKind"] == "edition-page"


def test_a_page_that_only_points_elsewhere_is_a_cross_reference_page() -> None:
    result = _kind(
        "Brief einer Unbekannten (IS)",
        POINTER_TEXT,
        ["Fiction / Individual Stories (German)"],
    )
    assert result["wikiPageKind"] == "other"
    assert result["wikiPageKindRule"] == "cross-reference-page"
    (statement,) = result["wikiPageKindEvidence"]
    assert statement["sourceValue"] == "'''See:''' [[Brief einer Unbekannten (VIST)]]"
    assert statement["sourceStart"] == 0


@pytest.mark.parametrize(
    ("title", "text", "categories", "rule"),
    [
        # Page 426: one translation filed under three language labels.
        (
            "Nestrpljivo srce",
            "'''[1956]: Matica Srpska, Novi Sad'''\n\n''Nestrpljivo srce'' "
            "[Ungeduld des Herzens]. Translated by Kaćuša Maletin-Avakuinović. "
            "304p. [Reprinted 1960]",
            [
                "Fiction / Volumes (Croatian)",
                "Fiction / Volumes (Serbian)",
                "Fiction / Volumes (Serbo-Croatian)",
            ],
            "several-category-languages",
        ),
        # Page 1142 carries nothing but its category.
        (
            "Liu da shi",
            "[[Category:Historical Studies / Chinese]]",
            ["Historical Studies / Chinese"],
            "no-source-body",
        ),
        # Page 6781: the category link is broken, so the page has none.
        (
            "Riede, Peter",
            '\\"Revolte gegen die Zeit und den Kriegsdienst\\" in [[Der Zwang. '
            "Eine Novelle]] [Frankfurt am Main/Wien/Zürich, 2020], No. 2, pp.  "
            "85-92\n\n\n[Category:Secondary Literature / Authors (German)]]",
            [],
            "no-category",
        ),
    ],
)
def test_cases_no_rule_decides_are_undetermined(title, text, categories, rule) -> None:
    result = _kind(title, text, categories)
    assert result["wikiPageKind"] == "undetermined"
    assert result["wikiPageKindRule"] == rule


@pytest.mark.parametrize(
    ("title", "text", "categories", "rule"),
    [
        (
            "Angst / Play",
            "'''Angst'''. A dramatized version based on Zweig’s novella.",
            ["Films / Plays / Operas"],
            "adaptation-category",
        ),
        (
            "Der Amokläufer / Dramatic Reading",
            "'''[1930]: Theater in der Josefstadt, Wien/Vienna'''\n\n"
            '\\"Der Amokläufer\\". A dramatic reading by Alfred Beierle',
            ["Dramatic Readings"],
            "adaptation-category",
        ),
        (
            "1981 November 24-25: Stefan Zweig Symposium",
            "'''Stefan Zweig Symposium''' [24-25 November 1981].",
            ["Symposia and Exhibitions"],
            "event-category",
        ),
        (
            "Volksfront",
            '<lst type=bracket start=1>\n\\"Original-Interview mit Stefan Zweig\\" '
            "in ''Volksfront / The People's Front'' [Chicago]",
            ["Newspapers"],
            "periodical-category",
        ),
    ],
)
def test_adaptations_events_and_periodicals_are_other(
    title, text, categories, rule
) -> None:
    """Pages 2035, 4809, 968 and 2965."""
    result = _kind(title, text, categories)
    assert result["wikiPageKind"] == "other"
    assert result["wikiPageKindRule"] == rule


# Corpus checks over the published dataset.


def test_every_content_page_carries_a_kind_its_rule_and_evidence(ns0_entries) -> None:
    for entry in ns0_entries:
        kind = entry["wikiPageKind"]
        assert kind in WIKI_PAGE_KINDS
        assert entry["wikiPageKindRule"]
        if kind != "undetermined":
            assert entry["wikiPageKindEvidence"], (
                f"page {entry['sourcePageId']} names a kind without evidence"
            )


def test_structural_pages_carry_no_kind(all_entries) -> None:
    for entry in all_entries:
        if entry["pageNamespace"] != 0:
            assert "wikiPageKind" not in entry


def test_the_meta_counts_the_kinds_of_every_content_page(
    frontend_data, ns0_entries
) -> None:
    counts = frontend_data["_meta"]["wikiPageKinds"]
    assert list(counts) == list(WIKI_PAGE_KINDS)
    assert sum(counts.values()) == len(ns0_entries)
    for kind, count in counts.items():
        assert count == sum(1 for e in ns0_entries if e["wikiPageKind"] == kind)


def test_text_evidence_points_into_the_source_text(classified_rows, ns0_by_id) -> None:
    checked = 0
    for row in classified_rows:
        entry = ns0_by_id.get(int(row["page_id"]))
        if entry is None:
            continue
        text = row["raw_content"]
        for evidence in entry["wikiPageKindEvidence"]:
            if evidence["sourceField"] != "sourceText":
                continue
            excerpt = text[evidence["sourceStart"] : evidence["sourceEnd"]]
            assert unescape_dump_quotes(excerpt) == evidence["sourceValue"]
            checked += 1
    assert checked, "no kind evidence names a source passage"


def test_the_coordinator_examples_keep_their_kind(ns0_by_id) -> None:
    """Pages named in the brief of 2026-10-24: 448 one translation with four
    publications, 40 a VIST hub, 1148 a secondary-literature author page."""
    assert ns0_by_id[448]["wikiPageKind"] == "edition-page"
    assert ns0_by_id[40]["wikiPageKind"] == "work-hub"
    assert ns0_by_id[1148]["wikiPageKind"] == "author-page"
    assert ns0_by_id[35]["wikiPageKindRule"] == "translations-section"


def test_the_kind_reaches_the_canonical_graph(canonical_entries) -> None:
    content = [
        e
        for e in canonical_entries
        if e.get("pageNamespace") == 0 and not e.get("isRedirect")
    ]
    assert content
    assert all(e["wikiPageKind"] in WIKI_PAGE_KINDS for e in content)
    stage_05 = importlib.import_module("05_to_jsonld")
    assert stage_05.WIKI_PAGE_KINDS == WIKI_PAGE_KINDS
