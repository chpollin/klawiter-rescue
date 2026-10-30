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
same fault. Writes `docs/local/acceptance.json` (gitignored, local only).

tei_all is the TEI P5 4.12.0 RELAX NG schema, fetched once into
`data/cache/` and pinned by its sha256.

Usage: python -m uv run python pipeline/acceptance.py
Exit code 0 when every check that ran passed, 1 otherwise.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from collections import Counter

import export_tei
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
ACCEPTANCE = [
    {
        "id": "E1",
        "milestone": "D3",
        "question": "The SZD harness builds on the branch gams-www-split.",
        "state": "open",
    },
    {
        "id": "E2",
        "milestone": "D3",
        "question": "Klawiter gets its own SZD menu entry 'Bibliographie' in place of the external link.",
        "state": "open",
    },
    {
        "id": "E3",
        "milestone": "D2",
        "question": "Author pages and work hubs become links in the TEI, not publications.",
        "state": "open",
    },
    {
        "id": "E4",
        "milestone": "D3",
        "question": "Klawiter enters the SZD search through an RDF branch.",
        "state": "open",
    },
    {
        "id": "E5",
        "milestone": "D4",
        "question": "How strictly GAMS validates is settled on Staging; until then tei_all is the gate.",
        "state": "open",
    },
    {
        "id": "E6",
        "milestone": "D2",
        "question": "The three sample objects in this view show the publications as Klawiter's entries describe them.",
        "state": "open",
    },
    {
        "id": "E8",
        "milestone": "D2",
        "question": "Pages not classified as edition pages whose entry still yields publications (__N__ pages, e.g. page 54) get their biblStructs from the publication layer.",
        "state": "open",
    },
    {
        "id": "E7",
        "milestone": "P",
        "question": "The identifier scheme: SZDKLA.<page>.<n> stays provisional until a publication is identified independently of its page.",
        "state": "open",
    },
]
OPEN_CHECKS = [
    (
        "mutation-suite",
        "D1",
        "Wrong documents are rejected",
        "Each of a set of deliberately broken exports fails at least one check.",
    ),
    (
        "profile-schema",
        "D1",
        "Profile schema admits only the profile",
        "The RELAX NG profile schema follows the export's structure and rejects what TEI admits but the profile does not.",
    ),
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


def run() -> dict:
    data = export_tei.load_dataset()
    records = {r["sourcePageId"]: r for r in export_tei.exported_pages(data)}
    raw = export_tei.serialize(export_tei.build())
    OUT_XML.parent.mkdir(parents=True, exist_ok=True)
    OUT_XML.write_bytes(raw)
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
        return {"checks": [c.d]}
    checks.append(c.d)
    checks.append(
        _schema_check(
            "tei-all",
            "The export is valid TEI",
            "The export validates against tei_all of TEI P5 4.12.0.",
            _tei_all(),
            doc,
        )
    )

    c = Check(
        "deterministic",
        "D1",
        "The export is reproducible",
        "Two runs over the same data give the same bytes.",
    )
    c.ok() if export_tei.serialize(export_tei.build()) == raw else c.fail(
        None, "two builds differ"
    )
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
    first = header.find(f".//{T}title")
    c.ok() if first is not None and first.text == "Klawiter-Bibliographie Stefan Zweig digital" else c.fail(
        None, f"first title is {first.text if first is not None else None!r}"
    )
    wiki_in_header = header.findall(f".//{T}bibl[@type='wikiPage']")
    c.ok() if not wiki_in_header else c.fail(
        None, f"{len(wiki_in_header)} source entries in the header"
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
        "The text of every source entry in the TEI equals the entry text of the canonical data, character for character.",
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
            int(sid.split("-")[2]), f"{sid} is pointed to by no value"
        )
    checks.append(c.d)

    # Publications: one biblStruct per publication of an edition page, none for other kinds.
    describes: dict[int, list[str]] = {}
    for rel in doc.iterfind(f".//{T}relation[@name='describes']"):
        describes.setdefault(int(rel.get("active").split("-")[-1]), []).append(
            rel.get("passive")[1:]
        )
    structs = {s.get(XML_ID): s for s in doc.iterfind(f".//{T}body//{T}biblStruct")}
    c = Check(
        "publications",
        "D1",
        "Each publication is its own record",
        "An edition page gives one biblStruct per publication of its publication layer, or one when it has none; no other page kind gives a biblStruct.",
    )
    for page, rec in records.items():
        got = len(describes.get(page, []))
        if rec["wikiPageKind"] == export_tei.PUBLICATION_KIND:
            want = len(export_tei.load_layer(page)) or 1
        else:
            want = 0
        c.ok() if got == want else c.fail(
            page, f"{rec['wikiPageKind']}: {got} biblStruct, expected {want}"
        )
    checks.append(c.d)

    # Values: recomputed from the canonical data, then looked up in the export.
    c_val = Check(
        "values",
        "D1",
        "Every exported value arrives unchanged",
        "Title, people, places, publisher, date, language and extent of each publication appear in its biblStruct exactly as in the canonical data.",
    )
    c_resp = Check(
        "producers",
        "D1",
        "Every value names its producer",
        "@resp of each value is the application of the producer class the canonical data records for it.",
    )
    c_state = Check(
        "states",
        "D1",
        "Every value carries its review state",
        "@ana of each value is its state in the canonical data: the review state where one is recorded, not-reviewed otherwise.",
    )
    c_src = Check(
        "passages",
        "D1",
        "Every located value points to its passage",
        "A value whose evidence locates a passage points to it, and the passage is the text at those offsets.",
    )
    app = {
        v: f"#{k}"
        for k, v in {
            "app-rules": "regex",
            "app-llm": "llm",
            "app-derivation": "derived",
        }.items()
    }
    values = Counter()
    for page, rec in records.items():
        if rec["wikiPageKind"] != export_tei.PUBLICATION_KIND:
            continue
        layer = export_tei.load_layer(page)
        states = (rec.get("review") or {}).get("fieldStates") or {}
        expected = []  # (pub index, tag, text, producer, state, evidence)
        if layer:
            for i, pub in enumerate(layer, 1):
                prov, spans = pub.get("provenance") or {}, pub.get("valueSpans") or {}

                def exp(
                    tag,
                    field,
                    text,
                    ev=None,
                    sf=None,
                    i=i,
                    prov=prov,
                    spans=spans,
                    pub=pub,
                ):
                    sf = sf or field
                    st = (
                        states[sf]
                        if sf in states and str(rec.get(sf, "")) == text
                        else "not-reviewed"
                    )
                    expected.append(
                        (
                            i,
                            tag,
                            text,
                            prov.get(field, "undeclared"),
                            st,
                            spans.get(field, []) if ev is None else ev,
                        )
                    )

                if pub.get("title"):
                    exp("title", "title", pub["title"])
                for cr in pub.get("credits") or []:
                    exp(
                        "persName",
                        "credits",
                        cr.get("name", ""),
                        [
                            s
                            for s in spans.get("credits", [])
                            if s.get("part") == "name"
                            and s.get("value") == cr.get("name")
                        ],
                    )
                for pl in pub.get("places") or []:
                    exp(
                        "pubPlace",
                        "places",
                        pl,
                        [s for s in spans.get("places", []) if s.get("value") == pl],
                        "location",
                    )
                if pub.get("publisher"):
                    exp("publisher", "publisher", pub["publisher"])
                if pub.get("year"):
                    exp("date", "yearRaw", str(pub.get("yearRaw") or pub["year"]))
        else:
            prov, evid = rec.get("_provenance") or {}, rec.get("fieldEvidence") or {}
            for tag, field in (
                ("title", "title"),
                ("persName", "translator"),
                ("pubPlace", "location"),
                ("publisher", "publisher"),
                ("date", "year"),
                ("measure", "pageCount"),
            ):
                if rec.get(field):
                    expected.append(
                        (
                            1,
                            tag,
                            str(rec[field]),
                            prov.get(field, "undeclared"),
                            states.get(field, "not-reviewed"),
                            evid.get(field, []),
                        )
                    )
        for i, tag, text, producer, state, ev in expected:
            values["total"] += 1
            struct = structs.get(f"SZDKLA.{page}.{i}")
            cands = [
                el
                for el in (struct.iter(f"{T}{tag}") if struct is not None else [])
                if el.text == text
            ]
            if not cands:
                c_val.fail(page, f"{tag} {text!r} missing from SZDKLA.{page}.{i}")
                continue
            c_val.ok()
            el = cands[0]
            # No default: a producer class the export does not declare is a fault, not a rule.
            want_resp = app.get(producer, f"undeclared producer {producer!r}")
            c_resp.ok() if el.get("resp") == want_resp else c_resp.fail(
                page, f"{tag} {text!r}: resp {el.get('resp')}, expected {want_resp}"
            )
            c_state.ok() if el.get("ana") == f"#{state}" else c_state.fail(
                page, f"{tag} {text!r}: ana {el.get('ana')}, expected #{state}"
            )
            span = next(
                (
                    (e["textStart"], e["textEnd"])
                    for e in ev
                    if isinstance(e.get("textStart"), int)
                    and isinstance(e.get("textEnd"), int)
                ),
                None,
            )
            src = el.get("source")
            if span is None:
                gaps = {e.get("gap") for e in ev}
                if src and ("page-title" in gaps or "category-markup" in gaps):
                    values["withMetaSource"] += 1
                else:
                    values[next((g for g in gaps if g), "no-evidence")] += 1
                continue
            m = RANGE.fullmatch(src or "")
            if m:
                got = (int(m.group(2)), int(m.group(2)) + int(m.group(3)))
                values["byRange"] += 1
            elif src and src[1:] in seg_pos:
                got = seg_pos[src[1:]][:2]
            else:
                c_src.fail(page, f"{tag} {text!r} has no passage, evidence {span}")
                continue
            if got != span:
                c_src.fail(page, f"{tag} {text!r} points to {got}, evidence {span}")
                continue
            c_src.ok()
            values["withPassage"] += 1
            if (rec.get("fullBibliographicEntry") or "")[span[0] : span[1]] != text:
                values["textDiffers"] += 1
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

    profile = Check(
        "profile-schema",
        "D1",
        "Profile schema admits only the profile",
        "The RELAX NG profile schema follows the export's structure and rejects what TEI admits but the profile does not.",
    )
    profile.d.update(
        status="open",
        note="The profile schema still describes the first export; it is rewritten with the mutation suite.",
    )
    checks.append(profile.d)
    for cid, ms, title, proves in OPEN_CHECKS:
        if cid == "profile-schema":
            continue
        k = Check(cid, ms, title, proves)
        k.d["status"] = "open"
        checks.append(k.d)

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
        "coverage": coverage,
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
        "acceptance": [
            {
                **a,
                "question": a["question"].replace("__N__", str(_unclassified(records))),
            }
            for a in ACCEPTANCE
        ],
    }


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
