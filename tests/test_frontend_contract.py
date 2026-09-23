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
# the co-imprint pairs and series gloss, and the release license and version.
FRONTEND_SCHEMA_VERSION = "1.4"

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
    "entryTypes",
    "fieldCoverage",
    "frontendSchemaVersion",
    "languageCount",
    "license",
    "locationCount",
    "ns0Count",
    "publicationCoverage",
    "redirectCount",
    "totalCount",
    "version",
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
    "timePeriod": (False, (str,)),
    "translations": (False, (list,)),
    "translator": (False, (str,)),
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
REVIEW_KEYS = {"status", "reviewed_by", "reviewed_at", "fields"}
REVIEW_REQUIRED_KEYS = {"status", "reviewed_by"}
REVIEW_STATUSES = {"approved", "agent_verified", "contested"}
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
        for field in fields:
            assert entry.get(field), (
                f"entry {entry['@id']} reviews {field} without carrying a value"
            )


def test_review_projection_is_derived_from_gate2_decisions() -> None:
    """The projection reports a decision that exists, never a bare status."""
    stage_05 = importlib.import_module("05_to_jsonld")
    index = stage_05.load_review_index()
    assert index, "Gate 2 decisions did not reach the review index"
    entry = {"location": "Amsterdam", "translator": "not a reviewed name"}
    review = stage_05.build_review(entry, index)
    assert review["fields"] == {"location": "confirm"}
    assert review["status"] == "agent_verified"
    assert review["reviewed_by"] == index[("location", "Amsterdam")]["decidedBy"]
    assert stage_05.build_review({"location": "not a reviewed place"}, index) is None


def test_unresolved_decision_projects_as_contested() -> None:
    stage_05 = importlib.import_module("05_to_jsonld")
    index = {
        ("location", "Tyresö"): {
            "action": "unresolved",
            "decidedBy": "independent-verification-agent",
            "decidedAt": "2026-08-21T20:00:00Z",
        }
    }
    review = stage_05.build_review({"location": "Tyresö"}, index)
    assert review == {
        "status": "contested",
        "reviewed_by": "independent-verification-agent",
        "reviewed_at": "2026-08-21T20:00:00Z",
        "fields": {"location": "unresolved"},
    }


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
    "reviewFlags",
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
    "reviewFlags",
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
                assert set(credit) == {"role", "name", "creditLabel"}
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
    status; any other publication is proposed and names no node."""
    states = _gate1_edition_states()
    named = 0
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
    assert named, "no publication names a Gate-1 edition node"
    assert "confirmed" in {
        publication["reviewStatus"]
        for entry in _pages_with_publications(all_entries)
        for publication in _side_file(entry["sourcePageId"])["publications"]
    }, "the reviewed Gate-1 sample did not reach the publication layer"


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
