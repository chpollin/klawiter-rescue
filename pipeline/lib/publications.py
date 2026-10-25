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
    COMPOUND_HEADER_RE,
    EDITION_HEADER_RE,
    HEADER_RE,
    LOCATOR_HEADER_RE,
    MALFORMED_PAGE_COUNT_RE,
    PAREN_PAGE_COUNT_RE,
    PREFATORY_PAGES_RE,
    SERIES_RE,
    STANDARD_PAGE_COUNT_RE,
    HeaderFields,
    _continues_imprint,
    parse_header_line,
    protected_mask,
    resolve_imprints,
    segment_page,
    split_imprint,
)
from lib.encoding import source_value, unescape_dump_quotes
from lib.patterns import (
    ABSENCE_MARKS,
    BRACKET_KNOWN_RE,
    BRACKET_PLACE_RE,
    CATEGORY_LANGUAGE_RE,
    CORPORATE_SUFFIXES,
    clean_location,
    credited_name,
    extract_translator,
    location_from_header,
)
from lib.value_spans import (
    category_gap,
    category_links,
    display_form,
    displayed_span,
    locate,
)
from lib.vocabulary import LANGUAGE_MAP, language_to_iso

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
# A bold label announcing the edition in another language ("'''French
# edition:'''", page 2083) opens a publication without a year header, so the
# contents after it belong to that edition, not to the publication before it.
_LANGUAGE_EDITION_RE = re.compile(
    rf"^'''\s*(?:{'|'.join(map(re.escape, LANGUAGE_MAP))}) edition\s*:?\s*'''\s*$",
    re.MULTILINE,
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
    {
        "id",
        "provenance",
        "sourceSlice",
        "reviewFlags",
        "editionId",
        "reviewStatus",
        "reviewDecision",
        "reviewProducer",
        "valueSpans",
    }
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


def _unescaped(value):
    """The record with the dump's quote escape undone in every string.

    The source slice and its offsets stay in the dump's form; only the values
    read from it leave the source, so the escape ends here.
    """
    if isinstance(value, str):
        return unescape_dump_quotes(value)
    if isinstance(value, list):
        return [_unescaped(item) for item in value]
    if isinstance(value, dict):
        return {
            key: item if key == "sourceSlice" else _unescaped(item)
            for key, item in value.items()
        }
    return value


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


def _language_scopes(text: str) -> list[tuple[int, str, tuple[int, int]]]:
    """Offsets of the bold language headings that scope the following blocks,
    each with the span of its name."""
    scopes = []
    for match in _LANGUAGE_HEADING_RE.finditer(text):
        name = match.group(1).strip()
        if name in LANGUAGE_MAP:
            scopes.append((match.start(), name, match.span(1)))
    return scopes


def _language_at(
    scopes: list[tuple[int, str, tuple[int, int]]], start: int
) -> tuple[str | None, tuple[int, int] | None]:
    """The language heading a block stands under, that is the last one above
    it, with the span of its name."""
    enclosing = [(name, span) for offset, name, span in scopes if offset < start]
    return enclosing[-1] if enclosing else (None, None)


def _category_languages(categories: list[str]) -> list[str]:
    names = []
    for category in categories:
        match = CATEGORY_LANGUAGE_RE.search(category)
        if match and match.group(1) in LANGUAGE_MAP and match.group(1) not in names:
            names.append(match.group(1))
    return names


_DATE_SEGMENT_RE = re.compile(
    r"^\d{1,2}\.?\s+(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\b"
)


def _split_imprint(
    fields: HeaderFields, attested: set[str]
) -> tuple[str | None, list[str], list[dict], dict | None]:
    """Publisher, places and imprint pairs of a header, in source wording.

    The string rules of lib.editions.split_imprint read qualifiers, legal-form
    suffixes and co-imprints, and lib.editions.resolve_imprints the readings
    that need the reviewed location stock, which Gate 1 shares. What stays
    undecided is reported as a review flag.
    """
    imprints, run_places = resolve_imprints(fields, attested)
    segments = [_flat(part) for part in (fields.imprint or "").split(",")]
    segments = [segment for segment in segments if segment]
    # A film header can set its broadcast date where an imprint names the
    # publisher ("'''[1973]: 13 February and 31 October, Warszawa'''", page
    # 4474); a date is no publisher.
    publishers = [
        _flat(item.publisher)
        for item in imprints
        if item.publisher and not _DATE_SEGMENT_RE.match(_flat(item.publisher))
    ]
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


def _title(block_body: str) -> tuple[str, tuple[int, int]] | None:
    """The publication title, the first italic or quoted string of the block,
    with the span it was read from.

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
    first = min(candidates, key=lambda m: m.start())
    title = _flat(first.group(1))
    # Stray quote markup can leave a title of punctuation alone, which names
    # nothing; the source then documents no title for this publication.
    return (title, first.span(1)) if re.search(r"\w", title) else None


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
    # A bracket after an italic or quoted title glosses, places or credits that
    # title ("serialized in ''Le Monde'' [Paris]", page 675; "\"Predislovie\"
    # [Ivan Inozemtsev]", page 2485), and one after a contribution label names
    # its author ("Afterword [Josef Polišenský]", page 2598); neither is a
    # series statement.
    gap = line[:opening]
    if (
        "''" in gap
        or '"' in gap
        or "“" in gap
        or _CONTRIBUTION_LABEL_END_RE.search(gap)
    ):
        return None
    return extent.end() + opening


_CONTRIBUTION_LABEL_END_RE = re.compile(
    r"\b(?:Afterword|Foreword|Preface|Introduction|Epilogue|Postface|Notes|"
    r"Commentary|Nachwort|Vorwort|Einleitung)\s*:?\s*$"
)
# A bracket that records a printing, a reprint, a source edition or a copy
# count is a note, not a series ("[Reprinted 1967]", pages 846 and 1848; "[4th
# impression 1961. 8th impression 1973 …]", page 151; "[Based on the 1957
# Reclam edition]", page 2336; "[111.-130. Tsd.]", page 263).
_SERIES_NOTE_RE = re.compile(
    r"^(?:Reprint|Reissu|Based on|This is|Licen[cs]ed|Braille|School edition|"
    r"Illustrated by|Translated|Edited by|First|No\.\s*\d|\d)"
    r"|\b(?:edition|edtion|impression|printing|reprint(?:ed)?|copies)\b"
)


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
    # A parenthesized gloss may translate "edition" inside a series name
    # ("iṣdār jadīd (‘My Book’-Prints: New edition)", page 1685).
    if _SERIES_NOTE_RE.search(re.sub(r"\([^()]*\)", "", content)):
        return None
    if block_body[end + 1 : end + 2] == "]":
        end += 1
    return {
        "series": content,
        "volume": volume,
        "gloss": gloss,
        "start": start,
        "end": end + 1,
    }


def _set_reference(block_body: str) -> tuple[str, str, dict] | None:
    """The multi-volume set and volume number a "See" reference names, with
    the spans they were read from."""
    extent = _EXTENT_RE.search(block_body)
    if not extent:
        return None
    tail = block_body[extent.end() :]
    line_end = tail.find("\n")
    line = tail if line_end < 0 else tail[:line_end]
    match = _SET_REFERENCE_RE.search(line)
    if not match:
        return None
    base = extent.end()
    spans = {
        "series": (base + match.start(1), base + match.end(1)),
        "seriesVolume": (base + match.start(2), base + match.end(2)),
    }
    return _flat(match.group(1)), match.group(2), spans


def _series_note(
    block_body: str, series_end: int
) -> tuple[str, tuple[int, int]] | None:
    """Prose that follows the series statement on the same line, such as the
    note that a volume was originally a thesis, with its line's span."""
    tail = block_body[series_end:]
    line_end = tail.find("\n")
    line = tail if line_end < 0 else tail[:line_end]
    note = _flat(line.lstrip(". "))
    if len(note) < 20:
        return None
    return note, (series_end, series_end + len(line))


# A verb of publication history before "in ''…''" says where the publication
# appeared besides ("This edition was serialized in ''Le Monde'' [Paris], 29
# August - 8 September 1972", page 675); the journal is then no container.
_HISTORY_BEFORE_IN_RE = re.compile(
    r"\b(?:seriali[sz]ed|reprinted|printed|published|appeared|excerpted|"
    r"reviewed|announced|quoted|reproduced)\s*$",
    re.IGNORECASE,
)


def _container(block_body: str) -> tuple[dict, dict] | None:
    """Journal, place, issue and pages of an article-shaped publication, and
    the spans they were read from."""
    match = next(
        (
            m
            for m in _CONTAINER_RE.finditer(block_body)
            if not _HISTORY_BEFORE_IN_RE.search(block_body[: m.start()])
        ),
        None,
    )
    if not match:
        return None
    container: dict = {"title": _flat(match.group(1))}
    spans = {"title": match.span(1)}
    tail = _CONTAINER_TAIL_RE.search(block_body, match.end())
    if tail:
        for index, part in enumerate(("place", "issue", "pages"), start=1):
            container[part] = _flat(tail.group(index))
            spans[part] = tail.span(index)
    return container, spans


def _online(block_body: str) -> tuple[dict, dict] | None:
    """An online address with the qualification the source gives it, and the
    spans they were read from."""
    match = _URL_RE.search(block_body)
    if not match:
        return None
    online = {"url": match.group(0).rstrip(".,;")}
    spans = {"url": (match.start(), match.start() + len(online["url"]))}
    head = block_body[: match.start()].rstrip()
    line_start = head.rfind("\n") + 1
    note = _URL_NOTE_RE.search(head[line_start:])
    if note:
        online["note"] = _flat(note.group(1))
        spans["note"] = (line_start + note.start(1), line_start + note.end(1))
    return online, spans


def _name_region(text: str, start: int, name: str) -> tuple[int, int]:
    """The span of a name read at start: the name itself where it stands
    there verbatim, else the rest of its line."""
    if text.startswith(name, start):
        return start, start + len(name)
    line_end = text.find("\n", start)
    return start, len(text) if line_end < 0 else line_end


def _credits(text: str) -> list[dict]:
    """Read the credited roles a source passage states, with their labels."""
    return [credit for credit, _ in _credit_readings(text)]


def _credit_readings(text: str) -> list[tuple[dict, dict]]:
    """The credits of a passage, each with the spans of its name and label."""
    readings: list[tuple[dict, dict]] = []

    def add(credit: dict, spans: dict) -> None:
        if all(credit != known for known, _ in readings):
            readings.append((credit, spans))

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
            add(
                {"role": role, "name": chained.group(1), "creditLabel": label},
                {"name": chained.span(1), "creditLabel": match.span(1)},
            )
            second = credited_name(text, chained.end())
            if second:
                add(
                    {
                        "role": "translator",
                        "name": second,
                        "creditLabel": chained.group(2),
                    },
                    {
                        "name": _name_region(text, chained.end(), second),
                        "creditLabel": chained.span(2),
                    },
                )
            continue
        name = credited_name(text, match.end())
        if not name:
            continue
        credit = {"role": role, "name": name, "creditLabel": label}
        if _uncertain_after(text, match.end(), name):
            credit["uncertain"] = True
        add(
            credit,
            {
                "name": _name_region(text, match.end(), name),
                "creditLabel": match.span(1),
            },
        )
    return readings


# The source's mark of a doubtful attribution right after a name ("Translated
# by Jacqueline Des Gouttes (?)", page 675).
_UNCERTAINTY_MARK_RE = re.compile(r"\s*\(\?\)")


def _uncertain_after(text: str, start: int, name: str) -> bool:
    """Whether the credited name at start is followed by the mark "(?)"."""
    offset = text.find(name, start, start + len(name) + 8)
    if offset < 0:
        return False
    return bool(_UNCERTAINTY_MARK_RE.match(text, offset + len(name)))


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


def _lines(text: str, base: int):
    """The lines of text as str.splitlines() yields them, each with its offset."""
    offset = base
    for chunk in text.splitlines(keepends=True):
        parts = chunk.splitlines()
        yield (parts[0] if parts else ""), offset
        offset += len(chunk)


def _contributions(section_text: str) -> list[tuple[dict, dict]]:
    """Parse the contents lines of a publication into scoped contributions,
    each with the spans in section_text its parts were read from ("" names
    the whole contents line)."""
    contributions = []
    for list_block in _LIST_BLOCK_RE.finditer(section_text):
        for raw_line, offset in _lines(list_block.group(1), list_block.start(1)):
            at = offset + len(raw_line) - len(raw_line.lstrip())
            spans = {"": (at, at + len(raw_line.strip()))}
            line = _own_statement(raw_line.strip())
            if len(line) < 3:
                continue
            scope: dict = {}
            rebuilt = None
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
                spans["pages"] = spans["pageStart"] = spans["pageEnd"] = (
                    at + pages.start(1),
                    at + pages.end(1),
                )
                numbers = [int(n) for n in _PAGE_NUMBER_RE.findall(pages.group(1))]
                if numbers:
                    scope["pageStart"] = numbers[0]
                    scope["pageEnd"] = numbers[-1]
                remainder = _TRAILING_NOTE_RE.match(line[pages.end() :])
                after_pages = pages.end()
                line = line[: pages.start()].strip()
                # The bracket after the pages names the original of a translated
                # poem ("Die Riesin, p. 178 [\"La Géante\" … in ''Les Fleurs du
                # mal'', pp. (48)-49]", page 39).
                if remainder and not _CONTRIBUTION_NOTE_RE.match(line):
                    line = f"{line} [{remainder.group(1)}]"
                    rebuilt = (
                        at + after_pages + remainder.start(1),
                        at + after_pages + remainder.end(1),
                    )
            note = _CONTRIBUTION_NOTE_RE.match(line)
            if note:
                title = _flat(note.group(1))
                spans["title"] = (at, at + note.end(1))
                scope["note"] = _flat(note.group(2))
                if rebuilt is None:
                    spans["note"] = (at + note.start(2), at + note.end(2))
                elif "[" not in note.group(1) and note.group(2) == remainder.group(1):
                    spans["note"] = rebuilt
                if "note" in spans:
                    spans["credits"] = spans["note"]
                credits = _credits(f"[{note.group(2)}]")
                if credits:
                    scope["credits"] = credits
            else:
                title = _flat(line)
                spans["title"] = (at, at + len(line))
            contribution = {"title": title, **scope} if title else scope
            if contribution:
                contributions.append((contribution, spans))
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


def _header_regions(line: str) -> list[dict]:
    """Offsets within a header line of each part's year statement and imprint
    field, read by the grammar of lib.editions.parse_header_line.

    The imprint field of the last part runs to the end of the line where the
    text after the closing bold continues it, as parse_header_line joins it.
    """
    stripped = line.strip()
    lead = len(line) - len(line.lstrip())
    body, body_at = stripped, lead
    if stripped.startswith("'''"):
        rest = stripped[3:]
        body = rest.lstrip()
        body_at = lead + 3 + len(rest) - len(body)
    suffix = None
    if "'''" in body:
        cut = body.index("'''")
        header_text = body[:cut]
        suffix = body[cut + 3 :].strip() or None
    else:
        header_text = body
    if suffix and SERIES_RE.fullmatch(suffix):
        suffix = None
    bounds, position = [], 0
    for separator in COMPOUND_HEADER_RE.finditer(header_text):
        bounds.append((position, separator.start()))
        position = separator.end()
    bounds.append((position, len(header_text)))
    regions = []
    for index, (start, end) in enumerate(bounds):
        at = body_at + start
        match = HEADER_RE.match(header_text[start:end])
        if not match:
            regions.append({"imprint": (at, body_at + end)})
            continue
        field_end = at + match.end(2)
        if (
            suffix
            and index == len(bounds) - 1
            and _continues_imprint(match.group(2), suffix) is not None
        ):
            field_end = lead + len(stripped)
        regions.append(
            {
                "yearRaw": (at + match.start(1), at + match.end(1)),
                "imprint": (at + match.start(2), field_end),
            }
        )
    return regions


def _extent_region(block: str) -> tuple[int, int] | None:
    """The span of the extent statement lib.editions reads from a block."""
    standard = STANDARD_PAGE_COUNT_RE.search(block)
    if standard:
        prefix = PREFATORY_PAGES_RE.search(block, 0, standard.start())
        return (prefix.start(1) if prefix else standard.start()), standard.end()
    for pattern in (PAREN_PAGE_COUNT_RE, MALFORMED_PAGE_COUNT_RE):
        match = pattern.search(block)
        if match:
            return match.span()
    return None


def _first_line_end(text: str) -> int:
    """The end of the first line of text that holds a statement."""
    match = re.search(r"[^\n]*\S[^\n]*", text)
    return match.end() if match else 0


# The parts of a compound value whose own wording the source gives; a role,
# a mark such as "uncertain" and the numbers of a page range read from the
# notation beside them are no further passages.
_VALUE_PARTS = {
    "imprints": ("publisher", "place"),
    "extent": ("raw", "numbered", "unnumbered"),
    "credits": ("name", "creditLabel"),
    "container": ("title", "place", "issue", "pages"),
    "online": ("url", "note"),
}
_CONTRIBUTION_PARTS = ("title", "pages", "pageStart", "pageEnd", "note")


def publication_values(publication: dict):
    """Every value a publication publishes, in its order, as (field, part,
    path, value); the structural keys carry none."""
    for field, value in publication.items():
        if field in _PROVENANCE_EXCLUDED:
            continue
        if field == "contributions":
            for index, item in enumerate(value):
                for part in _CONTRIBUTION_PARTS:
                    if part in item:
                        yield field, part, (field, index, part), str(item[part])
                for number, credit in enumerate(item.get("credits", [])):
                    for part in _VALUE_PARTS["credits"]:
                        yield (
                            field,
                            f"credits.{part}",
                            (field, index, "credits", number, part),
                            credit[part],
                        )
        elif field in ("imprints", "credits"):
            for index, item in enumerate(value):
                for part in _VALUE_PARTS[field]:
                    if part in item:
                        yield field, part, (field, index, part), str(item[part])
        elif field in _VALUE_PARTS:
            for part in _VALUE_PARTS[field]:
                if part in value:
                    yield field, part, (field, part), str(value[part])
        elif isinstance(value, list):
            for index, item in enumerate(value):
                yield field, None, (field, index), str(item)
        else:
            yield field, None, (field,), str(value)


def _region_of(regions: dict, path: tuple):
    """The region recorded for a value's path or for the nearest enclosing one."""
    for length in range(len(path), 0, -1):
        if path[:length] in regions:
            return regions[path[:length]]
    return None


def _value_spans(publication: dict, regions: dict, display) -> dict:
    """The evidence entry of every published value, grouped by field."""
    spans: dict[str, list[dict]] = {}
    for field, part, path, value in publication_values(publication):
        region = _region_of(regions, path)
        if isinstance(region, list):
            entry = category_gap(value, region)
        else:
            derivation = "language-code" if field == "languageCode" else None
            entry = locate(value, display, region, derivation)
        if part:
            entry = {"value": entry.pop("value"), "part": part, **entry}
        spans.setdefault(field, []).append(entry)
    return spans


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
                owner = (start, end, publication)
        if owner is None:
            continue
        block_start, block_end, publication = owner
        if _LANGUAGE_EDITION_RE.search(text, block_start, section["start"]):
            continue
        readings = _contributions(
            _contents_text(text[section["start"] : section["end"]])
        )
        if not readings:
            continue
        listed = publication.setdefault("contributions", [])
        for contribution, spans in readings:
            for part, (part_start, part_end) in spans.items():
                path = ("contributions", len(listed)) + ((part,) if part else ())
                publication["_regions"][path] = (
                    section["start"] + part_start,
                    section["start"] + part_end,
                )
            listed.append(contribution)
        contributions = [contribution for contribution, _ in readings]
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
    language_region,
    attested: set[str],
    display,
    part: int = 0,
) -> dict:
    """One publication record, built only from its own source block.

    ``_regions`` maps the path of every value to the raw span of the page
    text its rule read it from, so its displayed position is mapped rather
    than searched; build_page_publications turns it into valueSpans.
    """
    header_line = edition["klawiter:headerLine"]
    body_at = start + len(header_line) if block.startswith(header_line) else start
    body = block[body_at - start :]
    masked_body = _mask(body)

    def at_body(span: tuple[int, int]) -> tuple[int, int]:
        return body_at + span[0], body_at + span[1]

    header = _header_regions(header_line)
    header = header[part] if part < len(header) else {}
    regions: dict = {}
    if "yearRaw" in header:
        year_span = (start + header["yearRaw"][0], start + header["yearRaw"][1])
        regions[("year",)] = regions[("yearRaw",)] = year_span

    imprint = _flat(fields.imprint or "")
    publisher, places, pairs, imprint_flag = _split_imprint(fields, attested)
    if imprint and "imprint" in header:
        imprint_span = (start + header["imprint"][0], start + header["imprint"][1])
    else:
        # The statement at the header: the header line and the first body line.
        imprint_span = (start, body_at + _first_line_end(masked_body))
    if not imprint:
        # A compound header shares one tail among its parts, so the tail names
        # the imprint of none of them in particular.
        tail = None if "compound-header" in fields.flags else fields.description
        publisher, places = _body_imprint(
            masked_body, edition.get("schema:datePublished"), tail
        )
    for key in ("imprint", "publisher", "places", "imprints"):
        regions[(key,)] = imprint_span
    series = _series(masked_body)

    publication: dict = {
        "id": f"klawiter:publication/{edition['@id'].rsplit('/', 1)[1]}"
    }
    _put(publication, "year", edition.get("schema:datePublished"), int)
    _put(publication, "yearRaw", edition.get("klawiter:yearRaw"))
    title = _title(masked_body)
    if title:
        _put(publication, "title", title[0])
        regions[("title",)] = at_body(title[1])
    _put(publication, "imprint", imprint)
    _put(publication, "publisher", publisher)
    _put(publication, "places", places)
    _put(publication, "imprints", pairs)
    _put(publication, "language", language)
    _put(publication, "languageCode", language_to_iso(language) if language else None)
    if language_region is not None:
        regions[("language",)] = regions[("languageCode",)] = language_region
    statement = _edition_statement(masked_body, edition.get("schema:datePublished"))
    if statement:
        _put(publication, "editionStatement", statement[0])
        regions[("editionStatement",)] = at_body(statement[1])
    _put(
        publication,
        "extent",
        _extent(
            edition.get("klawiter:pageCountRaw"), edition.get("schema:numberOfPages")
        ),
    )
    extent_span = _extent_region(block)
    if extent_span:
        regions[("extent",)] = (start + extent_span[0], start + extent_span[1])
    set_reference = None if series else _set_reference(masked_body)
    if set_reference:
        _put(publication, "series", set_reference[0])
        _put(publication, "seriesVolume", set_reference[1])
        for key, span in set_reference[2].items():
            regions[(key,)] = at_body(span)
    elif series:
        _put(publication, "series", series["series"])
        _put(publication, "seriesVolume", series["volume"])
        _put(publication, "seriesGloss", series["gloss"])
        series_span = at_body((series["start"], series["end"]))
        for key in ("series", "seriesVolume", "seriesGloss"):
            regions[(key,)] = series_span
        note = _series_note(masked_body, series["end"])
        if note:
            _put(publication, "note", note[0])
            regions[("note",)] = at_body(note[1])
    readings = _credit_readings(masked_body)
    _put(publication, "credits", [credit for credit, _ in readings])
    for index, (_, spans) in enumerate(readings):
        for key, span in spans.items():
            regions[("credits", index, key)] = at_body(span)
    for key, reader in (("container", _container), ("online", _online)):
        read = reader(masked_body)
        if read:
            _put(publication, key, read[0])
            for part_key, span in read[1].items():
                regions[(key, part_key)] = at_body(span)
    source_slice = {
        "start": start,
        "end": end,
        "sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
    }
    span = displayed_span(display, start, end)
    if span:
        source_slice["textStart"], source_slice["textEnd"] = span
    publication["sourceSlice"] = source_slice
    publication["_regions"] = regions

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


