"""Export wiki records as TEI for Stefan Zweig Digital, the delivery format.

Regime: script pipeline. The canonical data stay the frontend dataset and its
gates; this script projects selected records into the TEI profile of
`knowledge/tei-profile.md` and is rebuilt from them, never edited.

Data flow: `docs/data/klawiter.json` (one record per wiki page, values with
their passage offsets and producer class) and, where present on this
computer, the proposed print-wiki concordance under `data/print/` go into
one TEI document. The profile follows the encoding patterns of Stefan Zweig
Digital (header, `listBibl`, `@ref`, dates with display text) and departs
from them where Klawiter needs it: `biblStruct` for a publication nobody
holds, `@resp`, `@source` and `@ana` on every value, and the source entries
with their passages in `sourceDesc`.

Usage:
    python -m uv run python pipeline/export_tei.py --pages 212
    python -m uv run python pipeline/export_tei.py --pages 212 --with-print

Without `--with-print` the output holds wiki data only and may be versioned.
With it, print records join as identifiers and proposed claims, never with
print text, and the file is written under `data/print/` because the rights
to the print volumes are unresolved (`CLAUDE.md`, Print Strand).

Deliberate shortcuts: only the flat page record is exported; pages with a
publication layer and proposed authority links follow in the next increment
of the profile (`knowledge/tei-profile.md`, Open).
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "docs" / "data" / "klawiter.json"
CONCORDANCE = ROOT / "data" / "print" / "derived" / "claims" / "concordance.jsonl"
OUT_PUBLIC = ROOT / "data" / "output" / "tei"
OUT_LOCAL = ROOT / "data" / "print" / "derived" / "tei"

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("", TEI_NS)

# Producer classes of the dataset (`_provenance`) to the declared applications.
PRODUCER_APP = {
    "regex": "app-rules",
    "rule": "app-rules",
    "llm": "app-llm",
    "derived": "app-derivation",
}
# Gaps whose value stands in the page metadata, which the source entry carries.
META_GAPS = {"page-title": "title", "category-markup": "categories"}


def _t(tag: str) -> str:
    return f"{{{TEI_NS}}}{tag}"


def _el(
    parent: ET.Element, tag: str, text: str | None = None, **attrs: str
) -> ET.Element:
    """A TEI child with attributes; `xml_id` and `xml_lang` become xml:id and xml:lang."""
    node = ET.SubElement(parent, _t(tag))
    for key, value in attrs.items():
        if key == "xml_id":
            node.set(f"{{{XML_NS}}}id", value)
        elif key == "xml_lang":
            node.set(f"{{{XML_NS}}}lang", value)
        else:
            node.set(key, value)
    if text is not None:
        node.text = text
    return node


def _load_records(pages: list[int]) -> tuple[list[dict], dict]:
    """The records of the pages and the dataset's LLM enrichment metadata."""
    if not DATASET.is_file():
        sys.exit(f"{DATASET} is missing; run the production pipeline first")
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    entries = {e["sourcePageId"]: e for e in data["entries"]}
    missing = [p for p in pages if p not in entries]
    if missing:
        sys.exit(f"pages not in the dataset: {missing}")
    return [entries[p] for p in pages], data.get("_meta", {}).get("llmEnrichment", {})


def _load_claims(pages: set[int]) -> dict[int, list[dict]]:
    """Proposed print-wiki claims per wiki page, read from the local print strand."""
    if not CONCORDANCE.is_file():
        sys.exit(f"{CONCORDANCE} is missing; --with-print needs the local print strand")
    found: dict[int, list[dict]] = {}
    with CONCORDANCE.open(encoding="utf-8") as fh:
        for line in fh:
            claim = json.loads(line)
            page = (claim.get("evidence") or {}).get("wiki_page")
            if page in pages and claim.get("predicate") == "samePublicationAs":
                found.setdefault(page, []).append(claim)
    return found


