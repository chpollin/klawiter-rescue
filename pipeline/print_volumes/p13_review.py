"""p13: check the human review log against the current records and measure field correctness and the concordance.

The log (data/print/review/decisions.jsonl, written by review_server.py) is
checked line by line against the strict models and the current records
(_review.py): a decision applies, or it is stale because a rebuild changed the
value it judged, or it is invalid. Correctness is measured only on the frozen
review samples (review_sample.py) and only on their objects marked complete,
in which every value carries a decision. Decisions on other objects are
development reviews, counted but never measured, because those objects were
open to rule development.

The measurement contract (knowledge/print-wiki-merge.md, Measurement):
- Reviewers. Precision comes from the first reviewer of each object
  (_review.layers). The second reviewer decides the subset marked in advance
  (review-second-subset.json) and measures agreement only; a decision of a
  second reviewer outside it is counted and never used. Disagreements are
  settled by adjudications. Three figures: reviewer 1 on the sample,
  reviewer 2 on the subset (beside reviewer 1 on the same subset), and the
  adjudicated state on the sample, which is also what p12 publishes.
- Precision per value is confirmed / (confirmed + corrected), with the Wilson
  95 % interval and a 95 % percentile interval from resampling whole objects;
  beside it the pessimistic precision with unresolved values counted as wrong
  and the field recall confirmed / (confirmed + corrected + missing). Per
  object, the share of judged objects without a correction. An object marked
  with a wrong boundary leaves these figures and enters the boundary rate.
- Weights. The sample draws a few objects per part from parts of very
  different size, so beside the unweighted figures stands a Horvitz-Thompson
  estimate with weight (entries - hard entries) / objects drawn per part
  (review-sample-pools.json) and a bootstrap that resamples objects within
  parts (parts with one object are pooled). The estimate is per entry: each
  entry counts once, by one random object.
- Hard entries. The entries the sample excluded (p10 violation or listed
  exception) are a stratum of their own (review-hard-sample.json), reported
  apart, and with the sample in one population estimate.
- Agreement on the subset: raw agreement, Cohen's kappa per kind of decision,
  and the positive specific agreement on "correct"; on objects both marked
  complete, whether a missing value was added; on objects both reviewed,
  whether a boundary was marked.
- The decision rule (confirmation_rule.json) has two rules, rule classes of
  the fields and routes of the concordance, each bound to the volume. Only
  the classes fixed in advance (--fix-rule, before any decision) may confirm:
  those with at least minExpectedJudged values (claims) expected in the
  sample. A class confirms when the weighted precision exceeds the threshold
  under the object-resampled bootstrap, with Holm's correction over the
  admissible classes of its rule, and only while the code the classes were
  fixed on is unchanged. While a threshold is null nothing confirms; the
  operator has decided that in this phase every confirmation is a person's.

The concordance part reads the blind sheets of p09, compares each answer
with the proposals the current claims make for that entry (p07 changed after
the first drawing), and weighs each entry by the inverse of its inclusion
probability in the union of both blind samples. The claim sheet of phase 2
gives claim precision per route and volume.

The field figures measure what persons accepted while seeing the rule values;
the blind phase of the concordance alone measures from the print entry
without proposals. Silver pairs (p07, p08) are a development metric and enter
no figure here. Every report names the commit and the gate result it ran on.

Output: data/print/derived/reports/p13_review.json.

Usage: python -m uv run python pipeline/print_volumes/p13_review.py
       [--log PATH] [--fix-rule]
"""

import argparse
import ast
import hashlib
import json
import math
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import _review
from _common import DERIVED_DIR, HERE, PROJECT_ROOT, write_report
from _heldout import (
    BLIND_KEY,
    BLIND_KEY_2,
    BLIND_SHEET,
    BLIND_SHEET_2,
    BLIND_STRATA,
    CLAIMS_SHEET,
    REVIEW_HARD,
    REVIEW_POOLS,
    REVIEW_SAMPLE,
    REVIEW_SECOND,
)
from _review import (
    VALUE_DECISIONS,
    check,
    in_force,
    layers,
    load_log,
    load_records,
    value_paths,
)

RECORDS = DERIVED_DIR / "records"
RULE_FILE = HERE / "confirmation_rule.json"
GATE_REPORT = DERIVED_DIR / "gate" / "p14_gate.json"
BOOTSTRAP_SEED = 20261024
BOOTSTRAP_ROUNDS = 2000
# Holm's smallest level over a few dozen classes needs a finer distribution.
RULE_ROUNDS = 10000
VALUE_KINDS = VALUE_DECISIONS
ROUTES = ("field", "title-year", "alignment")
MEASURED_ROUTES = ("field", "title-year")
ABOUT = (
    "Field correctness on the frozen review samples as judged by persons in the "
    "viewer, and the concordance on the blind samples of p09. Precision = confirmed / "
    "(confirmed + corrected) per value with a Wilson 95 % interval and a 95 % "
    "interval from resampling whole objects; beside it with unresolved counted as "
    "wrong, the field recall over complete objects, the share of objects without a "
    "correction, and a Horvitz-Thompson estimate weighted by part. Reviewer 1 gives "
    "precision, reviewer 2 agreement on the subset marked in advance, adjudications "
    "settle their disagreements. Objects with a wrong boundary leave the field "
    "figures. Reviewers saw the rule values, so the field figures are acceptance by "
    "one reviewer after inspection, not a blind annotation; until a second person "
    "decides the subset they are one person's. Silver pairs of p07 and p08 are a "
    "development metric and enter no figure here."
)


