"""Check the TEI export against the canonical data and write the acceptance report.

Regime: script pipeline. The report feeds the local acceptance view
(`docs/acceptance/`), which shows per milestone of the program
(`knowledge/plan.md`, Program from 2026-10-30) which checks pass, which fields
reach the TEI and how sample records look in source, values and TEI.

Data flow: `export_tei.build()` over every content page, serialised to
`data/output/tei/klawiter-all.xml` (regenerable, not versioned), parsed again
with lxml and checked against `docs/data/klawiter.json` and the publication
layer. The checks recompute what they expect from the canonical data and read
the export only as XML, so that a fault in the exporter is not checked by the
same fault. `check_export()` runs the checks on given bytes without
rebuilding; `run()` gives it the real export with tei_all and a second build,
then lets `pipeline/tei_mutations.py` break copies of the export and checks
each against the profile schema and the invariants. Writes
`docs/local/acceptance.json` (gitignored, local only).

tei_all is the TEI P5 4.12.0 RELAX NG schema, fetched once into
`data/cache/` and pinned by its sha256.

Usage: python -m uv run python pipeline/acceptance.py
Exit code 0 when every check that ran passed, 1 otherwise.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from collections import Counter

import export_tei
import tei_mutations
from lxml import etree

ROOT = export_tei.ROOT
OUT_XML = export_tei.OUT_PUBLIC / "klawiter-all.xml"
REPORT = ROOT / "docs" / "local" / "acceptance.json"
TEI_ALL = ROOT / "data" / "cache" / "tei_all-4.12.0.rng"
TEI_ALL_URL = (
    "https://www.tei-c.org/Vault/P5/4.12.0/xml/tei/custom/schema/relaxng/tei_all.rng"
)
TEI_ALL_SHA = "b0f115095ead2ccc6933aa3365c6f4a82cba3b2ec7eee7f76bb616d7a63b7e48"
PROFILE = ROOT / "docs" / "schema" / "klawiter-tei.rng"
T = "{http://www.tei-c.org/ns/1.0}"
XML_ID = export_tei.XML_ID
MAX_EXAMPLES = 20
SAMPLES = {
    212: "A single publication whose place and publisher came from the language model and whose place a review agent proposed",
    54: "The merged bibliography's first sample; classified as a work hub, its entry still describes a 1939 edition, which D1 therefore leaves out",
    3: "An edition page with several publications, each its own biblStruct",
    1605: "An author page, which lists a person's contributions and gives no publication of its own",
}
RANGE = re.compile(r"#string-range\(//\*\[@xml:id='([^']+)'\],(\d+),(\d+)\)")

# The milestones of knowledge/plan.md, Program from 2026-10-30; the plan holds their prose.
PROGRAM = [
    {
        "id": "D1",
        "title": "Faithful export",
        "repos": ["klawiter-rescue"],
        "goal": "Every value that reaches the TEI is the canonical value, with its producer, state and passage; the source text survives unaltered.",
        "verifiedBy": "The checks below over every content page, tei_all, and a mutation suite whose wrong documents must all fail.",
        "acceptedBy": "No acceptance by the operator; the profile questions go to D2.",
    },
    {
        "id": "D2",
        "title": "Complete model",
        "repos": ["klawiter-rescue"],
        "goal": "Record types, contents, translations, reprints and cross references have their TEI shape; nothing is pending.",
        "verifiedBy": "The coverage ledger has no pending field; the D1 checks extended to the new shapes.",
        "acceptedBy": "The operator accepts three sample objects in this view.",
    },
    {
        "id": "D3",
        "title": "SZD page local",
        "repos": ["SZD", "gams-www"],
        "goal": "szd-klawiter.xsl renders the object in the design of Stefan Zweig Digital, with an RDF branch and a menu entry.",
        "verifiedBy": "SZD check_data.py, the local harness (smoke, golden, RDF), screenshots in both languages, an independent review.",
        "acceptedBy": "No acceptance locally; visual acceptance on GAMS Staging.",
    },
    {
        "id": "D4",
        "title": "Staging",
        "repos": ["SZD", "gams-www"],
        "goal": "The object is ingested into GAMS Staging and renders there.",
        "verifiedBy": "Datastreams read back, before-and-after examples.",
        "acceptedBy": "The operator accepts the rendered pages on Staging (VPN).",
    },
    {
        "id": "C1",
        "title": "Curation surface",
        "repos": ["klawiter-rescue"],
        "goal": "A prototype of the review surface in which a person checks values against their passages.",
        "verifiedBy": "Tests, screenshots, an independent review.",
        "acceptedBy": "The operator tries it on real records.",
    },
    {
        "id": "P",
        "title": "Production",
        "repos": ["SZD", "gams-www", "klawiter-rescue"],
        "goal": "The reviewed bibliography in production on Stefan Zweig Digital.",
        "verifiedBy": "D1 to D4 rerun on reviewed data.",
        "acceptedBy": "The operator's order, after the human review round and the identifier scheme.",
    },
]
# The operator's open decisions, content first. Answers given in the chat are
# recorded in DECISIONS by the session and change the state shown in the view.
DECISIONS = ROOT / "pipeline" / "data" / "acceptance-decisions.json"
ACCEPTANCE = [
    {
        "id": "E6",
        "milestone": "D2",
        "question": "Do the sample pages show the publications as Klawiter's entries describe them?",
        "why": "This is the content check no test can make: whether each marked passage is the value beside it.",
        "recommendation": "Look at pages 212 and 3 before answering.",
        "evidence": [
            {
                "page": 212,
                "look": "Each value and its marked passage, and the two values the language model supplied.",
            },
            {
                "page": 3,
                "look": "Whether the page splits into the publications Klawiter lists.",
            },
        ],
    },
    {
        "id": "E8",
        "milestone": "D2",
        "question": "Should pages classified otherwise, whose entry still describes publications, get them in the export?",
        "why": "__N__ pages are not classified as edition pages, yet the publication layer reads publications from them; the export leaves these out today.",
        "recommendation": "Yes: the publication layer reads the entry itself, the page class only sorts pages.",
        "evidence": [
            {
                "page": 54,
                "look": "Classified as a work hub; the publication layer reads 31 editions from its entry, from 1939 to 2020, and none of them reaches the export.",
            }
        ],
    },
    {
        "id": "E3",
        "milestone": "D2",
        "question": "Should an author page become a person with linked contributions, not a publication?",
        "why": "Author pages list what a person wrote about Zweig, such as forewords in others' volumes.",
        "recommendation": "Yes: each listed item is a contribution to a publication, and the page is about its author.",
        "evidence": [
            {
                "page": 1605,
                "look": "An editorial foreword in a 1998 volume, listed under its author.",
            }
        ],
    },
    {
        "id": "E2",
        "milestone": "D3",
        "question": "Should Klawiter get its own menu entry 'Bibliographie' in Stefan Zweig Digital?",
        "why": "The menu links to the external site klawiter.stefanzweig.digital today.",
        "recommendation": "Yes: the bibliography becomes one of the holdings of Stefan Zweig Digital.",
        "evidence": [],
    },
    {
        "id": "E4",
        "milestone": "D3",
        "question": "Should the bibliography enter the search of Stefan Zweig Digital?",
        "why": "The search reads RDF, which needs a branch for the object in the RDF stylesheet.",
        "recommendation": "Yes, built in D3 with the page.",
        "evidence": [],
    },
    {
        "id": "E1",
        "milestone": "D3",
        "question": "Should the local page build on the branch gams-www-split?",
        "why": "The local harness of Stefan Zweig Digital lives there; the local master has diverged from origin.",
        "recommendation": "Yes.",
        "evidence": [],
    },
    {
        "id": "E5",
        "milestone": "D4",
        "question": "Is tei_all the gate until Staging shows how strictly GAMS validates?",
        "why": "Two productive files of Stefan Zweig Digital are invalid against tei_all, so GAMS may validate less strictly.",
        "recommendation": "Yes.",
        "evidence": [],
    },
    {
        "id": "E7",
        "milestone": "P",
        "question": "Does the identifier SZDKLA.<page>.<n> stay provisional until a publication is identified independently of its page?",
        "why": "Identifiers of Stefan Zweig Digital are never reused, so the scheme is fixed before production.",
        "recommendation": "Yes.",
        "evidence": [],
    },
]
OPEN_CHECKS = [
    (
        "record-types",
        "D2",
        "Every page kind has its TEI shape",
        "Author pages, work hubs and other pages are encoded as what they are.",
    ),
    (
        "szd-check-data",
        "D3",
        "SZD data gate passes",
        "check_data.py of the SZD repository accepts data/Klawiter/SZDKLA.xml.",
    ),
    (
        "harness-render",
        "D3",
        "The local harness renders the object",
        "szd-klawiter.xsl renders the object with SaxonJS without error, in German and English.",
    ),
    (
        "staging-ingest",
        "D4",
        "Ingest into GAMS Staging",
        "The datastreams on Staging match the local object.",
    ),
    (
        "curation-prototype",
        "C1",
        "The curation prototype records decisions",
        "A trial decision in the prototype reaches the trial log, not the real log.",
    ),
]


class Check:
    def __init__(self, cid: str, milestone: str, title: str, proves: str) -> None:
        self.d = {
            "id": cid,
            "milestone": milestone,
            "title": title,
            "proves": proves,
            "status": "pass",
            "measured": {"checked": 0, "failed": 0},
            "examples": [],
        }

    def ok(self, n: int = 1) -> None:
        self.d["measured"]["checked"] += n

    def fail(self, page: int | None, detail: str) -> None:
        self.d["measured"]["checked"] += 1
        self.d["measured"]["failed"] += 1
        self.d["status"] = "fail"
        if len(self.d["examples"]) < MAX_EXAMPLES:
            self.d["examples"].append({"page": page, "detail": detail})


def _tei_all() -> etree.RelaxNG:
    if not TEI_ALL.is_file():
        TEI_ALL.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(TEI_ALL_URL, timeout=60) as resp:  # noqa: S310 - fixed https URL
            TEI_ALL.write_bytes(resp.read())
    digest = hashlib.sha256(TEI_ALL.read_bytes()).hexdigest()
    if digest != TEI_ALL_SHA:
        sys.exit(f"{TEI_ALL} has sha256 {digest}, expected {TEI_ALL_SHA}")
    return etree.RelaxNG(etree.parse(str(TEI_ALL)))


def _schema_check(
    cid: str, title: str, proves: str, schema: etree.RelaxNG, doc
) -> dict:
    c = Check(cid, "D1", title, proves)
    if schema.validate(doc):
        c.ok()
    else:
        for err in list(schema.error_log)[:MAX_EXAMPLES]:
            c.fail(None, f"line {err.line}: {err.message}")
    return c.d


def _page_of(elem) -> int | None:
    m = re.match(r"(?:src-wiki-|SZDKLA\.)(\d+)", elem.get(XML_ID) or "")
    return int(m.group(1)) if m else None


def _offsets(quote) -> dict[str, tuple[int, int]]:
    """Each seg's start and end in the string value of its quote, in code points."""
    out: dict[str, tuple[int, int]] = {}
    pos = 0

    def walk(el) -> None:
        nonlocal pos
        start = pos
        pos += len(el.text or "")
        for child in el:
            walk(child)
            pos += len(child.tail or "")
        if el.tag == f"{T}seg":
            out[el.get(XML_ID)] = (start, pos)

    walk(quote)
    return out