def _header(tei: ET.Element, llm: dict) -> tuple[ET.Element, ET.Element]:
    """The header after the Stefan Zweig Digital pattern; returns the source list and the class declaration."""
    header = _el(tei, "teiHeader")
    file_desc = _el(header, "fileDesc")
    title_stmt = _el(file_desc, "titleStmt")
    _el(
        title_stmt,
        "title",
        "Klawiter-Bibliographie Stefan Zweig digital",
        xml_lang="de",
    )
    _el(
        title_stmt, "title", "Klawiter Bibliography Stefan Zweig digital", xml_lang="en"
    )
    _el(title_stmt, "editor", "Randolph J. Klawiter", role="compiler")
    pub = _el(file_desc, "publicationStmt")
    publisher = _el(pub, "publisher")
    _el(
        publisher,
        "orgName",
        "Literaturarchiv Salzburg",
        corresp="https://www.uni-salzburg.at/index.php?id=72",
        ref="d-nb.info/gnd/1047605287",
    )
    availability = _el(pub, "availability")
    _el(
        availability,
        "licence",
        "Creative Commons BY 4.0",
        target="https://creativecommons.org/licenses/by/4.0",
    )
    _el(pub, "idno", "o:szd.klawiter", type="PID")
    source_desc = _el(file_desc, "sourceDesc")
    sources = _el(source_desc, "listBibl", type="sources")

    encoding = _el(header, "encodingDesc")
    app_info = _el(encoding, "appInfo")
    _el(
        _el(
            app_info,
            "application",
            ident="klawiter-rules",
            version="0.9",
            xml_id="app-rules",
        ),
        "desc",
        "Parser rules of the Klawiter pipeline reading a value from its passage",
    )
    _el(
        _el(
            app_info,
            "application",
            ident="klawiter-derivation",
            version="0.9",
            xml_id="app-derivation",
        ),
        "desc",
        "Rules of the Klawiter pipeline computing a value from another value",
    )
    _el(
        _el(
            app_info,
            "application",
            ident="klawiter-concordance",
            version="0.9",
            xml_id="app-concordance",
        ),
        "desc",
        "Rules of the print strand proposing that a print record and a wiki page describe one publication",
    )
    _el(
        _el(
            app_info,
            "application",
            ident=llm.get("model", "llm"),
            version=llm.get("frozenAt", ""),
            xml_id="app-llm",
        ),
        "desc",
        f"Language model filling gaps the rules left, frozen cache, prompt sha256 {llm.get('promptSha256', '')}",
    )
    class_decl = _el(encoding, "classDecl")
    # The record identifiers of the canonical data, `klawiter:entry/212`, resolve here.
    prefixes = _el(encoding, "listPrefixDef")
    _el(
        prefixes,
        "prefixDef",
        ident="klawiter",
        matchPattern="(.+)",
        replacementPattern="https://chpollin.github.io/klawiter-rescue/vocab/$1",
    )
    return sources, class_decl


def _states(class_decl: ET.Element) -> None:
    """The statement states a value or relation points to with @ana."""
    taxonomy = _el(class_decl, "taxonomy", xml_id="state")
    for ident, gloss in (
        (
            "not-reviewed",
            "read or proposed by a rule or model, not reviewed by a person",
        ),
        (
            "proposed",
            "a proposal that publishes nothing until a person or an exact rule decides",
        ),
        ("confirmed", "confirmed by a person or an exact deterministic rule"),
        ("contested", "an open statement with competing interpretations"),
    ):
        _el(_el(taxonomy, "category", xml_id=ident), "catDesc", gloss)


def _source_entry(sources: ET.Element, rec: dict) -> dict[str, str]:
    """Klawiter's entry with one seg per located passage; returns key to seg id."""
    page = rec["sourcePageId"]
    bibl = _el(sources, "bibl", type="wikiPage", xml_id=f"src-wiki-{page}")
    _el(bibl, "idno", str(page), type="pageId")
    revision = (rec.get("revisionDates") or {}).get("lastRevisionId")
    if revision is not None:
        _el(bibl, "idno", str(revision), type="revision")
    seg_of: dict[str, str] = {}
    title = _el(bibl, "title", rec.get("title", ""), xml_id=f"src-wiki-{page}-title")
    seg_of["meta:title"] = title.get(f"{{{XML_NS}}}id")
    cats = _el(bibl, "note", type="categories")
    for i, cat in enumerate(rec.get("categories") or []):
        seg = _el(cats, "seg", cat, xml_id=f"src-wiki-{page}-cat{i + 1}")
        seg_of[f"meta:category:{cat}"] = seg.get(f"{{{XML_NS}}}id")

    text = rec.get("fullBibliographicEntry") or ""
    spans = sorted(
        {
            (v["textStart"], v["textEnd"])
            for values in (rec.get("fieldEvidence") or {}).values()
            for v in values
            if isinstance(v.get("textStart"), int) and isinstance(v.get("textEnd"), int)
        }
    )
    quote = _el(bibl, "quote")
    cursor, last, n = 0, None, 0
    for start, end in spans:
        if start < cursor:
            continue  # a span crossing a drawn one gets no seg and its value no @source
        n += 1
        seg_id = f"src-wiki-{page}-s{n}"
        if last is None:
            quote.text = text[cursor:start]
        else:
            last.tail = text[cursor:start]
        last = _el(quote, "seg", text[start:end], xml_id=seg_id)
        seg_of[f"{start}:{end}"] = seg_id
        cursor = end
    if last is None:
        quote.text = text
    else:
        last.tail = text[cursor:]
    return seg_of


def _value_attrs(rec: dict, field: str, seg_of: dict[str, str]) -> dict[str, str]:
    """@resp, @source and @ana of one flat value, from its producer class and evidence."""
    cls = (rec.get("_provenance") or {}).get(field, "regex")
    attrs = {"resp": f"#{PRODUCER_APP.get(cls, 'app-rules')}", "ana": "#not-reviewed"}
    for ev in (rec.get("fieldEvidence") or {}).get(field, []):
        key = f"{ev.get('textStart')}:{ev.get('textEnd')}"
        if key in seg_of:
            attrs["source"] = f"#{seg_of[key]}"
            break
        meta = META_GAPS.get(ev.get("gap", ""))
        if meta == "title":
            attrs["source"] = f"#{seg_of['meta:title']}"
            break
        if meta == "categories":
            target = next(
                (sid for k, sid in seg_of.items() if k.startswith("meta:category:")),
                None,
            )
            if target:
                attrs["source"] = f"#{target}"
                break
    return attrs


