"""Break copies of the TEI export on purpose and report which check rejects each.

Regime: script pipeline. The mutation suite of milestone D1 (`knowledge/plan.md`):
a check that never fails proves nothing, so each mutation below writes one
fault an exporter could plausibly make into a copy of a real export, and the
checks of `pipeline/acceptance.py` must reject every copy.

Data flow: the bytes of an export and the canonical records of its pages go
into `run()`. The checks run once on the unaltered export, then on each
mutant; a mutation is caught by the checks that fail on the mutant but not on
the original (or fail more often there). `pipeline/acceptance.py` calls
`run()` on the export it built and passes its own checks, with the profile
schema and without tei_all; `tests/test_tei_mutations.py` runs it on samples.

Each mutation picks its target in the document by structure, never by a
page number, so that it applies to the full export and to any sample with an
edition page. The values it alters are ones the canonical data fix (imprint
values, the source text), so that a mutation is a fault and not a second
valid reading.

Usage: python -m uv run python pipeline/tei_mutations.py [--pages 212 3]
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Callable

import export_tei
from lxml import etree

TEI_NS = export_tei.TEI_NS
NS = {"t": TEI_NS, "re": "http://exslt.org/regular-expressions"}
T = f"{{{TEI_NS}}}"
XML_ID = export_tei.XML_ID
SEG_REF = re.compile(r"#(src-wiki-\d+-s\d+)")

# The values every check of the canonical data compares, in both record shapes.
IMPRINT_VALUES = "//t:body//t:biblStruct/t:monogr/t:imprint/*[@resp]"

Check = Callable[[bytes, dict[int, dict]], list[dict]]


def _first(doc: etree._Element, xpath: str) -> etree._Element | None:
    found = doc.xpath(xpath, namespaces=NS)
    return found[0] if found else None


def _page(el: etree._Element) -> int | None:
    """The page an element belongs to, from the nearest identifier above it."""
    for node in el.iterancestors():
        m = re.match(r"(?:src-wiki-|SZDKLA\.)(\d+)", node.get(XML_ID) or "")
        if m:
            return int(m.group(1))
    m = re.match(r"(?:src-wiki-|SZDKLA\.)(\d+)", el.get(XML_ID) or "")
    return int(m.group(1)) if m else None


def _other_char(ch: str) -> str:
    return "x" if ch != "x" else "y"


def _unmarked(
    doc: etree._Element, pattern: str
) -> tuple[etree._Element, bool, str] | None:
    """The first text of an entry outside every passage that matches `pattern`.

    Returns the element holding the text, whether it is that element's tail,
    and the text; the text stands directly in a quote, so no seg encloses it.
    """
    for node in doc.xpath(
        f"//t:standOff//t:quote/text()[re:test(., '{pattern}')]", namespaces=NS
    ):
        return node.getparent(), node.is_tail, str(node)
    return None


def _set_text(owner: etree._Element, is_tail: bool, text: str) -> None:
    if is_tail:
        owner.tail = text
    else:
        owner.text = text


def source_char(doc: etree._Element) -> etree._Element | None:
    """One letter of Klawiter's text, outside any passage, is replaced."""
    found = _unmarked(doc, "[A-Za-z]")
    if found is None:
        return None
    owner, is_tail, text = found
    i = next(i for i, ch in enumerate(text) if ch.isalpha())
    _set_text(owner, is_tail, text[:i] + _other_char(text[i]) + text[i + 1 :])
    return owner


def resp_swapped(doc: etree._Element) -> etree._Element | None:
    """A value of the language model is ascribed to the rules, or the reverse."""
    el = _first(doc, f"{IMPRINT_VALUES}[@resp='#app-llm']")
    if el is None:
        el = _first(doc, f"{IMPRINT_VALUES}[@resp='#app-rules']")
    if el is None:
        return None
    el.set("resp", "#app-rules" if el.get("resp") == "#app-llm" else "#app-llm")
    return el


def ana_changed(doc: etree._Element) -> etree._Element | None:
    """A value's statement state is raised to confirmed, or lowered from it."""
    el = _first(doc, IMPRINT_VALUES)
    if el is None:
        return None
    el.set("ana", "#not-reviewed" if el.get("ana") == "#confirmed" else "#confirmed")
    return el