# What follows an edition statement that dates it: ", 1945", " of 1936", a
# bracketed extent before the year ("5th edition [116p.], 2000", page 675), or
# an imprint closing the same clause ("23rd edition, Éditions Grasset, Paris,
# 2004", page 675). A sentence break or semicolon ends the clause.
_EDITION_DATE_RE = re.compile(
    r"\s*(?:,|:|\bof\b|\bin\b)?\s*(?:\[[^\[\]\n]*\]\s*,?\s*)?\(?(\d{4})\b"
    r"|,(?:[^;.\n]|\.(?=\S)){0,80}?\b(\d{4})\b"
)


def _edition_statement(
    block_body: str, year: int | str | None = None
) -> tuple[str, tuple[int, int]] | None:
    """The edition statement of this publication with its span, or None.

    A statement dated with another year than the publication's records a later
    printing ("124/(1)p. … 2nd edition, 1945; 3rd edition, 1946" under the 1944
    header of page 675; "2nd edition of 1936 published online" under 1933 on
    page 4124), not the edition this block describes.
    """
    # Blank bracket contents in place, so offsets still address block_body.
    without_brackets = _BRACKET_RE.sub(lambda m: " " * len(m.group(0)), block_body)
    for match in _EDITION_STATEMENT_RE.finditer(without_brackets):
        dated = _EDITION_DATE_RE.match(block_body, match.end())
        if dated and (dated.group(1) or dated.group(2)) != str(year):
            # The reprint history starts here; what follows lists later
            # printings ("2nd edition 1936. … 3rd edition. 370p. 1938").
            return None
        return _flat(match.group(1)), match.span(1)
    return None


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
        if not EDITION_HEADER_RE.match(line) or LOCATOR_HEADER_RE.match(line):
            continue
        for fields in parse_header_line(line):
            publisher, places, _, _ = _split_imprint(fields, attested_places)
            if places and not publisher:
                first = _flat((fields.imprint or "").split(",")[0])
                publisher = first if first in ABSENCE_MARKS else None
            if publisher and places:
                return publisher
    return None