def _page_of_pointer(ptr: str | None) -> int | None:
    m = re.fullmatch(r"#src-wiki-(\d+)", ptr or "")
    return int(m.group(1)) if m else None


def _value(
    tag: str,
    text: str,
    producer: str,
    state: str,
    evidence: list[dict],
    **attrs: str,
) -> dict:
    """An expected valued element: its key (tag, text, every other attribute) and provenance."""
    return {
        "key": (tag, text, tuple(sorted(attrs.items()))),
        "producer": producer,
        "state": state,
        "evidence": evidence,
    }


def _expected_structs(rec: dict) -> list[dict]:
    """The biblStructs the canonical data call for on one page, recomputed without the exporter.

    Each has its identifier, @corresp, @ana and the valued elements it must
    hold, no more and no fewer. A producer the data do not record is
    "undeclared", which no application stands for, so that the export
    cannot supply a default unnoticed.
    """
    page = rec["sourcePageId"]
    if rec["wikiPageKind"] != export_tei.PUBLICATION_KIND:
        return []
    states = (rec.get("review") or {}).get("fieldStates") or {}
    layer = export_tei.load_layer(page)
    if not layer:
        prov, evid = rec.get("_provenance") or {}, rec.get("fieldEvidence") or {}

        def flat(tag: str, field: str, text: str, **attrs: str) -> dict:
            return _value(
                tag,
                text,
                prov.get(field, "undeclared"),
                states.get(field, "not-reviewed"),
                evid.get(field, []),
                **attrs,
            )

        vals = [flat("title", "title", str(rec.get("title", "")), level="m")]
        if rec.get("translator"):
            vals.append(
                flat(
                    "persName",
                    "translator",
                    str(rec["translator"]),
                    role="translator",
                    label="Translated by",
                )
            )
        if rec.get("languageCode"):
            vals.append(
                flat(
                    "textLang",
                    "language",
                    str(rec.get("language", "")),
                    mainLang=str(rec["languageCode"]),
                )
            )
        for tag, field in (("pubPlace", "location"), ("publisher", "publisher")):
            if rec.get(field):
                vals.append(flat(tag, field, str(rec[field])))
        if rec.get("year"):
            vals.append(flat("date", "year", str(rec["year"]), when=str(rec["year"])))
        if rec.get("pageCount"):
            n = str(rec["pageCount"])
            vals.append(flat("measure", "pageCount", n, unit="page", quantity=n))
        return [
            {
                "id": f"SZDKLA.{page}.1",
                "corresp": rec["@id"],
                "ana": None,
                "values": vals,
            }
        ]

    out = []
    for i, pub in enumerate(layer, 1):
        prov, spans = pub.get("provenance") or {}, pub.get("valueSpans") or {}

        def put(
            tag: str,
            field: str,
            text: str,
            evidence: list[dict] | None = None,
            state_field: str | None = None,
            prov=prov,
            spans=spans,
            **attrs: str,
        ) -> dict:
            # A review state of the page record applies where its value is this value.
            sf = state_field or field
            state = (
                states[sf]
                if sf in states and str(rec.get(sf, "")) == text
                else "not-reviewed"
            )
            return _value(
                tag,
                text,
                prov.get(field, "undeclared"),
                state,
                spans.get(field, []) if evidence is None else evidence,
                **attrs,
            )

        vals = []
        if pub.get("title"):
            vals.append(put("title", "title", pub["title"], level="m"))
        for cr in pub.get("credits") or []:
            name = cr.get("name", "")
            vals.append(
                put(
                    "persName",
                    "credits",
                    name,
                    [
                        s
                        for s in spans.get("credits", [])
                        if s.get("part") == "name" and s.get("value") == name
                    ],
                    role=cr.get("role", ""),
                    label=cr.get("creditLabel") or cr.get("role", ""),
                )
            )
        if pub.get("languageCode"):
            vals.append(
                put(
                    "textLang",
                    "language",
                    pub.get("language", ""),
                    mainLang=pub["languageCode"],
                )
            )
        if pub.get("editionStatement"):
            vals.append(put("edition", "editionStatement", pub["editionStatement"]))
        for pl in pub.get("places") or []:
            ev = [s for s in spans.get("places", []) if s.get("value") == pl]
            vals.append(put("pubPlace", "places", pl, ev, "location"))
        if pub.get("publisher"):
            vals.append(put("publisher", "publisher", pub["publisher"]))
        if pub.get("year"):
            text = str(pub.get("yearRaw") or pub["year"])
            vals.append(put("date", "yearRaw", text, when=str(pub["year"])))
        extent = pub.get("extent") or {}
        if extent.get("raw"):
            ev = [s for s in spans.get("extent", []) if s.get("part") == "raw"]
            qty = (
                {"quantity": str(extent["numbered"])} if extent.get("numbered") else {}
            )
            vals.append(put("measure", "extent", extent["raw"], ev, unit="page", **qty))
        if pub.get("series"):
            vals.append(put("title", "series", pub["series"], level="s"))
            if pub.get("seriesVolume"):
                vals.append(
                    put(
                        "biblScope",
                        "seriesVolume",
                        str(pub["seriesVolume"]),
                        unit="volume",
                    )
                )
        out.append(
            {
                "id": f"SZDKLA.{page}.{i}",
                "corresp": pub["id"],
                "ana": f"#{pub['reviewStatus']}" if pub.get("reviewStatus") else None,
                "values": vals,
            }
        )
    return out


