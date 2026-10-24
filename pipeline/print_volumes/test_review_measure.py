"""Tests of the measurement contract of p13_review.py on invented records and decisions."""

import csv
import hashlib
import json

import pytest
from _review import (
    Correction,
    DecisionIn,
    ValueRef,
    adjudication_problem,
    effective,
    in_force,
    layers,
    stamp,
    value_paths,
)
from p13_review import (
    ABOUT,
    blind_units,
    bootstrap,
    concordance,
    decide,
    holm,
    kappa,
    load_rule,
    measure,
    positive_agreement,
    stratified_draws,
    weighted,
    wilson,
)

TEXT = "Der Weg. Wien 1950"
PATHS = ("title", "imprints[0].year", "types[0]")
UNSET = {"threshold": None, "admissible": [], "fixed": None}
RULE = {"fields": UNSET, "routes": UNSET}


def _records(n: int = 6, part: str = "F") -> dict:
    records = {}
    for i in range(1, n + 1):
        eid = f"I/{part}/{i}"
        sha = hashlib.sha256(TEXT.encode("utf-8")).hexdigest()
        obj = {
            "id": f"{eid}#1",
            "entry": eid,
            "entry_sha256": sha,
            "volume": "I",
            "part": part,
            "address": f"{part} {i}",
            "span": [0, len(TEXT)],
            "text": TEXT,
            "title": {
                "value": "Der Weg",
                "span": [0, 7],
                "by": "rule",
                "rule": "p03.title",
            },
            "imprints": [
                {
                    "year": {
                        "value": 1950,
                        "span": [14, 18],
                        "by": "rule",
                        "rule": "p03.year",
                    }
                }
            ],
            "types": [
                {
                    "value": "book_edition",
                    "span": [0, 7],
                    "by": "rule",
                    "rule": "p03.type",
                }
            ],
        }
        records[eid] = {
            "id": eid,
            "volume": "I",
            "text": TEXT,
            "sha256": sha,
            "objects": [obj],
        }
    return records


def _decide(records, oid, decision, path=None, reviewer="A", correction=None, **extra):
    record = records[oid.split("#")[0]]
    obj = record["objects"][0]
    target = None
    if path:
        v = value_paths(obj)[path]
        target = ValueRef(
            path=path, value=v["value"], span=v["span"], source=obj["entry"]
        )
    return stamp(
        DecisionIn(
            object=oid,
            entry_sha256=record["sha256"],
            reviewer=reviewer,
            decision=decision,
            target=target,
            correction=correction,
            **extra,
        )
    )


def _review_all(records, oid, reviewer="A", wrong=(), open_=()):
    """Decide every value of an object, correcting the paths in wrong and
    leaving those in open_ unresolved, then complete it."""

    def kind(p):
        return "correct" if p in wrong else "unresolved" if p in open_ else "confirm"

    out = [
        _decide(
            records,
            oid,
            kind(p),
            p,
            reviewer,
            Correction() if p in wrong else None,
        )
        for p in PATHS
    ]
    return out + [_decide(records, oid, "complete", reviewer=reviewer)]


def _design(review, hard=(), second=(), weights=None):
    weights = weights or {}
    return {
        "review": {
            o: {
                "volume": "I",
                "stratum": f"I/{o.split('/')[1]}",
                "weight": weights.get(o, 1.0),
            }
            for o in review
        },
        "hard": {o: {"volume": "I", "stratum": "hard/I", "weight": 1.0} for o in hard},
        "second": set(second),
    }


def _measure(records, log, review, **kw):
    return measure(records, log, _design(review, **kw), RULE)


def test_precision_per_value_and_per_object():
    records = _records()
    log = (
        _review_all(records, "I/F/1#1")
        + _review_all(records, "I/F/2#1", wrong=("title",))
        + _review_all(records, "I/F/3#1")
    )
    sample = ["I/F/1#1", "I/F/2#1", "I/F/3#1"]
    row = _measure(records, log, sample)["figures"]["reviewer1"]["overall"]["all"]
    assert (row["confirmed"], row["corrected"]) == (8, 1)
    assert row["precision"] == round(8 / 9, 3)
    assert row["interval95"] == wilson(8, 9)
    assert (row["objects_judged"], row["objects_without_correction"]) == (3, 2)
    assert row["object_precision"] == round(2 / 3, 3)
    low, high = row["interval95_objects_resampled"]
    assert low <= row["precision"] <= high
    again = _measure(records, log, sample)["figures"]["reviewer1"]["overall"]["all"]
    assert again["interval95_objects_resampled"] == row["interval95_objects_resampled"]


