"""
Tests for the editor-corrections overlay (pipeline/apply_patches.py).

These run on synthetic in-memory data, not the real dataset: they verify the
write-back logic of the EIL editing interface (provenance -> editor, edit
history preserving the machine original, three-status review, idempotency)
without touching docs/data/klawiter.json or needing a browser.
"""

import apply_patches as ap
import pytest


@pytest.mark.parametrize(
    "document",
    [
        [],
        {},
        {"patches": []},
        {"patchVersion": 1, "patches": []},
        {"patchVersion": 2, "patches": {}},
        {"reconciliationPatchVersion": 1},
    ],
)
def test_malformed_patch_envelope_cannot_be_an_empty_success(document):
    with pytest.raises(ValueError):
        ap.field_patches(document)


def test_field_and_reconciliation_only_documents_remain_separate():
    record = patch(1, "publisher", "accept", old="A", new="A")
    assert ap.field_patches({"patchVersion": 2, "patches": [record]}) == [record]
    assert (
        ap.field_patches({"reconciliationPatchVersion": 1, "reconciliationPatches": []})
        == []
    )


def make_entries():
    return [
        {
            "sourcePageId": 1,
            "title": "A",
            "publisher": "Leipzig",
            "_provenance": {
                "publisher": "llm",
                "location": "regex",
                "translator": "missing",
                "pageCount": "missing",
            },
        },
        {
            "sourcePageId": 2,
            "title": "B",
            "publisher": "",
            "_provenance": {"publisher": "missing"},
        },
    ]


def patch(
    pid,
    field,
    action,
    old=None,
    new=None,
    prov="llm",
    by="Editor (SZD)",
    at="2026-06-21T10:00:00Z",
    source="human",
):
    return {
        "pageId": pid,
        "field": field,
        "action": action,
        "oldValue": old,
        "newValue": new,
        "previousProvenance": prov,
        "edited_by": by,
        "edited_at": at,
        "source": source,
    }


def test_correct_sets_value_provenance_and_history():
    entries = make_entries()
    report = ap.apply_patches(
        entries, [patch(1, "publisher", "correct", old="Leipzig", new="Insel-Verlag")]
    )
    e = entries[0]
    assert e["publisher"] == "Insel-Verlag"
    assert e["_provenance"]["publisher"] == "editor"
    assert len(e["edit_history"]) == 1
    h = e["edit_history"][0]
    assert h["originalValue"] == "Leipzig" and h["newValue"] == "Insel-Verlag"
    assert h["previousProvenance"] == "llm" and h["source"] == "human"
    assert e["review"]["status"] == "approved"
    assert report["by_action"]["correct"] == 1 and report["entries_touched"] == 1


def test_add_fills_missing_field():
    entries = make_entries()
    ap.apply_patches(
        entries, [patch(2, "publisher", "add", old="", new="Fischer", prov="missing")]
    )
    e = entries[1]
    assert e["publisher"] == "Fischer"
    assert e["_provenance"]["publisher"] == "editor"
    assert e["edit_history"][0]["action"] == "add"


def test_accept_keeps_value_but_marks_editor():
    entries = make_entries()
    ap.apply_patches(
        entries,
        [patch(1, "publisher", "accept", old="Leipzig", new="Leipzig", prov="llm")],
    )
    e = entries[0]
    assert e["publisher"] == "Leipzig"  # value unchanged
    assert e["_provenance"]["publisher"] == "editor"  # but verified
    assert e["edit_history"][0]["action"] == "accept"


def test_unknown_pageid_is_reported_not_applied():
    entries = make_entries()
    report = ap.apply_patches(
        entries, [patch(999, "publisher", "correct", old="x", new="y")]
    )
    assert report["entries_touched"] == 0
    assert report["not_found"] == [{"pageId": 999, "field": "publisher"}]


def test_multiple_corrections_last_wins_history_ordered():
    entries = make_entries()
    ap.apply_patches(
        entries,
        [
            patch(
                1,
                "publisher",
                "correct",
                old="Leipzig",
                new="Wrong",
                at="2026-06-21T10:00:00Z",
            ),
            patch(
                1,
                "publisher",
                "correct",
                old="Wrong",
                new="Insel-Verlag",
                at="2026-06-21T11:00:00Z",
            ),
        ],
    )
    e = entries[0]
    assert e["publisher"] == "Insel-Verlag"  # later edit wins
    assert [h["newValue"] for h in e["edit_history"]] == ["Wrong", "Insel-Verlag"]


@pytest.mark.parametrize("pid", ["1", True, 1.0, 0, -1])
def test_patch_requires_integer_page_identity(pid):
    assert "pageId must be a positive integer" in ap.validate_patch(
        patch(pid, "publisher", "accept", old="Leipzig", new="Leipzig")
    )


@pytest.mark.parametrize(
    "timestamp", ["not-a-date", "2026-09-05", "2026-09-05T10:00:00", None]
)
def test_patch_requires_valid_timezone_aware_timestamp(timestamp):
    problems = ap.validate_patch(patch(1, "publisher", "accept", at=timestamp))
    assert any("invalid edited_at" in problem for problem in problems)


def test_patch_order_uses_instants_across_timezone_offsets():
    entries = make_entries()
    ap.apply_patches(
        entries,
        [
            patch(
                1,
                "publisher",
                "correct",
                old="Wrong",
                new="Final",
                at="2026-06-21T09:30:00Z",
            ),
            patch(
                1,
                "publisher",
                "correct",
                old="Leipzig",
                new="Wrong",
                at="2026-06-21T10:00:00+02:00",
            ),
        ],
    )
    assert entries[0]["publisher"] == "Final"
    assert [h["newValue"] for h in entries[0]["edit_history"]] == ["Wrong", "Final"]


