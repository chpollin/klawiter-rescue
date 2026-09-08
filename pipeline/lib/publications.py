"""Publication- and contribution-scoped facts for one source page.

A wiki page can describe several publications. The flat record answers with one
value per field, so it can combine one publication's imprint with another
publication's language and describe a publication the source does not document.
This module structures the same source text by publication, so every field
belongs to the publication it was written under.

Data flow: stage 05 reads the stage-04 row, calls ``build_page_publications``
with the source text and the frozen attested-place stock, and projects the
result into the frontend record. The canonical Work/Edition graph (Gate 1) is
unchanged; this layer reuses its exact segmentation through
``lib.editions.segment_page``, so publication identifiers, source slices and
extents agree with the edition graph wherever both cover a page.

Contract decisions (operator specification 2026-09-08, see knowledge/data.md):
- Every value is rule-extracted from the source slice it is reported with. No
  model value and no editor value enters this layer.
- The publications of one page assert co-occurrence on that source page. No
  translation, edition or work relation between them is asserted here.
- Source wording is preserved. An undecidable case becomes an explicit review
  flag instead of a guessed value.
"""

from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from lib.config import LOCATIONS_JSON
from lib.editions import (
    EDITION_HEADER_RE,
    HEADER_RE,
    SERIES_RE,
    parse_header_line,
    segment_page,
)
from lib.patterns import CATEGORY_LANGUAGE_RE, credited_name
from lib.vocabulary import LANGUAGE_MAP, language_to_iso
from lib.wiki_parser import (
    extract_categories,
    extract_defaultsortkey,
    remove_wiki_markup,
)

ROLE_VOCABULARY = ("translator", "editor", "illustrator", "contributor")
PAGE_KINDS = ("author-page", "edition-page", "single-publication")

# A credit is read only where the source names a contribution role. A label
# without one of these stems ("Cover design by") stays unread rather than
# entering the record as an untyped contributor.
_ROLE_STEMS = (
    ("translat", "translator"),
    ("edited", "editor"),
    ("editing", "editor"),
    ("illustrat", "illustrator"),
    ("foreword", "contributor"),
    ("afterword", "contributor"),
    ("preface", "contributor"),
    ("introduc", "contributor"),
    ("annotat", "contributor"),
    ("compil", "contributor"),
    ("select", "contributor"),
    ("revis", "contributor"),
    ("adapt", "contributor"),
    ("arrang", "contributor"),
)

# A credit label opens a line, a sentence or a bracket. Anchoring it there keeps
# a mid-sentence "…and translated into French by" out of the credit list.
_CREDIT_RE = re.compile(
    r"(?:^|(?<=\. )|(?<=\[))([^.\[\]\n;]{2,80}?\bby)\s+", re.MULTILINE
)
_CREDIT_STOP_TOKENS = frozenset(
    {"A", "An", "The", "This", "These", "Contains", "See", "In", "Written"}
)
_LANGUAGE_HEADING_RE = re.compile(
    r"^'''\s*([A-Za-z][A-Za-z\- ]{1,20}?)\s*'''\s*$", re.MULTILINE
)
_LIST_BLOCK_RE = re.compile(r"<lst[^>]*>(.*?)</lst>", re.DOTALL)
_CATEGORY_LINK_RE = re.compile(r"\[\[Category:[^\]]+\]\]")
_EXTENT_RE = re.compile(r"(?<!\()\b(\d+)(?:/\((\d+)\))?p\.")
_UNNUMBERED_RE = re.compile(r"/\((\d+)\)p\.")
_EDITION_STATEMENT_RE = re.compile(
    r"\b((?:\d{1,2}(?:st|nd|rd|th)|New|Newly|Revised)(?:\s+[a-z]+){0,2}\s+edition)\b"
)
_SERIES_LABEL_RE = re.compile(r"\[\s*Series:\s*([^\[\]\n]+)\]")
_BRACKET_RE = re.compile(r"\[([^\[\]\n]{2,200})\]")
_SERIES_VOLUME_RE = re.compile(r",\s*(\d{1,4})\s*$")
_TITLE_ITALIC_RE = re.compile(r"''(.+?)''")
_TITLE_QUOTED_RE = re.compile(r'\\?"(.+?)\\?"')
_CONTAINER_RE = re.compile(r"\bin\s+''(.+?)''")
_CONTAINER_TAIL_RE = re.compile(
    r"\[([^\[\]\n]{2,60})\]\s*,\s*([^,\[\]\n]{1,20})\s*\[\d{4}\]\s*,\s*pp?\.\s*([\d()\-–]+)"
)
_URL_RE = re.compile(r"https?://\S+")
_URL_NOTE_RE = re.compile(r"\[([^\[\]\n]{2,60})\]\s*:?\s*$")
_CONTRIBUTION_PAGES_RE = re.compile(r",\s*pp?\.\s*([\d()\-–]+)\s*$")
_CONTRIBUTION_NOTE_RE = re.compile(r"^(.*?)\s*\[(.+)\]$", re.DOTALL)
_PAGE_NUMBER_RE = re.compile(r"\d+")
_NAME_SHAPED_RE = re.compile(
    r"^[^\W\d_][^\W\d_'’.\- ]*(?:[ ]+(?:[^\W\d_]\.|[^\W\d_][^\W\d_'’.\-]*))+$"
)

