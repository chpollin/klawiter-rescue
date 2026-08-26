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
    OUTPUT_EDITIONS_DIR,
    OUTPUT_ENTRIES_DIR,
    OUTPUT_FRONTEND_JSON,
    OUTPUT_JSONLD,
    OUTPUT_PUBLISHABLE_LINKS,
    STEP_01_PAGELINKS,
    STEP_04_OUTPUT,
    csv_bool,
    load_csv,
    setup_logging,
    write_json,
)
from lib.vocabulary import CONTEXT, SCHEMA_TYPE_MAP, to_rdf_entry

log = setup_logging(__name__)

# Stefan Zweig as one referenceable entity: the @id makes every author
# reference resolve to a single node (canonical Wikidata RDF IRI, http form)
# instead of thousands of blank nodes.
STEFAN_ZWEIG = {
    "@id": "http://www.wikidata.org/entity/Q78491",
    "@type": "schema:Person",
    "name": "Stefan Zweig",
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


def load_agent_wikidata():
    """Load only reviewed and publishable agent links from Gate 2."""
    with open(OUTPUT_PUBLISHABLE_LINKS, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    links = {
        (link["kind"], link["name"]): link["uri"]
        for link in document.get("agents", {}).values()
    }
    log.info("Loaded %d reviewed Wikidata agent links", len(links))
    return links


def safe_json_parse(value):
    """Parse a JSON string, returning empty list/None on failure."""
    if not value:
        return None
    try:
        parsed = json.loads(value)
        return parsed if parsed else None
    except (json.JSONDecodeError, TypeError):
        return None


def build_reference_targets(rows):
    """Map every resolvable reference name (parsed title, wiki page title,
    redirect name) to the page id of the entry it finally lands on."""
    direct = {}
    for row in rows:
        if csv_bool(row.get("is_redirect")):
            continue
        pid = int(row["page_id"])
        for key in ("title", "page_title"):
            value = row.get(key, "")
            if value:
                direct.setdefault(value, pid)
    targets = dict(direct)
    for row in rows:
        if not csv_bool(row.get("is_redirect")):
            continue
        target = row.get("redirect_target", "") or row.get("title", "")
        pid = direct.get(target)
        if pid:
            for key in ("page_title", "title"):
                value = row.get(key, "")
                if value:
                    targets.setdefault(value, pid)
    return targets


def load_work_pages():
    """Page ids that the canonical Work/Edition graph decomposes."""
    path = os.path.join(OUTPUT_EDITIONS_DIR, "work-editions.jsonld")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Work/Edition graph is missing: {path}. Run Gate 1 before stage 05."
        )
    with open(path, encoding="utf-8") as handle:
        works = json.load(handle)["works"]
    return {int(work["@id"].rsplit("/", 1)[1]) for work in works}


def row_to_jsonld(row, location_uris=None, reference_targets=None, work_pages=None):
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

    # Language: schema:inLanguage carries the code (Schema.org expects a
    # BCP-47 code); the human-readable name lives in klawiter:languageName.
    language = row.get("language", "")
    language_iso = row.get("language_iso", "")
    if language_iso:
        entry["inLanguage"] = language_iso
    if language:
        entry["languageName"] = language

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

    # Cross-references: resolved See-references become dcterms:relation
    # with entry IRIs; genuinely dead references (red links in the source
    # wiki) stay preserved as plain text.
    see_also = safe_json_parse(row.get("see_also", ""))
    if see_also:
        resolved = []
        unresolved = []
        for ref in see_also:
            target_pid = (reference_targets or {}).get(ref)
            if target_pid and target_pid != int(page_id):
                resolved.append({"@id": f"klawiter:entry/{target_pid}", "name": ref})
            else:
                unresolved.append(ref)
        if resolved:
            entry["relation"] = resolved
        if unresolved:
            entry["seeAlsoText"] = unresolved

    # Coupling to the canonical Work/Edition graph
    if work_pages and int(page_id) in work_pages:
        entry["decomposedAsWork"] = f"klawiter:work/{page_id}"

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
    "inLanguage": "languageCode",
    "languageName": "language",
    "numberOfPages": "pageCount",
    "bibliographicCitation": "fullBibliographicEntry",
    "workTranslation": "translations",
    "hasPart": "contentItems",
}

# RDF-only structure the UI does not render
_FRONTEND_SKIPPED_KEYS = {"author", "relation", "seeAlsoText", "decomposedAsWork"}


def make_frontend_entry(jsonld_entry):
    """Create a simplified entry for the frontend JSON.

    Maps semantic property names back to short keys the frontend expects.
    Converts datePublished (string) back to integer year for the frontend.
    Resolved and unresolved cross-references merge back into one flat
    seeAlso list of display titles.
    """
    e = {}
    see_also = [item["name"] for item in jsonld_entry.get("relation", [])]
    see_also += jsonld_entry.get("seeAlsoText", [])
    if see_also:
        e["seeAlso"] = see_also
    for key, val in jsonld_entry.items():
        if key.startswith("@"):
            e[key] = val
            continue
        if key in _FRONTEND_SKIPPED_KEYS:
            continue
        # Map to frontend key name, or keep as-is
        frontend_key = _FRONTEND_KEY_MAP.get(key, key)
        # Convert year string back to int for frontend
        if key == "datePublished":
            try:
                val = int(val)
            except (ValueError, TypeError):
                pass
        e[frontend_key] = val
    return e


def _normalize_title(title):
    """MediaWiki title normalization: underscores as spaces, collapsed
    whitespace, first letter uppercased."""
    flat = " ".join(title.replace("_", " ").split())
    return flat[:1].upper() + flat[1:] if flat else flat