def first_publication_fields(
    page_id: int,
    text: str,
    page_title: str,
    categories: list[str],
    attested_places: set[str],
) -> dict | None:
    """Flat year, extent and publisher of the page's first publication.

    Returns None for a page without a publication layer, whose flat fields
    keep coming from the body patterns. On a page with a layer the three flat
    fields describe one publication, the first in source order, so the flat
    record never joins one publication's year to another's extent (page 23:
    the 1936 imprint beside the 274 pages of the 1954 edition). A field the
    first publication lacks stays empty. The publisher is taken only where the
    publication also names a place, as before; an attested absence mark
    ("[s.n.], Tiranë", page 5126) is kept, because the flat layer has no other
    state for it and an empty field would be filled by the enrichment.
    """
    regions: list[dict] = []
    layer = build_page_publications(
        page_id=page_id,
        text=text,
        page_title=page_title,
        categories=categories,
        attested_places=attested_places,
        regions_out=regions,
    )
    if not layer:
        return None
    first = layer["publications"][0]
    publisher = None
    if first.get("places"):
        publisher = first.get("publisher")
        if not publisher:
            mark = _flat((first.get("imprint") or "").split(",")[0])
            publisher = mark if mark in ABSENCE_MARKS else None
    # The raw regions the three values were read from, for the flat record's
    # field evidence (stage 03 field_spans).
    spans = {
        field: regions[0].get(path)
        for field, path in (
            ("year", ("year",)),
            ("publisher", ("publisher",)),
            ("page_count", ("extent",)),
        )
    }
    return {
        "year": first.get("year"),
        "page_count": (first.get("extent") or {}).get("numbered"),
        "publisher": publisher,
        "spans": {field: span for field, span in spans.items() if span},
    }


