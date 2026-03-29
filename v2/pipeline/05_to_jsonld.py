#!/usr/bin/env python3
"""
Step 5: Convert classified entries to JSON-LD.
Produces both individual entry files and a complete dataset file.

Input:  data/intermediate/04_classified.csv
Output: data/output/klawiter.jsonld (complete dataset)
        data/output/entries/*.jsonld (individual entries)
"""

import csv
import json
import os
import sys
import logging

csv.field_size_limit(10 * 1024 * 1024)  # 10MB field limit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.vocabulary import CONTEXT, ENTRY_TYPES

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(BASE_DIR, 'data', 'intermediate', '04_classified.csv')
OUTPUT_DATASET = os.path.join(BASE_DIR, 'data', 'output', 'klawiter.jsonld')
OUTPUT_ENTRIES_DIR = os.path.join(BASE_DIR, 'data', 'output', 'entries')
OUTPUT_FRONTEND = os.path.join(BASE_DIR, 'frontend', 'data', 'klawiter.json')


def safe_json_parse(value):
    """Parse a JSON string, returning empty list/None on failure."""
    if not value:
        return None
    try:
        parsed = json.loads(value)
        return parsed if parsed else None
    except (json.JSONDecodeError, TypeError):
        return None


def row_to_jsonld(row):
    """Convert a CSV row to a JSON-LD entry."""
    page_id = row['page_id']
    entry_type = row.get('entry_type', 'other')

    entry = {
        "@type": f"klawiter:{entry_type.title().replace('-', '')}Entry",
        "@id": f"klawiter:entry/{page_id}",
        "klawiter:entryType": entry_type,
    }

    # Title
    title = row.get('title', '')
    if title:
        entry["klawiter:title"] = title

    original_title = row.get('original_title', '')
    if original_title:
        entry["klawiter:originalTitle"] = original_title

    # Source provenance (set for ALL entries including redirects)
    entry["klawiter:sourcePageId"] = int(page_id)
    text_id = row.get('text_id', '')
    if text_id:
        try:
            entry["klawiter:sourceTextId"] = int(text_id)
        except (ValueError, TypeError):
            pass

    # Redirect
    if row.get('is_redirect') in ('True', 'true', '1'):
        entry["klawiter:isRedirect"] = True
        redirect_target = row.get('redirect_target', '')
        if redirect_target:
            entry["klawiter:redirectTarget"] = redirect_target
        return entry

    # Year
    year = row.get('year', '')
    if year:
        try:
            entry["klawiter:year"] = int(float(year))
        except (ValueError, TypeError):
            pass

    all_years = safe_json_parse(row.get('all_years', ''))
    if all_years and len(all_years) > 1:
        entry["klawiter:allYears"] = all_years

    # Time period
    time_period = row.get('time_period', '')
    if time_period:
        entry["klawiter:timePeriod"] = time_period

    # Publisher
    publisher = row.get('publisher', '')
    if publisher:
        entry["klawiter:publisher"] = publisher

    # Location
    location = row.get('location', '')
    if location:
        entry["klawiter:location"] = location

    all_locations = safe_json_parse(row.get('all_locations', ''))
    if all_locations and len(all_locations) > 1:
        entry["klawiter:allLocations"] = all_locations

    # Language
    language = row.get('language', '')
    language_iso = row.get('language_iso', '')
    if language:
        entry["klawiter:language"] = language
    if language_iso:
        entry["klawiter:languageCode"] = language_iso

    # Page count
    page_count = row.get('page_count', '')
    if page_count:
        try:
            entry["klawiter:pageCount"] = int(float(page_count))
        except (ValueError, TypeError):
            pass

    # Translator
    translator = row.get('translator', '')
    if translator:
        entry["klawiter:translator"] = translator

    # Categories
    categories = safe_json_parse(row.get('categories', ''))
    if categories:
        entry["klawiter:categories"] = categories

    main_category = row.get('main_category', '')
    if main_category:
        entry["klawiter:mainCategory"] = main_category

    # Cross-references
    see_also = safe_json_parse(row.get('see_also', ''))
    if see_also:
        entry["klawiter:seeAlso"] = see_also

    reprints = safe_json_parse(row.get('reprints', ''))
    if reprints:
        entry["klawiter:reprints"] = reprints

    translations = safe_json_parse(row.get('translations', ''))
    if translations:
        entry["klawiter:translations"] = translations

    content_items = safe_json_parse(row.get('content_items', ''))
    if content_items:
        entry["klawiter:contentItems"] = content_items

    # Full bibliographic entry (cleaned)
    clean_content = row.get('clean_content', '')
    if clean_content:
        entry["klawiter:fullBibliographicEntry"] = clean_content

    # Blob ID (provenance — page_id and text_id already set above)
    blob_id = row.get('blob_id', '')
    if blob_id and blob_id != '-1':
        try:
            entry["klawiter:sourceBlobId"] = int(blob_id)
        except (ValueError, TypeError):
            pass

    return entry


