"""Regression tests on complete source records.

Every case is a page whose published record was wrong; the source text comes
from tests/record_sources.json, which test_source_tables checks against the
dump. The expectation is what the source documents, or None where it
documents nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

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
from lib.publications import (
    build_page_publications,
    load_attested_places,
    statement_bindings,
    unbound_flat_fields,
)
from lib.translations import translation_statements
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


# A flat place, publisher or translator of a page without a publication header
# stands only where its first statement carries it (a gap before a wrong value).


def _flat_values(text):
    return {
        "location": extract_location(text),
        "publisher": extract_publisher(text),
        "translator": extract_translator(text),
    }


@pytest.mark.parametrize(
    ("page_id", "field", "value"),
    [
        # The third printing of an "in:" list, not the first (Taiyuan/Xi'an).
        (635, "location", "Shanghai"),
        # A reprint of 2019; the essay appeared in Zürich in 1918.
        (6776, "location", "Wien"),
        # The town of a lecturer at a symposium held in Wien.
        (968, "location", "Budapest"),
        # A person's name, "Jeffrey B. Berlin", in the source citation.
        (1666, "location", "Berlin"),
        # "Wien/Leipzig/Zürich" of a reprint below the 1934 header.
        (53, "location", "Zürich"),
        # A translation credit ("Translated by the Editorial Juventud") is no
        # imprint, and Alfredo Cahn translated the second printing only.
        (5747, "publisher", "Juventud"),
        (5747, "translator", "Alfredo Cahn"),
    ],
)
def test_an_unbound_headerless_value_is_a_gap(record_sources, page_id, field, value):
    text = record_sources[page_id]["text"]
    values = _flat_values(text)
    assert values[field] == value
    assert field in unbound_flat_fields(text, values)


@pytest.mark.parametrize(
    ("page_id", "field", "value"),
    [
        # The bracket after the container title ("''Blätter …'' [Wien]").
        (4421, "location", "Wien"),
        # The first item of the "in:" list ("[Paris, 1937]").
        (720, "location", "Paris"),
        # A bracket without a comma ("[Beijing 2000]") and a credit in the
        # statement ("[Translated by Yan Zhu]").
        (1258, "location", "Beijing"),
        (1258, "translator", "Yan Zhu"),
        # The bold header of a numbered edition, "[1]. 1934: Herbert Reichner
        # Verlag, Wien".
        (53, "publisher", "Herbert Reichner Verlag"),
        # The imprint "Locarno: Armando Dadò Editore, 2009" of the statement.
        (1666, "publisher", "Armando Dadò Editore"),
        # The label word stays out of the value ("Paris: Éditions Hervas").
        (3439, "publisher", "Hervas"),
    ],
)
def test_a_bound_headerless_value_stays(record_sources, page_id, field, value):
    text = record_sources[page_id]["text"]
    values = _flat_values(text)
    assert values[field] == value
    assert field not in unbound_flat_fields(text, values)


def test_the_first_statement_ends_before_the_second_item(record_sources):
    bindings = statement_bindings(record_sources[635]["text"])
    lines = bindings["statement"].splitlines()
    assert len(lines) == 2
    assert lines[1].startswith("[[Ciweige wenji]] [Taiyuan/Xi'an, 1998]")
    assert bindings["places"] == ["Taiyuan/Xi'an"]


# The translations section becomes one statement per printing, each value
# with its span; what the rules cannot read stays absent.


def _translations(record_sources, page_id):
    return [
        {
            key: value
            for key, value in statement.items()
            if key not in {"spans", "sourceSlice"}
        }
        for statement in translation_statements(record_sources[page_id]["text"])
    ]


def test_each_printing_of_a_translation_is_a_statement(record_sources):
    # Page 7166, "Brügge": the French translation is printed twice, the first
    # Portuguese printing stands before the first number.
    statements = _translations(record_sources, 7166)
    assert statements[0] == {
        "language": "Bulgarian",
        "languageCode": "bg",
        "title": "Briuge",
        "container": "Portreti na evropeĭski pisateli",
        "place": "Sofija",
        "year": 1984,
    }
    french = [s for s in statements if s["language"] == "French"]
    assert [(s["place"], s["year"]) for s in french] == [
        ("Paris", 1996),
        ("Paris", 1998),
    ]
    portuguese = [s for s in statements if s["language"] == "Portuguese"]
    assert [s["container"] for s in portuguese] == [
        "Obras completas de Stefan Zweig, 1934-1950",
        "Obras completas de Stefan Zweig, 1960",
        "Obras de Stefan Zweig, 1934-1950",
    ]
    # A range of years is no publication year; it stays the raw statement.
    assert portuguese[0]["yearRaw"] == "1934-1950" and "year" not in portuguese[0]
    serbian = next(s for s in statements if s["language"].startswith("Serbian"))
    assert serbian["language"] == "Serbian (Serbo-Croatian)"
    assert {s["language"] for s in statements} >= {
        "Danish",
        "English",
        "Hungarian",
        "Spanish",
        "Swedish",
    }


def test_a_translated_book_reads_its_own_imprint_and_credit(record_sources):
    # Page 4411: the Arabic translation is a book, not a contribution, and its
    # title gloss is no container.
    (statement,) = _translations(record_sources, 4411)
    assert statement == {
        "language": "Arabic",
        "languageCode": "ar",
        "title": "Al-Sāqiṭūn",
        "place": "Dimashq [Damascus]",
        "publisher": (
            "Dār al-Yaqẓah al-ʿArabiyyah li-l-Taʾlīf waʾl-Tarjamah waʾl-Nashr "
            "bi-Sūriyyah"
        ),
        "year": 1950,
        "translator": "Fuʾād Ayyūb",
    }


def test_translations_split_at_double_slashes_and_keep_misprints_raw(record_sources):
    # Page 7224: two French translations, the second a book with its credit;
    # the Greek bracket prints the year as 19556.
    statements = _translations(record_sources, 7224)
    french = [s for s in statements if s["language"] == "French"]
    assert french[0]["container"] == "Souvenirs et rencontres"
    assert french[0]["yearRaw"] == "1951 and 1997" and "year" not in french[0]
    assert french[1]["translator"] == "Alzir Hella and Olivier Bouranc"
    assert french[1]["year"] == 2004 and "container" not in french[1]
    greek = next(s for s in statements if s["language"] == "Greek")
    assert greek["yearRaw"] == "19556" and "year" not in greek


def test_every_translation_value_is_the_text_of_its_span(record_sources):
    for page_id in (7139, 7166, 7203, 7224, 4411):
        text = record_sources[page_id]["text"]
        for statement in translation_statements(text):
            for field, (start, end) in statement["spans"].items():
                if field == "language":
                    continue
                value = " ".join(unescape_dump_quotes(text[start:end]).split())
                assert str(statement[field]) == value, (page_id, field)


# Defect 14: a letter whose byte the dump lost becomes a gap, not a guess.


def _normalize_stage():
    import importlib

    return importlib.import_module("03c_normalize")


def test_a_title_with_a_lost_byte_is_a_gap(record_sources):
    """The dump's page title of page 2364 lost the byte A0 of the final "à";
    the page text spells the title intact, but the rule takes the page title."""
    title = record_sources[2364]["page_title"]
    assert title == "Estasi di libertÃ"
    row = {"title": title, "page_title": title, "translator": "Luciana Rotter"}
    assert _normalize_stage().gap_damaged_values(row) == ["title"]
    assert row["title"] == "" and row["page_title"] == title
    assert row["translator"] == "Luciana Rotter"
    assert row["encoding_damaged_fields"] == '["title"]'


def test_the_published_damaged_titles_are_gaps_with_a_hint(ns0_by_id, all_entries):
    by_page = {entry["sourcePageId"]: entry for entry in all_entries}
    for page_id in (2364, 7432):
        entry = by_page[page_id]
        assert "title" not in entry
        assert any(
            flag["code"] == "encoding-damaged" and flag["field"] == "title"
            for flag in entry["reviewFlags"]
        )
        assert {"gapField": "title", "gapRule": "damaged-letter"} in entry["ruleGaps"]
    assert "Estasi di libertà" in ns0_by_id[2364]["fullBibliographicEntry"]


# Defect 15: a whitespace run of the dump is one space in the value.


def test_a_credit_with_a_double_space_reads_as_the_wiki_shows_it(
    record_sources, ns0_by_id
):
    text = record_sources[384]["text"]
    assert "Translated by A.  Druktenis." in text
    raw = extract_translator(text)
    assert raw == "A.  Druktenis"
    row = {"translator": raw}
    _normalize_stage().unescape_row(row)
    assert row["translator"] == "A. Druktenis"
    assert ns0_by_id[384]["translator"] == "A. Druktenis"
    assert "A. Druktenis" in ns0_by_id[384]["fullBibliographicEntry"]


# Defect 16: a gap by rule is labelled as one.


def test_an_unbound_value_is_a_rule_gap_not_a_source_gap(ns0_by_id):
    entry = ns0_by_id[41]
    gaps = {gap["gapField"]: gap["gapRule"] for gap in entry["ruleGaps"]}
    assert gaps
    assert set(gaps.values()) == {"statement-bindings"}
    for field in gaps:
        assert entry["_provenance"][field] == "rule-gap"


# Defect 17: a category page of the same title neither blocks nor receives a
# main-namespace redirect.


def test_redirects_blocked_by_category_titles_resolve(frontend_data):
    redirects = frontend_data["redirects"]
    assert redirects["Correspondence / Volumes (Portuguese)"] == 2431
    assert redirects["Secondary Literature / Titles (Uzbek)"] == 5104
    assert redirects["Secondary Literature / Authors (Japanese)"] == 7475
    for key in ("Main", "Sidebar", "Mainpage"):
        assert key not in redirects


def test_redirects_into_category_titles_are_reported_unresolved():
    from lib.config import OUTPUT_UNRESOLVED_REDIRECTS

    report = json.loads(Path(OUTPUT_UNRESOLVED_REDIRECTS).read_text(encoding="utf-8"))
    reported = {item["pageId"]: item for item in report["redirects"]}
    assert reported[5211]["pageTitle"] == "Secondary Literature/ Titles (Thai)"
    assert reported[5211]["kind"] == "absent-target"
    for page_id in (6440, 7435):
        assert reported[page_id]["kind"] == "absent-target"


# Defect 18: a structure page names no author.


def test_category_pages_name_no_author(canonical_entries):
    by_page = {entry["sourcePageId"]: entry for entry in canonical_entries}
    for page_id in (232, 7432):
        assert "author" not in by_page[page_id]


# Defect 19: Gate 1 reads a lone attested place as a place, leaves the dump
# form, and a year heading before a page locator is no edition.


def _editions(record_sources, attested, page_id):
    from lib.editions import segment_page

    entry = record_sources[page_id]
    return {
        edition["@id"]: edition
        for edition in segment_page(
            page_id, entry["text"], entry["page_title"], attested
        )["editions"]
    }


def test_a_lone_attested_place_is_the_edition_place(record_sources, attested):
    for page_id, edition_id, place in (
        (4101, "klawiter:edition/4101-1947-a", "Beirut"),
        (4353, "klawiter:edition/4353-1931-a", "Stockholm"),
    ):
        edition = _editions(record_sources, attested, page_id)[edition_id]
        assert edition["schema:locationCreated"] == place
        assert "schema:publisher" not in edition


def test_edition_values_leave_the_dump_form_on_real_pages(record_sources, attested):
    editions = _editions(record_sources, attested, 2485)
    assert (
        editions["klawiter:edition/2485-2010-a"]["schema:publisher"]
        == 'Izdatel\'stvo "AST"'
    )
    editions = _editions(record_sources, attested, 2530)
    assert editions["klawiter:edition/2530-2018-a"]["schema:publisher"] == "Lind & Co."


def test_a_year_heading_before_a_page_locator_is_no_edition(record_sources, attested):
    editions = _editions(record_sources, attested, 3757)
    assert list(editions) == ["klawiter:edition/3757-2016-a"]
    publications = _publications(record_sources, attested, 3757)
    assert [p["id"] for p in publications] == ["klawiter:publication/3757-2016-a"]
