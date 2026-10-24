"""p12: the print objects as JSON-LD with a provenance chain per value, validated, plus the viewer data.

Every value of a p03 object becomes a node of type kp:Value that names its
literal (rdf:value), the field it fills, its producer (rule, llm, compiler,
inherited), the rule or prompt that produced it (a prov:Plan), and a W3C text
position selector (oa:TextPositionSelector with start, end and the exact
passage) into its source record (oa:hasSource). The record carries its text,
hash, PDF page and line and derives from its source file (prov:wasDerivedFrom),
whose name and hash prefix come from sections.json. The chain therefore runs
value -> passage -> record -> PDF file, and for inherited values through the
heading or header they were read from. The context is
schema/print-context.jsonld, the shapes schema/print-shapes.ttl.

The documents are written in chunks of at most CHUNK records per volume and
part, each self-contained (context inline, the records its values quote and
the plans they name). The apparatus records of _apparatus.py (index entries,
front matter and tail passages) are exported the same way, each with one
kp:ApparatusItem in place of the print objects. Every chunk is validated on
four levels:

1. terms: every key used is defined in the context, so no statement is dropped
   silently on expansion;
2. RDF: the document parses as JSON-LD into a graph, and the graph holds one
   kp:PrintObject or kp:ApparatusItem per object and one kp:Value per value of
   the records;
3. SHACL: the shapes hold, including the SPARQL constraint that every selector
   quotes its source record exactly and every text value equals its passage;
4. exits non-zero on any failure.

The viewer (viewer/ beside this module, no print text) is copied next to the
data with an index of all objects; both stay local under data/print/derived/
(rights unresolved).

Output: data/print/derived/jsonld/<volume>/<part>-<n>.jsonld,
data/print/derived/viewer/ (index.json and the viewer files),
data/print/derived/reports/p12_jsonld.json.

Usage: python -m uv run python pipeline/print_volumes/p12_jsonld.py [--no-shacl]
"""

import argparse
import json
import re
import shutil
import sys
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from _apparatus import slug
from _common import DERIVED_DIR, HERE, SECTIONS, VOLUMES, write_report
from _fields import summary
from _heldout import review_objects
from _review import MISSING_FIELDS, check, effective, load_log
from _schema import BASE_KEYS, LANGUAGES, OBJECT_TYPES, ROLES, object_values

RECORDS = DERIVED_DIR / "records"
OUT = DERIVED_DIR / "jsonld"
VIEWER_SRC = HERE / "viewer"
VIEWER = DERIVED_DIR / "viewer"
CONTEXT_FILE = HERE / "schema" / "print-context.jsonld"
SHAPES_FILE = HERE / "schema" / "print-shapes.ttl"
CHUNK = 250
CLASSES = {
    "persons": "kp:Person",
    "imprints": "kp:Imprint",
    "extent": "kp:Extent",
    "parts": "kp:ExtentPart",
    "edition_notes": "kp:EditionNote",
    "series": "kp:Series",
    "periodicals": "kp:PeriodicalCitation",
    "hosts": "kp:Citation",
    "reviewed": "kp:Citation",
    "event": "kp:Event",
    "contents": "kp:ContentItem",
    "holdings": "kp:Holding",
    "references": "kp:Reference",
    "work_refs": "kp:Address",
    "address": "kp:Address",
    "targets": "kp:AddressTarget",
    "relation": "kp:Relation",
    "inherited": "kp:Inherited",
}
DERIVED = re.compile(r"(?:roles|types)\[\d+\]$|(?:^|\.)(?:kind|language)$")
RECORD_CLASS = {
    "entry": "kp:Entry",
    "heading": "kp:Heading",
    "reference": "kp:CrossReference",
    "index": "kp:IndexEntry",
    "front": "kp:FrontMatterPassage",
    "tail": "kp:TailPassage",
}
OBJECT_CLASSES = ("PrintObject", "ApparatusItem")


def _plan_producer(rule: str) -> str:
    if rule.startswith("llm:"):
        return "llm"
    return "compiler" if rule.startswith("p06.") else "rule"


STATE = {"confirm": "confirmed", "correct": "corrected", "unresolved": "contested"}


