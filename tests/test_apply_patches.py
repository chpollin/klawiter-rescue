"""
Tests for the editor-corrections overlay (pipeline/apply_patches.py).

These run on synthetic in-memory data, not the real dataset: they verify the
write-back logic of the EIL editing interface (provenance -> editor, edit
history preserving the machine original, three-status review, idempotency)
without touching docs/data/klawiter.json or needing a browser.
"""

import apply_patches as ap


def make_entries():
    return [
        {'sourcePageId': 1, 'title': 'A', 'publisher': 'Leipzig',
         '_provenance': {'publisher': 'llm', 'location': 'regex',
                         'translator': 'missing', 'pageCount': 'missing'}},
        {'sourcePageId': 2, 'title': 'B', 'publisher': '',
         '_provenance': {'publisher': 'missing'}},
    ]


def patch(pid, field, action, old=None, new=None, prov='llm',
          by='Editor (SZD)', at='2026-06-21T10:00:00Z', source='human'):
    return {'pageId': pid, 'field': field, 'action': action, 'oldValue': old,
            'newValue': new, 'previousProvenance': prov, 'edited_by': by,
            'edited_at': at, 'source': source}


def test_correct_sets_value_provenance_and_history():
    entries = make_entries()
    report = ap.apply_patches(entries, [
        patch(1, 'publisher', 'correct', old='Leipzig', new='Insel-Verlag')
    ])
    e = entries[0]
    assert e['publisher'] == 'Insel-Verlag'
    assert e['_provenance']['publisher'] == 'editor'
    assert len(e['edit_history']) == 1
    h = e['edit_history'][0]
    assert h['originalValue'] == 'Leipzig' and h['newValue'] == 'Insel-Verlag'
    assert h['previousProvenance'] == 'llm' and h['source'] == 'human'
    assert e['review']['status'] == 'approved'
    assert report['by_action']['correct'] == 1 and report['entries_touched'] == 1


def test_add_fills_missing_field():
    entries = make_entries()
    ap.apply_patches(entries, [
        patch(2, 'publisher', 'add', old='', new='Fischer', prov='missing')
    ])
    e = entries[1]
    assert e['publisher'] == 'Fischer'
    assert e['_provenance']['publisher'] == 'editor'
    assert e['edit_history'][0]['action'] == 'add'


def test_accept_keeps_value_but_marks_editor():
    entries = make_entries()
    ap.apply_patches(entries, [
        patch(1, 'publisher', 'accept', old='Leipzig', new='Leipzig', prov='llm')
    ])
    e = entries[0]
    assert e['publisher'] == 'Leipzig'                 # value unchanged
    assert e['_provenance']['publisher'] == 'editor'    # but verified
    assert e['edit_history'][0]['action'] == 'accept'


def test_unknown_pageid_is_reported_not_applied():
    entries = make_entries()
    report = ap.apply_patches(entries, [patch(999, 'publisher', 'correct',
                                              old='x', new='y')])
    assert report['entries_touched'] == 0
    assert report['not_found'] == [{'pageId': 999, 'field': 'publisher'}]


def test_multiple_corrections_last_wins_history_ordered():
    entries = make_entries()
    ap.apply_patches(entries, [
        patch(1, 'publisher', 'correct', old='Leipzig', new='Wrong',
              at='2026-06-21T10:00:00Z'),
        patch(1, 'publisher', 'correct', old='Wrong', new='Insel-Verlag',
              at='2026-06-21T11:00:00Z'),
    ])
    e = entries[0]
    assert e['publisher'] == 'Insel-Verlag'             # later edit wins
    assert [h['newValue'] for h in e['edit_history']] == ['Wrong', 'Insel-Verlag']


def test_idempotent_on_rerun():
    patches = [patch(1, 'publisher', 'correct', old='Leipzig', new='Insel-Verlag')]
    a = make_entries()
    ap.apply_patches(a, patches)
    b = make_entries()
    ap.apply_patches(b, patches)
    ap.apply_patches(b, patches)   # applied twice
    assert a[0] == b[0]            # history not duplicated, same result


def test_human_beats_agent_in_review_status():
    entries = make_entries()
    ap.apply_patches(entries, [
        patch(1, 'location', 'accept', old='X', new='X', source='agent',
              at='2026-06-21T09:00:00Z'),
        patch(1, 'publisher', 'correct', old='Leipzig', new='Insel-Verlag',
              source='human', at='2026-06-21T10:00:00Z'),
    ])
    assert entries[0]['review']['status'] == 'approved'


def test_invalid_patch_is_skipped_and_reported():
    entries = make_entries()
    report = ap.apply_patches(entries, [
        patch(1, 'publisher', 'frobnicate', old='Leipzig', new='x'),  # bad action
    ])
    assert report['entries_touched'] == 0
    assert len(report['invalid']) == 1
    assert any('action' in p for p in report['invalid'][0]['problems'])