def load_pagelink_resolver():
    """Build page_id -> {normalized title -> canonical target title} from
    MediaWiki's own resolved link graph (main namespace only)."""
    if not os.path.exists(STEP_01_PAGELINKS):
        raise FileNotFoundError(
            f"Page-link table is missing: {STEP_01_PAGELINKS}. "
            "Run pipeline stage 01 first."
        )
    resolver = {}
    for row in load_csv(STEP_01_PAGELINKS):
        if row["pl_namespace"] != "0":
            continue
        title = row["pl_title"]
        resolver.setdefault(int(row["pl_from"]), {})[_normalize_title(title)] = title
    return resolver


def repair_see_references(rows):
    """Repair See-references against the wiki's resolved link graph.

    The regex extraction reproduces the reference text as written; where
    that text differs from the canonical page title (case, whitespace,
    dropped suffixes), the link stayed broken although MediaWiki had
    resolved it at save time. zweig_pagelinks holds those resolutions, so
    a broken reference is replaced by the canonical target title of the
    same source page when that target is a live page. Genuinely dead
    references (red links) stay untouched.
    """
    known = set()
    for row in rows:
        for key in ("page_title", "title"):
            value = row.get(key, "")
            if value:
                known.add(value)
    resolver = load_pagelink_resolver()
    broken_before = repaired = broken_after = 0
    for row in rows:
        see_also = safe_json_parse(row.get("see_also", ""))
        if not see_also:
            continue
        changed = False
        result = []
        for ref in see_also:
            if ref in known:
                result.append(ref)
                continue
            broken_before += 1
            canonical = resolver.get(int(row["page_id"]), {}).get(_normalize_title(ref))
            if canonical and canonical in known:
                result.append(canonical)
                repaired += 1
                changed = True
            else:
                result.append(ref)
                broken_after += 1
        if changed:
            row["see_also"] = json.dumps(result, ensure_ascii=False)
    log.info(
        f"See-reference repair: {broken_before} unresolved, "
        f"{repaired} repaired via pagelinks, {broken_after} remain (red links)"
    )


def main():
    rows = load_csv(STEP_04_OUTPUT)
    log.info(f"Loaded {len(rows)} entries, converting to JSON-LD...")

    repair_see_references(rows)
    location_uris = load_location_wikidata()
    agent_links = load_agent_wikidata()
    reference_targets = build_reference_targets(rows)
    work_pages = load_work_pages()
    log.info(f"Work/Edition coupling targets: {len(work_pages)} pages")

    entries = []
    for row in rows:
        entry = row_to_jsonld(row, location_uris, reference_targets, work_pages)
        entries.append(entry)

    # Write complete dataset. The published RDF shape (language-tagged
    # titles, agent and place resources) exists only at this write
    # boundary; the in-memory entries stay flat for every downstream step.
    os.makedirs(os.path.dirname(OUTPUT_JSONLD), exist_ok=True)
    dataset = {
        **CONTEXT,
        "@type": "schema:Dataset",
        "@id": "klawiter:klawiter-bibliography",
        "name": "Stefan Zweig Bibliography (Klawiter)",
        "description": "Complete bibliography of Stefan Zweig compiled by Dr. Randolph J. Klawiter at the University of Notre Dame",
        "creator": {
            "@id": "klawiter:person/Randolph%20J.%20Klawiter",
            "@type": "schema:Person",
            "name": "Dr. Randolph J. Klawiter",
        },
        "sourceOrganization": {
            "@id": "klawiter:organization/University%20of%20Notre%20Dame",
            "@type": "schema:Organization",
            "name": "University of Notre Dame",
        },
        "license": "https://creativecommons.org/licenses/by/4.0/",
        # The Work/Edition graph is the canonical dataset for pages with
        # multiple editions; this flat dataset is its derived convenience
        # projection (operator decision 2026-08-26).
        "klawiter:canonicalDataset": {"@id": "klawiter:dataset/work-editions"},
        "klawiter:authorityNote": (
            "For pages with multiple editions the Work/Edition graph "
            "(data/output/editions/work-editions.jsonld) is the canonical "
            "dataset; this flat dataset is a derived convenience projection."
        ),
        "totalEntries": len(entries),
        "entries": [to_rdf_entry(entry, agent_links) for entry in entries],
    }

    write_json(OUTPUT_JSONLD, dataset, indent=2)
    log.info(f"Complete dataset written to {OUTPUT_JSONLD}")

    # Write individual entry files
    os.makedirs(OUTPUT_ENTRIES_DIR, exist_ok=True)
    for entry in entries:
        entry_id = entry.get("@id", "").split("/")[-1]
        if entry_id:
            entry_file = {**CONTEXT, **to_rdf_entry(entry, agent_links)}
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

    # Wiki page titles are the keys the source's See-references and its
    # resolved link graph use. Where a page title differs from the parsed
    # display title, reference resolution would break although the page
    # exists; the page title therefore joins the redirect map as an alias
    # of its own entry. Real redirects keep precedence.
    alias_count = 0
    for row, e in zip(rows, entries, strict=True):
        if e.get("isRedirect"):
            continue
        pid = e.get("sourcePageId")
        page_title = row.get("page_title", "")
        if pid and page_title and page_title != e.get("name", ""):
            if page_title not in redirect_map and page_title not in title_to_pid:
                redirect_map[page_title] = pid
                alias_count += 1
    log.info(f"Page-title aliases added to the redirect map: {alias_count}")

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
