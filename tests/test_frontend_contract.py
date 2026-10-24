"""Frontend data contract: the projection boundary between RDF and UI.

The modeling layer may enrich the RDF datasets freely; make_frontend_entry in
pipeline/05_to_jsonld.py must keep projecting docs/data/klawiter.json to
exactly this declared shape (resources flattened to display values). A
deliberate contract change updates this declaration in the same change that
adapts the frontend, never as a side effect of modeling work.
"""

from __future__ import annotations

import importlib
import json
from functools import lru_cache
from pathlib import Path

# Bumped whenever the declared entry or _meta shape changes. 1.1 added the
# review projection (dataset-level review state per entry), 1.2 the
# publication- and contribution-scoped layer, 1.3 its move into per-page side
# files so the main dataset stays loadable without them, 1.4 the Gate-1 edition
# node and review status per publication, the page's publication flag codes,
# the co-imprint pairs and series gloss, the release license and version, and
# the review scope and reviewed status that main added while 1.3 still stood,
# 1.5 the source revision a restored page is published from, 1.6 the
# "uncertain" mark of a credit the source qualifies with "(?)", 1.7 the wiki
# page kind with its rule and evidence, and the print addresses the page's text
# cites, with their counts in _meta, 1.8 the producers a value's provenance
# chain names, the edition review and the LLM enrichment run, 1.9 the producer
# class, per-field state and proposal basis of a review decision (an LLM
# agent's decision is proposed, never confirmed), the agent review disposition
# and producer of a publication's edition, and the structured translation
# statements of a translations section.
FRONTEND_SCHEMA_VERSION = "1.9"

TOP_LEVEL_KEYS = {
    "_meta",
    "compiler",
    "entries",
    "institution",
    "name",
    "redirects",
    "totalEntries",
}

META_KEYS = {
    "editionReview",
    "entryTypes",
    "fieldCoverage",
    "frontendSchemaVersion",
    "languageCount",
    "license",
    "llmEnrichment",
    "locationCount",
    "ns0Count",
    "publicationCoverage",
    "redirectCount",
    "printAddressCitations",
    "totalCount",
    "translationStatements",
    "version",
    "wikiPageKinds",
    "yearRange",
}

# Entry key -> (required, allowed value types). Optional keys are omitted
# from an entry entirely; a present key must carry a declared type.
ENTRY_CONTRACT: dict[str, tuple[bool, tuple[type, ...]]] = {
    "@id": (True, (str,)),
    "@type": (True, (list,)),
    "_provenance": (True, (dict,)),
    "entryType": (True, (str,)),
    "pageNamespace": (True, (int,)),
    "sourcePageId": (True, (int,)),
    "sourceTextId": (True, (int,)),
    "title": (True, (str,)),
    "allLocations": (False, (list,)),
    "allYears": (False, (list,)),
    "categories": (False, (list,)),
    "contentItems": (False, (list,)),
    "edit_history": (False, (list,)),
    "fullBibliographicEntry": (False, (str,)),
    "language": (False, (str,)),
    "languageCode": (False, (str,)),
    "location": (False, (str,)),
    "locationSameAs": (False, (str,)),
    "mainCategory": (False, (str,)),
    "originalTitle": (False, (str,)),
    "pageCount": (False, (int,)),
    "pageKind": (False, (str,)),
    "printAddressCitations": (False, (list,)),
    "publicationCount": (False, (int,)),
    "publicationLanguages": (False, (list,)),
    "publicationPlaces": (False, (list,)),
    "publicationReviewFlags": (False, (list,)),
    "publicationYears": (False, (list,)),
    "reviewFlags": (False, (list,)),
    "publisher": (False, (str,)),
    "reprints": (False, (list,)),
    "review": (False, (dict,)),
    "seeAlso": (False, (list,)),
    "sourceBlobId": (False, (int,)),
    "sourceRevision": (False, (dict,)),
    "timePeriod": (False, (str,)),
    "translationStatements": (False, (list,)),
    "translations": (False, (list,)),
    "translator": (False, (str,)),
    "wikiPageKind": (False, (str,)),
    "wikiPageKindEvidence": (False, (list,)),
    "wikiPageKindRule": (False, (str,)),
    "year": (False, (int,)),
}

