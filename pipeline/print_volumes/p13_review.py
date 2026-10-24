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
- Agreement on the subset: raw agreement, Cohen's kappa and Krippendorff's
  alpha (nominal, with an object-resampled interval), positive and negative
  specific agreement per category and the full table, per kind of decision;
  on objects both marked complete, whether a missing value was added; on
  objects both reviewed, whether a boundary was marked. Both reviewers decide
  with the rule values in view, so this is agreement under proposals, and the
  operator, who wrote the rules, is one of the reviewers (UNDER_PROPOSALS).
- Intra-rater consistency: the hidden repeats of the repeat set
  (review_sample.py --protocol) against the same reviewer's first decision on
  the value, with the same figures and the interval between the two.
- Order: the protocol's queues, shuffled with a recorded seed, are checked
  against the samples, and the report says per reviewer how far the order of
  their first decisions followed their queue.
- The decision rule (confirmation_rule.json) has two rules, rule classes of
  the fields and routes of the concordance, each bound to the volume. Only
  the classes fixed in advance (--fix-rule, before any decision) may confirm:
  those with at least minExpectedJudged values (claims) expected in the
  sample, and only while the code they were fixed on is unchanged. A class
  confirms only with at least minJudgedObjects judged objects (entries) and
  at least ceil(ln(alpha / m) / ln(threshold)) judged values, m the
  admissible classes: below that, zero observed errors cannot carry the exact
  lower bound above the threshold at the strictest Holm level. Its p-value is
  the larger of the exact binomial tail and the object-resampled bootstrap
  (which alone confirms any error-free class), under Holm's step-down at
  level alpha. While a threshold is null nothing confirms; the operator has
  decided that in this phase every confirmation is a person's.

The concordance part reads the blind sheets of p09, compares each answer
with the proposals the current claims make for that entry (p07 changed after
the first drawing), and weighs each entry by the inverse of its inclusion
probability in the union of both blind samples. The claim sheet of phase 2
gives claim precision per route and volume. The anchoring effect compares,
claim by claim, phase 2 with what the same person's blind answer on the same
entry implies (anchoring).

