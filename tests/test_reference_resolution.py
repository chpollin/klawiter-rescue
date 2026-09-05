"""Source redirect identity, chained aliases and unresolved references."""

import importlib
from types import SimpleNamespace

import pytest

classify = importlib.import_module("04_classify")
project = importlib.import_module("05_to_jsonld")


@pytest.fixture
def reference_rows():
    return [
        {"page_id": "1", "title": "Display title", "page_title": "Source title"},
        {
            "page_id": "2",
            "page_title": "Earlier alias",
            "title": "Later alias",
            "redirect_target": "Later alias",
            "is_redirect": True,
        },
        {
            "page_id": "3",
            "page_title": "Later alias",
            "title": "Source title",
            "redirect_target": "Source title",
            "is_redirect": True,
        },
    ]


def test_classification_preserves_literal_redirect_targets(monkeypatch, reference_rows):
    expected = [row.get("redirect_target") for row in reference_rows]
    written = []
    monkeypatch.setattr(classify, "_parse_args", lambda: SimpleNamespace(input="03c"))
    monkeypatch.setattr(classify, "load_csv", lambda path: reference_rows)
    monkeypatch.setattr(
        classify, "write_csv", lambda path, rows, fields: written.extend(rows)
    )
    classify.main()
    assert [row.get("redirect_target") for row in written] == expected


@pytest.mark.parametrize("reverse", [False, True])
def test_aliases_resolve_to_terminal_page_independent_of_row_order(
    reference_rows, reverse
):
    rows = list(reversed(reference_rows)) if reverse else reference_rows
    targets = project.build_reference_targets(rows)
    assert targets == dict.fromkeys(
        ("Display title", "Source title", "Earlier alias", "Later alias"), 1
    )
    entry = project.row_to_jsonld(
        {"page_id": "4", "see_also": '["Earlier alias", "Missing title"]'},
        reference_targets=targets,
    )
    assert entry["relation"] == [{"@id": "klawiter:entry/1", "name": "Earlier alias"}]
    assert entry["seeAlsoText"] == ["Missing title"]


def test_redirect_cycles_and_missing_targets_remain_unresolved(reference_rows):
    for pid, alias, target in [
        (4, "Cycle A", "Cycle B"),
        (5, "Cycle B", "Cycle A"),
        (6, "Broken alias", "Missing title"),
    ]:
        reference_rows.append(
            {
                "page_id": str(pid),
                "page_title": alias,
                "title": target,
                "redirect_target": target,
                "is_redirect": True,
            }
        )
    targets = project.build_reference_targets(reference_rows)
    assert not {"Cycle A", "Cycle B", "Broken alias", "Missing title"} & targets.keys()
    assert targets["Earlier alias"] == 1