def make_frontend_entry(jsonld_entry):
    """Create a simplified entry for the frontend JSON (no @context, shorter keys)."""
    e = {}
    for key, val in jsonld_entry.items():
        if key.startswith('@'):
            e[key] = val
        elif key.startswith('klawiter:'):
            short_key = key.split(':')[1]
            e[short_key] = val
    return e


def main():
    log.info(f"Reading {INPUT_PATH}")

    rows = []
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    log.info(f"Loaded {len(rows)} entries, converting to JSON-LD...")

    # Convert all entries
    entries = []
    for row in rows:
        entry = row_to_jsonld(row)
        entries.append(entry)

    # Write complete dataset
    os.makedirs(os.path.dirname(OUTPUT_DATASET), exist_ok=True)
    dataset = {
        **CONTEXT,
        "@type": "klawiter:Bibliography",
        "@id": "klawiter:klawiter-bibliography",
        "klawiter:name": "Stefan Zweig Bibliography (Klawiter)",
        "klawiter:compiler": "Dr. Randolph J. Klawiter",
        "klawiter:institution": "University of Notre Dame",
        "klawiter:totalEntries": len(entries),
        "klawiter:entries": entries,
    }

    with open(OUTPUT_DATASET, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    log.info(f"Complete dataset written to {OUTPUT_DATASET}")

    # Write individual entry files
    os.makedirs(OUTPUT_ENTRIES_DIR, exist_ok=True)
    for entry in entries:
        entry_id = entry.get('@id', '').split('/')[-1]
        if entry_id:
            entry_file = {**CONTEXT, **entry}
            path = os.path.join(OUTPUT_ENTRIES_DIR, f'{entry_id}.jsonld')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(entry_file, f, ensure_ascii=False, indent=2)

    log.info(f"Individual entries written to {OUTPUT_ENTRIES_DIR}/ ({len(entries)} files)")

    # Write frontend-optimized JSON
    # - Non-redirects: full entries with short keys
    # - Redirects: separate map (title -> target page_id) for URL resolution
    os.makedirs(os.path.dirname(OUTPUT_FRONTEND), exist_ok=True)

    non_redirect_entries = []
    redirect_map = {}  # page_title -> target_page_id
    title_to_pid = {}  # build lookup: title -> sourcePageId

    # First pass: index non-redirect titles
    for e in entries:
        if not e.get('klawiter:isRedirect'):
            fe = make_frontend_entry(e)
            non_redirect_entries.append(fe)
            title = e.get('klawiter:title', '')
            pid = e.get('klawiter:sourcePageId')
            if title and pid:
                title_to_pid[title] = pid

    # Second pass: resolve redirects to target page_ids
    for e in entries:
        if e.get('klawiter:isRedirect'):
            target_title = e.get('klawiter:title', '')
            source_title = e.get('klawiter:redirectTarget', '') or target_title
            target_pid = title_to_pid.get(target_title)
            if target_pid:
                # Map both the source page_title and the redirect target
                redirect_map[target_title] = target_pid
                if source_title != target_title:
                    redirect_map[source_title] = target_pid

    frontend_data = {
        "name": "Stefan Zweig Bibliography (Klawiter)",
        "compiler": "Dr. Randolph J. Klawiter",
        "institution": "University of Notre Dame",
        "totalEntries": len(non_redirect_entries),
        "entries": non_redirect_entries,
        "redirects": redirect_map,
    }

    with open(OUTPUT_FRONTEND, 'w', encoding='utf-8') as f:
        json.dump(frontend_data, f, ensure_ascii=False, separators=(',', ':'))

    size_mb = os.path.getsize(OUTPUT_FRONTEND) / 1024 / 1024
    log.info(f"Frontend JSON written to {OUTPUT_FRONTEND} ({size_mb:.1f} MB)")
    log.info(f"  Non-redirect entries: {len(non_redirect_entries)}")
    log.info(f"  Redirect map entries: {len(redirect_map)}")

    # Stats
    types = {}
    redirects = 0
    for e in entries:
        t = e.get('klawiter:entryType', 'unknown')
        types[t] = types.get(t, 0) + 1
        if e.get('klawiter:isRedirect'):
            redirects += 1

    log.info(f"JSON-LD conversion complete:")
    log.info(f"  Total entries: {len(entries)}")
    log.info(f"  Redirects: {redirects}")
    log.info(f"  Types: {json.dumps(types, indent=4)}")


if __name__ == '__main__':
    main()
