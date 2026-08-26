"""
Unit tests for pipeline/lib/vocabulary.py.
Tests classification, category mapping, and ISO language conversion.
"""

from lib.vocabulary import category_to_entry_type, classify_time_period, language_to_iso


class TestClassifyTimePeriod:
    def test_lifetime(self):
        assert classify_time_period(1881) == "lifetime"
        assert classify_time_period(1942) == "lifetime"
        assert classify_time_period(1920) == "lifetime"

    def test_post_wwii(self):
        assert classify_time_period(1943) == "post-wwii"
        assert classify_time_period(1980) == "post-wwii"

    def test_late_20c(self):
        assert classify_time_period(1981) == "late-20c"
        assert classify_time_period(2000) == "late-20c"

    def test_contemporary(self):
        assert classify_time_period(2001) == "contemporary"
        assert classify_time_period(2024) == "contemporary"

    def test_pre_zweig(self):
        assert classify_time_period(1850) == "pre-zweig"
        assert classify_time_period(1880) == "pre-zweig"

    def test_none(self):
        assert classify_time_period(None) is None


class TestCategoryToEntryType:
    def test_fiction_prefix(self):
        assert category_to_entry_type("Fiction / Volumes (German)") == "fiction"
        assert (
            category_to_entry_type("Fiction / Individual Stories (Chinese)")
            == "fiction"
        )

    def test_essays(self):
        assert category_to_entry_type("Essays / Individual Essays (French)") == "essay"

    def test_historical_studies(self):
        assert (
            category_to_entry_type("Historical Studies / Volumes (Bulgarian)")
            == "historical-study"
        )

    def test_secondary_literature(self):
        assert (
            category_to_entry_type("Secondary Literature / Authors (English)")
            == "secondary-literature"
        )

    def test_films(self):
        assert category_to_entry_type("Films / Plays / Operas") == "film"

    def test_collected_works(self):
        assert (
            category_to_entry_type("Collected and Selected Works") == "collected-works"
        )

    def test_poetry(self):
        assert category_to_entry_type("Poetry / Individual Poems (German)") == "poetry"

    def test_unknown_returns_other(self):
        assert category_to_entry_type("Something Completely Unknown") == "other"

    def test_empty_returns_other(self):
        assert category_to_entry_type("") == "other"
        assert category_to_entry_type(None) == "other"


class TestLanguageToIso:
    def test_common_languages(self):
        assert language_to_iso("German") == "de"
        assert language_to_iso("English") == "en"
        assert language_to_iso("French") == "fr"
        assert language_to_iso("Japanese") == "ja"
        assert language_to_iso("Chinese") == "zh"
        assert language_to_iso("Russian") == "ru"

    def test_case_insensitive(self):
        assert language_to_iso("german") == "de"
        assert language_to_iso("ENGLISH") == "en"

    def test_already_iso_code(self):
        assert language_to_iso("de") == "de"
        assert language_to_iso("en") == "en"

    def test_unknown_returns_none(self):
        assert language_to_iso("Klingon") is None
        assert language_to_iso("") is None
        assert language_to_iso(None) is None
