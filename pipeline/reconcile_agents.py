#!/usr/bin/env python3
"""Generate frozen Wikidata candidates for translators and publishers.

REFREEZING TOOL, NOT A PIPELINE STAGE. It calls the live Wikidata
Reconciliation API and OVERWRITES data/provenance/agent-reconciliation.json,
a frozen, hash-bound Gate-2 input. Running it replaces that frozen
evidence; Gate 2 must be rebuilt and revalidated afterwards. It therefore
refuses to run without the explicit --i-am-refreezing switch.

Candidates are proposals only: nothing publishes without a confirmed
decision in data/reconciliation/agent-decisions.json (fail-closed, the
same contract locations and works follow).

The initial freeze covers names with at least --min-occurrences entries
(default 5), the head of the distribution where curation pays off;
lowering the threshold in a later refreeze widens the review pool.

Usage: python pipeline/reconcile_agents.py --i-am-refreezing
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import (  # noqa: E402
    AGENT_RECONCILIATION,
    OUTPUT_FRONTEND_JSON,
    write_json,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

USER_AGENT = (
    "KlawitterBibliography/1.0 (https://github.com/chpollin/klawiter-rescue; research)"
)
RECON_BASE = "https://wikidata.reconci.link"
BATCH_SIZE = 20
DELAY_S = 2.0
# Wikidata types constraining the reconciliation per agent kind
KIND_TYPES = {"person": "Q5", "publisher": "Q43229"}


def collect_names(min_occurrences: int) -> list[dict]:
    with open(OUTPUT_FRONTEND_JSON, encoding="utf-8") as f:
        entries = json.load(f)["entries"]
    counts: Counter = Counter()
    for entry in entries:
        if entry.get("translator"):
            counts[("person", entry["translator"])] += 1
        if entry.get("publisher"):
            counts[("publisher", entry["publisher"])] += 1
    return [
        {"kind": kind, "name": name, "occurrences": count}
        for (kind, name), count in sorted(counts.items())
        if count >= min_occurrences
    ]


def reconcile_batch(items: list[dict], lang: str) -> dict:
    queries = {
        str(i): {
            "query": item["name"],
            "type": KIND_TYPES[item["kind"]],
            "limit": 3,
        }
        for i, item in enumerate(items)
    }
    response = requests.post(
        f"{RECON_BASE}/{lang}/api",
        data={"queries": json.dumps(queries)},
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    results = {}
    for i, item in enumerate(items):
        hits = payload.get(str(i), {}).get("result", [])
        results[(item["kind"], item["name"])] = [
            {
                "qid": hit["id"],
                "label": hit["name"],
                "score": round(hit.get("score", 0)),
                "matchExact": bool(hit.get("match", False)),
            }
            for hit in hits
        ]
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--i-am-refreezing",
        action="store_true",
        help=(
            "Confirm that you intend to overwrite the frozen, hash-bound "
            "Gate-2 input data/provenance/agent-reconciliation.json with "
            "live Wikidata results."
        ),
    )
    parser.add_argument("--min-occurrences", type=int, default=5)
    args = parser.parse_args()
    if not args.i_am_refreezing:
        print(
            "REFUSED: this tool overwrites data/provenance/"
            "agent-reconciliation.json, a frozen Gate-2 input whose SHA-256 "
            "is recorded in the Gate-2 manifest.\n"
            "Run again with --i-am-refreezing only if you intend to replace "
            "that frozen evidence, then rebuild and revalidate Gate 2.",
            file=sys.stderr,
        )
        sys.exit(2)

    subjects = collect_names(args.min_occurrences)
    print(f"{len(subjects)} agent names with >= {args.min_occurrences} occurrences.")

    batch_failures = 0
    results: dict = {}
    for lang in ("en", "de"):
        print(f"\nReconciling against {lang} endpoint...")
        batches = [
            subjects[i : i + BATCH_SIZE] for i in range(0, len(subjects), BATCH_SIZE)
        ]
        for index, batch in enumerate(batches):
            print(f"  Batch {index + 1}/{len(batches)}...", end=" ", flush=True)
            try:
                batch_results = reconcile_batch(batch, lang)
                matched = sum(1 for hits in batch_results.values() if hits)
                print(f"{matched} with candidates")
                for key, hits in batch_results.items():
                    existing = {c["qid"] for c in results.get(key, [])}
                    results.setdefault(key, []).extend(
                        hit for hit in hits if hit["qid"] not in existing
                    )
            except Exception as error:  # noqa: BLE001 - report and count
                print(f"ERROR: {error}")
                batch_failures += 1
                if "429" in str(error):
                    print("  Rate limited, waiting 10s...")
                    time.sleep(10)
            time.sleep(DELAY_S)

    for subject in subjects:
        hits = results.get((subject["kind"], subject["name"]), [])
        subject["candidates"] = sorted(
            hits, key=lambda hit: (-hit["score"], hit["qid"])
        )

    document = {
        "schemaVersion": "1.0",
        "contract": (
            "Frozen Wikidata reconciliation candidates for translators and "
            "publishers. Proposals only: nothing publishes without a "
            "confirmed decision in data/reconciliation/agent-decisions.json."
        ),
        "parameters": {
            "minOccurrences": args.min_occurrences,
            "batchSize": BATCH_SIZE,
            "candidateLimitPerLanguage": 3,
            "languages": ["en", "de"],
            "types": KIND_TYPES,
        },
        "agents": subjects,
    }
    write_json(AGENT_RECONCILIATION, document, indent=2, sort_keys=True)

    with_candidates = sum(1 for s in subjects if s["candidates"])
    print(f"\nFrozen: {len(subjects)} subjects, {with_candidates} with candidates.")
    print(f"Written: {AGENT_RECONCILIATION}")
    if batch_failures:
        print(
            f"WARNING: {batch_failures} batch(es) failed; the frozen data is "
            "incomplete. Inspect before rebuilding Gate 2.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