REQUIRED_KEYS = {key for key, (required, _) in ENTRY_CONTRACT.items() if required}


def test_top_level_shape(frontend_data) -> None:
    assert set(frontend_data.keys()) == TOP_LEVEL_KEYS


def test_meta_shape(frontend_data) -> None:
    assert set(frontend_data["_meta"].keys()) == META_KEYS


def test_every_entry_matches_the_declared_contract(all_entries) -> None:
    for entry in all_entries:
        keys = set(entry.keys())
        undeclared = keys - ENTRY_CONTRACT.keys()
        assert not undeclared, (
            f"entry {entry.get('@id')} carries undeclared keys {sorted(undeclared)}; "
            "extend the contract deliberately, together with the frontend"
        )
        missing = REQUIRED_KEYS - keys
        assert not missing, (
            f"entry {entry.get('@id')} misses required {sorted(missing)}"
        )
        for key, value in entry.items():
            allowed = ENTRY_CONTRACT[key][1]
            assert isinstance(value, allowed), (
                f"entry {entry.get('@id')} key {key} has type {type(value).__name__}, "
                f"contract allows {[t.__name__ for t in allowed]}"
            )


# Review projection: which review vocabulary a projected entry may carry.
REVIEW_KEYS = {
    "status",
    "reviewed_by",
    "reviewed_at",
    "producer",
    "basis",
    "fields",
    "fieldStates",
    "scope",
}
REVIEW_REQUIRED_KEYS = {"status", "reviewed_by", "producer"}
REVIEW_STATUSES = {"approved", "confirmed", "proposed", "contested", "reviewed"}
REVIEW_PRODUCERS = {"llm-agent", "person", "rule"}
DECISION_STATES = {"proposed", "confirmed", "contested"}
REVIEW_FIELDS = {"location", "translator", "publisher"}
REVIEW_ACTIONS = {"confirm", "correct", "reject", "unresolved"}


def test_meta_declares_the_contract_version(frontend_data) -> None:
    assert frontend_data["_meta"]["frontendSchemaVersion"] == FRONTEND_SCHEMA_VERSION


def test_review_projection_matches_the_declared_vocabulary(all_entries) -> None:
    reviewed = [entry for entry in all_entries if "review" in entry]
    assert reviewed, (
        "no entry carries a review projection although Gate 2 holds "
        "evidence-bearing decisions on entry field values"
    )
    for entry in reviewed:
        review = entry["review"]
        assert set(review) <= REVIEW_KEYS
        assert REVIEW_REQUIRED_KEYS <= set(review)
        assert review["status"] in REVIEW_STATUSES
        assert isinstance(review["reviewed_by"], str) and review["reviewed_by"]
        fields = review.get("fields", {})
        assert set(fields) <= REVIEW_FIELDS
        assert set(fields.values()) <= REVIEW_ACTIONS
        if fields:
            assert review["scope"] == list(fields)
            assert set(review["fieldStates"]) == set(fields)
            assert set(review["fieldStates"].values()) <= DECISION_STATES
        assert review["producer"] in REVIEW_PRODUCERS
        # Only a person or an exact rule confirms (operator principle).
        if review["producer"] == "llm-agent":
            assert review["status"] in {"proposed", "contested"}
            assert review["basis"].startswith("proposed by LLM agents")
            assert "confirmed" not in review.get("fieldStates", {}).values()
        for field in fields:
            assert entry.get(field), (
                f"entry {entry['@id']} reviews {field} without carrying a value"
            )


