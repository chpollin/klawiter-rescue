"""p13: check the human review log against the current records and measure field correctness.

The log (data/print/review/decisions.jsonl, written by review_server.py) is
checked line by line against the strict models and the current records
(_review.py): a decision applies, or it is stale because a rebuild changed the
value it judged, or it is invalid. Correctness is measured only on the frozen
review sample (review_sample.py) and only on its objects marked complete, in
which every value carries a decision. Values the reviewer added as missing
give the misses per field; unresolved values are counted apart and enter no
rate. Decisions on other objects are development reviews, counted but never
measured, because those objects were open to rule development.

The measurement contract (knowledge/print-wiki-merge.md, Measurement):
- Precision per value is confirmed / (confirmed + corrected), with the Wilson
  95 % interval and, because the values of one object are not independent, a
  95 % percentile interval from resampling whole objects (bootstrap with a
  fixed seed). Precision per object is the share of judged objects without a
  corrected value, with its Wilson interval.
- Where two reviewers decided the same sample, Cohen's kappa per kind of
  decision on what both decided: on a value, confirm, correct or unresolved;
  on an object both marked complete, whether a missing value was added
  (complete states that every missing value was added, so adding none is a
  decision). A decision only one of them made does not count.
- The decision rule for automatic confirmation is read from
  confirmation_rule.json. While its threshold is unset no rule class may
  confirm; once set, a rule class (the rule that produced a value) may when the
  lower Wilson bound of its precision reaches it. The threshold is the
  operator's.

The figures measure what one or more persons accepted while seeing the rule
values; a blind annotation from the source page alone would measure more
strictly (knowledge/print-wiki-merge.md, How results are checked).

Output: data/print/derived/reports/p13_review.json.

Usage: python -m uv run python pipeline/print_volumes/p13_review.py [--log PATH]
"""

import argparse
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import _review
from _common import DERIVED_DIR, HERE, write_report
from _heldout import review_objects
from _review import check, effective, load_log, load_records, value_paths

RECORDS = DERIVED_DIR / "records"
RULE_FILE = HERE / "confirmation_rule.json"
BOOTSTRAP_SEED = 20261024
BOOTSTRAP_ROUNDS = 2000
VALUE_KINDS = ("confirm", "correct", "unresolved")


def wilson(hits: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    z, p = 1.96, hits / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3)]


def bootstrap(
    per_object: list[tuple[int, int]],
    rounds: int = BOOTSTRAP_ROUNDS,
    seed: int = BOOTSTRAP_SEED,
) -> list[float] | None:
    """95 % percentile interval of the pooled precision hits / n, resampling
    whole objects with replacement; per_object holds (hits, n) per object."""
    judged = [(h, n) for h, n in per_object if n]
    if not judged:
        return None
    rng = random.Random(seed)
    stats = []
    for _ in range(rounds):
        draw = rng.choices(judged, k=len(judged))
        stats.append(sum(h for h, _ in draw) / sum(n for _, n in draw))
    stats.sort()
    low = stats[math.floor(0.025 * (rounds - 1))]
    high = stats[math.ceil(0.975 * (rounds - 1))]
    return [round(low, 3), round(high, 3)]


def kappa(pairs: list[tuple[str, str]]) -> dict:
    """Cohen's kappa of two raters over the items both decided; None when
    chance agreement is 1 (both gave one and the same category throughout)."""
    n = len(pairs)
    if n == 0:
        return {"n": 0, "observed": None, "expected": None, "kappa": None}
    observed = sum(a == b for a, b in pairs) / n
    first, second = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(first[c] * second[c] for c in first) / (n * n)
    value = None if expected == 1 else (observed - expected) / (1 - expected)
    return {
        "n": n,
        "observed": round(observed, 3),
        "expected": round(expected, 3),
        "kappa": None if value is None else round(value, 3),
    }


def load_threshold(path: Path = RULE_FILE) -> float | None:
    """The operator's threshold, or None while unset; anything else is an error."""
    threshold = json.loads(path.read_text(encoding="utf-8")).get("threshold")
    if threshold is None:
        return None
    if type(threshold) not in (int, float) or not 0 < threshold <= 1:
        raise ValueError(f"{path}: threshold must be null or a number in (0, 1]")
    return float(threshold)


def family(path: str) -> str:
    """persons[0].roles[1] -> persons.roles"""
    return re.sub(r"\[\d+\]", "", path)


