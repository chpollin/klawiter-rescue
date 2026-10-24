"""p13: check the human review log against the current records and measure field correctness.

The log (data/print/review/decisions.jsonl, written by review_server.py) is
checked line by line against the strict models and the current records
(_review.py): a decision applies, or it is stale because a rebuild changed the
value it judged, or it is invalid. Correctness is measured only on the frozen
review sample (review_sample.py) and only on its objects marked complete, in
which every value carries a decision: precision is confirmed / (confirmed +
corrected) per volume, type and field, with a Wilson 95 % interval; values the
reviewer added as missing give the misses per field; unresolved values are
counted apart and enter no rate. Decisions on other objects are development
reviews, counted but never measured, because those objects were open to rule
development.

The figures measure what one or more persons accepted while seeing the rule
values; a blind annotation from the source page alone would measure more
strictly (knowledge/print-wiki-merge.md, How results are checked).

Output: data/print/derived/reports/p13_review.json.

Usage: python -m uv run python pipeline/print_volumes/p13_review.py [--log PATH]
"""

import argparse
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import _review
from _common import DERIVED_DIR, write_report
from _heldout import review_objects
from _review import check, effective, load_log, load_records, value_paths

RECORDS = DERIVED_DIR / "records"


def wilson(hits: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    z, p = 1.96, hits / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3)]


def family(path: str) -> str:
    """persons[0].roles[1] -> persons.roles"""
    return re.sub(r"\[\d+\]", "", path)


def rates(counts: dict[str, Counter]) -> dict[str, dict]:
    out = {}
    for key, c in sorted(counts.items()):
        judged = c["confirm"] + c["correct"]
        out[key] = {
            "confirmed": c["confirm"],
            "corrected": c["correct"],
            "unresolved": c["unresolved"],
            "missing": c["missing"],
            "precision": round(c["confirm"] / judged, 3) if judged else None,
            "interval95": wilson(c["confirm"], judged),
        }
    return out


def measure() -> dict:
    records = load_records(RECORDS)
    log = load_log()
    active = effective(log)
    status = {}
    for d in active.values():
        status[d.id] = check(d, records)
    current = {k: d for k, d in active.items() if status[d.id] is None}
    stale = sorted(
        (d.object, d.id, status[d.id]) for d in active.values() if status[d.id]
    )
    sample = set(review_objects())
    objects = {o["id"]: o for r in records.values() for o in r["objects"]}
    by_object: dict[str, list] = defaultdict(list)
    for key, d in current.items():
        by_object[d.object].append((key, d))
    complete, incomplete = [], []
    for oid in sorted(sample):
        decisions = by_object.get(oid, [])
        if not any(d.decision == "complete" for _, d in decisions):
            continue
        decided = {k[2] for k, _ in decisions if k[1] == "value"}
        undecided = sorted(set(value_paths(objects[oid])) - decided)
        (incomplete if undecided else complete).append((oid, undecided))
    by_field: dict[str, Counter] = defaultdict(Counter)
    by_volume: dict[str, Counter] = defaultdict(Counter)
    by_type: dict[str, Counter] = defaultdict(Counter)
    boundary = Counter()
    for oid, _ in complete:
        obj = objects[oid]
        types = [t["value"] for t in obj.get("types", [])] or ["(none)"]
        for key, d in by_object[oid]:
            if d.decision in ("confirm", "correct", "unresolved"):
                kind, field = d.decision, family(d.target.path)
            elif d.decision == "missing":
                kind, field = "missing", family(d.correction.field)
            else:
                if d.decision == "boundary":
                    boundary[obj["volume"]] += 1
                continue
            by_field[field][kind] += 1
            by_volume[obj["volume"]][kind] += 1
            for t in types:
                by_type[t][kind] += 1
    development = Counter(
        d.decision for d in current.values() if d.object not in sample
    )
    return {
        "about": "Field correctness on the frozen review sample as judged by persons in the viewer; "
        "precision = confirmed / (confirmed + corrected) with a Wilson 95 % interval, misses "
        "from values added as missing. Only complete sample objects count; reviewers saw the "
        "rule values, so this measures acceptance after inspection, not a blind annotation.",
        "log_lines": len(log),
        "decisions_in_force": len(current),
        "stale_or_invalid": [
            {"object": o, "decision": i, "reason": r} for o, i, r in stale
        ],
        "sample_objects": len(sample),
        "sample_complete": len(complete),
        "sample_complete_with_undecided_values": [
            {"object": o, "undecided": u} for o, u in incomplete
        ],
        "reviewers": sorted({d.reviewer for d in current.values()}),
        "by_volume": rates(by_volume),
        "by_type": rates(by_type),
        "by_field": rates(by_field),
        "boundary_errors_by_volume": dict(sorted(boundary.items())),
        "development_reviews": dict(sorted(development.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--log",
        type=Path,
        default=_review.LOG,
        help="decision log; another file is a trial and writes p13_review_trial",
    )
    args = parser.parse_args()
    trial = args.log.resolve() != _review.LOG.resolve()
    _review.LOG = args.log.resolve()
    try:
        report = measure()
    except ValueError as e:
        print(f"FEHLER {e}")
        return 1
    write_report("p13_review_trial" if trial else "p13_review", report)
    print(
        f"OK {report['log_lines']} log lines, {report['decisions_in_force']} decisions in force, "
        f"{len(report['stale_or_invalid'])} stale or invalid; review sample "
        f"{report['sample_complete']} of {report['sample_objects']} objects complete"
    )
    for volume, r in report["by_volume"].items():
        print(
            f"OK {volume}: precision {r['precision']} {r['interval95']}, missing {r['missing']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