def test_review_projection_is_derived_from_gate2_decisions() -> None:
    """The projection reports a decision that exists, never a bare status."""
    stage_05 = importlib.import_module("05_to_jsonld")
    index = stage_05.load_review_index()
    assert index, "Gate 2 decisions did not reach the review index"
    entry = {"location": "Amstelveen", "translator": "not a reviewed name"}
    review = stage_05.build_review(entry, index)
    assert review["fields"] == {"location": "confirm"}
    assert review["fieldStates"] == {"location": "proposed"}
    assert review["scope"] == ["location"]
    # The independent verification agent confirmed Amstelveen; an LLM agent's
    # confirm is a proposal.
    assert review["status"] == "proposed"
    assert review["producer"] == "llm-agent"
    assert review["basis"] == (
        "proposed by LLM agents, source occurrence checked, no person"
    )
    # A test fixture confirms nothing (operator decision of 2026-10-23).
    assert stage_05.build_review({"location": "Amsterdam"}, index) is None
    assert review["reviewed_by"] == index[("location", "Amstelveen")]["decidedBy"]
    assert stage_05.build_review({"location": "not a reviewed place"}, index) is None


def test_unresolved_decision_projects_as_contested() -> None:
    stage_05 = importlib.import_module("05_to_jsonld")
    index = {
        ("location", "Tyresö"): {
            "action": "unresolved",
            "decidedBy": "independent-verification-agent",
            "decidedAt": "2026-08-21T20:00:00Z",
            "decisionProducer": "llm-agent",
            "decisionState": "contested",
            "sourceOccurrences": 1,
        }
    }
    review = stage_05.build_review({"location": "Tyresö"}, index)
    assert review == {
        "status": "contested",
        "reviewed_by": "independent-verification-agent",
        "producer": "llm-agent",
        "basis": "proposed by LLM agents, source occurrence checked, no person",
        "reviewed_at": "2026-08-21T20:00:00Z",
        "fields": {"location": "unresolved"},
        "fieldStates": {"location": "contested"},
        "scope": ["location"],
    }


def test_rejection_verifies_nothing() -> None:
    """A person's rejected candidate link lends the entry no verified status;
    a person's confirmed place on the same entry states its own field scope,
    and an LLM agent's confirm beside it stays a proposal."""
    stage_05 = importlib.import_module("05_to_jsonld")
    person = {"decidedBy": "Editor (SZD)", "decisionProducer": "person"}
    reject = {"action": "reject", "decisionState": "confirmed", **person}
    confirm = {"action": "confirm", "decisionState": "confirmed", **person}
    agent_confirm = {
        "action": "confirm",
        "decidedBy": "independent-verification-agent",
        "decisionProducer": "llm-agent",
        "decisionState": "proposed",
        "sourceOccurrences": 0,
    }
    only_reject = stage_05.build_review(
        {"location": "Sofija, Varna"}, {("location", "Sofija, Varna"): reject}
    )
    assert only_reject == {
        "status": "reviewed",
        "reviewed_by": "Editor (SZD)",
        "producer": "person",
        "fields": {"location": "reject"},
        "fieldStates": {"location": "confirmed"},
        "scope": ["location"],
    }
    mixed = stage_05.build_review(
        {"location": "Wien", "publisher": "Refused"},
        {("location", "Wien"): confirm, ("publisher", "Refused"): reject},
    )
    assert mixed["status"] == "confirmed"
    assert mixed["scope"] == ["location", "publisher"]
    proposal = stage_05.build_review(
        {"location": "Wien", "publisher": "Refused"},
        {("location", "Wien"): agent_confirm, ("publisher", "Refused"): reject},
    )
    assert proposal["status"] == "reviewed"
    assert proposal["fieldStates"] == {"location": "proposed", "publisher": "confirmed"}
    only_agent = stage_05.build_review(
        {"location": "Wien"}, {("location", "Wien"): agent_confirm}
    )
    assert only_agent["status"] == "proposed"
    assert only_agent["basis"] == (
        "proposed by LLM agents, no source occurrence, no person"
    )


