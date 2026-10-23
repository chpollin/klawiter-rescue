"""Probe 3, entry signatures: how many objects does a unit describe?

Takes the consensus units of _segment.py and computes a form profile per unit:
imprints ("Place: Publisher, 1931"), periodical citations ("25:1 (1992)",
"21 Apr. 1912"), host references ("in Romans et Nouvelles [BA1 5]"), extent
with year for volumes whose imprint stands in a collection header, numbered sub-items ("[2]."), a Contents list, markers such as
Tr., Rep:, REV:, EXC: and FAC, and bracketed sigla ([PF], [RJS]). From the
profile each unit falls into one class:

- reference: a stub (****, *) or a short unit whose only content is a See
- single: exactly one citation and fewer than two sub-items
- multi: several citations or at least two sub-items
- note: neither citation nor reference, such as a commentary paragraph

The classes are a measurement aid, not a data model; they show per section how
often the entry and the described publication coincide, which decides the
record model of the parse stage.

Output: data/print/derived/reports/probe_signatures.json and a summary.

Usage: python -m uv run python pipeline/print_volumes/probe_signatures.py
"""

import re
import sys
from collections import Counter, defaultdict

from _common import VOLUMES, load_lines, write_report
from _lines import STUB, annotate
from _segment import body_by_part, units, votes

IMPRINT = re.compile(
    r"(?<![\w-])[A-Z][\w.'’/ -]{1,40}: [^.;:\[\]]{2,60}?, [\[(]?(1[5-9]|20)\d\d"
)
MONTH = r"(?:Jan|Feb|Mar|Apr|May|June?|July?|Aug|Sept?|Oct|Nov|Dec)[a-z]*\.?"
PERIODICAL = re.compile(
    rf"\d{{1,3}}:\d{{1,3}}[a-z]? \(|\b\d{{1,2}}\.? {MONTH} (1[89]|20)\d\d\b"
)
# A contribution citing its host volume by address: "in Romans et Nouvelles [BA1 5]".
HOST = re.compile(r"\bin\b[^\[]{2,120}\[[A-R](?:A[12])? ?\d{1,4}")
# A volume whose imprint stands once in a collection header: "757/(3)p. 1983."
EXTENT_YEAR = re.compile(r"\d+(?:/\(?\d+\)?)?p\. \[?(1[5-9]|20)\d\d\b")
SUBITEM = re.compile(r"\[\d{1,2}\]\.")
SIGLUM = re.compile(r"\[([A-Z][A-Za-z]{1,4})\]")
MARKERS = {
    "Tr.": re.compile(r"\bTr\."),
    "Rep:": re.compile(r"\b(?:Rep|REP):"),
    "REV:": re.compile(r"\bREV:"),
    "EXC": re.compile(r"\bEXC\b"),
    "FAC": re.compile(r"\bFAC\b"),
    "Contents:": re.compile(r"\bContents:"),
    "See": re.compile(r"\bSee\b"),
    "Frw.": re.compile(r"\bFrw\."),
    "Aftw.": re.compile(r"\bAftw\."),
    "Tsd.": re.compile(r"\bTsd\."),
}


def _profile(text: str) -> dict:
    return {
        "imprints": len(IMPRINT.findall(text)),
        "periodicals": len(PERIODICAL.findall(text)),
        "hosts": len(HOST.findall(text)),
        "extent_years": len(EXTENT_YEAR.findall(text)),
        "subitems": len(SUBITEM.findall(text)),
        "markers": [m for m, rx in MARKERS.items() if rx.search(text)],
        "sigla": SIGLUM.findall(text),
    }


def _classify(text: str, profile: dict) -> str:
    citations = sum(
        profile[k] for k in ("imprints", "periodicals", "hosts", "extent_years")
    )
    if STUB.match(text) or (
        citations == 0 and "See" in profile["markers"] and len(text) < 200
    ):
        return "reference"
    if profile["subitems"] >= 2 or citations >= 2:
        return "multi"
    if citations == 1:
        return "single"
    return "note"


def main() -> int:
    report: dict = {}
    for volume in VOLUMES:
        lines = annotate(load_lines(volume), volume)
        classes: dict[str, Counter] = defaultdict(Counter)
        markers: Counter = Counter()
        sigla: Counter = Counter()
        examples: dict[str, list] = defaultdict(list)
        headings = 0
        citation_types: Counter = Counter()
        for part, body in body_by_part(lines).items():
            votes(body)
            for unit in units(body):
                if unit[0]["heading"] and len(unit) == 1:
                    headings += 1
                    continue
                text = " ".join(ln["text"].strip() for ln in unit)
                profile = _profile(text)
                kind = _classify(text, profile)
                classes[part][kind] += 1
                markers.update(profile["markers"])
                for key in ("imprints", "periodicals", "hosts", "extent_years"):
                    citation_types[key] += bool(profile[key])
                sigla.update(profile["sigla"])
                if len(examples[kind]) < 3 and unit[0]["page"] % 7 == 0:
                    examples[kind].append(f"p{unit[0]['page']}: {text[:140]}")
        total = Counter()
        for counter in classes.values():
            total.update(counter)
        report[volume] = {
            "headings": headings,
            "classes": dict(total),
            "classes_by_section": {p: dict(c) for p, c in classes.items()},
            "markers": dict(markers.most_common()),
            "units_with_citation_type": dict(citation_types),
            "sigla_top": dict(sigla.most_common(40)),
            "examples": dict(examples),
        }
    path = write_report("probe_signatures", report)

    print("=" * 72)
    for volume, data in report.items():
        n = sum(data["classes"].values())
        shares = " ".join(
            f"{k}={v} ({v / n:.0%})" for k, v in sorted(data["classes"].items())
        )
        print(f"{volume}: {n} units, {data['headings']} headings | {shares}")
        for part, c in sorted(data["classes_by_section"].items()):
            m = sum(c.values())
            row = " ".join(f"{k}={v / m:.0%}" for k, v in sorted(c.items()))
            print(f"  {part:>3} n={m:>5}  {row}")
        print(f"  citation types: {data['units_with_citation_type']}")
        print(f"  markers: {data['markers']}")
        print(f"  sigla: {list(data['sigla_top'].items())[:20]}")
    print(f"OK report {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
