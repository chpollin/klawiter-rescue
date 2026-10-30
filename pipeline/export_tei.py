"""Export the wiki as TEI for Stefan Zweig Digital, the delivery format.

Regime: script pipeline. The canonical data stay the frontend dataset and its
gates; this script projects them into the TEI profile of
`knowledge/tei-profile.md` and is rebuilt from them, never edited.

Data flow: `docs/data/klawiter.json` (one record per wiki page, values with
their passage offsets, producer class and review state), the publication
layer `docs/data/publications/<page>.json` (one entry per publication a
page describes) and, where present on this computer, the proposed print-wiki
concordance under `data/print/` go into one TEI document:

- `text/body/listBibl`: one `biblStruct` per publication of an edition page.
  Author pages, work hubs and pages of other or undetermined kind describe
  no publication of their own and get none (their model is milestone D2).
- `standOff/listBibl[@type='sources']`: Klawiter's entry of every page with
  its text unaltered and one `seg` per passage a value points to. The entries
  stand outside the header, so that the header's first title stays the title
  of the object (the Dublin Core mapping of GAMS reads it).
- `standOff/listRelation`: which source describes which publication, and the
  proposed identities of print records with wiki pages.

Every value carries `@resp` (its producer), `@ana` (its statement state) and,
where its passage is located, `@source`. A passage crossing another one
cannot nest and is addressed by a `string-range()` pointer into the entry.
Which field reaches which element, which waits for a later milestone and
which is left out on purpose is declared in FIELDS; `pipeline/acceptance.py`
checks the export against the canonical data independently of this module.

Usage:
    python -m uv run python pipeline/export_tei.py                 # every page
    python -m uv run python pipeline/export_tei.py --pages 212 3   # a sample
    python -m uv run python pipeline/export_tei.py --pages 212 --with-print

Without `--with-print` the output holds wiki data only. With it, print records
join as identifiers and proposed claims, never with print text, and the file
is written under `data/print/` because the rights to the print volumes are
unresolved (`CLAUDE.md`, Print Strand).
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "docs" / "data" / "klawiter.json"
PUBLICATIONS = ROOT / "docs" / "data" / "publications"
CONCORDANCE = ROOT / "data" / "print" / "derived" / "claims" / "concordance.jsonl"
OUT_PUBLIC = ROOT / "data" / "output" / "tei"
OUT_LOCAL = ROOT / "data" / "print" / "derived" / "tei"

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"
XML_ID = f"{{{XML_NS}}}id"
ET.register_namespace("", TEI_NS)

# Producer classes of the dataset to the declared applications.
PRODUCER_APP = {"regex": "app-rules", "llm": "app-llm", "derived": "app-derivation"}
PUBLICATION_KIND = "edition-page"
CITATION_PRODUCER = "regex"

# Every field of a page record and of a publication, with its place in the
# export: ("exported", target), ("pending", milestone, reason) or
# ("excluded", reason). The acceptance report shows this ledger, and a field
# missing here fails it, so that a new field cannot vanish unnoticed.
FIELDS: dict[str, dict[str, tuple[str, ...]]] = {
    "page": {
        "title": ("exported", "monogr/title"),
        "year": ("exported", "imprint/date"),
        "publisher": ("exported", "imprint/publisher"),
        "location": ("exported", "imprint/pubPlace"),
        "language": ("exported", "monogr/textLang"),
        "languageCode": ("exported", "monogr/textLang/@mainLang"),
        "pageCount": ("exported", "monogr/extent/measure"),
        "translator": ("exported", "monogr/respStmt"),
        "categories": ("exported", "source bibl, note of categories"),
        "fullBibliographicEntry": ("exported", "source bibl/quote"),
        "revisionDates": ("exported", "source bibl, idno of the revision"),
        "sourcePageId": ("exported", "source bibl, idno of the page"),
        "wikiPageKind": ("exported", "source bibl/@subtype"),
        "printAddressCitations": ("exported", "source bibl, note of print citations"),
        "@id": ("exported", "biblStruct/@corresp"),
        "review": ("exported", "@ana of each value"),
        "fieldEvidence": ("exported", "@source of each value"),
        "_provenance": ("exported", "@resp of each value"),
        "originalTitle": (
            "pending",
            "D2",
            "the original of a translation is a relation to a work",
        ),
        "contentItems": (
            "pending",
            "D2",
            "contents become analytic items of the publication",
        ),
        "seeAlso": ("pending", "D2", "cross references become relations between pages"),
        "reprints": ("pending", "D2", "reprints are publications of their own"),
        "translations": ("pending", "D2", "translations are publications of their own"),
        "translationStatements": (
            "pending",
            "D2",
            "translations are publications of their own",
        ),
        "reviewFlags": ("pending", "D2", "review flags need their own note type"),
        "publicationReviewFlags": (
            "pending",
            "D2",
            "review flags need their own note type",
        ),
        "entryType": (
            "pending",
            "D2",
            "the record type decides the TEI shape of the record",
        ),
        "ruleGaps": (
            "excluded",
            "a record of where the rules found nothing, not a statement of the source",
        ),
        "@type": ("excluded", "JSON-LD class, replaced by the TEI element"),
        "pageNamespace": ("excluded", "only main-namespace pages are exported"),
        "sourceTextId": (
            "excluded",
            "database key of the dump; page and revision identify the text",
        ),
        "sourceBlobId": ("excluded", "database key of the dump"),
        "sourceRevision": ("excluded", "database key of the dump"),
        "mainCategory": ("excluded", "derived from the categories, which are exported"),
        "timePeriod": ("excluded", "derived from the year"),
        "allYears": ("excluded", "aggregate of the publications' years"),
        "allLocations": ("excluded", "aggregate of the publications' places"),
        "publicationCount": ("excluded", "the number of biblStruct elements"),
        "publicationYears": ("excluded", "aggregate of the publications' years"),
        "publicationPlaces": ("excluded", "aggregate of the publications' places"),
        "publicationLanguages": (
            "excluded",
            "aggregate of the publications' languages",
        ),
        "pageKind": (
            "excluded",
            "the publication layer's kind; wikiPageKind is exported",
        ),
        "wikiPageKindRule": (
            "excluded",
            "rule that set the page kind, part of the pipeline record",
        ),
        "wikiPageKindEvidence": (
            "excluded",
            "evidence of the page kind, part of the pipeline record",
        ),
    },
    "publication": {
        "id": ("exported", "biblStruct/@corresp"),
        "title": ("exported", "monogr/title"),
        "year": ("exported", "imprint/date/@when"),
        "yearRaw": ("exported", "imprint/date"),
        "publisher": ("exported", "imprint/publisher"),
        "places": ("exported", "imprint/pubPlace"),
        "language": ("exported", "monogr/textLang"),
        "languageCode": ("exported", "monogr/textLang/@mainLang"),
        "extent": ("exported", "monogr/extent/measure"),
        "credits": ("exported", "monogr/respStmt"),
        "editionStatement": ("exported", "monogr/edition"),
        "series": ("exported", "series/title"),
        "seriesVolume": ("exported", "series/biblScope"),
        "reviewStatus": ("exported", "biblStruct/@ana"),
        "provenance": ("exported", "@resp of each value"),
        "valueSpans": ("exported", "@source of each value"),
        "sourceSlice": (
            "excluded",
            "the publication's passage; its values point into it",
        ),
        "imprint": (
            "excluded",
            "the imprint phrase, exported as its publisher and places",
        ),
        "contributions": (
            "pending",
            "D2",
            "contents become analytic items of the publication",
        ),
        "container": ("pending", "D2", "an article's journal becomes its monogr"),
        "imprints": ("pending", "D2", "co-publishers need a second imprint"),
        "note": ("pending", "D2", "the note of a publication needs its place"),
        "online": ("pending", "D2", "online copies need their own ref"),
        "editionId": ("pending", "D2", "editions group publications across pages"),
        "seriesGloss": ("pending", "D2", "a gloss of the series title"),
        "reviewFlags": ("pending", "D2", "review flags need their own note type"),
        "reviewDecision": (
            "pending",
            "D2",
            "a proposed decision of a review agent, not a person",
        ),
        "reviewProducer": (
            "pending",
            "D2",
            "a proposed decision of a review agent, not a person",
        ),
    },
}


def _t(tag: str) -> str:
    return f"{{{TEI_NS}}}{tag}"


def _el(
    parent: ET.Element, tag: str, text: str | None = None, **attrs: str
) -> ET.Element:
    """A TEI child with attributes; `xml_id` and `xml_lang` become xml:id and xml:lang."""
    node = ET.SubElement(parent, _t(tag))
    for key, value in attrs.items():
        if key == "xml_id":
            node.set(XML_ID, value)
        elif key == "xml_lang":
            node.set(f"{{{XML_NS}}}lang", value)
        else:
            node.set(key, value)
    if text is not None:
        node.text = text
    return node


def load_dataset() -> dict:
    if not DATASET.is_file():
        sys.exit(f"{DATASET} is missing; run the production pipeline first")
    return json.loads(DATASET.read_text(encoding="utf-8"))


def exported_pages(data: dict) -> list[dict]:
    """The main-namespace pages with a page kind, the wiki's content pages."""
    return [
        e for e in data["entries"] if e["pageNamespace"] == 0 and e.get("wikiPageKind")
    ]


