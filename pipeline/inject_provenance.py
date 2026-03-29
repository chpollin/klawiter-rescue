#!/usr/bin/env python3
"""
Inject per-field provenance metadata into the frontend JSON.

Reads the LLM cache to determine which fields were LLM-filled vs regex-extracted.
Adds a `_provenance` object to each entry: { field: "regex"|"llm"|"missing" }

Input:  docs/data/klawiter.json + data/intermediate/03b_llm_cache.json
Output: docs/data/klawiter.json (updated in-place)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import setup_logging, INTERMEDIATE_DIR, OUTPUT_FRONTEND_JSON

log = setup_logging(__name__)

CACHE_PATH = os.path.join(INTERMEDIATE_DIR, '03b_llm_cache.json')

# Fields we track provenance for (frontend key → LLM cache key)
TRACKED_FIELDS = {
    'publisher': 'publisher',
    'location': 'location',
    'translator': 'translator',
    'pageCount': 'page_count',
}


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
        prov = {}

        for frontend_key, cache_key in TRACKED_FIELDS.items():
            has_value = bool(entry.get(frontend_key))
            was_llm = cache_key in entry_llm

            if has_value and was_llm:
                prov[frontend_key] = 'llm'
                stats['llm'] += 1
            elif has_value:
                prov[frontend_key] = 'regex'
                stats['regex'] += 1
            else:
                prov[frontend_key] = 'missing'
                stats['missing'] += 1

        entry['_provenance'] = prov

    log.info(f"Provenance stats: {stats}")
    log.info(f"  regex: {stats['regex']} ({100*stats['regex']/sum(stats.values()):.1f}%)")
    log.info(f"  llm:   {stats['llm']} ({100*stats['llm']/sum(stats.values()):.1f}%)")
    log.info(f"  missing: {stats['missing']} ({100*stats['missing']/sum(stats.values()):.1f}%)")

    # Write back
    with open(OUTPUT_FRONTEND_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    size_mb = os.path.getsize(OUTPUT_FRONTEND_JSON) / 1024 / 1024
    log.info(f"Updated frontend JSON: {OUTPUT_FRONTEND_JSON} ({size_mb:.1f} MB)")


if __name__ == '__main__':
    main()
