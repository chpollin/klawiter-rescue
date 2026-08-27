#!/usr/bin/env python3
"""Build Gate-2 candidates, reviewed decisions, public links, and EIL data."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (  # noqa: E402
    AGENT_DECISIONS,
    AGENT_RECONCILIATION,
    CORRECTIONS_DIR,
    EDITION_MODELING_DECISIONS,
    LOCATION_DECISIONS,
    LOCATION_RECONCILIATION_LOG,
    LOCATION_REVIEW_EVIDENCE,
    LOCATIONS_JSON,
    OUTPUT_EDITIONS_DIR,
    OUTPUT_RECONCILIATION_DIR,
    OUTPUT_RECONCILIATION_FRONTEND,
    PROJECT_ROOT,
    STEP_04_OUTPUT,
    SZD_WORK_INDEX,
    WORK_DECISIONS,
    load_csv,
    setup_logging,
    write_json,
)
from lib.reconciliation import (  # noqa: E402
    ALGORITHM_VERSION,
    build_reconciliation,
    load_reconciliation_patches,
    merge_agent_decision_patches,
    merge_decision_patches,
    parse_szd_work_index,
)

log = setup_logging(__name__)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _repository_path(path: Path) -> str:
    """Return a portable path and reject provenance inputs outside the checkout."""
    try:
        return path.resolve().relative_to(Path(PROJECT_ROOT).resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"Gate 2 input is outside the repository: {path}") from exc


def _provenance(generated_at: str, inputs: dict[str, dict], code_hash: str) -> dict:
    used = [{"@id": f"klawiter:gate2-input/{name}"} for name in sorted(inputs)]
    graph = [
        {
            "@id": "klawiter:run/gate2-reconciliation",
            "@type": "prov:Activity",
            "prov:generatedAtTime": generated_at,
            "prov:used": used,
            "prov:qualifiedAssociation": {
                "@type": "prov:Association",
                "prov:agent": {"@id": "klawiter:agent/gate2-builder"},
                "prov:hadPlan": {"@id": "klawiter:plan/gate2-v1"},
            },
        },
        {
            "@id": "klawiter:agent/gate2-builder",
            "@type": ["prov:SoftwareAgent", "earl:Software"],
            "schema:name": "Klawiter deterministic Gate 2 reconciliation builder",
        },
        {
            "@id": "klawiter:plan/gate2-v1",
            "@type": "prov:Plan",
            "klawiter:algorithmVersion": ALGORITHM_VERSION,
            "klawiter:sourceCodeSha256": code_hash,
        },
    ]
    graph.extend(
        {
            "@id": f"klawiter:gate2-input/{name}",
            "@type": "prov:Entity",
            "prov:atLocation": item["path"],
            "klawiter:sha256": item["sha256"],
        }
        for name, item in sorted(inputs.items())
    )
    return {
        "@context": {
            "schema": "https://schema.org/",
            "klawiter": "https://chpollin.github.io/klawiter-rescue/vocab/",
            "prov": "http://www.w3.org/ns/prov#",
            "earl": "http://www.w3.org/ns/earl#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "prov:generatedAtTime": {"@type": "xsd:dateTime"},
        },
        "@graph": graph,
    }


# Context for the standalone contested-claims artifact: every key is a
# defined term, so the file expands to real RDF instead of silently
# dropping subtrees.
CONTESTED_CONTEXT = {
    "@context": {
        "schema": "https://schema.org/",
        "klawiter": "https://chpollin.github.io/klawiter-rescue/vocab/",
        "prov": "http://www.w3.org/ns/prov#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "klawiter:interpretation": {"@container": "@set"},
        "klawiter:hasReviewAction": {"@container": "@set"},
        "klawiter:sourceEvidence": {"@container": "@set"},
        "klawiter:evidence": {"@container": "@set"},
        "klawiter:decidedAt": {"@type": "xsd:dateTime"},
        # Source-occurrence evidence keys
        "sourcePageId": {"@id": "klawiter:sourcePageId", "@type": "xsd:integer"},
        "sourceLine": {"@id": "klawiter:sourceLine", "@type": "xsd:integer"},
        "sourceValue": "klawiter:sourceValue",
        "sourceTextSha256": "klawiter:sourceTextSha256",
        "sourcePath": "klawiter:sourcePath",
        "sourceTitle": "klawiter:sourceTitle",
        "sourceField": "klawiter:sourceField",
    }
}


def _frontend_authority_claims(claims: list[dict]) -> list[dict]:
    """Project the unified contested-claim model onto the stable UI shape
    the detail view renders; the data model may evolve independently."""
    projected = []
    for claim in claims:
        projected.append(
            {
                "claimId": claim["@id"],
                "entityType": claim["klawiter:identityScope"],
                "subject": {
                    "@id": claim["klawiter:claimSubject"]["@id"],
                    "name": claim["klawiter:claimSubject"].get("schema:name"),
                },
                "predicate": {"@id": claim["klawiter:claimPredicate"]["@id"]},
                "claimStatus": claim["klawiter:claimStatus"],
                "decisionStatus": claim["klawiter:decisionStatus"],
                # The internal pipeline path of an occurrence stays out of
                # the published projection.
                "sourceEvidence": [
                    {k: v for k, v in evidence.items() if k != "sourcePath"}
                    for evidence in claim["klawiter:sourceEvidence"]
                ],
                "interpretations": [
                    {
                        "interpretationId": item["@id"],
                        "label": item["schema:name"],
                        "proposedObject": item.get("klawiter:proposedObject"),
                        "status": item["klawiter:interpretationStatus"],
                        "candidateId": item.get("klawiter:candidateId"),
                        "candidateSource": item.get("klawiter:candidateSource"),
                    }
                    for item in claim["klawiter:interpretation"]
                ],
                "reviewHistory": [
                    {
                        "reviewId": item["@id"],
                        "decisionId": item["klawiter:decisionId"],
                        "action": item["klawiter:reviewOutcome"],
                        "decidedBy": item["prov:wasAssociatedWith"]["schema:name"],
                        "decidedAt": item.get("klawiter:decidedAt"),
                        "evidence": item["klawiter:evidence"],
                    }
                    for item in claim["klawiter:hasReviewAction"]
                ],
            }
        )
    return projected


def _frontend(result: dict, edition_dataset: dict) -> dict:
    location_items = {}
    for subject in result["candidates"]["locations"]:
        name = subject["sourceLocation"]
        location_items[name] = {
            "candidates": subject["candidates"],
            "decision": subject.get("decision"),
            "publishable": result["publishable"]["locations"].get(name),
            "legacyStatus": subject["legacyStatus"],
        }
    edition_claims: dict[str, list[dict]] = {}
    for claim in edition_dataset["contestedClaims"]:
        page_id = str(claim["klawiter:sourcePageId"])
        selector = claim["oa:hasTarget"]["oa:hasSelector"]
        edition_claims.setdefault(page_id, []).append(
            {
                "claimId": claim["@id"],
                "claimStatus": claim["klawiter:claimStatus"],
                "decisionStatus": claim["klawiter:decisionStatus"],
                "subject": claim["klawiter:claimSubject"]["@id"],
                "predicate": claim["klawiter:claimPredicate"]["@id"],
                "source": {
                    "sourcePageId": claim["klawiter:sourcePageId"],
                    "selector": [selector["oa:start"], selector["oa:end"]],
                    "sliceSha256": claim["klawiter:sourceSliceSha256"],
                },
                "interpretations": [
                    {
                        "interpretationId": item["@id"],
                        "label": item["schema:name"],
                        "basis": item["schema:description"],
                        "proposedObject": item["klawiter:proposedObject"]["@id"],
                        "status": item["klawiter:interpretationStatus"],
                    }
                    for item in claim["klawiter:interpretation"]
                ],
                "reviewHistory": [
                    {
                        "reviewId": item["@id"],
                        "reviewer": item["prov:wasAssociatedWith"]["@id"],
                        "outcome": item["klawiter:reviewOutcome"],
                        "basis": item.get("klawiter:reviewBasis"),
                    }
                    for item in claim["klawiter:hasReviewAction"]
                ],
            }
        )
    return {
        # 1.1 added source-occurrence evidence to the agent subjects.
        "schemaVersion": "1.1",
        "contract": result["publishable"]["publicationContract"],
        "summary": {
            "locationSubjects": len(result["candidates"]["locations"]),
            "workSubjects": len(result["candidates"]["works"]),
            "publishedLocationLinks": len(result["publishable"]["locations"]),
            "publishedWorkLinks": len(result["publishable"]["works"]),
            "reviewCases": result["queue"]["caseCount"],
            "contestedAuthorityClaims": len(result["contestedClaims"]),
            "contestedEditionClaims": sum(
                len(items) for items in edition_claims.values()
            ),
        },
        "locations": location_items,
        "works": result["candidates"]["works"],
        "agents": {
            f"{subject['entityType']}/{subject['sourceName']}": {
                "kind": subject["entityType"],
                "name": subject["sourceName"],
                "occurrences": subject["occurrences"],
                # The internal pipeline path of an occurrence stays out of
                # the published projection.
                "sourceOccurrences": [
                    {
                        key: value
                        for key, value in occurrence.items()
                        if key != "sourcePath"
                    }
                    for occurrence in subject["sourceOccurrences"]
                ],
                **(
                    {"sourceOccurrenceNote": subject["sourceOccurrenceNote"]}
                    if subject.get("sourceOccurrenceNote")
                    else {}
                ),
                "candidates": subject["candidates"],
                "decision": subject.get("decision"),
                "publishable": result["publishable"]["agents"].get(
                    f"{subject['entityType']}/{subject['sourceName']}"
                ),
            }
            for subject in result["candidates"]["agents"]
        },
        "contestedClaims": _frontend_authority_claims(result["contestedClaims"]),
        "editionClaims": edition_claims,
    }


def main() -> None:
    output_dir = Path(OUTPUT_RECONCILIATION_DIR)
    input_paths = {
        "editions": Path(OUTPUT_EDITIONS_DIR) / "work-editions.jsonld",
        "locations": Path(LOCATIONS_JSON),
        "location-log": Path(LOCATION_RECONCILIATION_LOG),
        "location-decisions": Path(LOCATION_DECISIONS),
        "location-review": Path(LOCATION_REVIEW_EVIDENCE),
        "work-decisions": Path(WORK_DECISIONS),
        "szd-work-index": Path(SZD_WORK_INDEX),
        "edition-modeling-decisions": Path(EDITION_MODELING_DECISIONS),
        "classified-source": Path(STEP_04_OUTPUT),
        "agent-reconciliation": Path(AGENT_RECONCILIATION),
        "agent-decisions": Path(AGENT_DECISIONS),
    }
    for description, path in input_paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Gate 2 input is missing ({description}): {path}")

    decision_patches = load_reconciliation_patches(Path(CORRECTIONS_DIR))
    for path in decision_patches["files"]:
        input_paths[f"curation-patch-{path.name}"] = path
    inputs = {
        name: {
            "path": _repository_path(path),
            "sha256": _sha256(path),
        }
        for name, path in input_paths.items()
    }
    edition_dataset = _read_json(input_paths["editions"])
    locations = _read_json(input_paths["locations"])
    location_log = _read_json(input_paths["location-log"])
    location_decisions = _read_json(input_paths["location-decisions"])
    location_review = _read_json(input_paths["location-review"])
    work_decisions = _read_json(input_paths["work-decisions"])
    location_decisions = merge_decision_patches(
        location_decisions, decision_patches["location"], "location"
    )
    work_decisions = merge_decision_patches(
        work_decisions, decision_patches["work"], "work"
    )
    agent_decisions = merge_agent_decision_patches(
        _read_json(input_paths["agent-decisions"]),
        decision_patches["person"] + decision_patches["publisher"],
    )
    authorities = parse_szd_work_index(input_paths["szd-work-index"])
    result = build_reconciliation(
        edition_dataset,
        locations,
        location_log,
        location_review,
        location_decisions,
        work_decisions,
        authorities,
        load_csv(STEP_04_OUTPUT),
        _read_json(input_paths["agent-reconciliation"]),
        agent_decisions,
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    # LF-normalize so the recorded provenance hash is independent of the
    # git eol settings that produced the working copy.
    code_hash = hashlib.sha256(
        Path(__file__).read_bytes().replace(b"\r\n", b"\n")
        + (Path(__file__).parent / "lib" / "reconciliation.py")
        .read_bytes()
        .replace(b"\r\n", b"\n")
    ).hexdigest()

    artifacts = {
        "candidates.json": result["candidates"],
        "decisions.json": result["decisions"],
        "publishable-links.json": result["publishable"],
        "review-queue.json": result["queue"],
        "contested-claims.json": {
            **CONTESTED_CONTEXT,
            "@graph": result["contestedClaims"],
        },
        "provenance.jsonld": _provenance(generated_at, inputs, code_hash),
    }
    for name, document in artifacts.items():
        write_json(str(output_dir / name), document, indent=2, sort_keys=True)
    frontend = _frontend(result, edition_dataset)
    write_json(
        OUTPUT_RECONCILIATION_FRONTEND,
        frontend,
        separators=(",", ":"),
        sort_keys=True,
    )

    manifest = {
        "generatedAt": generated_at,
        "algorithmVersion": ALGORITHM_VERSION,
        "codeSha256": code_hash,
        "inputs": inputs,
        "counts": {
            "locationSubjects": len(result["candidates"]["locations"]),
            "locationCandidates": sum(
                len(subject["candidates"])
                for subject in result["candidates"]["locations"]
            ),
            "locationDecisions": len(result["decisions"]["locationDecisions"]),
            "publishableLocationLinks": len(result["publishable"]["locations"]),
            "workSubjects": len(result["candidates"]["works"]),
            "workCandidates": sum(
                len(subject["candidates"]) for subject in result["candidates"]["works"]
            ),
            "workDecisions": len(result["decisions"]["workDecisions"]),
            "publishableWorkLinks": len(result["publishable"]["works"]),
            "agentSubjects": len(result["candidates"]["agents"]),
            "agentDecisions": len(result["decisions"]["agentDecisions"]),
            "publishableAgentLinks": len(result["publishable"]["agents"]),
            "reviewCases": result["queue"]["caseCount"],
            "contestedAuthorityClaims": len(result["contestedClaims"]),
            "contestedEditionClaims": len(edition_dataset["contestedClaims"]),
        },
        "artifacts": {name: _sha256(output_dir / name) for name in artifacts},
        "frontendArtifact": {
            "path": "docs/data/reconciliation.json",
            "sha256": _sha256(Path(OUTPUT_RECONCILIATION_FRONTEND)),
        },
        "operatorPoints": [
            {
                "subject": "klawiter:edition/4916-2016-b",
                "question": "Select or create the canonical adaptation work before accepting its work binding.",
                "evidence": "data/output/editions/review-queue.json",
            }
        ],
    }
    write_json(str(output_dir / "manifest.json"), manifest, indent=2, sort_keys=True)
    log.info(
        "Gate 2 output: %d location links, %d work links, %d review cases",
        manifest["counts"]["publishableLocationLinks"],
        manifest["counts"]["publishableWorkLinks"],
        manifest["counts"]["reviewCases"],
    )


if __name__ == "__main__":
    main()
