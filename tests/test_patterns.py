"""
Unit tests for pipeline/lib/patterns.py extraction functions.
Uses real examples from the Klawiter bibliography dataset.
"""

from lib.patterns import (
    extract_year,
    extract_all_years,
    extract_publisher,
    extract_location,
    extract_all_locations,
    extract_page_count,
    extract_translator,
    extract_language_from_category,
)


class TestExtractYear:
    def test_year_in_header(self):
        assert extract_year("'''[1943]: Skoglunds Bokförlag, Stockholm'''") == 1943

    def test_year_in_text(self):
        assert extract_year("Published in Leipzig, 1932. 542p.") == 1932

    def test_multiple_years_returns_first(self):
        assert extract_year("'''[1947]: Pechat Far'''\n'''[1960]: Narodna Kultura'''") == 1947

    def test_rejects_page_numbers(self):
        assert extract_year("pp. 100-124") is None

    def test_boundary_years(self):
        assert extract_year("Printed in 1800") == 1800
        assert extract_year("Expected in 2030") == 2030
        # Years beyond MAX_VALID_YEAR are rejected
        assert extract_year("Far future 2099") is None

    def test_empty_and_none(self):
        assert extract_year(None) is None
        assert extract_year("") is None
        assert extract_year("No year here") is None


class TestExtractAllYears:
    def test_multiple_years_sorted_deduped(self):
        text = "Reprinted 1990, first published 1942, edition 1981, again 1942"
        assert extract_all_years(text) == [1942, 1981, 1990]

    def test_empty(self):
        assert extract_all_years("") == []
        assert extract_all_years(None) == []


class TestExtractPublisher:
    def test_verlag_suffix(self):
        assert extract_publisher("Suhrkamp Verlag, Frankfurt") == "Suhrkamp Verlag"

    def test_press_suffix(self):
        assert extract_publisher("Oxford University Press, 2001") == "Oxford University Press"

    def test_explicit_label(self):
        assert extract_publisher("Verlag: Insel-Verlag") == "Insel-Verlag"

    def test_published_by(self):
        assert extract_publisher("Published by Insel-Verlag. Leipzig.") == "Insel-Verlag"

    def test_editions_suffix(self):
        result = extract_publisher("Éditions Gallimard, Paris")
        assert result is not None and "Gallimard" in result

    def test_no_match(self):
        assert extract_publisher(None) is None
        assert extract_publisher("Just some text about Stefan Zweig") is None


class TestExtractLocation:
    def test_known_cities(self):
        assert extract_location("Published in Wien, 1932") == "Wien"
        assert extract_location("Published in Tokyo, 1998") == "Tokyo"
        assert extract_location("Buenos Aires, 1940") == "Buenos Aires"

    def test_city_in_brackets(self):
        assert extract_location("[Stockholm] 1943") == "Stockholm"

    def test_compound_city_longest_match(self):
        assert extract_location("Frankfurt am Main, 1976") == "Frankfurt am Main"

    def test_no_match(self):
        assert extract_location(None) is None
        assert extract_location("No city here") is None

    # --- Publication-line header fix (validation.md error class 1, "Weimar") ---

    def test_location_from_publication_header(self):
        # The bold '''[YEAR]: Publisher, Location''' header is read first.
        assert extract_location("'''[1943]: Skoglunds Bokförlag, Stockholm'''") == "Stockholm"

    def test_chapter_title_city_not_taken_as_location(self):
        # A city inside a chapter title must not become the place of publication
        # when a real publication header is present. This is the Weimar bug.
        text = ("'''[1981]: Insel Verlag, Frankfurt am Main'''\n"
                "''Die Marienbader Elegie. Goethe zwischen Karlsbad und Weimar''. 120p.")
        assert extract_location(text) == "Frankfurt am Main"

    def test_non_western_city_recovered_from_header(self):
        # A place absent from the known-city list is kept as the literal header
        # tail, so the fix enriches rather than only filters.
        assert extract_location("'''[2010]: Apaga Press, Yerevan'''") == "Yerevan"

    def test_trailing_us_state_code_falls_back_to_city(self):
        # "City, ST" — a two-letter state code is not the place; use the segment
        # before it. Ann Arbor is not in the known list, so it is kept literally.
        assert extract_location("'''[1955]: Some Press, Ann Arbor, MI'''") == "Ann Arbor"

    def test_primary_alternate_reduced_to_primary(self):
        # "Wien [Vienna]" -> "Wien".
        assert extract_location("'''[1935]: Herbert Reichner Verlag, Wien [Vienna]'''") == "Wien"

    def test_bracket_known_city_preferred_over_reprint_reference(self):
        # A headerless article keeps its original journal place ([Berlin]) rather
        # than the city of a later reprint anthology ([Krems an der Donau, 2019]).
        text = "Some review. [Berlin] Later reprinted in [Krems an der Donau, 2019]."
        assert extract_location(text) == "Berlin"

    def test_headerless_excerpt_uses_bracket_place(self):
        # No publication header, no known city in a bracket: a [City, year]
        # reference supplies the place.
        assert extract_location("Excerpt. [Ljubljana, 1959] pp. 12-18.") == "Ljubljana"

    def test_header_without_location_falls_through_to_body(self):
        # Header carries no recognizable place: fall through to the body search.
        assert extract_location("'''[1920]: Insel-Verlag'''\nsomething in Leipzig") == "Leipzig"