def _exported_values(struct) -> list:
    """The valued elements of a biblStruct, each with its key as `_value` builds it."""
    out = []
    for el in struct.iter():
        if not isinstance(el.tag, str) or el.get("resp") is None:
            continue
        attrs = {
            k: v
            for k, v in el.attrib.items()
            if k not in ("resp", "ana", "source", XML_ID)
        }
        parent = el.getparent()
        if parent is not None and parent.tag == f"{T}respStmt":
            label = parent.find(f"{T}resp")
            attrs["label"] = label.text if label is not None else None
        key = (etree.QName(el).localname, el.text or "", tuple(sorted(attrs.items())))
        out.append((key, el))
    return out


def _located(evidence: list[dict]) -> tuple[int, int] | None:
    return next(
        (
            (e["textStart"], e["textEnd"])
            for e in evidence
            if isinstance(e.get("textStart"), int) and isinstance(e.get("textEnd"), int)
        ),
        None,
    )


@dataclasses.dataclass
class Checked:
    """The checks of one export and what the report reads besides them."""

    checks: list[dict]
    doc: etree._Element | None = None
    coverage: list[dict] = dataclasses.field(default_factory=list)
    values: Counter = dataclasses.field(default_factory=Counter)
    structs: dict = dataclasses.field(default_factory=dict)
    seg_pos: dict = dataclasses.field(default_factory=dict)


