"""p07b: overlap of print and wiki as the concordance proposes it, per volume and section.

Reads the p03 records, the p07 claims and the published wiki layer
(docs/data/klawiter.json, docs/data/publications/) and counts, per volume and
part, the print objects by the strongest route a claim reaches them on:

- text: the object's entry is aligned near-verbatim with a wiki page
  (textAlignedWith);
- field: a claim on title, year and a second field, split by the relation it
  states (samePublicationAs, containedIn, contains);
- title-year: only a title-year block (candidateFor);
- none: no claim.

Objects p07 never matches are counted apart: cross-reference objects and
collection headers without address. On the wiki side it counts the
publications and main-namespace pages that no claim names, and those named
only by a title-year block.

Every count is of claims in the state "proposed". A candidate is no
confirmed identity or containment: the figures say what the concordance
proposes, not what exists in both sources; only the human round measures how
often a proposal holds (knowledge/print-wiki-merge.md, Measurement). The
report holds counts and identifiers only, no print text.

Output: data/print/derived/reports/p07b_overlap.json.

Usage: python -m uv run python pipeline/print_volumes/p07b_overlap.py
"""

import json
import sys
from collections import Counter, defaultdict

from _common import DERIVED_DIR, PROJECT_ROOT, VOLUMES, write_report

RECORDS = DERIVED_DIR / "records"
CLAIMS = DERIVED_DIR / "claims" / "concordance.jsonl"
KLAWITER = PROJECT_ROOT / "docs" / "data" / "klawiter.json"
PUBLICATIONS = PROJECT_ROOT / "docs" / "data" / "publications"
FIELD = ("samePublicationAs", "containedIn", "contains")
# Strongest first; an object counts once, under the first route it reaches.
ORDER = ("text", *(f"field:{p}" for p in FIELD), "title-year", "none")


def _route(predicates: set[str], aligned: bool) -> str:
    if aligned:
        return "text"
    for predicate in FIELD:
        if predicate in predicates:
            return f"field:{predicate}"
    return "title-year" if "candidateFor" in predicates else "none"


def _wiki_target(claim: dict) -> tuple[str | None, int | None]:
    target = claim["object"]
    page = (claim.get("evidence") or {}).get("wiki_page")
    if page is None and target.startswith("klawiter:entry/"):
        page = int(target.rsplit("/", 1)[1])
    return (target if target.startswith("klawiter:publication/") else None), page


def overlap(records, claims, publications: set[str], pages: set[int]) -> dict:
    """The report body from records, claims and the wiki identifiers."""
    by_object: dict[str, set[str]] = defaultdict(set)
    aligned: set[str] = set()
    named_pub: dict[str, set[str]] = defaultdict(set)
    named_page: dict[int, set[str]] = defaultdict(set)
    for claim in claims:
        if claim.get("state") != "proposed":
            raise ValueError(f"claim {claim['id']} is not proposed")
        predicate = claim["predicate"]
        if predicate == "textAlignedWith":
            aligned.add(claim["subject"])
        else:
            by_object[claim["subject"]].add(predicate)
        pub, page = _wiki_target(claim)
        if pub:
            named_pub[pub].add(predicate)
        if page is not None:
            named_page[page].add(predicate)
    table: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for record in records:
        for obj in record["objects"]:
            types = {t.get("value") for t in obj.get("types", [])}
            if record["kind"] == "reference":
                route = "not matched: cross-reference"
            elif "collection" in types and not obj.get("address"):
                route = "not matched: collection header"
            else:
                route = _route(by_object.get(obj["id"], set()), record["id"] in aligned)
            table[record["volume"]][record["part"]][route] += 1

    def side(named: dict, universe: set) -> dict:
        counts = Counter()
        for key in universe:
            predicates = named.get(key, set())
            if not predicates:
                counts["named by no claim"] += 1
            elif predicates <= {"candidateFor"}:
                counts["named only by a title-year block"] += 1
            else:
                counts["named by a text or field claim"] += 1
        return dict(sorted(counts.items()))

    rows = {}
    for volume in VOLUMES:
        rows[volume] = {}
        for part, counts in sorted(table[volume].items()):
            rows[volume][part] = [
                {"route": route, "state": "proposed", "objects": counts[route]}
                for route in (*ORDER, *sorted(set(counts) - set(ORDER)))
                if counts[route]
            ]
    totals = {
        volume: dict(sum((table[volume][p] for p in table[volume]), Counter()))
        for volume in VOLUMES
    }
    return {
        "print": rows,
        "print_totals": totals,
        "wiki": {
            "publications": {"all": len(publications), **side(named_pub, publications)},
            "pages": {"all": len(pages), **side(named_page, pages)},
        },
    }


def _jsonl(path):
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def main() -> int:
    for path in (CLAIMS, KLAWITER, PUBLICATIONS):
        if not path.exists():
            sys.exit(f"FEHLER: {path} missing; run p07 and the production pipeline")
    records = [r for v in VOLUMES for r in _jsonl(RECORDS / f"entries-{v}.jsonl")]
    publications = {
        pub["id"]
        for path in sorted(PUBLICATIONS.glob("*.json"))
        for pub in json.loads(path.read_text("utf-8")).get("publications", [])
        if pub.get("id")
    }
    pages = {
        int(e["sourcePageId"])
        for e in json.loads(KLAWITER.read_text("utf-8"))["entries"]
        if e.get("pageNamespace", 0) == 0 and e.get("sourcePageId") is not None
    }
    body = overlap(records, _jsonl(CLAIMS), publications, pages)
    report = {
        "about": "Overlap of print and wiki as the p07 concordance proposes it. Print "
        "objects per volume and part by the strongest route a claim reaches them on "
        "(text alignment, a field claim by the relation it states, a title-year block "
        "only, none); wiki publications and main-namespace pages by whether a claim "
        "names them. Every claim counted is proposed: a candidate is no confirmed "
        "identity or containment, and only the human round measures how often one "
        "holds. Counts and identifiers only, no print text.",
        **body,
    }
    path = write_report("p07b_overlap", report)
    for volume, counts in body["print_totals"].items():
        print(
            f"OK {volume}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
        )
    print(f"OK wiki {body['wiki']}")
    print(f"OK report {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