# The first statement of a page without a publication header: the lines the
# described publication stands in, read before any reprint list, translations
# section, review list, note or cross-reference that follows it.
_STATEMENT_SKIP_RE = re.compile(
    r"^\s*(?:\[\[Category:|\{\{DEFAULTSORT|</?lst\b|__[A-Z]+__\s*$|<!--|$)",
    re.IGNORECASE,
)
# A line that only labels what follows: a bold label ("'''Volume:'''",
# "'''English'''", "'''Printed in'''"), a wiki heading ("===German===") or the
# bracket of an original title alone ("[Joseph Fouché. Bildnis eines
# politischen Menschen]", page 1838).
_STATEMENT_LABEL_RE = re.compile(
    r"^\s*(?:'''[^']{1,60}'''\s*:?|={2,}[^=\n]+={2,}|\[[^\[\]\n]+\]\.?)\s*$"
)
# A statement that names its container on the next line ('"Virata" in:').
_STATEMENT_CONTINUES_RE = re.compile(r"\bin\s*:?\s*$")
# A bold header of any bracket, including the year forms the edition grammar
# does not read ("'''[196-?]: Foreign Languages Publishing House, Moscow'''")
# and a numbered header that states its year after the number ("'''[1]. 1934:
# Herbert Reichner Verlag, Wien'''", page 53).
_ANY_HEADER_RE = re.compile(
    r"'''\s*\[[^\]\n]*\]\s*[:.]\s*(?:(?:ca\.\s*)?\d{4}\s*[:.]\s*)?(.+?)'''"
)
# The bracket directly after a container title names the container's place
# ("in ''Neue Freie Presse'' [Wien]", "in [[Yin xian ji]] [Beijing 2000]").
_CONTAINER_BRACKET_RE = re.compile(
    r"\bin\s*:?\s*(?:''[^\n]+?''|\[\[[^\]\n]+\]\])\s*\[([^\[\]\n]+)\]"
)
# "Place: Publisher, YEAR" with any publisher wording, also inside a bracket
# ("[München: Heller Verlag 1936]", "Hamburg: Verlag Dr. Kovač, 2004").
_LOOSE_IMPRINT_RE = re.compile(
    r"(?:^|(?<=[.;\]]\s)|(?<=\[))([^\W\d_][^:;.\n\[\]]{0,40}):\s+"
    r"([^:\n\[\]]{2,80}?),?\s+\(?(?:1[789]|20)\d{2}\b",
    re.MULTILINE,
)


