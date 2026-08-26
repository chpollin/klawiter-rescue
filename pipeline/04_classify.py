#!/usr/bin/env python3
"""
Step 4: Classify entry types and resolve relationships.
Maps categories to entry types, assigns time periods, resolves redirects.
Handles all namespaces: ns 0 = bibliography, ns 14 = category pages, etc.

Input:  data/intermediate/03c_normalized.csv (explicit via --input)
Output: data/intermediate/04_classified.csv
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (
    CLASSIFIED_FIELDS,
    STEP_03_OUTPUT,
    STEP_03B_OUTPUT,
    STEP_03C_OUTPUT,
    STEP_04_OUTPUT,
    csv_bool,
    load_csv,
    setup_logging,
    write_csv,
)
from lib.vocabulary import category_to_entry_type, classify_time_period

log = setup_logging(__name__)

# MediaWiki namespace names
NAMESPACE_NAMES = {
    0: "main",
    6: "file",
    8: "mediawiki",
    10: "template",
    12: "help",
    14: "category",
}


def classify_entry(row):
    """Determine entry type based on namespace, categories, and content."""
    namespace = int(row.get("page_namespace", 0))

    # Non-main namespaces get their own type
    if namespace != 0:
        return NAMESPACE_NAMES.get(namespace, f"namespace-{namespace}")

    # Redirects
    if csv_bool(row.get("is_redirect")):
        return "redirect"

    # Try category-based classification
    main_cat = row.get("main_category", "")
    if main_cat:
        entry_type = category_to_entry_type(main_cat)
        if entry_type != "other":
            return entry_type

    # Content-based fallback
    content = (row.get("raw_content", "") or "").lower()

    if "novel" in content or "novella" in content or "novelle" in content:
        return "fiction"
    if "essay" in content:
        return "essay"
    if "poem" in content or "gedicht" in content:
        return "poetry"
    if "drama" in content or "play" in content or "libretto" in content:
        return "drama"
    if "letter" in content or "brief" in content or "correspondence" in content:
        return "correspondence"
    if "film" in content or "movie" in content or "opera" in content:
        return "film"
    if "translation" in content or "translated" in content:
        return "translation"

    return "other"


def build_redirect_map(rows):
    """Build a map of redirect targets to page_ids for relationship resolution."""
    title_to_page = {}
    for row in rows:
        title = row.get("title", "") or row.get("page_title", "")
        if title:
            title_to_page[title] = row["page_id"]
    return title_to_page


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Classify entry types and periods from an explicit input."
    )
    parser.add_argument(
        "--input",
        choices=("03", "03b", "03c"),
        default="03c",
        help="Select the classification input explicitly; stale intermediates are never auto-selected.",
    )
    return parser.parse_args()


def _input_path(choice):
    """Map the explicit input choice to its stage output; a missing file is a
    hard error in load_csv instead of a silent fallback to a stale stage."""
    return {
        "03": STEP_03_OUTPUT,
        "03b": STEP_03B_OUTPUT,
        "03c": STEP_03C_OUTPUT,
    }[choice]


def main():
    args = _parse_args()
    input_path = _input_path(args.input)
    rows = load_csv(input_path)
    log.info(f"Loaded {len(rows)} entries, classifying...")

    title_to_page = build_redirect_map(rows)

    type_counts = {}
    period_counts = {}

    for row in rows:
        entry_type = classify_entry(row)
        row["entry_type"] = entry_type
        type_counts[entry_type] = type_counts.get(entry_type, 0) + 1

        year = row.get("year", "")
        if year:
            try:
                year_int = int(year)
                period = classify_time_period(year_int)
                row["time_period"] = period or ""
                if period:
                    period_counts[period] = period_counts.get(period, 0) + 1
            except (ValueError, TypeError):
                row["time_period"] = ""
        else:
            row["time_period"] = ""

        if row.get("redirect_target"):
            target = row["redirect_target"]
            target_page_id = title_to_page.get(target)
            if target_page_id:
                row["redirect_target"] = f"{target} (→ {target_page_id})"

    log.info("Entry type distribution:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        log.info(f"  {t}: {count} ({100 * count / len(rows):.1f}%)")

    log.info("Time period distribution:")
    for p, count in sorted(period_counts.items(), key=lambda x: -x[1]):
        log.info(f"  {p}: {count}")

    write_csv(STEP_04_OUTPUT, rows, CLASSIFIED_FIELDS)
    log.info(f"Output written to {STEP_04_OUTPUT}")


if __name__ == "__main__":
    main()