def test_place_review_states_its_field_scope(all_entries) -> None:
    """Place decisions verify the place alone, and the test fixture of twenty
    places decides nothing since the operator decision of 2026-10-23."""
    reviews = [entry["review"] for entry in all_entries if entry.get("review")]
    assert reviews
    assert all(review["scope"] == ["location"] for review in reviews)
    assert not any(
        review.get("reviewed_by") == "repository-ground-truth-fixture"
        for review in reviews
    )


def test_display_values_are_flat(all_entries) -> None:
    """Resource-valued RDF properties must reach the frontend as flat display
    strings, never as {'@id': ...} objects the UI would render raw."""
    flat_string_keys = [
        key
        for key, (_, allowed) in ENTRY_CONTRACT.items()
        if allowed == (str,) and not key.startswith("@")
    ]
    for entry in all_entries:
        for key in flat_string_keys:
            value = entry.get(key)
            assert value is None or isinstance(value, str)


# Publication layer: per-page side files the entry card loads on demand.
PUBLICATION_KEYS = {
    "container",
    "credits",
    "contributions",
    "editionId",
    "editionStatement",
    "extent",
    "id",
    "imprint",
    "imprints",
    "language",
    "languageCode",
    "note",
    "online",
    "places",
    "provenance",
    "publisher",
    "reviewDecision",
    "reviewFlags",
    "reviewProducer",
    "reviewStatus",
    "series",
    "seriesGloss",
    "seriesVolume",
    "sourceSlice",
    "title",
    "year",
    "yearRaw",
}
PUBLICATION_REQUIRED_KEYS = {"id", "provenance", "reviewStatus", "sourceSlice"}
PUBLICATION_STRUCTURAL_KEYS = {
    "editionId",
    "id",
    "provenance",
    "reviewDecision",
    "reviewFlags",
    "reviewProducer",
    "reviewStatus",
    "sourceSlice",
}
# The Gate-1 statement states. A publication outside the Gate-1 corpus is
# rule-extracted and unreviewed, so it is proposed; contested passes through
# from an edition whose binding is held open.
PUBLICATION_REVIEW_STATUSES = {"confirmed", "proposed", "contested"}
SOURCE_SLICE_KEYS = {"start", "end", "sha256", "textStart", "textEnd"}
SIDE_FILE_KEYS = {"sourcePageId", "publications", "nameVariants"}
PROVENANCE_CLASSES = {"regex", "llm", "missing", "editor"}
PAGE_KINDS = {"author-page", "edition-page", "single-publication"}
CREDIT_ROLES = {"author", "translator", "editor", "illustrator", "contributor"}
PUBLICATIONS_DIR = (
    Path(__file__).resolve().parents[1] / "docs" / "data" / "publications"
)


def _pages_with_publications(all_entries) -> list[dict]:
    return [entry for entry in all_entries if entry.get("publicationCount")]


@lru_cache(maxsize=None)
def _side_file(page_id: int) -> dict:
    return json.loads(
        (PUBLICATIONS_DIR / f"{page_id}.json").read_text(encoding="utf-8")
    )


def test_the_main_dataset_carries_no_publication_arrays(all_entries) -> None:
    """The arrays live in side files, so the main dataset stays loadable for
    search and facets without fetching them."""
    for entry in all_entries:
        assert "publications" not in entry
        assert "nameVariants" not in entry


def test_the_publication_layer_reached_the_dataset(all_entries) -> None:
    pages = _pages_with_publications(all_entries)
    assert pages, "no entry declares publication-scoped facts"
    for entry in pages:
        assert entry["pageKind"] in PAGE_KINDS
        assert entry["publicationCount"] >= 1


