#!/usr/bin/env python3
"""Generate dereferenceable vocabulary term pages and the JSON-LD mirror.

GitHub Pages cannot content-negotiate, so every term IRI
(…/vocab/TermName) gets its own directory with an index.html derived
from docs/vocab/klawiter.ttl; the JSON-LD mirror is serialized with
stable ordering so reruns are byte-identical. The TTL is the single
authoritative source; everything here is derived.

Usage:
    python pipeline/build_vocab_pages.py
"""

from __future__ import annotations

import html
import os
import shutil
import sys
from pathlib import Path

from rdflib import RDF, RDFS, Graph, URIRef

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import PROJECT_ROOT, setup_logging, write_json  # noqa: E402

log = setup_logging(__name__)

VOCAB_DIR = Path(PROJECT_ROOT) / "docs" / "vocab"
VOCAB_NS = "https://chpollin.github.io/klawiter-rescue/vocab/"

PREFIXES = {
    "https://schema.org/": "schema:",
    "http://purl.org/dc/terms/": "dcterms:",
    "http://www.w3.org/2004/02/skos/core#": "skos:",
    "http://www.w3.org/2000/01/rdf-schema#": "rdfs:",
    "http://www.w3.org/2001/XMLSchema#": "xsd:",
    "http://www.w3.org/ns/prov#": "prov:",
    "http://www.w3.org/ns/oa#": "oa:",
    VOCAB_NS: "klawiter:",
}


def _compact(iri: str) -> str:
    for namespace, prefix in PREFIXES.items():
        if iri.startswith(namespace):
            return prefix + iri[len(namespace) :]
    return iri


def _term_name(subject: URIRef) -> str | None:
    iri = str(subject)
    if not iri.startswith(VOCAB_NS):
        return None
    name = iri[len(VOCAB_NS) :]
    # Instance identifiers contain a slash; term names never do.
    if not name or "/" in name or "#" in name:
        return None
    return name


def _term_page(name: str, kind: str, label: str, comment: str, links: list) -> str:
    rows = "".join(
        f"<tr><th>{html.escape(pred)}</th><td>{value}</td></tr>"
        for pred, value in links
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>klawiter:{html.escape(name)}</title>
<style>
body {{ font-family: Georgia, serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; color: #222; }}
code {{ background: #f4f1ea; padding: 0.1rem 0.3rem; }}
table {{ border-collapse: collapse; margin-top: 1rem; }}
th, td {{ text-align: left; padding: 0.3rem 0.8rem 0.3rem 0; vertical-align: top; }}
th {{ font-weight: normal; color: #666; white-space: nowrap; }}
a {{ color: #7a1f1f; }}
</style>
</head>
<body>
<p><a href="../index.html">Klawiter Bibliography Vocabulary</a></p>
<h1><code>klawiter:{html.escape(name)}</code></h1>
<p><em>{html.escape(kind)}</em> — {html.escape(label)}</p>
<p>{html.escape(comment)}</p>
<table>{rows}</table>
<p>Serializations: <a href="../klawiter.ttl">Turtle</a> ·
<a href="../klawiter.vocab.jsonld">JSON-LD</a></p>
</body>
</html>
"""


def main() -> None:
    graph = Graph()
    graph.parse(VOCAB_DIR / "klawiter.ttl", format="turtle")

    terms = {}
    for subject in sorted(set(graph.subjects()), key=str):
        name = _term_name(subject)
        if name is None:
            continue
        types = sorted(str(t) for t in graph.objects(subject, RDF.type))
        kind = "Class" if any(t.endswith("Class") for t in types) else "Property"
        label = next((str(o) for o in graph.objects(subject, RDFS.label)), name)
        comment = next((str(o) for o in graph.objects(subject, RDFS.comment)), "")
        links = []
        for predicate, obj in sorted(graph.predicate_objects(subject), key=str):
            pred_c = _compact(str(predicate))
            if pred_c in ("rdfs:label", "rdfs:comment"):
                continue
            if isinstance(obj, URIRef):
                target = _compact(str(obj))
                value = f'<a href="{html.escape(str(obj))}">{html.escape(target)}</a>'
            else:
                value = html.escape(str(obj))
            links.append((pred_c, value))
        terms[name] = (kind, label, comment, links)

    # Remove stale term directories (recognizable by their generated
    # index.html), then write current ones.
    for child in VOCAB_DIR.iterdir():
        if (
            child.is_dir()
            and child.name not in terms
            and (child / "index.html").exists()
        ):
            shutil.rmtree(child)
    for name, (kind, label, comment, links) in terms.items():
        term_dir = VOCAB_DIR / name
        term_dir.mkdir(exist_ok=True)
        page = _term_page(name, kind, label, comment, links)
        path = term_dir / "index.html"
        if not path.exists() or path.read_text(encoding="utf-8") != page:
            path.write_text(page, encoding="utf-8", newline="\n")

    # Deterministic JSON-LD mirror: sorted subjects and predicates.
    nodes = []
    for subject in sorted(set(graph.subjects()), key=str):
        node = {"@id": _compact(str(subject))}
        by_pred = {}
        for predicate, obj in graph.predicate_objects(subject):
            key = "@type" if predicate == RDF.type else _compact(str(predicate))
            if isinstance(obj, URIRef):
                value = (
                    _compact(str(obj))
                    if key == "@type"
                    else {"@id": _compact(str(obj))}
                )
            else:
                value = str(obj)
            by_pred.setdefault(key, []).append(value)
        for key in sorted(by_pred):
            values = sorted(by_pred[key], key=str)
            node[key] = values[0] if len(values) == 1 else values
        nodes.append(node)
    document = {
        "@context": {
            prefix.rstrip(":"): namespace for namespace, prefix in PREFIXES.items()
        },
        "@graph": nodes,
    }
    write_json(str(VOCAB_DIR / "klawiter.vocab.jsonld"), document, indent=2)

    log.info(f"Vocabulary pages written for {len(terms)} terms")


if __name__ == "__main__":
    main()
