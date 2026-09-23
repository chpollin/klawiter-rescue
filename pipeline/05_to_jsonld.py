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
import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (
    FRONTEND_PUBLICATIONS_PATH_TEMPLATE,
    OUTPUT_EDITIONS_DIR,
    OUTPUT_ENTRIES_DIR,
    OUTPUT_FRONTEND_JSON,
    OUTPUT_FRONTEND_PUBLICATIONS_DIR,
    OUTPUT_JSONLD,
    OUTPUT_PUBLISHABLE_LINKS,
    OUTPUT_RECONCILIATION_DECISIONS,
    OUTPUT_RECONCILIATION_DIR,
    PROJECT_ROOT,
    SOURCE_REVISION_DECISIONS,
    STEP_01_PAGELINKS,
    STEP_04_OUTPUT,
    csv_bool,
    load_csv,
    setup_logging,
    write_json,
)
from lib.publications import (
    attach_edition_state,
    build_page_publications,
    load_attested_places,
    review_flag_codes,
)
from lib.vocabulary import CONTEXT, SCHEMA_TYPE_MAP, to_rdf_entry

log = setup_logging(__name__)

DATA_LICENSE = "https://creativecommons.org/licenses/by/4.0/"
EDITION_URL = "https://chpollin.github.io/klawiter-rescue/"
# The release covers the current wiki pages; titles recorded as deleted are
# outside it (knowledge/production-readiness.md#release-scope).
DATASET_DESCRIPTION = (
    "Bibliography of Stefan Zweig compiled by Dr. Randolph J. Klawiter at the "
    "University of Notre Dame. This digital edition covers the current pages "
    "of the compiler's wiki; titles the wiki records as deleted are outside "
    "its scope."
)
EDITOR = {
    "@id": "klawiter:person/Christopher%20Pollin",
    "@type": "schema:Person",
    "name": "Christopher Pollin",
    "description": "Responsible editor of the digital edition",
    "affiliation": {
        "@id": "klawiter:organization/Digital%20Humanities%20Craft",
        "@type": "schema:Organization",
        "name": "Digital Humanities Craft",
    },
}


def release_version():
    """The release version, read from its single source in pyproject.toml."""
    with open(os.path.join(PROJECT_ROOT, "pyproject.toml"), "rb") as handle:
        return tomllib.load(handle)["project"]["version"]


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


def load_withheld_redirects():
    """Page ids whose Redirect-fixer redirect is not resolved as a relation.

    Where the revision the fixer overwrote is not delivered, the dump cannot
    show whether the page held content; the decision withholds the redirect
    and Gate 2 records an open claim instead (source-revision-decisions.json).
    """
    with open(SOURCE_REVISION_DECISIONS, encoding="utf-8") as handle:
        document = json.load(handle)
    return frozenset(
        decision["pageId"]
        for decision in document["decisions"]
        if decision["action"] == "withhold-redirect-relation"
    )


def load_source_revision_restorations():
    """Page id -> the record a reader needs to see why a restored page is
    published from an earlier revision than page_latest."""
    with open(SOURCE_REVISION_DECISIONS, encoding="utf-8") as handle:
        document = json.load(handle)
    restorations = {}
    for decision in document["decisions"]:
        if decision["action"] != "restore-human-revision":
            continue
        human = decision["humanRevision"]
        restorations[decision["pageId"]] = {
            "decisionId": decision["decisionId"],
            "action": decision["action"],
            "reason": decision["reason"],
            "humanRevision": {
                key: human[key]
                for key in ("revisionId", "timestamp", "actor", "textId")
            },
            "fixerRevisions": [
                {key: rev[key] for key in ("revisionId", "timestamp", "comment")}
                for rev in decision["fixerRevisions"]
            ],
            "decidedBy": document["provenance"],
        }
    return restorations


def _collapse(title):
    """MediaWiki collapses whitespace runs in a title before the lookup."""
    return " ".join(title.split())