def load_layer(page: int) -> list[dict]:
    path = PUBLICATIONS / f"{page}.json"
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["publications"]


def field_states(rec: dict) -> dict[str, str]:
    return ((rec.get("review") or {}).get("fieldStates")) or {}


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


def _application(
    app_info: ET.Element, ident: str, version: str, xml_id: str, desc: str
) -> None:
    app = _el(app_info, "application", ident=ident, version=version, xml_id=xml_id)
    _el(app, "desc", desc)


def _header(tei: ET.Element, meta: dict) -> None:
    """The header after the Stefan Zweig Digital pattern."""
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
    pub = _el(file_desc, "publicationStmt")
    publisher = _el(pub, "publisher")
    _el(
        publisher,
        "orgName",
        "Literaturarchiv Salzburg",
        corresp="https://www.uni-salzburg.at/index.php?id=72",
        ref="https://d-nb.info/gnd/1047605287",
    )
    availability = _el(pub, "availability")
    _el(
        availability,
        "licence",
        "Creative Commons BY 4.0",
        target="https://creativecommons.org/licenses/by/4.0",
    )
    _el(pub, "idno", "o:szd.klawiter", type="PID")
    # The wiki is the source of the file; the compiler belongs to it, not to the file.
    source = _el(_el(file_desc, "sourceDesc"), "bibl", type="wiki")
    _el(source, "title", "Stefan Zweig Bibliography")
    _el(source, "editor", "Randolph J. Klawiter", role="compiler")
    dump = meta.get("sourceDump") or {}
    _el(source, "idno", dump.get("sha256", ""), type="sha256")
    _el(source, "note", f"Database dump of the wiki, {dump.get('file', '')}")

    encoding = _el(header, "encodingDesc")
    app_info = _el(encoding, "appInfo")
    version = str(meta.get("version", "0"))
    _application(
        app_info,
        "klawiter-rules",
        version,
        "app-rules",
        "Parser rules of the Klawiter pipeline reading a value from its passage",
    )
    _application(
        app_info,
        "klawiter-derivation",
        version,
        "app-derivation",
        "Rules of the Klawiter pipeline computing a value from another value",
    )
    _application(
        app_info,
        "klawiter-concordance",
        version,
        "app-concordance",
        "Rules of the print strand proposing that a print record and a wiki page "
        "describe one publication",
    )
    llm = meta.get("llmEnrichment") or {}
    frozen = llm.get("frozenAt", "")
    # @version takes a version number; the date the cache was frozen stands in for it.
    _application(
        app_info,
        llm.get("model", "llm"),
        frozen[:10].replace("-", ".") or "0",
        "app-llm",
        f"Language model filling gaps the rules left, read from a cache frozen at "
        f"{frozen}, prompt sha256 {llm.get('promptSha256', '')}",
    )
    taxonomy = _el(_el(encoding, "classDecl"), "taxonomy", xml_id="state")
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
    prefixes = _el(encoding, "listPrefixDef")
    # The record identifiers of the canonical data, `klawiter:entry/212`, resolve here.
    _el(
        prefixes,
        "prefixDef",
        ident="klawiter",
        matchPattern="(.+)",
        replacementPattern="https://chpollin.github.io/klawiter-rescue/vocab/$1",
    )


