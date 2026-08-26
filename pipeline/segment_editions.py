#!/usr/bin/env python3
"""Build the complete Gate-1 Work and Edition proposal layer.

Input is the encoding-corrected source CSV from stage 02. Output contains the
deterministic Schema.org graph, Web Annotation selectors, PROV run evidence, a
manifest with hashes, and a prioritized queue for every flagged proposal.

Usage:
    python pipeline/segment_editions.py
    python pipeline/segment_editions.py --input path/to/02_encoding_fixed.csv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (  # noqa: E402
    EDITION_MODELING_DECISIONS,
    EDITION_SAMPLE_RECONCILIATION,
    OUTPUT_EDITIONS_DIR,
    STEP_02_OUTPUT,
    SZD_WORK_INDEX,
    WORK_DECISIONS,
    load_csv,
    setup_logging,
    write_json,
)
from lib.editions import (  # noqa: E402
    ALGORITHM_VERSION,
    apply_confirmed_work_links,
    apply_review_reconciliation,
    build_corpus,
)
from lib.reconciliation import parse_szd_work_index  # noqa: E402

log = setup_logging(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=STEP_02_OUTPUT)
    parser.add_argument("--output-dir", default=OUTPUT_EDITIONS_DIR)
    parser.add_argument(
        "--sample-reconciliation", default=EDITION_SAMPLE_RECONCILIATION
    )
    parser.add_argument("--modeling-decisions", default=EDITION_MODELING_DECISIONS)
    return parser.parse_args()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _code_hash() -> str:
    # LF-normalize so the recorded provenance hash is independent of the
    # git eol settings that produced the working copy.
    paths = (Path(__file__), Path(__file__).parent / "lib" / "editions.py")
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _review_priority(flags: list[str]) -> str:
    if {
        "unparsed-header",
        "missing-year",
        "contested-work-identity",
    }.intersection(flags):
        return "P0"
    if {
        "compound-header",
        "approximate-year",
        "page-count-notation-review",
        "missing-location",
    }.intersection(flags):
        return "P1"
    return "P2"


def _review_queue(dataset: dict) -> dict:
    annotations = {
        annotation["oa:hasBody"]["@id"]: annotation["oa:hasTarget"]
        for annotation in dataset["annotations"]
    }
    cases = []
    for edition in dataset["editions"]:
        flags = edition["klawiter:reviewFlags"]
        status = edition["klawiter:reviewStatus"]
        if status == "confirmed" or (not flags and status != "contested"):
            continue
        cases.append(
            {
                "editionId": edition["@id"],
                "sourcePageId": edition["klawiter:sourcePageId"],
                "priority": _review_priority(flags),
                "reviewStatus": edition["klawiter:reviewStatus"],
                "flags": flags,
                "headerLine": edition["klawiter:headerLine"],
                "proposedValues": {
                    "year": edition.get("schema:datePublished"),
                    "publisher": edition.get("schema:publisher"),
                    "location": edition.get("schema:locationCreated"),
                    "pageCount": edition.get("schema:numberOfPages"),
                    "pageCountCandidate": edition.get("klawiter:pageCountCandidate"),
                    "series": edition.get("klawiter:headerSeries"),
                    "description": edition.get("schema:description"),
                    "contestedClaim": edition.get("klawiter:contestedClaim"),
                },
                "evidence": annotations[edition["@id"]],
                "sourceSliceSha256": edition["klawiter:sourceSliceSha256"],
            }
        )
    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    cases.sort(
        key=lambda case: (
            priority_order[case["priority"]],
            case["sourcePageId"],
            case["editionId"],
        )
    )
    return {
        "contract": "Every unconfirmed flagged case and every contested claim remains explicit until an authorized source-bound decision is recorded.",
        "caseCount": len(cases),
        "cases": cases,
    }


def _provenance(
    dataset: dict,
    generated_at: str,
    code_hash: str,
    reconciliation_hash: str,
    modeling_hash: str,
) -> dict:
    corpus_hash = dataset["klawiter:sourceCorpusSha256"]
    run_id = f"klawiter:run/segment-{corpus_hash[:16]}-{code_hash[:16]}"
    graph = [
        {
            "@id": run_id,
            "@type": "prov:Activity",
            "prov:startedAtTime": generated_at,
            "prov:used": [
                {"@id": "klawiter:sourceCorpus/mediawiki"},
                {"@id": "klawiter:evidence/sample-reconciliation"},
                {"@id": "klawiter:decisions/edition-modeling"},
            ],
            "prov:qualifiedAssociation": {
                "@type": "prov:Association",
                "prov:agent": {"@id": "klawiter:agent/deterministic-segmenter"},
                "prov:hadPlan": {"@id": "klawiter:plan/segment-editions-v1"},
            },
        },
        {
            "@id": "klawiter:sourceCorpus/mediawiki",
            "@type": "prov:Entity",
            "klawiter:sha256": corpus_hash,
        },
        {
            "@id": "klawiter:agent/deterministic-segmenter",
            "@type": ["prov:SoftwareAgent", "earl:Software"],
            "schema:name": "Klawiter deterministic edition segmenter",
        },
        {
            "@id": "klawiter:evidence/sample-reconciliation",
            "@type": "prov:Entity",
            "klawiter:sha256": reconciliation_hash,
        },
        {
            "@id": "klawiter:decisions/edition-modeling",
            "@type": "prov:Entity",
            "klawiter:sha256": modeling_hash,
            "prov:wasDerivedFrom": {"@id": "klawiter:evidence/sample-reconciliation"},
        },
        {
            "@id": "klawiter:plan/segment-editions-v1",
            "@type": "prov:Plan",
            "klawiter:algorithmVersion": ALGORITHM_VERSION,
            "klawiter:sourceCodeSha256": code_hash,
        },
    ]
    graph.extend(
        {
            "@id": edition["@id"],
            "prov:wasGeneratedBy": {"@id": run_id},
        }
        for edition in dataset["editions"]
    )
    graph.extend(
        {
            "@id": claim["@id"],
            "prov:wasGeneratedBy": {"@id": run_id},
        }
        for claim in dataset["contestedClaims"]
    )
    return {
        "@context": {
            "schema": "https://schema.org/",
            "klawiter": "https://chpollin.github.io/klawiter-rescue/vocab/",
            "prov": "http://www.w3.org/ns/prov#",
            "earl": "http://www.w3.org/ns/earl#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "prov:startedAtTime": {"@type": "xsd:dateTime"},
        },
        "@graph": graph,
    }


def main() -> None:
    args = _parse_args()
    input_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve()
    reconciliation_path = Path(args.sample_reconciliation).resolve()
    modeling_path = Path(args.modeling_decisions).resolve()
    for path, description in (
        (input_path, "Stage-02 source"),
        (reconciliation_path, "sample reconciliation"),
        (modeling_path, "edition modeling decisions"),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{description} is missing: {path}")
    rows = load_csv(str(input_path))
    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
    modeling_decisions = json.loads(modeling_path.read_text(encoding="utf-8"))
    reconciliation_hash = _sha256(reconciliation_path)
    modeling_hash = _sha256(modeling_path)
    if modeling_decisions["sample_reconciliation_sha256"] != reconciliation_hash:
        raise ValueError("Edition modeling decisions reference another reconciliation")
    dataset = apply_review_reconciliation(
        build_corpus(rows), reconciliation, modeling_decisions
    )
    work_decisions = json.loads(Path(WORK_DECISIONS).read_text(encoding="utf-8"))
    szd_authorities = parse_szd_work_index(Path(SZD_WORK_INDEX))
    linked = apply_confirmed_work_links(dataset, work_decisions, szd_authorities)
    log.info(f"Confirmed work identities linked as sameAs: {linked}")
    generated_at = datetime.now(timezone.utc).isoformat()
    code_hash = _code_hash()

    dataset_path = output_dir / "work-editions.jsonld"
    provenance_path = output_dir / "provenance.jsonld"
    queue_path = output_dir / "review-queue.json"
    manifest_path = output_dir / "manifest.json"

    write_json(str(dataset_path), dataset, indent=2, sort_keys=True)
    write_json(
        str(provenance_path),
        _provenance(
            dataset,
            generated_at,
            code_hash,
            reconciliation_hash,
            modeling_hash,
        ),
        indent=2,
        sort_keys=True,
    )
    queue = _review_queue(dataset)
    write_json(str(queue_path), queue, indent=2, sort_keys=True)

    manifest = {
        "generatedAt": generated_at,
        "algorithmVersion": ALGORITHM_VERSION,
        "source": {
            "path": str(input_path.relative_to(input_path.parents[2])).replace(
                "\\", "/"
            ),
            "sha256": _sha256(input_path),
            "selectedCorpusSha256": dataset["klawiter:sourceCorpusSha256"],
        },
        "reviewEvidence": {
            "sampleReconciliation": {
                "path": "data/output/edition-samples/reviews/reconciliation.json",
                "sha256": reconciliation_hash,
            },
            "modelingDecisions": {
                "path": "data/reconciliation/edition-modeling-decisions.json",
                "sha256": modeling_hash,
            },
        },
        "authorityEvidence": {
            "workDecisions": {
                "path": "data/reconciliation/work-decisions.json",
                "sha256": _sha256(Path(WORK_DECISIONS)),
            },
            "szdWorkIndex": {
                "path": "data/provenance/szd-work-index.xml",
                "sha256": _sha256(Path(SZD_WORK_INDEX)),
            },
        },
        "codeSha256": code_hash,
        "selectionRule": dataset["klawiter:selectionRule"],
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
            "reviewCases": queue["caseCount"],
        },
        "artifacts": {
            "work-editions.jsonld": _sha256(dataset_path),
            "provenance.jsonld": _sha256(provenance_path),
            "review-queue.json": _sha256(queue_path),
        },
    }
    write_json(str(manifest_path), manifest, indent=2, sort_keys=True)
    log.info(
        "Gate 1 output: %d works, %d editions, %d review cases",
        manifest["counts"]["works"],
        manifest["counts"]["editions"],
        manifest["counts"]["reviewCases"],
    )
    log.info("Manifest written to %s", manifest_path)


if __name__ == "__main__":
    main()