def test_every_declared_page_has_its_side_file(all_entries, frontend_data) -> None:
    pages = _pages_with_publications(all_entries)
    declared = {entry["sourcePageId"] for entry in pages}
    present = {int(path.stem) for path in PUBLICATIONS_DIR.glob("*.json")}
    assert declared == present, (
        "the side-file set must equal the set of pages declaring a layer"
    )
    coverage = frontend_data["_meta"]["publicationCoverage"]
    assert coverage["pages"] == len(declared)
    assert coverage["pathTemplate"] == "data/publications/{sourcePageId}.json"


def test_every_side_file_matches_the_declared_contract(all_entries) -> None:
    for entry in _pages_with_publications(all_entries):
        page_id = entry["sourcePageId"]
        side = _side_file(page_id)
        assert set(side) == SIDE_FILE_KEYS
        assert side["sourcePageId"] == page_id
        assert len(side["publications"]) == entry["publicationCount"]
        for publication in side["publications"]:
            keys = set(publication)
            assert not keys - PUBLICATION_KEYS, (
                f"page {page_id} publication carries undeclared keys "
                f"{sorted(keys - PUBLICATION_KEYS)}"
            )
            assert PUBLICATION_REQUIRED_KEYS <= keys
            assert {"start", "end", "sha256"} <= set(publication["sourceSlice"])
            assert set(publication["sourceSlice"]) <= SOURCE_SLICE_KEYS
            assert set(publication["provenance"].values()) <= PROVENANCE_CLASSES
            for credit in publication.get("credits", []):
                assert {"role", "name", "creditLabel"} <= set(credit)
                assert set(credit) <= {"role", "name", "creditLabel", "uncertain"}
                assert credit.get("uncertain", True) is True
                assert credit["role"] in CREDIT_ROLES
            for flag in publication.get("reviewFlags", []):
                assert set(flag) == {"code", "detail"}


def test_every_publication_field_states_its_provenance_class(all_entries) -> None:
    """No displayed publication value is left without a provenance class."""
    for entry in _pages_with_publications(all_entries):
        for publication in _side_file(entry["sourcePageId"])["publications"]:
            assert (
                set(publication["provenance"])
                == set(publication) - PUBLICATION_STRUCTURAL_KEYS
            )


def _gate1_edition_states() -> dict[str, str]:
    graph = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "data/output/editions/work-editions.jsonld"
        ).read_text(encoding="utf-8")
    )
    return {
        edition["@id"]: edition["klawiter:reviewStatus"]
        for edition in graph["editions"]
    }


def test_publications_name_their_edition_node_and_its_review_status(
    all_entries,
) -> None:
    """A publication that is a Gate-1 edition names that node and reports its
    status; any other publication is proposed and names no node. An edition the
    agentic sample reviewed names that disposition and its producer, and stays
    proposed or contested, because only a person or an exact rule confirms."""
    states = _gate1_edition_states()
    named = agent_reviewed = 0
    for entry in _pages_with_publications(all_entries):
        for publication in _side_file(entry["sourcePageId"])["publications"]:
            status = publication["reviewStatus"]
            assert status in PUBLICATION_REVIEW_STATUSES
            edition_id = publication["id"].replace(
                "klawiter:publication/", "klawiter:edition/", 1
            )
            if edition_id in states:
                named += 1
                assert publication["editionId"] == edition_id
                assert status == states[edition_id]
            else:
                assert "editionId" not in publication
                assert status == "proposed"
            if "reviewDecision" in publication:
                agent_reviewed += 1
                assert publication["reviewProducer"] == "llm-agent"
                assert status in {"proposed", "contested"}
            else:
                assert "reviewProducer" not in publication
            assert status != "confirmed"
    assert named, "no publication names a Gate-1 edition node"
    assert agent_reviewed, "the agent-reviewed Gate-1 sample did not reach the layer"