class Source:
    """Klawiter's entry of one page and the passages its exported values point to.

    Values register their passages while the publications are built and get
    a placeholder `@start:end`; the entry is written afterwards, so that only
    passages a value points to become a `seg`, and every `seg` is pointed to.
    """

    def __init__(self, rec: dict) -> None:
        self.rec = rec
        self.page = rec["sourcePageId"]
        self.sid = f"src-wiki-{self.page}"
        self.text = rec.get("fullBibliographicEntry") or ""
        self.categories = rec.get("categories") or []
        self.spans: set[tuple[int, int]] = set()

    def pointer(self, evidence: list[dict], value: str) -> str | None:
        """The @source of a value from its evidence; None when no passage is located."""
        for ev in evidence:
            start, end = ev.get("textStart"), ev.get("textEnd")
            if (
                isinstance(start, int)
                and isinstance(end, int)
                and 0 <= start < end <= len(self.text)
            ):
                self.spans.add((start, end))
                return f"@{start}:{end}"
            gap = ev.get("gap")
            if gap == "page-title":
                return f"#{self.sid}-title"
            if gap == "category-markup" and self.categories:
                return f"#{self.sid}-cat{self._category(value)}"
        return None

    def _category(self, value: str) -> int:
        """The category the value was read from: the first that names it, else the first."""
        low = value.lower()
        for i, cat in enumerate(self.categories, 1):
            if low and low in cat.lower():
                return i
        return 1

    def write(self, sources: ET.Element) -> dict[str, str]:
        """Write the entry; returns each placeholder's final pointer."""
        rec = self.rec
        bibl = _el(
            sources,
            "bibl",
            type="wikiPage",
            subtype=rec["wikiPageKind"],
            xml_id=self.sid,
        )
        _el(bibl, "title", rec.get("title", ""), xml_id=f"{self.sid}-title")
        _el(bibl, "idno", str(self.page), type="pageId")
        revision = (rec.get("revisionDates") or {}).get("lastRevisionId")
        if revision is not None:
            _el(bibl, "idno", str(revision), type="revision")
        if self.categories:
            cats = _el(bibl, "note", type="categories")
            for i, cat in enumerate(self.categories, 1):
                _el(cats, "seg", cat, xml_id=f"{self.sid}-cat{i}")
        citations = rec.get("printAddressCitations") or []
        # A citation's sourceStart counts in the raw wikitext; its passage in the
        # entry text is the evidence the pipeline located for it, in the same order.
        evidence = (rec.get("fieldEvidence") or {}).get("printAddressCitations") or []
        # Register the citations' passages before the text is written.
        pointers = [
            self.pointer([ev], c.get("printAddress", "")) if i < len(evidence) else None
            for i, (c, ev) in enumerate(
                zip(citations, evidence + [{}] * len(citations))
            )
        ]
        resolved = self._quote(bibl)
        if citations:
            note = _el(bibl, "note", type="printCitations")
            state = field_states(rec).get("printAddressCitations", "not-reviewed")
            for cite, ptr in zip(citations, pointers):
                attrs = {
                    "type": "printAddress",
                    "subtype": cite.get("printVolume", ""),
                    # Citations are read by rule only (lib/print_addresses.py), and
                    # the dataset records no producer class for them.
                    "resp": f"#{PRODUCER_APP[CITATION_PRODUCER]}",
                    "ana": f"#{state}",
                }
                if ptr:
                    attrs["source"] = resolved[ptr]
                _el(note, "idno", cite.get("printAddress", ""), **attrs)
        return resolved

    def _range(self, start: int, end: int) -> str:
        return f"#string-range(//*[@xml:id='{self.sid}-text'],{start},{end - start})"

    def _quote(self, bibl: ET.Element) -> dict[str, str]:
        """The entry text with nested segs; a span crossing another gets a range pointer."""
        quote = _el(bibl, "quote", xml_id=f"{self.sid}-text")
        text = self.text
        resolved: dict[str, str] = {}
        # Open elements with the offset where each ends, and the last child written into each.
        stack: list[tuple[ET.Element, int]] = [(quote, len(text))]
        last: dict[int, ET.Element | None] = {id(quote): None}
        cursor = 0

        def put(chunk: str) -> None:
            parent = stack[-1][0]
            child = last[id(parent)]
            if child is None:
                parent.text = (parent.text or "") + chunk
            else:
                child.tail = (child.tail or "") + chunk

        def close() -> None:
            nonlocal cursor
            put(text[cursor : stack[-1][1]])
            cursor = stack[-1][1]
            stack.pop()

        n = 0
        for start, end in sorted(self.spans, key=lambda se: (se[0], -se[1])):
            while start >= stack[-1][1]:
                close()
            if end > stack[-1][1]:
                resolved[f"@{start}:{end}"] = self._range(start, end)
                continue
            put(text[cursor:start])
            cursor = start
            n += 1
            parent = stack[-1][0]
            seg = _el(parent, "seg", xml_id=f"{self.sid}-s{n}")
            last[id(parent)] = seg
            last[id(seg)] = None
            stack.append((seg, end))
            resolved[f"@{start}:{end}"] = f"#{self.sid}-s{n}"
        while stack:
            close()
        return resolved