@pytest.mark.parametrize("invalid", [False, True])
def test_failed_authoritative_batch_does_not_write_partial_dataset(
    tmp_path, monkeypatch, invalid
):
    dataset = tmp_path / "frontend.json"
    dataset.write_text(
        '{"entries": [{"sourcePageId": 1, "publisher": "Leipzig"}]}', encoding="utf-8"
    )
    before = dataset.read_bytes()
    patches = [
        patch(1, "publisher", "correct", old="Leipzig", new="Insel-Verlag"),
        patch("2" if invalid else 999, "publisher", "accept", old="x", new="x"),
    ]
    monkeypatch.setattr(ap, "OUTPUT_FRONTEND_JSON", dataset)
    monkeypatch.setattr(ap, "REPORT_PATH", str(tmp_path / "report.json"))
    monkeypatch.setattr(ap, "load_corrections", lambda: patches)
    assert ap.main() == 1
    assert dataset.read_bytes() == before


def test_location_correction_uses_only_reviewed_authority_link():
    entries = [make_entries()[0]]
    entries[0]["location"] = "Old"
    entries[0]["locationSameAs"] = "https://example.invalid/old"
    report = ap.apply_patches(
        entries,
        [patch(1, "location", "correct", old="Old", new="Wien")],
        {"Wien": {"uri": "https://www.wikidata.org/entity/Q1741"}},
    )
    assert report["patches_applied"] == 1
    assert entries[0]["locationSameAs"] == "https://www.wikidata.org/entity/Q1741"


def test_location_correction_drops_unreviewed_authority_link():
    entries = [make_entries()[0]]
    entries[0]["location"] = "Old"
    entries[0]["locationSameAs"] = "https://example.invalid/old"
    ap.apply_patches(
        entries,
        [patch(1, "location", "correct", old="Old", new="Unreviewed")],
        {},
    )
    assert "locationSameAs" not in entries[0]


def test_idempotent_on_rerun():
    patches = [patch(1, "publisher", "correct", old="Leipzig", new="Insel-Verlag")]
    a = make_entries()
    ap.apply_patches(a, patches)
    b = make_entries()
    ap.apply_patches(b, patches)
    ap.apply_patches(b, patches)  # applied twice
    assert a[0] == b[0]  # history not duplicated, same result


def test_human_beats_agent_in_review_status():
    entries = make_entries()
    ap.apply_patches(
        entries,
        [
            patch(
                1,
                "location",
                "accept",
                old="X",
                new="X",
                source="agent",
                at="2026-06-21T09:00:00Z",
            ),
            patch(
                1,
                "publisher",
                "correct",
                old="Leipzig",
                new="Insel-Verlag",
                source="human",
                at="2026-06-21T10:00:00Z",
            ),
        ],
    )
    assert entries[0]["review"]["status"] == "approved"


def test_invalid_patch_is_skipped_and_reported():
    entries = make_entries()
    report = ap.apply_patches(
        entries,
        [
            patch(1, "publisher", "frobnicate", old="Leipzig", new="x"),  # bad action
        ],
    )
    assert report["entries_touched"] == 0
    assert len(report["invalid"]) == 1
    assert any("action" in p for p in report["invalid"][0]["problems"])


def test_unknown_field_is_rejected_not_applied():
    entries = make_entries()
    report = ap.apply_patches(
        entries,
        [
            patch(1, "publsher", "correct", old="Leipzig", new="Insel-Verlag"),  # typo
        ],
    )
    assert report["entries_touched"] == 0
    assert "publsher" not in entries[0]
    assert any("field" in prob for prob in report["invalid"][0]["problems"])


def test_old_value_mismatch_is_reported_but_applied():
    entries = make_entries()
    report = ap.apply_patches(
        entries,
        [
            patch(1, "publisher", "correct", old="Vienna", new="Insel-Verlag"),
        ],
    )
    assert entries[0]["publisher"] == "Insel-Verlag"  # store is authoritative
    assert report["old_value_mismatch"] == [
        {
            "pageId": 1,
            "field": "publisher",
            "patchOldValue": "Vienna",
            "currentValue": "Leipzig",
        }
    ]


def test_rerun_on_patched_data_is_not_a_mismatch():
    entries = make_entries()
    patches = [patch(1, "publisher", "correct", old="Leipzig", new="Insel-Verlag")]
    ap.apply_patches(entries, patches)
    report = ap.apply_patches(entries, patches)  # current equals newValue
    assert report["old_value_mismatch"] == []


def test_editor_review_keeps_the_dataset_review_projection():
    """Stage 05 projects Gate-2 field decisions into entry['review']; an
    editor patch raises the status without discarding that field record."""
    entries = make_entries()
    entries[0]["review"] = {
        "status": "agent_verified",
        "reviewed_by": "independent-verification-agent",
        "fields": {"location": "confirm"},
    }
    ap.apply_patches(
        entries, [patch(1, "publisher", "correct", old="Leipzig", new="Insel-Verlag")]
    )
    review = entries[0]["review"]
    assert review["status"] == "approved"
    assert review["reviewed_by"] == "Editor (SZD)"
    assert review["fields"] == {"location": "confirm"}
