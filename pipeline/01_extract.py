#!/usr/bin/env python3
"""
Step 1: Extract all bibliography entries from SQL dump + binary BLOB files.
No MySQL required — parses the raw files directly.

Input:  working/zweig_part_01.sql, working/zt_00..zt_07
Output: data/intermediate/01_extracted.csv
"""

import csv
import os
import re
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING_DIR = os.path.join(os.path.dirname(BASE_DIR), 'working')
OUTPUT_PATH = os.path.join(BASE_DIR, 'data', 'intermediate', '01_extracted.csv')


def parse_sql_inserts(sql_text, table_name):
    """Parse INSERT INTO statements for a given table from SQL text.
    Returns raw value tuples as strings.
    """
    pattern = re.compile(
        rf"INSERT INTO `{re.escape(table_name)}` VALUES\s*(.+?);\s*$",
        re.MULTILINE | re.DOTALL
    )
    results = []
    for match in pattern.finditer(sql_text):
        values_str = match.group(1)
        results.append(values_str)
    return results


def parse_value_tuples(values_str):
    """Parse (v1,v2,...),(v1,v2,...) into list of tuples.
    Handles _binary 'xxx' values and numeric values.
    """
    tuples = []
    i = 0
    while i < len(values_str):
        if values_str[i] == '(':
            # Find matching closing paren
            depth = 1
            j = i + 1
            in_string = False
            escape_next = False
            while j < len(values_str) and depth > 0:
                c = values_str[j]
                if escape_next:
                    escape_next = False
                elif c == '\\':
                    if in_string:
                        escape_next = True
                elif c == "'":
                    in_string = not in_string
                elif not in_string:
                    if c == '(':
                        depth += 1
                    elif c == ')':
                        depth -= 1
                j += 1
            tuple_str = values_str[i+1:j-1]
            tuples.append(tuple_str)
            i = j
        else:
            i += 1
    return tuples


def parse_tuple_values(tuple_str):
    """Parse a single value tuple string into individual values."""
    values = []
    i = 0
    current = ''
    in_string = False
    escape_next = False

    while i < len(tuple_str):
        c = tuple_str[i]
        if escape_next:
            current += c
            escape_next = False
        elif c == '\\' and in_string:
            escape_next = True
            current += c
        elif c == "'" and in_string:
            # Check for '' (escaped quote in SQL)
            if i + 1 < len(tuple_str) and tuple_str[i+1] == "'":
                current += "'"
                i += 1
            else:
                in_string = False
        elif c == "'":
            in_string = True
        elif c == ',' and not in_string:
            values.append(current.strip())
            current = ''
        else:
            current += c
        i += 1

    if current.strip():
        values.append(current.strip())
    return values


def clean_binary_value(val):
    """Clean a _binary 'xxx' value to just the string content."""
    val = val.strip()
    if val.startswith('_binary '):
        val = val[8:]
    if val.startswith("'") and val.endswith("'"):
        val = val[1:-1]
    # Unescape SQL escapes
    val = val.replace("\\'", "'").replace("\\\\", "\\")
    return val


def load_page_table(sql_text):
    """Parse zweig_page table. Returns dict: page_id -> {title, namespace, page_latest}."""
    log.info("Parsing zweig_page...")
    pages = {}
    for values_str in parse_sql_inserts(sql_text, 'zweig_page'):
        for t in parse_value_tuples(values_str):
            vals = parse_tuple_values(t)
            if len(vals) >= 10:
                page_id = int(vals[0])
                namespace = int(vals[1])
                title_raw = clean_binary_value(vals[2])
                page_latest = int(vals[8])
                # Decode title: stored as binary, may need hex decoding
                try:
                    title = title_raw.replace('_', ' ')
                except Exception:
                    title = title_raw
                pages[page_id] = {
                    'title': title,
                    'namespace': namespace,
                    'page_latest': page_latest,
                }
    log.info(f"  Parsed {len(pages)} pages")
    return pages


def load_revision_table(sql_text):
    """Parse zweig_revision. Returns dict: rev_id -> page_id."""
    log.info("Parsing zweig_revision...")
    revisions = {}
    for values_str in parse_sql_inserts(sql_text, 'zweig_revision'):
        for t in parse_value_tuples(values_str):
            vals = parse_tuple_values(t)
            if len(vals) >= 2:
                rev_id = int(vals[0])
                page_id = int(vals[1])
                revisions[rev_id] = page_id
    log.info(f"  Parsed {len(revisions)} revisions")
    return revisions


def load_slots_table(sql_text):
    """Parse zweig_slots. Returns dict: rev_id -> content_id."""
    log.info("Parsing zweig_slots...")
    slots = {}
    for values_str in parse_sql_inserts(sql_text, 'zweig_slots'):
        for t in parse_value_tuples(values_str):
            vals = parse_tuple_values(t)
            if len(vals) >= 4:
                rev_id = int(vals[0])
                content_id = int(vals[2])  # slot_content_id is 3rd field
                slots[rev_id] = content_id
    log.info(f"  Parsed {len(slots)} slots")
    return slots


