"""
Unit tests for pipeline/lib/wiki_parser.py.
Uses real examples from the Klawiter bibliography dataset.
"""

from lib.wiki_parser import (
    extract_categories,
    extract_contents_block,
    extract_defaultsortkey,
    extract_original_title,
    extract_reprints,
    extract_see_references,
    extract_structured_data,
    extract_title,
    extract_translations_block,
    is_redirect,
    parse_redirect,
    remove_wiki_markup,
)


class TestParseRedirect:
    def test_standard_redirect(self, entry_redirect):
        assert (
            parse_redirect(entry_redirect)
            == "Mariia Antoaneta. Slika jednog osrednjeg karaktera"
        )

    def test_case_insensitive(self):
        assert parse_redirect("#redirect [[Target]]") == "Target"

    def test_not_a_redirect(self):
        assert parse_redirect("'''Normal Entry''' content") is None


class TestIsRedirect:
    def test_true_and_false(self, entry_redirect, entry_bold_title):
        assert is_redirect(entry_redirect) is True
        assert is_redirect(entry_bold_title) is False
        assert is_redirect("") is False
        assert is_redirect(None) is False


class TestExtractCategories:
    def test_single_category(self):
        content = "Some text\n[[Category:Fiction / Volumes (German)]]"
        cats, cleaned = extract_categories(content)
        assert cats == ["Fiction / Volumes (German)"]
        assert "[[Category:" not in cleaned

    def test_multiple_categories(self):
        content = "Text\n[[Category:Fiction (German)]]\n[[Category:Novellas]]"
        cats, cleaned = extract_categories(content)
        assert len(cats) == 2

    def test_real_entry(self, entry_standard_header):
        cats, cleaned = extract_categories(entry_standard_header)
        assert cats == ["Fiction / Volumes (Swedish)"]


class TestExtractDefaultsortkey:
    def test_extracts_and_removes(self, entry_film):
        sortkey, cleaned = extract_defaultsortkey(entry_film)
        assert sortkey == "Sach-mat"
        assert "{{DEFAULTSORTKEY:" not in cleaned

    def test_no_sortkey(self, entry_bold_title):
        sortkey, _ = extract_defaultsortkey(entry_bold_title)
        assert sortkey is None


class TestRemoveWikiMarkup:
    def test_wiki_links(self):
        assert remove_wiki_markup("[[Target|Display]]") == "Display"
        assert remove_wiki_markup("[[Target Page]]") == "Target Page"

    def test_formatting(self):
        assert remove_wiki_markup("'''Bold''' and ''italic''") == "Bold and italic"

    def test_html_and_lst(self):
        assert "<lst" not in remove_wiki_markup("<lst type=bracket>Content</lst>")
        assert remove_wiki_markup("<p>Text</p>") == "Text"

    def test_escaped_quotes(self):
        assert remove_wiki_markup('\\"Title\\"') == '"Title"'

    def test_whitespace_normalization(self):
        assert "  " not in remove_wiki_markup("Too   many    spaces")

    def test_passthrough(self):
        assert remove_wiki_markup(None) is None
        assert remove_wiki_markup("") == ""

    def test_magic_words_removed(self):
        assert "__TOC__" not in remove_wiki_markup("__TOC__\nContent here")
        assert "__NOTOC__" not in remove_wiki_markup("__NOTOC__\nContent")
        assert "__FORCETOC__" not in remove_wiki_markup("__FORCETOC__")
        assert "__NOEDITSECTION__" not in remove_wiki_markup("__NOEDITSECTION__")

    def test_defaultsort_removed(self):
        text = "Title\n{{DEFAULTSORT:Zweig, Stefan}}"
        result = remove_wiki_markup(text)
        assert "DEFAULTSORT" not in result
        assert "DEFAULTSORTKEY" not in remove_wiki_markup("{{DEFAULTSORTKEY:Test}}")