def source_wrong_seg(doc: etree._Element) -> etree._Element | None:
    """A value points to another passage of its own entry."""
    for el in doc.xpath(f"{IMPRINT_VALUES}[@source]", namespaces=NS):
        m = SEG_REF.fullmatch(el.get("source"))
        if not m:
            continue
        own = _first(doc, f"//t:seg[@xml:id='{m.group(1)}']")
        quote = next(a for a in own.iterancestors() if a.tag == f"{T}quote")
        # Another passage of the entry, neither inside this one nor around it.
        other = next(
            (
                s
                for s in quote.iter(f"{T}seg")
                if s not in own.iter() and own not in s.iter()
            ),
            None,
        )
        if other is not None:
            el.set("source", f"#{other.get(XML_ID)}")
            return el
    return None


def source_dangling(doc: etree._Element) -> etree._Element | None:
    """A value points to a passage that does not exist."""
    el = _first(doc, f"{IMPRINT_VALUES}[@source]")
    if el is None:
        return None
    el.set("source", f"#src-wiki-{_page(el)}-s9999")
    return el


def value_text(doc: etree._Element) -> etree._Element | None:
    """A value's text differs from the canonical value in its last character."""
    el = _first(doc, f"{IMPRINT_VALUES}[string-length(text()) > 0]")
    if el is None:
        return None
    last = el.text[-1]
    new = str((int(last) + 1) % 10) if last.isdigit() else _other_char(last)
    el.text = el.text[:-1] + new
    return el


def struct_dropped(doc: etree._Element) -> etree._Element | None:
    """A publication is left out together with its relation, as an exporter skipping it would."""
    structs = doc.xpath("//t:body//t:biblStruct", namespaces=NS)
    if not structs:
        return None
    struct = structs[1] if len(structs) > 1 else structs[0]
    sid = struct.get(XML_ID)
    struct.getparent().remove(struct)
    for rel in doc.xpath(f"//t:relation[@passive='#{sid}']", namespaces=NS):
        rel.getparent().remove(rel)
    return struct


def id_duplicated(doc: etree._Element) -> etree._Element | None:
    """Two passages of one entry carry the same xml:id."""
    quote = _first(doc, "//t:standOff//t:quote[count(.//t:seg) > 1]")
    if quote is None:
        return None
    segs = list(quote.iter(f"{T}seg"))
    segs[1].set(XML_ID, segs[0].get(XML_ID))
    return segs[1]


def producer_unknown(doc: etree._Element) -> etree._Element | None:
    """A value names a producer the profile does not know, declared so that its pointer resolves."""
    el = _first(doc, IMPRINT_VALUES)
    app_info = _first(doc, "//t:appInfo")
    if el is None or app_info is None:
        return None
    app = etree.SubElement(
        app_info, f"{T}application", ident="unknown-tool", version="1"
    )
    app.set(XML_ID, "app-unknown")
    etree.SubElement(app, f"{T}desc").text = "A producer outside the profile"
    el.set("resp", "#app-unknown")
    return el


def seg_unpointed(doc: etree._Element) -> etree._Element | None:
    """Unread text of an entry is marked as a passage, so it reads as read text."""
    found = _unmarked(doc, "\w{3}")
    if found is None:
        return None
    owner, is_tail, text = found
    quote = owner.getparent() if is_tail else owner
    m = re.search(r"\w{3,}", text)
    seg = etree.Element(f"{T}seg")
    seg.set(XML_ID, f"{quote.get(XML_ID).removesuffix('-text')}-s9999")
    seg.text, seg.tail = m.group(), text[m.end() :]
    _set_text(owner, is_tail, text[: m.start()])
    quote.insert(quote.index(owner) + 1 if is_tail else 0, seg)
    return seg


def source_in_header(doc: etree._Element) -> etree._Element | None:
    """A source entry stands in the header, where it reads as the source of the file."""
    bibl = _first(doc, "//t:standOff/t:listBibl/t:bibl[@type='wikiPage']")
    source_desc = _first(doc, "//t:teiHeader//t:sourceDesc")
    if bibl is None or source_desc is None:
        return None
    source_desc.append(bibl)
    return bibl


