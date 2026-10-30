"""The TEI delivery profile: schema, pointers and provenance of page 212.

Page 212 is a single-publication page whose place and publisher came from
the language model and whose other values were read by rule, so one record
carries both producers, a value from the page title and one from a category.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

lxml_etree = pytest.importorskip("lxml.etree")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import export_tei  # noqa: E402

SCHEMA = ROOT / "docs" / "schema" / "klawiter-tei.rng"
TEI = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


@pytest.fixture(scope="module")
def doc():
    return lxml_etree.fromstring(export_tei.serialize(export_tei.build([212])))


TEI_ALL = ROOT / "data" / "cache" / "tei_all-4.12.0.rng"


def test_the_export_validates_against_tei_all(doc) -> None:
    if not TEI_ALL.is_file():
        pytest.skip("tei_all is fetched by pipeline/acceptance.py")
    schema = lxml_etree.RelaxNG(lxml_etree.parse(str(TEI_ALL)))
    assert schema.validate(doc), schema.error_log


def test_the_export_validates_against_the_profile_schema(doc) -> None:
    schema = lxml_etree.RelaxNG(lxml_etree.parse(str(SCHEMA)))
    assert schema.validate(doc), schema.error_log


def test_every_pointer_resolves_inside_the_document(doc) -> None:
    ids = {el.get(XML_ID) for el in doc.iter() if el.get(XML_ID)}
    for el in doc.iter():
        for attr in ("resp", "source", "ana", "active", "passive"):
            for pointer in (el.get(attr) or "").split():
                assert pointer.startswith("#") and pointer[1:] in ids, (
                    el.tag,
                    attr,
                    pointer,
                )


def test_each_value_names_its_producer_and_its_passage(doc) -> None:
    imprint = doc.find(f".//{TEI}imprint")
    publisher = imprint.find(f"{TEI}publisher")
    assert publisher.text == "Editura Ştiinţifică", (
        "the source spelling, not a normalised one"
    )
    assert publisher.get("resp") == "#app-llm"
    assert imprint.find(f"{TEI}date").get("resp") == "#app-rules"
    seg = doc.find(f".//{TEI}seg[@{XML_ID}='{publisher.get('source')[1:]}']")
    assert seg.text == "Editura Ştiinţifică", "the passage is the value's own words"
    # Values from page metadata point to the title and the category of the source entry.
    assert doc.find(f".//{TEI}monogr/{TEI}title").get("source") == "#src-wiki-212-title"
    assert doc.find(f".//{TEI}textLang").get("source") == "#src-wiki-212-cat1"


def test_the_source_text_survives_whole_and_unread_text_stays_unmarked(doc) -> None:
    quote = doc.find(f".//{TEI}quote")
    text = "".join(quote.itertext())
    assert text.startswith("Translated by Eugen Relgis. 248p.")
    assert text.endswith("See G 201, 491, 492]")
    marked = " ".join(seg.text for seg in quote.iter(f"{TEI}seg"))
    assert "Ardealul" not in marked and not re.search(r"\b491\b", marked)


def test_a_wiki_only_export_carries_no_print_record(doc) -> None:
    assert not doc.findall(f".//{TEI}bibl[@type='printEntry']")


# Decisions E8 and E3 of 2026-10-30: page 54 is a work hub whose layer reads 31
# editions, page 1605 an author page whose layer reads nothing, page 1818 an
# author page with eight contributions, four of them in a container.
KINDS = [54, 1605, 1818]


@pytest.fixture(scope="module")
def kinds():
    return lxml_etree.fromstring(export_tei.serialize(export_tei.build(KINDS)))


def _structs(doc, page: int) -> list:
    return [
        s
        for s in doc.iterfind(f".//{TEI}body//{TEI}biblStruct")
        if s.get(XML_ID).startswith(f"SZDKLA.{page}.")
    ]


def _passage(doc, el) -> str:
    seg = doc.find(f".//{TEI}seg[@{XML_ID}='{el.get('source')[1:]}']")
    return "".join(seg.itertext())


def test_the_page_kinds_validate_against_both_schemas(kinds) -> None:
    profile = lxml_etree.RelaxNG(lxml_etree.parse(str(SCHEMA)))
    assert profile.validate(kinds), profile.error_log
    if TEI_ALL.is_file():
        tei_all = lxml_etree.RelaxNG(lxml_etree.parse(str(TEI_ALL)))
        assert tei_all.validate(kinds), tei_all.error_log


def test_a_work_hub_gives_the_publications_its_entry_yields(kinds) -> None:
    structs = _structs(kinds, 54)
    assert len(structs) == len(export_tei.load_layer(54)) == 31
    first = structs[0]
    assert first.get("corresp") == "klawiter:publication/54-1939-a"
    assert first.find(f"{TEI}analytic") is None
    assert first.find(f".//{TEI}author") is None, "a work hub names no author"
    date = first.find(f".//{TEI}imprint/{TEI}date")
    assert (date.get("when"), _passage(kinds, date)) == ("1939", "1939")
    passive = [
        r.get("passive")
        for r in kinds.iterfind(f".//{TEI}relation[@active='#src-wiki-54']")
    ]
    assert passive == [f"#{s.get(XML_ID)}" for s in structs]


def test_an_author_page_is_a_person_and_no_publication_of_its_own(kinds) -> None:
    person = kinds.find(
        f".//{TEI}listPerson/{TEI}person[@{XML_ID}='SZDKLA.1605.person']"
    )
    name = person.find(f"{TEI}persName")
    assert name.text == "Cai, Yuanhuang"
    assert name.get("source") == "#src-wiki-1605-title"
    assert person.get("corresp") == "klawiter:entry/1605"
    # The layer reads no contribution from page 1605, so none is invented from
    # its flat record, whose title is the person's name.
    assert export_tei.load_layer(1605) == []
    assert _structs(kinds, 1605) == []
    passive = [
        r.get("passive")
        for r in kinds.iterfind(f".//{TEI}relation[@active='#src-wiki-1605']")
    ]
    assert passive == ["#SZDKLA.1605.person"]


def test_contributions_point_to_their_person_and_their_container(kinds) -> None:
    structs = _structs(kinds, 1818)
    assert len(structs) == 8
    for s in structs:
        authors = s.findall(f".//{TEI}author")
        assert [a.get("ref") for a in authors] == ["#SZDKLA.1818.person"]
        # The first category the page-kind rule names: Authors (Croatian).
        assert authors[0].get("source") == "#src-wiki-1818-cat1"
    article = next(s for s in structs if s.get("corresp").endswith("1818-1965-a"))
    title = article.find(f"{TEI}analytic/{TEI}title[@level='a']")
    assert title.text.startswith("Romain Rolland et Stefan Zweig. Les Années")
    monogr = article.find(f"{TEI}monogr")
    container = monogr.find(f"{TEI}title")
    assert container.get("level") is None, "journal or book, the layer does not say"
    assert (container.text, _passage(kinds, container)) == ("Filološki pregled",) * 2
    pages = monogr.find(f"{TEI}biblScope[@unit='page']")
    assert (pages.text, _passage(kinds, pages)) == ("(153)-180",) * 2
    assert monogr.find(f"{TEI}biblScope[@unit='issue']").text == "I-II"
    assert monogr.find(f"{TEI}imprint/{TEI}pubPlace").text == "Beograd"
    book = next(s for s in structs if s.get("corresp").endswith("1818-1970-a"))
    assert book.find(f"{TEI}analytic") is None
    assert book.find(f"{TEI}monogr/{TEI}author") is not None
    assert book.find(f"{TEI}monogr/{TEI}title").get("level") == "m"