def wilson(hits: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    z, p = 1.96, hits / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3)]


def ratio(hits: float, n: float) -> float | None:
    return round(hits / n, 3) if n else None


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
    return percentile(sorted(stats))


def percentile(stats: list[float], low: float = 0.025) -> list[float] | None:
    if not stats:
        return None
    rounds = len(stats)
    return [
        round(stats[math.floor(low * (rounds - 1))], 3),
        round(stats[math.ceil((1 - low) * (rounds - 1))], 3),
    ]


# A unit is one sampled object (or entry): (stratum, weight, hits, n).
def weighted_ratio(units: list[tuple]) -> float | None:
    den = sum(w * n for _, w, _, n in units)
    return sum(w * h for _, w, h, _ in units) / den if den else None


def stratified_draws(
    units: list[tuple], rounds: int = BOOTSTRAP_ROUNDS, seed: int = BOOTSTRAP_SEED
) -> list[float]:
    """Sorted bootstrap distribution of the weighted ratio, resampling units
    with replacement within their strata; strata holding one unit are pooled,
    since a single unit shows no variance of its own."""
    strata: dict[str, list] = defaultdict(list)
    for u in units:
        strata[u[0]].append(u)
    groups = [g for g in strata.values() if len(g) > 1]
    single = [u for g in strata.values() if len(g) == 1 for u in g]
    if single:
        groups.append(single)
    rng = random.Random(seed)
    stats = []
    for _ in range(rounds):
        num = den = 0.0
        for group in groups:
            for _, w, h, n in rng.choices(group, k=len(group)):
                num += w * h
                den += w * n
        if den:
            stats.append(num / den)
    return sorted(stats)


def weighted(units: list[tuple]) -> dict:
    """The weighted estimate of a ratio with its stratified 95 % interval."""
    estimate = weighted_ratio(units)
    return {
        "estimate": None if estimate is None else round(estimate, 3),
        "interval95": percentile(stratified_draws(units))
        if estimate is not None
        else None,
        "units": sum(1 for u in units if u[3]),
    }


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


def positive_agreement(pairs: list[tuple[str, str]], category: str) -> dict:
    """Positive specific agreement on one category: 2a / (2a + b + c), with a
    the items both put in it and b + c those only one did."""
    both = sum(1 for a, b in pairs if a == b == category)
    one = sum(1 for a, b in pairs if (a == category) != (b == category))
    return {
        "category": category,
        "both": both,
        "one_only": one,
        "value": ratio(2 * both, 2 * both + one),
    }


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
        strict = judged + c["unresolved"]
        complete = judged + c["missing"]
        judged_objects = [k for k in ordered if k["confirm"] + k["correct"]]
        clean = sum(1 for k in judged_objects if not k["correct"])
        out[key] = {
            "confirmed": c["confirm"],
            "corrected": c["correct"],
            "unresolved": c["unresolved"],
            "missing": c["missing"],
            "precision": ratio(c["confirm"], judged),
            "interval95": wilson(c["confirm"], judged),
            "interval95_objects_resampled": bootstrap(
                [(k["confirm"], k["confirm"] + k["correct"]) for k in ordered]
            ),
            "precision_unresolved_as_wrong": ratio(c["confirm"], strict),
            "interval95_unresolved_as_wrong": wilson(c["confirm"], strict),
            "recall": ratio(c["confirm"], complete),
            "recall_interval95": wilson(c["confirm"], complete),
            "objects": len(ordered),
            "objects_judged": len(judged_objects),
            "objects_without_correction": clean,
            "object_precision": ratio(clean, len(judged_objects)),
            "object_interval95": wilson(clean, len(judged_objects)),
        }
    return out


def complete_objects(
    decisions: dict[tuple, object], objects: dict[str, dict], sample
) -> tuple[dict[str, list], list[tuple[str, list[str]]], set[str]]:
    """Per sample object marked complete in which every value carries a
    decision, its decisions in force; the objects marked complete with
    undecided values; and the objects marked with a wrong boundary, which
    leave the field figures."""
    by_object: dict[str, list] = defaultdict(list)
    for key, d in decisions.items():
        by_object[d.object].append((key, d))
    complete, incomplete, boundary = {}, [], set()
    for oid in sorted(sample):
        held = by_object.get(oid, [])
        if oid not in objects:
            continue
        if any(d.decision == "boundary" for _, d in held):
            boundary.add(oid)
            continue
        if not any(d.decision == "complete" for _, d in held):
            continue
        decided = {k[2] for k, _ in held if k[1] == "value"}
        undecided = sorted(set(value_paths(objects[oid])) - decided)
        if undecided:
            incomplete.append((oid, undecided))
        else:
            complete[oid] = held
    return complete, incomplete, boundary