def print_added(doc: etree._Element) -> etree._Element | None:
    """A print record joins the wiki export, valid in every other respect."""
    sources = _first(doc, "//t:standOff/t:listBibl[@type='sources']")
    wiki = _first(doc, "//t:standOff/t:listBibl/t:bibl[@type='wikiPage']")
    if sources is None or wiki is None:
        return None
    bibl = etree.SubElement(sources, f"{T}bibl", type="printEntry")
    bibl.set(XML_ID, "src-print-H-670")
    etree.SubElement(bibl, f"{T}idno", type="printRecord").text = "H/670"
    etree.SubElement(bibl, f"{T}idno", type="sha256").text = "0" * 64
    relations = _first(doc, "//t:standOff/t:listRelation")
    if relations is not None:
        etree.SubElement(
            relations,
            f"{T}relation",
            name="samePublicationAs",
            mutual=f"#src-print-H-670 #{wiki.get(XML_ID)}",
            resp="#app-concordance",
            ana="#proposed",
            n="claim-mutant",
        )
    return bibl


def imprint_emptied(doc: etree._Element) -> etree._Element | None:
    """An imprint loses all its parts."""
    imprint = _first(doc, "//t:body//t:imprint[*[@resp]]")
    if imprint is None:
        return None
    for child in list(imprint):
        imprint.remove(child)
    return imprint


def attribute_foreign(doc: etree._Element) -> etree._Element | None:
    """A value carries an attribute TEI admits and the profile does not (@cert of SZD dates)."""
    el = _first(doc, "//t:body//t:imprint/t:date[@when]")
    if el is None:
        el = _first(doc, IMPRINT_VALUES)
    if el is None:
        return None
    el.set("cert", "high")
    return el


# id, the fault in a phrase, the mutation.
MUTATIONS: list[tuple[str, str, Callable[[etree._Element], etree._Element | None]]] = [
    ("source-char", "a letter of the source text altered", source_char),
    ("resp-swapped", "producer swapped between model and rules", resp_swapped),
    ("ana-changed", "statement state of a value changed", ana_changed),
    ("source-wrong-seg", "a value points to another passage", source_wrong_seg),
    ("source-dangling", "a value points to a missing passage", source_dangling),
    ("value-text", "a value's text altered", value_text),
    ("struct-dropped", "a publication and its relation left out", struct_dropped),
    ("id-duplicated", "an xml:id given twice", id_duplicated),
    ("producer-unknown", "a declared producer outside the profile", producer_unknown),
    ("seg-unpointed", "unread text marked as a passage", seg_unpointed),
    ("source-in-header", "a source entry moved into the header", source_in_header),
    ("print-added", "a print record in the wiki export", print_added),
    ("imprint-emptied", "an imprint without parts", imprint_emptied),
    ("attribute-foreign", "an attribute outside the profile", attribute_foreign),
]


def _failures(checks: list[dict]) -> dict[str, int]:
    return {c["id"]: c["measured"]["failed"] for c in checks if c["status"] == "fail"}


def run(
    doc_bytes: bytes, records: dict[int, dict], check: Check | None = None
) -> list[dict]:
    """Apply each mutation to a fresh copy of the export and name the checks that catch it.

    `check(raw, records)` returns the check dicts of `pipeline/acceptance.py`;
    by default its `check_export` with the profile schema and without tei_all.
    """
    if check is None:
        import acceptance  # noqa: PLC0415 - acceptance imports this module

        profile = acceptance._profile()

        def check(raw: bytes, recs: dict[int, dict]) -> list[dict]:
            return acceptance.check_export(raw, recs, profile=profile).checks

    base = _failures(check(doc_bytes, records))
    results = []
    for mid, fault, mutate in MUTATIONS:
        doc = etree.fromstring(doc_bytes)
        target = mutate(doc)
        result = {
            "id": mid,
            "fault": fault,
            "applied": target is not None,
            "page": _page(target) if target is not None else None,
            "caughtBy": [],
            "caught": False,
        }
        if target is not None:
            mutant = etree.tostring(doc, xml_declaration=True, encoding="utf-8")
            failed = _failures(check(mutant, records))
            result["caughtBy"] = [
                cid for cid, n in failed.items() if n > base.get(cid, 0)
            ]
            result["caught"] = bool(result["caughtBy"])
        results.append(result)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--pages", type=int, nargs="+")
    args = parser.parse_args()
    data = export_tei.load_dataset()
    records = {r["sourcePageId"]: r for r in export_tei.exported_pages(data)}
    if args.pages:
        records = {p: records[p] for p in args.pages}
    raw = export_tei.serialize(export_tei.build(args.pages))
    for res in run(raw, records):
        caught = ", ".join(res["caughtBy"]) or "NOT CAUGHT"
        print(f"{res['id']:18s} page {res['page']}: {caught}")


if __name__ == "__main__":
    main()
