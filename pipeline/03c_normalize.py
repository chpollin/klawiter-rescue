#!/usr/bin/env python3
"""
Step 03c: Normalize extracted fields.

Applies auditable normalization rules via external mapping tables.
Does NOT invent data — only standardizes existing values or rejects garbage.

Input:  data/intermediate/03b_llm_enriched.csv (or 03_parsed.csv)
Output: data/intermediate/03c_normalized.csv
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (
    PARSED_FIELDS,
    STEP_03_OUTPUT,
    STEP_03B_OUTPUT,
    STEP_03C_OUTPUT,
    load_csv,
    setup_logging,
    write_csv,
)
from lib.encoding import fix_encoding, has_mojibake

log = setup_logging("normalize")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# --- Mapping loaders ---


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --- Normalization functions ---

TRANSLATOR_SUFFIX_RE = re.compile(
    r"\.\s*(Afterword|Foreword|Introduction|Preface|Edited|Cover|"
    r"Postface|Nachwort|Vorwort|Einleitung).*$",
    re.IGNORECASE,
)

# Page-count plausibility bounds (independent of config.MAX_VALID_YEAR, which is
# dynamic year+5; these are fixed so the reject behavior is stable over time).
MAX_PLAUSIBLE_PAGE_COUNT = 2000
YEAR_LIKE_MIN = 1800
YEAR_LIKE_MAX = 2030


def normalize_location(value, loc_map):
    """Map location variants to canonical form."""
    if not value or not loc_map:
        return value
    return loc_map.get(value, value)


def normalize_all_locations(value, loc_map):
    """Normalize each location in a JSON-serialized list."""
    if not value or not loc_map:
        return value
    try:
        locs = json.loads(value)
        normalized = [loc_map.get(loc, loc) for loc in locs]
        return json.dumps(
            list(dict.fromkeys(normalized))
        )  # deduplicate, preserve order
    except (json.JSONDecodeError, TypeError):
        return value


def clean_publisher(value, reject_patterns):
    """Reject garbage publisher values. Returns value or empty string."""
    if not value:
        return value
    for pattern in reject_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            return ""
    return value


def normalize_publisher(value, pub_map):
    """Map publisher variants to canonical form."""
    if not value or not pub_map:
        return value
    # Reverse lookup: check if value is in any variant list
    for canonical, variants in pub_map.items():
        if value in variants:
            return canonical
    return value


def clean_translator(value):
    """Fix mojibake and strip non-person suffixes from translator field."""
    if not value:
        return value
    # Fix mojibake
    if has_mojibake(value):
        value = fix_encoding(value)
    # Strip afterword/foreword suffixes
    cleaned = TRANSLATOR_SUFFIX_RE.sub("", value).strip().rstrip(".,;:")
    return cleaned if len(cleaned) >= 3 else value


def validate_page_count(value):
    """Reject implausible page counts (outliers and year-like values)."""
    if not value:
        return value
    try:
        n = int(value)
    except (ValueError, TypeError):
        return value
    if n > MAX_PLAUSIBLE_PAGE_COUNT:
        return ""
    if YEAR_LIKE_MIN <= n <= YEAR_LIKE_MAX:
        return ""
    return value


# --- Main ---


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize deterministic or LLM-enriched parsed fields."
    )
    parser.add_argument(
        "--input",
        choices=("03", "03b"),
        default="03b",
        help="Select the parsed input explicitly; stale intermediates are never auto-selected.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    input_path = STEP_03B_OUTPUT if args.input == "03b" else STEP_03_OUTPUT
    rows = load_csv(input_path)
    log.info(f"Loaded {len(rows)} entries from {os.path.basename(input_path)}")

    # Load mapping tables
    loc_map = load_json("location_normalize.json") or {}
    pub_reject = load_json("publisher_reject_patterns.json") or {}
    reject_patterns = pub_reject.get("patterns", [])
    pub_map = load_json("publisher_normalize.json") or {}

    # Counters
    stats = {
        "location_normalized": 0,
        "publisher_rejected": 0,
        "publisher_normalized": 0,
        "translator_cleaned": 0,
        "pagecount_rejected": 0,
    }

    for row in rows:
        # Location
        old_loc = row.get("location", "")
        row["location"] = normalize_location(old_loc, loc_map)
        if row["location"] != old_loc and old_loc:
            stats["location_normalized"] += 1
        row["all_locations"] = normalize_all_locations(
            row.get("all_locations", ""), loc_map
        )

        # Publisher: reject garbage, then normalize variants
        old_pub = row.get("publisher", "")
        row["publisher"] = clean_publisher(old_pub, reject_patterns)
        if row["publisher"] != old_pub and old_pub:
            stats["publisher_rejected"] += 1
        if row["publisher"] and pub_map:
            old_pub2 = row["publisher"]
            row["publisher"] = normalize_publisher(old_pub2, pub_map)
            if row["publisher"] != old_pub2:
                stats["publisher_normalized"] += 1

        # Translator
        old_tr = row.get("translator", "")
        row["translator"] = clean_translator(old_tr)
        if row["translator"] != old_tr and old_tr:
            stats["translator_cleaned"] += 1

        # Page count
        old_pc = row.get("page_count", "")
        row["page_count"] = validate_page_count(old_pc)
        if row["page_count"] != old_pc and old_pc:
            stats["pagecount_rejected"] += 1

    # Write output
    write_csv(STEP_03C_OUTPUT, rows, PARSED_FIELDS)

    log.info(f"Wrote {len(rows)} entries to {os.path.basename(STEP_03C_OUTPUT)}")
    log.info("Normalization stats:")
    for key, count in stats.items():
        log.info(f"  {key}: {count}")


if __name__ == "__main__":
    main()