def build_reference_targets(rows, withheld=None):
    """Map every resolvable reference name (parsed title, wiki page title,
    redirect name) to the page id of the entry it finally lands on.

    Every name also enters in its whitespace-collapsed form, the form a link
    target takes, without displacing an exact name. A withheld redirect
    neither resolves nor carries a chain; it defaults to the recorded
    decisions so that every caller applies them.
    """
    if withheld is None:
        withheld = load_withheld_redirects()
    direct = {}
    for row in rows:
        if csv_bool(row.get("is_redirect")):
            continue
        pid = int(row["page_id"])
        for key in ("title", "page_title"):
            value = row.get(key, "")
            if value:
                direct.setdefault(value, pid)
    for value, pid in list(direct.items()):
        direct.setdefault(_collapse(value), pid)
    targets = dict(direct)
    redirect_rows = [
        row
        for row in rows
        if csv_bool(row.get("is_redirect")) and int(row["page_id"]) not in withheld
    ]
    redirects = {
        row["page_title"]: row.get("redirect_target") or row.get("title", "")
        for row in redirect_rows
        if row.get("page_title")
    }
    for row in redirect_rows:
        target = row.get("redirect_target", "") or row.get("title", "")
        seen = set()
        while target not in direct and target in redirects and target not in seen:
            seen.add(target)
            target = redirects[target]
        pid = direct.get(target) or direct.get(_collapse(target))
        if pid:
            for key in ("page_title", "title"):
                value = row.get(key, "")
                if value:
                    targets.setdefault(value, pid)
                    targets.setdefault(_collapse(value), pid)
    return targets


def _load_edition_graph():
    path = os.path.join(OUTPUT_EDITIONS_DIR, "work-editions.jsonld")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Work/Edition graph is missing: {path}. Run Gate 1 before stage 05."
        )
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_work_pages():
    """Page ids that the canonical Work/Edition graph decomposes."""
    works = _load_edition_graph()["works"]
    # A work created by a claim decision stands on no source page of its own.
    return {
        work["klawiter:sourcePageId"]
        for work in works
        if "klawiter:sourcePageId" in work
    }


def load_edition_states():
    """Review status of every edition node of the reviewed Gate-1 graph."""
    return {
        edition["@id"]: edition["klawiter:reviewStatus"]
        for edition in _load_edition_graph()["editions"]
    }


# Flat fields whose value a Gate-2 claim can hold open, and the scope the
# claim names for them.
_CLAIM_FIELDS = {
    "location": "locationCreated",
    "person": "translator",
    "publisher": "publisher",
}


def load_contested_values():
    """Open Gate-2 claims by the flat field and value they hold open.

    The flat graph otherwise cannot tell a contested value from an unreviewed
    one: neither carries a sameAs link. A resolved claim is no longer open.
    """
    path = os.path.join(OUTPUT_RECONCILIATION_DIR, "contested-claims.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Gate 2 contested claims are missing: {path}. Run Gate 2 before stage 05."
        )
    with open(path, encoding="utf-8") as handle:
        claims = json.load(handle)["@graph"]
    contested = {}
    for claim in claims:
        field = _CLAIM_FIELDS.get(claim.get("klawiter:identityScope"))
        if field is None or claim.get("klawiter:claimStatus") != "contested":
            continue
        name = claim["klawiter:claimSubject"]["schema:name"]
        contested.setdefault((field, name), []).append(claim["@id"])
    log.info("Contested flat values: %d", len(contested))
    return contested


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

# Review projection: the flat entry fields Gate 2 decides on, and the agent
# kind that decides each of them.
_REVIEW_FIELDS = ("location", "translator", "publisher")
_AGENT_DECISION_FIELDS = {"person": "translator", "publisher": "publisher"}
# What a decision action says about the entry as a whole. A rejection
# refuses a candidate link and verifies no value, so it yields the weakest
# status, reviewed: a decision exists, nothing was verified.
_REVIEW_STATUS_BY_ACTION = {
    "confirm": "agent_verified",
    "correct": "agent_verified",
    "reject": "reviewed",
    "unresolved": "contested",
}
# approved is reserved for apply_patches.py, where a human editor decided.
_REVIEW_STATUS_RANK = {
    "reviewed": 0,
    "contested": 1,
    "agent_verified": 2,
    "approved": 3,
}


