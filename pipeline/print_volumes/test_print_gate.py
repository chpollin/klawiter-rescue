"""Tests of the local print gate (p14_gate.py) on invented data, never print text.

Each failure mode of the gate has a test that passes only while the check
that catches it is in place.
"""

import hashlib
import json

import p14_gate
from p14_gate import (
    blind_row_failures,
    dir_differences,
    input_failures,
    lines_text_hash,
    p10_failures,
    pin_of,
    run_checks,
    sample_failures,
    undo_remaps,
)

FULL = "ab" * 32
VOLUMES = {"X": {"file": "x.pdf", "sha256": "abab"}}


def _p01(text_hash: str = "t" * 64, sha: str = FULL) -> dict:
    return {"X": {"sha256": sha, "text_sha256": text_hash, "pages": 2}}


def test_inputs_pass_when_hash_prefix_and_lines_agree():
    assert input_failures(VOLUMES, {"X": FULL}, _p01(), {"X": "t" * 64}) == []


def test_inputs_fail_on_a_wrong_pdf_hash():
    other = "cd" * 32
    failures = input_failures(VOLUMES, {"X": other}, _p01(sha=other), {"X": "t" * 64})
    assert any("expected abab" in f for f in failures)


def test_inputs_fail_on_a_missing_pdf():
    assert input_failures(VOLUMES, {}, _p01(), {"X": "t" * 64}) == ["X: x.pdf missing"]


def test_inputs_fail_when_p01_read_another_file_or_the_lines_changed():
    assert any(
        "p01 extracted another file" in f
        for f in input_failures(
            VOLUMES, {"X": FULL}, _p01(sha="ab" * 31 + "cd"), {"X": "t" * 64}
        )
    )
    assert any(
        "not p01's output" in f
        for f in input_failures(VOLUMES, {"X": FULL}, _p01(), {"X": "u" * 64})
    )
    assert any(
        "lines file missing" in f
        for f in input_failures(VOLUMES, {"X": FULL}, _p01(), {})
    )


def test_lines_text_hash_follows_p01(tmp_path):
    lines = tmp_path / "lines.jsonl"
    rows = [
        {"page": 1, "text": "Alpha"},
        {"page": 1, "text": "Beta"},
        {"page": 3, "text": "Gamma"},
    ]
    lines.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    # p01: one hash per page in order, an empty page hashes the empty string.
    pages = [
        hashlib.sha256(t.encode()).hexdigest() for t in ("Alpha\nBeta", "", "Gamma")
    ]
    expected = hashlib.sha256("".join(pages).encode()).hexdigest()
    assert lines_text_hash(lines, 3, set()) == expected
    skipped = hashlib.sha256((pages[0] + pages[2]).encode()).hexdigest()
    assert lines_text_hash(lines, 3, {2}) == skipped


def test_rebuilds_differing_in_one_byte_fail(tmp_path):
    a, b = tmp_path / "run-a", tmp_path / "run-b"
    for d in (a, b):
        d.mkdir()
        (d / "entries-X.jsonl").write_text('{"id": "X/A/1"}\n', encoding="utf-8")
    assert dir_differences(a, b, ("entries-X.jsonl",)) == []
    (b / "entries-X.jsonl").write_text('{"id": "X/A/2"}\n', encoding="utf-8")
    assert dir_differences(a, b, ("entries-X.jsonl",)) == [
        "entries-X.jsonl: differs from line 1"
    ]


def test_a_rebuild_missing_a_file_fails(tmp_path):
    a, b = tmp_path / "run-a", tmp_path / "run-b"
    a.mkdir()
    b.mkdir()
    (a / "entries-X.jsonl").write_text("{}\n", encoding="utf-8")
    assert dir_differences(a, b, ("entries-X.jsonl",)) == [
        "entries-X.jsonl: missing in run-b"
    ]
    assert dir_differences(a, b, ("entries-X.jsonl", "apparatus-X.jsonl"))[
        0
    ].startswith("apparatus-X.jsonl: missing in run-a, run-b")
    (b / "nested").mkdir()
    (b / "nested" / "c.jsonld").write_text("{}", encoding="utf-8")
    (b / "entries-X.jsonl").write_text("{}\n", encoding="utf-8")
    assert dir_differences(a, b) == ["nested/c.jsonld: missing in run-a"]


def test_p10_must_hold_every_line_and_list_every_violation():
    green = {"lines_outside_records": 0}
    assert p10_failures(green, [], []) == []
    assert p10_failures({"lines_outside_records": 3}, [], []) == [
        "3 lines outside every record"
    ]
    assert p10_failures({}, [], []) == ["p10 reported no line ledger"]
    assert p10_failures(green, [("shape", "X/A/1#1")], []) == [
        "new violation shape X/A/1#1"
    ]
    assert p10_failures(green, [], [("year", "X/A/2#1")]) == [
        "stale exception year X/A/2#1"
    ]


IDS = ["X/A/1#1", "X/A/p2l3#1", "X/B/7#2"]


def _exists(ids):
    return set(ids).__contains__


