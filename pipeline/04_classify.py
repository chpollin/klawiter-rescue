#!/usr/bin/env python3
"""
Step 4: Classify entry types and resolve relationships.
Maps categories to entry types, assigns time periods, resolves redirects.
Handles all namespaces: ns 0 = bibliography, ns 14 = category pages, etc.

Input:  data/intermediate/03_parsed.csv
Output: data/intermediate/04_classified.csv
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import setup_logging, load_csv, write_csv, STEP_03_OUTPUT, STEP_04_OUTPUT
from lib.vocabulary import category_to_entry_type, classify_time_period

log = setup_logging(__name__)

OUTPUT_FIELDS = [
    'page_id', 'page_namespace', 'page_title', 'text_id', 'blob_id',
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

# MediaWiki namespace names
NAMESPACE_NAMES = {
    0: 'main', 6: 'file', 8: 'mediawiki', 10: 'template', 12: 'help', 14: 'category',
}


def classify_entry(row):
    """Determine entry type based on namespace, categories, and content."""
    namespace = int(row.get('page_namespace', 0))

    # Non-main namespaces get their own type
    if namespace != 0:
        return NAMESPACE_NAMES.get(namespace, f'namespace-{namespace}')

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
    content = (row.get('raw_content', '') or '').lower()

    if 'novel' in content or 'novella' in content or 'novelle' in content:
        return 'fiction'
    if 'essay' in content:
        return 'essay'
    if 'poem' in content or 'gedicht' in content:
        return 'poetry'
    if 'drama' in content or 'play' in content or 'libretto' in content:
        return 'drama'
    if 'letter' in content or 'brief' in content or 'correspondence' in content:
        return 'correspondence'
    if 'film' in content or 'movie' in content or 'opera' in content:
        return 'film'
    if 'translation' in content or 'translated' in content:
        return 'translation'

    return 'other'


def build_redirect_map(rows):
    """Build a map of redirect targets to page_ids for relationship resolution."""
    title_to_page = {}
    for row in rows:
        title = row.get('title', '') or row.get('page_title', '')
        if title:
            title_to_page[title] = row['page_id']
    return title_to_page


def main():
    rows = load_csv(STEP_03_OUTPUT)
    log.info(f"Loaded {len(rows)} entries, classifying...")

    title_to_page = build_redirect_map(rows)

    type_counts = {}
    period_counts = {}

    for row in rows:
        entry_type = classify_entry(row)
        row['entry_type'] = entry_type
        type_counts[entry_type] = type_counts.get(entry_type, 0) + 1

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

        if row.get('redirect_target'):
            target = row['redirect_target']
            target_page_id = title_to_page.get(target)
            if target_page_id:
                row['redirect_target'] = f"{target} (→ {target_page_id})"

    log.info("Entry type distribution:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        log.info(f"  {t}: {count} ({100*count/len(rows):.1f}%)")

    log.info("Time period distribution:")
    for p, count in sorted(period_counts.items(), key=lambda x: -x[1]):
        log.info(f"  {p}: {count}")

    write_csv(STEP_04_OUTPUT, rows, OUTPUT_FIELDS)
    log.info(f"Output written to {STEP_04_OUTPUT}")


if __name__ == '__main__':
    main()