def rates(groups: dict[str, dict[str, Counter]]) -> dict[str, dict]:
    """Per group the counts and precisions; groups map an object to its counts."""
    out = {}
    for key, per_object in sorted(groups.items()):
        ordered = [per_object[o] for o in sorted(per_object)]
        c = sum(ordered, Counter())
        judged = c["confirm"] + c["correct"]
        judged_objects = [k for k in ordered if k["confirm"] + k["correct"]]
        clean = sum(1 for k in judged_objects if not k["correct"])
        out[key] = {
            "confirmed": c["confirm"],
            "corrected": c["correct"],
            "unresolved": c["unresolved"],
            "missing": c["missing"],
            "precision": round(c["confirm"] / judged, 3) if judged else None,
            "interval95": wilson(c["confirm"], judged),
            "interval95_objects_resampled": bootstrap(
                [(k["confirm"], k["confirm"] + k["correct"]) for k in ordered]
            ),
            "objects": len(ordered),
            "objects_judged": len(judged_objects),
            "objects_without_correction": clean,
            "object_precision": round(clean / len(judged_objects), 3)
            if judged_objects
            else None,
            "object_interval95": wilson(clean, len(judged_objects)),
        }
    return out


def rule_classes(by_rule: dict[str, Counter], threshold: float | None) -> dict:
    """Per rule class its precision and whether it may confirm under the rule."""
    classes = {}
    for rule, c in sorted(by_rule.items()):
        judged = c["confirm"] + c["correct"]
        interval = wilson(c["confirm"], judged)
        classes[rule] = {
            "confirmed": c["confirm"],
            "corrected": c["correct"],
            "unresolved": c["unresolved"],
            "precision": round(c["confirm"] / judged, 3) if judged else None,
            "interval95": interval,
            "may_confirm": None
            if threshold is None
            else bool(interval and interval[0] >= threshold),
        }
    return {
        "config": RULE_FILE.name,
        "threshold": threshold,
        "criterion": "lower bound of the Wilson 95 % interval of a rule class's "
        "precision on the complete objects of the frozen review sample reaches "
        "the threshold",
        "state": "unset: no rule class may confirm without a person"
        if threshold is None
        else f"set to {threshold}: only rule classes marked may_confirm may confirm",
        "may_confirm": []
        if threshold is None
        else [r for r, v in classes.items() if v["may_confirm"]],
        "by_rule": classes,
    }


def complete_objects(
    decisions: dict[tuple, object], objects: dict[str, dict], sample: set[str]
) -> tuple[dict[str, list], list[tuple[str, list[str]]]]:
    """Decisions in force per sample object marked complete in which every value
    carries a decision, and the objects marked complete with undecided values."""
    by_object: dict[str, list] = defaultdict(list)
    for key, d in decisions.items():
        by_object[d.object].append((key, d))
    complete, incomplete = {}, []
    for oid in sorted(sample):
        held = by_object.get(oid, [])
        if oid not in objects or not any(d.decision == "complete" for _, d in held):
            continue
        decided = {k[2] for k, _ in held if k[1] == "value"}
        undecided = sorted(set(value_paths(objects[oid])) - decided)
        if undecided:
            incomplete.append((oid, undecided))
        else:
            complete[oid] = held
    return complete, incomplete


def _current(decisions: dict, records: dict) -> dict:
    return {k: d for k, d in decisions.items() if check(d, records) is None}


def agreement(log: list, records: dict, objects: dict, sample: set[str]) -> dict:
    """Cohen's kappa per pair of reviewers on the sample decisions both made.

    Each reviewer's decisions are taken in force on their own (their own
    supersessions and withdrawals), so that one reviewer never replaces the
    other's decision here."""
    reviewers = sorted({d.reviewer for d in log})
    own = {
        r: {
            k: d
            for k, d in _current(
                effective([d for d in log if d.reviewer == r]), records
            ).items()
            if d.object in sample
        }
        for r in reviewers
    }
    pairs = {}
    for a, b in combinations(reviewers, 2):
        da, db = own[a], own[b]
        shared = sorted(k for k in set(da) & set(db) if k[1] == "value")
        values = [(da[k].decision, db[k].decision) for k in shared]
        one_only = sum(1 for k in set(da) ^ set(db) if k[1] == "value")
        per_kind = {
            kind: kappa([(x == kind, y == kind) for x, y in values])
            for kind in VALUE_KINDS
        }
        complete_a, _ = complete_objects(da, objects, sample)
        complete_b, _ = complete_objects(db, objects, sample)
        both = sorted(set(complete_a) & set(complete_b))

        def added(held):
            return "added" if any(d.decision == "missing" for _, d in held) else "none"

        missing = [(added(complete_a[o]), added(complete_b[o])) for o in both]
        pairs[f"{a} | {b}"] = {
            "shared_objects": len({k[0] for k in shared}),
            "values": kappa(values),
            "values_by_kind": per_kind,
            "values_decided_by_one_only": one_only,
            "objects_both_complete": len(both),
            "missing": kappa(missing),
        }
    return {
        "about": "Cohen's kappa on the frozen review sample per pair of reviewers, "
        "only on what both decided: value decisions (all three kinds, and each "
        "kind against the others) and, on objects both marked complete, whether "
        "a missing value was added.",
        "reviewers": reviewers,
        "pairs": pairs,
    }


