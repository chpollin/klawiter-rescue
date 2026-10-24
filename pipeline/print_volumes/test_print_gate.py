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
    leak_failures,
    lines_text_hash,
    p10_failures,
    pin_of,
    print_shingles,
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
    assert names == ["inputs", "leaks", "rebuild", "validate", "samples"]
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


# An invented print page: a sentence runs over a line break.
INVENTED_PRINT = [
    [
        "12 Muster, Max. Ein erfundener Satz, der quer",
        "über zwei Zeilen läuft und genau so nur hier gedruckt steht. 1950.",
    ]
]


def test_a_versioned_file_quoting_the_print_fails_with_its_line():
    quoted = (
        "Intro.\n> Ein erfundener Satz, der quer über zwei Zeilen läuft und "
        "genau so nur hier gedruckt steht.\n"
    )
    failures = leak_failures({"knowledge/x.md": quoted}, print_shingles(INVENTED_PRINT))
    assert failures == ["knowledge/x.md:2 repeats 12 consecutive words of the print"]


def test_an_address_title_or_paraphrase_does_not_count_as_a_leak():
    clean = "See F 61, Muster, Max (1950). A sentence about the entry, in other words."
    assert (
        leak_failures({"knowledge/x.md": clean}, print_shingles(INVENTED_PRINT)) == []
    )


def test_an_admitted_label_passes_only_by_its_own_hash():
    from p14_gate import WORD, shingle_hash

    sentence = "Ein erfundener Satz, der quer über zwei Zeilen läuft und genau so"
    words = tuple(WORD.findall(sentence.lower()))
    print_set = print_shingles(INVENTED_PRINT)
    files = {"knowledge/x.md": sentence}
    assert leak_failures(files, print_set, frozenset({shingle_hash(words)})) == []
    assert leak_failures(files, print_set, frozenset({"0" * 64})) != []


def _fp(record, object_id=None):
    from p14_gate import fingerprint

    return fingerprint(record, object_id)


RECORD = {"sha256": "e" * 64, "objects": [{"id": "X/A/1#1", "span": [0, 9]}]}


def test_a_fingerprint_binds_the_entry_text_and_the_object_span():
    assert _fp(RECORD) == "e" * 64
    assert _fp(RECORD, "X/A/1#1") == "e" * 64 + ":0-9"
    assert _fp(RECORD, "X/A/1#2") is None


def _prints_check(frozen, rehashed, current, remaps=()):
    from p14_gate import fingerprint_failures, fingerprint_pin

    return fingerprint_failures(
        list(frozen),
        frozen,
        rehashed,
        list(remaps),
        fingerprint_pin(frozen),
        current.get,
    )


def test_a_changed_fingerprint_fails_unless_its_rehash_is_recorded():
    frozen = {"X/A/1#1": "old"}
    assert _prints_check(frozen, [], {"X/A/1#1": "old"}) == []
    failures = _prints_check(frozen, [], {"X/A/1#1": "new"})
    assert len(failures) == 1 and "rehash list" in failures[0]
    change = {
        "id": "X/A/1#1",
        "from": "old",
        "to": "new",
        "reason": "span widened by one",
    }
    assert _prints_check(frozen, [change], {"X/A/1#1": "new"}) == []
    wrong_start = {**change, "from": "other"}
    assert any(
        "starts from another" in f
        for f in _prints_check(frozen, [wrong_start], {"X/A/1#1": "new"})
    )
    assert any(
        "lacks" in f
        for f in _prints_check(frozen, [{**change, "reason": ""}], {"X/A/1#1": "new"})
    )


def test_fingerprints_follow_a_remapped_identifier_and_their_pin():
    from p14_gate import fingerprint_failures

    frozen = {"X/A/p2l3#1": "fp"}
    remaps = [{"from": "X/A/p2l3#1", "to": "X/A/p2l4#1", "reason": "heading split off"}]
    assert _prints_check(frozen, [], {"X/A/p2l4#1": "fp"}, remaps) == []
    failures = fingerprint_failures(
        ["X/A/p2l3#1"], frozen, [], remaps, "0" * 64, {"X/A/p2l4#1": "fp"}.get
    )
    assert failures == ["the fingerprints differ from their pin"]
    assert fingerprint_failures(["X/A/1#1"], None, [], [], None, {}.get) == [
        "the sample has no fingerprints (p14_gate.py --pin)"
    ]


def test_the_pool_sizes_must_match_the_review_sample():
    from p14_gate import pools_failures

    review = {"objects": {"X": {"A": ["X/A/1#1", "X/A/2#1"]}}}
    pools = {
        "parts": {"X": {"A": {"entries": 9, "hard": 1, "eligible": 7, "drawn": 2}}}
    }
    assert pools_failures(pools, review) == []
    pools["parts"]["X"]["A"]["drawn"] = 3
    assert pools_failures(pools, review) == [
        "review-pools: X/A does not hold the 2 objects drawn"
    ]
    assert pools_failures(None, review)[0].startswith(
        "review-pools: the pool sizes are missing"
    )


def test_the_blind_stratum_sizes_must_cover_the_strata():
    from p14_gate import strata_failures

    key = {"s": {"printId": "X/A/1", "stratum": "none"}}
    assert strata_failures({"sizes": {"X": {"none": 40}}}, key) == []
    assert strata_failures({"sizes": {"X": {"field": 4}}}, key) == [
        "blind-strata: no size for X none"
    ]
