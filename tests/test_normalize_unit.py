"""
Unit tests for the pure normalization functions in pipeline/03c_normalize.py.

This is the safety net for the 03c refactoring: it pins the input→output
behavior of every normalization function BEFORE any structural change, so a
behavior drift would surface immediately.

The module has a digit in its filename (03c) and cannot be imported with a
normal `import` statement — it is loaded via importlib, the same mechanism the
pipeline runner uses for numbered steps.

Location variants are loaded from the real mapping table
(pipeline/data/location_normalize.json) and iterated over, rather than
duplicated here, so the tests stay in sync with the canonical data.
"""

import importlib.util
import json
import os

import pytest

PIPELINE_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "pipeline")
DATA_DIR = os.path.join(PIPELINE_DIR, "data")


def _load_03c():
    """Load the numbered pipeline module via importlib (digit in module name)."""
    path = os.path.abspath(os.path.join(PIPELINE_DIR, "03c_normalize.py"))
    spec = importlib.util.spec_from_file_location("normalize_03c", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def m():
    return _load_03c()


@pytest.fixture(scope="module")
def location_map():
    """The real canonical location mapping table."""
    path = os.path.join(DATA_DIR, "location_normalize.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def reject_patterns():
    """The real publisher reject patterns."""
    path = os.path.join(DATA_DIR, "publisher_reject_patterns.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f).get("patterns", [])


# ---------------------------------------------------------------------------
# normalize_location
# ---------------------------------------------------------------------------

class TestNormalizeLocation:
    def test_every_variant_maps_to_canonical(self, m, location_map):
        """Each variant in the real table maps to its canonical form."""
        for variant, canonical in location_map.items():
            assert m.normalize_location(variant, location_map) == canonical

    def test_unknown_value_unchanged(self, m, location_map):
        assert m.normalize_location("Some Unmapped City", location_map) == "Some Unmapped City"

    def test_empty_value_returned_as_is(self, m, location_map):
        assert m.normalize_location("", location_map) == ""
        assert m.normalize_location(None, location_map) is None

    def test_empty_map_returns_value(self, m):
        assert m.normalize_location("Vienna", {}) == "Vienna"


# ---------------------------------------------------------------------------
# normalize_all_locations
# ---------------------------------------------------------------------------

class TestNormalizeAllLocations:
    def test_maps_and_dedupes(self, m, location_map):
        # Build an input list from the first two variants plus a duplicate.
        variants = list(location_map.keys())
        first, second = variants[0], variants[1]
        canon_first, canon_second = location_map[first], location_map[second]
        value = json.dumps([first, second, first])
        result = json.loads(m.normalize_all_locations(value, location_map))
        # Order preserved, duplicates removed after canonicalization.
        assert result == list(dict.fromkeys([canon_first, canon_second, canon_first]))

    def test_unmapped_locations_kept(self, m, location_map):
        value = json.dumps(["Some Unmapped City"])
        assert json.loads(m.normalize_all_locations(value, location_map)) == ["Some Unmapped City"]

    def test_empty_value(self, m, location_map):
        assert m.normalize_all_locations("", location_map) == ""
        assert m.normalize_all_locations(None, location_map) is None

    def test_empty_map(self, m):
        value = json.dumps(["Vienna", "Munich"])
        assert m.normalize_all_locations(value, {}) == value

    def test_invalid_json_returned_unchanged(self, m, location_map):
        assert m.normalize_all_locations("not-json", location_map) == "not-json"


# ---------------------------------------------------------------------------
# clean_publisher
# ---------------------------------------------------------------------------

class TestCleanPublisher:
    def test_every_reject_pattern_strips_a_match(self, m, reject_patterns):
        """Each reject pattern, given a value it matches, yields empty string."""
        samples = {
            r"^\d+(st|nd|rd|th)\s+edition": "1st edition",
            r"^(Company|House|company|house)$": "Company",
            r"cataloging|website": "library cataloging in publication",
            r"^p\.\s": "p. 123",
            r"^(Vol|Part|Chapter|Section)\b": "Vol. 3",
            r"^[,;:\.\-\s]+$": " , . - ",
            r"^& Distribution$": "& Distribution",
            r"^and Distribution$": "and Distribution",
        }
        for pattern in reject_patterns:
            assert pattern in samples, f"No sample for reject pattern {pattern!r}"
            sample = samples[pattern]
            assert m.clean_publisher(sample, reject_patterns) == "", (
                f"Pattern {pattern!r} did not reject sample {sample!r}"
            )

    def test_valid_publisher_kept(self, m, reject_patterns):
        assert m.clean_publisher("Insel-Verlag", reject_patterns) == "Insel-Verlag"
        assert m.clean_publisher("S. Fischer Verlag", reject_patterns) == "S. Fischer Verlag"

    def test_empty_value(self, m, reject_patterns):
        assert m.clean_publisher("", reject_patterns) == ""
        assert m.clean_publisher(None, reject_patterns) is None


# ---------------------------------------------------------------------------
# normalize_publisher
# ---------------------------------------------------------------------------

class TestNormalizePublisher:
    def test_variant_maps_to_canonical(self, m):
        pub_map = {"Insel Verlag": ["Insel", "Insel-Verlag"]}
        assert m.normalize_publisher("Insel", pub_map) == "Insel Verlag"
        assert m.normalize_publisher("Insel-Verlag", pub_map) == "Insel Verlag"

    def test_unknown_value_unchanged(self, m):
        pub_map = {"Insel Verlag": ["Insel"]}
        assert m.normalize_publisher("Suhrkamp", pub_map) == "Suhrkamp"

    def test_empty_value_or_map(self, m):
        assert m.normalize_publisher("", {"X": ["y"]}) == ""
        assert m.normalize_publisher(None, {"X": ["y"]}) is None
        assert m.normalize_publisher("Insel", {}) == "Insel"


# ---------------------------------------------------------------------------
# clean_translator
# ---------------------------------------------------------------------------

class TestCleanTranslator:
    def test_strips_afterword_suffix(self, m):
        assert m.clean_translator("Hugo Hultenberg. Afterword by X") == "Hugo Hultenberg"

    def test_strips_introduction_suffix(self, m):
        assert m.clean_translator("Anthea Bell. Introduction by Y") == "Anthea Bell"

    def test_strips_german_nachwort_suffix(self, m):
        assert m.clean_translator("Anna Schmidt. Nachwort von Z") == "Anna Schmidt"

    def test_plain_name_unchanged(self, m):
        assert m.clean_translator("John Smith") == "John Smith"

    def test_strips_trailing_punctuation(self, m):
        assert m.clean_translator("Maria Mueller;") == "Maria Mueller"

    def test_short_residual_falls_back_to_original(self, m):
        # When stripping leaves <3 chars, the original value is returned.
        original = "ab. Foreword by Someone"
        assert m.clean_translator(original) == original

    def test_empty_value(self, m):
        assert m.clean_translator("") == ""
        assert m.clean_translator(None) is None


# ---------------------------------------------------------------------------
# validate_page_count
# ---------------------------------------------------------------------------

class TestValidatePageCount:
    def test_plausible_counts_kept(self, m):
        assert m.validate_page_count("250") == "250"
        assert m.validate_page_count("1") == "1"
        assert m.validate_page_count("1799") == "1799"

    def test_outliers_rejected(self, m):
        assert m.validate_page_count("2500") == ""
        assert m.validate_page_count("9999") == ""

    def test_year_like_values_rejected(self, m):
        assert m.validate_page_count("1948") == ""
        assert m.validate_page_count("1800") == ""
        assert m.validate_page_count("2030") == ""
        assert m.validate_page_count("2000") == ""

    def test_non_numeric_or_empty_returned_as_is(self, m):
        assert m.validate_page_count("") == ""
        assert m.validate_page_count(None) is None
        assert m.validate_page_count("abc") == "abc"