# Minimum similarity for reading a spelling as a variant of a credited name.
# Combined with an identical token count and an identical final token, so a
# different person with a similar name is not folded into one identity.
_VARIANT_SIMILARITY = 0.85

# Fields whose provenance the publication record reports individually.
_PROVENANCE_EXCLUDED = frozenset({"id", "provenance", "sourceSlice", "reviewFlags"})


def load_attested_places() -> set[str]:
    """Place names attested by the frozen, reviewed location stock.

    The stock is the Gate-2 input docs/data/locations.json, refrozen only by the
    gated reconciliation tool. It is the evidence that lets a header with three
    or more comma segments be split into a publisher and several places; from
    the string alone that split is not decidable.
    """
    document = json.loads(Path(LOCATIONS_JSON).read_text(encoding="utf-8"))
    return set(document)


def _flat(value: str) -> str:
    return " ".join(value.split())


def _unique(values: list) -> list:
    return list(dict.fromkeys(values))


def _put(target: dict, key: str, value, cast=None) -> None:
    """Set a field only where the source supports a value; empty stays absent."""
    if value is None or value == "" or value == [] or value == {}:
        return
    target[key] = cast(value) if cast else value


def _mask(text: str) -> str:
    """Blank the regions that carry no publication-level statement.

    Contents lists hold contribution-scoped credits and category links hold wiki
    infrastructure; both would otherwise be read as publication credits.
    Blanking rather than deleting keeps every source offset intact.
    """

    def blank(match: re.Match[str]) -> str:
        return " " * (match.end() - match.start())

    return _CATEGORY_LINK_RE.sub(blank, _LIST_BLOCK_RE.sub(blank, text))


def _language_scopes(text: str) -> list[tuple[int, str]]:
    """Offsets of the bold language headings that scope the following blocks."""
    scopes = []
    for match in _LANGUAGE_HEADING_RE.finditer(text):
        name = match.group(1).strip()
        if name in LANGUAGE_MAP:
            scopes.append((match.start(), name))
    return scopes


def _language_at(scopes: list[tuple[int, str]], start: int) -> str | None:
    """The language heading a block stands under, that is the last one above it."""
    enclosing = [name for offset, name in scopes if offset < start]
    return enclosing[-1] if enclosing else None


def _category_languages(categories: list[str]) -> list[str]:
    names = []
    for category in categories:
        match = CATEGORY_LANGUAGE_RE.search(category)
        if match and match.group(1) in LANGUAGE_MAP and match.group(1) not in names:
            names.append(match.group(1))
    return names


def _header_body(header_line: str) -> str:
    """The imprint statement of a header line, in its source wording."""
    stripped = header_line.strip()
    body = stripped[3:].lstrip() if stripped.startswith("'''") else stripped
    body = body.split("'''", 1)[0]
    match = HEADER_RE.match(body)
    if not match:
        return ""
    field_text = match.group(2).strip()
    series = SERIES_RE.search(field_text)
    if series:
        field_text = field_text[: series.start()]
    return _flat(field_text.rstrip("'").strip())


