#!/usr/bin/env python3
"""
Inject per-field provenance metadata into the frontend JSON.

Diffs the regex output (03_parsed.csv) against the final values to decide
which fields were LLM-filled vs regex-extracted. Cache presence alone is not
enough: the 03b merge fills gaps only, so the cache can hold a value for a
field the regex had already filled — that value was never used.
Adds a `_provenance` object to each entry: { field: "regex"|"llm"|"missing" }

Input:  docs/data/klawiter.json + data/intermediate/03_parsed.csv
        + data/intermediate/03b_llm_cache.json
Output: docs/data/klawiter.json (updated in-place)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (
    setup_logging, load_csv, write_json,
    INTERMEDIATE_DIR, OUTPUT_FRONTEND_JSON, STEP_03_OUTPUT,
)

log = setup_logging(__name__)

CACHE_PATH = os.path.join(INTERMEDIATE_DIR, '03b_llm_cache.json')

# Fields we track provenance for (frontend key → cache/CSV key)
TRACKED_FIELDS = {
    'publisher': 'publisher',
    'location': 'location',
    'translator': 'translator',
    'pageCount': 'page_count',
}


def field_provenance(has_value, regex_had, llm_has):
    """Decide the provenance label for one field.

    regex_had wins over llm_has because the 03b merge never overwrites a
    regex value — a cache entry for an already-filled field was never merged.
    A filled field with neither source is labeled regex (the conservative
    default; normalization only rewrites values, it never adds them).
    """
    if not has_value:
        return 'missing'
    if regex_had:
        return 'regex'
    if llm_has:
        return 'llm'
    return 'regex'


def main():
    # Load LLM cache
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        log.info(f"LLM cache loaded: {len(cache)} entries")
    else:
        cache = {}
        log.warning(f"No LLM cache found at {CACHE_PATH}")

    # Build set of LLM-filled fields per page_id
    llm_fields = {}  # page_id (str) -> set of field names
    for pid, result in cache.items():
        filled = set()
        for field in ['publisher', 'location', 'translator', 'page_count']:
            if field in result and result[field]:
                filled.add(field)
        if filled:
            llm_fields[pid] = filled

    log.info(f"Entries with LLM-filled fields: {len(llm_fields)}")

    # Load regex output for the merge diff. Without it the llm label would
    # rest on cache presence alone and overcount (the pre-fix behavior).
    regex_rows = {}
    if os.path.exists(STEP_03_OUTPUT):
        for row in load_csv(STEP_03_OUTPUT):
            regex_rows[row['page_id']] = row
        log.info(f"Regex output loaded: {len(regex_rows)} entries")
    else:
        log.warning(f"Regex output not found at {STEP_03_OUTPUT} — "
                    f"falling back to cache presence, 'llm' labels may overcount")

    # Load frontend JSON
    with open(OUTPUT_FRONTEND_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries = data.get('entries', [])
    log.info(f"Frontend entries: {len(entries)}")

    # Inject provenance
    stats = {'regex': 0, 'llm': 0, 'missing': 0}

    for entry in entries:
        pid = str(entry.get('sourcePageId', ''))
        entry_llm = llm_fields.get(pid, set())
        regex_row = regex_rows.get(pid)
        prov = {}

        for frontend_key, cache_key in TRACKED_FIELDS.items():
            has_value = bool(entry.get(frontend_key))
            regex_had = bool(regex_row and regex_row.get(cache_key))
            llm_has = cache_key in entry_llm

            label = field_provenance(has_value, regex_had, llm_has)
            prov[frontend_key] = label
            stats[label] += 1

        entry['_provenance'] = prov

    log.info(f"Provenance stats: {stats}")
    log.info(f"  regex: {stats['regex']} ({100*stats['regex']/sum(stats.values()):.1f}%)")
    log.info(f"  llm:   {stats['llm']} ({100*stats['llm']/sum(stats.values()):.1f}%)")
    log.info(f"  missing: {stats['missing']} ({100*stats['missing']/sum(stats.values()):.1f}%)")

    # Write back
    write_json(OUTPUT_FRONTEND_JSON, data, separators=(',', ':'))

    size_mb = os.path.getsize(OUTPUT_FRONTEND_JSON) / 1024 / 1024
    log.info(f"Updated frontend JSON: {OUTPUT_FRONTEND_JSON} ({size_mb:.1f} MB)")


if __name__ == '__main__':
    main()