class Exporter:
    def __init__(self, texts: dict[str, dict], reviews: dict[str, list] | None = None):
        self.records = texts
        self.values = 0
        self.sources: set[str] = set()
        self.plans: set[str] = set()
        # Decisions in force per object id, as (key, decision) pairs.
        self.reviews = reviews or {}
        self.decisions: list = []
        self.by_path: dict[str, object] = {}

    def value(self, v: dict, path: str, entry: str) -> dict:
        source = v.get("from") or entry
        a, b = v["span"]
        self.values += 1
        self.sources.add(source)
        self.plans.add(v["rule"])
        # Text and years equal their passage; roles, types, kinds, languages
        # and flags are derived from it (p10 checks each derivation).
        derived = isinstance(v["value"], bool) or (
            isinstance(v["value"], str) and DERIVED.search(path) is not None
        )
        node = {
            "type": ["kp:Value", "kp:DerivedValue" if derived else "kp:VerbatimValue"],
            "value": v["value"],
            "field": path,
            "producer": v["by"],
            "rule": f"rule/{v['rule']}",
            "source": source,
            "selector": {
                "type": "oa:TextPositionSelector",
                "start": a,
                "end": b,
                "exact": self.records[source]["text"][a:b],
            },
        }
        if v.get("state"):
            node["state"] = v["state"]
        decision = self.by_path.get(path)
        if decision is not None:
            node["reviewState"] = STATE[decision.decision]
            node["review"] = f"review/{decision.id}"
        return node

    def convert(self, node, path: str, entry: str, key: str = ""):
        if isinstance(node, dict):
            if "span" in node and "by" in node:
                return self.value(node, path, entry)
            out = {}
            if key in CLASSES:
                out["type"] = CLASSES[key]
            for k, child in node.items():
                if k == "record" and child:
                    out["record"] = child
                elif k == "target" and isinstance(child, str):
                    out["target"] = child
                elif isinstance(child, (dict, list)):
                    name = "note_text" if k == "text" else k
                    out[name] = self.convert(child, f"{path}.{k}", entry, k)
                elif child is not None:
                    out[k] = child
            return out
        if isinstance(node, list):
            return [
                self.convert(c, f"{path}[{i}]", entry, key) for i, c in enumerate(node)
            ]
        return node

    def obj(self, obj: dict) -> dict:
        s, e = obj["span"]
        out = {
            "id": obj["id"],
            "type": "kp:ApparatusItem" if "kind" in obj else "kp:PrintObject",
            "entry": obj["entry"],
            "volume": obj["volume"],
            "part": obj["part"],
            "address": obj["address"],
            "objectText": obj["text"],
            **({"kind": obj["kind"]} if "kind" in obj else {}),
            "selector": {
                "type": "oa:TextPositionSelector",
                "start": s,
                "end": e,
                "exact": obj["text"],
            },
        }
        self.sources.add(obj["entry"])
        decisions = self.reviews.get(obj["id"], [])
        self.by_path = {k[2]: d for k, d in decisions if k[1] == "value"}
        for key, child in obj.items():
            if key not in BASE_KEYS and child not in (None, [], {}):
                out[key] = self.convert(child, key, obj["entry"], key)
        own = [d for k, d in decisions if k[1] != "value"]
        if own:
            out["reviews"] = [f"review/{d.id}" for d in own]
        self.decisions.extend(d for _, d in decisions)
        return out

    def decision_nodes(self) -> list[dict]:
        """One prov:Activity per decision in force, with its reviewer as prov:Agent."""
        nodes, agents = [], {}
        for d in self.decisions:
            agent = "reviewer/" + re.sub(r"[^a-z0-9]+", "-", d.reviewer.lower()).strip(
                "-"
            )
            agents[agent] = d.reviewer
            node = {
                "id": f"review/{d.id}",
                "type": ["kp:ReviewDecision", "prov:Activity"],
                "decision": d.decision,
                "about": d.object,
                "wasAssociatedWith": agent,
                "endedAtTime": d.at,
            }
            if d.target:
                node["targetField"] = d.target.path
            if d.note:
                node["reviewNote"] = d.note
            if d.correction:
                correction = {
                    "type": "kp:Correction",
                    "field": d.correction.field or d.target.path,
                }
                if d.correction.span:
                    a, b = d.correction.span
                    entry = d.object.split("#")[0]
                    correction.update(
                        value=d.correction.value,
                        source=entry,
                        selector={
                            "type": "oa:TextPositionSelector",
                            "start": a,
                            "end": b,
                            "exact": self.records[entry]["text"][a:b],
                        },
                    )
                node["correction"] = correction
            nodes.append(node)
        nodes.extend(
            {"id": a, "type": "prov:Agent", "label": label}
            for a, label in sorted(agents.items())
        )
        return nodes


