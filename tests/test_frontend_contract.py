"""Frontend data contract: the projection boundary between RDF and UI.

The modeling layer may enrich the RDF datasets freely; make_frontend_entry in
pipeline/05_to_jsonld.py must keep projecting docs/data/klawiter.json to
exactly this declared shape (resources flattened to display values). A
deliberate contract change updates this declaration in the same change that
adapts the frontend, never as a side effect of modeling work.
"""

from __future__ import annotations

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