def _first_statement(text: str) -> str:
    """The lines of the first statement of a page.

    A label, heading or header joins the line after it, and a line ending in
    "in" joins the first item it introduces, one item and no more: the items
    after it are further printings, not the described publication. A line
    after the statement is not read, because author and list pages set one
    item per line without a blank line between them (page 2542).
    """
    lines = [line for line in text.splitlines() if not _STATEMENT_SKIP_RE.match(line)]
    if not lines:
        return ""
    statement = [lines[0]]
    index = 1
    while index < len(lines) and (
        _STATEMENT_LABEL_RE.match(statement[-1])
        or _STATEMENT_CONTINUES_RE.search(statement[-1])
    ):
        statement.append(lines[index])
        index += 1
    return "\n".join(statement)


# Legal forms a body imprint sets after the publisher's name.
_LEGAL_FORMS = CORPORATE_SUFFIXES | {"GmbH", "AG", "KG", "Inc", "Ltd"}
# The label words of the first publisher pattern in lib/patterns.py.
_PUBLISHER_LABEL_WORDS = frozenset(
    "Verlag Publisher Press Publishing Édition Éditions Editore Editorial Editora "
    "Wydawnictwo Издательство".split()
)


def _whole_word(value: str, text: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(value)}(?!\w)", text) is not None