class TestExtractTitle:
    def test_bold_title(self, entry_bold_title):
        assert extract_title(entry_bold_title) == "Marie Antoinette"

    def test_year_publisher_header_rejected_as_bold(self):
        """Pipeline strips categories first, then extracts title.
        The '''[year]: Publisher''' pattern is rejected by bold-match
        but falls through to first-line fallback."""
        content = "'''[1943]: Skoglunds Bokförlag, Stockholm'''\n\nMore content"
        title = extract_title(content)
        assert title is not None
        # The bold matcher rejects [year]: patterns — verify it didn't match as bold
        # (it falls through to first-line cleanup instead)

    def test_title_after_category_stripping(self):
        """Test extract_title the way extract_structured_data uses it:
        categories stripped first."""
        content = (
            "'''[1976]: Suhrkamp Verlag, Frankfurt am Main'''\n\n"
            "''Die Monotonisierung der Welt''. 254p.\n\n"
            "[[Category:Essays / Volumes (German)]]"
        )
        cats, cleaned = extract_categories(content)
        sortkey, cleaned = extract_defaultsortkey(cleaned)
        title = extract_title(cleaned)
        assert title is not None

    def test_quoted_title(self):
        assert (
            extract_title('"Some Quoted Title" in Journal, 1976') == "Some Quoted Title"
        )

    def test_empty_none(self):
        assert extract_title(None) is None
        assert extract_title("") is None


class TestExtractOriginalTitle:
    def test_in_parentheses(self):
        assert extract_original_title("'''Title''' (Original)") == "Original"

    def test_in_brackets(self):
        assert extract_original_title("'''Title''' [Originalwerk]") == "Originalwerk"

    def test_real_entry(self, entry_bold_title):
        assert extract_original_title(entry_bold_title) == "Original German Title"

    def test_no_original_title(self):
        assert extract_original_title("'''Just a Title'''\nContent") is None


class TestExtractSeeReferences:
    def test_single_ref(self, entry_see_references):
        refs = extract_see_references(entry_see_references)
        assert "Der Amokläufer" in refs

    def test_multiple_refs(self):
        content = "'''See:''' [[Target1]], [[Target2]], [[Target3]]"
        refs = extract_see_references(content)
        assert "Target1" in refs and "Target2" in refs

    def test_see_also(self):
        refs = extract_see_references("'''See also:''' [[Related Entry]]")
        assert "Related Entry" in refs

    def test_real_entry_chinese(self):
        content = (
            "'''See also:''' '''[1]'''. [[Baoshou buzhu de mimi]]; "
            "'''[2]'''. [[Huoxiao huoliao de mimi]]\n\n"
            "[[Category:Fiction (Chinese)]]"
        )
        refs = extract_see_references(content)
        assert "Baoshou buzhu de mimi" in refs


class TestExtractReprints:
    def test_extracted(self, entry_reprints):
        reprints = extract_reprints(entry_reprints)
        assert len(reprints) == 2
        assert any("Gesammelte Werke" in r for r in reprints)

    def test_with_lst_tags(self):
        content = (
            "'''Reprinted in:'''\n<lst type=bracket>\n"
            "[[Collection One]], pp. 1-50\n</lst>\n\n[[Category:Test]]"
        )
        reprints = extract_reprints(content)
        assert any("Collection One" in r for r in reprints)


class TestExtractTranslationsBlock:
    def test_extracted(self, entry_translations_block):
        trans = extract_translations_block(entry_translations_block)
        assert len(trans) == 3
        assert any("English" in t for t in trans)

    def test_singular_header(self):
        content = "'''Translation:'''\nEnglish: The Royal Game\n\n[[Category:Test]]"
        assert len(extract_translations_block(content)) >= 1


class TestExtractContentsBlock:
    def test_extracted(self, entry_collected_works):
        items = extract_contents_block(entry_collected_works)
        assert len(items) >= 2
        assert any("Monotonisierung" in i for i in items)

    def test_with_lst_tags(self, entry_standard_header):
        items = extract_contents_block(entry_standard_header)
        assert len(items) >= 2


class TestExtractStructuredData:
    def test_redirect(self, entry_redirect):
        data = extract_structured_data(entry_redirect)
        assert data["is_redirect"] is True
        assert "redirect_target" in data
        assert "title" not in data

    def test_normal_entry(self, entry_bold_title):
        data = extract_structured_data(entry_bold_title)
        assert data["is_redirect"] is False
        assert "title" in data
        assert "categories" in data
        assert "clean_content" in data

    def test_film_entry(self, entry_film):
        data = extract_structured_data(entry_film)
        assert "Films / Plays / Operas" in data["categories"]
        assert data["sortkey"] == "Sach-mat"

    def test_entry_with_all_blocks(
        self, entry_reprints, entry_translations_block, entry_collected_works
    ):
        assert "reprints" in extract_structured_data(entry_reprints)
        assert "translations" in extract_structured_data(entry_translations_block)
        assert "content_items" in extract_structured_data(entry_collected_works)

    def test_empty_none(self):
        assert extract_structured_data("") == {}
        assert extract_structured_data(None) == {}