def record_node(r: dict) -> dict:
    node = {
        "id": r["id"],
        "type": ["kp:Record", RECORD_CLASS[r["kind"]]],
        "volume": r["volume"],
        "part": r["part"],
        "kind": r["kind"],
        "address": r["address"],
        "pdfPage": r["page"],
        "pdfPageEnd": r["page_end"],
        "line": r["line"],
        "text": r["text"],
        "sha256": r["sha256"],
        "context": r["context"],
        "derivedFrom": f"file/{r['volume']}",
    }
    if "column" in r:
        node["column"] = r["column"]
    return node


def file_nodes() -> list[dict]:
    return [
        {
            "id": f"file/{volume}",
            "type": "kp:SourceFile",
            "fileName": spec["file"],
            "sha256Prefix": spec["sha256"],
        }
        for volume, spec in SECTIONS["volumes"].items()
    ]


def plan_nodes(rules: set[str], models: dict[str, str]) -> list[dict]:
    nodes = []
    for rule in sorted(rules):
        node = {
            "id": f"rule/{rule}",
            "type": "prov:Plan",
            "label": rule,
            "producer": _plan_producer(rule),
        }
        if rule in models:
            node["llm_model"] = models[rule]
        nodes.append(node)
    return nodes


def _fold(text: str) -> str:
    text = (
        text.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def _keys(node, found: set[str]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if not k.startswith("@"):
                found.add(k)
            _keys(v, found)
    elif isinstance(node, list):
        for v in node:
            _keys(v, found)


def _llm_models() -> dict[str, str]:
    from _llm import PROMPT_ID, load_cache

    models = {
        e.get("model")
        for e in load_cache().get("entries", {}).values()
        if e.get("model")
    }
    return {f"llm:{PROMPT_ID}": ", ".join(sorted(models))} if models else {}


def build() -> tuple[list[dict], list[dict]]:
    """Write all chunks; return the chunk descriptors and the viewer index."""
    context = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))["@context"]
    models = _llm_models()
    records: dict[str, dict] = {}
    by_volume: dict[str, list[dict]] = {}
    for volume in VOLUMES:
        by_volume[volume] = []
        # The apparatus records (indexes, front matter, tail) follow the entries.
        for name in ("entries", "apparatus"):
            with (RECORDS / f"{name}-{volume}.jsonl").open(encoding="utf-8") as source:
                by_volume[volume].extend(json.loads(line) for line in source)
        records.update({r["id"]: r for r in by_volume[volume]})
    reviews: dict[str, list] = {}
    stale = 0
    for key, d in effective(load_log()).items():
        if check(d, records) is None:
            reviews.setdefault(d.object, []).append((key, d))
        else:
            stale += 1
    sample = set(review_objects())
    if OUT.exists():
        shutil.rmtree(OUT)
    chunks, index = [], []
    for volume, recs in by_volume.items():
        parts: dict[str, list[dict]] = {}
        for r in recs:
            parts.setdefault(
                slug(r["part"]) if "column" in r else r["part"], []
            ).append(r)
        for part, items in parts.items():
            for n in range(0, len(items), CHUNK):
                batch = items[n : n + CHUNK]
                exporter = Exporter(records, reviews)
                objects = [exporter.obj(o) for r in batch for o in r["objects"]]
                exporter.sources.update(r["id"] for r in batch)
                graph = (
                    file_nodes()
                    + plan_nodes(exporter.plans, models)
                    + [record_node(records[i]) for i in sorted(exporter.sources)]
                    + objects
                    + exporter.decision_nodes()
                )
                path = OUT / volume / f"{part}-{n // CHUNK + 1}.jsonld"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(
                        {"@context": context, "@graph": graph}, ensure_ascii=False
                    ),
                    encoding="utf-8",
                )
                rel = path.relative_to(DERIVED_DIR).as_posix()
                chunks.append(
                    {
                        "path": str(path),
                        "objects": len(objects),
                        "values": exporter.values,
                        "decisions": len(exporter.decisions),
                    }
                )
                for r in batch:
                    for o in r["objects"]:
                        s = summary(o)
                        # Only a read title or term is a title; otherwise the
                        # viewer shows the start of the text, marked as such.
                        label = (
                            o["term"]["value"] if o.get("term") else s["title"] or ""
                        )
                        index.append(
                            {
                                "id": o["id"],
                                "entry": r["id"],
                                "volume": volume,
                                "part": part,
                                "address": r["address"],
                                "page": r["page"],
                                "title": label,
                                "snippet": "" if label else o["text"][:120],
                                "types": [o["kind"]]
                                if "kind" in o
                                else [t["value"] for t in o.get("types", [])],
                                "producers": sorted(
                                    {v["by"] for _, v in object_values(o)}
                                ),
                                "chunk": "../" + rel,
                                "review": o["id"] in sample,
                                "search": _fold(
                                    " ".join((o["id"], r["address"], label, o["text"]))
                                ),
                            }
                        )
    return chunks, index, stale