def load_review_index():
    """Index the Gate-2 decisions by the flat field value they adjudicate.

    Locations resolve through the location value of an entry, translators and
    publishers through their agent name; both are the exact strings the
    entry carries, so no fuzzy matching enters the projection.
    """
    with open(OUTPUT_RECONCILIATION_DECISIONS, encoding="utf-8") as handle:
        document = json.load(handle)
    index = {}
    for decision in document.get("locationDecisions", []):
        index[("location", decision["subject"])] = decision
    for decision in document.get("agentDecisions", []):
        field = _AGENT_DECISION_FIELDS.get(decision["entityType"])
        if field:
            index[(field, decision["subject"])] = decision
    log.info("Review index: %d decided field values", len(index))
    return index


def build_review(frontend_entry, review_index):
    """Project the reviewed state of an entry's own field values.

    Returns None where no decision covers any value of the entry, so an
    unreviewed entry carries no key at all. The status reports the strongest
    statement any of its fields carries; the fields map keeps the per-field
    detail, and scope lists the fields the status covers, because a decided
    place says nothing about year, translator or any other field.
    """
    fields = {}
    strongest = None
    for field in _REVIEW_FIELDS:
        value = frontend_entry.get(field)
        decision = review_index.get((field, value)) if value else None
        if not decision:
            continue
        action = decision["action"]
        fields[field] = action
        status = _REVIEW_STATUS_BY_ACTION[action]
        if strongest is None or (
            _REVIEW_STATUS_RANK[status] > _REVIEW_STATUS_RANK[strongest[0]]
        ):
            strongest = (status, decision)
    if not fields:
        return None
    status, decision = strongest
    review = {"status": status, "reviewed_by": decision["decidedBy"]}
    if decision.get("decidedAt"):
        review["reviewed_at"] = decision["decidedAt"]
    review["fields"] = fields
    review["scope"] = list(fields)
    return review


def publication_layer(row, attested_places, edition_states=None):
    """Publication- and contribution-scoped facts of one source page.

    The flat fields stay as they are for search, facets and exports; this layer
    says which publication each fact belongs to. It is projected here rather
    than into the canonical flat graph, because for multi-edition pages the
    Gate-1 Work/Edition graph is the canonical structure and this projection
    must not compete with it; each publication names its edition node and that
    node's review status. See knowledge/data.md.
    """
    if row.get("page_namespace") != "0":
        return {}
    layer = build_page_publications(
        page_id=int(row["page_id"]),
        text=row.get("raw_content", ""),
        page_title=row.get("page_title", ""),
        categories=safe_json_parse(row.get("categories", "")) or [],
        attested_places=attested_places,
        delivered_text=row.get("clean_content", ""),
    )
    attach_edition_state(layer, edition_states or {})
    return layer


# Page-level keys the main dataset keeps, so search and facets need no side
# file; the arrays move to docs/data/publications/<sourcePageId>.json.
_PUBLICATION_SUMMARY_KEYS = (
    "pageKind",
    "publicationCount",
    "publicationYears",
    "publicationPlaces",
    "publicationLanguages",
)
_PUBLICATION_SIDE_KEYS = ("publications", "nameVariants")


def write_publication_files(layers):
    """Write one publication file per source page and drop stale files.

    Rewriting the whole directory keeps the output a pure function of the
    source, so a page that loses its layer does not leave a file behind.
    """
    os.makedirs(OUTPUT_FRONTEND_PUBLICATIONS_DIR, exist_ok=True)
    written = set()
    for page_id, layer in sorted(layers.items()):
        document = {"sourcePageId": page_id}
        for key in _PUBLICATION_SIDE_KEYS:
            document[key] = layer.get(key, [])
        path = os.path.join(OUTPUT_FRONTEND_PUBLICATIONS_DIR, f"{page_id}.json")
        write_json(path, document, separators=(",", ":"))
        written.add(f"{page_id}.json")
    stale = [
        name
        for name in os.listdir(OUTPUT_FRONTEND_PUBLICATIONS_DIR)
        if name.endswith(".json") and name not in written
    ]
    for name in stale:
        os.remove(os.path.join(OUTPUT_FRONTEND_PUBLICATIONS_DIR, name))
    log.info(
        "Publication files written: %d (%d stale removed)", len(written), len(stale)
    )


