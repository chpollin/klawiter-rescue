#!/usr/bin/env python3
"""
Step 3b: LLM-based metadata enrichment using Gemini 3.1 Flash Lite.
Fills gaps left by regex extraction (publisher, location, translator, page_count).

Only processes entries where at least one field is missing.
Never overwrites existing regex results (100% precision guarantee).

Input:  data/intermediate/03_parsed.csv
Output: data/intermediate/03b_llm_enriched.csv
Frozen input: data/provenance/llm-enrichment-cache.json
Live resume cache: data/intermediate/03b_llm_cache.json

Usage:
    python pipeline/03b_llm_enrich.py --mode frozen
    python pipeline/03b_llm_enrich.py --mode live

Frozen mode is deterministic and performs no network call. Live mode is an
explicit enrichment operation whose new responses stay in the working cache
until they have been reviewed and frozen as a production input.
"""

import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (
    FROZEN_LLM_CACHE,
    MIN_CONTENT_LENGTH,
    OUTPUT_LLM_REPORT,
    PARSED_FIELDS,
    STEP_03_OUTPUT,
    STEP_03B_OUTPUT,
    WORKING_LLM_CACHE,
    csv_bool,
    load_csv,
    load_env,
    setup_logging,
    write_csv,
    write_json,
)
from lib.llm_extract import (
    BATCH_SIZE,
    MODEL_ID,
    REQUEST_DELAY,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    call_gemini,
    create_client,
    determine_needed_fields,
    load_cache,
    prepare_batch_entry,
    save_cache,
    validate_extraction,
)
from lib.patterns import PAGE_RANGE_RE

log = setup_logging(__name__)

PROMPT_HASH = hashlib.sha256(
    (SYSTEM_PROMPT + "\n\n" + USER_PROMPT_TEMPLATE).encode("utf-8")
).hexdigest()


def filter_entries(
    rows: list[dict[str, str]],
) -> list[tuple[dict[str, str], list[str]]]:
    """Select entries that need LLM enrichment."""
    candidates = []
    for row in rows:
        # Skip non-main-namespace
        if row.get("page_namespace", "0") != "0":
            continue
        # Skip redirects
        if csv_bool(row.get("is_redirect")):
            continue
        # Skip entries without substantial content
        raw = row.get("raw_content", "") or row.get("content", "")
        if len(raw) < MIN_CONTENT_LENGTH:
            continue
        # Check if any field is missing
        needed = determine_needed_fields(row)
        if needed:
            candidates.append((row, needed))
    return candidates


def _correct_page_count(page_count: int | None, raw_content: str) -> int | None:
    """Fix off-by-one errors in LLM page range calculations.
    When text has 'pp. (X)-Y', correct count is Y - X + 1.
    """
    if not page_count or not raw_content:
        return page_count
    for m in PAGE_RANGE_RE.finditer(raw_content):
        start, end = int(m.group(1)), int(m.group(2))
        correct = end - start + 1
        # LLM often computes end - start (off by one)
        if page_count == end - start:
            return correct
    return page_count


def merge_result(row: dict[str, str], validated: dict[str, object]) -> dict[str, str]:
    """Merge LLM result into row, filling gaps only."""
    for field in ["publisher", "location", "translator"]:
        if not row.get(field) and validated.get(field):
            row[field] = validated[field]
    if not row.get("page_count") and validated.get("page_count"):
        raw = row.get("raw_content", "") or row.get("content", "")
        corrected = _correct_page_count(int(validated["page_count"]), raw)
        row["page_count"] = str(corrected)
    return row


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply frozen LLM results or explicitly extend them live."
    )
    parser.add_argument(
        "--mode",
        choices=("frozen", "live"),
        default="frozen",
        help="Frozen is network-free; live may call Gemini for cache misses.",
    )
    return parser.parse_args()