class Values:
    """The valued elements of one page; their pointers are final once the source is written."""

    def __init__(self, src: Source) -> None:
        self.src = src
        self.pending: list[tuple[ET.Element, str]] = []

    def put(
        self,
        parent: ET.Element,
        tag: str,
        text: str,
        producer: str,
        state: str,
        evidence: list[dict],
        **attrs: str,
    ) -> ET.Element:
        node = _el(parent, tag, text, **attrs)
        node.set("resp", f"#{PRODUCER_APP.get(producer, 'app-rules')}")
        node.set("ana", f"#{state}")
        ptr = self.src.pointer(evidence, text)
        if ptr:
            self.pending.append((node, ptr))
        return node

    def resolve(self, resolved: dict[str, str]) -> None:
        for node, ptr in self.pending:
            node.set("source", resolved.get(ptr, ptr))


def _publication_from_record(body: ET.Element, rec: dict, vals: Values) -> list[str]:
    """One biblStruct from the flat record of a page without a publication layer."""
    pub_id = f"SZDKLA.{rec['sourcePageId']}.1"
    prov = rec.get("_provenance") or {}
    evid = rec.get("fieldEvidence") or {}
    states = field_states(rec)

    def put(parent, tag, field, text, **attrs):
        return vals.put(
            parent,
            tag,
            text,
            prov.get(field, "regex"),
            states.get(field, "not-reviewed"),
            evid.get(field, []),
            **attrs,
        )

    struct = _el(body, "biblStruct", xml_id=pub_id, corresp=rec["@id"])
    monogr = _el(struct, "monogr")
    put(monogr, "title", "title", rec.get("title", ""), level="m")
    if rec.get("translator"):
        resp_stmt = _el(monogr, "respStmt")
        _el(resp_stmt, "resp", "Translated by")
        put(resp_stmt, "persName", "translator", rec["translator"], role="translator")
    if rec.get("languageCode"):
        put(
            monogr,
            "textLang",
            "language",
            rec.get("language", ""),
            mainLang=rec["languageCode"],
        )
    imprint = _el(monogr, "imprint")
    if rec.get("location"):
        put(imprint, "pubPlace", "location", rec["location"])
    if rec.get("publisher"):
        put(imprint, "publisher", "publisher", rec["publisher"])
    if rec.get("year"):
        put(imprint, "date", "year", str(rec["year"]), when=str(rec["year"]))
    if not len(imprint):
        _el(imprint, "date")  # TEI requires an imprint part; the source states none.
    if rec.get("pageCount"):
        extent = _el(monogr, "extent")
        put(
            extent,
            "measure",
            "pageCount",
            str(rec["pageCount"]),
            unit="page",
            quantity=str(rec["pageCount"]),
        )
    return [pub_id]