def _split_imprint(
    imprint: str,
    gate1_publisher: str | None,
    gate1_place: str | None,
    attested: set[str],
) -> tuple[str | None, list[str], dict | None]:
    """Separate publisher and places, keeping the source wording of both.

    Two comma segments are the ratified Gate-1 split and stay as they are. With
    three or more segments the string alone does not say where the publisher
    ends, so the split is made only where the reviewed location stock attests a
    trailing run of two or more places. Otherwise the Gate-1 value is kept and
    the undecided segmentation is reported as a review flag.
    """
    segments = [_flat(part) for part in imprint.split(",") if part.strip()]
    places = [gate1_place] if gate1_place else []
    if len(segments) < 3:
        return gate1_publisher, places, None
    run = 0
    while run < len(segments) - 1 and segments[len(segments) - 1 - run] in attested:
        run += 1
    if run >= 2:
        return ", ".join(segments[:-run]), segments[-run:], None
    flag = {
        "code": "imprint-segments-unresolved",
        "detail": (
            "The publication header carries more than two comma segments; the "
            "boundary between publisher and place is not decidable from the "
            f"source wording: {'; '.join(segments)}"
        ),
    }
    return gate1_publisher, places, flag


def _title(block_body: str) -> str | None:
    """The publication title, the first italic or quoted string of the block.

    Whichever notation comes first wins, so an article title in quotes is not
    displaced by the italic journal name that follows it.
    """
    candidates = [
        match
        for match in (
            _TITLE_ITALIC_RE.search(block_body),
            _TITLE_QUOTED_RE.search(block_body),
        )
        if match
    ]
    if not candidates:
        return None
    title = _flat(min(candidates, key=lambda m: m.start()).group(1))
    # Stray quote markup can leave a title of punctuation alone, which names
    # nothing; the source then documents no title for this publication.
    return title if re.search(r"\w", title) else None


def _extent(page_count_raw: str | None, numbered: int | None) -> dict | None:
    """Extent in the original source notation beside the normalized number."""
    if not page_count_raw:
        return None
    extent: dict = {"raw": page_count_raw}
    if numbered is not None:
        extent["numbered"] = numbered
    unnumbered = _UNNUMBERED_RE.search(page_count_raw)
    if unnumbered:
        extent["unnumbered"] = int(unnumbered.group(1))
    return extent


def _series(block_body: str) -> str | None:
    """The series statement, either explicitly labelled or the bracket that
    closes the extent statement on the same source line."""
    labelled = _SERIES_LABEL_RE.search(block_body)
    if labelled:
        return _flat(labelled.group(1))
    extent = _EXTENT_RE.search(block_body)
    if not extent:
        return None
    tail = block_body[extent.end() :]
    line_end = tail.find("\n")
    line = tail if line_end < 0 else tail[:line_end]
    bracket = _BRACKET_RE.search(line)
    if not bracket or bracket.start() > 60:
        return None
    content = bracket.group(1)
    if _EXTENT_RE.search(content) or content.startswith("["):
        return None
    return _flat(content)


def _series_volume(series: str | None) -> str | None:
    if not series:
        return None
    match = _SERIES_VOLUME_RE.search(series)
    return match.group(1) if match else None


def _series_note(block_body: str, series: str | None) -> str | None:
    """Prose that follows the series statement on the same line, such as the
    note that a volume was originally a thesis."""
    if not series:
        return None
    bracket = next(
        (
            match
            for match in _BRACKET_RE.finditer(block_body)
            if _flat(match.group(1)).endswith(series)
        ),
        None,
    )
    if bracket is None:
        return None
    tail = block_body[bracket.end() :]
    line_end = tail.find("\n")
    line = tail if line_end < 0 else tail[:line_end]
    note = _flat(line.lstrip(". "))
    return note if len(note) >= 20 else None