def _load_frozen_cache(path: str) -> tuple[dict[str, dict[str, object]], dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Frozen LLM input not found: {path}. "
            "Restore the tracked artifact before running production."
        )
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)
    results = document.get("results")
    if not isinstance(results, dict):
        raise ValueError(f"Frozen LLM input has no results object: {path}")
    recorded_hash = document.get("provenance", {}).get("promptSha256")
    if recorded_hash != PROMPT_HASH:
        raise ValueError(
            "Frozen LLM prompt hash does not match the executable prompt. "
            "Review and re-freeze the artifact before use."
        )
    canonical_results = json.dumps(
        results,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    results_hash = hashlib.sha256(canonical_results).hexdigest()
    recorded_results_hash = document.get("provenance", {}).get("resultsSha256")
    if recorded_results_hash != results_hash:
        raise ValueError(
            "Frozen LLM result hash does not match its provenance record. "
            "Restore the reviewed production artifact before use."
        )
    return results, document.get("provenance", {})


def main() -> None:
    args = _parse_args()
    if args.mode == "live":
        load_env()

    log.info(f"Loading parsed entries: {STEP_03_OUTPUT}")
    rows = load_csv(STEP_03_OUTPUT)
    log.info(f"  Loaded {len(rows)} entries")

    # Filter entries needing LLM help
    candidates = filter_entries(rows)
    log.info(f"  Entries needing LLM enrichment: {len(candidates)}")

    frozen_cache, frozen_provenance = _load_frozen_cache(FROZEN_LLM_CACHE)
    working_cache = load_cache(WORKING_LLM_CACHE) if args.mode == "live" else {}
    cache = {**frozen_cache, **working_cache}
    log.info(
        "  Frozen results: %d; live working results: %d",
        len(frozen_cache),
        len(working_cache),
    )

    # Build index for fast lookup
    row_index = {row["page_id"]: row for row in rows}

    # Prepare batches (skip cached entries)
    to_process = []
    for row, needed in candidates:
        pid = row["page_id"]
        if pid not in cache:
            to_process.append((row, needed))

    log.info("  Cache misses: %d", len(to_process))

    if not to_process:
        log.info("  Nothing new to process — applying cached results")
    elif args.mode == "frozen":
        log.warning(
            "  Frozen mode leaves %d entries without LLM enrichment; no network call made",
            len(to_process),
        )
    else:
        # Create Gemini client
        client = create_client()

        # Process in batches
        total_batches = (len(to_process) + BATCH_SIZE - 1) // BATCH_SIZE
        processed = 0
        api_errors = 0

        for batch_idx in range(0, len(to_process), BATCH_SIZE):
            batch = to_process[batch_idx : batch_idx + BATCH_SIZE]
            batch_num = batch_idx // BATCH_SIZE + 1

            # Prepare batch for API
            batch_entries = []
            for row, needed in batch:
                batch_entries.append(prepare_batch_entry(row, needed))

            # Call Gemini
            extractions = call_gemini(client, batch_entries)

            if extractions:
                for ext in extractions:
                    validated = validate_extraction(ext)
                    pid = str(validated["page_id"])
                    cache[pid] = validated
                processed += len(extractions)
            else:
                api_errors += 1

            # Progress logging
            if batch_num % 25 == 0 or batch_num == total_batches:
                log.info(
                    f"  Batch {batch_num}/{total_batches} "
                    f"(processed={processed}, errors={api_errors})"
                )

            # Save cache periodically
            if batch_num % 50 == 0:
                save_cache(WORKING_LLM_CACHE, cache)

            # Rate limiting
            time.sleep(REQUEST_DELAY)

        # Final cache save
        save_cache(WORKING_LLM_CACHE, cache)
        log.info(
            f"  LLM processing complete: {processed} entries, {api_errors} batch errors"
        )

    # Re-validate cached results with current validation rules (catches mojibake)
    from lib.llm_extract import _has_llm_mojibake

    revalidated_cache = {}
    rejected = 0
    for pid, validated in cache.items():
        clean = {"page_id": validated["page_id"]}
        for field in ["publisher", "location", "translator"]:
            val = validated.get(field)
            if val and not _has_llm_mojibake(val):
                clean[field] = val
            elif val:
                rejected += 1
        if "page_count" in validated:
            clean["page_count"] = validated["page_count"]
        revalidated_cache[pid] = clean
    if rejected:
        log.info(f"  Re-validation: rejected {rejected} mojibake values from cache")

    # Merge all cached results into rows
    merged = 0
    fields_filled = {"publisher": 0, "location": 0, "translator": 0, "page_count": 0}

    for pid, validated in revalidated_cache.items():
        if pid in row_index:
            row = row_index[pid]
            old = {f: row.get(f, "") for f in fields_filled}
            merge_result(row, validated)
            for f in fields_filled:
                if not old[f] and row.get(f, ""):
                    fields_filled[f] += 1
                    merged += 1

    log.info(f"  Merged {merged} new field values from LLM:")
    for field, count in fields_filled.items():
        log.info(f"    {field}: +{count}")

    # Write enriched output
    write_csv(STEP_03B_OUTPUT, rows, PARSED_FIELDS)
    log.info(f"Output written to {STEP_03B_OUTPUT}")

    # Summary stats
    total = len(
        [
            r
            for r in rows
            if r.get("page_namespace", "0") == "0"
            and not csv_bool(r.get("is_redirect"))
        ]
    )
    for field in ["publisher", "location", "translator", "page_count"]:
        count = sum(
            1
            for r in rows
            if r.get(field)
            and r.get("page_namespace", "0") == "0"
            and not csv_bool(r.get("is_redirect"))
        )
        log.info(f"  {field}: {count}/{total} ({100 * count / total:.1f}%)")

    write_json(
        OUTPUT_LLM_REPORT,
        {
            "mode": args.mode,
            "model": MODEL_ID,
            "promptSha256": PROMPT_HASH,
            "frozenProvenance": frozen_provenance,
            "frozenResultCount": len(frozen_cache),
            "workingResultCount": len(working_cache),
            "cacheMissCount": len(to_process),
            "networkCallsAllowed": args.mode == "live",
            "networkCallsMade": args.mode == "live" and bool(to_process),
            "rejectedCachedValues": rejected,
            "fieldsFilled": fields_filled,
        },
        indent=2,
    )
    log.info("Provenance report written to %s", OUTPUT_LLM_REPORT)


if __name__ == "__main__":
    main()
