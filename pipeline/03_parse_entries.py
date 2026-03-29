#!/usr/bin/env python3
"""
Step 3: Parse wiki markup into structured fields.
Extracts titles, years, publishers, locations, languages, translators,
cross-references, reprints, and content items from raw wiki content.

Input:  data/intermediate/02_encoding_fixed.csv
Output: data/intermediate/03_parsed.csv
"""

import os
import re
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import setup_logging, load_csv, write_csv, STEP_02_OUTPUT, STEP_03_OUTPUT, PARSED_FIELDS
from lib.wiki_parser import extract_structured_data, is_redirect, remove_wiki_markup
from lib.patterns import (
    extract_year, extract_all_years, extract_publisher,
    extract_location, extract_all_locations, extract_page_count,
    extract_translator, extract_language_from_category,
)
from lib.vocabulary import language_to_iso

log = setup_logging(__name__)


def derive_main_category(categories):
    """Derive the main (top-level) category from category list."""
    if not categories:
        return ''
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
        'page_namespace': row.get('page_namespace', '0'),
        'page_title': row.get('page_title', ''),
        'text_id': row.get('text_id', ''),
        'blob_id': row.get('blob_id', ''),
        'raw_content': content,
    }

    if not content:
        result.update({k: '' for k in PARSED_FIELDS if k not in result})
        return result

    # Parse structured data from wiki content
    parsed = extract_structured_data(content)

    result['is_redirect'] = parsed.get('is_redirect', False)
    result['redirect_target'] = parsed.get('redirect_target', '')

    if result['is_redirect']:
        result['title'] = parsed.get('redirect_target', '')
        result.update({k: '' for k in PARSED_FIELDS if k not in result})
        return result

    # Title: prefer parsed title, but fall back to page_title
    extracted_title = parsed.get('title', '')
    page_title = row.get('page_title', '')
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
    rows = load_csv(STEP_02_OUTPUT)
    log.info(f"Loaded {len(rows)} entries, parsing...")

    results = []
    stats = {'redirects': 0, 'year': 0, 'publisher': 0, 'location': 0, 'language': 0, 'title': 0, 'empty': 0}

    for i, row in enumerate(rows):
        parsed = process_entry(row)
        results.append(parsed)

        if parsed['is_redirect']:
            stats['redirects'] += 1
        if parsed['year']:
            stats['year'] += 1
        if parsed['publisher']:
            stats['publisher'] += 1
        if parsed['location']:
            stats['location'] += 1
        if parsed['language']:
            stats['language'] += 1
        if parsed['title']:
            stats['title'] += 1
        if not parsed.get('raw_content'):
            stats['empty'] += 1

        if (i + 1) % 1000 == 0:
            log.info(f"  Processed {i+1}/{len(rows)}...")

    total = len(results)
    log.info(f"Parsing complete: {total} entries")
    log.info(f"  Redirects: {stats['redirects']} ({100*stats['redirects']/total:.1f}%)")
    log.info(f"  With title: {stats['title']} ({100*stats['title']/total:.1f}%)")
    log.info(f"  With year: {stats['year']} ({100*stats['year']/total:.1f}%)")
    log.info(f"  With publisher: {stats['publisher']} ({100*stats['publisher']/total:.1f}%)")
    log.info(f"  With location: {stats['location']} ({100*stats['location']/total:.1f}%)")
    log.info(f"  With language: {stats['language']} ({100*stats['language']/total:.1f}%)")

    write_csv(STEP_03_OUTPUT, results, PARSED_FIELDS)
    log.info(f"Output written to {STEP_03_OUTPUT}")


if __name__ == '__main__':
    main()
