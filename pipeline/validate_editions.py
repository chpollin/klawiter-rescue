#!/usr/bin/env python3
"""Validate Gate-1 Work and Edition proposals and their evidence chain.

Validation combines the published SHACL contract with repository-specific
checks for exact source selectors, stable identifiers, complete selection,
review-queue coverage, and deterministic rebuilding. Results are written as a
compact JSON report and EARL assertions linked to the automatic run.

Usage:
    python pipeline/validate_editions.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (  # noqa: E402
    EDITION_MODELING_DECISIONS,
    EDITION_SAMPLE_RECONCILIATION,
    OUTPUT_EDITIONS_DIR,
    PROJECT_ROOT,
    STEP_02_OUTPUT,
    SZD_WORK_INDEX,
    WORK_DECISIONS,
    load_csv,
    setup_logging,
    write_json,
)
from lib.editions import (  # noqa: E402
    apply_confirmed_work_links,
    apply_review_reconciliation,
    build_corpus,
)
from lib.reconciliation import parse_szd_work_index  # noqa: E402

log = setup_logging(__name__)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_selectors(dataset: dict, rows: list[dict[str, str]]) -> list[str]:
    source_by_page = {
        int(row["page_id"]): row.get("content", "")
        for row in rows
        if row.get("page_namespace", "0") == "0"
    }
    editions = {edition["@id"]: edition for edition in dataset["editions"]}
    errors: list[str] = []
    seen_bodies: set[str] = set()
    for annotation in dataset["annotations"]:
        body_id = annotation["oa:hasBody"]["@id"]
        target = annotation["oa:hasTarget"]
        source_id = target["oa:hasSource"]["@id"]
        selector = target["oa:hasSelector"]
        page_id = int(source_id.rsplit("/", 1)[1])
        start = selector["oa:start"]
        end = selector["oa:end"]
        text = source_by_page.get(page_id)
        edition = editions.get(body_id)
        seen_bodies.add(body_id)
        if text is None:
            errors.append(f"{body_id}: source page {page_id} is absent")
            continue
        if edition is None:
            errors.append(f"{body_id}: annotation body has no edition")
            continue
        if not (0 <= start < end <= len(text)):
            errors.append(f"{body_id}: invalid selector [{start}, {end})")
            continue
        block = text[start:end]
        if not block.startswith(edition["klawiter:headerLine"]):
            errors.append(f"{body_id}: selector does not start with its exact header")
        source_hash = hashlib.sha256(block.encode("utf-8")).hexdigest()
        if source_hash != edition["klawiter:sourceSliceSha256"]:
            errors.append(f"{body_id}: source slice hash mismatch")
        if edition["klawiter:sourcePageId"] != page_id:
            errors.append(f"{body_id}: sourcePageId disagrees with annotation source")
    missing_annotations = set(editions).difference(seen_bodies)
    errors.extend(
        f"{edition_id}: missing annotation" for edition_id in missing_annotations
    )
    return errors


def _check_review_queue(dataset: dict, queue: dict) -> list[str]:
    review_required = {
        edition["@id"]
        for edition in dataset["editions"]
        if edition["klawiter:reviewStatus"] != "confirmed"
        and (
            edition["klawiter:reviewFlags"]
            or edition["klawiter:reviewStatus"] == "contested"
        )
    }
    queued = {case["editionId"] for case in queue["cases"]}
    errors: list[str] = []
    for edition_id in sorted(review_required.difference(queued)):
        errors.append(f"{edition_id}: review-required edition absent from queue")
    for edition_id in sorted(queued.difference(review_required)):
        errors.append(f"{edition_id}: queued without review evidence")
    for case in queue["cases"]:
        if case["reviewStatus"] not in {"proposed", "contested"}:
            errors.append(
                f"{case['editionId']}: confirmed decision remains in the review queue"
            )
    return errors


def _check_unique_ids(dataset: dict) -> list[str]:
    identifiers = [
        node["@id"]
        for collection in (
            "works",
            "editions",
            "annotations",
            "carriers",
            "contestedClaims",
            "candidateWorks",
        )
        for node in dataset[collection]
    ]
    for claim in dataset["contestedClaims"]:
        identifiers.extend(
            item["@id"]
            for key in ("klawiter:interpretation", "klawiter:hasReviewAction")
            for item in claim[key]
        )
    duplicates = sorted(
        identifier
        for identifier in set(identifiers)
        if identifiers.count(identifier) > 1
    )
    return [f"Duplicate identifier: {identifier}" for identifier in duplicates]


def _check_contested_claims(dataset: dict) -> list[str]:
    claims = {claim["@id"]: claim for claim in dataset["contestedClaims"]}
    annotations = {
        annotation["oa:hasBody"]["@id"]: annotation
        for annotation in dataset["annotations"]
    }
    work_examples = {
        example["@id"]
        for work in dataset["works"]
        for example in work["schema:workExample"]
    }
    candidate_ids = {item["@id"] for item in dataset["candidateWorks"]}
    errors: list[str] = []
    for edition in dataset["editions"]:
        edition_id = edition["@id"]
        claim_ref = edition.get("klawiter:hasContestedClaim")
        if edition["klawiter:reviewStatus"] != "contested":
            if claim_ref:
                errors.append(f"{edition_id}: non-contested edition has a claim")
            continue
        if not claim_ref or claim_ref["@id"] not in claims:
            errors.append(f"{edition_id}: contested edition lacks its claim")
            continue
        if "schema:exampleOfWork" in edition or edition_id in work_examples:
            errors.append(f"{edition_id}: contested binding is asserted as confirmed")
        claim = claims[claim_ref["@id"]]
        if claim["klawiter:claimSubject"]["@id"] != edition_id:
            errors.append(f"{claim['@id']}: claim subject mismatch")
        if claim["klawiter:decisionStatus"] != "open":
            errors.append(f"{claim['@id']}: contested claim is not open")
        annotation = annotations[edition_id]
        if claim["oa:hasTarget"] != annotation["oa:hasTarget"]:
            errors.append(f"{claim['@id']}: exact source target changed")
        if claim["klawiter:sourceSliceSha256"] != edition["klawiter:sourceSliceSha256"]:
            errors.append(f"{claim['@id']}: source slice hash mismatch")
        interpretations = claim["klawiter:interpretation"]
        if len(interpretations) < 2:
            errors.append(f"{claim['@id']}: fewer than two interpretations")
        proposed = {item["klawiter:proposedObject"]["@id"] for item in interpretations}
        missing_candidates = {
            item for item in proposed if item.startswith("klawiter:work-candidate/")
        }.difference(candidate_ids)
        if missing_candidates:
            errors.append(
                f"{claim['@id']}: missing candidate works {sorted(missing_candidates)}"
            )
        if len(claim["klawiter:hasReviewAction"]) < 3:
            errors.append(f"{claim['@id']}: incomplete review history")
    referenced_claims = {
        edition["klawiter:hasContestedClaim"]["@id"]
        for edition in dataset["editions"]
        if edition.get("klawiter:hasContestedClaim")
    }
    for claim_id in sorted(set(claims).difference(referenced_claims)):
        errors.append(f"{claim_id}: unreferenced contested claim")
    return errors


def _earl_assertion(test: str, passed: bool, generated_at: str) -> dict:
    return {
        "@type": "earl:Assertion",
        "earl:assertedBy": {"@id": "klawiter:agent/edition-validator"},
        "earl:subject": {"@id": "klawiter:dataset/work-editions"},
        "earl:test": {"@id": f"klawiter:test/{test}"},
        "earl:mode": {"@id": "earl:automatic"},
        "earl:result": {
            "@type": "earl:TestResult",
            "earl:outcome": {"@id": "earl:passed" if passed else "earl:failed"},
            "dc:date": generated_at,
        },
    }


def main() -> None:
    output_dir = Path(OUTPUT_EDITIONS_DIR)
    dataset_path = output_dir / "work-editions.jsonld"
    queue_path = output_dir / "review-queue.json"
    shapes_path = Path(PROJECT_ROOT) / "data" / "schema" / "work-edition-shapes.ttl"
    reconciliation_path = Path(EDITION_SAMPLE_RECONCILIATION)
    modeling_path = Path(EDITION_MODELING_DECISIONS)
    for path in (
        dataset_path,
        queue_path,
        shapes_path,
        Path(STEP_02_OUTPUT),
        reconciliation_path,
        modeling_path,
    ):
        if not path.exists():
            raise FileNotFoundError(f"Required Gate-1 input is missing: {path}")

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    rows = load_csv(STEP_02_OUTPUT)

    data_graph = Graph().parse(
        data=dataset_path.read_text(encoding="utf-8"), format="json-ld"
    )
    shapes_graph = Graph().parse(shapes_path, format="turtle")
    shacl_conforms, _, shacl_text = validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference="none",
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
    )

    selector_errors = _check_selectors(dataset, rows)
    queue_errors = _check_review_queue(dataset, queue)
    identifier_errors = _check_unique_ids(dataset)
    contested_errors = _check_contested_claims(dataset)
    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
    modeling_decisions = json.loads(modeling_path.read_text(encoding="utf-8"))
    rebuilt = apply_review_reconciliation(
        build_corpus(rows), reconciliation, modeling_decisions
    )
    apply_confirmed_work_links(
        rebuilt,
        json.loads(Path(WORK_DECISIONS).read_text(encoding="utf-8")),
        parse_szd_work_index(Path(SZD_WORK_INDEX)),
    )
    deterministic = rebuilt == dataset
    checks = {
        "shacl": bool(shacl_conforms),
        "selectors": not selector_errors,
        "stableIdentifiers": not identifier_errors,
        "reviewQueue": not queue_errors,
        "contestedClaims": not contested_errors,
        "deterministicRebuild": deterministic,
    }
    errors = {
        "selectors": selector_errors,
        "stableIdentifiers": identifier_errors,
        "reviewQueue": queue_errors,
        "contestedClaims": contested_errors,
    }
    if not deterministic:
        errors["deterministicRebuild"] = [
            "Rebuilding from the same stage-02 source changed the proposal graph"
        ]
    if not shacl_conforms:
        errors["shacl"] = [str(shacl_text)]

    generated_at = datetime.now(timezone.utc).isoformat()
    report = {
        "generatedAt": generated_at,
        "allChecksPass": all(checks.values()),
        "checks": checks,
        "counts": {
            "works": len(dataset["works"]),
            "editions": len(dataset["editions"]),
            "annotations": len(dataset["annotations"]),
            "carriers": len(dataset["carriers"]),
            "contestedClaims": len(dataset["contestedClaims"]),
            "candidateWorks": len(dataset["candidateWorks"]),
            "confirmedEditions": sum(
                edition["klawiter:reviewStatus"] == "confirmed"
                for edition in dataset["editions"]
            ),
            "contestedEditions": sum(
                edition["klawiter:reviewStatus"] == "contested"
                for edition in dataset["editions"]
            ),
            "reviewCases": len(queue["cases"]),
        },
        "errors": errors,
        "shaclReport": str(shacl_text),
    }
    report_path = output_dir / "validation-report.json"
    write_json(str(report_path), report, indent=2, sort_keys=True)
    earl = {
        "@context": {
            "dc": "http://purl.org/dc/terms/",
            "earl": "http://www.w3.org/ns/earl#",
            "klawiter": "https://chpollin.github.io/klawiter-rescue/vocab/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "dc:date": {"@type": "xsd:dateTime"},
        },
        "@graph": [
            _earl_assertion(test, passed, generated_at)
            for test, passed in checks.items()
        ],
    }
    earl_path = output_dir / "earl.jsonld"
    write_json(str(earl_path), earl, indent=2, sort_keys=True)
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["validation"] = checks
    manifest["artifacts"]["validation-report.json"] = _sha256(report_path)
    manifest["artifacts"]["earl.jsonld"] = _sha256(earl_path)
    write_json(str(manifest_path), manifest, indent=2, sort_keys=True)
    if not report["allChecksPass"]:
        log.error("Gate 1 validation failed: %s", errors)
        raise SystemExit(1)
    log.info(
        "Gate 1 validation passed: %d works, %d editions, %d review cases",
        report["counts"]["works"],
        report["counts"]["editions"],
        report["counts"]["reviewCases"],
    )


if __name__ == "__main__":
    main()