def measure(
    records: dict, log: list, sample: set[str], threshold: float | None
) -> dict:
    active = effective(log)
    status = {d.id: check(d, records) for d in active.values()}
    current = {k: d for k, d in active.items() if status[d.id] is None}
    stale = sorted(
        (d.object, d.id, status[d.id]) for d in active.values() if status[d.id]
    )
    objects = {o["id"]: o for r in records.values() for o in r["objects"]}
    complete, incomplete = complete_objects(current, objects, sample)
    by_field: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    by_volume: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    by_type: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    overall: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    by_rule: dict[str, Counter] = defaultdict(Counter)
    boundary = Counter()
    for oid, held in complete.items():
        obj = objects[oid]
        values = value_paths(obj)
        types = [t["value"] for t in obj.get("types", [])] or ["(none)"]
        for _, d in held:
            if d.decision in VALUE_KINDS:
                kind, field = d.decision, family(d.target.path)
                by_rule[values[d.target.path]["rule"]][kind] += 1
            elif d.decision == "missing":
                kind, field = "missing", family(d.correction.field)
            else:
                if d.decision == "boundary":
                    boundary[obj["volume"]] += 1
                continue
            by_field[field][oid][kind] += 1
            by_volume[obj["volume"]][oid][kind] += 1
            overall["all"][oid][kind] += 1
            for t in types:
                by_type[t][oid][kind] += 1
    # Where several reviewers decided one value, effective() keeps the latest.
    deciders: dict[tuple, set] = defaultdict(set)
    for d in log:
        if d.target and d.object in sample:
            deciders[(d.object, d.target.path)].add(d.reviewer)
    development = Counter(
        d.decision for d in current.values() if d.object not in sample
    )
    return {
        "about": "Field correctness on the frozen review sample as judged by persons in the viewer; "
        "precision = confirmed / (confirmed + corrected) per value with a Wilson 95 % interval "
        "and a 95 % interval from resampling whole objects, and per object as the share of "
        "judged objects without a correction; misses from values added as missing. Only "
        "complete sample objects count; reviewers saw the rule values, so this measures "
        "acceptance after inspection, not a blind annotation.",
        "bootstrap": {"seed": BOOTSTRAP_SEED, "rounds": BOOTSTRAP_ROUNDS},
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
        "values_decided_by_several_reviewers": sum(
            1 for who in deciders.values() if len(who) > 1
        ),
        "overall": rates(overall),
        "by_volume": rates(by_volume),
        "by_type": rates(by_type),
        "by_field": rates(by_field),
        "boundary_errors_by_volume": dict(sorted(boundary.items())),
        "confirmation_rule": rule_classes(by_rule, threshold),
        "agreement": agreement(log, records, objects, sample),
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
        report = measure(
            load_records(RECORDS), load_log(), set(review_objects()), load_threshold()
        )
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
            f"OK {volume}: precision {r['precision']} {r['interval95']} "
            f"(objects resampled {r['interval95_objects_resampled']}), "
            f"per object {r['object_precision']}, missing {r['missing']}"
        )
    rule = report["confirmation_rule"]
    print(f"OK confirmation rule {rule['state']}; may confirm {rule['may_confirm']}")
    for pair, a in report["agreement"]["pairs"].items():
        print(
            f"OK kappa {pair}: values {a['values']['kappa']} (n {a['values']['n']}), "
            f"missing {a['missing']['kappa']} (n {a['missing']['n']})"
        )
    if report["values_decided_by_several_reviewers"]:
        print(
            f"NOTE {report['values_decided_by_several_reviewers']} values decided by "
            "several reviewers; the latest decision enters precision"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
