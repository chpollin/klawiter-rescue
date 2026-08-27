#!/usr/bin/env python3
"""Generate the vocabulary index, the term pages, and the JSON-LD mirror.

GitHub Pages cannot content-negotiate, so every term IRI
(…/vocab/TermName) gets its own directory with an index.html derived
from docs/vocab/klawiter.ttl; the JSON-LD mirror is serialized with
stable ordering so reruns are byte-identical. docs/vocab/index.html is
derived from the same register, grouped by the section headings of the
TTL, so a new term reaches the human-readable documentation with the
term page. The TTL is the single authoritative source; everything here
is derived and carries no run timestamp.

Usage:
    python pipeline/build_vocab_pages.py
"""

from __future__ import annotations

import html
import os
import re
import shutil
import sys
from pathlib import Path

from rdflib import DCTERMS, OWL, RDF, RDFS, Graph, URIRef

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import PROJECT_ROOT, setup_logging, write_json  # noqa: E402
from lib.vocabulary import CONTEXT  # noqa: E402

log = setup_logging(__name__)

VOCAB_DIR = Path(PROJECT_ROOT) / "docs" / "vocab"
VOCAB_NS = "https://chpollin.github.io/klawiter-rescue/vocab/"
TTL_PATH = VOCAB_DIR / "klawiter.ttl"
INDEX_PATH = VOCAB_DIR / "index.html"
UNGROUPED_SECTION = "Further terms"

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


INDEX_STYLE = """    :root {
      --burgundy: #722f37;
      --gold: #c5a55a;
      --cream: #faf6f0;
      --text: #2d2926;
      --border: #d4c5a9;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Palatino Linotype', Palatino, 'Book Antiqua', Georgia, serif;
      background: var(--cream);
      color: var(--text);
      line-height: 1.6;
      max-width: 900px;
      margin: 0 auto;
      padding: 2rem 1.5rem;
    }
    h1 { color: var(--burgundy); font-size: 1.8rem; margin-bottom: 0.5rem; }
    h2 { color: var(--burgundy); font-size: 1.3rem; margin: 2rem 0 0.8rem; border-bottom: 2px solid var(--gold); padding-bottom: 0.3rem; }
    h3 { color: var(--burgundy); font-size: 1.1rem; margin: 1.5rem 0 0.5rem; }
    p { margin-bottom: 0.8rem; }
    a { color: var(--burgundy); }
    code { background: #f0ebe3; padding: 0.15em 0.4em; border-radius: 3px; font-size: 0.9em; }
    .subtitle { color: #666; font-size: 1rem; margin-bottom: 1.5rem; }
    .namespace { background: #f0ebe3; padding: 1rem; border-left: 4px solid var(--gold); margin: 1rem 0; font-family: monospace; }
    table { width: 100%; border-collapse: collapse; margin: 0.8rem 0 1.5rem; }
    th { background: var(--burgundy); color: white; text-align: left; padding: 0.5rem 0.8rem; font-weight: normal; }
    td { padding: 0.5rem 0.8rem; border-bottom: 1px solid var(--border); vertical-align: top; }
    tr:hover td { background: #f5f0e8; }
    td code { font-size: 0.85em; }
    .kind { color: #555; font-style: italic; white-space: nowrap; }
    .tag { display: inline-block; background: var(--burgundy); color: white; font-size: 0.75rem; padding: 0.1rem 0.5rem; border-radius: 3px; margin-right: 0.3rem; }
    .tag.schema { background: #1a73e8; }
    .tag.dc { background: #e67e22; }
    .tag.domain { background: var(--burgundy); }
    footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); color: #888; font-size: 0.85rem; }"""

ALIGNMENT_NOTES = """<h2>Alignment Notes</h2>

<h3>Stefan Zweig Digital</h3>
<p>
  The <a href="https://www.stefanzweig.digital/">Stefan Zweig Digital</a> project at the Stefan Zweig Centre Salzburg (University of Salzburg)
  uses CIDOC-CRM for cultural heritage modeling. A future alignment between this vocabulary and
  CIDOC-CRM / LRMoo is planned as a separate research project to enable cross-project linked data queries.
</p>

<h3>Wikidata</h3>
<p>
  Stefan Zweig is identified as <a href="https://www.wikidata.org/entity/Q78491">Q78491</a> in Wikidata.
  Publication places, translators, and publishers are reconciled against Wikidata under Gate 2; only a
  decided and evidenced match becomes a published link, a disputed one stays a
  <a href="ContestedClaim/"><code>klawiter:ContestedClaim</code></a>.
</p>"""

SECTION_HEADING = re.compile(r"^#\s{2,}(\S.*?)\s*$")
TERM_LINE = re.compile(r"^klawiter:(\w+)\b")


def case_collisions(names) -> list:
    """Term names that share a directory on a case-insensitive filesystem.

    Term pages are directories, so klawiter:ReviewAction and
    klawiter:reviewAction resolve to one directory on Windows and macOS and
    to two on the Linux host serving the site. A collision therefore
    publishes one term page under the other term's IRI; it is reported, and
    resolving it is a vocabulary decision, not a generator fix.
    """
    by_lowercase: dict[str, list[str]] = {}
    for name in sorted(names):
        by_lowercase.setdefault(name.lower(), []).append(name)
    return [group for group in by_lowercase.values() if len(group) > 1]


def _write_if_changed(path: Path, page: str) -> None:
    if not path.exists() or path.read_text(encoding="utf-8") != page:
        path.write_text(page, encoding="utf-8", newline="\n")


def load_graph() -> Graph:
    """Parse the authoritative Turtle register."""
    graph = Graph()
    graph.parse(TTL_PATH, format="turtle")
    return graph


def collect_terms(graph: Graph) -> dict:
    """Map every term name of the namespace to kind, label, comment, links."""
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
    return terms