class TestExtractAllLocations:
    def test_multiple_cities_ordered_deduped(self):
        text = "Berlin, Wien, Leipzig, Wien again"
        result = extract_all_locations(text)
        assert "Berlin" in result and "Wien" in result and "Leipzig" in result
        assert result.count("Wien") == 1
        assert result.index("Berlin") < result.index("Wien")

    def test_empty(self):
        assert extract_all_locations("") == []
        assert extract_all_locations(None) == []


class TestExtractPageCount:
    def test_various_formats(self):
        assert extract_page_count("542p.") == 542
        assert extract_page_count("pp. 254") == 254
        assert extract_page_count("348 pages") == 348
        assert extract_page_count("254 Seiten") == 254
        assert extract_page_count("142 S.") == 142
        assert extract_page_count("496p Illustrated") == 496

    def test_real_entry_simple(self):
        assert extract_page_count("Translated by Hymne Weiss. 160p.") == 160

    def test_parenthesized_supplement_matched(self):
        # 347/(1)p. — N/(M)p. notation: N numbered + M unnumbered pages
        assert extract_page_count("Hugo Hultenberg. 347/(1)p.") == 347

    def test_rejects_page_ranges(self):
        """pp. N-M is a page range (start-end), not a page count."""
        assert extract_page_count("pp. 111-118") is None
        assert extract_page_count("pp. 289-325") is None
        assert extract_page_count("pp. 84-125") is None
        assert extract_page_count("pp. 7-18") is None

    def test_rejects_over_10000(self):
        assert extract_page_count("99999p.") is None

    def test_no_match(self):
        assert extract_page_count(None) is None
        assert extract_page_count("No pages mentioned") is None


class TestExtractTranslator:
    def test_multilingual_patterns(self):
        assert extract_translator("Translated by Hugo Hultenberg.") == "Hugo Hultenberg"
        assert extract_translator("Übersetzt von Hermann Wolf.") == "Hermann Wolf"
        assert extract_translator("Traduit par Alzir Hella.") == "Alzir Hella"
        assert extract_translator("Traducción de Alfredo Cahn.") == "Alfredo Cahn"
        assert extract_translator("Traduzione di Lavinia Mazzucchetti.") == "Lavinia Mazzucchetti"
        assert extract_translator("Trans. John Smith.") == "John Smith"

    def test_strips_trailing_punctuation(self):
        assert extract_translator("Translated by Hugo Hultenberg.,;:") == "Hugo Hultenberg"

    def test_name_must_start_uppercase(self):
        assert extract_translator("Translated by someone unknown") is None

    def test_german_original_no_translator(self):
        assert extract_translator("Compiled with an afterword by Volker Michels. 254/(1)p.") is None

    def test_no_match(self):
        assert extract_translator(None) is None
        assert extract_translator("Just some text") is None


class TestExtractLanguageFromCategory:
    def test_common_languages(self):
        assert extract_language_from_category(["Fiction / Volumes (German)"]) == "German"
        assert extract_language_from_category(["Secondary Literature (English)"]) == "English"
        assert extract_language_from_category(["Fiction (Japanese)"]) == "Japanese"

    def test_unknown_language_rejected(self):
        assert extract_language_from_category(["Fiction (Klingon)"]) is None

    def test_no_language_in_category(self):
        assert extract_language_from_category(["Films / Plays / Operas"]) is None

    def test_multiple_categories_first_match(self):
        cats = ["Secondary Literature", "Fiction / Volumes (Spanish)"]
        assert extract_language_from_category(cats) == "Spanish"

    def test_empty_and_none(self):
        assert extract_language_from_category([]) is None
        assert extract_language_from_category(None) is None
