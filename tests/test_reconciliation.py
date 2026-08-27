"""Gate-2 proposal, decision, publication, and EIL feedback contracts."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
from lib.config import (
    AGENT_DECISIONS,
    AGENT_RECONCILIATION,
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
        read(AGENT_RECONCILIATION),
        read(AGENT_DECISIONS),
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


def test_agent_candidates_are_fail_closed(reconciliation: dict) -> None:
    """101 frozen agent subjects join the review pool; without a single
    decision nothing publishes and every subject queues."""
    agents = reconciliation["candidates"]["agents"]
    assert len(agents) == 101
    assert all(subject["decision"] is None for subject in agents)
    assert reconciliation["publishable"]["agents"] == {}
    queued = {
        (case["entityType"], case["subject"])
        for case in reconciliation["queue"]["cases"]
    }
    assert all(
        (subject["entityType"], subject["sourceName"]) in queued for subject in agents
    )


def test_unresolved_and_unreviewed_cases_remain_in_complete_queue(
    reconciliation: dict,
) -> None:
    queue = reconciliation["queue"]
    assert queue["caseCount"] == 796 + 101
    queued = {(item["entityType"], item["subject"]): item for item in queue["cases"]}
    assert queued[("location", "Saint-Aignan")]["status"] == "unresolved"
    assert queued[("location", "Tyresö")]["status"] == "unresolved"
    assert ("work", "klawiter:work/54") not in queued


def test_unresolved_decisions_are_explicit_contested_claims(
    reconciliation: dict,
) -> None:
    claims = reconciliation["contestedClaims"]
    assert len(claims) == 5
    assert all(claim["klawiter:claimStatus"] == "contested" for claim in claims)
    assert all(claim["klawiter:decisionStatus"] == "open" for claim in claims)
    assert all(len(claim["klawiter:interpretation"]) >= 2 for claim in claims)
    assert all(claim["klawiter:sourceEvidence"] for claim in claims)
    tyreso = next(
        claim
        for claim in claims
        if claim["klawiter:claimSubject"]["@id"] == "klawiter:location/Tyres%C3%B6"
    )
    assert tyreso["klawiter:claimSubject"]["schema:name"] == "Tyresö"
    assert any(
        evidence["sourceValue"] == "Tyresö" and len(evidence["sourceTextSha256"]) == 64
        for evidence in tyreso["klawiter:sourceEvidence"]
    )


def test_stage_05_reads_only_publishable_links() -> None:
    stage_05 = importlib.import_module("05_to_jsonld")
    links = stage_05.load_location_wikidata()
    assert len(links) == 26
    assert links["Yanji"] == "http://www.wikidata.org/entity/Q713362"
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


AGENT_OCCURRENCE_FIELDS = {"person": "translator", "publisher": "publisher"}


def test_agent_subjects_carry_source_occurrence_evidence(reconciliation: dict) -> None:
    """Every agent subject with a candidate needs source evidence or an
    explicit null finding; without it no unresolved decision is arguable."""
    subjects = reconciliation["candidates"]["agents"]
    with_candidates = [subject for subject in subjects if subject["candidates"]]
    assert with_candidates
    for subject in subjects:
        occurrences = subject["sourceOccurrences"]
        if subject["candidates"]:
            assert occurrences or subject.get("sourceOccurrenceNote"), (
                f"{subject['subjectId']} has candidates without occurrence evidence"
            )
        field = AGENT_OCCURRENCE_FIELDS[subject["entityType"]]
        for occurrence in occurrences:
            assert occurrence["sourceField"] == field
            assert occurrence["sourceValue"] == subject["sourceName"]
            assert occurrence["sourcePath"] == "data/intermediate/04_classified.csv"
            assert isinstance(occurrence["sourcePageId"], int)
            assert occurrence["sourceMatchMode"] in {"field-value", "field-value-line"}
            if occurrence["sourceMatchMode"] == "field-value-line":
                assert len(occurrence["sourceTextSha256"]) == 64
                assert occurrence["sourceText"]
                assert occurrence["sourceLine"] >= 1


def test_agent_occurrence_pages_match_the_classified_source(
    reconciliation: dict,
) -> None:
    rows = load_csv(STEP_04_OUTPUT)
    for subject in reconciliation["candidates"]["agents"][:5]:
        field = AGENT_OCCURRENCE_FIELDS[subject["entityType"]]
        expected = {
            int(row["page_id"]) for row in rows if row[field] == subject["sourceName"]
        }
        found = {
            occurrence["sourcePageId"] for occurrence in subject["sourceOccurrences"]
        }
        assert found == expected


def test_agent_occurrences_are_deterministically_ordered(reconciliation: dict) -> None:
    for subject in reconciliation["candidates"]["agents"]:
        keys = [
            (
                occurrence["sourcePageId"],
                occurrence["sourceTextId"] or 0,
                occurrence["sourceLine"] or 0,
            )
            for occurrence in subject["sourceOccurrences"]
        ]
        assert keys == sorted(keys)
        ids = [occurrence["@id"] for occurrence in subject["sourceOccurrences"]]
        assert len(ids) == len(set(ids))


def _rebuild_with_agent_decision(decision: dict) -> dict:
    def read(path: str | Path) -> dict | list:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    agent_decisions = read(AGENT_DECISIONS)
    agent_decisions = {**agent_decisions, "decisions": [decision]}
    return build_reconciliation(
        read(Path(OUTPUT_EDITIONS_DIR) / "work-editions.jsonld"),
        read(LOCATIONS_JSON),
        read(LOCATION_RECONCILIATION_LOG),
        read(LOCATION_REVIEW_EVIDENCE),
        read(LOCATION_DECISIONS),
        read(WORK_DECISIONS),
        parse_szd_work_index(Path(SZD_WORK_INDEX)),
        load_csv(STEP_04_OUTPUT),
        read(AGENT_RECONCILIATION),
        agent_decisions,
    )


def test_unresolved_agent_decision_becomes_a_contested_claim(
    reconciliation: dict,
) -> None:
    """The occurrence scan is what makes an unresolved agent decision
    representable: it supplies the source evidence the claim requires."""
    subject = next(
        item
        for item in reconciliation["candidates"]["agents"]
        if item["candidates"] and item["sourceOccurrences"]
    )
    rebuilt = _rebuild_with_agent_decision(
        {
            "entityType": subject["entityType"],
            "subject": subject["sourceName"],
            "action": "unresolved",
            "decisionId": f"agent/{subject['sourceName']}/unresolved",
            "decidedBy": "independent-verification-agent",
            "decidedAt": "2026-08-27T10:00:00Z",
            "evidence": ["source-imprint"],
        }
    )
    claim = next(
        item
        for item in rebuilt["contestedClaims"]
        if item["klawiter:claimSubject"]["@id"] == subject["subjectId"]
    )
    assert claim["klawiter:identityScope"] == subject["entityType"]
    assert claim["klawiter:claimStatus"] == "contested"
    assert claim["klawiter:decisionStatus"] == "open"
    assert len(claim["klawiter:interpretation"]) >= 2
    assert claim["klawiter:sourceEvidence"] == subject["sourceOccurrences"]
    assert rebuilt["publishable"]["agents"] == {}


def test_public_agent_projection_carries_occurrence_evidence(
    reconciliation: dict,
) -> None:
    reconcile_entities = importlib.import_module("reconcile_entities")
    edition_dataset = json.loads(
        (Path(OUTPUT_EDITIONS_DIR) / "work-editions.jsonld").read_text(encoding="utf-8")
    )
    frontend = reconcile_entities._frontend(reconciliation, edition_dataset)
    assert frontend["schemaVersion"] == "1.1"
    subject = reconciliation["candidates"]["agents"][0]
    key = f"{subject['entityType']}/{subject['sourceName']}"
    projected = frontend["agents"][key]
    # The internal pipeline path stays out of the published projection, the
    # same rule the contested-claim projection follows.
    assert projected["sourceOccurrences"] == [
        {name: value for name, value in occurrence.items() if name != "sourcePath"}
        for occurrence in subject["sourceOccurrences"]
    ]