def test_a_sample_holds_when_every_identifier_exists():
    assert sample_failures(IDS, [], pin_of(IDS), _exists(IDS)) == []


def test_a_moved_identifier_without_remap_fails():
    rebuilt = ["X/A/1#1", "X/A/p2l4#1", "X/B/7#2"]
    failures = sample_failures(IDS, [], pin_of(IDS), _exists(rebuilt))
    assert len(failures) == 1 and failures[0].startswith(
        "X/A/p2l3#1 is not in the rebuilt"
    )


def test_a_recorded_move_holds():
    listed = ["X/A/1#1", "X/A/p2l4#1", "X/B/7#2"]
    remaps = [{"from": "X/A/p2l3#1", "to": "X/A/p2l4#1", "reason": "heading split off"}]
    assert sample_failures(listed, remaps, pin_of(IDS), _exists(listed)) == []


def test_an_identifier_replaced_in_the_listing_without_remap_fails_the_pin():
    listed = ["X/A/1#1", "X/A/p2l4#1", "X/B/7#2"]
    failures = sample_failures(listed, [], pin_of(IDS), _exists(listed))
    assert failures == [
        "the frozen identifiers differ from their pin: an identifier changed "
        "without a remap entry"
    ]


def test_a_sample_without_pin_fails():
    assert sample_failures(IDS, [], None, _exists(IDS)) == [
        "the sample has no pin (p14_gate.py --pin)"
    ]


def test_a_remap_without_reason_or_target_fails():
    listed = ["X/A/1#1", "X/A/p2l4#1", "X/B/7#2"]
    no_reason = [{"from": "X/A/p2l3#1", "to": "X/A/p2l4#1", "reason": " "}]
    assert any(
        "lacks" in f
        for f in sample_failures(listed, no_reason, pin_of(IDS), _exists(listed))
    )
    # The remap names a move the listing does not show.
    stray = [{"from": "X/A/9#1", "to": "X/A/10#1", "reason": "moved"}]
    assert any(
        "does not list X/A/10#1" in f
        for f in sample_failures(IDS, stray, pin_of(IDS), _exists(IDS))
    )


def test_a_remap_target_missing_from_the_rebuild_fails():
    listed = ["X/A/1#1", "X/A/p2l4#1", "X/B/7#2"]
    remaps = [{"from": "X/A/p2l3#1", "to": "X/A/p2l4#1", "reason": "heading split off"}]
    failures = sample_failures(
        listed, remaps, pin_of(IDS), _exists(["X/A/1#1", "X/B/7#2"])
    )
    assert failures and "its remap target moved" in failures[0]


def test_remaps_undo_in_chains_and_duplicates_fail():
    remaps = [
        {"from": "X/A/1#1", "to": "X/A/2#1", "reason": "first move"},
        {"from": "X/A/2#1", "to": "X/A/3#1", "reason": "second move"},
    ]
    frozen, problems = undo_remaps(["X/A/3#1", "X/B/7#2"], remaps)
    assert frozen == ["X/A/1#1", "X/B/7#2"] and problems == []
    assert undo_remaps(["X/A/1#1", "X/A/1#1"], [])[1] == [
        "the sample lists an identifier twice"
    ]


def _sid(identifier: str) -> str:
    return hashlib.sha256(identifier.encode()).hexdigest()[:10]


def test_a_blind_row_is_pinned_by_its_sample_id():
    key = {_sid("X/A/1"): {"printId": "X/A/1"}}
    assert blind_row_failures(key, [], set(key)) == []
    moved = {_sid("X/A/1"): {"printId": "X/A/2"}}
    assert blind_row_failures(moved, [], set(moved))[0].endswith(
        "is not the entry it was drawn as"
    )
    remaps = [{"from": "X/A/1", "to": "X/A/2", "reason": "renumbered"}]
    assert blind_row_failures(moved, remaps, set(moved)) == []


def test_the_blind_sheet_must_hold_the_key_rows():
    key = {_sid("X/A/1"): {"printId": "X/A/1"}}
    assert blind_row_failures(key, [], None) == ["the blind sheet is missing"]
    assert blind_row_failures(key, [], {"0" * 10}) == [
        "sheet and key differ in 2 sample identifiers"
    ]


def test_the_gate_runs_every_named_check():
    names = [n for n, _ in p14_gate.Gate(export=False).checks()]
    assert names == ["inputs", "rebuild", "validate", "samples"]
    assert [n for n, _ in p14_gate.Gate(export=True).checks()][-1] == "export"


def test_the_first_failure_stops_the_run_and_a_raise_fails():
    calls = []

    def ok():
        calls.append("ok")
        return [], {}

    def bad():
        calls.append("bad")
        return ["broken"], {}

    def boom():
        raise KeyError("x")

    results = run_checks([("a", ok), ("b", bad), ("c", ok)], keep_going=False)
    assert calls == ["ok", "bad"]
    assert results["b"]["ok"] is False and results["c"]["ok"] is None
    results = run_checks([("a", boom), ("b", ok)], keep_going=True)
    assert results["a"]["ok"] is False and results["b"]["ok"] is True
