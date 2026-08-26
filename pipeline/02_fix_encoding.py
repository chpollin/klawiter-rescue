#!/usr/bin/env python3
"""
Step 2: Fix Mojibake encoding issues in extracted data.
Detects UTF-8 bytes misinterpreted as Latin-1 and repairs line-by-line.

Input:  data/intermediate/01_extracted.csv
Output: data/intermediate/02_encoding_fixed.csv
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (
    EXTRACTED_FIELDS,
    STEP_01_OUTPUT,
    STEP_02_OUTPUT,
    load_csv,
    setup_logging,
    write_csv,
)
from lib.encoding import fix_encoding, has_mojibake

log = setup_logging(__name__)


def main():
    rows = load_csv(STEP_01_OUTPUT)
    log.info(f"Loaded {len(rows)} entries")

    mojibake_before = sum(
        1
        for r in rows
        if has_mojibake(r.get("content", "")) or has_mojibake(r.get("page_title", ""))
    )
    log.info(
        f"Entries with Mojibake before fix: {mojibake_before} ({100 * mojibake_before / len(rows):.1f}%)"
    )

    fixed_count = 0
    for row in rows:
        changed = False
        for field in ("content", "page_title"):
            original = row.get(field, "")
            if original:
                fixed = fix_encoding(original)
                if fixed != original:
                    row[field] = fixed
                    changed = True
        if changed:
            fixed_count += 1

    log.info(f"Fixed encoding in {fixed_count} entries")

    mojibake_after = sum(
        1
        for r in rows
        if has_mojibake(r.get("content", "")) or has_mojibake(r.get("page_title", ""))
    )
    log.info(
        f"Entries with Mojibake after fix: {mojibake_after} ({100 * mojibake_after / len(rows):.1f}%)"
    )

    write_csv(STEP_02_OUTPUT, rows, EXTRACTED_FIELDS)
    log.info(f"Output written to {STEP_02_OUTPUT}")


if __name__ == "__main__":
    main()