def make_frontend_entry(jsonld_entry, review_index=None, publications=None):
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
    review = build_review(e, review_index or {})
    if review:
        e["review"] = review
    if publications:
        e.update({key: publications[key] for key in _PUBLICATION_SUMMARY_KEYS})
        # The card can say that a page holds open cases without fetching
        # its side file.
        flag_codes = review_flag_codes(publications)
        if flag_codes:
            e["publicationReviewFlags"] = flag_codes
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
    contested = load_contested_values()
    reference_targets = build_reference_targets(rows)
    work_pages = load_work_pages()
    edition_states = load_edition_states()
    version = release_version()
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
        "description": DATASET_DESCRIPTION,
        "creator": {
            "@id": "klawiter:person/Randolph%20J.%20Klawiter",
            "@type": "schema:Person",
            "name": "Dr. Randolph J. Klawiter",
        },
        "editor": EDITOR,
        "sourceOrganization": {
            "@id": "klawiter:organization/University%20of%20Notre%20Dame",
            "@type": "schema:Organization",
            "name": "University of Notre Dame",
        },
        "license": DATA_LICENSE,
        "version": version,
        "url": EDITION_URL,
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
        "entries": [to_rdf_entry(entry, agent_links, contested) for entry in entries],
    }

    write_json(OUTPUT_JSONLD, dataset, indent=2)
    log.info(f"Complete dataset written to {OUTPUT_JSONLD}")

    # Write individual entry files
    os.makedirs(OUTPUT_ENTRIES_DIR, exist_ok=True)
    for entry in entries:
        entry_id = entry.get("@id", "").split("/")[-1]
        if entry_id:
            entry_file = {**CONTEXT, **to_rdf_entry(entry, agent_links, contested)}
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
    review_index = load_review_index()
    restorations = load_source_revision_restorations()
    attested_places = load_attested_places()
    log.info("Attested place stock for imprint splitting: %d", len(attested_places))

    publication_layers = {}
    for row, e in zip(rows, entries, strict=True):
        if not e.get("isRedirect"):
            layer = publication_layer(row, attested_places, edition_states)
            if layer:
                publication_layers[int(row["page_id"])] = layer
            fe = make_frontend_entry(e, review_index, layer)
            restoration = restorations.get(fe.get("sourcePageId"))
            if restoration:
                fe["sourceRevision"] = restoration
            non_redirect_entries.append(fe)
            title = e.get("name", "")
            pid = e.get("sourcePageId")
            if title and pid:
                title_to_pid[title] = pid

    for row, e in zip(rows, entries, strict=True):
        if e.get("isRedirect"):
            for key in ("page_title", "title"):
                alias = row.get(key, "")
                target_pid = reference_targets.get(alias)
                if target_pid and alias not in title_to_pid:
                    redirect_map[alias] = target_pid

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

    layers = list(publication_layers.values())
    publication_coverage = {
        "pages": len(layers),
        "publications": sum(len(layer["publications"]) for layer in layers),
        "contributions": sum(
            len(p.get("contributions", []))
            for layer in layers
            for p in layer["publications"]
        ),
        "reviewFlags": sum(
            len(p.get("reviewFlags", []))
            for layer in layers
            for p in layer["publications"]
        ),
        "pathTemplate": FRONTEND_PUBLICATIONS_PATH_TEMPLATE,
    }

    _meta = {
        # Declared shape of this file; tests/test_frontend_contract.py holds
        # the matching declaration. 1.1 added the per-entry review projection,
        # 1.2 the publication- and contribution-scoped layer, 1.3 its move
        # into per-page side files, 1.4 the edition node and review status
        # per publication, the page's publication flag codes, the imprint
        # pairs and series gloss, the release license and version, and the
        # review scope and reviewed status.
        "frontendSchemaVersion": "1.5",
        "license": DATA_LICENSE,
        "version": version,
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
        "publicationCoverage": publication_coverage,
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
    write_publication_files(publication_layers)

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
