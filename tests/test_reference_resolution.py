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


def test_collapsed_names_resolve_without_displacing_exact_names():
    rows = [
        {"page_id": "1", "title": "Two  spaces", "page_title": "Page one"},
        {"page_id": "2", "title": "Two spaces", "page_title": "Page two"},
    ]
    targets = project.build_reference_targets(rows, withheld=frozenset())
    assert targets["Two  spaces"] == 1
    assert targets["Two spaces"] == 2


# See-references the 2026-09-05 review left technically unresolved, with the
# literal source form and the page each reaches once the link target is read
# as MediaWiki reads it. 679 and 7232 name no page of the dump.
LITERAL_REFERENCES = [
    (297, "[[Sytë e vëllait të  përjetshëm]]", 5483),
    (297, "[[Amok * To gramma mias agnōstēs   * To phengarolousto dromaki]]", 3442),
    (306, "[[Die Mondscheingasse. Gesammelte  Erzählungen]]", 270),
    (310, "[[Vergessene Träume  / Die Erzählungen, Band 1]]", 6167),
    (681, "[[La Pitié dangereuse  / Individual Story]]", 7113),
    (774, "[[Der Amokläufer   .  Amok]]", 6831),
    (2088, "[[Prater, Donald A.|Donald A. Prater]]", 1645),
    (2651, "[[Zvjezdani sati čovječanstva *   Jučerašnji svijet]]", 1854),
    (6820, "[[Královská  hra]]", 3610),
    (7388, "[[Der Sechzigjährige dankt  / Letztes Gedicht]]", 7383),
]


def test_reviewed_references_resolve_as_mediawiki_reads_them(
    classified_rows, canonical_entries
):
    source = {int(row["page_id"]): row["raw_content"] for row in classified_rows}
    relations = {
        (entry["sourcePageId"], relation["@id"])
        for entry in canonical_entries
        for relation in entry.get("relation") or []
    }
    for page_id, literal, target in LITERAL_REFERENCES:
        assert literal in source[page_id], (page_id, literal)
        assert (page_id, f"klawiter:entry/{target}") in relations, (page_id, target)
    unresolved = {
        (entry["sourcePageId"], text)
        for entry in canonical_entries
        for text in entry.get("seeAlsoText") or []
    }
    assert unresolved == {
        (679, "Stefan Zweig. Oeuvres romanesques"),
        (7232, "Verlaine, Paul / German"),
    }


def test_redirect_310_reaches_6167_through_7065(classified_rows):
    rows = {int(row["page_id"]): row for row in classified_rows}
    assert rows[7065]["page_title"] == "Vergessene Träume / Die Erzählungen, Band 1"
    assert rows[7065]["is_redirect"] == "True"
    targets = project.build_reference_targets(classified_rows)
    assert targets["Vergessene Träume / Die Erzählungen, Band 1"] == 6167