def test_resampling_objects_widens_the_interval_when_errors_cluster():
    per_object = [(10, 10)] * 9 + [(0, 10)]
    resampled = bootstrap(per_object)
    assert resampled[0] < wilson(90, 100)[0]
    assert bootstrap(per_object) == resampled
    assert bootstrap([(0, 0)]) is None


def test_incomplete_and_unmarked_objects_do_not_count():
    records = _records()
    log = _review_all(records, "I/F/1#1")[:-1]
    log += [
        _decide(records, "I/F/2#1", "confirm", "title"),
        _decide(records, "I/F/2#1", "complete"),
    ]
    fig = _measure(records, log, ["I/F/1#1", "I/F/2#1"])["figures"]["reviewer1"]
    assert fig["complete"] == 0
    assert fig["complete_with_undecided_values"] == [
        {"object": "I/F/2#1", "undecided": ["imprints[0].year", "types[0]"]}
    ]
    assert fig["overall"] == {}


def test_decisions_outside_the_samples_are_development_feedback():
    records = _records()
    log = _review_all(records, "I/F/1#1") + _review_all(records, "I/F/4#1", wrong=PATHS)
    report = _measure(records, log, ["I/F/1#1"])
    assert report["figures"]["reviewer1"]["overall"]["all"]["corrected"] == 0
    assert report["development_reviews"] == {"complete": 1, "correct": 3}


# Finding 1: reviewers.
def test_a_second_reviewer_never_replaces_the_first():
    records = _records()
    log = _review_all(records, "I/F/1#1", "A") + _review_all(
        records, "I/F/1#1", "B", wrong=("title",)
    )
    report = _measure(records, log, ["I/F/1#1"], second=["I/F/1#1"])
    figures = report["figures"]
    assert figures["reviewer1"]["overall"]["all"]["corrected"] == 0
    assert figures["reviewer2"]["overall"]["all"]["corrected"] == 1
    assert figures["adjudicated"]["overall"]["all"]["corrected"] == 0
    # The published state is the first reviewer's.
    assert effective(log)[("I/F/1#1", "value", "title")].reviewer == "A"
    assert report["adjudications"]["open_disagreements"] == [
        {
            "object": "I/F/1#1",
            "path": "title",
            "first": log[0].id,
            "second": log[4].id,
        }
    ]


def test_an_adjudication_settles_and_the_published_state_follows_it():
    records = _records()
    first = _review_all(records, "I/F/1#1", "A")
    second = _review_all(records, "I/F/1#1", "B", wrong=("title",))
    settle = _decide(
        records,
        "I/F/1#1",
        "adjudicate",
        "title",
        "C",
        settles=[first[0].id, second[0].id],
        adopts=second[0].id,
    )
    log = first + second + [settle]
    assert adjudication_problem(settle, log) is None
    published = effective(log)[("I/F/1#1", "value", "title")]
    assert published is second[0]
    report = _measure(records, log, ["I/F/1#1"], second=["I/F/1#1"])
    assert report["figures"]["adjudicated"]["overall"]["all"]["corrected"] == 1
    assert report["figures"]["reviewer1"]["overall"]["all"]["corrected"] == 0
    assert report["adjudications"]["valid"] == 1
    assert report["adjudications"]["open_disagreements"] == []


def test_an_adjudication_settles_only_a_disagreement_of_the_first_two_reviewers():
    records = _records()
    first = _review_all(records, "I/F/1#1", "A")
    second = _review_all(records, "I/F/1#1", "B", wrong=("title",))
    third = [_decide(records, "I/F/1#1", "confirm", "title", "D")]
    log = first + second + third

    def adj(reviewer, settles, adopts, path="title"):
        return _decide(
            records,
            "I/F/1#1",
            "adjudicate",
            path,
            reviewer,
            settles=settles,
            adopts=adopts,
        )

    pair = [first[0].id, second[0].id]
    assert "neither" in adjudication_problem(adj("A", pair, pair[0]), log)
    assert "nothing to settle" in adjudication_problem(
        adj("C", [first[1].id, second[1].id], first[1].id, "imprints[0].year"), log
    )
    assert "first and the second" in adjudication_problem(
        adj("C", [first[0].id, third[0].id], first[0].id), log
    )
    assert "value it names" in adjudication_problem(
        adj("C", pair, pair[0], "types[0]"), log
    )
    # B revises the title: the adjudication of the old disagreement is stale.
    revised = _decide(records, "I/F/1#1", "confirm", "title", "B")
    assert "stale" in adjudication_problem(adj("C", pair, pair[0]), [*log, revised])
    with pytest.raises(ValueError):
        adj("C", [pair[0], pair[0]], pair[0])
    with pytest.raises(ValueError):
        adj("C", pair, "0" * 32)


