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

import sys
from collections import Counter, defaultdict

from _common import VOLUMES, load_lines, write_report
from _lines import annotate
from _objects import citation_profile, classify_unit, unit_text
from _segment import body_by_part, units, votes


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
                text = unit_text(unit)
                profile = citation_profile(text)
                kind = classify_unit(text, profile)
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
