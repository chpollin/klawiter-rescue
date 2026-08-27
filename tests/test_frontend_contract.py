"""Frontend data contract: the projection boundary between RDF and UI.

The modeling layer may enrich the RDF datasets freely; make_frontend_entry in
pipeline/05_to_jsonld.py must keep projecting docs/data/klawiter.json to
exactly this declared shape (resources flattened to display values). A
deliberate contract change updates this declaration in the same change that
adapts the frontend, never as a side effect of modeling work.
"""

from __future__ import annotations

import importlib

# Bumped whenever the declared entry or _meta shape changes. 1.1 added the
# review projection (dataset-level review state per entry).
FRONTEND_SCHEMA_VERSION = "1.1"

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
    "locationCount",
    "ns0Count",
    "redirectCount",
    "totalCount",
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
