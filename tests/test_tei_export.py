"""The TEI delivery profile: schema, pointers and provenance of page 212.

Page 212 is a single-publication page whose place and publisher came from
the language model and whose other values were read by rule, so one record
carries both producers, a value from the page title and one from a category.
"""

from __future__ import annotations

import io
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
    buf = io.BytesIO()
    export_tei.build([212], with_print=False).write(
        buf, encoding="utf-8", xml_declaration=True
    )
    return lxml_etree.fromstring(buf.getvalue())


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
