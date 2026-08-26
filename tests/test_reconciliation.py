"""Gate-2 proposal, decision, publication, and EIL feedback contracts."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
from lib.config import (
    LOCATION_DECISIONS,
    LOCATION_RECONCILIATION_LOG,
    LOCATION_REVIEW_EVIDENCE,
    LOCATIONS_JSON,
    OUTPUT_EDITIONS_DIR,
    STEP_04_OUTPUT,
    SZD_WORK_INDEX,
    WORK_DECISIONS,
    load_csv,
)
from lib.reconciliation import (
    build_reconciliation,
    load_reconciliation_patches,
    merge_decision_patches,
    parse_szd_work_index,
)


@pytest.fixture(scope="session")
def reconciliation(required_intermediates) -> dict:
    def read(path: str | Path) -> dict | list:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    return build_reconciliation(
        read(Path(OUTPUT_EDITIONS_DIR) / "work-editions.jsonld"),
        read(LOCATIONS_JSON),
        read(LOCATION_RECONCILIATION_LOG),
        read(LOCATION_REVIEW_EVIDENCE),
        read(LOCATION_DECISIONS),
        read(WORK_DECISIONS),
        parse_szd_work_index(Path(SZD_WORK_INDEX)),
        load_csv(STEP_04_OUTPUT),
    )


def test_frozen_szd_index_and_confirmed_work_links(reconciliation: dict) -> None:
    assert len(parse_szd_work_index(Path(SZD_WORK_INDEX))) == 590
    works = reconciliation["publishable"]["works"]
    assert {work_id: link["szdId"] for work_id, link in works.items()} == {
        "klawiter:work/54": "SZDWRK.133",
        "klawiter:work/56": "SZDWRK.5",
        "klawiter:work/4916": "SZDWRK.39",
    }


def test_location_candidates_are_not_public_links(reconciliation: dict) -> None:
    published = reconciliation["publishable"]["locations"]
    assert len(published) == 26
    assert "Girona" not in published
    girona = next(
        item
        for item in reconciliation["candidates"]["locations"]
        if item["sourceLocation"] == "Girona"
    )
    assert {candidate["qid"] for candidate in girona["candidates"]} == {"Q7038"}


def test_wrong_legacy_qids_are_replaced_fail_closed(reconciliation: dict) -> None:
    published = reconciliation["publishable"]["locations"]
    assert published["Rio de Janiero"]["qid"] == "Q8678"
    assert published["Yanji"]["qid"] == "Q713362"
    assert published["Bambaī"]["qid"] == "Q1156"
    serialized = json.dumps(published)
    assert "Q2720540" not in serialized
    assert "Q26085641" not in serialized


def test_unresolved_and_unreviewed_cases_remain_in_complete_queue(
    reconciliation: dict,
) -> None:
    queue = reconciliation["queue"]
    assert queue["caseCount"] == 796
    queued = {(item["entityType"], item["subject"]): item for item in queue["cases"]}
    assert queued[("location", "Saint-Aignan")]["status"] == "unresolved"
    assert queued[("location", "Tyresö")]["status"] == "unresolved"
    assert ("work", "klawiter:work/54") not in queued


def test_unresolved_decisions_are_explicit_contested_claims(
    reconciliation: dict,
) -> None:
    claims = reconciliation["contestedClaims"]
    assert len(claims) == 5
    assert all(claim["claimStatus"] == "contested" for claim in claims)
    assert all(claim["decisionStatus"] == "open" for claim in claims)
    assert all(len(claim["interpretations"]) >= 2 for claim in claims)
    assert all(claim["sourceEvidence"] for claim in claims)
    tyreso = next(
        claim
        for claim in claims
        if claim["subject"]["@id"] == "klawiter:location/Tyresö"
    )
    assert any(
        evidence["sourceValue"] == "Tyresö" and len(evidence["sourceTextSha256"]) == 64
        for evidence in tyreso["sourceEvidence"]
    )


def test_stage_05_reads_only_publishable_links() -> None:
    stage_05 = importlib.import_module("05_to_jsonld")
    links = stage_05.load_location_wikidata()
    assert len(links) == 26
    assert links["Yanji"] == "https://www.wikidata.org/entity/Q713362"
    assert "Girona" not in links


def test_public_reconciliation_projection_is_time_independent(
    reconciliation: dict,
) -> None:
    reconcile_entities = importlib.import_module("reconcile_entities")
    edition_dataset = json.loads(
        (Path(OUTPUT_EDITIONS_DIR) / "work-editions.jsonld").read_text(encoding="utf-8")
    )
    first = reconcile_entities._frontend(reconciliation, edition_dataset)
    second = reconcile_entities._frontend(reconciliation, edition_dataset)
    assert first == second
    assert "generatedAt" not in first


def test_reconciliation_patch_supersedes_prior_decision(tmp_path: Path) -> None:
    patch_path = tmp_path / "curation.json"
    patch_path.write_text(
        json.dumps(
            {
                "reconciliationPatchVersion": 1,
                "reconciliationPatches": [
                    {
                        "entityType": "location",
                        "subject": "Tyresö",
                        "action": "confirm",
                        "qid": "Q113730",
                        "decisionId": "location/Tyreso/Q113730/editor",
                        "decidedBy": "Editor (SZD)",
                        "decidedAt": "2026-08-21T20:00:00Z",
                        "evidence": ["source-imprint"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    loaded = load_reconciliation_patches(tmp_path)
    base = json.loads(Path(LOCATION_DECISIONS).read_text(encoding="utf-8"))
    merged = merge_decision_patches(base, loaded["location"], "location")
    decision = next(item for item in merged["decisions"] if item["subject"] == "Tyresö")
    assert decision["action"] == "confirm"
    assert decision["supersedesDecisionId"] == "location/Tyreso/unresolved"


def test_generated_gate2_validation_passes() -> None:
    report = json.loads(
        Path("data/output/reconciliation/validation-report.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["allChecksPass"] is True
    assert all(report["checks"].values())


def test_gate2_provenance_paths_are_repository_relative() -> None:
    manifest = json.loads(
        Path("data/output/reconciliation/manifest.json").read_text(encoding="utf-8")
    )
    assert all(
        not Path(item["path"]).is_absolute() and "\\" not in item["path"]
        for item in manifest["inputs"].values()
    )
    provenance = json.loads(
        Path("data/output/reconciliation/provenance.jsonld").read_text(encoding="utf-8")
    )
    locations = [
        item["prov:atLocation"]
        for item in provenance["@graph"]
        if "prov:atLocation" in item
    ]
    assert locations
    assert all(not Path(path).is_absolute() and "\\" not in path for path in locations)