def _publication(body_list: ET.Element, rec: dict, seg_of: dict[str, str]) -> str:
    """One biblStruct for the publication a single-publication page describes."""
    page = rec["sourcePageId"]
    # Provisional identifier until the identifier scheme is decided (knowledge/tei-profile.md, Open).
    pub_id = f"SZDKLA.{page}.1"
    struct = _el(
        body_list, "biblStruct", xml_id=pub_id, corresp=f"klawiter:entry/{page}"
    )
    monogr = _el(struct, "monogr")
    _el(
        monogr,
        "title",
        rec.get("title", ""),
        level="m",
        **_value_attrs(rec, "title", seg_of),
    )
    if rec.get("translator"):
        resp_stmt = _el(monogr, "respStmt")
        _el(resp_stmt, "resp", "translator")
        _el(
            resp_stmt,
            "persName",
            rec["translator"],
            **_value_attrs(rec, "translator", seg_of),
        )
    if rec.get("languageCode"):
        _el(
            monogr,
            "textLang",
            rec.get("language", ""),
            mainLang=rec["languageCode"],
            **_value_attrs(rec, "languageCode", seg_of),
        )
    imprint = _el(monogr, "imprint")
    if rec.get("location"):
        _el(
            imprint,
            "pubPlace",
            rec["location"],
            xml_id=f"{pub_id}.place",
            **_value_attrs(rec, "location", seg_of),
        )
    if rec.get("publisher"):
        _el(
            imprint,
            "publisher",
            rec["publisher"],
            xml_id=f"{pub_id}.publisher",
            **_value_attrs(rec, "publisher", seg_of),
        )
    if rec.get("year"):
        _el(
            imprint,
            "date",
            str(rec["year"]),
            when=str(rec["year"]),
            **_value_attrs(rec, "year", seg_of),
        )
    if rec.get("pageCount"):
        extent = _el(monogr, "extent")
        _el(
            extent,
            "measure",
            str(rec["pageCount"]),
            unit="page",
            quantity=str(rec["pageCount"]),
            **_value_attrs(rec, "pageCount", seg_of),
        )
    return pub_id


def _print_relations(
    sources: ET.Element, relations: ET.Element, pub_id: str, claims: list[dict]
) -> None:
    """Print records as identifiers only, each linked by its proposed claim."""
    for claim in sorted(claims, key=lambda c: c["subject"]):
        record = claim["evidence"]["print"]["record"]
        rid = "src-print-" + record.replace("/", "-")
        bibl = _el(sources, "bibl", type="printEntry", xml_id=rid)
        _el(bibl, "idno", record, type="printRecord")
        _el(bibl, "idno", claim["evidence"]["print"]["sha256"], type="sha256")
        state = claim.get("state", "proposed")
        _el(
            relations,
            "relation",
            name="samePublicationAs",
            active=f"#{rid}",
            passive=f"#{pub_id}",
            resp="#app-concordance",
            ana=f"#{state}",
            n=claim["id"],
        )


def build(pages: list[int], with_print: bool) -> ET.ElementTree:
    records, llm = _load_records(pages)
    claims = _load_claims(set(pages)) if with_print else {}
    tei = ET.Element(_t("TEI"))
    sources, class_decl = _header(tei, llm)
    _states(class_decl)
    text = _el(tei, "text")
    body_list = _el(_el(text, "body"), "listBibl")
    stand_off = ET.Element(_t("standOff"))
    relations = _el(stand_off, "listRelation")
    for rec in records:
        seg_of = _source_entry(sources, rec)
        pub_id = _publication(body_list, rec, seg_of)
        _el(
            relations,
            "relation",
            name="describes",
            active=f"#src-wiki-{rec['sourcePageId']}",
            passive=f"#{pub_id}",
            resp="#app-rules",
            ana="#not-reviewed",
        )
        _print_relations(
            sources, relations, pub_id, claims.get(rec["sourcePageId"], [])
        )
    tei.append(stand_off)
    ET.indent(tei)
    return ET.ElementTree(tei)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--pages", type=int, nargs="+", required=True)
    parser.add_argument("--with-print", action="store_true")
    args = parser.parse_args()
    out_dir = OUT_LOCAL if args.with_print else OUT_PUBLIC
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"klawiter-{'-'.join(map(str, args.pages))}.xml"
    # A binary handle keeps LF on every platform; a path would be opened in text mode.
    with out.open("wb") as fh:
        build(args.pages, args.with_print).write(
            fh, encoding="utf-8", xml_declaration=True
        )
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