def test_an_adjudication_adds_a_missing_value_of_the_second_reviewer():
    records = _records()
    added = Correction(field="imprints.place", value="Wien", span=[9, 13])
    first = _review_all(records, "I/F/1#1", "A")
    second = _review_all(records, "I/F/1#1", "B") + [
        _decide(records, "I/F/1#1", "missing", reviewer="B", correction=added)
    ]
    settle = _decide(
        records,
        "I/F/1#1",
        "adjudicate",
        reviewer="C",
        settles=[first[-1].id, second[-1].id],
        adopts=second[-1].id,
    )
    log = first + second + [settle]
    figures = _measure(records, log, ["I/F/1#1"], second=["I/F/1#1"])["figures"]
    assert figures["reviewer1"]["overall"]["all"]["missing"] == 0
    assert figures["adjudicated"]["overall"]["all"]["missing"] == 1


def test_a_reviewer_withdraws_only_their_own_decisions():
    records = _records()
    mine = _decide(records, "I/F/1#1", "confirm", "title", "A")
    foreign = _decide(records, "I/F/1#1", "withdraw", reviewer="B", supersedes=mine.id)
    assert ("A", "I/F/1#1", "value", "title") in in_force([mine, foreign])
    own = _decide(records, "I/F/1#1", "withdraw", reviewer="A", supersedes=mine.id)
    assert in_force([mine, own]) == {}


def test_the_first_reviewer_is_who_decided_the_object_first():
    records = _records()
    log = [
        _decide(records, "I/F/1#1", "confirm", "title", "B"),
        _decide(records, "I/F/1#1", "confirm", "title", "A"),
        _decide(records, "I/F/2#1", "confirm", "title", "A"),
    ]
    order = layers(log)["order"]
    assert order == {"I/F/1#1": ["B", "A"], "I/F/2#1": ["A"]}


# Finding 3: weights.
def test_the_weighted_estimate_follows_the_part_sizes():
    # Part G is large and right, part H small and wrong; unweighted they tie.
    records = {**_records(2, "G"), **_records(2, "H")}
    log = (
        _review_all(records, "I/G/1#1")
        + _review_all(records, "I/G/2#1")
        + _review_all(records, "I/H/1#1", wrong=PATHS)
        + _review_all(records, "I/H/2#1", wrong=PATHS)
    )
    sample = ["I/G/1#1", "I/G/2#1", "I/H/1#1", "I/H/2#1"]
    weights = {"I/G/1#1": 99.0, "I/G/2#1": 99.0, "I/H/1#1": 1.0, "I/H/2#1": 1.0}
    fig = _measure(records, log, sample, weights=weights)["figures"]["reviewer1"]
    assert fig["overall"]["all"]["precision"] == 0.5
    w = fig["weighted"]["all"]["precision"]
    assert w["estimate"] == 0.99
    # Within-part resampling keeps both parts; the estimate cannot move.
    assert w["interval95"] == [0.99, 0.99]


def test_the_stratified_bootstrap_pools_single_unit_strata():
    units = [("a", 1.0, 1, 1), ("b", 1.0, 0, 1), ("c", 2.0, 1, 1), ("c", 2.0, 1, 1)]
    draws = stratified_draws(units, rounds=200, seed=1)
    assert min(draws) < max(draws)  # a and b vary once pooled
    assert stratified_draws(units, rounds=200, seed=1) == draws
    assert weighted([])["estimate"] is None


