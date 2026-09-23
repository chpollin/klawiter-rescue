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
    HeaderFields,
    Imprint,
    parse_header_line,
    protected_mask,
    segment_page,
)
from lib.patterns import ABSENCE_MARKS, CATEGORY_LANGUAGE_RE, credited_name
from lib.vocabulary import LANGUAGE_MAP, language_to_iso
from lib.wiki_parser import (
    extract_categories,
    extract_defaultsortkey,
    remove_wiki_markup,
)

ROLE_VOCABULARY = ("author", "translator", "editor", "illustrator", "contributor")
PAGE_KINDS = ("author-page", "edition-page", "single-publication")

# A credit is read only where the source names a contribution role. A label
# without one of these stems ("Cover design by") stays unread rather than
# entering the record as an untyped contributor.
_ROLE_STEMS = (
    ("translat", "translator"),
    # Adapting a text into another language is translating it; the generic
    # "adapt" below stays a contribution.
    ("adapted into", "translator"),
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
# Labels that credit the publication itself to its author. They open with a
# stop token, so they are named whole rather than read by the role stems; the
# graphic novel on pages 4916 and 5110 is the case the corpus holds.
_AUTHOR_LABELS = frozenset({"A graphic novel by"})
# A second credit chained onto a name without a sentence break ("A graphic
# novel by <author> adapted into German by <translator>"). Without it the first
# name runs on into the label of the second credit.
_CHAINED_CREDIT_RE = re.compile(
    r"([^\W\d_][^\W\d_'’.\-]*(?: [^\W\d_][^\W\d_'’.\-]*){0,3}) "
    r"(adapted into [A-Z][a-z]+ by)\s+"
)
# A "See" cross-reference ends the statement a series bracket closes: the
# brackets of "See: [[Le Joueur d'échecs]] [2015]" are the target page and its
# date, not a series. A wiki link without "See" can name the set a volume
# belongs to ("[[Kassette VI: …]]. Vol. 2") and stays readable as a series.
_CROSS_REFERENCE_RE = re.compile(r"\bSee\b")
# The one "See" reference that does state membership: the target is a
# multi-volume set and a volume number follows it ("See: [[Z díla Stefana
# Zweiga]], Vol. 7"), with an optional bracketed qualifier in between.
_SET_REFERENCE_RE = re.compile(
    r"\bSee:?\s*\[\[([^\[\]\n]+)\]\]\s*(?:\[[^\[\]\n]*\])?[.,]?\s*Vol\.\s*([0-9IVXLC]+)\b"
)
_LANGUAGE_HEADING_RE = re.compile(
    r"^'''\s*([A-Za-z][A-Za-z\- ]{1,20}?)\s*'''\s*$", re.MULTILINE
)
_LIST_BLOCK_RE = re.compile(r"<lst[^>]*>(.*?)</lst>", re.DOTALL)
_CATEGORY_LINK_RE = re.compile(r"\[\[Category:[^\]]+\]\]")
_EXTENT_RE = re.compile(r"(?<!\()\b(\d+)(?:/\((\d+)\))?p\.")
# The unnumbered component of "444/(3)p.", also in the malformed "463/1)p."
# that Gate 1 reads as 463 numbered pages (page 56).
_UNNUMBERED_RE = re.compile(r"/\(?(\d+)\)p\.")
_EDITION_STATEMENT_RE = re.compile(
    r"\b((?:\d{1,2}(?:st|nd|rd|th)|New|Newly|Revised)(?:\s+[a-z]+){0,2}\s+edition)\b"
)
# "Sereis" is the source's misspelling of the label on page 3772.
_SERIES_LABEL_RE = re.compile(r"\[\s*(?:Series|Sereis)\s*:")
_SERIES_LABEL_PREFIX_RE = re.compile(r"^(?:Series|Sereis)\s*:\s*")
_BRACKET_RE = re.compile(r"\[([^\[\]\n]{2,200})\]")
_SERIES_VOLUME_RE = re.compile(r",\s*(?:Vol\.\s*)?(\d{1,4})\s*$")
# A volume number the source set after a bracket that closed too early:
# "[Series: Maṭbūʿāt Kitābī : iṣdār jadīd (‘My Book’-Prints: New edition)], 48]"
# on page 1685.
_STRAY_VOLUME_RE = re.compile(r"\s*,\s*(\d{1,4})\s*\]")
# The English gloss the source adds to a series name in a closing square
# bracket ("Tvorba národov [The Formation of Nations)", page 5039). A trailing
# parenthesis stays part of the name: it glosses as often as it names a place
# or publisher ("Collection Folio bilingue (Paris)", page 675).
_SERIES_GLOSS_RE = re.compile(r"^(.*?\S)\s+\[(.+)[\])]$")
# "Vol. 2" after a wiki link that names a set, the volume within that set.
_LINK_VOLUME_RE = re.compile(r"\]?\.?\s*,?\s*Vol\.\s*(\d{1,4})\b")
# What may stand between the extent and a wiki link that names the set: a
# separating slash, "In:", or the volume statement "Vol. 10 of:" / "Vol. 1 of
# the 10-volume set" (pages 3058, 226, 25). Other prose says the link is
# something else, the source of an expanded edition or of a translation.
_SET_LINK_LEAD_RE = re.compile(
    r"(?:^|\s/|\.)\s*(?:In:|(?:This is )?Vol\.\s*\w+\.? of(?: the [\w-]+ set)?:?)?\s*$"
)
_TITLE_ITALIC_RE = re.compile(r"''(.+?)''")
_TITLE_QUOTED_RE = re.compile(r'\\?"(.+?)\\?"')
_CONTAINER_RE = re.compile(r"\bin\s+''(.+?)''")
_CONTAINER_TAIL_RE = re.compile(
    r"\[([^\[\]\n]{2,60})\]\s*,\s*([^,\[\]\n]{1,20})\s*\[\d{4}\]\s*,\s*pp?\.\s*([\d()\-–]+)"
)
# A header that states only the year can leave the imprint to the body, in the
# citation form "Place: Publisher, YEAR" ("Budapest: Rózsavölgyi, Athenaeum
# Kiadó, 1935", page 2569), with co-imprints joined by " / ". It is read only
# where YEAR is the header's year, also in the parenthesized form of a date the
# title page does not state ("Paderborn: Schöningh Verlag, (2002)", page 279).
# The publisher runs over no colon and no sentence break except the period of
# an initial ("S. Fischer Verlag"), so the statement cannot open in a label
# such as "First printing:" and swallow the extent and the next sentence.
_IMPRINT_NAME = r"(?:[^:;.\n]|\.(?=\S)|(?<=\b[A-ZÀ-Þ])\.\s)+?"
_IMPRINT_PART = rf"[^\W\d_][^:;.\n\[\]]{{0,40}}:\s{_IMPRINT_NAME}"
_IMPRINT_CHAIN = (
    rf"(?:^|(?<=[.;]\s))(?P<chain>{_IMPRINT_PART}(?:\s+/\s+{_IMPRINT_PART})*)"
)
_BODY_IMPRINT_RE = re.compile(
    rf"{_IMPRINT_CHAIN},\s*\(?(?P<year>\d{{4}})\b\)?", re.MULTILINE
)
# The statement after the closing bold of a date-only header ends in the imprint
# without repeating the year the bold states ("'''[1857]:''' ''Les Fleurs du
# mal''. 248p. Paris: Poulet-Malassis et de Broise", page 793). It is read only
# as the last statement of that line.
_HEADER_TAIL_IMPRINT_RE = re.compile(rf"{_IMPRINT_CHAIN}\s*\.?\s*$")
_BODY_IMPRINT_PART_RE = re.compile(r"^([^\W\d_][^:\d]{0,40}?):\s*(.+)$")
_URL_RE = re.compile(r"https?://\S+")
_URL_NOTE_RE = re.compile(r"\[([^\[\]\n]{2,60})\]\s*:?\s*$")
# A contribution's own pages are the first page statement outside brackets.
# What follows it states the pages of a part ("Notes, pp. 319-320") or of
# another printing ("An excerpt from the chapter … [1981], pp. 386-390",
# page 202), which the line-final statement used to be mistaken for.
_CONTRIBUTION_PAGES_RE = re.compile(r",\s*pp?\.\s*([()\-–]*\d[\d()\-–]*)")
_TRAILING_NOTE_RE = re.compile(r"^\s*\[(.+)\]\s*\.?\s*$")
# A cross-reference opens a new sentence or a bold label. The pages after it
# belong to the referenced publication ("pp. (339)-371. See: [[Gesamtausgabe
# des erzählerischen Werkes]] [1936], Vol. 2, No. 14, pp. 7-45", page 141).
# "Episode am Genfer See" shows why a bare "See" is no marker. A statement of
# the first or a later printing carries that printing's pages the same way
# ("pp. 371-377. First printed in ''Die Neue Rundschau'' [...], pp. 1315-1321",
# page 3757).
_CROSS_REFERENCE_MARK_RE = re.compile(
    r"(?:(?<=[.;])\s+|'''\s*|^)(?:See\b|(?:First |Re)?[Pp]rinted in\b)"
)
# Headings that end a contents list although Gate 1 does not segment at them:
# the wiki's own section headings and the bold labels of the sections that
# follow a volume's contents (page 259 "Reprinted in:", page 527
# "==Individual Stories==", page 2083 "Correspondence:").
_CONTENTS_END_RE = re.compile(
    r"^(?:={2,}[^=\n]+={2,}\s*$|'''\s*(?:Reprinted in|Individual Stor(?:y|ies)|"
    r"Reviews?|See(?: also)?|Reserialization|Film|Excerpts?|Translations?|"
    r"Correspondence|Correspondance|Secondary Literature|Autobiography|Biography|"
    r"NB|[A-Z][a-z]+ Editions/Reprints)\b)",
    re.MULTILINE,
)
# A year header followed only by a page locator is a heading inside a
# publication, not a publication ("'''[1911]''', p. 12" on page 3757).
_LOCATOR_HEADER_RE = re.compile(
    r"^'''\s*\[(?:ca\.\s*)?\d{4}\]\s*'''\s*,\s*pp?\.\s*[\d()\-–]+\s*$"
)
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
_PROVENANCE_EXCLUDED = frozenset(
    {"id", "provenance", "sourceSlice", "reviewFlags", "editionId", "reviewStatus"}
)


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


def _attested_place(value: str, attested: set[str]) -> bool:
    """Whether the location stock attests a value, or every part of a slash
    list such as "London/New York" (page 1565)."""
    return value in attested or all(part in attested for part in value.split("/"))


def _split_imprint(
    fields: HeaderFields, attested: set[str]
) -> tuple[str | None, list[str], list[dict], dict | None]:
    """Publisher, places and imprint pairs of a header, in source wording.

    The string rules of lib.editions.split_imprint read qualifiers, legal-form
    suffixes and co-imprints. Two further readings need the reviewed location
    stock: a single segment it attests is a place, not a publisher ("'''[1930]:
    Oslo'''", page 5057), and an undecided header whose trailing run of two or
    more segments it attests carries several places ("Nasionale Pers Beperk,
    Bloemfontein, Kaapstad (Capetown)", page 4209). What stays undecided is
    reported as a review flag.
    """
    imprints = list(fields.imprints)
    segments = [_flat(part) for part in (fields.imprint or "").split(",")]
    segments = [segment for segment in segments if segment]
    run_places: list[str] = []
    if len(imprints) == 1 and not imprints[0].resolved:
        run = 0
        while run < len(segments) - 1 and segments[len(segments) - 1 - run] in attested:
            run += 1
        if run >= 2:
            imprints = [Imprint(", ".join(segments[:-run]), None, True)]
            run_places = segments[-run:]
    imprints = [
        Imprint(None, item.publisher, True)
        if item.place is None
        and item.publisher
        and _attested_place(item.publisher, attested)
        else item
        for item in imprints
    ]
    publishers = [_flat(item.publisher) for item in imprints if item.publisher]
    places = _unique(
        [_flat(item.place) for item in imprints if item.place] + run_places
    )
    pairs = []
    if len(imprints) > 1:
        for item in imprints:
            pair: dict = {}
            _put(pair, "publisher", item.publisher and _flat(item.publisher))
            _put(pair, "place", item.place and _flat(item.place))
            pairs.append(pair)
    flag = None
    if not all(item.resolved for item in imprints):
        flag = {
            "code": "imprint-segments-unresolved",
            "detail": (
                "The boundary between publisher and place is not decidable from "
                "the source wording of the publication header: "
                f"{'; '.join(segments)}"
            ),
        }
    return (publishers[0] if publishers else None), places, pairs, flag


def _imprint_chain(chain: str) -> tuple[str | None, list[str]]:
    """Publisher and places of one "Place: Publisher" chain.

    A part without a place of its own follows the part before it as a further
    publisher at that place ("Budapest: Könnyvkiadó Franklin / Gondolat Kiadó",
    page 2569).
    """
    parts = [
        _BODY_IMPRINT_PART_RE.match(part.strip())
        for part in re.split(r"\s+/\s+", chain)
    ]
    if not parts[0] or not chain[0].isupper():
        return None, []
    places = [_flat(part.group(1)) for part in parts if part]
    if any(len(place.split()) > 4 for place in places):
        return None, []
    return _flat(parts[0].group(2)), _unique(places)


def _body_imprint(
    block_body: str, year: str | None, header_tail: str | None = None
) -> tuple[str | None, list[str]]:
    """Publisher and places of a "Place: Publisher, YEAR" statement at the
    header, for a header that names no imprint of its own.

    The statement is read from the text after the closing bold of the header
    line, then from the first body line. The header line may also end in the
    imprint without the year, which its bold already states.
    """
    if not year:
        return None, []
    lines = [line for line in block_body.splitlines() if line.strip()]
    # Only the statement directly at the header: a later line can cite the book
    # a review discusses (page 2613) or a second item (page 2301).
    candidates = [text for text in (header_tail, lines[0] if lines else None) if text]
    for text in candidates:
        for match in _BODY_IMPRINT_RE.finditer(text):
            if match.group("year") != year:
                continue
            publisher, places = _imprint_chain(match.group("chain"))
            if places:
                return publisher, places
    if header_tail:
        match = _HEADER_TAIL_IMPRINT_RE.search(header_tail)
        if match:
            return _imprint_chain(match.group("chain"))
    return None, []


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


def _closing_bracket(text: str, start: int) -> int | None:
    """Offset of the bracket that closes the one opening at start.

    Square brackets and parentheses count alike, because the source closes a
    square bracket with a parenthesis now and then ("[Tvorba národov [The
    Formation of Nations)]", page 5039). The scan stays on one line.
    """
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "\n":
            return None
        if char in "[(":
            depth += 1
        elif char in "])":
            depth -= 1
            if depth == 0:
                return index
    return None


def _series_start(block_body: str) -> int | None:
    """Where the series bracket opens: an explicitly labelled bracket, or the
    bracket that closes the extent statement on the same source line."""
    labelled = _SERIES_LABEL_RE.search(block_body)
    if labelled:
        return labelled.start()
    extent = _EXTENT_RE.search(block_body)
    if not extent:
        return None
    tail = block_body[extent.end() :]
    line_end = tail.find("\n")
    line = tail if line_end < 0 else tail[:line_end]
    reference = _CROSS_REFERENCE_RE.search(line)
    if reference:
        line = line[: reference.start()]
    opening = line.find("[")
    if line[opening + 1 : opening + 2] == "[":
        # A wiki link names the set a volume belongs to ("[[Ausgewählte Werke
        # in vier Bänden]]. Vol. 2", page 37), unless prose introduces it as
        # something else ("This is an expanded edition of [[…]]", page 2054).
        if not _SET_LINK_LEAD_RE.search(line[:opening]):
            return None
        opening += 1
    if opening < 0 or opening > 60:
        return None
    return extent.end() + opening


def _series(block_body: str) -> dict | None:
    """The series statement split into name, volume number and gloss.

    The volume is its own value, so no consumer can print it twice; the gloss
    is the source's translation of the series name and stays apart from it.
    Returns the offset after the statement as well, for the note that follows.
    A bracket longer than a series statement, or one whose nested brackets are
    no trailing gloss, is a note and yields nothing.
    """
    start = _series_start(block_body)
    if start is None:
        return None
    end = _closing_bracket(block_body, start)
    if end is None:
        return None
    content = _flat(block_body[start + 1 : end])
    if not 2 <= len(content) <= 200 or _EXTENT_RE.search(content):
        return None
    content = _SERIES_LABEL_PREFIX_RE.sub("", content)
    volume = None
    stray = _STRAY_VOLUME_RE.match(block_body, end + 1)
    link_volume = _LINK_VOLUME_RE.match(block_body, end + 1)
    if stray:
        volume, end = stray.group(1), stray.end() - 1
    elif block_body[start - 1 : start] == "[" and link_volume:
        volume, end = link_volume.group(1), link_volume.end() - 1
    else:
        match = _SERIES_VOLUME_RE.search(content)
        if match:
            volume, content = match.group(1), content[: match.start()].rstrip()
    gloss = None
    glossed = _SERIES_GLOSS_RE.match(content)
    if glossed and _closing_bracket(content, glossed.start(2) - 1) == len(content) - 1:
        content, gloss = glossed.group(1), glossed.group(2).strip()
    if not content or "[" in content or "]" in content:
        return None
    if block_body[end + 1 : end + 2] == "]":
        end += 1
    return {"series": content, "volume": volume, "gloss": gloss, "end": end + 1}


def _set_reference(block_body: str) -> tuple[str, str] | None:
    """The multi-volume set and volume number a "See" reference names."""
    extent = _EXTENT_RE.search(block_body)
    if not extent:
        return None
    tail = block_body[extent.end() :]
    line_end = tail.find("\n")
    line = tail if line_end < 0 else tail[:line_end]
    match = _SET_REFERENCE_RE.search(line)
    return (_flat(match.group(1)), match.group(2)) if match else None


def _series_note(block_body: str, series_end: int) -> str | None:
    """Prose that follows the series statement on the same line, such as the
    note that a volume was originally a thesis."""
    tail = block_body[series_end:]
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

    def add(credit: dict) -> None:
        if credit not in credits:
            credits.append(credit)

    for match in _CREDIT_RE.finditer(text):
        label = _flat(match.group(1))
        tokens = label.split()
        if label in _AUTHOR_LABELS:
            role = "author"
        else:
            if len(tokens) > 8 or tokens[0] in _CREDIT_STOP_TOKENS:
                continue
            if not tokens[0][:1].isupper():
                continue
            lowered = label.lower()
            role = next((role for stem, role in _ROLE_STEMS if stem in lowered), None)
            if role is None:
                continue
        chained = _CHAINED_CREDIT_RE.match(text, match.end())
        if chained:
            add({"role": role, "name": chained.group(1), "creditLabel": label})
            second = credited_name(text, chained.end())
            if second:
                add(
                    {
                        "role": "translator",
                        "name": second,
                        "creditLabel": chained.group(2),
                    }
                )
            continue
        name = credited_name(text, match.end())
        if not name:
            continue
        add({"role": role, "name": name, "creditLabel": label})
    return credits


def _outside_brackets(text: str, offset: int) -> bool:
    """Whether an offset lies outside every balanced bracket; a bracket the
    source never closes ("Ĭozef Rot [Joseph Roth (Eulogy), pp. 488-497", page
    1796) encloses nothing."""
    return not protected_mask(text)[offset]


def _own_statement(line: str) -> str:
    """A contents line up to its first cross-reference outside brackets."""
    for mark in _CROSS_REFERENCE_MARK_RE.finditer(line):
        if mark.start() > 0 and _outside_brackets(line, mark.start()):
            return line[: mark.start()].rstrip()
    return line


def _contents_text(section_text: str) -> str:
    """The contents list of a section, cut at a heading that starts another
    kind of section."""
    first_line_end = section_text.find("\n")
    if first_line_end < 0:
        return section_text
    end = _CONTENTS_END_RE.search(section_text, first_line_end + 1)
    return section_text[: end.start()] if end else section_text


def _contributions(section_text: str) -> list[dict]:
    """Parse the contents lines of a publication into scoped contributions."""
    contributions = []
    for list_block in _LIST_BLOCK_RE.finditer(section_text):
        for raw_line in list_block.group(1).splitlines():
            line = _own_statement(raw_line.strip())
            if len(line) < 3:
                continue
            scope: dict = {}
            pages = next(
                (
                    match
                    for match in _CONTRIBUTION_PAGES_RE.finditer(line)
                    if _outside_brackets(line, match.start())
                ),
                None,
            )
            if pages:
                scope["pages"] = _flat(pages.group(1))
                numbers = [int(n) for n in _PAGE_NUMBER_RE.findall(pages.group(1))]
                if numbers:
                    scope["pageStart"] = numbers[0]
                    scope["pageEnd"] = numbers[-1]
                remainder = _TRAILING_NOTE_RE.match(line[pages.end() :])
                line = line[: pages.start()].strip()
                # The bracket after the pages names the original of a translated
                # poem ("Die Riesin, p. 178 [\"La Géante\" … in ''Les Fleurs du
                # mal'', pp. (48)-49]", page 39).
                if remainder and not _CONTRIBUTION_NOTE_RE.match(line):
                    line = f"{line} [{remainder.group(1)}]"
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
    """Report contents that run past the extent stated for them.

    The extent counts numbered and unnumbered pages: "444/(3)p." declares 447,
    so contents ending on the unnumbered page (445) stay inside it (page 1891).
    """
    numbered = (extent or {}).get("numbered")
    ends = [c["pageEnd"] for c in contributions if "pageEnd" in c]
    if numbered is None or not ends:
        return None
    total = numbered + extent.get("unnumbered", 0)
    if max(ends) <= total:
        return None
    return {
        "code": "contents-pagination-exceeds-extent",
        "detail": (
            f"The contents end at page {max(ends)}, the stated extent "
            f"{extent['raw']} counts {total} pages."
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


def _governing_extent(text: str, block_end: int, section_start: int) -> dict | None:
    """The extent stated last between a publication block and its contents.

    A multi-volume set states each volume's extent before that volume's
    contents (page 1875), so a later contents list is measured against the
    extent it follows rather than the first volume's.
    """
    region = _mask(text[block_end:section_start])
    matches = list(_EXTENT_RE.finditer(region))
    if not matches:
        return None
    last = matches[-1]
    extent: dict = {"raw": last.group(0), "numbered": int(last.group(1))}
    if last.group(2):
        extent["unnumbered"] = int(last.group(2))
    return extent


def _attach_contributions(
    publications: list[tuple[int, int, dict]], sections: list[dict], text: str
) -> None:
    """Attach a contents section to the publication block it follows, and
    record the pagination flag of each contents list against its extent."""
    for section in sections:
        if section["heading"].strip().lower() != "contents":
            continue
        owner = None
        for start, end, publication in publications:
            if start < section["start"]:
                owner = (end, publication)
        if owner is None:
            continue
        block_end, publication = owner
        contributions = _contributions(
            _contents_text(text[section["start"] : section["end"]])
        )
        if not contributions:
            continue
        publication.setdefault("contributions", []).extend(contributions)
        # A set can paginate its volumes continuously (page 363) or anew (page
        # 1875), so the contents fit if they fit either extent.
        candidates = [
            extent
            for extent in (
                publication.get("extent"),
                _governing_extent(text, block_end, section["start"]),
            )
            if extent and "numbered" in extent
        ]
        extent = max(
            candidates,
            key=lambda item: item["numbered"] + item.get("unnumbered", 0),
            default=None,
        )
        flag = _pagination_flag(extent, contributions)
        if flag and flag not in publication["_flags"]:
            publication["_flags"].append(flag)


def _build_publication(
    edition: dict,
    fields: HeaderFields,
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

    imprint = _flat(fields.imprint or "")
    publisher, places, pairs, imprint_flag = _split_imprint(fields, attested)
    if not imprint:
        # A compound header shares one tail among its parts, so the tail names
        # the imprint of none of them in particular.
        tail = None if "compound-header" in fields.flags else fields.description
        publisher, places = _body_imprint(
            masked_body, edition.get("schema:datePublished"), tail
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
    _put(publication, "imprints", pairs)
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
    set_reference = None if series else _set_reference(masked_body)
    if set_reference:
        _put(publication, "series", set_reference[0])
        _put(publication, "seriesVolume", set_reference[1])
    elif series:
        _put(publication, "series", series["series"])
        _put(publication, "seriesVolume", series["volume"])
        _put(publication, "seriesGloss", series["gloss"])
        _put(publication, "note", _series_note(masked_body, series["end"]))
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
    if not places:
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

    Where the header marks the publisher as unknown ("[s.n.], Tiranë", page
    5126), the flat field keeps that mark: the flat layer has no state for an
    attested absence, and an empty field would be filled by the enrichment.
    """
    if not text:
        return None
    for line in text.splitlines():
        if not EDITION_HEADER_RE.match(line) or _LOCATOR_HEADER_RE.match(line):
            continue
        for fields in parse_header_line(line):
            publisher, places, _, _ = _split_imprint(fields, attested_places)
            if places and not publisher:
                first = _flat((fields.imprint or "").split(",")[0])
                publisher = first if first in ABSENCE_MARKS else None
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
    selectors = {
        annotation["oa:hasBody"]["@id"]: annotation["oa:hasTarget"]["oa:hasSelector"]
        for annotation in segmented["annotations"]
    }
    scopes = _language_scopes(text)
    category_languages = _category_languages(categories)

    built: list[tuple[int, int, dict]] = []
    parts_seen: dict[int, int] = {}
    for edition in segmented["editions"]:
        selector = selectors[edition["@id"]]
        start, end = selector["oa:start"], selector["oa:end"]
        # A compound header yields one edition per part, in header order.
        part = parts_seen.get(start, 0)
        parts_seen[start] = part + 1
        header_line = edition["klawiter:headerLine"]
        if _LOCATOR_HEADER_RE.match(header_line.strip()):
            continue
        fields = parse_header_line(header_line)[part]
        language = _language_at(scopes, start)
        if language is None and len(category_languages) == 1:
            language = category_languages[0]
        built.append(
            (
                start,
                end,
                _build_publication(
                    edition,
                    fields,
                    text[start:end],
                    start,
                    end,
                    language,
                    attested_places,
                    delivered_text,
                ),
            )
        )
    if not built:
        return {}

    _attach_contributions(built, segmented["unsegmentedSections"], text)

    publications = []
    for _, _, publication in built:
        _put(publication, "reviewFlags", publication.pop("_flags"))
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


def attach_edition_state(layer: dict, edition_states: dict[str, str]) -> None:
    """Name the Gate-1 edition node and its review status per publication.

    A publication whose page lies outside the Gate-1 corpus has no edition
    node; it is rule-extracted and unreviewed, so it reports "proposed".
    """
    for publication in layer.get("publications", []):
        edition_id = publication["id"].replace(
            "klawiter:publication/", "klawiter:edition/", 1
        )
        status = edition_states.get(edition_id)
        if status is not None:
            publication["editionId"] = edition_id
        publication["reviewStatus"] = status or "proposed"


def review_flag_codes(layer: dict) -> list[str]:
    """The distinct review flag codes of a page's publications, sorted."""
    return sorted(
        {
            flag["code"]
            for publication in layer.get("publications", [])
            for flag in publication.get("reviewFlags", [])
        }
    )