def statement_bindings(text: str) -> dict:
    """The places, publishers and translator a rule reads from the first
    statement of a page without a publication header.

    A place is bound where it is the place of a header, of a "Place:
    Publisher, YEAR" imprint or of a place bracket, or stands as a word in the
    bracket after a container title; a publisher where it is the publisher of
    a header or an imprint; a translator where a translation credit of the
    statement names it.
    """
    statement = _first_statement(text)
    places: list[str] = []
    publishers: list[str] = []
    for match in _ANY_HEADER_RE.finditer(statement):
        place = location_from_header(match.group(1))
        if place:
            places.append(place)
        for imprint in split_imprint(match.group(1)):
            if imprint.publisher:
                publishers.append(_flat(imprint.publisher))
            if imprint.place:
                places.append(_flat(imprint.place))
    places += [match.group(1) for match in BRACKET_KNOWN_RE.finditer(statement)]
    places += [
        clean_location(match.group(1)) for match in BRACKET_PLACE_RE.finditer(statement)
    ]
    for match in _BODY_IMPRINT_RE.finditer(statement):
        publisher, chain_places = _imprint_chain(match.group("chain"))
        places += chain_places
        if publisher:
            publishers.append(publisher)
    for match in _LOOSE_IMPRINT_RE.finditer(statement):
        places.append(_flat(match.group(1)))
        publishers.append(_flat(match.group(2)))
    return {
        "statement": statement,
        "places": _unique(places),
        "containerBrackets": [
            match.group(1) for match in _CONTAINER_BRACKET_RE.finditer(statement)
        ],
        "publishers": _unique(publishers),
        "translator": extract_translator(statement),
    }


