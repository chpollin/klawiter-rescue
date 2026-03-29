#!/usr/bin/env python3
"""
Step 4: Classify entry types and resolve relationships.
Maps categories to entry types, assigns time periods, resolves redirects.

Input:  data/intermediate/03_parsed.csv
Output: data/intermediate/04_classified.csv
"""

import csv
import json
import os
import sys
import logging

csv.field_size_limit(10 * 1024 * 1024)  # 10MB field limit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.vocabulary import category_to_entry_type, classify_time_period, CATEGORY_TYPE_MAP

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(BASE_DIR, 'data', 'intermediate', '03_parsed.csv')
OUTPUT_PATH = os.path.join(BASE_DIR, 'data', 'intermediate', '04_classified.csv')

OUTPUT_FIELDS = [
    'page_id', 'page_title', 'text_id', 'blob_id',
    'entry_type', 'is_redirect', 'redirect_target',
    'title', 'original_title', 'sortkey',
    'year', 'all_years', 'time_period',
    'publisher', 'location', 'all_locations',
    'language', 'language_iso',
    'page_count', 'translator',
    'categories', 'main_category',
    'see_also', 'reprints', 'translations', 'content_items',
    'clean_content', 'raw_content',
]


def classify_entry(row):
    """Determine entry type based on categories and content analysis."""
    # Redirects
    if row.get('is_redirect') in ('True', 'true', '1'):
        return 'redirect'

    # Try category-based classification
    main_cat = row.get('main_category', '')
    if main_cat:
        entry_type = category_to_entry_type(main_cat)
        if entry_type != 'other':
            return entry_type

    # Content-based fallback
    content = row.get('raw_content', '') or ''
    content_lower = content.lower()

    if 'novel' in content_lower or 'novella' in content_lower or 'novelle' in content_lower:
        return 'fiction'
    if 'essay' in content_lower:
        return 'essay'
    if 'poem' in content_lower or 'gedicht' in content_lower:
        return 'poetry'
    if 'drama' in content_lower or 'play' in content_lower or 'libretto' in content_lower:
        return 'drama'
    if 'letter' in content_lower or 'brief' in content_lower or 'correspondence' in content_lower:
        return 'correspondence'
    if 'film' in content_lower or 'movie' in content_lower or 'opera' in content_lower:
        return 'film'
    if 'translation' in content_lower or 'translated' in content_lower:
        return 'translation'

    return 'other'


def build_redirect_map(rows):
    """Build a map of redirect targets to page_ids for relationship resolution."""
    # Title -> page_id lookup
    title_to_page = {}
    for row in rows:
        title = row.get('title', '') or row.get('page_title', '')
        if title:
            title_to_page[title] = row['page_id']
    return title_to_page


def main():
    log.info(f"Reading {INPUT_PATH}")

    rows = []
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    log.info(f"Loaded {len(rows)} entries, classifying...")

    # Build title lookup for redirect resolution
    title_to_page = build_redirect_map(rows)

    type_counts = {}
    period_counts = {}

    for row in rows:
        # Classify entry type
        entry_type = classify_entry(row)
        row['entry_type'] = entry_type
        type_counts[entry_type] = type_counts.get(entry_type, 0) + 1

        # Assign time period
        year = row.get('year', '')
        if year:
            try:
                year_int = int(float(year))
                period = classify_time_period(year_int)
                row['time_period'] = period or ''
                if period:
                    period_counts[period] = period_counts.get(period, 0) + 1
            except (ValueError, TypeError):
                row['time_period'] = ''
        else:
            row['time_period'] = ''

        # Resolve redirect targets to page_ids where possible
        if row.get('redirect_target'):
            target = row['redirect_target']
            target_page_id = title_to_page.get(target)
            if target_page_id:
                row['redirect_target'] = f"{target} (→ {target_page_id})"

    # Log statistics
    log.info("Entry type distribution:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        log.info(f"  {t}: {count} ({100*count/len(rows):.1f}%)")

    log.info("Time period distribution:")
    for p, count in sorted(period_counts.items(), key=lambda x: -x[1]):
        log.info(f"  {p}: {count}")

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    log.info(f"Output written to {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
