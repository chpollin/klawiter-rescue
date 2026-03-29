#!/usr/bin/env python3
"""
Step 2: Fix Mojibake encoding issues in extracted data.
55% of entries have UTF-8 bytes misinterpreted as Latin-1.

Input:  data/intermediate/01_extracted.csv
Output: data/intermediate/02_encoding_fixed.csv
"""

import csv
import os
import sys
import logging

csv.field_size_limit(10 * 1024 * 1024)  # 10MB field limit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.encoding import fix_encoding, has_mojibake

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(BASE_DIR, 'data', 'intermediate', '01_extracted.csv')
OUTPUT_PATH = os.path.join(BASE_DIR, 'data', 'intermediate', '02_encoding_fixed.csv')


def main():
    log.info(f"Reading {INPUT_PATH}")

    rows = []
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    log.info(f"Loaded {len(rows)} entries")

    # Analyze before fixing
    mojibake_before = sum(1 for r in rows if has_mojibake(r.get('content', '')) or has_mojibake(r.get('page_title', '')))
    log.info(f"Entries with Mojibake before fix: {mojibake_before} ({100*mojibake_before/len(rows):.1f}%)")

    # Fix encoding in content and title fields
    fixed_count = 0
    for row in rows:
        changed = False
        for field in ('content', 'page_title'):
            original = row.get(field, '')
            if original:
                fixed = fix_encoding(original)
                if fixed != original:
                    row[field] = fixed
                    changed = True
        if changed:
            fixed_count += 1

    log.info(f"Fixed encoding in {fixed_count} entries")

    # Verify
    mojibake_after = sum(1 for r in rows if has_mojibake(r.get('content', '')) or has_mojibake(r.get('page_title', '')))
    log.info(f"Entries with Mojibake after fix: {mojibake_after} ({100*mojibake_after/len(rows):.1f}%)")

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['page_id', 'page_title', 'text_id', 'content', 'flags', 'blob_id'])
        writer.writeheader()
        writer.writerows(rows)

    log.info(f"Output written to {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
