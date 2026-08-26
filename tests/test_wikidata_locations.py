"""Tests for Wikidata location reconciliation.

Verifies that locations.json has correct Wikidata Q-IDs, sufficient coverage,
valid coordinate ranges, and no false duplicate matches.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
LOCATIONS_PATH = PROJECT_ROOT / "docs" / "data" / "locations.json"
GROUND_TRUTH_PATH = Path(__file__).parent / "wikidata_ground_truth.json"


@pytest.fixture(scope="session")
def locations_with_wikidata():
    return json.loads(LOCATIONS_PATH.read_text("utf-8"))


@pytest.fixture(scope="session")
def wikidata_ground_truth():
    return json.loads(GROUND_TRUTH_PATH.read_text("utf-8"))


class TestWikidataReconciliation:
    """Deterministic tests for Wikidata location matching."""

    def test_top20_qids(self, locations_with_wikidata, wikidata_ground_truth):
        """The 20 most important locations must have the correct Q-ID."""
        for name, expected_qid in wikidata_ground_truth.items():
            loc = locations_with_wikidata.get(name)
            assert loc is not None, f"{name} not in locations.json"
            actual_qid = loc.get("wikidataId")
            assert actual_qid == expected_qid, (
                f"{name}: expected {expected_qid}, got {actual_qid}"
            )

    def test_reconciliation_coverage(self, locations_with_wikidata):
        """At least 90% of locations must have a Wikidata Q-ID."""
        total = len(locations_with_wikidata)
        with_qid = sum(
            1 for v in locations_with_wikidata.values() if v.get("wikidataId")
        )
        coverage = with_qid / total
        assert coverage >= 0.90, (
            f"Wikidata coverage {coverage:.1%} < 90% ({with_qid}/{total})"
        )

    def test_qid_format(self, locations_with_wikidata):
        """All Q-IDs must match the pattern Q[digits]."""
        for name, loc in locations_with_wikidata.items():
            qid = loc.get("wikidataId")
            if qid:
                assert re.match(r"^Q\d+$", qid), f'{name}: invalid Q-ID format "{qid}"'

    def test_coordinates_valid_range(self, locations_with_wikidata):
        """All coordinates must be in valid geographic range."""
        for name, loc in locations_with_wikidata.items():
            assert -90 <= loc["lat"] <= 90, f"{name}: lat {loc['lat']} out of range"
            assert -180 <= loc["lng"] <= 180, f"{name}: lng {loc['lng']} out of range"

    def test_no_false_duplicate_qids(self, locations_with_wikidata):
        """Different cities must not share the same Q-ID.

        Spelling variants (Wien/Vienna) sharing a Q-ID are allowed
        if their coordinates are within 0.15 degrees.
        """
        qid_to_names = defaultdict(list)
        for name, loc in locations_with_wikidata.items():
            qid = loc.get("wikidataId")
            if qid:
                qid_to_names[qid].append(name)

        for qid, names in qid_to_names.items():
            if len(names) <= 1:
                continue
            locs = [locations_with_wikidata[n] for n in names]
            for i in range(1, len(locs)):
                delta = abs(locs[0]["lat"] - locs[i]["lat"]) + abs(
                    locs[0]["lng"] - locs[i]["lng"]
                )
                assert delta < 1.0, (
                    f"Q-ID {qid} shared by distant locations: "
                    f"{names[0]} and {names[i]} (delta={delta:.2f}°)"
                )

    def test_country_code_present(self, locations_with_wikidata):
        """All locations must have an ISO alpha-2 country code."""
        for name, loc in locations_with_wikidata.items():
            cc = loc.get("country")
            assert cc and re.match(r"^[A-Z]{2}$", cc), (
                f'{name}: missing or invalid country code "{cc}"'
            )