def _container(block_body: str) -> dict | None:
    """Journal, place, issue and pages of an article-shaped publication."""
    match = _CONTAINER_RE.search(block_body)
    if not match:
        return None
    container: dict = {"title": _flat(match.group(1))}
    tail = _CONTAINER_TAIL_RE.search(block_body, match.end())
    if tail:
        container["place"] = _flat(tail.group(1))
        container["issue"] = _flat(tail.group(2))
        container["pages"] = _flat(tail.group(3))
    return container


def _online(block_body: str) -> dict | None:
    """An online address with the qualification the source gives it."""
    match = _URL_RE.search(block_body)
    if not match:
        return None
    online = {"url": match.group(0).rstrip(".,;")}
    head = block_body[: match.start()].rstrip()
    note = _URL_NOTE_RE.search(head[head.rfind("\n") + 1 :])
    if note:
        online["note"] = _flat(note.group(1))
    return online


def _credits(text: str) -> list[dict]:
    """Read the credited roles a source passage states, with their labels."""
    credits: list[dict] = []
    for match in _CREDIT_RE.finditer(text):
        label = _flat(match.group(1))
        tokens = label.split()
        if len(tokens) > 8 or tokens[0] in _CREDIT_STOP_TOKENS:
            continue
        if not tokens[0][:1].isupper():
            continue
        lowered = label.lower()
        role = next((role for stem, role in _ROLE_STEMS if stem in lowered), None)
        if role is None:
            continue
        name = credited_name(text, match.end())
        if not name:
            continue
        credit = {"role": role, "name": name, "creditLabel": label}
        if credit not in credits:
            credits.append(credit)
    return credits


def _contributions(section_text: str) -> list[dict]:
    """Parse the contents lines of a publication into scoped contributions."""
    contributions = []
    for list_block in _LIST_BLOCK_RE.finditer(section_text):
        for raw_line in list_block.group(1).splitlines():
            line = raw_line.strip()
            if len(line) < 3:
                continue
            scope: dict = {}
            pages = _CONTRIBUTION_PAGES_RE.search(line)
            if pages:
                scope["pages"] = _flat(pages.group(1))
                numbers = [int(n) for n in _PAGE_NUMBER_RE.findall(pages.group(1))]
                if numbers:
                    scope["pageStart"] = numbers[0]
                    scope["pageEnd"] = numbers[-1]
                line = line[: pages.start()].strip()
            note = _CONTRIBUTION_NOTE_RE.match(line)
            if note:
                title = _flat(note.group(1))
                scope["note"] = _flat(note.group(2))
                credits = _credits(f"[{note.group(2)}]")
                if credits:
                    scope["credits"] = credits
            else:
                title = _flat(line)
            contribution = {"title": title, **scope} if title else scope
            if contribution:
                contributions.append(contribution)
    return contributions


def _pagination_flag(extent: dict | None, contributions: list[dict]) -> dict | None:
    """Report contents that run past the stated numbered extent."""
    numbered = (extent or {}).get("numbered")
    ends = [c["pageEnd"] for c in contributions if "pageEnd" in c]
    if numbered is None or not ends or max(ends) <= numbered:
        return None
    return {
        "code": "contents-pagination-exceeds-extent",
        "detail": (
            f"The contents end at page {max(ends)}, the stated numbered extent "
            f"is {numbered}."
        ),
    }


def _bracket_name_candidates(text: str) -> list[tuple[str, str]]:
    """Name-shaped strings inside brackets, with the source line they stand in."""
    candidates = []
    for match in _BRACKET_RE.finditer(text):
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        context = _flat(text[line_start : line_end if line_end >= 0 else len(text)])
        for segment in match.group(1).split(","):
            value = _flat(segment)
            if _NAME_SHAPED_RE.match(value):
                candidates.append((value, context))
    return candidates


def _name_variants(text: str, credited: list[str]) -> list[dict]:
    """Spellings that differ slightly from a credited name, held unresolved.

    The source is not corrected: the variant is recorded with the line it stands
    in, and no identity between the two spellings is asserted.
    """
    variants: list[dict] = []
    seen: set[str] = set()
    for value, context in _bracket_name_candidates(text):
        if value in credited or value in seen:
            continue
        for name in credited:
            if len(value.split()) != len(name.split()):
                continue
            if value.split()[-1] != name.split()[-1]:
                continue
            if SequenceMatcher(None, value, name).ratio() < _VARIANT_SIMILARITY:
                continue
            seen.add(value)
            variants.append(
                {
                    "name": value,
                    "variantOf": name,
                    "status": "unresolved",
                    "sourceContext": context,
                    "provenance": "regex",
                }
            )
            break
    return variants