The field figures measure what persons accepted while seeing the rule values;
the blind phase of the concordance alone measures from the print entry
without proposals. Silver pairs (p07, p08) are a development metric and enter
no figure here. Every report names the commit and the gate result it ran on,
and its "reporting" part states the design along GRRAS and GUILD.

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
    OBJECT_DECISIONS,
    VALUE_DECISIONS,
    check,
    in_force,
    layers,
    load_log,
    load_records,
    value_paths,
)
from review_sample import REVIEW_PROTOCOL

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
RULE_KEYS = ("confirmation_rule_fields", "confirmation_rule_routes")
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
UNDER_PROPOSALS = (
    "Agreement under proposals, not blind agreement: both reviewers decide with "
    "the rule values in view, and the second does not see the first reviewer's "
    "decisions. The operator wrote the reading rules whose values are judged and "
    "the decision rule, and reviews as a person; where the operator is one of the "
    "two reviewers, the figure is the agreement of the rules' author with a second "
    "person on the output of the author's own rules."
)
RULE_DERIVATION = (
    "A class may confirm only when it was fixed admissible, the code it was fixed "
    "on is unchanged, at least min_judged_objects objects (entries) carry a judged "
    "value (claim) of it, and its judged values reach min_judged_values = "
    "ceil(ln(holm_floor) / ln(threshold)), holm_floor = alpha / m over the m "
    "admissible classes: the smallest n at which n values without an error give an "
    "exact one-sided Clopper-Pearson lower bound above the threshold at the "
    "strictest Holm level, since threshold ** n is then the exact p-value. Its "
    "p-value is the larger of the exact binomial tail P(X >= right | n, threshold), "
    "which treats values as independent, and the bootstrap over objects within "
    "strata, which carries clustering and weights but cannot see an error-free "
    "class; Holm's step-down at level alpha decides over all m. "
    "lower_bound_if_all_right is the exact bound at holm_floor a class with its "
    "judged values would reach without an error, the highest threshold it could "
    "pass."
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


def krippendorff_alpha(pairs: list[tuple]) -> float | None:
    """Krippendorff's alpha of two coders on nominal data, every unit coded by
    both: 1 - (n - 1)(n - sum o_cc) / (n^2 - sum n_c^2) over the n = 2N
    pairable values, o_cc the coincidences within a category and n_c its
    marginal; None when every value falls in one category."""
    n = 2 * len(pairs)
    margins = Counter(a for a, _ in pairs) + Counter(b for _, b in pairs)
    expected = n * n - sum(v * v for v in margins.values())
    if not expected:
        return None
    same = 2 * sum(a == b for a, b in pairs)
    return 1 - (n - 1) * (n - same) / expected


def alpha_interval(clusters: list[list[tuple]]) -> dict | None:
    """95 % percentile interval of alpha, resampling whole objects (clusters of
    pairs); draws in which alpha is undefined are left out and counted."""
    clusters = [c for c in clusters if c]
    if not clusters:
        return None
    rng = random.Random(BOOTSTRAP_SEED)
    stats = []
    for _ in range(BOOTSTRAP_ROUNDS):
        value = krippendorff_alpha(
            [p for c in rng.choices(clusters, k=len(clusters)) for p in c]
        )
        if value is not None:
            stats.append(value)
    return {"interval95": percentile(sorted(stats)), "defined_draws": len(stats)}


def two_raters(pairs: list[tuple], clusters: list[list[tuple]] | None = None) -> dict:
    """Agreement of two ratings of the same items: raw agreement, Cohen's
    kappa, Krippendorff's alpha with an interval over objects (clusters; each
    pair its own without them), positive and negative specific agreement per
    category, and the table of pairs."""
    out = kappa(pairs)
    alpha = krippendorff_alpha(pairs)
    out["alpha"] = None if alpha is None else round(alpha, 3)
    out["alpha_objects_resampled"] = alpha_interval(
        clusters if clusters is not None else [[p] for p in pairs]
    )
    out["specific_agreement"] = {
        str(c): {
            "positive": positive_agreement(pairs, c)["value"],
            "negative": positive_agreement([(a == c, b == c) for a, b in pairs], False)[
                "value"
            ],
        }
        for c in sorted({x for p in pairs for x in p}, key=str)
    }
    out["table"] = {f"{a}|{b}": k for (a, b), k in sorted(Counter(pairs).items())}
    return out


def binomial_tail(hits: int, n: int, p: float) -> float:
    """P(X >= hits) for X ~ Binomial(n, p), summed in log space."""
    if hits <= 0 or p >= 1:
        return 1.0
    if p <= 0 or hits > n:
        return 0.0
    lp, lq = math.log(p), math.log1p(-p)
    terms = [
        math.lgamma(n + 1)
        - math.lgamma(k + 1)
        - math.lgamma(n - k + 1)
        + k * lp
        + (n - k) * lq
        for k in range(hits, n + 1)
    ]
    top = max(terms)
    return min(1.0, math.exp(top) * sum(math.exp(t - top) for t in terms))


def exact_lower_bound(hits: int, n: int, level: float) -> float | None:
    """The one-sided Clopper-Pearson lower bound at level: the p at which
    P(X >= hits | n, p) = level; for hits = n it is level ** (1 / n)."""
    if n == 0:
        return None
    if hits == 0:
        return 0.0
    if hits == n:
        return level ** (1 / n)
    low, high = 0.0, 1.0
    for _ in range(60):
        mid = (low + high) / 2
        if binomial_tail(hits, n, mid) < level:
            low = mid
        else:
            high = mid
    return low


def minimum_values(threshold: float | None, level: float) -> int | None:
    """The smallest n at which n values without an error pass the exact test at
    level: threshold ** n <= level. None without a threshold or at 1, which
    nothing can exceed."""
    if threshold is None or threshold >= 1:
        return None
    return math.ceil(math.log(level) / math.log(threshold))


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

    values, clusters, one_only, missing, boundary, both_reviewed = [], [], 0, [], [], 0
    for oid in sorted(subset):
        a, b = on(first, oid), on(second, oid)
        if not a or not b or oid not in objects:
            continue
        both_reviewed += 1
        va = {k: d for k, d in a.items() if k[1] == "value"}
        vb = {k: d for k, d in b.items() if k[1] == "value"}
        pairs = [(va[k].decision, vb[k].decision) for k in sorted(set(va) & set(vb))]
        values += pairs
        clusters.append(pairs)
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
        "on what both decided: on value decisions (all three kinds, and each kind "
        "against the others) raw agreement, Cohen's kappa, Krippendorff's alpha with "
        "an interval from resampling objects, positive and negative specific agreement "
        "per category and the table of pairs (first|second); the same on objects both "
        "marked complete for whether a missing value was added, and on objects both "
        "reviewed for whether a boundary was marked.",
        "conditions": UNDER_PROPOSALS,
        "subset_objects": len(subset),
        "objects_both_reviewed": both_reviewed,
        "values": two_raters(values, clusters),
        "values_by_kind": {
            kind: kappa([(x == kind, y == kind) for x, y in values])
            for kind in VALUE_KINDS
        },
        "values_decided_by_one_only": one_only,
        "missing": two_raters(missing),
        "boundary": two_raters(boundary),
    }


