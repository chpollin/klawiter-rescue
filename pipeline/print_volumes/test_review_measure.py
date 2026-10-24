"""Tests of the measurement contract of p13_review.py on invented records and decisions."""

import hashlib
import json
from collections import Counter

import pytest
from _review import Correction, DecisionIn, ValueRef, stamp, value_paths
from p13_review import (
    bootstrap,
    kappa,
    load_threshold,
    measure,
    rule_classes,
    wilson,
)

TEXT = "Der Weg. Wien 1950"


def _records(n: int = 4) -> dict:
    records = {}
    for i in range(1, n + 1):
        eid = f"I/F/{i}"
        sha = hashlib.sha256(TEXT.encode("utf-8")).hexdigest()
        obj = {
            "id": f"{eid}#1",
            "entry": eid,
            "entry_sha256": sha,
            "volume": "I",
            "part": "F",
            "address": f"F {i}",
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


PATHS = ("title", "imprints[0].year", "types[0]")


def _decide(records, oid, decision, path=None, reviewer="A", correction=None):
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
        )
    )


def _review_all(records, oid, reviewer="A", wrong=()):
    """Decide every value of an object, correcting the paths in wrong, then complete it."""
    out = [
        _decide(
            records,
            oid,
            "correct" if p in wrong else "confirm",
            p,
            reviewer,
            Correction() if p in wrong else None,
        )
        for p in PATHS
    ]
    return out + [_decide(records, oid, "complete", reviewer=reviewer)]


def test_precision_per_value_and_per_object():
    records = _records()
    log = (
        _review_all(records, "I/F/1#1")
        + _review_all(records, "I/F/2#1", wrong=("title",))
        + _review_all(records, "I/F/3#1")
    )
    sample = {"I/F/1#1", "I/F/2#1", "I/F/3#1"}
    row = measure(records, log, sample, None)["overall"]["all"]
    assert (row["confirmed"], row["corrected"]) == (8, 1)
    assert row["precision"] == round(8 / 9, 3)
    assert row["interval95"] == wilson(8, 9)
    assert (row["objects_judged"], row["objects_without_correction"]) == (3, 2)
    assert row["object_precision"] == round(2 / 3, 3)
    assert row["object_interval95"] == wilson(2, 3)
    low, high = row["interval95_objects_resampled"]
    assert low <= row["precision"] <= high
    # The same seed gives the same interval.
    again = measure(records, log, sample, None)["overall"]["all"]
    assert again["interval95_objects_resampled"] == row["interval95_objects_resampled"]


def test_resampling_objects_widens_the_interval_when_errors_cluster():
    # Ten objects of ten values; every error lies in one object.
    per_object = [(10, 10)] * 9 + [(0, 10)]
    resampled = bootstrap(per_object)
    assert resampled[0] < wilson(90, 100)[0]
    assert bootstrap(per_object) == resampled
    assert bootstrap([(0, 0)]) is None


def test_incomplete_and_unmarked_objects_do_not_count():
    records = _records()
    log = _review_all(records, "I/F/1#1")[:-1]  # decided, not marked complete
    log += [
        _decide(records, "I/F/2#1", "confirm", "title"),
        _decide(records, "I/F/2#1", "complete"),
    ]
    report = measure(records, log, {"I/F/1#1", "I/F/2#1"}, None)
    assert report["sample_complete"] == 0
    assert report["sample_complete_with_undecided_values"] == [
        {"object": "I/F/2#1", "undecided": ["imprints[0].year", "types[0]"]}
    ]
    assert report["overall"] == {}


def test_decisions_outside_the_sample_are_development_feedback():
    records = _records()
    log = _review_all(records, "I/F/1#1") + _review_all(records, "I/F/4#1", wrong=PATHS)
    report = measure(records, log, {"I/F/1#1"}, None)
    assert report["overall"]["all"]["corrected"] == 0
    assert report["development_reviews"] == {"complete": 1, "correct": 3}


