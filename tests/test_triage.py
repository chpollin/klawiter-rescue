"""
Triage artifact contract (EIL editing interface, increment 2).

pipeline/build_triage.py reduces verify.py results and census anomalies to
docs/data/triage.json; docs/js/edit.js reads that file in edit mode. These
tests pin the artifact shape both sides depend on: the flag keys
(notInSource / detectable / census), the frontend field naming (pageCount,
not page_count), and the rule that unflagged entries do not appear at all.
"""

import build_triage as bt


def verify_result(pid, fields):
    return {'page_id': pid, 'title': 'T', 'fields': fields}


def census(empty_bib_pages=()):
    return {'source': {'empty_content_pages': {
        'bibliographic_ns0': [{'page_id': p, 'title': 't', 'text_id': '1'} for p in empty_bib_pages],
        'non_bibliographic': [{'page_id': 2365, 'namespace': 8, 'title': 'Print.css'}],
    }}}


def test_false_positive_becomes_not_in_source():
    results = [verify_result(87, {
        'publisher': {'extracted': 'X', 'in_raw': False, 'status': 'false_positive'},
        'location': {'extracted': 'Weimar', 'in_raw': True, 'status': 'correct'},
    })]
    triage = bt.build_triage(results, census())
    assert triage == {'87': {'notInSource': ['publisher']}}


def test_false_negative_becomes_detectable_with_raw_value():
    results = [verify_result(87, {
        'translator_false_negative': {'detected_in_raw': 'Felix Braun',
                                      'note': 'translator found in raw but not in output'},
    })]
    triage = bt.build_triage(results, census())
    assert triage == {'87': {'detectable': {'translator': 'Felix Braun'}}}


def test_page_count_maps_to_frontend_field_name():
    results = [verify_result(87, {
        'page_count': {'extracted': 999, 'in_raw': False, 'status': 'false_positive'},
    })]
    triage = bt.build_triage(results, census())
    assert triage['87']['notInSource'] == ['pageCount']


def test_census_anomaly_flagged_non_bibliographic_ignored():
    triage = bt.build_triage([], census(empty_bib_pages=[2979]))
    assert list(triage.keys()) == ['2979']
    assert 'census' in triage['2979']


def test_clean_entries_are_absent():
    """Correct and correct_fallback extractions produce no flag at all."""
    results = [verify_result(3, {
        'title': {'extracted': 'Amok', 'in_raw': True, 'status': 'correct'},
        'publisher': {'extracted': 'Insel-Verlag', 'in_raw': True, 'status': 'correct'},
    })]
    assert bt.build_triage(results, census()) == {}


def test_flag_keys_are_pinned():
    """edit.js reads exactly these keys; anything else is contract drift."""
    results = [verify_result(87, {
        'publisher': {'extracted': 'X', 'in_raw': False, 'status': 'false_positive'},
        'translator_false_negative': {'detected_in_raw': 'Felix Braun'},
    })]
    triage = bt.build_triage(results, census(empty_bib_pages=[2979]))
    for flags in triage.values():
        assert set(flags) <= {'notInSource', 'detectable', 'census'}
