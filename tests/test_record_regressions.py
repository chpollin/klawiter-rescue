"""Regression tests on complete source records.

Every case is a page whose published record was wrong; the source text comes
from tests/record_sources.json, which test_source_tables checks against the
dump. The expectation is what the source documents, or None where it
documents nothing.
"""

from __future__ import annotations

import pytest
from lib.encoding import unescape_dump_quotes
from lib.llm_extract import occurs_in_source, page_count_in_source
from lib.patterns import (
    extract_all_years,
    extract_language_from_category,
    extract_location,
    extract_publisher,
    extract_translator,
    extract_year,
    publisher_shape_ok,
)
from lib.publications import build_page_publications, load_attested_places
from lib.vocabulary import language_to_iso
from lib.wiki_parser import blank_translations_block, extract_categories


@pytest.fixture(scope="module")
def attested():
    return load_attested_places()


def _publications(record_sources, attested, page_id):
    entry = record_sources[page_id]
    categories, _ = extract_categories(entry["text"])
    layer = build_page_publications(
        page_id, entry["text"], entry["page_title"], categories, attested
    )
    return layer["publications"]


def _by_year(publications, year):
    (publication,) = [p for p in publications if p.get("year") == year]
    return publication


# Defect 1: an occurrence is a whole-word occurrence.


def test_a_word_fragment_is_no_occurrence():
    assert not occurs_in_source("Ka", "Translated by Katharina")
    assert occurs_in_source("Katharina", "Translated by Katharina")


@pytest.mark.parametrize(
    ("page_id", "fragment", "whole"),
    [
        (1941, "Matthew Pollard, Ka", "Karin Doerr"),
        (4340, "Dam", "Damascus"),
        (5950, "Mīshīl Wākī", "Mīshīl Wākīm"),
        (5951, "Mīshīl Wākīm and Quṣ", "Mīshīl Wākīm and Quṣayy Atāsī"),
    ],
)
def test_cached_model_fragments_are_refused(record_sources, page_id, fragment, whole):
    text = record_sources[page_id]["text"]
    assert not occurs_in_source(fragment, text)
    assert occurs_in_source(whole, text)


def test_a_model_page_count_needs_an_extent_statement(record_sources):
    text = record_sources[4340]["text"]
    assert page_count_in_source(207, text)
    # A page locator or the start of a range is no extent.
    assert not page_count_in_source(26, "in ''Journal'', No. 3 [2007], pp. 26-51")
    assert page_count_in_source(124, "124/(1)p. Cover illustration")


def test_a_rule_read_latin_extended_credit_keeps_its_letters(record_sources):
    # Page 448: the credit is read by rule, not left to the enrichment.
    assert extract_translator(record_sources[448]["text"]) == "Božena Koseková"


# Defect 2: dates of the subject are no publication years.


@pytest.mark.parametrize(
    ("page_id", "year"),
    [
        (4512, 2017),  # "[Stefan Zweig, 1881, died 1942, Austria]" glosses the title
        (972, 1981),  # "Stefan Zweig, 1881-1942" in the bold title
        (1066, 2002),  # the gloss date 1823 of a Sternstunden miniature
        (1092, 1983),  # "[Die Weltminute von Waterloo … 18. Juni 1815]"
        (1166, 1983),  # the frozen semantic case
        (94, 1949),  # '''[1949-1966]: Cassell''' is a publication period
        (7396, 1921),  # an unclosed quote must not hide "[22 May 1921]"
    ],
)
def test_publication_year_skips_subject_dates(record_sources, page_id, year):
    assert extract_year(record_sources[page_id]["text"]) == year


def test_url_and_print_run_numbers_are_no_years(record_sources):
    # Page 4779: "?p=2028" in a URL; page 279: "[2029.-2058. Tsd.]" thousands.
    assert extract_all_years(record_sources[4779]["text"]) == [2007]
    assert not [y for y in extract_all_years(record_sources[279]["text"]) if y > 2021]


# Defect 3: a publisher is a name, never prose or an editor credit.


def test_page_4512_has_no_publisher_place_or_subject_year(record_sources):
    text = record_sources[4512]["text"]
    assert extract_publisher(text) is None
    assert extract_location(text) is None  # Defect 4: "Stefan Zweig" is no place
    assert extract_year(text) == 2017