def _profile() -> etree.RelaxNG:
    return etree.RelaxNG(etree.parse(str(PROFILE)))


def check_export(
    raw: bytes,
    records: dict[int, dict],
    *,
    profile: etree.RelaxNG | None = None,
    tei_all: etree.RelaxNG | None = None,
    rebuilt: bytes | None = None,
    meta: dict | None = None,
) -> Checked:
    """Run the checks on the bytes of an export of `records`, without rebuilding it.

    tei_all, the determinism check, the profile schema and the header check
    (`meta`, the dataset's `_meta`) run only when their input is given, so that the mutation suite can check many wrong documents
    against the profile schema and the invariants in reasonable time.
    """
    checks: list[dict] = []

    c = Check(
        "well-formed",
        "D1",
        "The export is well-formed XML",
        "An XML parser reads the whole export without error.",
    )
    try:
        doc = etree.fromstring(raw)
        c.ok()
    except etree.XMLSyntaxError as exc:
        c.fail(None, str(exc))
        return Checked(checks=[c.d])
    checks.append(c.d)
    if tei_all is not None:
        checks.append(
            _schema_check(
                "tei-all",
                "The export is valid TEI",
                "The export validates against tei_all of TEI P5 4.12.0.",
                tei_all,
                doc,
            )
        )

    if rebuilt is not None:
        c = Check(
            "deterministic",
            "D1",
            "The export is reproducible",
            "Two runs over the same data give the same bytes.",
        )
        c.ok() if rebuilt == raw else c.fail(None, "two builds differ")
        checks.append(c.d)

    ids = Counter(el.get(XML_ID) for el in doc.iter() if el.get(XML_ID))
    by_id = {el.get(XML_ID): el for el in doc.iter() if el.get(XML_ID)}
    c = Check("ids-unique", "D1", "Identifiers are unique", "No xml:id occurs twice.")
    for ident, n in ids.items():
        c.ok() if n == 1 else c.fail(
            _page_of(by_id[ident]), f"{ident} occurs {n} times"
        )
    checks.append(c.d)

    header = doc.find(f"{T}teiHeader")
    c = Check(
        "header-title",
        "D1",
        "The object's title comes first",
        "The first title in the header, which the Dublin Core mapping of GAMS reads, is the object's German title, and no source entry stands in the header.",
    )
    first = header.find(f".//{T}title") if header is not None else None
    c.ok() if first is not None and first.text == "Klawiter-Bibliographie Stefan Zweig digital" else c.fail(
        None, f"first title is {first.text if first is not None else None!r}"
    )
    wiki_in_header = (
        header.findall(f".//{T}bibl[@type='wikiPage']") if header is not None else []
    )
    c.ok() if not wiki_in_header else c.fail(
        None, f"{len(wiki_in_header)} source entries in the header"
    )
    checks.append(c.d)

    if meta is not None:
        c = Check(
            "header-provenance",
            "D1",
            "The header names the dump and the producers",
            "The checksum of the wiki dump and the name and version of each application in the header are those the canonical data record.",
        )
        dump = meta.get("sourceDump") or {}
        sha = doc.find(f"{T}teiHeader//{T}sourceDesc/{T}bibl/{T}idno[@type='sha256']")
        got_sha = sha.text if sha is not None else None
        c.ok() if got_sha == dump.get("sha256") else c.fail(
            None, f"dump sha256 {got_sha}, expected {dump.get('sha256')}"
        )
        llm = meta.get("llmEnrichment") or {}
        frozen = llm.get("frozenAt", "")
        version = str(meta.get("version", "0"))
        for xml_id, ident, ver in (
            ("app-rules", "klawiter-rules", version),
            ("app-derivation", "klawiter-derivation", version),
            ("app-concordance", "klawiter-concordance", version),
            # @version takes a number; the date the model cache was frozen stands in for it.
            ("app-llm", llm.get("model"), frozen[:10].replace("-", ".")),
        ):
            el = by_id.get(xml_id)
            got = (el.get("ident"), el.get("version")) if el is not None else None
            c.ok() if got == (ident, ver) else c.fail(
                None, f"{xml_id}: {got}, expected {(ident, ver)}"
            )
        desc = by_id.get("app-llm")
        desc = desc.findtext(f"{T}desc") if desc is not None else ""
        for part in (frozen, llm.get("promptSha256", "")):
            c.ok() if part and part in desc else c.fail(
                None, f"app-llm description lacks {part!r}"
            )
        checks.append(c.d)

    # Source text: the quote of each page is the canonical entry text, character for character.
    quotes = {
        _page_of(b): b.find(f"{T}quote")
        for b in doc.iterfind(f".//{T}standOff/{T}listBibl/{T}bibl[@type='wikiPage']")
    }
    c = Check(
        "source-text",
        "D1",
        "Klawiter's text survives unaltered",
        "The text of every source entry in the TEI equals the entry text of the canonical data, character for character, and its page title, page id, revision, page kind and categories are those of the page.",
    )
    for page, rec in records.items():
        q = quotes.get(page)
        want = rec.get("fullBibliographicEntry") or ""
        got = "".join(q.itertext()) if q is not None else None
        if got == want:
            c.ok()
        else:
            at = next(
                (i for i, (a, b) in enumerate(zip(got or "", want)) if a != b),
                min(len(got or ""), len(want)),
            )
            c.fail(
                page,
                f"differs at offset {at}" if got is not None else "no source entry",
            )
        bibl = q.getparent() if q is not None else None
        if bibl is None:
            continue
        revision = (rec.get("revisionDates") or {}).get("lastRevisionId")
        entry = {
            "kind": bibl.get("subtype"),
            "title": bibl.findtext(f"{T}title") or "",
            "pageId": bibl.findtext(f"{T}idno[@type='pageId']"),
            "revision": bibl.findtext(f"{T}idno[@type='revision']"),
            "categories": [
                seg.text or ""
                for seg in bibl.iterfind(f"{T}note[@type='categories']/{T}seg")
            ],
        }
        canon = {
            "kind": rec["wikiPageKind"],
            "title": rec.get("title") or "",
            "pageId": str(page),
            "revision": str(revision) if revision is not None else None,
            "categories": list(rec.get("categories") or []),
        }
        for key, want_val in canon.items():
            c.ok() if entry[key] == want_val else c.fail(
                page, f"{key} {entry[key]!r}, expected {want_val!r}"
            )
    checks.append(c.d)

    seg_pos: dict[str, tuple[int, int, str]] = {}
    for page, q in quotes.items():
        if q is None:
            continue
        text = "".join(q.itertext())
        for sid, (s, e) in _offsets(q).items():
            seg_pos[sid] = (s, e, text)

    # Pointers: every #id resolves, every range lies inside its entry, every seg is pointed to.
    c = Check(
        "pointers",
        "D1",
        "Every pointer resolves",
        "Every @resp, @ana, @source, @active, @passive and @mutual names an element of the document, and every range pointer lies inside its entry.",
    )
    pointed: set[str] = set()
    for el in doc.iter():
        for attr in ("resp", "ana", "source", "active", "passive", "mutual"):
            val = el.get(attr)
            if not val:
                continue
            m = RANGE.fullmatch(val)
            if m:
                q = by_id.get(m.group(1))
                start, length = int(m.group(2)), int(m.group(3))
                if q is not None and start + length <= len("".join(q.itertext())):
                    c.ok()
                else:
                    c.fail(
                        _page_of(q) if q is not None else None,
                        f"range {val} outside its entry",
                    )
                continue
            for ptr in val.split():
                if ptr.startswith("#") and ptr[1:] in by_id:
                    c.ok()
                    pointed.add(ptr[1:])
                else:
                    c.fail(None, f"{attr}={ptr} resolves to nothing")
    checks.append(c.d)
    c = Check(
        "segs-pointed",
        "D1",
        "Every marked passage carries a value",
        "Every seg in a source entry is the passage of at least one value, so marked text is read text.",
    )
    for sid in seg_pos:
        c.ok() if sid in pointed else c.fail(
            _page_of(by_id[sid]), f"{sid} is pointed to by no value"
        )
    checks.append(c.d)

    # Publications: one biblStruct per publication of an edition page, none for other kinds.
    expected = {page: _expected_structs(rec) for page, rec in records.items()}
    structs = {s.get(XML_ID): s for s in doc.iterfind(f".//{T}body//{T}biblStruct")}
    describes: dict[int, list] = {}
    for rel in doc.iterfind(f".//{T}relation[@name='describes']"):
        describes.setdefault(_page_of_pointer(rel.get("active")), []).append(rel)
    c = Check(
        "publications",
        "D1",
        "Each publication is its own record",
        "An edition page gives one biblStruct per publication of its publication layer, or one when it has none, with the record link of the canonical data and a relation from its source entry; no other page kind gives a biblStruct.",
    )
    wanted_ids = set()
    for page, rec in records.items():
        want = [s["id"] for s in expected[page]]
        wanted_ids.update(want)
        got = [rel.get("passive", "")[1:] for rel in describes.get(page, [])]
        c.ok() if got == want else c.fail(
            page, f"{rec['wikiPageKind']}: relations to {got}, expected {want}"
        )
        for exp in expected[page]:
            struct = structs.get(exp["id"])
            if struct is None:
                c.fail(page, f"{exp['id']} is missing")
            elif struct.get("corresp") != exp["corresp"]:
                c.fail(
                    page,
                    f"{exp['id']}: corresp {struct.get('corresp')}, expected {exp['corresp']}",
                )
            else:
                c.ok()
    for sid in structs.keys() - wanted_ids:
        if _page_of(structs[sid]) in records:
            c.fail(_page_of(structs[sid]), f"{sid} is not called for by the data")
    checks.append(c.d)

    # Values: recomputed from the canonical data; the valued elements of each
    # biblStruct must be exactly the expected ones, then producer, state and passage.
    c_val = Check(
        "values",
        "D1",
        "Every exported value arrives unchanged",
        "The valued elements of each publication (every element with @resp, its text and attributes) are exactly those the canonical data call for, none missing and none added; print citations likewise.",
    )
    c_resp = Check(
        "producers",
        "D1",
        "Every value names its producer",
        "@resp of each value and print citation is the application of the producer class the canonical data record for it; a describes relation names the rules.",
    )
    c_state = Check(
        "states",
        "D1",
        "Every value carries its review state",
        "@ana of each value and print citation is its state in the canonical data, the review state where one is recorded and not-reviewed otherwise; @ana of a publication is its review status, and a describes relation is not reviewed.",
    )
    c_src = Check(
        "passages",
        "D1",
        "Every located value points to its passage",
        "A value whose evidence locates a passage points to it and the passage is the text at those offsets; a value read from the page title or a category points there; a value without evidence points nowhere.",
    )
    app = {"regex": "#app-rules", "llm": "#app-llm", "derived": "#app-derivation"}
    values = Counter()

    def judge(page: int, rec: dict, label: str, exp: dict, el) -> None:
        # No default: a producer class the export does not declare is a fault, not a rule.
        want_resp = app.get(exp["producer"], f"undeclared producer {exp['producer']!r}")
        c_resp.ok() if el.get("resp") == want_resp else c_resp.fail(
            page, f"{label}: resp {el.get('resp')}, expected {want_resp}"
        )
        c_state.ok() if el.get("ana") == f"#{exp['state']}" else c_state.fail(
            page, f"{label}: ana {el.get('ana')}, expected #{exp['state']}"
        )
        span = _located(exp["evidence"])
        src = el.get("source")
        if span is None:
            gaps = {e.get("gap") for e in exp["evidence"]}
            meta = None
            if "page-title" in gaps:
                meta = re.compile(rf"#src-wiki-{page}-title")
            elif "category-markup" in gaps and rec.get("categories"):
                meta = re.compile(rf"#src-wiki-{page}-cat\d+")
            if meta is not None:
                if src and meta.fullmatch(src) and src[1:] in by_id:
                    c_src.ok()
                    values["withMetaSource"] += 1
                else:
                    c_src.fail(page, f"{label}: source {src}, expected {meta.pattern}")
                return
            values[next((g for g in gaps if g), "no-evidence")] += 1
            c_src.ok() if src is None else c_src.fail(
                page, f"{label}: source {src} without evidence"
            )
            return
        m = RANGE.fullmatch(src or "")
        if m and m.group(1) == f"src-wiki-{page}-text":
            got = (int(m.group(2)), int(m.group(2)) + int(m.group(3)))
            values["byRange"] += 1
        elif src and src[1:] in seg_pos and _page_of(by_id[src[1:]]) == page:
            got = seg_pos[src[1:]][:2]
        else:
            c_src.fail(page, f"{label} has no passage of its entry, evidence {span}")
            return
        if got != span:
            c_src.fail(page, f"{label} points to {got}, evidence {span}")
            return
        entry = rec.get("fullBibliographicEntry") or ""
        # A print citation records its source text, so its passage must be those words.
        if "verbatim" in exp and entry[span[0] : span[1]] != exp["verbatim"]:
            c_src.fail(
                page,
                f"{label}: passage {span} reads {entry[span[0] : span[1]]!r}",
            )
            return
        c_src.ok()
        values["withPassage"] += 1
        if (rec.get("fullBibliographicEntry") or "")[span[0] : span[1]] != el.text:
            values["textDiffers"] += 1

    for page, rec in records.items():
        for exp_struct in expected[page]:
            struct = structs.get(exp_struct["id"])
            if struct is None:
                c_val.fail(page, f"{exp_struct['id']} is missing")
                continue
            want_ana = exp_struct["ana"]
            c_state.ok() if struct.get("ana") == want_ana else c_state.fail(
                page,
                f"{exp_struct['id']}: ana {struct.get('ana')}, expected {want_ana}",
            )
            got: dict[tuple, list] = {}
            for key, el in _exported_values(struct):
                got.setdefault(key, []).append(el)
            for exp in exp_struct["values"]:
                values["total"] += 1
                tag, text = exp["key"][0], exp["key"][1]
                label = f"{exp_struct['id']} {tag} {text!r}"
                if not got.get(exp["key"]):
                    c_val.fail(page, f"{label} {dict(exp['key'][2])} is missing")
                    continue
                c_val.ok()
                judge(page, rec, label, exp, got[exp["key"]].pop(0))
            for key, els in got.items():
                for _ in els:
                    c_val.fail(page, f"{exp_struct['id']}: unexpected {key}")
        # Print citations: the note of the source entry, in the order of the data.
        state = ((rec.get("review") or {}).get("fieldStates") or {}).get(
            "printAddressCitations", "not-reviewed"
        )
        # Citations are read by rule only (lib/print_addresses.py, called from
        # 05_to_jsonld.py); the dataset records no producer class for them.
        producer = (rec.get("_provenance") or {}).get("printAddressCitations", "regex")
        source = by_id.get(f"src-wiki-{page}")
        cited = (
            source.findall(f"{T}note[@type='printCitations']/{T}idno")
            if source is not None
            else []
        )
        cites = rec.get("printAddressCitations") or []
        # sourceStart counts in the raw wikitext; the entry-text passage is the
        # located evidence, one per citation in the same order.
        cite_ev = (rec.get("fieldEvidence") or {}).get("printAddressCitations") or []
        if len(cited) != len(cites):
            c_val.fail(page, f"{len(cited)} print citations, expected {len(cites)}")
        for n, (cite, el) in enumerate(zip(cites, cited)):
            values["total"] += 1
            label = f"print citation {cite.get('printAddress')!r}"
            if (el.text, el.get("type"), el.get("subtype")) != (
                cite.get("printAddress"),
                "printAddress",
                cite.get("printVolume"),
            ):
                c_val.fail(page, f"{label}: {el.text!r} {el.get('subtype')}")
                continue
            c_val.ok()
            judge(
                page,
                rec,
                label,
                {
                    "producer": producer,
                    "state": state,
                    "evidence": [cite_ev[n]] if n < len(cite_ev) else [],
                    "verbatim": cite.get("sourceValue"),
                },
                el,
            )
        for rel in describes.get(page, []):
            c_resp.ok() if rel.get("resp") == "#app-rules" else c_resp.fail(
                page, f"describes relation: resp {rel.get('resp')}"
            )
            c_state.ok() if rel.get("ana") == "#not-reviewed" else c_state.fail(
                page, f"describes relation: ana {rel.get('ana')}"
            )
    checks += [c_val.d, c_resp.d, c_state.d, c_src.d]

    c = Check(
        "field-ledger",
        "D1",
        "Every field has a decided place",
        "Every field that occurs in the canonical data is declared as exported, pending for a milestone, or excluded with a reason.",
    )
    coverage = []
    for layer_name, counts in (
        ("page", Counter(k for r in records.values() for k in r)),
        ("publication", _layer_field_counts(records)),
    ):
        declared = export_tei.FIELDS[layer_name]
        for field, n in sorted(counts.items()):
            spec = declared.get(field)
            if spec is None:
                c.fail(
                    None, f"{layer_name} field {field} ({n} records) is not declared"
                )
                coverage.append(
                    {
                        "field": field,
                        "layer": layer_name,
                        "records": n,
                        "disposition": "undeclared",
                        "target": None,
                        "milestone": None,
                        "reason": None,
                    }
                )
                continue
            c.ok()
            coverage.append(
                {
                    "field": field,
                    "layer": layer_name,
                    "records": n,
                    "disposition": spec[0],
                    "target": spec[1] if spec[0] == "exported" else None,
                    "milestone": spec[1] if spec[0] == "pending" else None,
                    "reason": spec[-1] if spec[0] != "exported" else None,
                }
            )
    checks.append(c.d)

    c = Check(
        "no-print-text",
        "D1",
        "The versioned export holds no print data",
        "The wiki export carries no print record, since the rights to the print volumes are unresolved.",
    )
    printed = doc.findall(f".//{T}bibl[@type='printEntry']")
    c.ok() if not printed else c.fail(None, f"{len(printed)} print records")
    checks.append(c.d)

    if profile is not None:
        checks.append(
            _schema_check(
                "profile-schema",
                "Profile schema admits only the profile",
                "The RELAX NG profile schema follows the export's structure and rejects what TEI admits but the profile does not.",
                profile,
                doc,
            )
        )
    return Checked(
        checks=checks,
        doc=doc,
        coverage=coverage,
        values=values,
        structs=structs,
        seg_pos=seg_pos,
    )