def test_pool_sizes_give_the_weights(tmp_path, monkeypatch):
    import p13_review

    sample = tmp_path / "review.json"
    pools = tmp_path / "pools.json"
    sample.write_text(json.dumps({"objects": {"I": {"F": ["I/F/1#1", "I/F/2#1"]}}}))
    pools.write_text(
        json.dumps({"parts": {"I": {"F": {"entries": 50, "hard": 4, "drawn": 2}}}})
    )
    monkeypatch.setattr(p13_review, "REVIEW_SAMPLE", sample)
    monkeypatch.setattr(p13_review, "REVIEW_POOLS", pools)
    monkeypatch.setattr(p13_review, "REVIEW_HARD", tmp_path / "absent.json")
    monkeypatch.setattr(p13_review, "REVIEW_SECOND", tmp_path / "absent.json")
    design = p13_review.load_design()
    assert design["review"]["I/F/1#1"] == {
        "volume": "I",
        "stratum": "I/F",
        "weight": 23.0,
    }


# Finding 4: hard entries.
def test_hard_entries_are_reported_apart_and_join_the_population():
    records = _records(3)
    log = (
        _review_all(records, "I/F/1#1")
        + _review_all(records, "I/F/2#1")
        + _review_all(records, "I/F/3#1", wrong=PATHS)
    )
    report = _measure(records, log, ["I/F/1#1", "I/F/2#1"], hard=["I/F/3#1"])
    assert report["figures"]["reviewer1"]["overall"]["all"]["corrected"] == 0
    assert report["figures"]["hard"]["overall"]["all"]["corrected"] == 3
    population = report["population"]["weighted"]["all"]["precision"]
    assert population["estimate"] == round(6 / 9, 3)


# Finding 5: pessimistic precision and recall.
def test_unresolved_count_as_wrong_and_misses_lower_the_recall():
    records = _records()
    added = Correction(field="imprints.place", value="Wien", span=[9, 13])
    log = _review_all(records, "I/F/1#1", wrong=("title",), open_=("types[0]",)) + [
        _decide(records, "I/F/1#1", "missing", correction=added)
    ]
    row = _measure(records, log, ["I/F/1#1"])["figures"]["reviewer1"]["overall"]["all"]
    assert row["precision"] == 0.5  # 1 confirmed of 2 judged
    assert row["precision_unresolved_as_wrong"] == round(1 / 3, 3)
    assert row["recall"] == round(1 / 3, 3)  # 1 / (1 + 1 corrected + 1 missing)


# Finding 6: boundary.
def test_an_object_with_a_wrong_boundary_leaves_the_field_figures():
    records = _records()
    log = (
        _review_all(records, "I/F/1#1")
        + _review_all(records, "I/F/2#1", wrong=PATHS)
        + [_decide(records, "I/F/2#1", "boundary", note="two items joined")]
    )
    fig = _measure(records, log, ["I/F/1#1", "I/F/2#1"])["figures"]["reviewer1"]
    assert fig["overall"]["all"]["corrected"] == 0
    assert fig["boundary"]["by_volume"]["I"] == {
        "flagged": 1,
        "reviewed": 2,
        "rate": 0.5,
        "interval95": wilson(1, 2),
    }


# Finding 7: the second reviewer's subset.
def test_agreement_counts_only_the_subset_marked_in_advance():
    records = _records()
    log = (
        _review_all(records, "I/F/1#1", "A")
        + _review_all(records, "I/F/2#1", "A", wrong=("title",))
        + _review_all(records, "I/F/1#1", "B", wrong=("types[0]",))
        + _review_all(records, "I/F/2#1", "B", wrong=("title",))
    )
    sample = ["I/F/1#1", "I/F/2#1"]
    report = _measure(records, log, sample, second=["I/F/1#1"])
    a = report["agreement"]
    assert (a["subset_objects"], a["objects_both_reviewed"]) == (1, 1)
    assert a["values"]["n"] == 3 and a["values"]["observed"] == round(2 / 3, 3)
    assert a["values_positive_agreement"] == {
        "category": "correct",
        "both": 0,
        "one_only": 1,
        "value": 0.0,
    }
    assert report["second_reviewer_outside_subset"]["objects"] == ["I/F/2#1"]
    assert report["figures"]["reviewer2"]["complete"] == 1


def test_cohen_kappa_and_positive_agreement_on_known_tables():
    pairs = [("y", "y")] * 20 + [("y", "n")] * 5 + [("n", "y")] * 10 + [("n", "n")] * 15
    result = kappa(pairs)
    assert (result["n"], result["observed"], result["expected"]) == (50, 0.7, 0.5)
    assert result["kappa"] == 0.4
    assert kappa([("y", "y")] * 3)["kappa"] is None
    assert kappa([])["n"] == 0
    # 2 * 20 / (2 * 20 + 15)
    assert positive_agreement(pairs, "y")["value"] == round(40 / 55, 3)