def consistency(log: list, layer: dict, status: dict, repeat_set) -> dict:
    """Each hidden repeat against the same reviewer's first decision in force on
    the value: intra-rater consistency under the same proposals. A repeat
    outside the protocol's repeat set, or one whose first decision stands
    after it in the log (made or revised later), enters no figure."""
    force = in_force(log)
    position = {d.id: i for i, d in enumerate(log)}
    clusters: dict[tuple, list] = defaultdict(list)
    hours, outside, first_later = [], set(), 0
    for (reviewer, oid, path), rep in sorted(layer["repeats"].items()):
        if status.get(rep.id):
            continue
        if repeat_set is not None and oid not in repeat_set:
            outside.add(oid)
            continue
        first = force.get((reviewer, oid, "value", path))
        if first is None or status.get(first.id):
            continue
        if position[first.id] > position[rep.id]:
            first_later += 1
            continue
        clusters[(reviewer, oid)].append((first.decision, rep.decision))
        span = datetime.fromisoformat(rep.at) - datetime.fromisoformat(first.at)
        hours.append(span.total_seconds() / 3600)
    pairs = [p for c in clusters.values() for p in c]
    hours.sort()
    return {
        "about": "The repeat set's second, hidden judgements against the same "
        "reviewer's first, value by value, both under the rule values: intra-rater "
        "consistency (raw agreement, kappa, alpha over objects, specific agreement, "
        "table first|repeat) and the hours between the two.",
        "repeat_set": None if repeat_set is None else len(repeat_set),
        "reviewers": sorted({r for r, _ in clusters}),
        "objects": len(clusters),
        "values": two_raters(pairs, list(clusters.values())),
        "interval_hours": {
            "min": round(hours[0], 2),
            "median": round(hours[len(hours) // 2], 2),
            "max": round(hours[-1], 2),
        }
        if hours
        else None,
        "outside_repeat_set": sorted(outside),
        "first_decision_after_repeat": first_later,
    }


def protocol_check(plan: dict | None, design: dict) -> dict:
    """Whether the protocol orders exactly the frozen samples."""
    if plan is None:
        return {"state": "missing: review_sample.py --protocol", "problems": []}
    first, second = plan["queues"]["first"], plan["queues"]["second"]
    problems = []
    shown = set(design["review"]) | set(design.get("hard", {}))
    if set(first) != shown or len(first) != len(shown) + len(plan["repeat"]):
        problems.append(
            "the first queue does not show the review sample and the hard stratum "
            "once each and each repeat object twice"
        )
    if sorted(second) != sorted(design.get("second", ())):
        problems.append("the second queue is not the marked subset")
    if not set(plan["repeat"]) <= set(design["review"]):
        problems.append("the repeat set lies outside the review sample")
    return {
        "state": "failed" if problems else "ok",
        "problems": problems,
        "seed": plan["seed"],
        "repeat_set": len(plan["repeat"]),
        "repeat_gap": plan["repeatGap"],
    }


def order_followed(log: list, layer: dict, plan: dict | None) -> dict:
    """Per reviewer and queue, the share of pairs of objects whose first
    decisions came in the order of the queue (1.0 in order, 0.5 unrelated)."""
    if plan is None:
        return {}
    rank = {
        name: {o: i for i, o in reversed(list(enumerate(queue)))}
        for name, queue in plan["queues"].items()
    }
    seen: dict[tuple, list] = defaultdict(list)
    met = set()
    for d in log:
        if d.repeat or d.decision in ("withdraw", "adjudicate"):
            continue
        roles = layer["order"].get(d.object, [])[:2]
        if d.reviewer not in roles or (d.reviewer, d.object) in met:
            continue
        met.add((d.reviewer, d.object))
        queue = ("first", "second")[roles.index(d.reviewer)]
        if d.object in rank[queue]:
            seen[(d.reviewer, queue)].append(rank[queue][d.object])
    out: dict[str, dict] = defaultdict(dict)
    for (reviewer, queue), ranks in sorted(seen.items()):
        pairs = len(ranks) * (len(ranks) - 1) // 2
        ordered = sum(
            1
            for i in range(len(ranks))
            for j in range(i + 1, len(ranks))
            if ranks[i] < ranks[j]
        )
        out[reviewer][queue] = {
            "objects": len(ranks),
            "pairs_in_queue_order": ratio(ordered, pairs),
        }
    return dict(out)


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
        least = rule.get("minJudgedObjects")
        if type(least) is not int or least < 1:
            raise ValueError(f"{path}: {name}.minJudgedObjects must be an integer >= 1")
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


def class_counts(units: list[tuple]) -> dict:
    """Right and judged values and the objects with a judged value, for units
    that hold whole counts."""
    return {
        "right": sum(h for _, _, h, _ in units),
        "judged": sum(n for _, _, _, n in units),
        "objects": sum(1 for u in units if u[3]),
    }


def decide(
    rule: dict,
    classes: dict[str, list[tuple]],
    code_now: str | None,
    counts: dict[str, dict] | None = None,
) -> dict:
    """The decision rule over measured classes (class -> units; counts gives
    the whole counts where the units hold weighted ones). Only admissible
    classes may confirm, only with a threshold set, the code unchanged and the
    minimum objects and values reached (RULE_DERIVATION)."""
    threshold = rule.get("threshold")
    alpha = rule.get("alpha", 0.025)
    admissible = list(rule.get("admissible", []))
    least_objects = rule.get("minJudgedObjects")
    holm_floor = alpha / max(1, len(admissible))
    least_values = minimum_values(threshold, holm_floor)
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
    elif type(least_objects) is not int or least_objects < 1:
        state = "incomplete: minJudgedObjects is not set; nothing may confirm"
    else:
        state = f"set to {threshold}"
    counts = counts or {}
    report, whole = {}, {}
    for name in sorted(set(classes) | set(admissible)):
        units = classes.get(name, [])
        c = whole[name] = counts.get(name) or class_counts(units)
        entry = weighted(units)
        bound = exact_lower_bound(c["right"], c["judged"], holm_floor)
        entry.update(
            right=c["right"],
            judged_values=c["judged"],
            judged_objects=c["objects"],
            exact_lower_bound_at_holm_floor=None if bound is None else round(bound, 4),
            lower_bound_if_all_right=round(holm_floor ** (1 / c["judged"]), 4)
            if c["judged"]
            else None,
            admissible=name in admissible,
        )
        report[name] = entry
    may = []
    if state.startswith("set"):
        pvalues = {}
        for name in admissible:
            entry, c = report[name], whole[name]
            short = []
            if c["objects"] < least_objects:
                short.append(f"fewer than {least_objects} judged objects")
            if least_values is None or c["judged"] < least_values:
                short.append(f"fewer than {least_values} judged values")
            exact = binomial_tail(c["right"], c["judged"], threshold)
            draws = stratified_draws(classes.get(name, []), RULE_ROUNDS)
            below = sum(1 for s in draws if s <= threshold)
            boot = (1 + below) / (1 + len(draws)) if draws else 1.0
            pvalues[name] = 1.0 if short else max(exact, boot)
            entry.update(
                below_minimum=short,
                p_exact=round(exact, 6),
                p_bootstrap=round(boot, 6),
                p_value=round(pvalues[name], 6),
            )
        may = sorted(holm(pvalues, alpha))
        for name in admissible:
            report[name]["may_confirm"] = name in may
    return {
        "threshold": threshold,
        "alpha": alpha,
        "correction": "holm",
        "state": state,
        "admissible": len(admissible),
        "derivation": {
            "about": RULE_DERIVATION,
            "m": len(admissible),
            "holm_floor": round(holm_floor, 6),
            "min_judged_objects": least_objects,
            "min_judged_values": least_values,
        },
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
    -> volume, stratum, weight), "second" (the subset) and "protocol" (the
    queues and the repeat set, or None)."""
    review, hard, second_subset, plan = (
        design["review"],
        design.get("hard", {}),
        design.get("second", set()),
        design.get("protocol"),
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
        "consistency": consistency(
            log, layer, status, set(plan["repeat"]) if plan else None
        ),
        "protocol": {
            **protocol_check(plan, design),
            "order_followed": order_followed(log, layer, plan),
        },
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
    decided: dict[tuple, dict] = defaultdict(lambda: defaultdict(Counter))
    for row in claim_rows:
        u = units.get(row["sample_id"])
        if u is None or not row.get("decision"):
            continue
        factor = int(row["claims_of_route"]) / int(row["drawn_of_route"])
        grouped[(u["volume"], row["route"])][row["sample_id"]][row["decision"]] += (
            factor
        )
        decided[(u["volume"], row["route"])][row["sample_id"]][row["decision"]] += 1
    classes, counts = {}, {}
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
        # The exact test counts the claims a person decided, not their weights.
        raw = decided[(volume, route)]
        counts[f"{route}@{volume}"] = {
            "right": sum(c["right"] for c in raw.values()),
            "judged": sum(c["right"] + c["wrong"] for c in raw.values()),
            "objects": sum(1 for c in raw.values() if c["right"] + c["wrong"]),
        }
    return {
        "phase1": phase1,
        "phase2": dict(phase2),
        "anchoring": anchoring(units, answers, claim_rows),
        "_classes": classes,
        "_counts": counts,
    }


def mcnemar_exact(b: int, c: int) -> float | None:
    """Two-sided exact McNemar p-value over the b + c discordant pairs."""
    if b + c == 0:
        return None
    return min(1.0, 2 * (1 - binomial_tail(min(b, c) + 1, b + c, 0.5)))


def anchoring(units: dict, answers: dict, claim_rows: list[dict]) -> dict:
    """Phase 2 claim by claim against what the same person's blind answer on
    the same entry implies: a claim is right blind when the answer named its
    wiki page, wrong when it named another page or none. Claims whose entry
    was answered unsure or not at all, or which phase 2 marked unsure, leave
    the table and are counted."""
    by_route: dict[str, list] = defaultdict(list)
    left = Counter()
    for row in claim_rows:
        sid, decision = row["sample_id"], row.get("decision")
        if sid not in units or not decision:
            continue
        answer = answers.get(sid)
        if answer is None or answer[0] == "unsure":
            left["no_blind_answer"] += 1
            continue
        if decision == "unsure":
            left["unsure_in_phase_2"] += 1
            continue
        page = str(row.get("wiki_page") or "")
        blind = "right" if answer[0] == "page" and page == str(answer[1]) else "wrong"
        by_route[row["route"]].append((sid, blind, decision))

    def table(rows: list[tuple]) -> dict:
        cells = Counter((blind, seen) for _, blind, seen in rows)
        a, b = cells[("right", "right")], cells[("wrong", "right")]
        c, d = cells[("right", "wrong")], cells[("wrong", "wrong")]
        n = a + b + c + d
        entries: dict[str, list] = defaultdict(list)
        for sid, blind, seen in rows:
            entries[sid].append((blind, seen))
        clusters = list(entries.values())
        rng = random.Random(BOOTSTRAP_SEED)
        draws = []
        for _ in range(BOOTSTRAP_ROUNDS) if clusters else ():
            pairs = [p for x in rng.choices(clusters, k=len(clusters)) for p in x]
            gained = sum(1 for p in pairs if p == ("wrong", "right"))
            lost = sum(1 for p in pairs if p == ("right", "wrong"))
            draws.append((gained - lost) / len(pairs))
        exact = mcnemar_exact(b, c)
        return {
            "claims": n,
            "entries": len(clusters),
            "table": {
                "right_blind_right_seen": a,
                "wrong_blind_right_seen": b,
                "right_blind_wrong_seen": c,
                "wrong_blind_wrong_seen": d,
            },
            "accepted_blind": ratio(a + c, n),
            "accepted_seen": ratio(a + b, n),
            "effect": ratio(b - c, n),
            "effect_interval95_entries_resampled": percentile(sorted(draws)),
            "accepted_against_blind": ratio(b, b + d),
            "mcnemar_exact_p": None if exact is None else round(exact, 4),
        }

    identity = [r for route in ROUTES for r in by_route.get(route, [])]
    return {
        "about": "Anchoring: the same person's decisions on the same claims without "
        "and with the proposal in view. effect = accepted_seen - accepted_blind, the "
        "share of claims the proposal phase accepts beyond what the person's own blind "
        "answer implies, with an interval from resampling entries and the exact "
        "McNemar test on the discordant claims; accepted_against_blind is the share "
        "of claims the blind answer rejects that phase 2 accepts. Unweighted, since it "
        "describes the person's behaviour on these items. The identity routes form "
        "'all'; containment is shown apart, because its page may rightly differ from "
        "the blind answer's.",
        "all": table(identity),
        "by_route": {route: table(rows) for route, rows in sorted(by_route.items())},
        "left_out": dict(sorted(left.items())),
    }


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
    classes, counts = result.pop("_classes"), result.pop("_counts")
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
            counts,
        ),
    }


def reporting(report: dict) -> dict:
    """The design and the actual numbers along GRRAS (Kottner et al. 2011) for
    the reviews, and along GUILD (Gilbert et al. 2018) for the concordance as a
    linkage of records; only the items a local measurement report can fill,
    keyed by item number."""
    import p09_human_sample as p09
    import review_sample as rs

    figures, agree, again = (
        report["figures"],
        report["agreement"],
        report["consistency"],
    )
    conc, plan = report["concordance"], report["protocol"]
    rules = {k: report.get(k) or conc.get(k) or {} for k in RULE_KEYS}
    return {
        "about": "Reporting fields along the Guidelines for Reporting Reliability and "
        "Agreement Studies (Kottner et al. 2011, J Clin Epidemiol 64: 96-106) and, for "
        "the concordance, the GUidance for Information about Linking Data sets "
        "(Gilbert et al. 2018, J Public Health 40: 191-198), by item number. Items "
        "that belong to a publication (GRRAS 1, 5 and 14; GUILD steps 1, 3 and 4 and "
        "disclosure control) are left to it.",
        "grras": {
            "2 device": {
                "value_decisions": list(VALUE_DECISIONS),
                "object_decisions": list(OBJECT_DECISIONS),
                "definitions": "pipeline/print_volumes/_review.py",
            },
            "3 subjects": "print objects of volumes I, A1 and A2 as the reading rules "
            "read them: the review sample (entries rule development has not seen), its "
            "stratum of hard entries (a p10 violation or a listed exception), and for "
            "the concordance the entries of both blind samples",
            "4 raters": UNDER_PROPOSALS,
            "6 sample size": {
                "review_objects_per_part": rs.PER_PART,
                "hard_entries_per_volume": rs.HARD_PER_VOLUME,
                "second_subset": rs.SECOND_SIZE,
                "repeat_set": rs.REPEAT_SIZE,
                "blind_entries_per_stratum": p09.PER_STRATUM,
                "claims_per_route_and_volume": p09.TARGET_CLAIMS,
                "raters_planned": "two reviewers and an adjudicator",
                "basis": "fixed by the measurement design, not by a power "
                "calculation; the decision rule states the sample a class needs",
                "decision_rule": {
                    k: rules[k].get("derivation") for k in RULE_KEYS if rules[k]
                },
            },
            "7 sampling": "random with recorded seeds: the review sample stratified "
            f"by volume and part (seed {rs.SEED}), the hard stratum by volume "
            f"(seed {rs.HARD_SEED}), the second subset allocated to the volumes in "
            f"proportion (seed {rs.SECOND_SEED}), the repeat set from the review "
            f"sample (seed {rs.PROTOCOL_SEED}); the blind samples stratified by volume "
            f"and proposal (seeds {p09.SEED} and {p09.SUPPLEMENT_SEED})",
            "8 rating process": {
                "proposals_in_view": "fields: yes, the rule values; concordance: "
                "no in phase 1, yes in phase 2",
                "order": "the review queues shuffled with seed "
                f"{rs.PROTOCOL_SEED} (protocol); the blind sheets with their drawing "
                f"seeds, the claim sheet with seed {p09.CLAIMS_SEED}",
                "order_followed": plan.get("order_followed"),
                "repeat": f"each repeat object shown again at least {rs.REPEAT_GAP} "
                "places later, unmarked and without its earlier decisions",
                "repeat_interval_hours": again["interval_hours"],
                "aware_of_comparison": "yes: the viewer names the review sample",
                "anchoring": "concordance.anchoring: phase 2 against the same "
                "person's blind answers on the same entries",
            },
            "9 independence": "the second reviewer reads only their own decisions "
            "(the reviewer filter of the review server); both read the rule values; "
            "a third person or the operator adjudicates after both",
            "10 statistics": "precision with Wilson and object-resampled intervals and "
            "Horvitz-Thompson weights by part; agreement and consistency as raw "
            "agreement, Cohen's kappa, Krippendorff's alpha (nominal) with an "
            "object-resampled interval, and positive and negative specific agreement; "
            "anchoring as a paired difference with an entry-resampled interval and "
            f"the exact McNemar test; bootstrap seed {BOOTSTRAP_SEED}, "
            f"{BOOTSTRAP_ROUNDS} rounds; Python standard library",
            "11 actual numbers": {
                "reviewers": len(report["reviewers"]),
                "objects_complete_reviewer1": figures["reviewer1"]["complete"],
                "objects_complete_hard": figures["hard"]["complete"],
                "objects_both_reviewed": agree["objects_both_reviewed"],
                "repeat_objects_judged": again["objects"],
                "blind_rows_answered": conc.get("answered"),
                "claims_decided": conc.get("claims_decided"),
            },
            "12 rater characteristics": "not recorded by the code; the operator's "
            "double role is item 4, and the training and experience of every further "
            "reviewer are to be recorded with the round",
            "13 estimates": "every rate carries a 95 % interval, and the decision rule "
            "tests the exact lower bound against the threshold",
            "15 detailed results": "the tables of pairs (agreement, consistency, "
            "anchoring) and the counts per class stand in this report",
        },
        "guild": {
            "2a(iii) algorithm": "rule-based routes of p07 (field, title-year, "
            "alignment, containment); several candidates per entry stay proposed "
            "claims, and the claim sheet lists at most "
            f"{p09.CLAIMS_PER_ENTRY} per entry and route",
            "2b record-level indicators": "every claim carries its route, evidence "
            "and state in the claims of p07",
            "2c(i) linked and unlinked": "data/print/derived/reports/p07b_overlap.json, "
            "per volume and part",
            "2d(i) error rates": "false matches as claim precision (phase 2), missed "
            "matches as recall and found_by_neither_route (phase 1), per route and "
            "volume",
            "2d(ii) how estimated": "against a person's blind answers on frozen "
            "samples, weighted by the inverse inclusion probability; silver pairs are a "
            "development metric only",
        },
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
    plan = (
        json.loads(REVIEW_PROTOCOL.read_text("utf-8"))
        if REVIEW_PROTOCOL.exists()
        else None
    )
    return {"review": review, "hard": hard, "second": second, "protocol": plan}


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
        report["reporting"] = reporting(report)
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
    on_correct = a["values"]["specific_agreement"].get("correct", {})
    print(
        f"OK agreement under proposals on {a['objects_both_reviewed']} of "
        f"{a['subset_objects']} subset objects: values kappa {a['values']['kappa']}, "
        f"alpha {a['values']['alpha']} (n {a['values']['n']}), specific agreement on "
        f"correct {on_correct.get('positive')} / {on_correct.get('negative')}"
    )
    k, plan = report["consistency"], report["protocol"]
    print(
        f"OK protocol {plan['state']}; consistency on {k['objects']} repeat objects: "
        f"alpha {k['values']['alpha']} (n {k['values']['n']})"
    )
    c = report["concordance"]
    anchor = (c.get("anchoring") or {}).get("all") or {}
    print(
        f"OK concordance: {c.get('answered')} of {c.get('rows')} blind rows answered, "
        f"{c.get('claims_decided')} claims decided; anchoring effect "
        f"{anchor.get('effect')} on {anchor.get('claims')} claims"
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
