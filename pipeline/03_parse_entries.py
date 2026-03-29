#!/usr/bin/env python3
"""
Step 3: Parse wiki markup into structured fields.
Extracts titles, years, publishers, locations, languages, translators,
cross-references, reprints, and content items from raw wiki content.

Input:  data/intermediate/02_encoding_fixed.csv
Output: data/intermediate/03_parsed.csv
"""

import csv
import os
import re
import sys
import json
import logging

csv.field_size_limit(10 * 1024 * 1024)  # 10MB field limit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.wiki_parser import extract_structured_data, is_redirect, remove_wiki_markup
from lib.patterns import (
    extract_year, extract_all_years, extract_publisher,
    extract_location, extract_all_locations, extract_page_count,
    extract_translator, extract_language_from_category,
)
from lib.vocabulary import language_to_iso

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(BASE_DIR, 'data', 'intermediate', '02_encoding_fixed.csv')
OUTPUT_PATH = os.path.join(BASE_DIR, 'data', 'intermediate', '03_parsed.csv')

OUTPUT_FIELDS = [
    'page_id', 'page_title', 'text_id', 'blob_id',
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


def derive_main_category(categories):
    """Derive the main (top-level) category from category list."""
    if not categories:
        return ''
    # Categories look like "Fiction / Novels (German)" — take the first part
    for cat in categories:
        parts = cat.split('/')
        main = parts[0].strip()
        if main:
            return main
    return ''


def process_entry(row):
    """Process a single entry: parse wiki content and extract metadata."""
    content = row.get('content', '')
    result = {
        'page_id': row['page_id'],
        'page_title': row.get('page_title', ''),
        'text_id': row.get('text_id', ''),
        'blob_id': row.get('blob_id', ''),
        'raw_content': content,
    }

    if not content:
        result.update({k: '' for k in OUTPUT_FIELDS if k not in result})
        return result

    # Parse structured data from wiki content
    parsed = extract_structured_data(content)

    result['is_redirect'] = parsed.get('is_redirect', False)
    result['redirect_target'] = parsed.get('redirect_target', '')

    if result['is_redirect']:
        # For redirects, use the target as title and skip other parsing
        result['title'] = parsed.get('redirect_target', '')
        result.update({k: '' for k in OUTPUT_FIELDS if k not in result})
        return result

    # Title: prefer parsed title, but fall back to page_title.
    # page_title is always a clean work title from the MediaWiki page name.
    extracted_title = parsed.get('title', '')
    page_title = row.get('page_title', '')
    # If extracted title looks like publication info ("[year]: Publisher"), use page_title
    if page_title and (not extracted_title or re.match(r'\[\d{4}', extracted_title)):
        result['title'] = page_title
    else:
        result['title'] = extracted_title or page_title
    result['original_title'] = parsed.get('original_title', '')
    result['sortkey'] = parsed.get('sortkey', '')

    # Categories
    categories = parsed.get('categories', [])
    result['categories'] = json.dumps(categories, ensure_ascii=False) if categories else ''
    result['main_category'] = derive_main_category(categories)

    # Clean content for metadata extraction
    clean = parsed.get('clean_content', '')
    result['clean_content'] = clean

    # Year
    result['year'] = extract_year(content) or ''
    all_years = extract_all_years(content)
    result['all_years'] = json.dumps(all_years) if all_years else ''

    # Publisher
    result['publisher'] = extract_publisher(content) or ''

    # Location
    result['location'] = extract_location(content) or ''
    all_locs = extract_all_locations(content)
    result['all_locations'] = json.dumps(all_locs, ensure_ascii=False) if all_locs else ''

    # Language (from categories, then from content)
    lang_name = extract_language_from_category(categories)
    result['language'] = lang_name or ''
    result['language_iso'] = language_to_iso(lang_name) if lang_name else ''

    # Page count
    result['page_count'] = extract_page_count(content) or ''

    # Translator
    result['translator'] = extract_translator(content) or ''

    # Cross-references
    see_also = parsed.get('see_also', [])
    result['see_also'] = json.dumps(see_also, ensure_ascii=False) if see_also else ''

    reprints = parsed.get('reprints', [])
    result['reprints'] = json.dumps(reprints, ensure_ascii=False) if reprints else ''

    translations = parsed.get('translations', [])
    result['translations'] = json.dumps(translations, ensure_ascii=False) if translations else ''

    content_items = parsed.get('content_items', [])
    result['content_items'] = json.dumps(content_items, ensure_ascii=False) if content_items else ''

    return result


def main():
    log.info(f"Reading {INPUT_PATH}")

    rows = []
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    log.info(f"Loaded {len(rows)} entries, parsing...")

    results = []
    redirects = 0
    with_year = 0
    with_publisher = 0
    with_location = 0
    with_language = 0
    with_title = 0
    empty = 0

    for i, row in enumerate(rows):
        parsed = process_entry(row)
        results.append(parsed)

        if parsed['is_redirect']:
            redirects += 1
        if parsed['year']:
            with_year += 1
        if parsed['publisher']:
            with_publisher += 1
        if parsed['location']:
            with_location += 1
        if parsed['language']:
            with_language += 1
        if parsed['title']:
            with_title += 1
        if not parsed.get('raw_content'):
            empty += 1

        if (i + 1) % 1000 == 0:
            log.info(f"  Processed {i+1}/{len(rows)}...")

    total = len(results)
    non_redirect = total - redirects
    log.info(f"Parsing complete:")
    log.info(f"  Total: {total}")
    log.info(f"  Redirects: {redirects} ({100*redirects/total:.1f}%)")
    log.info(f"  Empty content: {empty}")
    log.info(f"  With title: {with_title} ({100*with_title/total:.1f}%)")
    log.info(f"  With year: {with_year} ({100*with_year/total:.1f}%)")
    log.info(f"  With publisher: {with_publisher} ({100*with_publisher/total:.1f}%)")
    log.info(f"  With location: {with_location} ({100*with_location/total:.1f}%)")
    log.info(f"  With language: {with_language} ({100*with_language/total:.1f}%)")

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(results)

    log.info(f"Output written to {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