def unbound_flat_fields(text: str, values: dict[str, str]) -> list[str]:
    """The flat fields of a headerless page whose value no rule binds.

    A value the body patterns chose from anywhere in the text describes the
    page's publication only where its first statement carries it in one of
    the positions statement_bindings reads; elsewhere it can be a reprint, a
    translation, a lecturer's town or a person's name, and the field is a gap
    (knowledge/production-readiness.md, a gap before a wrong value).

    Both sides are compared as values leave the dump (encoding.source_value),
    so a whitespace run or quote escape of the dump decides nothing.
    """
    raw = statement_bindings(text)
    bindings = {
        "places": {source_value(place) for place in raw["places"]},
        "containerBrackets": [source_value(b) for b in raw["containerBrackets"]],
        "publishers": [source_value(bound) for bound in raw["publishers"]],
        "translator": source_value(raw["translator"] or ""),
    }
    values = {
        field: source_value(value) if isinstance(value, str) else value
        for field, value in values.items()
    }
    checks = {
        "location": lambda value: (
            value in bindings["places"]
            or any(
                _whole_word(value, bracket) for bracket in bindings["containerBrackets"]
            )
        ),
        # A legal form the source sets after a comma stays with the bound
        # publisher ("München: GRIN Verlag, GmbH, 2004", page 2511).
        # The label pattern leaves the label word out ("Hervas" of "Paris:
        # Éditions Hervas, 1997", page 3439); the value still names the
        # publisher the imprint binds.
        "publisher": lambda value: any(
            bound == value
            or (
                bound.startswith(value + ", ")
                and bound[len(value) + 2 :] in _LEGAL_FORMS
            )
            or (
                bound.endswith(" " + value)
                and bound[: -len(value) - 1] in _PUBLISHER_LABEL_WORDS
            )
            for bound in bindings["publishers"]
        ),
        # Stage 03c drops a closing initial's period ("J. L." -> "J. L").
        "translator": lambda value: (
            bool(bindings["translator"])
            and value.rstrip(".") == bindings["translator"].rstrip(".")
        ),
    }
    return [
        field
        for field, bound in checks.items()
        if values.get(field) and not bound(values[field])
    ]