def _publications_from_layer(
    body: ET.Element, rec: dict, layer: list[dict], vals: Values
) -> list[str]:
    """One biblStruct per publication of the page's publication layer."""
    page = rec["sourcePageId"]
    flat_states = field_states(rec)
    ids = []
    for n, pub in enumerate(layer, 1):
        pub_id = f"SZDKLA.{page}.{n}"
        prov = pub.get("provenance") or {}
        spans = pub.get("valueSpans") or {}

        def put(parent, tag, field, text, evidence=None, state_field=None, **attrs):
            # A review state of the flat record applies where the flat value is this value.
            sf = state_field or field
            state = "not-reviewed"
            if sf in flat_states and str(rec.get(sf, "")) == text:
                state = flat_states[sf]
            ev = spans.get(field, []) if evidence is None else evidence
            return vals.put(
                parent, tag, text, prov.get(field, "regex"), state, ev, **attrs
            )

        struct = _el(
            body,
            "biblStruct",
            xml_id=pub_id,
            corresp=pub["id"],
            ana=f"#{pub.get('reviewStatus', 'proposed')}",
        )
        monogr = _el(struct, "monogr")
        if pub.get("title"):
            put(monogr, "title", "title", pub["title"], level="m")
        else:
            _el(monogr, "title", level="m")
        for credit in pub.get("credits") or []:
            resp_stmt = _el(monogr, "respStmt")
            _el(resp_stmt, "resp", credit.get("creditLabel") or credit.get("role", ""))
            ev = [
                s
                for s in spans.get("credits", [])
                if s.get("part") == "name" and s.get("value") == credit.get("name")
            ]
            put(
                resp_stmt,
                "persName",
                "credits",
                credit.get("name", ""),
                evidence=ev,
                role=credit.get("role", ""),
            )
        # TEI orders monogr: title, responsibility and language, then edition, then imprint.
        if pub.get("languageCode"):
            put(
                monogr,
                "textLang",
                "language",
                pub.get("language", ""),
                mainLang=pub["languageCode"],
            )
        if pub.get("editionStatement"):
            put(monogr, "edition", "editionStatement", pub["editionStatement"])
        imprint = _el(monogr, "imprint")
        for place in pub.get("places") or []:
            ev = [s for s in spans.get("places", []) if s.get("value") == place]
            put(
                imprint,
                "pubPlace",
                "places",
                place,
                evidence=ev,
                state_field="location",
            )
        if pub.get("publisher"):
            put(imprint, "publisher", "publisher", pub["publisher"])
        if pub.get("year"):
            put(
                imprint,
                "date",
                "yearRaw",
                str(pub.get("yearRaw") or pub["year"]),
                when=str(pub["year"]),
            )
        if not len(imprint):
            _el(
                imprint, "date"
            )  # TEI requires an imprint part; the source states none.
        extent = pub.get("extent") or {}
        if extent.get("raw"):
            ev = [s for s in spans.get("extent", []) if s.get("part") == "raw"]
            measure = (
                {"quantity": str(extent["numbered"])} if extent.get("numbered") else {}
            )
            put(
                _el(monogr, "extent"),
                "measure",
                "extent",
                extent["raw"],
                evidence=ev,
                unit="page",
                **measure,
            )
        if pub.get("series"):
            series = _el(struct, "series")
            put(series, "title", "series", pub["series"], level="s")
            if pub.get("seriesVolume"):
                put(
                    series,
                    "biblScope",
                    "seriesVolume",
                    str(pub["seriesVolume"]),
                    unit="volume",
                )
        ids.append(pub_id)
    return ids


