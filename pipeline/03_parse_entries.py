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
    find_language_category,
    find_location,
    find_page_count,
    find_publisher,
    find_translator,
    find_year,
    location_occurrences,
    year_occurrences,
)
from lib.publications import (
    first_publication_fields,
    load_attested_places,
    unbound_flat_fields,
)
from lib.value_spans import category_links, cleaned_form, raw_span
from lib.vocabulary import LANGUAGE_MAP, language_to_iso
from lib.wiki_parser import (
    blank_translations_block,
    extract_structured_data,
    find_original_title,
    find_see_references,
    find_title,
    remove_wiki_markup,
    section_item_spans,
)

log = setup_logging(__name__)

# Main categories of Zweig's own works, whose translations bracket the
# original title after their title statement.
ORIGINAL_TITLE_CATEGORIES = frozenset(
    {"Fiction", "Essays", "Historical Studies", "Poetry", "Dramas"}
)

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
# (knowledge/data.md, stage 03 in knowledge/pipeline-architecture.md). The
# patterns anchor at statement boundaries, so a title that merely contains a word such as "See"
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
    # A quoted contribution title followed by the work it belongs to
    # ('"Preface" to The Jewish Contribution to Civilization.', page 6991).
    ("contribution", re.compile(r"^[\"“][^\"”]+[\"”]\s+to\s")),
    # An archival holdings statement: a shelf mark, a count of letters or
    # postcards, or a manuscript page count opening the line ("2 volumes.
    # Shelf number Acc. 2011/3", page 2980; "26 letters and 6 postcards", page
    # 3657; "1 page, undated handwritten text", page 1768).
    (
        "holdings",
        re.compile(
            r"\b[Ss]helf (?:number|mark)\b|\b\d+ (?:letters?|postcards?)\b"
            r"|^\d+ pages?,"
        ),
    ),
    # A postal address ("Antiquariat Richard Husslein, Postfach 1525, D-82144
    # Planegg", page 2712).
    ("address", re.compile(r"\bPostfach \d+|\b[A-Z]{1,2}-\d{4,5} [^\W\d_]")),
    # An academic paper statement after the title ("… 'Schachnovelle'.
    # Seminararbeit. Institut für Germanistik", page 3818).
    (
        "thesis",
        re.compile(
            r"\.\s+(?:Seminararbeit|Hausarbeit|Diplomarbeit|Magisterarbeit|"
            r"Masterarbeit|Bachelorarbeit|Dissertation|Habilitationsschrift|"
            r"(?:Doctoral |Master's |Ph\.?D\.? )?[Tt]hesis)\b"
        ),
    ),
    # A web address alone (page 6807).
    ("url", re.compile(r"^(?:https?://|www\.)\S+$")),
    # A compiler's note: an opening note formula ("Taken from the volume …",
    # page 187; "The following editions of …", page 6416), an abbreviation key
    # ("KH = Kelsea M. Halloran", page 3677) or a descriptive sentence after a
    # name ("…, ca. 1210 - ca. 1260. The sonnet was written ca. 1230", page 3262).
    (
        "note",
        re.compile(
            r"^(?:Taken from|The following)\b|^[A-Z]{1,4} = "
            r"|\.\s+(?:The|This|These)\s+\w+\s+(?:is|are|was|were)\s"
        ),
    ),
)
# Section labels the bold-title pattern returns without a colon.
_BARE_LABELS = frozenset(
    {"Volume", "Volumes", "Correspondence", "No Date Indicated", "No date indicated"}
)


def _category_labels(categories):
    """Each category name and the language its trailing bracket names."""
    labels = set()
    for category in categories:
        labels.add(category)
        m = re.search(r"\(([^()]+)\)\s*$", category)
        if m:
            labels.add(m.group(1).strip())
    return labels


def _credits_page_person(text, page_title):
    """Whether the line opens with the person an author page is titled by.

    An author page is titled "Surname, Forename"; a first line naming that
    person in natural order credits the work below it ("Christina-Maria
    Hochreiter and Armin Eidherr.", page 6060).
    """
    m = re.fullmatch(r"([^,/]+),\s*([^,/]+)", page_title or "")
    if not m:
        return False
    name = f"{m.group(2).strip()} {m.group(1).strip()}"
    return text == name or text.startswith((name + " ", name + ".", name + ","))


# A repository holding a correspondent's letters, named at the head of a
# Correspondence page ("The Stefan Zweig Collection", "Kungliga Biblioteket").
_REPOSITORY_NAME_RE = re.compile(r"\b(?:Collection|Papers?|Nachlass|Archives?)$")


def _names_repository(text, page_title, categories):
    """Whether the line names the archive holding a correspondence.

    A Correspondence page is titled by the correspondent ("Hasenclever,
    Walter"); a bold line above the letter list naming a collection or
    archive names its repository, not a title (page 3436).
    """
    if not any("Correspondence" in category for category in categories):
        return False
    if not re.fullmatch(r"([^,/]+),\s*([^,/]+)", page_title or ""):
        return False
    return bool(_REPOSITORY_NAME_RE.search(text))


def non_title_class(candidate, page_title="", categories=()):
    """The class of bibliographic statement a title candidate is, or None.

    page_title and categories let a candidate be read against its own page:
    a bold line restating a page category or its language ("Essays / Volumes
    (German)", page 162; "Bosnian", page 1855) labels the block below it.
    """
    text = remove_wiki_markup(candidate or "")
    if not text:
        return None
    if text in _BARE_LABELS or text in LANGUAGE_MAP:
        return "label"
    if text in _category_labels(categories):
        return "label"
    if _credits_page_person(text, page_title):
        return "credit"
    if _names_repository(text, page_title, categories):
        return "holdings"
    for name, pattern in NON_TITLE_CLASSES:
        if pattern.search(text):
            return name
    return None