def build_page_publications(
    page_id: int,
    text: str,
    page_title: str,
    categories: list[str],
    attested_places: set[str],
    delivered_text: str = "",
    regions_out: list | None = None,
) -> dict:
    """Structure one source page by publication and contribution.

    Returns an empty dict for a page whose source carries no publication header;
    that absence is the honest statement, not an empty publication. Every
    publication carries the displayed position of each of its values
    (valueSpans, lib/value_spans.py); ``delivered_text``, where given, must be
    the displayed text those positions address. ``regions_out`` receives the
    raw region of every value per publication, for stage 03.
    """
    if not text:
        return {}
    display = display_form(text)
    if delivered_text and delivered_text != display.text:
        raise ValueError(
            f"page {page_id}: the delivered text is not the displayed form"
        )
    segmented = segment_page(page_id, text, page_title)
    selectors = {
        annotation["oa:hasBody"]["@id"]: annotation["oa:hasTarget"]["oa:hasSelector"]
        for annotation in segmented["annotations"]
    }
    scopes = _language_scopes(text)
    category_languages = _category_languages(categories)
    links = category_links(text)

    built: list[tuple[int, int, dict]] = []
    parts_seen: dict[int, int] = {}
    for edition in segmented["editions"]:
        selector = selectors[edition["@id"]]
        start, end = selector["oa:start"], selector["oa:end"]
        # A compound header yields one edition per part, in header order.
        part = parts_seen.get(start, 0)
        parts_seen[start] = part + 1
        header_line = edition["klawiter:headerLine"]
        fields = parse_header_line(header_line)[part]
        language, language_region = _language_at(scopes, start)
        if language is None and len(category_languages) == 1:
            language = category_languages[0]
            # The language stands only in the category links that name it.
            language_region = [
                (link_start, link_end)
                for name, link_start, link_end in links
                if (found := CATEGORY_LANGUAGE_RE.search(name))
                and found.group(1) == language
            ]
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
                    language_region,
                    attested_places,
                    display,
                    part,
                ),
            )
        )
    if not built:
        return {}

    _attach_contributions(built, segmented["unsegmentedSections"], text)

    publications = []
    for _, _, publication in built:
        regions = publication.pop("_regions")
        if regions_out is not None:
            regions_out.append(regions)
        _put(publication, "reviewFlags", publication.pop("_flags"))
        publication["provenance"] = {
            key: "regex" for key in publication if key not in _PROVENANCE_EXCLUDED
        }
        publication = _unescaped(publication)
        publication["valueSpans"] = _value_spans(publication, regions, display)
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
        "nameVariants": _unescaped(_name_variants(text, _credited_names(publications))),
    }


def attach_edition_state(layer: dict, edition_states: dict[str, dict]) -> None:
    """Name the Gate-1 edition node and its review status per publication.

    A publication whose page lies outside the Gate-1 corpus has no edition
    node; it is rule-extracted and unreviewed, so it reports "proposed". An
    edition the agentic sample reviewed also names that review's disposition
    and its producer class, so the state never reads as a person's check.
    """
    for publication in layer.get("publications", []):
        edition_id = publication["id"].replace(
            "klawiter:publication/", "klawiter:edition/", 1
        )
        state = edition_states.get(edition_id)
        if state is not None:
            publication["editionId"] = edition_id
            if state.get("decision"):
                publication["reviewDecision"] = state["decision"]
                publication["reviewProducer"] = state["producer"]
        publication["reviewStatus"] = state["status"] if state else "proposed"


def review_flag_codes(layer: dict) -> list[str]:
    """The distinct review flag codes of a page's publications, sorted."""
    return sorted(
        {
            flag["code"]
            for publication in layer.get("publications", [])
            for flag in publication.get("reviewFlags", [])
        }
    )