def _page_kind(categories: list[str], publication_count: int) -> str:
    """The page type the card labels by, read from the source category path.

    A 'Secondary Literature / Authors' page is indexed under an author name, so
    its page title is a person and its publications are independent works.
    """
    if any("Authors" in category.split("(")[0] for category in categories):
        return "author-page"
    return "edition-page" if publication_count > 1 else "single-publication"


def _delivered_form(block: str) -> str:
    """The block as it appears in the delivered bibliographic text.

    Runs the same three steps stage 03 applies to the whole page, so the result
    is a literal substring of that page's delivered text wherever the block
    survives cleaning unchanged.
    """
    without_categories = extract_categories(block)[1]
    without_sortkey = extract_defaultsortkey(without_categories)[1]
    return remove_wiki_markup(without_sortkey)


def _delivered_span(block: str, delivered: str) -> tuple[int, int] | None:
    """Offsets of a publication block inside the delivered text.

    Returns None where the block does not appear or appears more than once, so
    an interface highlighting the passage never points at the wrong one. The
    raw-text offsets in sourceSlice stay the evidence anchor either way.
    """
    needle = _delivered_form(block)
    if not needle or not delivered:
        return None
    first = delivered.find(needle)
    if first < 0 or delivered.find(needle, first + 1) >= 0:
        return None
    return first, first + len(needle)


def _places_of(publication: dict) -> list[str]:
    """Every place a publication was issued at, for the page-level place facet.

    An article carries its place in the container statement rather than in an
    imprint header; without it the article would not be findable under the place
    the source names for it.
    """
    container_place = publication.get("container", {}).get("place")
    return [
        *publication.get("places", []),
        *([container_place] if container_place else []),
    ]


def _credited_names(publications: list[dict]) -> list[str]:
    names: list[str] = []
    for publication in publications:
        for scope in (publication, *publication.get("contributions", [])):
            for credit in scope.get("credits", []):
                if credit["name"] not in names:
                    names.append(credit["name"])
    return names


def _attach_contributions(
    publications: list[tuple[int, dict]], sections: list[dict], text: str
) -> None:
    """Attach a contents section to the publication block it follows."""
    for section in sections:
        if section["heading"].strip().lower() != "contents":
            continue
        owner = None
        for start, publication in publications:
            if start < section["start"]:
                owner = publication
        if owner is None:
            continue
        contributions = _contributions(text[section["start"] : section["end"]])
        if contributions:
            owner.setdefault("contributions", []).extend(contributions)


def _build_publication(
    edition: dict,
    block: str,
    start: int,
    end: int,
    language: str | None,
    attested: set[str],
    delivered: str,
) -> dict:
    """One publication record, built only from its own source block."""
    header_line = edition["klawiter:headerLine"]
    body = block[len(header_line) :] if block.startswith(header_line) else block
    masked_body = _mask(body)

    imprint = _header_body(header_line)
    publisher, places, imprint_flag = _split_imprint(
        imprint,
        edition.get("schema:publisher"),
        edition.get("schema:locationCreated"),
        attested,
    )
    series = _series(masked_body)

    publication: dict = {
        "id": f"klawiter:publication/{edition['@id'].rsplit('/', 1)[1]}"
    }
    _put(publication, "year", edition.get("schema:datePublished"), int)
    _put(publication, "yearRaw", edition.get("klawiter:yearRaw"))
    _put(publication, "title", _title(masked_body))
    _put(publication, "imprint", imprint)
    _put(publication, "publisher", publisher)
    _put(publication, "places", places)
    _put(publication, "language", language)
    _put(publication, "languageCode", language_to_iso(language) if language else None)
    _put(publication, "editionStatement", _edition_statement(masked_body))
    _put(
        publication,
        "extent",
        _extent(
            edition.get("klawiter:pageCountRaw"), edition.get("schema:numberOfPages")
        ),
    )
    _put(publication, "series", series)
    _put(publication, "seriesVolume", _series_volume(series))
    _put(publication, "note", _series_note(masked_body, series))
    _put(publication, "credits", _credits(masked_body))
    _put(publication, "container", _container(masked_body))
    _put(publication, "online", _online(masked_body))
    source_slice = {
        "start": start,
        "end": end,
        "sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
    }
    span = _delivered_span(block, delivered)
    if span:
        source_slice["textStart"], source_slice["textEnd"] = span
    publication["sourceSlice"] = source_slice

    flags = []
    if "missing-location" in edition["klawiter:reviewFlags"]:
        flags.append(
            {
                "code": "missing-location",
                "detail": "The publication header names no place of publication.",
            }
        )
    if imprint_flag:
        flags.append(imprint_flag)
    publication["_flags"] = flags
    return publication


