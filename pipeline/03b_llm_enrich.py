#!/usr/bin/env python3
"""
Step 3b: LLM-based metadata enrichment using Gemini 3.1 Flash Lite.
Fills gaps left by regex extraction (publisher, location, translator, page_count).

Only processes entries where at least one field is missing.
Never overwrites existing regex results (100% precision guarantee).

Input:  data/intermediate/03_parsed.csv
Output: data/intermediate/03b_llm_enriched.csv
Cache:  data/intermediate/03b_llm_cache.json
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import setup_logging, load_csv, write_csv, STEP_03_OUTPUT, STEP_03B_OUTPUT, INTERMEDIATE_DIR
from lib.llm_extract import (
    create_client, prepare_batch_entry, determine_needed_fields,
    call_gemini, validate_extraction, load_cache, save_cache,
    BATCH_SIZE, REQUEST_DELAY,
)

log = setup_logging(__name__)

# Use same output fields as step 03
OUTPUT_FIELDS = [
    'page_id', 'page_namespace', 'page_title', 'text_id', 'blob_id',
    'is_redirect', 'redirect_target',
    'title', 'original_title', 'sortkey',
    'year', 'all_years',
    'publisher', 'location', 'all_locations',
    'language', 'language_iso',
    'page_count', 'translator',
    'categories', 'main_category',
    'see_also', 'reprints', 'translations', 'content_items',
    'clean_content', 'raw_content',
]

CACHE_PATH = os.path.join(INTERMEDIATE_DIR, '03b_llm_cache.json')


def load_env():
    """Load .env file from project root if GEMINI_API_KEY not already set."""
    if os.environ.get('GEMINI_API_KEY'):
        return
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


def filter_entries(rows):
    """Select entries that need LLM enrichment."""
    candidates = []
    for row in rows:
        # Skip non-main-namespace
        if row.get('page_namespace', '0') != '0':
            continue
        # Skip redirects
        if row.get('is_redirect') in ('True', 'true', '1'):
            continue
        # Skip entries without substantial content
        raw = row.get('raw_content', '') or row.get('content', '')
        if len(raw) < 80:
            continue
        # Check if any field is missing
        needed = determine_needed_fields(row)
        if needed:
            candidates.append((row, needed))
    return candidates


def merge_result(row, validated):
    """Merge LLM result into row, filling gaps only."""
    for field in ['publisher', 'location', 'translator']:
        if not row.get(field) and validated.get(field):
            row[field] = validated[field]
    if not row.get('page_count') and validated.get('page_count'):
        row['page_count'] = str(validated['page_count'])
    return row


def main():
    load_env()

    log.info(f"Loading parsed entries: {STEP_03_OUTPUT}")
    rows = load_csv(STEP_03_OUTPUT)
    log.info(f"  Loaded {len(rows)} entries")

    # Filter entries needing LLM help
    candidates = filter_entries(rows)
    log.info(f"  Entries needing LLM enrichment: {len(candidates)}")

    # Load cache for resume support
    cache = load_cache(CACHE_PATH)
    cached_count = len(cache)
    if cached_count:
        log.info(f"  Cache loaded: {cached_count} entries already processed")

    # Build index for fast lookup
    row_index = {row['page_id']: row for row in rows}

    # Prepare batches (skip cached entries)
    to_process = []
    for row, needed in candidates:
        pid = row['page_id']
        if pid not in cache:
            to_process.append((row, needed))

    log.info(f"  Entries to send to LLM: {len(to_process)}")

    if not to_process:
        log.info("  Nothing new to process — applying cached results")
    else:
        # Create Gemini client
        client = create_client()

        # Process in batches
        total_batches = (len(to_process) + BATCH_SIZE - 1) // BATCH_SIZE
        processed = 0
        api_errors = 0

        for batch_idx in range(0, len(to_process), BATCH_SIZE):
            batch = to_process[batch_idx:batch_idx + BATCH_SIZE]
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
                    pid = str(validated['page_id'])
                    cache[pid] = validated
                    processed += len(batch)
            else:
                api_errors += 1

            # Progress logging
            if batch_num % 25 == 0 or batch_num == total_batches:
                log.info(f"  Batch {batch_num}/{total_batches} "
                         f"(processed={processed}, errors={api_errors})")

            # Save cache periodically
            if batch_num % 50 == 0:
                save_cache(CACHE_PATH, cache)

            # Rate limiting
            time.sleep(REQUEST_DELAY)

        # Final cache save
        save_cache(CACHE_PATH, cache)
        log.info(f"  LLM processing complete: {processed} entries, {api_errors} batch errors")

    # Merge all cached results into rows
    merged = 0
    fields_filled = {'publisher': 0, 'location': 0, 'translator': 0, 'page_count': 0}

    for pid, validated in cache.items():
        if pid in row_index:
            row = row_index[pid]
            old = {f: row.get(f, '') for f in fields_filled}
            merge_result(row, validated)
            for f in fields_filled:
                if not old[f] and row.get(f, ''):
                    fields_filled[f] += 1
                    merged += 1

    log.info(f"  Merged {merged} new field values from LLM:")
    for field, count in fields_filled.items():
        log.info(f"    {field}: +{count}")

    # Write enriched output
    write_csv(STEP_03B_OUTPUT, rows, OUTPUT_FIELDS)
    log.info(f"Output written to {STEP_03B_OUTPUT}")

    # Summary stats
    total = len([r for r in rows if r.get('page_namespace', '0') == '0'
                 and r.get('is_redirect') not in ('True', 'true', '1')])
    for field in ['publisher', 'location', 'translator', 'page_count']:
        count = sum(1 for r in rows if r.get(field)
                    and r.get('page_namespace', '0') == '0'
                    and r.get('is_redirect') not in ('True', 'true', '1'))
        log.info(f"  {field}: {count}/{total} ({100*count/total:.1f}%)")


if __name__ == '__main__':
    main()
