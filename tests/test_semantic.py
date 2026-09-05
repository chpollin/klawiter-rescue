"""Source-verified field diagnosis and exact regression protection.

The opt-in semantic suite keeps known failures red. The default gate allows
only the recorded page/field/value deviations, so fixing one cannot conceal
a new failure elsewhere. Both checks use the same field comparison.
"""

import warnings

import pytest

_FIELDS = (
    "title",
    "year",
    "publisher",
    "location",
    "language",
    "translator",
    "pageCount",
)


def _actual(field, entry):
    if field == "title":
        return entry.get(field, "")
    if field in ("year", "pageCount"):
        return entry.get(field)
    return entry.get(field) or None


def _field_ok(field, source, entry):
    expected = source["expected"][field]
    actual = _actual(field, entry)
    if field == "title":
        if expected is None:
            return not actual
        return actual == expected or actual in source.get("accepted_title_variants", [])
    return actual == expected


def _mismatches(wiki_entries, entries_by_id):
    bad = {}
    for source in wiki_entries:
        pid = source["page_id"]
        entry = entries_by_id.get(pid)
        for field in _FIELDS:
            if entry is None or not _field_ok(field, source, entry):
                bad[pid, field] = _actual(field, entry) if entry is not None else None
    return bad


def test_ground_truth_mismatches_bounded(
    wiki_entries, ns0_by_id, baseline, semantic_baseline
):
    ids = [source["page_id"] for source in wiki_entries]
    assert sorted(ids) == semantic_baseline["groundTruthPageIds"], (
        "Semantic ground-truth page inventory changed"
    )
    assert list(_FIELDS) == semantic_baseline["groundTruthFields"], (
        "Semantic comparison field inventory changed"
    )
    records = semantic_baseline["knownMismatches"]
    known = {(r["pageId"], r["field"]): r["actual"] for r in records}
    assert len(known) == len(records), "Duplicate semantic baseline cases"
    assert len(known) == baseline["known_issues"]["semantic_field_mismatches"]
    oracle_keys = {(w["page_id"], field) for w in wiki_entries for field in _FIELDS}
    assert known.keys() <= oracle_keys, "Semantic baseline contains untested cases"
    missing = {w["page_id"] for w in wiki_entries} - ns0_by_id.keys()
    assert not missing, f"Ground-truth pages absent from frontend: {sorted(missing)}"

    bad = _mismatches(wiki_entries, ns0_by_id)
    unexpected = {
        key: value
        for key, value in bad.items()
        if key not in known or known[key] != value
    }
    assert not unexpected, f"New or changed semantic failures: {unexpected}"
    resolved = known.keys() - bad.keys()
    if resolved:
        warnings.warn(
            f"Semantic cases resolved: {sorted(resolved)}. Review the source and remove "
            "these cases from semantic-baseline.json; lower semantic_field_mismatches.",
            stacklevel=2,
        )


@pytest.mark.semantic
@pytest.mark.parametrize("field", _FIELDS)
def test_source_verified_field(wiki_entry, ns0_by_id, field):
    pid = wiki_entry["page_id"]
    entry = ns0_by_id.get(pid)
    assert entry is not None, f"Entry {pid} not found"
    expected = wiki_entry["expected"][field]
    assert _field_ok(field, wiki_entry, entry), (
        f"page {pid} ({wiki_entry['page_title']}): {field}\n"
        f"expected: {expected!r}\nactual: {_actual(field, entry)!r}\n"
        f"source notes: {wiki_entry.get('notes', '')}"
    )


@pytest.mark.parametrize("regression", ["different-page", "changed-value"])
def test_semantic_guard_rejects_replacement_failures(regression):
    oracle = [{"page_id": pid, "expected": dict.fromkeys(_FIELDS)} for pid in (1, 2)]
    entries = {1: {"year": 1900}, 2: {}}
    if regression == "different-page":
        entries = {1: {}, 2: {"year": 1900}}
    else:
        entries[1]["year"] = 1901
    with pytest.raises(AssertionError, match="New or changed semantic failures"):
        test_ground_truth_mismatches_bounded(
            oracle,
            entries,
            {"known_issues": {"semantic_field_mismatches": 1}},
            {
                "groundTruthPageIds": [1, 2],
                "groundTruthFields": list(_FIELDS),
                "knownMismatches": [{"pageId": 1, "field": "year", "actual": 1900}],
            },
        )


def test_title_variants_match_source_page_titles(wiki_entries, source_rows):
    source_titles = {int(row["page_id"]): row["page_title"] for row in source_rows}
    for entry in wiki_entries:
        for variant in entry.get("accepted_title_variants", []):
            assert variant == source_titles[entry["page_id"]]


@pytest.mark.parametrize(
    "page_id,title",
    [
        (33, "Legenden completely invented trailing text"),
        (33, "Legenden (VIST)"),
        (285, "Verwirrung der Gefühle (VIST) invented"),
    ],
)
def test_semantic_guards_reject_invented_title_suffixes(
    wiki_entries, ns0_by_id, baseline, semantic_baseline, page_id, title
):
    changed = {**ns0_by_id, page_id: {**ns0_by_id[page_id], "title": title}}
    source = next(entry for entry in wiki_entries if entry["page_id"] == page_id)
    with pytest.raises(AssertionError, match="New or changed semantic failures"):
        test_ground_truth_mismatches_bounded(
            wiki_entries, changed, baseline, semantic_baseline
        )
    with pytest.raises(AssertionError, match=f"page {page_id}"):
        test_source_verified_field(source, changed, "title")


@pytest.mark.parametrize(
    "title", ["Verwirrung der Gefühle", "Verwirrung der Gefühle (VIST)"]
)
def test_semantic_guard_accepts_only_reviewed_title_forms(wiki_entries, title):
    source = next(entry for entry in wiki_entries if entry["page_id"] == 285)
    test_source_verified_field(source, {285: {"title": title}}, "title")