def load_content_table(sql_text):
    """Parse zweig_content. Returns dict: content_id -> text_id (from 'tt:XXXX')."""
    log.info("Parsing zweig_content...")
    contents = {}
    for values_str in parse_sql_inserts(sql_text, 'zweig_content'):
        for t in parse_value_tuples(values_str):
            vals = parse_tuple_values(t)
            if len(vals) >= 5:
                content_id = int(vals[0])
                addr_raw = clean_binary_value(vals[4])
                # Extract text_id from "tt:XXXXX"
                if 'tt:' in addr_raw:
                    try:
                        text_id = int(addr_raw.split('tt:')[1])
                        contents[content_id] = text_id
                    except (ValueError, IndexError):
                        pass
    log.info(f"  Parsed {len(contents)} content addresses")
    return contents


def build_page_to_textid(pages, slots, contents):
    """Build the full mapping: page_id -> text_id via page_latest -> slots -> content."""
    log.info("Building page→text_id mapping...")
    mapping = {}
    no_slot = 0
    no_content = 0
    for page_id, page_info in pages.items():
        if page_info['namespace'] != 0:
            continue  # Only main namespace
        rev_id = page_info['page_latest']
        content_id = slots.get(rev_id)
        if content_id is None:
            no_slot += 1
            continue
        text_id = contents.get(content_id)
        if text_id is None:
            no_content += 1
            continue
        mapping[page_id] = {
            'text_id': text_id,
            'title': page_info['title'],
        }
    log.info(f"  Mapped {len(mapping)} pages to text IDs")
    log.info(f"  No slot found: {no_slot}, No content address: {no_content}")
    return mapping


def load_blob_index(blob_path):
    """Parse a binary BLOB file and build text_id -> content lookup.
    The BLOB contains SQL INSERT statements with format:
    (text_id,_binary 'content',_binary 'flags')
    """
    log.info(f"Indexing BLOB: {os.path.basename(blob_path)}...")

    with open(blob_path, 'rb') as f:
        raw = f.read()

    # Use latin-1 to preserve all byte values
    text = raw.decode('latin-1')

    index = {}
    # Find all (text_id, _binary 'content', _binary 'flags') tuples
    # Pattern matches: (NUMBER,_binary 'CONTENT',_binary 'FLAGS')
    pattern = re.compile(
        r"\((\d+),_binary '((?:[^'\\]|\\.|'')*?)',_binary '((?:[^'\\]|\\.|'')*?)'\)"
    )

    for m in pattern.finditer(text):
        text_id = int(m.group(1))
        content = m.group(2)
        flags = m.group(3)
        # Unescape SQL
        content = content.replace("''", "'").replace("\\'", "'")
        content = content.replace("\\\\", "\\").replace("\\n", "\n")
        index[text_id] = {'content': content, 'flags': flags}

    log.info(f"  Found {len(index)} text entries")
    return index


def main():
    # Load SQL dump
    sql_path = os.path.join(WORKING_DIR, 'zweig_part_01.sql')
    log.info(f"Loading SQL dump: {sql_path}")
    with open(sql_path, 'rb') as f:
        sql_text = f.read().decode('latin-1')

    # Parse MediaWiki tables
    pages = load_page_table(sql_text)
    # We don't need the full revision table — page_latest is the rev_id
    slots = load_slots_table(sql_text)
    contents = load_content_table(sql_text)

    # Build page → text_id mapping
    mapping = build_page_to_textid(pages, slots, contents)

    # Load all BLOB files and build unified text index
    text_index = {}
    for i in range(8):
        blob_path = os.path.join(WORKING_DIR, f'zt_0{i}')
        if os.path.exists(blob_path):
            blob_index = load_blob_index(blob_path)
            for text_id, data in blob_index.items():
                data['blob_id'] = i
                text_index[text_id] = data
        else:
            log.warning(f"  BLOB file not found: {blob_path}")

    log.info(f"Total text index entries: {len(text_index)}")

    # Join: page mapping + text content
    results = []
    found = 0
    not_found = 0
    for page_id, info in sorted(mapping.items()):
        text_id = info['text_id']
        title = info['title']
        text_data = text_index.get(text_id)
        if text_data:
            results.append({
                'page_id': page_id,
                'page_title': title,
                'text_id': text_id,
                'content': text_data['content'],
                'flags': text_data['flags'],
                'blob_id': text_data['blob_id'],
            })
            found += 1
        else:
            results.append({
                'page_id': page_id,
                'page_title': title,
                'text_id': text_id,
                'content': '',
                'flags': '',
                'blob_id': -1,
            })
            not_found += 1

    log.info(f"Extraction complete: {found} found, {not_found} not found, {found+not_found} total")

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['page_id', 'page_title', 'text_id', 'content', 'flags', 'blob_id'])
        writer.writeheader()
        writer.writerows(results)

    log.info(f"Output written to {OUTPUT_PATH}")
    log.info(f"Success rate: {found}/{found+not_found} ({100*found/(found+not_found):.1f}%)")


if __name__ == '__main__':
    main()
