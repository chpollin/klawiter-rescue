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
    STEP_04_OUTPUT,
    SZD_WORK_INDEX,
    WORK_DECISIONS,
    load_csv,
    setup_logging,
    write_json,
)
from lib.reconciliation import (  # noqa: E402
    build_reconciliation,
    load_reconciliation_patches,
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
        location = entry.get("locationCreated")
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
        for key in ("locationDecisions", "workDecisions")
        for decision in result["decisions"][key]
        if decision["action"] in {"confirm", "correct"}
    }
    for entity_type in ("locations", "works"):
        for subject, link in result["publishable"][entity_type].items():
            if link["decisionId"] not in decision_ids:
                errors.append(
                    f"{entity_type}/{subject}: public link lacks an accepted decision"
                )
            if entity_type == "locations" and not re.fullmatch(r"Q\d+", link["qid"]):
                errors.append(f"locations/{subject}: invalid Q-ID {link['qid']}")
    return errors


def _check_contested_claims(result: dict) -> list[str]:
    errors = []
    unresolved = sum(
        decision["action"] == "unresolved"
        for key in ("locationDecisions", "workDecisions")
        for decision in result["decisions"][key]
    )
    claims = result["contestedClaims"]
    if len(claims) != unresolved:
        errors.append(
            f"{len(claims)} contested claims for {unresolved} unresolved decisions"
        )
    for claim in claims:
        claim_id = claim["@id"]
        if claim["claimStatus"] != "contested" or claim["decisionStatus"] != "open":
            errors.append(f"{claim_id}: claim status is not contested/open")
        if len(claim["interpretations"]) < 2:
            errors.append(f"{claim_id}: competing interpretations are missing")
        if not claim["sourceEvidence"]:
            errors.append(f"{claim_id}: exact source evidence is missing")
        if not claim["reviewHistory"]:
            errors.append(f"{claim_id}: review history is missing")
        for evidence in claim["sourceEvidence"]:
            source_hash = evidence.get("sourceTextSha256")
            if source_hash and not re.fullmatch(r"[0-9a-f]{64}", source_hash):
                errors.append(f"{claim_id}: invalid source evidence hash")
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
    expected = build_reconciliation(
        _read_json(paths["edition_dataset"]),
        _read_json(paths["locations"]),
        _read_json(paths["location_log"]),
        _read_json(paths["location_review"]),
        location_decisions,
        work_decisions,
        parse_szd_work_index(paths["szd_index"]),
        load_csv(STEP_04_OUTPUT),
    )
    actual = {
        "candidates": _read_json(paths["candidates"]),
        "decisions": _read_json(paths["decisions"]),
        "publishable": _read_json(paths["publishable"]),
        "queue": _read_json(paths["queue"]),
        "contestedClaims": _read_json(paths["contested_claims"]),
    }
    deterministic = expected == actual
    decision_errors = _check_decisions(actual)
    contested_errors = _check_contested_claims(actual)
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