def term_sections(names: set) -> list:
    """Group term names by the section headings of the Turtle register.

    The TTL banner comments already carry the intended grouping, so reading
    them keeps a single source for both order and membership. Any term
    defined outside a banner section is appended in a trailing group, so the
    index never silently drops a term.
    """
    sections: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    seen: set[str] = set()
    for line in TTL_PATH.read_text(encoding="utf-8").splitlines():
        heading = SECTION_HEADING.match(line)
        if heading:
            title = heading.group(1)
            sections.append((title, []))
            current = sections[-1][1]
            continue
        term = TERM_LINE.match(line)
        if term and term.group(1) in names and term.group(1) not in seen:
            seen.add(term.group(1))
            if current is None:
                sections.append((UNGROUPED_SECTION, []))
                current = sections[-1][1]
            current.append(term.group(1))
    remaining = sorted(names - seen)
    if remaining:
        sections.append((UNGROUPED_SECTION, remaining))
    return [(title, members) for title, members in sections if members]


def _term_rows(terms: dict, names: list) -> str:
    rows = []
    for name in names:
        kind, _label, comment, _links = terms[name]
        rows.append(
            f'    <tr><td><code><a href="{html.escape(name)}/">klawiter:'
            f"{html.escape(name)}</a></code></td>"
            f'<td class="kind">{html.escape(kind)}</td>'
            f"<td>{html.escape(comment)}</td></tr>"
        )
    return "\n".join(rows)


def _context_rows() -> str:
    """Short keys of the emitted JSON-LD context that map outside klawiter:."""
    rows = []
    for key, value in CONTEXT["@context"].items():
        target = value["@id"] if isinstance(value, dict) else value
        if not isinstance(target, str) or not target.startswith(
            ("schema:", "dcterms:")
        ):
            continue
        rows.append(
            f"    <tr><td><code>{html.escape(key)}</code></td>"
            f"<td><code>{html.escape(target)}</code></td></tr>"
        )
    return "\n".join(rows)


def build_index(graph: Graph, terms: dict) -> str:
    """Render the human-readable vocabulary index from the register."""
    ontology = URIRef(VOCAB_NS)
    version = next((str(o) for o in graph.objects(ontology, OWL.versionInfo)), "")
    description = next(
        (str(o) for o in graph.objects(ontology, DCTERMS.description)), ""
    )
    blocks = []
    for title, names in term_sections(set(terms)):
        blocks.append(
            f"<h2>{html.escape(title)}</h2>\n<table>\n  <thead>\n"
            "    <tr><th>Term</th><th>Kind</th><th>Definition</th></tr>\n"
            f"  </thead>\n  <tbody>\n{_term_rows(terms, names)}\n  </tbody>\n</table>"
        )
    term_tables = "\n\n".join(blocks)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Klawiter Bibliography Vocabulary</title>
  <style>
{INDEX_STYLE}
  </style>
</head>
<body>

<h1>Klawiter Bibliography Vocabulary</h1>
<p class="subtitle">Namespace for the Stefan Zweig Bibliography (Klawiter) Linked Data project</p>

<div class="namespace">
  <strong>Namespace URI:</strong> {VOCAB_NS}<br>
  <strong>Preferred prefix:</strong> klawiter:<br>
  <strong>Version:</strong> {html.escape(version)}
</div>

<p>{html.escape(description)}</p>

<h2>Machine-readable</h2>
<p>
  This page is generated from the Turtle register, so it lists every term the
  ontology defines. Both serializations carry the same content:
</p>
<ul style="margin: 0.5rem 0 1rem 1.5rem;">
  <li><a href="klawiter.ttl">klawiter.ttl</a> &mdash; Turtle (RDFS / SKOS)</li>
  <li><a href="klawiter.vocab.jsonld">klawiter.vocab.jsonld</a> &mdash; JSON-LD</li>
</ul>
<p>Every term below is dereferenceable at <code>{VOCAB_NS}TermName/</code>.</p>

<h2>Vocabulary Design</h2>
<p>Each bibliographic entry uses multiple vocabularies via JSON-LD <code>@context</code>:</p>
<ul style="margin: 0.5rem 0 1rem 1.5rem;">
  <li><span class="tag schema">schema:</span> Standard bibliographic fields</li>
  <li><span class="tag dc">dcterms:</span> Bibliographic citation and provenance</li>
  <li><span class="tag domain">klawiter:</span> Domain types, classifications, source metadata, and gate evidence (defined below)</li>
</ul>

{term_tables}

<h2>External context keys</h2>
<p>Short keys of the emitted JSON-LD that resolve outside the <code>klawiter:</code> namespace:</p>
<table>
  <thead>
    <tr><th>Short key</th><th>Maps to</th></tr>
  </thead>
  <tbody>
{_context_rows()}
  </tbody>
</table>

{ALIGNMENT_NOTES}

<footer>
  <p>
    Part of the <a href="https://chpollin.github.io/klawiter-rescue/">Klawiter Bibliography Rescue Project</a>.
    Based on the bibliography compiled by Dr. Randolph J. Klawiter at the University of Notre Dame.
  </p>
</footer>

</body>
</html>
"""


def main() -> None:
    graph = load_graph()
    terms = collect_terms(graph)

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
        _write_if_changed(
            term_dir / "index.html", _term_page(name, kind, label, comment, links)
        )

    _write_if_changed(INDEX_PATH, build_index(graph, terms))

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

    for group in case_collisions(terms):
        log.warning(
            f"Term names differing only in case share one page directory on a "
            f"case-insensitive filesystem: {', '.join(group)}"
        )
    log.info(f"Vocabulary index and term pages written for {len(terms)} terms")


if __name__ == "__main__":
    main()
