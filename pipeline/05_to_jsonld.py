#!/usr/bin/env python3
"""
Step 5: Convert classified entries to JSON-LD.
Produces individual entry files, a complete dataset file, and frontend JSON.

Uses Schema.org + Dublin Core + klawiter: vocabulary blend.
Schema.org for standard bibliographic fields, DC for citation/provenance,
klawiter: for domain-specific extensions (entry types, time periods, categories).

Input:  data/intermediate/04_classified.csv
Output: data/output/klawiter.jsonld (complete dataset)
        data/output/entries/*.jsonld (individual entries)
        docs/data/klawiter.json (frontend-optimized)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (
    OUTPUT_ENTRIES_DIR,
    OUTPUT_FRONTEND_JSON,
    OUTPUT_JSONLD,
    OUTPUT_PUBLISHABLE_LINKS,
    STEP_04_OUTPUT,
    csv_bool,
    load_csv,
    setup_logging,
    write_json,
)
from lib.vocabulary import CONTEXT, SCHEMA_TYPE_MAP

log = setup_logging(__name__)

# Stefan Zweig as linked data author reference
STEFAN_ZWEIG = {
    "@type": "schema:Person",
    "name": "Stefan Zweig",
    "sameAs": "https://www.wikidata.org/entity/Q78491",
}


def load_location_wikidata():
    """Load only reviewed and publishable location links from Gate 2."""
    if not os.path.exists(OUTPUT_PUBLISHABLE_LINKS):
        raise FileNotFoundError(
            "Gate 2 publishable links are missing. Run reconcile_entities.py "
            "before stage 05."
        )
    with open(OUTPUT_PUBLISHABLE_LINKS, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    uri_map = {
        name: decision["uri"]
        for name, decision in document.get("locations", {}).items()
    }
    log.info("Loaded %d reviewed Wikidata location links", len(uri_map))
    return uri_map


def safe_json_parse(value):
    """Parse a JSON string, returning empty list/None on failure."""
    if not value:
        return None
    try:
        parsed = json.loads(value)
        return parsed if parsed else None
    except (json.JSONDecodeError, TypeError):
        return None


def row_to_jsonld(row, location_uris=None):
    """Convert a CSV row to a JSON-LD entry using Schema.org + DC + klawiter: blend."""
    location_uris = location_uris or {}
    page_id = row["page_id"]
    entry_type = row.get("entry_type", "other")
    namespace = int(row.get("page_namespace", 0))

    # @type: array of Schema.org + klawiter: types
    type_array = SCHEMA_TYPE_MAP.get(entry_type, ["schema:CreativeWork"])

    entry = {
        "@type": type_array,
        "@id": f"klawiter:entry/{page_id}",
        "entryType": entry_type,
        "sourcePageId": int(page_id),
        "pageNamespace": namespace,
    }

    # Title → schema:name
    title = row.get("title", "")
    if title:
        entry["name"] = title

    original_title = row.get("original_title", "")
    if original_title:
        entry["originalTitle"] = original_title

    # Text ID provenance
    text_id = row.get("text_id", "")
    if text_id:
        try:
            entry["sourceTextId"] = int(text_id)
        except (ValueError, TypeError):
            pass

    # Redirect
    if csv_bool(row.get("is_redirect")):
        entry["isRedirect"] = True
        redirect_target = row.get("redirect_target", "")
        if redirect_target:
            entry["redirectTarget"] = redirect_target
        return entry

    # Author (Stefan Zweig for primary works, omit for secondary literature)
    if entry_type not in (
        "secondary-literature",
        "historical-study",
        "symposium",
        "redirect",
        "other",
    ):
        entry["author"] = STEFAN_ZWEIG

    # Year → schema:datePublished
    year = row.get("year", "")
    if year:
        try:
            entry["datePublished"] = str(int(year))
        except (ValueError, TypeError):
            pass

    all_years = safe_json_parse(row.get("all_years", ""))
    if all_years and len(all_years) > 1:
        entry["allYears"] = all_years

    # Time period (domain-specific)
    time_period = row.get("time_period", "")
    if time_period:
        entry["timePeriod"] = time_period

    # Publisher → schema:publisher
    publisher = row.get("publisher", "")
    if publisher:
        entry["publisher"] = publisher

    # Location → schema:locationCreated
    location = row.get("location", "")
    if location:
        entry["locationCreated"] = location
        # Wikidata URI of the primary publication location (klawiter:locationSameAs)
        location_uri = location_uris.get(location)
        if location_uri:
            entry["locationSameAs"] = location_uri

    all_locations = safe_json_parse(row.get("all_locations", ""))
    if all_locations and len(all_locations) > 1:
        entry["allLocations"] = all_locations

    # Language → schema:inLanguage + klawiter:languageCode
    language = row.get("language", "")
    language_iso = row.get("language_iso", "")
    if language:
        entry["inLanguage"] = language
    if language_iso:
        entry["languageCode"] = language_iso

    # Page count → schema:numberOfPages
    page_count = row.get("page_count", "")
    if page_count:
        try:
            entry["numberOfPages"] = int(page_count)
        except (ValueError, TypeError):
            pass

    # Translator → schema:translator
    translator = row.get("translator", "")
    if translator:
        entry["translator"] = translator

    # Categories (domain-specific)
    categories = safe_json_parse(row.get("categories", ""))
    if categories:
        entry["categories"] = categories

    main_category = row.get("main_category", "")
    if main_category:
        entry["mainCategory"] = main_category

    # Cross-references
    see_also = safe_json_parse(row.get("see_also", ""))
    if see_also:
        entry["isRelatedTo"] = see_also

    reprints = safe_json_parse(row.get("reprints", ""))
    if reprints:
        entry["reprints"] = reprints

    translations = safe_json_parse(row.get("translations", ""))
    if translations:
        entry["workTranslation"] = translations

    content_items = safe_json_parse(row.get("content_items", ""))
    if content_items:
        entry["hasPart"] = content_items

    # Full bibliographic entry → dcterms:bibliographicCitation
    clean_content = row.get("clean_content", "")
    if clean_content:
        entry["bibliographicCitation"] = clean_content

    # Blob ID provenance
    blob_id = row.get("blob_id", "")
    if blob_id and blob_id != "-1":
        try:
            entry["sourceBlobId"] = int(blob_id)
        except (ValueError, TypeError):
            pass

    return entry


# Mapping from JSON-LD keys to frontend short keys (where they differ)
_FRONTEND_KEY_MAP = {
    "name": "title",
    "datePublished": "year",
    "locationCreated": "location",
    "inLanguage": "language",
    "numberOfPages": "pageCount",
    "bibliographicCitation": "fullBibliographicEntry",
    "isRelatedTo": "seeAlso",
    "workTranslation": "translations",
    "hasPart": "contentItems",
}


def make_frontend_entry(jsonld_entry):
    """Create a simplified entry for the frontend JSON.

    Maps semantic property names back to short keys the frontend expects.
    Converts datePublished (string) back to integer year for the frontend.
    """
    e = {}
    for key, val in jsonld_entry.items():
        if key.startswith("@"):
            e[key] = val
            continue
        # Map to frontend key name, or keep as-is
        frontend_key = _FRONTEND_KEY_MAP.get(key, key)
        # Convert year string back to int for frontend
        if key == "datePublished":
            try:
                val = int(val)
            except (ValueError, TypeError):
                pass
        # Skip author object (frontend doesn't use it)
        if key == "author":
            continue
        e[frontend_key] = val
    return e


def main():
    rows = load_csv(STEP_04_OUTPUT)
    log.info(f"Loaded {len(rows)} entries, converting to JSON-LD...")

    location_uris = load_location_wikidata()

    entries = []
    for row in rows:
        entry = row_to_jsonld(row, location_uris)
        entries.append(entry)

    # Write complete dataset
    os.makedirs(os.path.dirname(OUTPUT_JSONLD), exist_ok=True)
    dataset = {
        **CONTEXT,
        "@type": "schema:Dataset",
        "@id": "klawiter:klawiter-bibliography",
        "name": "Stefan Zweig Bibliography (Klawiter)",
        "description": "Complete bibliography of Stefan Zweig compiled by Dr. Randolph J. Klawiter at the University of Notre Dame",
        "creator": "Dr. Randolph J. Klawiter",
        "sourceOrganization": "University of Notre Dame",
        "totalEntries": len(entries),
        "entries": entries,
    }

    write_json(OUTPUT_JSONLD, dataset, indent=2)
    log.info(f"Complete dataset written to {OUTPUT_JSONLD}")

    # Write individual entry files
    os.makedirs(OUTPUT_ENTRIES_DIR, exist_ok=True)
    for entry in entries:
        entry_id = entry.get("@id", "").split("/")[-1]
        if entry_id:
            entry_file = {**CONTEXT, **entry}
            path = os.path.join(OUTPUT_ENTRIES_DIR, f"{entry_id}.jsonld")
            write_json(path, entry_file, indent=2)

    log.info(
        f"Individual entries written to {OUTPUT_ENTRIES_DIR}/ ({len(entries)} files)"
    )

    # Write frontend-optimized JSON
    os.makedirs(os.path.dirname(OUTPUT_FRONTEND_JSON), exist_ok=True)

    non_redirect_entries = []
    redirect_map = {}
    title_to_pid = {}

    for e in entries:
        if not e.get("isRedirect"):
            fe = make_frontend_entry(e)
            non_redirect_entries.append(fe)
            title = e.get("name", "")
            pid = e.get("sourcePageId")
            if title and pid:
                title_to_pid[title] = pid

    for e in entries:
        if e.get("isRedirect"):
            target_title = e.get("name", "")
            source_title = e.get("redirectTarget", "") or target_title
            target_pid = title_to_pid.get(target_title)
            if target_pid:
                redirect_map[target_title] = target_pid
                if source_title != target_title:
                    redirect_map[source_title] = target_pid

    # Compute _meta for frontend data verification
    ns0 = [e for e in non_redirect_entries if e.get("pageNamespace") == 0]
    ns0_count = len(ns0)

    coverage_fields = {
        "title": "title",
        "year": "year",
        "publisher": "publisher",
        "location": "location",
        "language": "language",
        "translator": "translator",
        "pageCount": "pageCount",
    }
    field_coverage = {}
    for label, key in coverage_fields.items():
        count = sum(1 for e in ns0 if e.get(key) not in (None, ""))
        field_coverage[label] = {
            "count": count,
            "pct": round(100 * count / ns0_count, 1) if ns0_count else 0,
        }

    type_counts = {}
    for e in ns0:
        t = e.get("entryType", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    years = [e["year"] for e in ns0 if e.get("year")]
    languages = set(e.get("language") for e in ns0 if e.get("language"))
    locations = set(e.get("location") for e in ns0 if e.get("location"))

    _meta = {
        "ns0Count": ns0_count,
        "totalCount": len(non_redirect_entries),
        "redirectCount": len(redirect_map),
        "fieldCoverage": field_coverage,
        "entryTypes": type_counts,
        "yearRange": {
            "min": min(years) if years else None,
            "max": max(years) if years else None,
        },
        "languageCount": len(languages),
        "locationCount": len(locations),
    }

    frontend_data = {
        "name": "Stefan Zweig Bibliography (Klawiter)",
        "compiler": "Dr. Randolph J. Klawiter",
        "institution": "University of Notre Dame",
        "totalEntries": len(non_redirect_entries),
        "_meta": _meta,
        "entries": non_redirect_entries,
        "redirects": redirect_map,
    }

    write_json(OUTPUT_FRONTEND_JSON, frontend_data, separators=(",", ":"))

    size_mb = os.path.getsize(OUTPUT_FRONTEND_JSON) / 1024 / 1024
    log.info(f"Frontend JSON written to {OUTPUT_FRONTEND_JSON} ({size_mb:.1f} MB)")
    log.info(f"  Non-redirect entries: {len(non_redirect_entries)}")
    log.info(f"  Redirect map entries: {len(redirect_map)}")

    # Stats
    types = {}
    redirects = 0
    for e in entries:
        t = e.get("entryType", "unknown")
        types[t] = types.get(t, 0) + 1
        if e.get("isRedirect"):
            redirects += 1

    log.info(
        f"JSON-LD conversion complete: {len(entries)} entries, {redirects} redirects"
    )


if __name__ == "__main__":
    main()