def test_cohen_kappa_on_a_known_table():
    pairs = [("y", "y")] * 20 + [("y", "n")] * 5 + [("n", "y")] * 10 + [("n", "n")] * 15
    result = kappa(pairs)
    assert (result["n"], result["observed"], result["expected"]) == (50, 0.7, 0.5)
    assert result["kappa"] == 0.4
    assert kappa([("y", "y")] * 3)["kappa"] is None
    assert kappa([])["n"] == 0


def test_kappa_counts_only_what_both_reviewers_decided():
    records = _records()
    log = (
        _review_all(records, "I/F/1#1", "A")
        + _review_all(records, "I/F/2#1", "A", wrong=("title",))
        # B decides two values of object 1 and object 2 in full, disagreeing once.
        + [
            _decide(records, "I/F/1#1", "confirm", "title", "B"),
            _decide(records, "I/F/1#1", "correct", "types[0]", "B", Correction()),
        ]
        + _review_all(records, "I/F/2#1", "B", wrong=("title",))
        # B alone decides object 3: it never enters kappa.
        + _review_all(records, "I/F/3#1", "B")
    )
    report = measure(records, log, {"I/F/1#1", "I/F/2#1", "I/F/3#1"}, None)
    pair = report["agreement"]["pairs"]["A | B"]
    assert pair["values"]["n"] == 5
    assert pair["values_decided_by_one_only"] == 4
    assert pair["shared_objects"] == 2
    # Agreement on 4 of 5: confirm/confirm x3, correct/correct x1, confirm/correct x1.
    assert pair["values"]["observed"] == 0.8
    assert pair["values_by_kind"]["correct"]["n"] == 5
    assert pair["objects_both_complete"] == 1
    # B's later decisions on the shared values do not replace A's for kappa,
    # but effective() keeps the latest for precision, which the report names.
    assert report["values_decided_by_several_reviewers"] == 5


def test_missing_agreement_on_objects_both_completed():
    records = _records()
    added = Correction(field="imprints.place", value="Wien", span=[9, 13])
    log = (
        _review_all(records, "I/F/1#1", "A")
        + [_decide(records, "I/F/1#1", "missing", reviewer="A", correction=added)]
        + _review_all(records, "I/F/1#1", "B")
    )
    pair = measure(records, log, {"I/F/1#1"}, None)["agreement"]["pairs"]["A | B"]
    assert pair["missing"]["n"] == 1 and pair["missing"]["observed"] == 0.0


def test_the_confirmation_rule_is_unset_by_default_and_read_from_its_file(tmp_path):
    assert load_threshold() is None
    path = tmp_path / "rule.json"
    path.write_text(json.dumps({"threshold": 0.9}), encoding="utf-8")
    assert load_threshold(path) == 0.9
    for bad in ("0.9", 1.5, 0, True):
        path.write_text(json.dumps({"threshold": bad}), encoding="utf-8")
        with pytest.raises(ValueError):
            load_threshold(path)


def test_no_rule_class_confirms_while_the_threshold_is_unset():
    rule = rule_classes({"p03.title": Counter(confirm=50)}, None)
    assert rule["state"].startswith("unset: no rule class may confirm")
    assert rule["may_confirm"] == []
    assert rule["by_rule"]["p03.title"]["may_confirm"] is None


def test_a_set_threshold_admits_a_rule_class_by_its_lower_wilson_bound():
    records = _records()
    log = (
        _review_all(records, "I/F/1#1")
        + _review_all(records, "I/F/2#1", wrong=("title",))
        + _review_all(records, "I/F/3#1")
    )
    sample = {"I/F/1#1", "I/F/2#1", "I/F/3#1"}
    rule = measure(records, log, sample, 0.4)["confirmation_rule"]
    # p03.year 3 of 3: lower bound 0.438; p03.title 2 of 3: lower bound 0.208.
    assert wilson(3, 3)[0] >= 0.4 > wilson(2, 3)[0]
    assert rule["by_rule"]["p03.year"]["may_confirm"] is True
    assert rule["by_rule"]["p03.title"]["may_confirm"] is False
    assert rule["may_confirm"] == ["p03.type", "p03.year"]