def test_entry_names_the_flag_codes_of_its_publications(all_entries) -> None:
    """The main dataset tells a card which publication flags a page holds,
    without the side file; it lists exactly the codes the side file carries."""
    flagged = 0
    for entry in _pages_with_publications(all_entries):
        codes = sorted(
            {
                flag["code"]
                for publication in _side_file(entry["sourcePageId"])["publications"]
                for flag in publication.get("reviewFlags", [])
            }
        )
        assert entry.get("publicationReviewFlags", []) == codes
        flagged += bool(codes)
    assert flagged, "no page reports a publication review flag"
    for entry in all_entries:
        if not entry.get("publicationCount"):
            assert "publicationReviewFlags" not in entry


def test_meta_names_the_producers_of_the_provenance_chain(
    frontend_data, all_entries
) -> None:
    """An agent-reviewed edition and an `llm` value name who produced them."""
    review = frontend_data["_meta"]["editionReview"]
    assert review["producer"] == "llm-agent"
    assert (
        review["artifact"] == "data/output/edition-samples/reviews/reconciliation.json"
    )
    assert review["reviewers"] == ["reviewer_a", "reviewer_b"]
    assert review["reviewedAt"] and review["verifierAgent"] and review["cases"] > 0
    llm = frontend_data["_meta"]["llmEnrichment"]
    assert llm["mode"] in {"frozen", "live", "off"}
    if any("llm" in (e.get("_provenance") or {}).values() for e in all_entries):
        assert llm["model"] and llm["frozenAt"] and llm["promptSha256"]


def test_meta_states_license_and_release_version(frontend_data) -> None:
    import tomllib

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    version = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    meta = frontend_data["_meta"]
    assert meta["license"] == "https://creativecommons.org/licenses/by/4.0/"
    assert meta["version"] == version


def test_facet_fields_cover_every_publication(all_entries) -> None:
    """A page with several publications must be findable under each of their
    years, places and languages, without loading its side file."""
    for entry in _pages_with_publications(all_entries):
        for publication in _side_file(entry["sourcePageId"])["publications"]:
            if "year" in publication:
                assert publication["year"] in entry["publicationYears"]
            for place in publication.get("places", []):
                assert place in entry["publicationPlaces"]
            container_place = publication.get("container", {}).get("place")
            if container_place:
                assert container_place in entry["publicationPlaces"]
            if "language" in publication:
                assert publication["language"] in entry["publicationLanguages"]


def test_name_variants_are_never_silently_resolved(all_entries) -> None:
    for entry in _pages_with_publications(all_entries):
        for variant in _side_file(entry["sourcePageId"])["nameVariants"]:
            assert set(variant) == {
                "name",
                "variantOf",
                "status",
                "sourceContext",
                "provenance",
            }
            assert variant["status"] == "unresolved"


def test_entry_review_flags_name_their_field(all_entries) -> None:
    """An encoding repair on a flat field stays visible as a review hint."""
    flagged = [entry for entry in all_entries if entry.get("reviewFlags")]
    assert flagged, "no entry carries a field-level review hint"
    for entry in flagged:
        for flag in entry["reviewFlags"]:
            assert set(flag) == {"code", "field", "detail"}
            assert flag["field"] in ENTRY_CONTRACT
            assert flag["detail"].strip()


def test_publication_spans_point_into_the_delivered_text(all_entries) -> None:
    """Where the record names a span of the delivered bibliographic text, that
    span must carry this publication's own statement, and only one page region
    may match it. Where no unambiguous region exists the offsets are absent."""
    spanned = 0
    for entry in _pages_with_publications(all_entries):
        delivered = entry.get("fullBibliographicEntry", "")
        previous_start = previous_end = -1
        for publication in _side_file(entry["sourcePageId"])["publications"]:
            source_slice = publication["sourceSlice"]
            if "textStart" not in source_slice:
                assert "textEnd" not in source_slice
                continue
            spanned += 1
            start, end = source_slice["textStart"], source_slice["textEnd"]
            assert 0 <= start < end <= len(delivered)
            excerpt = delivered[start:end]
            assert delivered.count(excerpt) == 1, (
                f"page {entry['sourcePageId']}: the named span is not unique"
            )
            assert publication["yearRaw"] in excerpt
            # A compound header states two publications in one source block, so
            # those two share one span; blocks that differ must not overlap.
            if source_slice["start"] != previous_start:
                assert start >= previous_end, (
                    f"page {entry['sourcePageId']}: publication spans overlap"
                )
            previous_start, previous_end = source_slice["start"], end
    assert spanned, "no publication names a span of the delivered text"