def object_counts(held: list, obj: dict) -> tuple[Counter, dict, dict]:
    """An object's decisions as counts: overall, per field family and per rule."""
    values = value_paths(obj)
    total, fields, rules = Counter(), defaultdict(Counter), defaultdict(Counter)
    for _, d in held:
        if d.decision in VALUE_KINDS:
            kind, field = d.decision, family(d.target.path)
            rules[values[d.target.path]["rule"]][kind] += 1
        elif d.decision == "missing":
            kind, field = "missing", family(d.correction.field)
        else:
            continue
        total[kind] += 1
        fields[field][kind] += 1
    return total, fields, rules


METRICS = {
    "precision": (("confirm",), ("confirm", "correct")),
    "precision_unresolved_as_wrong": (
        ("confirm",),
        ("confirm", "correct", "unresolved"),
    ),
    "recall": (("confirm",), ("confirm", "correct", "missing")),
}


def units_of(per_object: dict[str, Counter], design: dict, metric: str) -> list[tuple]:
    hits, base = METRICS[metric]
    return [
        (
            design[o]["stratum"],
            design[o]["weight"],
            sum(c[k] for k in hits),
            sum(c[k] for k in base),
        )
        for o, c in sorted(per_object.items())
    ]


def weighted_figures(per_object: dict[str, Counter], design: dict) -> dict | None:
    """The weighted estimates overall and by volume; None without weights."""
    if any(design.get(o, {}).get("weight") is None for o in per_object):
        return None
    by_volume: dict[str, dict] = defaultdict(dict)
    for o in per_object:
        by_volume[design[o]["volume"]][o] = per_object[o]
    groups = {"all": per_object, **dict(sorted(by_volume.items()))}
    return {
        name: {m: weighted(units_of(group, design, m)) for m in METRICS}
        for name, group in groups.items()
    }


def figure(decisions: dict, objects: dict, sample, design: dict | None) -> dict:
    """Every figure of one layer of decisions on one sample."""
    complete, incomplete, boundary = complete_objects(decisions, objects, sample)
    overall, by_volume, by_type, by_field = (
        defaultdict(lambda: defaultdict(Counter)) for _ in range(4)
    )
    per_object: dict[str, Counter] = {}
    for oid, held in complete.items():
        obj = objects[oid]
        total, fields, _ = object_counts(held, obj)
        per_object[oid] = total
        overall["all"][oid] += total
        by_volume[obj["volume"]][oid] += total
        for t in [t["value"] for t in obj.get("types", [])] or ["(none)"]:
            by_type[t][oid] += total
        for field, c in fields.items():
            by_field[field][oid] += c
    reviewed = Counter(objects[o]["volume"] for o in (*complete, *boundary))
    flagged = Counter(objects[o]["volume"] for o in boundary)
    return {
        "sample_objects": len(sample),
        "complete": len(complete),
        "complete_with_undecided_values": [
            {"object": o, "undecided": u} for o, u in incomplete
        ],
        "overall": rates(overall),
        "by_volume": rates(by_volume),
        "by_type": rates(by_type),
        "by_field": rates(by_field),
        "weighted": weighted_figures(per_object, design) if design else None,
        "boundary": {
            "about": "objects marked with a wrong boundary among the objects "
            "reviewed (complete or so marked); they leave the field figures",
            "by_volume": {
                v: {
                    "flagged": flagged[v],
                    "reviewed": n,
                    "rate": ratio(flagged[v], n),
                    "interval95": wilson(flagged[v], n),
                }
                for v, n in sorted(reviewed.items())
            },
        },
        "_per_object": per_object,
        "_complete": complete,
    }


def agreement(first: dict, second: dict, objects: dict, subset: set[str]) -> dict:
    """Agreement of the first and second reviewer on the subset marked in advance."""

    def on(layer, oid):
        return {k: d for k, d in layer.items() if d.object == oid}

    values, one_only, missing, boundary, both_reviewed = [], 0, [], [], 0
    for oid in sorted(subset):
        a, b = on(first, oid), on(second, oid)
        if not a or not b or oid not in objects:
            continue
        both_reviewed += 1
        va = {k: d for k, d in a.items() if k[1] == "value"}
        vb = {k: d for k, d in b.items() if k[1] == "value"}
        values += [(va[k].decision, vb[k].decision) for k in sorted(set(va) & set(vb))]
        one_only += len(set(va) ^ set(vb))
        boundary.append(
            tuple(
                "boundary"
                if any(d.decision == "boundary" for d in x.values())
                else "none"
                for x in (a, b)
            )
        )
        if all(any(d.decision == "complete" for d in x.values()) for x in (a, b)):
            missing.append(
                tuple(
                    "added"
                    if any(d.decision == "missing" for d in x.values())
                    else "none"
                    for x in (a, b)
                )
            )
    return {
        "about": "First against second reviewer on the subset marked in advance, only "
        "on what both decided: raw agreement and Cohen's kappa on value decisions (all "
        "three kinds and each kind against the others), the positive specific "
        "agreement on correct, on objects both marked complete whether a missing value "
        "was added, and on objects both reviewed whether a boundary was marked.",
        "subset_objects": len(subset),
        "objects_both_reviewed": both_reviewed,
        "values": kappa(values),
        "values_positive_agreement": positive_agreement(values, "correct"),
        "values_by_kind": {
            kind: kappa([(x == kind, y == kind) for x, y in values])
            for kind in VALUE_KINDS
        },
        "values_decided_by_one_only": one_only,
        "missing": kappa(missing),
        "boundary": kappa(boundary),
    }