def validate_chunk(args: tuple[str, int, int, bool]) -> dict:
    path, n_objects, n_values, shacl = args
    import rdflib
    from rdflib.namespace import RDF

    text = Path(path).read_text(encoding="utf-8")
    doc = json.loads(text)
    result = {"path": path, "problems": []}
    used: set[str] = set()
    _keys(doc["@graph"], used)
    undefined = sorted(used - set(doc["@context"]))
    if undefined:
        result["problems"].append(f"undefined terms {undefined}")
    graph = rdflib.Graph()
    graph.parse(data=text, format="json-ld")
    kp = rdflib.Namespace("https://chpollin.github.io/klawiter-rescue/vocab/print/")
    objects = sum(
        len(set(graph.subjects(RDF.type, kp[name]))) for name in OBJECT_CLASSES
    )
    values = len(set(graph.subjects(RDF.type, kp.Value)))
    result["triples"] = len(graph)
    if objects != n_objects or values != n_values:
        result["problems"].append(
            f"graph holds {objects} objects and {values} values, records {n_objects} and {n_values}"
        )
    if shacl:
        import pyshacl

        shapes = rdflib.Graph().parse(SHAPES_FILE, format="turtle")
        conforms, _, report = pyshacl.validate(graph, shacl_graph=shapes, advanced=True)
        if not conforms:
            result["problems"].append("SHACL: " + report[:2000])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-shacl", action="store_true")
    args = parser.parse_args()
    chunks, index, stale = build()
    print(
        f"OK {len(chunks)} chunks, {sum(c['objects'] for c in chunks)} objects, "
        f"{sum(c['values'] for c in chunks)} values"
    )
    jobs = [(c["path"], c["objects"], c["values"], not args.no_shacl) for c in chunks]
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(validate_chunk, jobs))
    failed = [r for r in results if r["problems"]]
    # Empty the folder rather than remove it: on Windows a shell or editor
    # standing in it locks the folder itself, not its files.
    VIEWER.mkdir(parents=True, exist_ok=True)
    for child in VIEWER.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    shutil.copytree(VIEWER_SRC, VIEWER, dirs_exist_ok=True)
    (VIEWER / "index.json").write_text(
        json.dumps(index, ensure_ascii=False), encoding="utf-8"
    )
    (VIEWER / "vocab.json").write_text(
        json.dumps(
            {
                "roles": list(ROLES),
                "types": list(OBJECT_TYPES),
                "languages": list(LANGUAGES),
                "missingFields": list(MISSING_FIELDS),
            }
        ),
        encoding="utf-8",
    )
    report = {
        "about": "JSON-LD export of all print objects with one provenance chain per value, "
        "validated per chunk on terms, RDF round trip and SHACL.",
        "chunks": len(chunks),
        "objects": sum(c["objects"] for c in chunks),
        "values": sum(c["values"] for c in chunks),
        "triples": sum(r.get("triples", 0) for r in results),
        "review_decisions": sum(c["decisions"] for c in chunks),
        "review_decisions_stale": stale,
        "shacl": not args.no_shacl,
        "chunks_failed": len(failed),
        "failures": [
            {"path": Path(r["path"]).name, "problems": r["problems"]}
            for r in failed[:20]
        ],
    }
    write_report("p12_jsonld", report)
    print(f"OK {report['triples']} triples; failed chunks {len(failed)}")
    for r in failed[:5]:
        print("FEHLER", r["path"], r["problems"][0][:600])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