def build(pages: list[int] | None = None, with_print: bool = False) -> ET.Element:
    """The TEI document of the given pages, or of every content page."""
    data = load_dataset()
    records = exported_pages(data)
    if pages is not None:
        by_id = {r["sourcePageId"]: r for r in records}
        missing = [p for p in pages if p not in by_id]
        if missing:
            sys.exit(f"pages not among the exported content pages: {missing}")
        records = [by_id[p] for p in pages]
    claims = _load_claims({r["sourcePageId"] for r in records}) if with_print else {}

    tei = ET.Element(_t("TEI"))
    tei.set(f"{{{XML_NS}}}lang", "en")
    _header(tei, data.get("_meta") or {})
    body = _el(_el(_el(tei, "text"), "body"), "listBibl", type="publications")
    stand_off = _el(tei, "standOff")
    sources = _el(stand_off, "listBibl", type="sources")
    relations = ET.Element(_t("listRelation"))
    for rec in records:
        src = Source(rec)
        vals = Values(src)
        pub_ids: list[str] = []
        if rec["wikiPageKind"] == PUBLICATION_KIND:
            layer = load_layer(rec["sourcePageId"])
            if layer:
                pub_ids = _publications_from_layer(body, rec, layer, vals)
            else:
                pub_ids = _publication_from_record(body, rec, vals)
        vals.resolve(src.write(sources))
        for pub_id in pub_ids:
            _el(
                relations,
                "relation",
                name="describes",
                active=f"#{src.sid}",
                passive=f"#{pub_id}",
                resp="#app-rules",
                ana="#not-reviewed",
            )
        for claim in sorted(
            claims.get(rec["sourcePageId"], []), key=lambda c: c["subject"]
        ):
            record = claim["evidence"]["print"]["record"]
            rid = "src-print-" + record.replace("/", "-")
            bibl = _el(sources, "bibl", type="printEntry", xml_id=rid)
            _el(bibl, "idno", record, type="printRecord")
            _el(bibl, "idno", claim["evidence"]["print"]["sha256"], type="sha256")
            _el(
                relations,
                "relation",
                name="samePublicationAs",
                mutual=f"#{rid} #{src.sid}",
                resp="#app-concordance",
                ana=f"#{claim.get('state', 'proposed')}",
                n=claim["id"],
            )
    if not len(body):
        _el(body, "bibl")  # a sample without edition pages; listBibl needs a child
    if len(relations):
        stand_off.append(relations)
    _indent(tei)
    return tei


def _indent(elem: ET.Element, level: int = 0) -> None:
    """Indent element-only content; mixed content, the source text above all, stays untouched."""
    children = list(elem)
    if not children or elem.tag == _t("quote") or (elem.text and elem.text.strip()):
        return
    pad = "\n" + "  " * (level + 1)
    elem.text = pad
    for child in children:
        _indent(child, level + 1)
        child.tail = pad
    children[-1].tail = "\n" + "  " * level


def serialize(tei: ET.Element) -> bytes:
    buf = io.BytesIO()
    ET.ElementTree(tei).write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue() + b"\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--pages", type=int, nargs="+")
    parser.add_argument("--with-print", action="store_true")
    args = parser.parse_args()
    out_dir = OUT_LOCAL if args.with_print else OUT_PUBLIC
    out_dir.mkdir(parents=True, exist_ok=True)
    name = "-".join(map(str, args.pages)) if args.pages else "all"
    out = out_dir / f"klawiter-{name}.xml"
    out.write_bytes(serialize(build(args.pages, args.with_print)))
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