def test_page_103_reads_no_acknowledgement_as_publisher(record_sources):
    text = record_sources[103]["text"]
    assert extract_publisher(text) is None  # "I wish to express"
    assert extract_location(text) not in ("Moscow", "Moskva")


def test_editor_credits_and_sentences_are_no_publisher_shape():
    assert not publisher_shape_ok(
        "Eva von Seckendorff und Angelika Mundorff, hrsg. von"
    )
    assert not publisher_shape_ok("edited by Joan Fontcuberta")
    assert not publisher_shape_ok("I wish to express")
    assert not publisher_shape_ok("von Philipp Reclam jun")
    assert publisher_shape_ok("al-Dār al-Qawmiyyah li-l-Ṭibāʿah waʾl-Nashr")
    assert publisher_shape_ok("A Esfera dos Livros")
    assert publisher_shape_ok("“Hayastan” Hratarakch‘ut‘yun")


# Flat-field context class: affiliation prose and translation-section credits.


def test_an_affiliation_is_no_place(record_sources):
    # Page 6819: "a Delhi-based writer".
    assert extract_location(record_sources[6819]["text"]) is None


def test_a_translation_section_credit_is_not_the_originals(record_sources):
    # Page 272 (German): "Translated by Mien Labberton" credits the Dutch
    # translation listed in the translations section.
    text = record_sources[272]["text"]
    assert extract_translator(text) == "Mien Labberton"
    assert extract_translator(blank_translations_block(text)) is None


# Defects 6, 7 and 12: the publication layer of real pages.


def test_a_later_printing_is_no_edition_statement(record_sources, attested):
    publications = _publications(record_sources, attested, 675)
    # "124/(1)p. Cover illustration. 2nd edition, 1945; 3rd edition, 1946"
    assert "editionStatement" not in _by_year(publications, 1944)
    assert "editionStatement" not in _by_year(publications, 1981)
    page_4124 = _publications(record_sources, attested, 4124)
    # "2nd edition of 1936 published online" under the 1933 header.
    assert _by_year(page_4124, 1933).get("editionStatement") != "2nd edition"


def test_a_serialisation_note_is_no_container_or_series(record_sources, attested):
    publication = _by_year(_publications(record_sources, attested, 675), 1972)
    assert "container" not in publication
    assert "series" not in publication
    assert "note" not in publication


def test_a_doubtful_credit_keeps_its_mark(record_sources, attested):
    publication = _by_year(_publications(record_sources, attested, 675), 1972)
    (translator,) = [c for c in publication["credits"] if c["role"] == "translator"]
    assert translator["name"] == "Jacqueline Des Gouttes"
    assert translator["uncertain"] is True
    first = _by_year(_publications(record_sources, attested, 675), 1944)
    assert not any(c.get("uncertain") for c in first["credits"])


def test_credit_names_and_reprint_notes_are_no_series(record_sources, attested):
    for page_id in (2598, 2485):
        for publication in _publications(record_sources, attested, page_id):
            assert publication.get("series") not in (
                "Josef Polišenský",
                "Ivan Inozemtsev",
                "Ivan Inozemstev",
            )
    page_846 = _publications(record_sources, attested, 846)
    assert _by_year(page_846, 1965).get("series") != "Reprinted 1967"


def test_prefatory_pages_stay_in_the_extent_notation(record_sources, attested):
    extents = [
        p["extent"]
        for p in _publications(record_sources, attested, 892)
        if "extent" in p
    ]
    assert {"raw": "xi/237/(1)p.", "numbered": 237, "unnumbered": 1} in extents


# Defect 10: the dump's quote escape does not reach a value.


def test_a_value_leaves_the_dump_escape_behind(record_sources, attested):
    assert unescape_dump_quotes('Izdatel\'stvo \\"AST\\"') == 'Izdatel\'stvo "AST"'
    # An escaped backslash before a quote is unescaped once.
    assert unescape_dump_quotes('a\\\\\\"b') == 'a\\"b'
    for publication in _publications(record_sources, attested, 1982):
        assert "\\" not in publication.get("title", "")


# Defect 11: languages the closed list dropped.


def test_a_category_language_outside_the_old_list_is_kept(record_sources):
    categories, _ = extract_categories(record_sources[5657]["text"])
    language = extract_language_from_category(categories)
    # Page 5657 is categorized "(Tamil)", which the old closed list dropped.
    assert language == "Tamil"
    assert language_to_iso(language) == "ta"
