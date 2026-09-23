#!/usr/bin/env python3
"""
Step 3: Parse wiki markup into structured fields.
Extracts titles, years, publishers, locations, languages, translators,
cross-references, reprints, and content items from raw wiki content.

Input:  data/intermediate/02_encoding_fixed.csv
Output: data/intermediate/03_parsed.csv
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (
    PARSED_FIELDS,
    STEP_02_OUTPUT,
    STEP_03_OUTPUT,
    load_csv,
    setup_logging,
    write_csv,
)
from lib.encoding import has_mojibake
from lib.patterns import (
    extract_all_locations,
    extract_all_years,
    extract_language_from_category,
    extract_location,
    extract_page_count,
    extract_publisher,
    extract_translator,
    extract_year,
)
from lib.publications import imprint_publisher, load_attested_places
from lib.vocabulary import LANGUAGE_MAP, language_to_iso
from lib.wiki_parser import extract_structured_data, remove_wiki_markup

log = setup_logging(__name__)

# Section headers that are not real titles (extracted from ==Header== or '''Header:''')
SECTION_HEADER_RE = re.compile(
    r"^(Contents|Volumes|Vol\.\s*\d|German|Italian|French|English|Spanish|Russian|Chinese|"
    r"Japanese|Arabic|Hebrew|Portuguese|Dutch|Swedish|Norwegian|Danish|Finnish|"
    r"Polish|Czech|Hungarian|Romanian|Bulgarian|Croatian|Serbian|Turkish|Greek|"
    r"Albanian|Catalan|Korean|Slovenian|Slovak|Ukrainian|Georgian|Persian|"
    r"First printing|First edition|Reprinted in|See also|See:|Note:|Translations|"
    r"Manuscript|Reviews|Book editions|Printed editions|Excerpts|"
    r"Fischer Editions/Reprints|"
    r"Collected Works / [A-Za-z]+):?\s*",
    re.IGNORECASE,
)

# Shapes of a title candidate that is a bibliographic statement rather than a
# title. The first-line fallback of extract_title returns the whole first line,
# and the corpus writes its quotes escaped (\"), which the quoted-title pattern
# does not read, so an article page yields its full citation ('"Buchmendel".
# See: Book-Mendel', page 586). The source page title is then the title
# (knowledge/data.md, stage 03 in knowledge/pipeline.md). The patterns anchor at
# statement boundaries, so a title that merely contains a word such as "See"
# stays ("Der Flüchtling. Episode vom/am Genfer See", page 782).
NON_TITLE_CLASSES = (
    # "See:" / "See also" opening the line, a sentence, a bracket or following
    # a quoted title ('"Ist die Geschichte gerecht?" See: …', page 6230).
    ("cross-reference", re.compile(r"(?:^[\"'“”‘’\s]*|[.;:?!\]\[\"”’']\s*)See\b")),
    # The container of an article: a closing quote, bracket or parenthesis
    # followed by "in" ('"Title" [gloss] in Journal'), a line opening or ending
    # with "in", a page or column locator ("pp. 280-284", "p. ??"), an issue statement
    # after the place bracket ("[Wien], 32:5", "[Paris], No. 1190") or the
    # "Zweig references" locator of the secondary literature.
    (
        "citation",
        re.compile(
            r"[\"”“\])]\s*,?\s*in\b\s*:?(?:\s|$)|^in\s|\bin\s*:?\s*$"
            r"|\bpp?\.\s*[(\[]?[\d?]|\bcols?\.\s*\d"
            r"|\],\s*(?:No\.\s*\d|\d+:\d+)|\bZweig references?\b"
        ),
    ),
    # A quoted title followed by an editorial note or a description ('"Widerstand
    # der Wirklichkeit" [Individual story]', page 329; '"Deutschlands
    # Janusantlitz". A ca. 1939 typescript …', page 4026).
    ("annotation", re.compile(r"^[\"“][^\"”]+[\"”]\s*(?:\[|\.\s+\S)")),
    # A contribution credit ("Translated by Eugen Relgis", page 212).
    (
        "credit",
        re.compile(
            r"^By\s"
            r"|\b(?:[Tt]ranslat\w+|[Ee]dited|[Ii]llustrat\w+|[Aa]dapted|[Cc]ompiled|"
            r"[Ss]elected|[Pp]roduced|[Ss]ponsored|[Aa]fterword|[Ff]oreword|"
            r"[Pp]reface|[Ii]ntroduction|[Ss]cript|[Dd]rawings)\s+by\b"
        ),
    ),
    # An extent statement ("248p.", "240/(1)p.", "(8)p.", "17 leaves").
    ("extent", re.compile(r"(?<![\w/-])\(?\d+\)?(?:/\(\d+\))?p\.|\b\d+ leaves\b")),
    # "Place: Publisher, YEAR" after a sentence break.
    (
        "imprint",
        re.compile(r"[.)\]]\s+[^\W\d_][^:.\n]{1,40}:\s[^:\n]{2,80}?,\s*\(?\d{4}\)?\b"),
    ),
    # A publication header without a four-digit year ("[No date indicated]:
    # Latino Americana, Ciudad de México", page 608; "[s.a.]: …"), a list
    # number ("[1]", "[I].", "[1]. 1934: Herbert Reichner Verlag, Wien") or a
    # header whose opening bracket the source lost ("11946]: Prometeĭ, Sofija").
    (
        "header",
        re.compile(
            r"^'?\[[^\[\]]{1,60}\]\s*:\s*\S|^\[(?:\d{1,3}|[IVXL]{1,4})\]|^\d{4,5}\]\s*:"
        ),
    ),
    # A label introducing what follows ("Volume:", "Printed in:", "Essays:").
    ("label", re.compile(r":\s*$")),
    # An editorial bracket alone, the original title or a language gloss
    # ("[Magellan. Der Mann und seine Tat]", page 820).
    ("bracket", re.compile(r"^\[[^\[\]]+\]\.?$")),
)
# Section labels the bold-title pattern returns without a colon.
_BARE_LABELS = frozenset(
    {"Volume", "Volumes", "Correspondence", "No Date Indicated", "No date indicated"}
)


def non_title_class(candidate):
    """The class of bibliographic statement a title candidate is, or None."""
    text = remove_wiki_markup(candidate or "")
    if not text:
        return None
    if text in _BARE_LABELS or text in LANGUAGE_MAP:
        return "label"
    for name, pattern in NON_TITLE_CLASSES:
        if pattern.search(text):
            return name
    return None


def derive_main_category(categories):
    """Derive the main (top-level) category from category list."""
    if not categories:
        return ""
    for cat in categories:
        parts = cat.split("/")
        main = parts[0].strip()
        if main:
            return main
    return ""


def process_entry(row, attested_places=None):
    """Process a single entry: parse wiki content and extract metadata."""
    content = row.get("content", "")
    result = {
        "page_id": row["page_id"],
        "page_namespace": row.get("page_namespace", "0"),
        "page_title": row.get("page_title", ""),
        "text_id": row.get("text_id", ""),
        "blob_id": row.get("blob_id", ""),
        "raw_content": content,
    }

    if not content:
        result.update({k: "" for k in PARSED_FIELDS if k not in result})
        # Blanked source page (entry 2979): the BLOB text was emptied at the
        # source, but the page title survives in the page table. Show it with
        # that title rather than as "Untitled" (editor decision).
        page_title = row.get("page_title", "")
        if page_title:
            result["title"] = remove_wiki_markup(page_title)
        return result

    # Parse structured data from wiki content
    parsed = extract_structured_data(content)

    result["is_redirect"] = parsed.get("is_redirect", False)
    result["redirect_target"] = parsed.get("redirect_target", "")

    if result["is_redirect"]:
        result["title"] = parsed.get("redirect_target", "")
        result.update({k: "" for k in PARSED_FIELDS if k not in result})
        return result

    # Title: prefer parsed title, but fall back to page_title.
    # Reject extracted titles that are section headers, [year]: patterns,
    # or full citation text (>200 chars).
    extracted_title = parsed.get("title", "")
    page_title = row.get("page_title", "")
    rejected_for_length = False

    # Edition headers contain metadata; the source page title is authoritative.
    edition_header = r"\[(?:ca\.\s*)?\d{4}"
    if extracted_title and re.match(edition_header, extracted_title, re.IGNORECASE):
        extracted_title = ""

    # Reject: section headers ("Contents:", "Volumes:", "German:", etc.)
    if extracted_title and SECTION_HEADER_RE.match(extracted_title):
        extracted_title = ""

    # Reject: a bibliographic statement (NON_TITLE_CLASSES); the source page
    # title is the title then.
    if extracted_title and page_title and non_title_class(extracted_title):
        extracted_title = ""

    # Reject: full citation text (>200 chars is not a title)
    if extracted_title and len(extracted_title) > 200:
        rejected_for_length = True
        extracted_title = ""

    # Guard: if page_title has encoding artifacts AND the extracted title was
    # only rejected for length (not for being a section header), keep the
    # long extracted title — it's better than a mojibake page_title.
    # has_mojibake covers the common UTF-8-as-Latin-1 case; the C1 range
    # check covers raw control characters the repair cannot touch.
    if (
        rejected_for_length
        and page_title
        and (has_mojibake(page_title) or re.search(r"[\x80-\x9f]", page_title))
    ):
        extracted_title = remove_wiki_markup(parsed.get("title", ""))

    result["title"] = extracted_title or page_title
    # Clean any remaining wiki markup from title (e.g. page_title fallbacks)
    if result["title"]:
        result["title"] = remove_wiki_markup(result["title"])
    result["original_title"] = parsed.get("original_title", "")
    result["sortkey"] = parsed.get("sortkey", "")

    # Categories
    categories = parsed.get("categories", [])
    result["categories"] = (
        json.dumps(categories, ensure_ascii=False) if categories else ""
    )
    result["main_category"] = derive_main_category(categories)

    # Clean content for metadata extraction
    clean = parsed.get("clean_content", "")
    result["clean_content"] = clean

    # Year
    result["year"] = extract_year(content) or ""
    all_years = extract_all_years(content)
    result["all_years"] = json.dumps(all_years) if all_years else ""

    # Publisher: the publication header is the source-bound imprint statement,
    # so it takes precedence over the loose body patterns; those keep the
    # entries that never carried a header.
    result["publisher"] = (
        imprint_publisher(content, attested_places or set())
        or extract_publisher(content)
        or ""
    )

    # Location
    result["location"] = extract_location(content) or ""
    all_locs = extract_all_locations(content)
    result["all_locations"] = (
        json.dumps(all_locs, ensure_ascii=False) if all_locs else ""
    )

    # Language (from categories, then from content)
    lang_name = extract_language_from_category(categories)
    result["language"] = lang_name or ""
    result["language_iso"] = language_to_iso(lang_name) if lang_name else ""

    # Page count
    result["page_count"] = extract_page_count(content) or ""

    # Translator
    result["translator"] = extract_translator(content) or ""

    # Cross-references
    see_also = parsed.get("see_also", [])
    result["see_also"] = json.dumps(see_also, ensure_ascii=False) if see_also else ""

    reprints = parsed.get("reprints", [])
    result["reprints"] = json.dumps(reprints, ensure_ascii=False) if reprints else ""

    translations = parsed.get("translations", [])
    result["translations"] = (
        json.dumps(translations, ensure_ascii=False) if translations else ""
    )

    content_items = parsed.get("content_items", [])
    result["content_items"] = (
        json.dumps(content_items, ensure_ascii=False) if content_items else ""
    )

    return result


def main():
    rows = load_csv(STEP_02_OUTPUT)
    attested_places = load_attested_places()
    log.info(
        "Loaded %d entries, parsing with %d attested places...",
        len(rows),
        len(attested_places),
    )

    results = []
    stats = {
        "redirects": 0,
        "year": 0,
        "publisher": 0,
        "location": 0,
        "language": 0,
        "title": 0,
        "empty": 0,
    }

    for i, row in enumerate(rows):
        parsed = process_entry(row, attested_places)
        results.append(parsed)

        if parsed["is_redirect"]:
            stats["redirects"] += 1
        if parsed["year"]:
            stats["year"] += 1
        if parsed["publisher"]:
            stats["publisher"] += 1
        if parsed["location"]:
            stats["location"] += 1
        if parsed["language"]:
            stats["language"] += 1
        if parsed["title"]:
            stats["title"] += 1
        if not parsed.get("raw_content"):
            stats["empty"] += 1

        if (i + 1) % 1000 == 0:
            log.info(f"  Processed {i + 1}/{len(rows)}...")

    total = len(results)
    log.info(f"Parsing complete: {total} entries")
    log.info(
        f"  Redirects: {stats['redirects']} ({100 * stats['redirects'] / total:.1f}%)"
    )
    log.info(f"  With title: {stats['title']} ({100 * stats['title'] / total:.1f}%)")
    log.info(f"  With year: {stats['year']} ({100 * stats['year'] / total:.1f}%)")
    log.info(
        f"  With publisher: {stats['publisher']} ({100 * stats['publisher'] / total:.1f}%)"
    )
    log.info(
        f"  With location: {stats['location']} ({100 * stats['location'] / total:.1f}%)"
    )
    log.info(
        f"  With language: {stats['language']} ({100 * stats['language'] / total:.1f}%)"
    )

    write_csv(STEP_03_OUTPUT, results, PARSED_FIELDS)
    log.info(f"Output written to {STEP_03_OUTPUT}")


if __name__ == "__main__":
    main()
