"""The mutation suite of the TEI export: every deliberately wrong document fails a check.

Runs `pipeline/tei_mutations.py` with the checks of `pipeline/acceptance.py`
(profile schema and header check, without tei_all) on four samples: page 212
(one publication, values of the rules and of the language model, print
citations), page 3 (several publications from the publication layer), page
1010 (series and credits) and page 4939 (edition statement and series volume).
Each sample alone and all four together, so that every mutation finds a target.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("lxml.etree")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import acceptance  # noqa: E402
import export_tei  # noqa: E402
import tei_mutations  # noqa: E402

PAGES = [212, 3, 1010, 4939]

# Known mismatches of the canonical data, found on 2026-10-30 and kept visible:
# the print citations record no producer, so the export's @resp="#app-rules"
# on them fails `producers`, and a swapped citation producer cannot be told
# from that standing failure. Both sets are exact, so a fix shows up here.
KNOWN_FAILING: dict[int, set[str]] = {}
KNOWN_UNCAUGHT: set[str] = set()


@pytest.fixture(scope="module")
def checker():
    profile = acceptance._profile()
    meta = export_tei.load_dataset()["_meta"]
    return lambda raw, recs: (
        acceptance.check_export(raw, recs, profile=profile, meta=meta).checks
    )


@pytest.fixture(scope="module")
def all_records():
    return {
        r["sourcePageId"]: r
        for r in export_tei.exported_pages(export_tei.load_dataset())
    }


def _sample(pages: list[int], all_records: dict) -> tuple[bytes, dict]:
    raw = export_tei.serialize(export_tei.build(pages))
    return raw, {p: all_records[p] for p in pages}


@pytest.mark.parametrize("page", PAGES, ids=lambda p: f"page-{p}")
def test_the_unaltered_sample_fails_only_the_known_checks(
    page, checker, all_records
) -> None:
    checks = checker(*_sample([page], all_records))
    assert {"profile-schema", "header-provenance"} <= {c["id"] for c in checks}
    failing = {c["id"] for c in checks if c["status"] != "pass"}
    assert failing == KNOWN_FAILING.get(page, set())


@pytest.mark.parametrize("page", PAGES, ids=lambda p: f"page-{p}")
def test_every_applicable_mutation_is_caught(page, checker, all_records) -> None:
    results = tei_mutations.run(*_sample([page], all_records), check=checker)
    uncaught = {r["id"] for r in results if r["applied"] and not r["caught"]}
    known = {r["id"] for r in results if r["applied"]} & KNOWN_UNCAUGHT
    assert uncaught == known


@pytest.fixture(scope="module")
def combined(checker, all_records):
    return tei_mutations.run(*_sample(PAGES, all_records), check=checker)


def test_every_mutation_finds_a_target_and_is_caught(combined) -> None:
    assert [r["id"] for r in combined] == [m[0] for m in tei_mutations.MUTATIONS]
    assert not [r["id"] for r in combined if not r["applied"]]
    assert {r["id"] for r in combined if not r["caught"]} == KNOWN_UNCAUGHT


def test_the_profile_schema_rejects_what_no_invariant_reads(combined) -> None:
    caught = {r["id"]: r["caughtBy"] for r in combined}
    assert "profile-schema" in caught["attribute-foreign"]
    assert "profile-schema" in caught["imprint-emptied"]
    assert "profile-schema" in caught["producer-unknown"]