def test_missing_agreement_on_objects_both_completed():
    records = _records()
    added = Correction(field="imprints.place", value="Wien", span=[9, 13])
    log = (
        _review_all(records, "I/F/1#1", "A")
        + [_decide(records, "I/F/1#1", "missing", reviewer="A", correction=added)]
        + _review_all(records, "I/F/1#1", "B")
    )
    a = _measure(records, log, ["I/F/1#1"], second=["I/F/1#1"])["agreement"]
    assert a["missing"]["n"] == 1 and a["missing"]["observed"] == 0.0


# Finding 8: the blind concordance.
def test_blind_weights_add_the_inclusion_probabilities_of_both_designs():
    key1 = {"s1": {"printId": "I/A/1", "stratum": "field"}}
    sizes1 = {"I": {"field": 100}}
    key2 = {
        "firstSampleStrata": {"s1": "field"},
        "key": {
            "s2": {
                "printId": "I/A/2",
                "stratum": "no-year",
                "firstDesignStratum": "outside",
            }
        },
    }
    sizes2 = {
        "I": {"field": {"pool": 50, "drawn": 5}, "no-year": {"pool": 20, "drawn": 10}}
    }
    units = blind_units(key1, sizes1, key2, sizes2)
    assert units["s1"]["weight"] == pytest.approx(1 / (1 / 100 + 5 / 50))
    assert units["s2"]["weight"] == pytest.approx(2.0)
    assert units["s2"]["stratum"] == "second/I/no-year"


def test_blind_answers_meet_the_current_proposals():
    units = {
        "a": {"entry": "I/A/1", "volume": "I", "stratum": "x", "weight": 1.0},
        "b": {"entry": "I/A/2", "volume": "I", "stratum": "x", "weight": 1.0},
        "c": {"entry": "I/A/3", "volume": "I", "stratum": "y", "weight": 1.0},
        "d": {"entry": "I/A/4", "volume": "I", "stratum": "y", "weight": 1.0},
    }
    answers = {"a": ("page", 7), "b": ("none",), "c": ("page", 9), "d": ("unsure",)}
    proposed = {
        "I/A/1": {"field": {7}},
        "I/A/2": {"field": {8}},
        "I/A/3": {"title-year": {3}},
    }
    rows = [
        {
            "sample_id": "a",
            "route": "field",
            "decision": "right",
            "claims_of_route": "4",
            "drawn_of_route": "2",
        },
        {
            "sample_id": "a",
            "route": "field",
            "decision": "wrong",
            "claims_of_route": "4",
            "drawn_of_route": "2",
        },
        {
            "sample_id": "c",
            "route": "field",
            "decision": "unsure",
            "claims_of_route": "1",
            "drawn_of_route": "1",
        },
    ]
    result = concordance(units, answers, proposed, rows)
    field = result["phase1"]["I"]["routes"]["field"]
    # a proposes the right page, b proposes one where the wiki has none.
    assert (field["entry_precision"]["hits"], field["entry_precision"]["n"]) == (1, 2)
    # a and c have a page; only a's is proposed by the field route.
    assert (field["recall"]["hits"], field["recall"]["n"]) == (1, 2)
    assert result["phase1"]["I"]["found_by_neither_route"]["hits"] == 1
    claims = result["phase2"]["I"]["field"]
    assert claims["claim_precision"]["estimate"] == 0.5
    assert claims["claim_precision_unsure_as_wrong"]["estimate"] == round(2 / 5, 3)


