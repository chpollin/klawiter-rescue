"""The mutation suite of the TEI export: every deliberately wrong document fails a check.

Runs `pipeline/tei_mutations.py` on two samples, page 212 (one publication,
values of the rules and of the language model) and page 3 (an edition page
whose publication layer gives several publications), with the checks of
`pipeline/acceptance.py` against the profile schema and without tei_all.
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

PAGES = [212, 3]


@pytest.fixture(scope="module")
def profile():
    return acceptance._profile()


@pytest.fixture(scope="module", params=PAGES, ids=lambda p: f"page-{p}")
def sample(request, profile):
    page = request.param
    records = {
        r["sourcePageId"]: r
        for r in export_tei.exported_pages(export_tei.load_dataset())
        if r["sourcePageId"] == page
    }
    raw = export_tei.serialize(export_tei.build([page]))
    return raw, records


def _check(profile):
    return lambda raw, recs: acceptance.check_export(raw, recs, profile=profile).checks


def test_the_unaltered_sample_passes_every_check(sample, profile) -> None:
    raw, records = sample
    checks = _check(profile)(raw, records)
    assert "profile-schema" in {c["id"] for c in checks}
    failing = {c["id"]: c["examples"] for c in checks if c["status"] != "pass"}
    assert not failing, failing


@pytest.fixture(scope="module")
def results(sample, profile):
    raw, records = sample
    return tei_mutations.run(raw, records, check=_check(profile))


def test_every_mutation_is_applied_and_caught(results) -> None:
    assert [r["id"] for r in results] == [m[0] for m in tei_mutations.MUTATIONS]
    not_applied = [r["id"] for r in results if not r["applied"]]
    assert not not_applied, f"found nothing to mutate: {not_applied}"
    uncaught = [r["id"] for r in results if not r["caught"]]
    assert not uncaught, f"caught by no check: {uncaught}"


def test_the_profile_schema_rejects_what_no_invariant_reads(results) -> None:
    """A foreign attribute only the schema sees; an empty imprint and an unknown producer it sees too."""
    caught = {r["id"]: r["caughtBy"] for r in results}
    assert caught["attribute-foreign"] == ["profile-schema"]
    assert "profile-schema" in caught["imprint-emptied"]
    assert "profile-schema" in caught["producer-unknown"]
