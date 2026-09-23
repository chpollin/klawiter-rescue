#!/usr/bin/env python3
"""Validate Gate-2 separation, provenance, queue coverage, and publication."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (  # noqa: E402
    AGENT_DECISIONS,
    AGENT_RECONCILIATION,
    CORRECTIONS_DIR,
    LOCATION_DECISIONS,
    LOCATION_RECONCILIATION_LOG,
    LOCATION_REVIEW_EVIDENCE,
    LOCATIONS_JSON,
    OUTPUT_EDITIONS_DIR,
    OUTPUT_FRONTEND_JSON,
    OUTPUT_JSONLD,
    OUTPUT_RECONCILIATION_DIR,
    OUTPUT_RECONCILIATION_FRONTEND,
    PROJECT_ROOT,
    SOURCE_REVISION_DECISIONS,
    STEP_04_OUTPUT,
    SZD_WORK_INDEX,
    WORK_DECISIONS,
    load_csv,
    setup_logging,
    write_json,
)
from lib.reconciliation import (  # noqa: E402
    AGENT_SOURCE_FIELDS,
    SOURCE_REVISION_RESTORE,
    SOURCE_REVISION_WITHHOLD,
    build_reconciliation,
    closes_claim,
    load_reconciliation_patches,
    merge_agent_decision_patches,
    merge_decision_patches,
    parse_szd_work_index,
)

log = setup_logging(__name__)


def _read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_public_projection(publishable: dict, dataset: dict) -> list[str]:
    links = publishable["locations"]
    errors = []
    for entry in dataset["entries"]:
        place = entry.get("locationCreated")
        if isinstance(place, dict):
            location = place.get("name")
            actual = place.get("sameAs")
        else:
            location = place
            actual = entry.get("locationSameAs")
        expected = links.get(location, {}).get("uri")
        if actual != expected:
            errors.append(
                f"{entry.get('@id')}: location link {actual!r} != reviewed {expected!r}"
            )
    return errors


def _check_decisions(result: dict) -> list[str]:
    errors = []
    decision_ids = {
        decision["decisionId"]
        for key in ("locationDecisions", "workDecisions", "agentDecisions")
        for decision in result["decisions"][key]
        if decision["action"] in {"confirm", "correct"}
    }
    for entity_type in ("locations", "works", "agents"):
        for subject, link in result["publishable"][entity_type].items():
            if link["decisionId"] not in decision_ids:
                errors.append(
                    f"{entity_type}/{subject}: public link lacks an accepted decision"
                )
            if entity_type in ("locations", "agents") and not re.fullmatch(
                r"Q\d+", link["qid"]
            ):
                errors.append(f"locations/{subject}: invalid Q-ID {link['qid']}")
    return errors


def _check_contested_claims(result: dict) -> list[str]:
    """Open claims match open decisions, decided claims match closing ones.

    An open claim keeps every reading contested; a decided claim accepts
    exactly one reading and rejects the others, and its subject was once an
    open claim. Neither publishes a link on its own.
    """
    errors = []
    decisions = [
        decision
        for key in ("locationDecisions", "workDecisions", "agentDecisions")
        for decision in result["decisions"][key]
    ]
    unresolved = sum(decision["action"] == "unresolved" for decision in decisions)
    unresolved += sum(
        decision["action"] == SOURCE_REVISION_WITHHOLD
        for decision in result["decisions"].get("sourceRevisionDecisions", [])
    )
    closed = sum(closes_claim(decision) for decision in decisions)
    claims = result["contestedClaims"]
    open_claims = [c for c in claims if c["klawiter:decisionStatus"] == "open"]
    decided = [c for c in claims if c["klawiter:decisionStatus"] == "decided"]
    if len(open_claims) != unresolved:
        errors.append(
            f"{len(open_claims)} open claims for {unresolved} unresolved decisions"
        )
    if len(decided) != closed:
        errors.append(f"{len(decided)} decided claims for {closed} closing decisions")
    if len(open_claims) + len(decided) != len(claims):
        errors.append("a claim has neither an open nor a decided status")
    for claim in claims:
        claim_id = claim["@id"]
        statuses = [
            item["klawiter:interpretationStatus"]
            for item in claim["klawiter:interpretation"]
        ]
        is_open = claim["klawiter:decisionStatus"] == "open"
        if is_open and (
            claim["klawiter:claimStatus"] != "contested"
            or set(statuses) != {"contested"}
        ):
            errors.append(f"{claim_id}: open claim is not contested throughout")
        if not is_open and (
            claim["klawiter:claimStatus"] != "resolved"
            or statuses.count("accepted") != 1
            or set(statuses) != {"accepted", "rejected"}
        ):
            errors.append(f"{claim_id}: decided claim lacks one accepted reading")
        if len(claim["klawiter:interpretation"]) < 2:
            errors.append(f"{claim_id}: competing interpretations are missing")
        if not claim["klawiter:sourceEvidence"]:
            errors.append(f"{claim_id}: exact source evidence is missing")
        if not claim["klawiter:hasReviewAction"]:
            errors.append(f"{claim_id}: review history is missing")
        for evidence in claim["klawiter:sourceEvidence"]:
            source_hash = evidence.get("sourceTextSha256")
            if source_hash and not re.fullmatch(r"[0-9a-f]{64}", source_hash):
                errors.append(f"{claim_id}: invalid source evidence hash")
    return errors


def _check_source_revisions(result: dict, source_rows: list[dict]) -> list[str]:
    """Restored pages publish their human revision, withheld ones stay redirects."""
    errors = []
    rows = {int(row["page_id"]): row for row in source_rows}
    for decision in result["decisions"].get("sourceRevisionDecisions", []):
        page_id = decision["pageId"]
        row = rows.get(page_id)
        if row is None:
            errors.append(f"source revision {page_id}: page is absent")
            continue
        is_redirect = row.get("is_redirect") in ("True", "true", "1")
        if decision["action"] == SOURCE_REVISION_RESTORE:
            restored = str(decision["humanRevision"]["textId"])
            if row.get("text_id") != restored or is_redirect:
                errors.append(
                    f"source revision {page_id}: restored text {restored} "
                    "is not the published text"
                )
        elif not is_redirect:
            errors.append(f"source revision {page_id}: withheld page is no redirect")
    return errors


def _check_agent_occurrences(result: dict) -> list[str]:
    """Every agent subject that carries a candidate must carry source
    evidence for it, or state the null finding explicitly. Without that
    evidence an unresolved decision would rest on nothing."""
    errors = []
    for subject in result["candidates"]["agents"]:
        subject_id = subject["subjectId"]
        occurrences = subject.get("sourceOccurrences")
        if occurrences is None:
            errors.append(f"{subject_id}: occurrence scan did not run")
            continue
        if subject["candidates"] and not occurrences:
            if not subject.get("sourceOccurrenceNote"):
                errors.append(
                    f"{subject_id}: candidate without occurrence evidence and "
                    "without an explicit null finding"
                )
            continue
        field = AGENT_SOURCE_FIELDS[subject["entityType"]]
        for occurrence in occurrences:
            if occurrence.get("sourceField") != field:
                errors.append(f"{subject_id}: occurrence names a foreign field")
            if occurrence.get("sourceValue") != subject["sourceName"]:
                errors.append(f"{subject_id}: occurrence value differs from subject")
            source_hash = occurrence.get("sourceTextSha256")
            if source_hash and not re.fullmatch(r"[0-9a-f]{64}", source_hash):
                errors.append(f"{subject_id}: invalid occurrence hash")
        decision = subject.get("decision")
        if decision and decision["action"] == "unresolved" and not occurrences:
            errors.append(f"{subject_id}: unresolved without source occurrences")
    return errors


def _earl(test: str, passed: bool, generated_at: str) -> dict:
    return {
        "@type": "earl:Assertion",
        "earl:assertedBy": {"@id": "klawiter:agent/gate2-validator"},
        "earl:subject": {"@id": "klawiter:dataset/gate2-reconciliation"},
        "earl:test": {"@id": f"klawiter:test/{test}"},
        "earl:mode": {"@id": "earl:automatic"},
        "earl:result": {
            "@type": "earl:TestResult",
            "earl:outcome": {"@id": "earl:passed" if passed else "earl:failed"},
            "dc:date": generated_at,
        },
    }


def main() -> None:
    output_dir = Path(OUTPUT_RECONCILIATION_DIR)
    paths = {
        "edition_dataset": Path(OUTPUT_EDITIONS_DIR) / "work-editions.jsonld",
        "locations": Path(LOCATIONS_JSON),
        "location_log": Path(LOCATION_RECONCILIATION_LOG),
        "location_decisions": Path(LOCATION_DECISIONS),
        "location_review": Path(LOCATION_REVIEW_EVIDENCE),
        "work_decisions": Path(WORK_DECISIONS),
        "szd_index": Path(SZD_WORK_INDEX),
        "classified_source": Path(STEP_04_OUTPUT),
        "agent_reconciliation": Path(AGENT_RECONCILIATION),
        "agent_decisions": Path(AGENT_DECISIONS),
        "source_revision_decisions": Path(SOURCE_REVISION_DECISIONS),
        "candidates": output_dir / "candidates.json",
        "decisions": output_dir / "decisions.json",
        "publishable": output_dir / "publishable-links.json",
        "queue": output_dir / "review-queue.json",
        "contested_claims": output_dir / "contested-claims.json",
        "manifest": output_dir / "manifest.json",
        "frontend_reconciliation": Path(OUTPUT_RECONCILIATION_FRONTEND),
        "jsonld": Path(OUTPUT_JSONLD),
        "frontend": Path(OUTPUT_FRONTEND_JSON),
    }
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(
                f"Gate 2 validation input is missing ({name}): {path}. "
                "Derived inputs are regenerable: run "
                "`python pipeline/run_pipeline.py` on a fresh clone first."
            )

    decision_patches = load_reconciliation_patches(Path(CORRECTIONS_DIR))
    location_decisions = merge_decision_patches(
        _read_json(paths["location_decisions"]),
        decision_patches["location"],
        "location",
    )
    work_decisions = merge_decision_patches(
        _read_json(paths["work_decisions"]),
        decision_patches["work"],
        "work",
    )
    agent_decisions = merge_agent_decision_patches(
        _read_json(paths["agent_decisions"]),
        decision_patches["person"] + decision_patches["publisher"],
    )
    source_rows = load_csv(STEP_04_OUTPUT)
    expected = build_reconciliation(
        _read_json(paths["edition_dataset"]),
        _read_json(paths["locations"]),
        _read_json(paths["location_log"]),
        _read_json(paths["location_review"]),
        location_decisions,
        work_decisions,
        parse_szd_work_index(paths["szd_index"]),
        source_rows,
        _read_json(paths["agent_reconciliation"]),
        agent_decisions,
        _read_json(paths["source_revision_decisions"]),
    )
    actual = {
        "candidates": _read_json(paths["candidates"]),
        "decisions": _read_json(paths["decisions"]),
        "publishable": _read_json(paths["publishable"]),
        "queue": _read_json(paths["queue"]),
        "contestedClaims": _read_json(paths["contested_claims"])["@graph"],
    }
    deterministic = expected == actual
    decision_errors = _check_decisions(actual)
    contested_errors = _check_contested_claims(actual)
    agent_occurrence_errors = _check_agent_occurrences(actual)
    source_revision_errors = _check_source_revisions(actual, source_rows)

    # SHACL over the standalone contested-claims artifact: the unified
    # claim model must satisfy the same shapes the edition graph obeys.
    from pyshacl import validate as shacl_validate
    from rdflib import Graph

    shapes_path = Path(PROJECT_ROOT) / "data" / "schema" / "work-edition-shapes.ttl"
    shapes_graph = Graph().parse(shapes_path, format="turtle")
    contested_graph = Graph().parse(str(paths["contested_claims"]), format="json-ld")
    shacl_conforms, _, shacl_text = shacl_validate(
        contested_graph,
        shacl_graph=shapes_graph,
        inference="none",
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
    )
    if len(contested_graph) < 100:
        shacl_conforms = False
        shacl_text = (
            f"contested-claims graph expands to only {len(contested_graph)} "
            "triples; an undefined @context term is dropping data"
        )
    public_errors = _check_public_projection(
        actual["publishable"], _read_json(paths["jsonld"])
    )

    frontend = _read_json(paths["frontend"])
    frontend_errors = []
    for entry in frontend["entries"]:
        location = entry.get("location")
        actual_uri = entry.get("locationSameAs")
        expected_uri = actual["publishable"]["locations"].get(location, {}).get("uri")
        if actual_uri != expected_uri:
            frontend_errors.append(
                f"entry/{entry.get('sourcePageId')}: frontend link differs from decision"
            )

    manifest = _read_json(paths["manifest"])
    input_hash_errors = []
    manifest_inputs = manifest["inputs"]
    input_map = {
        "editions": paths["edition_dataset"],
        "locations": paths["locations"],
        "location-log": paths["location_log"],
        "location-decisions": paths["location_decisions"],
        "location-review": paths["location_review"],
        "work-decisions": paths["work_decisions"],
        "szd-work-index": paths["szd_index"],
        "classified-source": paths["classified_source"],
        "agent-reconciliation": paths["agent_reconciliation"],
        "agent-decisions": paths["agent_decisions"],
        "source-revision-decisions": paths["source_revision_decisions"],
    }
    for path in decision_patches["files"]:
        input_map[f"curation-patch-{path.name}"] = path
    for name, path in input_map.items():
        if manifest_inputs[name]["sha256"] != _sha256(path):
            input_hash_errors.append(f"{name}: manifest input hash mismatch")

    checks = {
        "deterministicRebuild": deterministic,
        "decisionSeparation": not decision_errors,
        "contestedClaims": not contested_errors,
        "agentOccurrenceEvidence": not agent_occurrence_errors,
        "sourceRevisions": not source_revision_errors,
        "shacl": bool(shacl_conforms),
        "inputHashes": not input_hash_errors,
        "jsonldProjection": not public_errors,
        "frontendProjection": not frontend_errors,
    }
    errors = {
        "deterministicRebuild": []
        if deterministic
        else ["Rebuilding from frozen inputs changed a Gate 2 layer"],
        "decisionSeparation": decision_errors,
        "contestedClaims": contested_errors,
        "agentOccurrenceEvidence": agent_occurrence_errors,
        "sourceRevisions": source_revision_errors,
        "shacl": [] if shacl_conforms else [str(shacl_text)],
        "inputHashes": input_hash_errors,
        "jsonldProjection": public_errors,
        "frontendProjection": frontend_errors,
    }
    generated_at = datetime.now(timezone.utc).isoformat()
    report = {
        "generatedAt": generated_at,
        "allChecksPass": all(checks.values()),
        "checks": checks,
        "counts": manifest["counts"],
        "errors": errors,
    }
    report_path = output_dir / "validation-report.json"
    write_json(str(report_path), report, indent=2, sort_keys=True)
    earl_path = output_dir / "earl.jsonld"
    write_json(
        str(earl_path),
        {
            "@context": {
                "dc": "http://purl.org/dc/terms/",
                "earl": "http://www.w3.org/ns/earl#",
                "klawiter": "https://chpollin.github.io/klawiter-rescue/vocab/",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "dc:date": {"@type": "xsd:dateTime"},
            },
            "@graph": [
                _earl(name, passed, generated_at) for name, passed in checks.items()
            ],
        },
        indent=2,
        sort_keys=True,
    )
    manifest["validation"] = checks
    manifest["artifacts"]["validation-report.json"] = _sha256(report_path)
    manifest["artifacts"]["earl.jsonld"] = _sha256(earl_path)
    write_json(str(paths["manifest"]), manifest, indent=2, sort_keys=True)
    if not report["allChecksPass"]:
        log.error("Gate 2 validation failed: %s", errors)
        raise SystemExit(1)
    log.info(
        "Gate 2 validation passed: %d location links, %d work links",
        manifest["counts"]["publishableLocationLinks"],
        manifest["counts"]["publishableWorkLinks"],
    )


if __name__ == "__main__":
    main()