def _edition_statement(block_body: str) -> str | None:
    without_brackets = _BRACKET_RE.sub(" ", block_body)
    match = _EDITION_STATEMENT_RE.search(without_brackets)
    return _flat(match.group(1)) if match else None


def imprint_publisher(text: str, attested_places: set[str]) -> str | None:
    """The publisher the flat compatibility field takes from the source.

    It is the publisher of the first publication whose header also names a
    place, split exactly as the publication layer splits it, so the flat field
    and the layer never disagree. A header without a place is left alone,
    because its single segment can equally be a publisher, a place or a country
    ("[1984]: Czechoslovakia" on a film page).
    """
    if not text:
        return None
    for line in text.splitlines():
        if not EDITION_HEADER_RE.match(line):
            continue
        imprint = _header_body(line)
        for fields in parse_header_line(line):
            publisher, places, _ = _split_imprint(
                imprint, fields.publisher, fields.location, attested_places
            )
            if publisher and places:
                return publisher
    return None


def build_page_publications(
    page_id: int,
    text: str,
    page_title: str,
    categories: list[str],
    attested_places: set[str],
    delivered_text: str = "",
) -> dict:
    """Structure one source page by publication and contribution.

    Returns an empty dict for a page whose source carries no publication header;
    that absence is the honest statement, not an empty publication.
    """
    if not text:
        return {}
    segmented = segment_page(page_id, text, page_title)
    editions = segmented["editions"]
    if not editions:
        return {}

    selectors = {
        annotation["oa:hasBody"]["@id"]: annotation["oa:hasTarget"]["oa:hasSelector"]
        for annotation in segmented["annotations"]
    }
    scopes = _language_scopes(text)
    category_languages = _category_languages(categories)

    built: list[tuple[int, dict]] = []
    for edition in editions:
        selector = selectors[edition["@id"]]
        start, end = selector["oa:start"], selector["oa:end"]
        language = _language_at(scopes, start)
        if language is None and len(category_languages) == 1:
            language = category_languages[0]
        built.append(
            (
                start,
                _build_publication(
                    edition,
                    text[start:end],
                    start,
                    end,
                    language,
                    attested_places,
                    delivered_text,
                ),
            )
        )

    _attach_contributions(built, segmented["unsegmentedSections"], text)

    publications = []
    for _, publication in built:
        flags = publication.pop("_flags")
        pagination = _pagination_flag(
            publication.get("extent"), publication.get("contributions", [])
        )
        if pagination:
            flags.append(pagination)
        _put(publication, "reviewFlags", flags)
        publication["provenance"] = {
            key: "regex" for key in publication if key not in _PROVENANCE_EXCLUDED
        }
        publications.append(publication)

    return {
        "pageKind": _page_kind(categories, len(publications)),
        "publicationCount": len(publications),
        "publications": publications,
        "publicationYears": _unique([p["year"] for p in publications if "year" in p]),
        "publicationPlaces": _unique(
            [place for p in publications for place in _places_of(p)]
        ),
        "publicationLanguages": _unique(
            [p["language"] for p in publications if "language" in p]
        ),
        "nameVariants": _name_variants(text, _credited_names(publications)),
    }