def _mutation_check(
    raw: bytes, records: dict[int, dict], profile: etree.RelaxNG, meta: dict
) -> dict:
    """Each deliberately broken copy of the export must fail at least one check."""
    c = Check(
        "mutation-suite",
        "D1",
        "Wrong documents are rejected",
        "Each of a set of deliberately broken exports fails at least one check of the profile schema and the invariants.",
    )
    results = tei_mutations.run(
        raw,
        records,
        check=lambda doc, recs: (
            check_export(doc, recs, profile=profile, meta=meta).checks
        ),
    )
    for res in results:
        if res["caught"]:
            c.ok()
        else:
            c.fail(
                res.get("page"),
                f"{res['id']} ({res['fault']}) is caught by no check"
                if res["applied"]
                else f"{res['id']} ({res['fault']}) found nothing to mutate",
            )
    c.d["note"] = "; ".join(
        f"{res['id']}: {', '.join(res['caughtBy']) or 'not caught'}" for res in results
    )
    return c.d


def run() -> dict:
    data = export_tei.load_dataset()
    records = {r["sourcePageId"]: r for r in export_tei.exported_pages(data)}
    raw = export_tei.serialize(export_tei.build())
    OUT_XML.parent.mkdir(parents=True, exist_ok=True)
    OUT_XML.write_bytes(raw)
    profile = _profile()
    checked = check_export(
        raw,
        records,
        profile=profile,
        tei_all=_tei_all(),
        rebuilt=export_tei.serialize(export_tei.build()),
        meta=data["_meta"],
    )
    if checked.doc is None:
        return {"checks": checked.checks}
    checks = checked.checks
    # tei_all runs once, on the real export; the mutants meet the profile schema and the invariants.
    checks.append(_mutation_check(raw, records, profile, data["_meta"]))
    for cid, ms, title, proves in OPEN_CHECKS:
        k = Check(cid, ms, title, proves)
        k.d["status"] = "open"
        checks.append(k.d)

    doc, values, structs, seg_pos = (
        checked.doc,
        checked.values,
        checked.structs,
        checked.seg_pos,
    )
    without = {
        k: v
        for k, v in values.items()
        if k not in ("total", "withPassage", "withMetaSource", "textDiffers", "byRange")
    }
    return {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "generatedBy": "pipeline/acceptance.py",
        "commit": _commit(),
        "dataset": {
            "version": str(data["_meta"].get("version")),
            "pages": len(records),
            "publications": len(structs),
        },
        "program": _program(checks),
        "checks": checks,
        "coverage": checked.coverage,
        "values": {
            "total": values["total"],
            "withPassage": values["withPassage"],
            "byRange": values["byRange"],
            "withMetaSource": values["withMetaSource"],
            "withoutSource": without,
            "textDiffers": values["textDiffers"],
        },
        "samples": [
            _sample(doc, records[p], why, seg_pos)
            for p, why in SAMPLES.items()
            if p in records
        ],
        "acceptance": _acceptance(records),
    }