def test_restored_pages_state_their_source_revision(frontend_data) -> None:
    """Maria Stuart is published from the compiler's revision 33251, which the
    wiki's Redirect fixer overwrote in revision 33773."""
    by_page = {entry["sourcePageId"]: entry for entry in frontend_data["entries"]}
    restored = by_page[35]["sourceRevision"]
    assert restored["humanRevision"]["revisionId"] == 33251
    assert restored["humanRevision"]["textId"] == by_page[35]["sourceTextId"]
    assert [rev["revisionId"] for rev in restored["fixerRevisions"]] == [33773]
    assert "sourceRevision" not in by_page[4113]


# Wiki page kind and cited print addresses (lib/page_kinds.py,
# lib/print_addresses.py).
WIKI_PAGE_KIND_VALUES = {
    "work-hub",
    "edition-page",
    "author-page",
    "other",
    "undetermined",
}
KIND_EVIDENCE_FIELDS = {"pageTitle", "categories", "sourceText"}
CITATION_KEYS = {
    "printAddress",
    "printVolume",
    "printSection",
    "printEntryNumber",
    "printEntryNumberEnd",
    "citationState",
    "citationNotation",
    "citationTarget",
    "sourceValue",
    "sourceStart",
    "sourceEnd",
    "passageText",
    "passageStart",
    "passageEnd",
}
CITATION_REQUIRED_KEYS = CITATION_KEYS - {"printEntryNumber", "printEntryNumberEnd"}
PRINT_VOLUMES = {"main-volume", "addendum-1", "addendum-2"}
CITATION_NOTATIONS = {"see", "bracket", "parenthesis", "plain"}
CITATION_TARGETS = {"entry", "section"}


def test_every_content_page_declares_its_wiki_page_kind(all_entries) -> None:
    for entry in all_entries:
        keys = {"wikiPageKind", "wikiPageKindRule", "wikiPageKindEvidence"}
        if entry["pageNamespace"] != 0:
            assert not keys & set(entry)
            continue
        assert keys <= set(entry)
        assert entry["wikiPageKind"] in WIKI_PAGE_KIND_VALUES
        for evidence in entry["wikiPageKindEvidence"]:
            assert evidence["sourceField"] in KIND_EVIDENCE_FIELDS
            assert isinstance(evidence["sourceValue"], str) and evidence["sourceValue"]
            if evidence["sourceField"] == "sourceText":
                assert set(evidence) == {
                    "sourceField",
                    "sourceValue",
                    "sourceStart",
                    "sourceEnd",
                }
                assert 0 <= evidence["sourceStart"] < evidence["sourceEnd"]
            else:
                assert set(evidence) == {"sourceField", "sourceValue"}


def test_cited_print_addresses_match_the_declared_contract(all_entries) -> None:
    cited = [e for e in all_entries if "printAddressCitations" in e]
    assert cited, "no entry cites a print address"
    for entry in cited:
        assert entry["printAddressCitations"], "an empty list is omitted"
        for citation in entry["printAddressCitations"]:
            assert CITATION_REQUIRED_KEYS <= set(citation) <= CITATION_KEYS
            assert citation["citationState"] == "cites"
            assert citation["printVolume"] in PRINT_VOLUMES
            assert citation["citationNotation"] in CITATION_NOTATIONS
            assert citation["citationTarget"] in CITATION_TARGETS
            assert (citation["citationTarget"] == "entry") == (
                "printEntryNumber" in citation
            )
            assert citation["printAddress"].startswith(citation["printSection"])
