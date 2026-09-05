"""Reconciliation of pipeline output against the dump's own relation tables.

MediaWiki already resolved categories and internal links at save time; the
tables zweig_categorylinks and zweig_pagelinks in the committed dump are an
authoritative, regex-independent oracle for what the wikitext parsing must
produce. These tests are the non-circular check the round-trip verifier
cannot provide.
"""

from __future__ import annotations

import hashlib
import importlib

import pytest
from lib.config import SQL_DUMP_PATH
from lib.encoding import fix_encoding

extract = importlib.import_module("01_extract")


def test_extraction_fixtures_match_complete_sources(real_entries, source_rows):
    by_id = {int(row["page_id"]): row for row in source_rows}
    for entry in real_entries:
        row = by_id[entry["page_id"]]
        assert entry["text"] == row["content"], entry["page_id"]
        assert entry["page_title"] == row["page_title"]
        assert entry["source"]["textId"] == int(row["text_id"])
        assert entry["source"]["path"] == f"data/raw/zt_0{row['blob_id']}"
        assert (
            entry["source"]["textSha256"]
            == hashlib.sha256(row["content"].encode("utf-8")).hexdigest()
        )


@pytest.fixture(scope="module")
def sql_text() -> str:
    with open(SQL_DUMP_PATH, "rb") as f:
        return f.read().decode("latin-1")


def _table_rows(sql_text: str, table: str, min_columns: int) -> list[list[str]]:
    rows = []
    for values_str in extract.parse_sql_inserts(sql_text, table):
        for tuple_str in extract.parse_value_tuples(values_str):
            vals = extract.parse_tuple_values(tuple_str)
            assert len(vals) >= min_columns, (
                f"malformed {table} tuple with {len(vals)} columns: {vals[:3]}"
            )
            rows.append(vals)
    assert rows, f"no rows parsed for {table}"
    return rows


def test_categories_match_the_categorylinks_table(sql_text, canonical_entries) -> None:
    """Every parsed category must equal MediaWiki's own category assignment.

    The category link syntax [[Category:Name|sort key]] carries a sort key
    after the pipe; treating it as part of the name splinters the category
    facets into phantom values (550 such assignments before the fix)."""
    expected: dict[int, set[str]] = {}
    for vals in _table_rows(sql_text, "zweig_categorylinks", 2):
        page_id = int(vals[0])
        # The raw table carries the wiki's own mojibake; the pipeline repairs
        # encoding in stage 02, so the oracle gets the same repair.
        name = fix_encoding(
            extract.clean_binary_value(vals[1]).replace("_", " ").strip()
        )
        expected.setdefault(page_id, set()).add(name)

    actual: dict[int, set[str]] = {}
    for entry in canonical_entries:
        cats = entry.get("categories")
        if cats:
            actual[entry["sourcePageId"]] = set(cats)

    assert set(actual) == set(expected), (
        f"pages with categories differ: only in output "
        f"{sorted(set(actual) - set(expected))[:5]}, only in table "
        f"{sorted(set(expected) - set(actual))[:5]}"
    )
    mismatched = {
        pid: (sorted(actual[pid]), sorted(expected[pid]))
        for pid in expected
        if actual[pid] != expected[pid]
    }
    sample = dict(list(mismatched.items())[:5])
    assert not mismatched, (
        f"{len(mismatched)} pages carry category names deviating from "
        f"zweig_categorylinks; sample: {sample}"
    )


# Unresolved targets are diagnostics, not proof of absent source pages.
# Keep the source-table check on the shared, reviewed regression ratchet.
def test_see_references_resolve_after_pagelinks_repair(frontend_data, baseline) -> None:
    ceiling = baseline["known_issues"]["broken_see_also_refs"]
    doc = frontend_data
    anchors = {e["title"] for e in doc["entries"] if e.get("title")}
    anchors |= set(doc["redirects"].keys())
    broken = [
        ref
        for entry in doc["entries"]
        for ref in entry.get("seeAlso") or []
        if ref not in anchors
    ]
    assert len(broken) <= ceiling, (
        f"{len(broken)} unresolved See-references exceed the ratchet of "
        f"{ceiling}; sample: {broken[:5]}"
    )