def _acceptance(records: dict) -> list[dict]:
    answers = (
        json.loads(DECISIONS.read_text(encoding="utf-8")) if DECISIONS.is_file() else {}
    )
    n = str(_unclassified(records))
    out = []
    for item in ACCEPTANCE:
        answer = answers.get(item["id"])
        out.append(
            {
                **item,
                "why": item["why"].replace("__N__", n),
                "state": "open"
                if answer is None
                else ("accepted" if answer["answer"] == "yes" else "rejected"),
                "answer": answer,
            }
        )
    return out


def _unclassified(records: dict) -> int:
    """Pages of another kind than edition page for which the publication layer holds publications."""
    return sum(
        1
        for p, r in records.items()
        if r["wikiPageKind"] != export_tei.PUBLICATION_KIND and export_tei.load_layer(p)
    )


def _layer_field_counts(records: dict) -> Counter:
    n = Counter()
    for page, rec in records.items():
        if rec["wikiPageKind"] == export_tei.PUBLICATION_KIND:
            for pub in export_tei.load_layer(page):
                n.update(pub.keys())
    return n


def _program(checks: list[dict]) -> list[dict]:
    out = []
    for m in PROGRAM:
        own = [c for c in checks if c["milestone"] == m["id"]]
        ran = [c for c in own if c["status"] in ("pass", "fail")]
        if own and all(c["status"] == "pass" for c in own):
            state = "done"
        elif ran:
            state = "in-progress"
        else:
            state = "open"
        out.append({**m, "state": state})
    return out


