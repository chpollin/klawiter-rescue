"""
Unit tests for the per-field provenance decision and the atomic JSON writer.

The provenance label must reflect the 03b merge semantics: the merge fills
gaps only, so a regex-filled field stays 'regex' even when the LLM cache
holds a value for the same field (regression: cache presence used to win).
"""

import json
import os

import pytest
from inject_provenance import (
    field_provenance,
    llm_enrichment_meta,
    load_provenance_cache,
)
from lib.config import write_json

# --- field_provenance ---


def test_empty_field_is_missing():
    assert field_provenance(False, False, False) == "missing"


def test_empty_field_is_missing_despite_cache():
    # 03c normalization can reject an LLM value after the merge
    assert field_provenance(False, False, True) == "missing"


def test_regex_value_without_cache():
    assert field_provenance(True, True, False) == "regex"


def test_regex_value_wins_over_cache_presence():
    # Regression: a cache entry for an already-filled field was never merged,
    # so the final value is the regex value, not the LLM value
    assert field_provenance(True, True, True) == "regex"


def test_llm_filled_gap():
    assert field_provenance(True, False, True) == "llm"


def test_filled_without_known_source_fails():
    # No value relied on the former regex default (audit 2026-10-30); an
    # unknown origin is an error, not a label.
    with pytest.raises(ValueError):
        field_provenance(True, False, False)


def test_frozen_provenance_cache_is_tracked_and_nonempty():
    assert load_provenance_cache("frozen")


def test_off_mode_has_no_llm_provenance():
    assert load_provenance_cache("off") == {}


def test_llm_run_is_named_from_the_frozen_cache():
    meta = llm_enrichment_meta("frozen")
    assert meta["mode"] == "frozen"
    assert meta["cache"] == "data/provenance/llm-enrichment-cache.json"
    assert meta["model"] and meta["frozenAt"] and len(meta["promptSha256"]) == 64
    # The cache's own statement of what it does not hold travels with the run.
    assert meta["originLimit"]


def test_off_mode_names_no_llm_run():
    assert llm_enrichment_meta("off") == {"mode": "off"}


# --- write_json ---


def test_write_json_valid_output_and_no_tmp_left(tmp_path):
    path = str(tmp_path / "out.json")
    write_json(path, {"a": 1, "text": "Künstler"}, separators=(",", ":"))
    with open(path, encoding="utf-8") as f:
        assert json.load(f) == {"a": 1, "text": "Künstler"}
    assert not os.path.exists(path + ".tmp")


def test_write_json_overwrites_existing_file(tmp_path):
    path = str(tmp_path / "out.json")
    write_json(path, {"v": 1})
    write_json(path, {"v": 2})
    with open(path, encoding="utf-8") as f:
        assert json.load(f) == {"v": 2}