def test_blind_sheet_answers_follow_the_convention(tmp_path):
    from p09_human_sample import SHEET_FIELDS, answers

    sheet = tmp_path / "sheet.csv"
    rows = [
        {"sample_id": "a", "wiki_page": "12", "decision": ""},
        {"sample_id": "b", "wiki_page": "", "decision": "none"},
        {"sample_id": "c", "wiki_page": "", "decision": "Unsure"},
        {"sample_id": "d", "wiki_page": "", "decision": ""},
        {"sample_id": "e", "wiki_page": "12", "decision": "none"},
    ]
    with sheet.open("w", encoding="utf-8", newline="") as sink:
        writer = csv.DictWriter(sink, fieldnames=SHEET_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    found, problems = answers(sheet)
    assert found == {
        "a": ("page", 12),
        "b": ("none",),
        "c": ("unsure",),
        "d": None,
        "e": None,
    }
    assert len(problems) == 1 and "row e" in problems[0]


def test_the_supplement_draws_enough_entries_for_forty_claims():
    from p09_human_sample import supplement_sizes

    def units(n, claims):
        return [{"routes": {"field": [0] * claims}}] * n

    pools = {
        "field": units(100, 2),
        "title-year": units(100, 9),
        "none": [],
        "no-year": units(3, 0),
    }
    sizes = supplement_sizes(pools, {"field": 30, "title-year": 50})
    # 10 field claims missing at 2 per entry; title-year already past 40.
    assert sizes == {"field": 5, "title-year": 0, "none": 0, "no-year": 3}


# Finding 9: the decision rule.
def test_holm_steps_down_and_stops_at_the_first_failure():
    assert holm({"a": 0.001, "b": 0.02, "c": 0.04}, 0.05) == {"a", "b", "c"}
    # b fails 0.05 / 2, so c is not tested although it would pass 0.05 alone.
    assert holm({"a": 0.001, "b": 0.03, "c": 0.04}, 0.05) == {"a"}
    assert holm({"a": 0.06, "b": 0.001}, 0.05) == {"b"}
    assert holm({"a": 0.2}, 0.05) == set()


def test_the_rule_file_has_two_rules_with_null_thresholds(tmp_path):
    rule = load_rule()
    assert set(rule) >= {"fields", "routes"}
    assert rule["fields"]["threshold"] is None and rule["routes"]["threshold"] is None
    path = tmp_path / "rule.json"
    for bad in ("0.9", 1.5, 0, True):
        path.write_text(
            json.dumps(
                {"fields": {"threshold": bad, "admissible": []}, "routes": UNSET}
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError):
            load_rule(path)
    path.write_text(json.dumps({"fields": UNSET}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_rule(path)


GOOD = [(f"I/{i % 5}", 1.0, 10, 10) for i in range(30)]
POOR = [(f"I/{i % 5}", 1.0, 6, 10) for i in range(30)]


def test_nothing_confirms_while_the_threshold_is_null():
    rule = {
        "threshold": None,
        "admissible": ["r@I"],
        "fixed": {"code": {"sha256": "h"}},
    }
    result = decide(rule, {"r@I": GOOD}, "h")
    assert result["state"].startswith("unset: nothing may confirm")
    assert result["may_confirm"] == []


def test_a_set_threshold_admits_only_fixed_classes_on_unchanged_code():
    rule = {
        "threshold": 0.8,
        "alpha": 0.025,
        "admissible": ["good@I", "poor@I"],
        "fixed": {"code": {"sha256": "h"}},
    }
    classes = {"good@I": GOOD, "poor@I": POOR, "late@I": GOOD}
    result = decide(rule, classes, "h")
    assert result["may_confirm"] == ["good@I"]
    assert result["classes"]["late@I"]["admissible"] is False
    assert "may_confirm" not in result["classes"]["late@I"]
    changed = decide(rule, classes, "other")
    assert changed["state"].startswith("invalidated") and changed["may_confirm"] == []
    unfixed = decide({**rule, "fixed": None}, classes, "h")
    assert unfixed["state"].startswith("not fixed") and unfixed["may_confirm"] == []


def test_the_report_rule_is_unset_and_bound_to_the_volume():
    records = _records()
    log = _review_all(records, "I/F/1#1")
    fixed = {
        "threshold": None,
        "admissible": ["p03.title@I"],
        "fixed": {"code": {"sha256": "h"}},
    }
    report = measure(
        records,
        log,
        _design(["I/F/1#1"]),
        {"fields": fixed, "routes": UNSET},
        {"fields": "h"},
    )
    rule = report["confirmation_rule_fields"]
    assert rule["state"].startswith("unset") and rule["may_confirm"] == []
    assert set(rule["classes"]) == {"p03.title@I", "p03.year@I", "p03.type@I"}
    assert rule["classes"]["p03.title@I"]["admissible"] is True


# Finding 11: silver pairs.
def test_the_report_says_silver_pairs_are_a_development_metric():
    assert "development metric" in ABOUT