def _sample(doc, rec: dict, why: str, seg_pos: dict) -> dict:
    """A sample page as the TEI states it: values read back from the export, not from the data."""
    page = rec["sourcePageId"]
    rels = doc.iterfind(
        f".//{T}relation[@name='describes'][@active='#src-wiki-{page}']"
    )
    producer = {"#app-rules": "regex", "#app-llm": "llm", "#app-derivation": "derived"}
    field_of = {
        "title": "title",
        "persName": "person",
        "pubPlace": "place",
        "publisher": "publisher",
        "date": "date",
        "textLang": "language",
        "measure": "extent",
        "edition": "edition",
        "biblScope": "series volume",
    }
    text = rec.get("fullBibliographicEntry") or ""
    pubs, frags = [], []
    source = doc.find(f".//{T}bibl[@{XML_ID}='src-wiki-{page}']")
    for rel in rels:
        struct = doc.find(f".//{T}biblStruct[@{XML_ID}='{rel.get('passive')[1:]}']")
        vals = []
        for el in struct.iter():
            if el.get("resp") is None:
                continue
            tag = etree.QName(el).localname
            field = (
                "series"
                if tag == "title" and el.get("level") == "s"
                else field_of.get(tag, tag)
            )
            src, span, gap = el.get("source"), None, None
            m = RANGE.fullmatch(src or "")
            if m:
                span = [int(m.group(2)), int(m.group(2)) + int(m.group(3))]
            elif src and src[1:] in seg_pos:
                span = list(seg_pos[src[1:]][:2])
            elif src and src.endswith("-title"):
                gap = "page-title"
            elif src and "-cat" in src:
                gap = "category-markup"
            else:
                gap = "not-located"
            vals.append(
                {
                    "field": field,
                    "value": el.text or "",
                    "producer": producer.get(el.get("resp"), "regex"),
                    "state": el.get("ana", "#not-reviewed")[1:],
                    "span": span,
                    "gap": gap,
                    "textDiffers": bool(span)
                    and text[span[0] : span[1]] != (el.text or ""),
                }
            )
        pubs.append(
            {
                "id": struct.get(XML_ID),
                "state": struct.get("ana", "#not-reviewed")[1:],
                "values": vals,
            }
        )
        frags.append(struct)
    if not pubs:
        pubs = _layer_preview(page)
    frags.append(source)
    tei = "\n".join(
        _dedent(etree.tostring(f, encoding="unicode", with_tail=False)) for f in frags
    )
    return {
        "page": page,
        "title": rec.get("title", ""),
        "kind": rec["wikiPageKind"],
        "why": why,
        "entry": text,
        "publications": pubs,
        "tei": tei,
    }