def derive_main_category(categories):
    """Derive the main (top-level) category from category list."""
    found = _main_category(categories)
    return found[0] if found else ""


def _main_category(categories):
    """The main category with the index of the category it is read from."""
    for index, cat in enumerate(categories or []):
        main = cat.split("/")[0].strip()
        if main:
            return main, index
    return None


def _first(found):
    return found[0] if found else None


def _scalar_spans(found_by_field, spans):
    """Record the raw span of each found (value, span) pair under its field."""
    for field, found in found_by_field.items():
        if found:
            spans[field] = list(found[1])


def flat_field_spans(content, result, categories, title_from_text):
    """The raw spans stage 03 read the page-level values from, for the
    field_spans column: a field's span, or for a list field its items, each
    as [value, start, end]. Readers of the cleaned text (title, original
    title, references, sections) are mapped back to raw offsets."""
    cleaned = cleaned_form(content)

    def raw(span):
        return list(raw_span(cleaned, *span))

    spans = {}
    title = find_title(cleaned.text) if title_from_text else None
    if title:
        spans["title"] = raw(title[1])
    if result.get("original_title"):
        original = find_original_title(cleaned.text)
        if original:
            spans["original_title"] = raw(original[1])
    links = category_links(content)
    spans["categories"] = [[name, start, end] for name, start, end in links]
    language = find_language_category(categories)
    if language:
        spans["language"] = list(links[language[1]][1:])
    main = _main_category(categories)
    if main:
        spans["main_category"] = list(links[main[1]][1:])
    spans["see_also"] = [
        [ref, *raw(span)] for ref, span in find_see_references(cleaned.text)
    ]
    for field, items in section_item_spans(cleaned.text).items():
        spans[field] = [[item, *raw(span)] for item, span in items]
    spans["all_years"] = [
        [str(year), *span]
        for year, found in year_occurrences(content).items()
        for span in found
    ]
    spans["all_locations"] = [
        [place, *span]
        for place, found in location_occurrences(content).items()
        for span in found
    ]
    return {field: value for field, value in spans.items() if value}


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
    if (
        extracted_title
        and page_title
        and non_title_class(extracted_title, page_title, parsed.get("categories", []))
    ):
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

    # Year, publisher and extent: on a page with a publication layer they are
    # the first publication's, so the three describe one publication; the body
    # patterns keep the entries that never carried a header.
    scoped = first_publication_fields(
        int(row["page_id"]),
        content,
        page_title,
        categories,
        attested_places or set(),
    )
    result["publication_scoped"] = "true" if scoped is not None else ""
    spans = {}
    if scoped is not None:
        result["year"] = scoped["year"] or ""
        result["publisher"] = scoped["publisher"] or ""
        result["page_count"] = scoped["page_count"] or ""
        spans.update(
            {
                field: list(span)
                for field, span in scoped["spans"].items()
                if result[field]
            }
        )
    else:
        found = {
            "year": find_year(content),
            "publisher": find_publisher(content),
            "page_count": find_page_count(content),
        }
        for field, reading in found.items():
            result[field] = _first(reading) or ""
        _scalar_spans(found, spans)
    all_years = extract_all_years(content)
    result["all_years"] = json.dumps(all_years) if all_years else ""

    # Location
    location = find_location(content)
    result["location"] = _first(location) or ""
    _scalar_spans({"location": location}, spans)
    all_locs = extract_all_locations(content)
    result["all_locations"] = (
        json.dumps(all_locs, ensure_ascii=False) if all_locs else ""
    )

    # Language (from categories, then from content)
    lang_name = _first(find_language_category(categories))
    result["language"] = lang_name or ""
    result["language_iso"] = language_to_iso(lang_name) if lang_name else ""

    # The bracket after the title statement gives the original title only on a
    # translation of one of Zweig's works. On a German page it names a cycle or
    # series ("[Die Kette. Ein Novellenkreis. Der 2. Ring]", page 3), and on
    # secondary literature, correspondence and collections it glosses the
    # title in English ("[Stefan Zweig, 1881, died 1942, Austria]", page 4512).
    translated_work = (
        lang_name
        and lang_name != "German"
        and result["main_category"] in ORIGINAL_TITLE_CATEGORIES
    )
    result["original_title"] = (
        parsed.get("original_title", "") if translated_work else ""
    )

    # Translator. On a German page the credits of the translations section
    # belong to the translations it lists ("Translated by Mien Labberton" of the
    # Dutch translation on page 272), never to the German original.
    translator_text = content
    if lang_name == "German":
        translator_text = blank_translations_block(content)
    translator = find_translator(translator_text)
    result["translator"] = _first(translator) or ""
    _scalar_spans({"translator": translator}, spans)

    # On a page without a publication header the body patterns read place,
    # publisher and translator from anywhere in the text. A value stays only
    # where the page's first statement carries it in a position a rule reads;
    # otherwise the field is a gap, because a value from another passage
    # describes another publication (a reprint, a translation, a note).
    result["unbound_fields"] = ""
    if scoped is None:
        unbound = unbound_flat_fields(content, result)
        for field in unbound:
            result[field] = ""
            spans.pop(field, None)
        if unbound:
            result["unbound_fields"] = json.dumps(unbound)

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

    spans.update(flat_field_spans(content, result, categories, bool(extracted_title)))
    result["field_spans"] = json.dumps(spans, ensure_ascii=False) if spans else ""

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