def disagreements(first: dict, second: dict, adjudications: dict) -> list[dict]:
    """Value decisions of the two reviewers that differ and stand unsettled."""
    out = []
    for key in sorted(set(first) & set(second)):
        if key[1] != "value":
            continue
        a, b = first[key], second[key]
        if (a.decision, a.correction) != (b.decision, b.correction) and (
            key[0],
            "adjudicate",
            key[2],
        ) not in adjudications:
            out.append(
                {"object": key[0], "path": key[2], "first": a.id, "second": b.id}
            )
    return out


# The decision rule.
def module_closure(entry: str) -> list[str]:
    """The strand modules an entry module imports, transitively, itself included."""
    seen, todo = set(), [entry]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        for node in ast.walk(ast.parse((HERE / name).read_text("utf-8"))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names = [node.module]
            else:
                continue
            todo += [f"{m}.py" for m in names if (HERE / f"{m}.py").is_file()]
    return sorted(seen)


# The values of the fields come from p03 and its imports and the section map;
# the claims of the routes from p07 and its imports. A rule's own code cannot
# be told apart inside these modules, so a change of any of them invalidates
# every class of its rule. Upgrade path: a code identity per rule.
CODE_OF = {
    "fields": ("p03_records.py", ("sections.json",)),
    "routes": ("p07_concordance.py", ()),
}


def code_identity(rule: str) -> dict:
    entry, data = CODE_OF[rule]
    files = [*module_closure(entry), *data]
    lines = "".join(
        f"{n}\t{hashlib.sha256((HERE / n).read_bytes()).hexdigest()}\n" for n in files
    )
    return {"files": files, "sha256": hashlib.sha256(lines.encode()).hexdigest()}


def load_rule(path: Path = RULE_FILE) -> dict:
    """The two rules, each with a threshold that is null or in (0, 1]."""
    data = json.loads(path.read_text(encoding="utf-8"))
    for name in ("fields", "routes"):
        rule = data.get(name)
        if not isinstance(rule, dict):
            raise ValueError(f"{path}: rule {name} missing")
        threshold = rule.get("threshold")
        if threshold is not None and (
            type(threshold) not in (int, float) or not 0 < threshold <= 1
        ):
            raise ValueError(f"{path}: {name}.threshold must be null or in (0, 1]")
        if not isinstance(rule.get("admissible"), list):
            raise ValueError(
                f"{path}: {name}.admissible must be a list fixed in advance"
            )
    return data


def holm(pvalues: dict[str, float], alpha: float) -> set[str]:
    """The hypotheses Holm's step-down procedure rejects at family level alpha."""
    out = set()
    ordered = sorted(pvalues.items(), key=lambda kv: (kv[1], kv[0]))
    for k, (name, p) in enumerate(ordered):
        if p > alpha / (len(ordered) - k):
            break
        out.add(name)
    return out


def decide(rule: dict, classes: dict[str, list[tuple]], code_now: str | None) -> dict:
    """The decision rule over measured classes (class -> units). Only admissible
    classes may confirm, only with a threshold set and the code unchanged."""
    threshold = rule.get("threshold")
    alpha = rule.get("alpha", 0.025)
    admissible = list(rule.get("admissible", []))
    fixed = (rule.get("fixed") or {}).get("code", {}).get("sha256")
    if code_now is not None and fixed is None:
        state = "not fixed: no admissible classes yet (p13_review.py --fix-rule)"
    elif code_now is not None and fixed != code_now:
        state = (
            f"invalidated: the code changed since the admissible classes were fixed "
            f"({fixed} -> {code_now}); nothing may confirm until they are fixed again"
        )
    elif threshold is None:
        state = (
            "unset: nothing may confirm without a person while the threshold is null"
            + (f" ({rule['thresholdReason']})" if rule.get("thresholdReason") else "")
        )
    else:
        state = f"set to {threshold}"
    report = {}
    for name in sorted(set(classes) | set(admissible)):
        units = classes.get(name, [])
        entry = weighted(units)
        entry["admissible"] = name in admissible
        report[name] = entry
    may = []
    if state.startswith("set"):
        pvalues = {}
        for name in admissible:
            draws = stratified_draws(classes.get(name, []), RULE_ROUNDS)
            below = sum(1 for s in draws if s <= threshold)
            pvalues[name] = (1 + below) / (1 + len(draws)) if draws else 1.0
            report[name]["p_value"] = round(pvalues[name], 5)
        may = sorted(holm(pvalues, alpha))
        for name in admissible:
            report[name]["may_confirm"] = name in may
    return {
        "threshold": threshold,
        "alpha": alpha,
        "correction": "holm",
        "state": state,
        "admissible": len(admissible),
        "may_confirm": may,
        "classes": report,
    }


def rule_units(complete: dict, objects: dict, design: dict | None) -> dict:
    """Per rule class (rule@volume) one unit per complete object of its volume."""
    classes: dict[str, list] = defaultdict(list)
    by_volume: dict[str, list] = defaultdict(list)
    for oid, held in sorted(complete.items()):
        _, _, rules = object_counts(held, objects[oid])
        by_volume[objects[oid]["volume"]].append((oid, rules))
    for volume, rows in by_volume.items():
        names = {r for _, rules in rows for r in rules}
        for rule in names:
            for oid, rules in rows:
                c = rules.get(rule, Counter())
                info = (design or {}).get(oid) or {"stratum": volume, "weight": 1.0}
                classes[f"{rule}@{volume}"].append(
                    (
                        info["stratum"],
                        info["weight"] or 1.0,
                        c["confirm"],
                        c["confirm"] + c["correct"],
                    )
                )
    return classes


def measure(
    records: dict,
    log: list,
    design: dict,
    rule: dict | None = None,
    code_now: dict | None = None,
) -> dict:
    """The field part of the report. design holds "review" and "hard" (object
    -> volume, stratum, weight) and "second" (the subset)."""
    review, hard, second_subset = (
        design["review"],
        design.get("hard", {}),
        design.get("second", set()),
    )
    measured = set(review) | set(hard)
    force = in_force(log)
    status = {d.id: check(d, records) for d in force.values()}
    stale = sorted(
        (d.object, d.id, status[d.id]) for d in force.values() if status[d.id]
    )
    layer = layers(log)

    def current(decisions):
        return {k: d for k, d in decisions.items() if status.get(d.id) is None}

    first, second, adjudicated = (
        current(layer[n]) for n in ("first", "second", "adjudicated")
    )
    objects = {o["id"]: o for r in records.values() for o in r["objects"]}
    weights = {**review, **hard}
    reviewer1 = figure(first, objects, set(review), review)
    adjudicated_fig = figure(adjudicated, objects, set(review), review)
    hard_fig = figure(first, objects, set(hard), hard)
    population = (
        weighted_figures(
            {**reviewer1["_per_object"], **hard_fig["_per_object"]}, weights
        )
        if hard
        else None
    )
    rule = rule if rule is not None else load_rule()
    fields_rule = decide(
        rule["fields"],
        rule_units(reviewer1["_complete"], objects, review),
        None if code_now is None else code_now.get("fields"),
    )
    outside = sorted(
        {d.object for d in second.values() if d.object not in second_subset}
    )
    development = Counter(
        d.decision
        for d in force.values()
        if status[d.id] is None
        and d.object not in measured
        and d.decision != "adjudicate"
    )
    figures = {
        "reviewer1": reviewer1,
        "reviewer1_on_second_subset": figure(first, objects, second_subset, None),
        "reviewer2": figure(second, objects, second_subset, None),
        "adjudicated": adjudicated_fig,
        "hard": hard_fig,
    }
    for f in figures.values():
        f.pop("_per_object")
        f.pop("_complete")
    return {
        "log_lines": len(log),
        "decisions_in_force": sum(1 for s in status.values() if s is None),
        "stale_or_invalid": [
            {"object": o, "decision": i, "reason": r} for o, i, r in stale
        ],
        "reviewers": sorted({d.reviewer for d in force.values()}),
        "figures": figures,
        "population": {
            "about": "review sample and hard stratum in one weighted estimate, "
            "reviewer 1; entries of the development sample and of other held-out "
            "samples are represented by the sample",
            "weighted": population,
        },
        "agreement": agreement(first, second, objects, second_subset),
        "second_reviewer_outside_subset": {
            "about": "objects a second reviewer decided outside the subset marked in "
            "advance; they enter no figure",
            "objects": outside,
        },
        "adjudications": {
            "valid": len(layer["adjudications"]),
            "invalid": [
                {"decision": d.id, "object": d.object, "reason": r}
                for d, r in layer["invalid_adjudications"]
            ],
            "open_disagreements": disagreements(first, second, layer["adjudications"]),
        },
        "confirmation_rule_fields": fields_rule,
        "development_reviews": dict(sorted(development.items())),
    }


# The concordance.
def blind_units(
    key1: dict, sizes1: dict, key2: dict | None, sizes2: dict | None
) -> dict:
    """Per blind row its entry, volume, bootstrap stratum and weight: the
    inverse of its inclusion probability in the union of both samples, the sum
    of the two designs' probabilities (first order, both fractions being small)."""
    drawn1 = Counter((r["printId"].split("/")[0], r["stratum"]) for r in key1.values())
    first_rows = (key2 or {}).get("firstSampleStrata", {})
    sizes2 = sizes2 or {}

    def pi1(volume, s):
        size = sizes1.get(volume, {}).get(s)
        return drawn1[(volume, s)] / size if size else 0.0

    def pi2(volume, t):
        cell = sizes2.get(volume, {}).get(t) or {}
        return cell["drawn"] / cell["pool"] if cell.get("pool") else 0.0

    out = {}
    rows = [
        ("first", sid, r, r["stratum"], first_rows.get(sid)) for sid, r in key1.items()
    ]
    rows += [
        ("second", sid, r, r["firstDesignStratum"], r["stratum"])
        for sid, r in ((key2 or {}).get("key") or {}).items()
    ]
    for design, sid, row, s1, s2 in rows:
        volume = row["printId"].split("/")[0]
        pi = pi1(volume, s1) + pi2(volume, s2)
        out[sid] = {
            "entry": row["printId"],
            "volume": volume,
            "stratum": f"{design}/{volume}/{s1 if design == 'first' else s2}",
            "weight": 1 / pi if pi else None,
        }
    return out


def _estimate(units: list[tuple]) -> dict:
    hits = sum(h for _, _, h, _ in units)
    n = sum(n for _, _, _, n in units)
    out = {"hits": hits, "n": n, "rate": ratio(hits, n), "interval95": wilson(hits, n)}
    if all(w is not None for _, w, _, _ in units):
        out["weighted"] = weighted(units)
    return out


def concordance(
    units: dict, answers: dict, proposed: dict, claim_rows: list[dict]
) -> dict:
    """Phase 1 against the current proposals, phase 2 on the claim sheet."""
    phase1: dict[str, dict] = {}
    for volume in sorted({u["volume"] for u in units.values()}):
        rows = [(sid, u) for sid, u in sorted(units.items()) if u["volume"] == volume]
        per_route = {}
        for route in ROUTES:
            precision, recall = [], []
            for sid, u in rows:
                answer = answers.get(sid)
                pages = proposed.get(u["entry"], {}).get(route, set())
                if answer is None or answer[0] == "unsure":
                    continue
                hit = int(answer[0] == "page" and answer[1] in pages)
                if pages:
                    precision.append((u["stratum"], u["weight"], hit, 1))
                if answer[0] == "page":
                    recall.append((u["stratum"], u["weight"], hit, 1))
            per_route[route] = {
                "entry_precision": _estimate(precision),
                "recall": _estimate(recall),
            }
        missed = []
        for sid, u in rows:
            answer = answers.get(sid)
            if answer and answer[0] == "page":
                routes = proposed.get(u["entry"], {})
                found = any(answer[1] in routes.get(r, set()) for r in MEASURED_ROUTES)
                missed.append((u["stratum"], u["weight"], int(not found), 1))
        phase1[volume] = {
            "entries": len(rows),
            "answered": sum(1 for sid, _ in rows if answers.get(sid)),
            "unsure": sum(
                1 for sid, _ in rows if (answers.get(sid) or ("",))[0] == "unsure"
            ),
            "none": sum(
                1 for sid, _ in rows if (answers.get(sid) or ("",))[0] == "none"
            ),
            "routes": per_route,
            "found_by_neither_route": _estimate(missed),
        }
    phase2: dict[str, dict] = defaultdict(dict)
    grouped: dict[tuple, dict] = defaultdict(lambda: defaultdict(Counter))
    for row in claim_rows:
        u = units.get(row["sample_id"])
        if u is None or not row.get("decision"):
            continue
        factor = int(row["claims_of_route"]) / int(row["drawn_of_route"])
        grouped[(u["volume"], row["route"])][row["sample_id"]][row["decision"]] += (
            factor
        )
    classes = {}
    for (volume, route), per_entry in sorted(grouped.items()):
        plain = sum(per_entry.values(), Counter())
        strict, lenient = [], []
        for sid, c in sorted(per_entry.items()):
            u = units[sid]
            strict.append(
                (
                    u["stratum"],
                    u["weight"],
                    c["right"],
                    c["right"] + c["wrong"] + c["unsure"],
                )
            )
            lenient.append(
                (u["stratum"], u["weight"], c["right"], c["right"] + c["wrong"])
            )
        phase2[volume][route] = {
            "entries": len(per_entry),
            "claims_decided": round(
                plain["right"] + plain["wrong"] + plain["unsure"], 3
            ),
            "claim_precision": weighted(lenient)
            if all(w is not None for _, w, _, _ in lenient)
            else None,
            "claim_precision_unsure_as_wrong": weighted(strict)
            if all(w is not None for _, w, _, _ in strict)
            else None,
        }
        classes[f"{route}@{volume}"] = lenient
    return {"phase1": phase1, "phase2": dict(phase2), "_classes": classes}


def load_concordance(rule: dict, code_now: dict | None) -> dict:
    """The concordance part of the report from the local sample files."""
    import p09_human_sample as p09

    if not BLIND_KEY.exists() or not BLIND_STRATA.exists():
        return {"state": "the blind sample or its stratum sizes are missing"}
    key1 = json.loads(BLIND_KEY.read_text("utf-8"))["key"]
    sizes1 = json.loads(BLIND_STRATA.read_text("utf-8"))["sizes"]
    key2 = json.loads(BLIND_KEY_2.read_text("utf-8")) if BLIND_KEY_2.exists() else None
    units = blind_units(key1, sizes1, key2, key2 and key2["sizes"])
    answers, problems = {}, []
    for sheet in (BLIND_SHEET, BLIND_SHEET_2):
        found, wrong = p09.answers(sheet)
        answers.update(found)
        problems += wrong
    claim_rows, wrong = p09.claim_answers(CLAIMS_SHEET)
    problems += wrong
    answered = sum(1 for a in answers.values() if a)
    # The claims file is large; it is read only once a person has answered.
    proposed = (
        p09.proposals(wanted={u["entry"] for u in units.values()}) if answered else {}
    )
    result = concordance(units, answers, proposed, claim_rows)
    classes = result.pop("_classes")
    return {
        "about": "Phase 1: the person's blind answers (wiki page, none or unsure) "
        "against the pages the current claims propose for the entry, per route and "
        "volume: entry precision over entries with a proposal of the route, recall "
        "over entries with a page; weighted by the inverse inclusion probability in "
        "the union of both blind samples, the first sample's stratum sizes "
        "reconstructed (concordance-blind-strata.json). Phase 2: claim precision per "
        "route and volume from the claim sheet, each claim weighted by its entry and "
        "by claims of the route over claims drawn. Silver pairs are a development "
        "metric and enter no figure here.",
        "rows": len(units),
        "answered": answered,
        "claim_sheet": CLAIMS_SHEET.exists(),
        "claims_decided": sum(1 for r in claim_rows if r["decision"]),
        "problems": problems,
        **result,
        "confirmation_rule_routes": decide(
            rule["routes"],
            classes,
            None if code_now is None else code_now.get("routes"),
        ),
    }


def load_design() -> dict:
    """The review samples with their bootstrap strata and weights."""
    review, hard, second = {}, {}, set()
    pools = (
        json.loads(REVIEW_POOLS.read_text("utf-8"))["parts"]
        if REVIEW_POOLS.exists()
        else {}
    )
    if REVIEW_SAMPLE.exists():
        for volume, parts in json.loads(REVIEW_SAMPLE.read_text("utf-8"))[
            "objects"
        ].items():
            for part, ids in parts.items():
                c = pools.get(volume, {}).get(part)
                weight = (c["entries"] - c["hard"]) / c["drawn"] if c else None
                for o in ids:
                    review[o] = {
                        "volume": volume,
                        "stratum": f"{volume}/{part}",
                        "weight": weight,
                    }
    if REVIEW_HARD.exists():
        data = json.loads(REVIEW_HARD.read_text("utf-8"))
        for volume, ids in data["objects"].items():
            size = data["pools"][volume]
            for o in ids:
                hard[o] = {
                    "volume": volume,
                    "stratum": f"hard/{volume}",
                    "weight": size["pool"] / size["drawn"],
                }
    if REVIEW_SECOND.exists():
        second = set(json.loads(REVIEW_SECOND.read_text("utf-8"))["objects"])
    return {"review": review, "hard": hard, "second": second}


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def provenance() -> dict:
    """The commit and the gate result this report ran on."""
    from p14_gate import sha256_file, strand_code_hash

    code, _ = strand_code_hash()
    out = {
        "commit": _git("rev-parse", "HEAD"),
        "changed_in_strand": (
            _git("status", "--porcelain", "--", "pipeline/print_volumes") or ""
        ).splitlines(),
        "strand_code_sha256": code,
        "gate": None,
    }
    if GATE_REPORT.exists():
        gate = json.loads(GATE_REPORT.read_text("utf-8"))
        rebuilt = gate.get("checks", {}).get("rebuild", {}).get("records", {})
        out["gate"] = {
            "ok": gate.get("ok"),
            "commit": gate.get("inputs", {}).get("git", {}).get("commit"),
            "strand_code_sha256": gate.get("inputs", {}).get("code", {}).get("sha256"),
            "same_code": gate.get("inputs", {}).get("code", {}).get("sha256") == code,
            "records_equal_live": bool(rebuilt)
            and all(
                (RECORDS / name).is_file() and sha256_file(RECORDS / name) == sha
                for name, sha in rebuilt.items()
            ),
            "checks": {k: v.get("ok") for k, v in gate.get("checks", {}).items()},
        }
    return out


def fix_rule(log: list, design: dict, records: dict) -> int:
    """Fix the admissible classes of both rules before any decision or answer."""
    import p09_human_sample as p09

    measured = set(design["review"]) | set(design["hard"])
    if any(d.object in measured for d in log):
        print(
            "FEHLER the log holds decisions on sample objects; the classes stay as fixed"
        )
        return 1
    answered = [
        a for s in (BLIND_SHEET, BLIND_SHEET_2) for a in p09.answers(s)[0].values() if a
    ]
    if answered or CLAIMS_SHEET.exists():
        print("FEHLER the blind round has begun; the classes stay as fixed")
        return 1
    rule = json.loads(RULE_FILE.read_text("utf-8"))
    objects = {o["id"]: o for r in records.values() for o in r["objects"]}
    expected = Counter()
    for oid, info in design["review"].items():
        for v in value_paths(objects[oid]).values():
            expected[f"{v['rule']}@{info['volume']}"] += 1
    least = rule["fields"]["minExpectedJudged"]
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    rule["fields"]["admissible"] = sorted(c for c, n in expected.items() if n >= least)
    rule["fields"]["fixed"] = {"on": today, "code": code_identity("fields")}
    keys = {**json.loads(BLIND_KEY.read_text("utf-8"))["key"]}
    if BLIND_KEY_2.exists():
        keys.update(json.loads(BLIND_KEY_2.read_text("utf-8"))["key"])
    claims = p09.claims_by_entry(wanted={r["printId"] for r in keys.values()})
    expected_claims = Counter()
    for row in keys.values():
        volume = row["printId"].split("/")[0]
        for route in MEASURED_ROUTES:
            expected_claims[f"{route}@{volume}"] += p09.capped(
                claims.get(row["printId"], {}), route
            )
    least = rule["routes"]["minExpectedJudged"]
    rule["routes"]["admissible"] = sorted(
        c for c, n in expected_claims.items() if n >= least
    )
    rule["routes"]["fixed"] = {"on": today, "code": code_identity("routes")}
    RULE_FILE.write_text(
        json.dumps(rule, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for name in ("fields", "routes"):
        print(f"OK {name}: {len(rule[name]['admissible'])} admissible classes fixed")
    print(f"OK expected claims {dict(sorted(expected_claims.items()))}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--log",
        type=Path,
        default=_review.LOG,
        help="decision log; another file is a trial and writes p13_review_trial",
    )
    parser.add_argument(
        "--fix-rule", action="store_true", help="fix the admissible classes of the rule"
    )
    args = parser.parse_args()
    trial = args.log.resolve() != _review.LOG.resolve()
    _review.LOG = args.log.resolve()
    try:
        log, records, design = load_log(), load_records(RECORDS), load_design()
        if args.fix_rule:
            return fix_rule(log, design, records)
        rule = load_rule()
        code_now = {name: code_identity(name)["sha256"] for name in CODE_OF}
        report = {
            "about": ABOUT,
            "bootstrap": {"seed": BOOTSTRAP_SEED, "rounds": BOOTSTRAP_ROUNDS},
            "ran_on": provenance(),
            **measure(records, log, design, rule, code_now),
            "concordance": load_concordance(rule, code_now),
        }
    except ValueError as e:
        print(f"FEHLER {e}")
        return 1
    write_report("p13_review_trial" if trial else "p13_review", report)
    ran = report["ran_on"]
    gate = ran["gate"] or {}
    print(
        f"OK ran on {ran['commit']} ({len(ran['changed_in_strand'])} changed in the strand); "
        f"gate ok {gate.get('ok')} on {gate.get('commit')}, same code {gate.get('same_code')}, "
        f"records equal live {gate.get('records_equal_live')}"
    )
    print(
        f"OK {report['log_lines']} log lines, {report['decisions_in_force']} decisions in force, "
        f"{len(report['stale_or_invalid'])} stale or invalid"
    )
    for name, f in report["figures"].items():
        print(f"OK {name}: {f['complete']} of {f['sample_objects']} objects complete")
        for volume, r in f["by_volume"].items():
            print(
                f"   {volume}: precision {r['precision']} {r['interval95']} "
                f"(objects resampled {r['interval95_objects_resampled']}), unresolved as "
                f"wrong {r['precision_unresolved_as_wrong']}, recall {r['recall']}"
            )
    a = report["agreement"]
    print(
        f"OK agreement on {a['objects_both_reviewed']} of {a['subset_objects']} subset objects: "
        f"values kappa {a['values']['kappa']} (n {a['values']['n']}), positive agreement "
        f"on correct {a['values_positive_agreement']['value']}"
    )
    c = report["concordance"]
    print(
        f"OK concordance: {c.get('answered')} of {c.get('rows')} blind rows answered, "
        f"{c.get('claims_decided')} claims decided"
    )
    for key in ("confirmation_rule_fields",):
        r = report[key]
        print(
            f"OK fields rule {r['state']}; {r['admissible']} admissible; may confirm {r['may_confirm']}"
        )
    r = c.get("confirmation_rule_routes")
    if r:
        print(
            f"OK routes rule {r['state']}; {r['admissible']} admissible; may confirm {r['may_confirm']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