def _layer_preview(page: int) -> list[dict]:
    """What the publication layer reads from a page the export leaves out (decision E8)."""
    out = []
    for pub in export_tei.load_layer(page):
        prov, spans = pub.get("provenance") or {}, pub.get("valueSpans") or {}
        vals = []
        for field, label in (
            ("title", "title"),
            ("credits", "person"),
            ("places", "place"),
            ("publisher", "publisher"),
            ("yearRaw", "date"),
            ("extent", "extent"),
        ):
            for ev in spans.get(field, []):
                if field in ("credits", "extent") and ev.get("part") not in (
                    "name",
                    "raw",
                ):
                    continue
                located = isinstance(ev.get("textStart"), int)
                vals.append(
                    {
                        "field": label,
                        "value": ev.get("value", ""),
                        "producer": prov.get(field, "regex"),
                        "state": "not-reviewed",
                        "span": [ev["textStart"], ev["textEnd"]] if located else None,
                        "gap": None if located else ev.get("gap", "not-located"),
                        "textDiffers": False,
                    }
                )
        out.append(
            {
                "id": pub["id"],
                "state": pub.get("reviewStatus", "proposed"),
                "exported": False,
                "values": vals,
            }
        )
    return out


def _dedent(xml: str) -> str:
    """Strip the namespace declaration and the export's indentation level of a fragment."""
    xml = xml.replace(' xmlns="http://www.tei-c.org/ns/1.0"', "")
    lines = xml.split("\n")
    pads = [len(ln) - len(ln.lstrip(" ")) for ln in lines[1:] if ln.strip()]
    cut = max(min(pads) - 2, 0) if pads else 0
    return "\n".join(
        [lines[0]] + [ln[cut:] if ln[:cut].strip() == "" else ln for ln in lines[1:]]
    )


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> int:
    report = run()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    failed = [c["id"] for c in report["checks"] if c["status"] == "fail"]
    ran = [c for c in report["checks"] if c["status"] in ("pass", "fail")]
    print(
        f"wrote {REPORT.relative_to(ROOT)}: {len(ran) - len(failed)} of {len(ran)} checks pass"
        + (f"; failing: {', '.join(failed)}" if failed else "")
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
