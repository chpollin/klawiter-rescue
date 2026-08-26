#!/usr/bin/env python3
"""
Step 1: Extract all pages from SQL dump + binary BLOB files.
No MySQL required — parses the raw files directly.
Extracts ALL namespaces (main, category, template, etc.).

Input:  data/raw/zweig_part_01.sql, data/raw/zt_00..zt_07
Output: data/intermediate/01_extracted.csv
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (
    BLOB_FILES,
    EXTRACTED_FIELDS,
    SQL_DUMP_PATH,
    STEP_01_OUTPUT,
    STEP_01_PAGELINKS,
    setup_logging,
    write_csv,
)

PAGELINK_FIELDS = ["pl_from", "pl_namespace", "pl_title"]

log = setup_logging(__name__)


def parse_sql_inserts(sql_text, table_name):
    """Parse INSERT INTO statements for a given table from SQL text.
    Returns raw value tuples as strings.
    """
    pattern = re.compile(
        rf"INSERT INTO `{re.escape(table_name)}` VALUES\s*(.+?);\s*$",
        re.MULTILINE | re.DOTALL,
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
        if values_str[i] == "(":
            depth = 1
            j = i + 1
            in_string = False
            escape_next = False
            while j < len(values_str) and depth > 0:
                c = values_str[j]
                if escape_next:
                    escape_next = False
                elif c == "\\":
                    if in_string:
                        escape_next = True
                elif c == "'":
                    in_string = not in_string
                elif not in_string:
                    if c == "(":
                        depth += 1
                    elif c == ")":
                        depth -= 1
                j += 1
            tuple_str = values_str[i + 1 : j - 1]
            tuples.append(tuple_str)
            i = j
        else:
            i += 1
    return tuples


def parse_tuple_values(tuple_str):
    """Parse a single value tuple string into individual values."""
    values = []
    i = 0
    current = ""
    in_string = False
    escape_next = False

    while i < len(tuple_str):
        c = tuple_str[i]
        if escape_next:
            current += c
            escape_next = False
        elif c == "\\" and in_string:
            escape_next = True
            current += c
        elif c == "'" and in_string:
            if i + 1 < len(tuple_str) and tuple_str[i + 1] == "'":
                current += "'"
                i += 1
            else:
                in_string = False
        elif c == "'":
            in_string = True
        elif c == "," and not in_string:
            values.append(current.strip())
            current = ""
        else:
            current += c
        i += 1

    if current.strip():
        values.append(current.strip())
    return values


def clean_binary_value(val):
    """Clean a _binary 'xxx' value to just the string content."""
    val = val.strip()
    if val.startswith("_binary "):
        val = val[8:]
    if val.startswith("'") and val.endswith("'"):
        val = val[1:-1]
    val = val.replace("\\'", "'").replace("\\\\", "\\")
    return val


def load_page_table(sql_text):
    """Parse zweig_page table. Returns dict: page_id -> {title, namespace, page_latest}."""
    log.info("Parsing zweig_page...")
    pages = {}
    skipped = 0
    for values_str in parse_sql_inserts(sql_text, "zweig_page"):
        for t in parse_value_tuples(values_str):
            vals = parse_tuple_values(t)
            if len(vals) >= 10:
                page_id = int(vals[0])
                namespace = int(vals[1])
                title_raw = clean_binary_value(vals[2])
                page_latest = int(vals[8])
                try:
                    title = title_raw.replace("_", " ")
                except Exception:
                    title = title_raw
                pages[page_id] = {
                    "title": title,
                    "namespace": namespace,
                    "page_latest": page_latest,
                }
            else:
                skipped += 1
    if skipped:
        log.warning(
            f"  Skipped {skipped} malformed zweig_page tuples (fewer than 10 columns)"
        )
    log.info(f"  Parsed {len(pages)} pages")
    # Log namespace distribution
    ns_counts = {}
    for p in pages.values():
        ns = p["namespace"]
        ns_counts[ns] = ns_counts.get(ns, 0) + 1
    for ns, count in sorted(ns_counts.items()):
        log.info(f"    Namespace {ns}: {count} pages")
    return pages


def load_slots_table(sql_text):
    """Parse zweig_slots. Returns dict: rev_id -> content_id."""
    log.info("Parsing zweig_slots...")
    slots = {}
    skipped = 0
    for values_str in parse_sql_inserts(sql_text, "zweig_slots"):
        for t in parse_value_tuples(values_str):
            vals = parse_tuple_values(t)
            if len(vals) >= 4:
                rev_id = int(vals[0])
                content_id = int(vals[2])
                slots[rev_id] = content_id
            else:
                skipped += 1
    if skipped:
        log.warning(
            f"  Skipped {skipped} malformed zweig_slots tuples (fewer than 4 columns)"
        )
    log.info(f"  Parsed {len(slots)} slots")
    return slots


def load_content_table(sql_text):
    """Parse zweig_content. Returns dict: content_id -> text_id (from 'tt:XXXX')."""
    log.info("Parsing zweig_content...")
    contents = {}
    skipped = 0
    bad_addr = 0
    for values_str in parse_sql_inserts(sql_text, "zweig_content"):
        for t in parse_value_tuples(values_str):
            vals = parse_tuple_values(t)
            if len(vals) >= 5:
                content_id = int(vals[0])
                addr_raw = clean_binary_value(vals[4])
                if "tt:" in addr_raw:
                    try:
                        text_id = int(addr_raw.split("tt:")[1])
                        contents[content_id] = text_id
                    except (ValueError, IndexError):
                        bad_addr += 1
            else:
                skipped += 1
    if skipped:
        log.warning(
            f"  Skipped {skipped} malformed zweig_content tuples (fewer than 5 columns)"
        )
    if bad_addr:
        log.warning(f"  Skipped {bad_addr} content rows with unparseable tt: address")
    log.info(f"  Parsed {len(contents)} content addresses")
    return contents


def build_page_to_textid(pages, slots, contents):
    """Build the full mapping: page_id -> text_id via page_latest -> slots -> content.
    Extracts ALL namespaces.
    """
    log.info("Building page→text_id mapping (all namespaces)...")
    mapping = {}
    no_slot = 0
    no_content = 0
    for page_id, page_info in pages.items():
        rev_id = page_info["page_latest"]
        content_id = slots.get(rev_id)
        if content_id is None:
            no_slot += 1
            continue
        text_id = contents.get(content_id)
        if text_id is None:
            no_content += 1
            continue
        mapping[page_id] = {
            "text_id": text_id,
            "title": page_info["title"],
            "namespace": page_info["namespace"],
        }
    log.info(f"  Mapped {len(mapping)} pages to text IDs")
    if no_slot:
        log.info(f"  No slot found: {no_slot}")
    if no_content:
        log.info(f"  No content address: {no_content}")
    return mapping


def load_pagelinks_table(sql_text):
    """Parse zweig_pagelinks: MediaWiki's own resolved internal link graph.

    The wiki resolved every [[...]] link at save time; this table is the
    authoritative target list per source page and repairs See-references
    whose regex-extracted title differs from the canonical page title.
    Returns rows with display-form titles (underscores as spaces).
    """
    log.info("Parsing zweig_pagelinks...")
    links = []
    skipped = 0
    for values_str in parse_sql_inserts(sql_text, "zweig_pagelinks"):
        for t in parse_value_tuples(values_str):
            vals = parse_tuple_values(t)
            if len(vals) >= 3:
                links.append(
                    {
                        "pl_from": int(vals[0]),
                        "pl_namespace": int(vals[1]),
                        "pl_title": clean_binary_value(vals[2]).replace("_", " "),
                    }
                )
            else:
                skipped += 1
    if skipped:
        log.warning(
            f"  Skipped {skipped} malformed zweig_pagelinks tuples (fewer than 3 columns)"
        )
    log.info(f"  Parsed {len(links)} page links")
    return links


def load_blob_index(blob_path):
    """Parse a binary BLOB file and build text_id -> content lookup."""
    log.info(f"Indexing BLOB: {os.path.basename(blob_path)}...")

    with open(blob_path, "rb") as f:
        raw = f.read()

    text = raw.decode("latin-1")

    index = {}
    pattern = re.compile(
        r"\((\d+),_binary '((?:[^'\\]|\\.|'')*?)',_binary '((?:[^'\\]|\\.|'')*?)'\)"
    )

    for m in pattern.finditer(text):
        text_id = int(m.group(1))
        content = m.group(2)
        flags = m.group(3)
        content = content.replace("''", "'").replace("\\'", "'")
        content = content.replace("\\\\", "\\").replace("\\n", "\n")
        index[text_id] = {"content": content, "flags": flags}

    log.info(f"  Found {len(index)} text entries")
    return index


def main():
    log.info(f"Loading SQL dump: {SQL_DUMP_PATH}")
    with open(SQL_DUMP_PATH, "rb") as f:
        sql_text = f.read().decode("latin-1")

    # Parse MediaWiki tables
    pages = load_page_table(sql_text)
    # We don't need the full revision table — page_latest is the rev_id
    slots = load_slots_table(sql_text)
    contents = load_content_table(sql_text)

    # Build page → text_id mapping (all namespaces)
    mapping = build_page_to_textid(pages, slots, contents)

    # Load all BLOB files and build unified text index
    text_index = {}
    for blob_path in BLOB_FILES:
        if os.path.exists(blob_path):
            blob_index = load_blob_index(blob_path)
            blob_id = int(re.search(r"(\d+)$", os.path.basename(blob_path)).group(1))
            for text_id, data in blob_index.items():
                data["blob_id"] = blob_id
                text_index[text_id] = data
        else:
            log.warning(f"  BLOB file not found: {blob_path}")

    log.info(f"Total text index entries: {len(text_index)}")

    # Join: page mapping + text content
    results = []
    found = 0
    not_found = 0
    not_found_pages = []
    for page_id, info in sorted(mapping.items()):
        text_id = info["text_id"]
        title = info["title"]
        namespace = info["namespace"]
        text_data = text_index.get(text_id)
        if text_data:
            results.append(
                {
                    "page_id": page_id,
                    "page_namespace": namespace,
                    "page_title": title,
                    "text_id": text_id,
                    "content": text_data["content"],
                    "flags": text_data["flags"],
                    "blob_id": text_data["blob_id"],
                }
            )
            found += 1
        else:
            results.append(
                {
                    "page_id": page_id,
                    "page_namespace": namespace,
                    "page_title": title,
                    "text_id": text_id,
                    "content": "",
                    "flags": "",
                    "blob_id": -1,
                }
            )
            not_found += 1
            not_found_pages.append((page_id, title, text_id))

    log.info(
        f"Extraction complete: {found} found, {not_found} not found, {found + not_found} total"
    )
    for pid, title, tid in not_found_pages:
        log.warning(f'  Missing: page_id={pid}, text_id={tid}, title="{title}"')

    # Write output
    write_csv(STEP_01_OUTPUT, results, EXTRACTED_FIELDS)
    log.info(f"Output written to {STEP_01_OUTPUT}")

    pagelinks = load_pagelinks_table(sql_text)
    write_csv(STEP_01_PAGELINKS, pagelinks, PAGELINK_FIELDS)
    log.info(f"Page links written to {STEP_01_PAGELINKS}")
    log.info(
        f"Success rate: {found}/{found + not_found} ({100 * found / (found + not_found):.1f}%)"
    )


if __name__ == "__main__":
    main()
