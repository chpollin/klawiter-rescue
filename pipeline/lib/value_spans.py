"""Where each published value stands in the text the record card displays.

The card shows ``fullBibliographicEntry``, the page text after stage 03 has
removed category links, the sort key and the wiki markup. Every extractor
reads the raw (dump-form) text, so the offsets a parser holds are raw
offsets. ``display_form`` replays the removal steps of ``lib.wiki_parser``
on the raw text and keeps, for every displayed character, the raw offset it
came from; a raw passage then maps to its displayed passage without any
search.

A value is located from the passage its parser read it from (its region):

- the region's displayed text is the value: the span is exact;
- the value occurs once, as a whole word, inside the region: the span is
  that occurrence (``locator: region``);
- the value occurs once inside the region in a form a declared rule turns
  into it (DERIVATIONS): the span carries ``derivedFrom``, the exact
  displayed passage, and ``derivation``, the rule;
- where no parser region exists (an enrichment value), the value's single
  occurrence in the displayed text is a labelled fallback
  (``locator: search``);
- otherwise the value carries a gap reason (GAP_REASONS) and no offsets. A
  region that lies entirely in markup the display removes, a category link,
  gives the raw character range instead (``rawStart``, ``rawEnd``).

A first match is never taken. knowledge/data.md holds the contract.
"""

from __future__ import annotations

import re
from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache

from lib.encoding import source_value
from lib.wiki_parser import (
    CATEGORY_LINK_RE,
    CATEGORY_STRIP,
    MARKUP_STEPS,
    SORTKEY_STRIP,
    category_name,
    remove_wiki_markup,
)

# Gap reasons, closed: tests/test_value_spans.py and the frontend contract
# test hold the same set.
GAP_REASONS = (
    # The value occurs more than once in its region, or, without a region,
    # in the displayed text; "count" says how often.
    "repeated",
    # The region holds the value in no form a declared rule derives it by.
    "not-verbatim",
    # The value stands only in markup the displayed text removes; the raw
    # range is given.
    "category-markup",
    # The region lies in removed markup that is no category link.
    "not-displayed",
    # The value is the wiki page title of the page table, not read from the
    # text (stage 03 title fallback).
    "page-title",
    # A value an editor set; the patch names no passage.
    "editor-value",
)
# Declared derivations of a value from its passage, closed like the gaps.
DERIVATIONS = (
    # Whitespace runs or line breaks the display collapses or keeps.
    "whitespace",
    # Wiki markup the value keeps and the display removes.
    "markup",
    # A number read from a notation with leading zeros.
    "number",
    # The BCP-47 subtag of the language name in the passage.
    "language-code",
    # A form stage 03c mapped or trimmed (location and publisher tables,
    # translator suffixes).
    "normalised",
    # The page a link names, where the display shows its label or the wiki
    # resolved it to a canonical title.
    "link-target",
)


@dataclass(frozen=True)
class Display:
    """The displayed text and, per character, the raw offset it came from."""

    raw: str
    text: str
    index: tuple[int, ...]

    def span(self, raw_start: int, raw_end: int) -> tuple[int, int]:
        """The displayed characters whose raw offsets lie in [raw_start, raw_end)."""
        return bisect_left(self.index, raw_start), bisect_left(self.index, raw_end)


def _literal_index(index: list[int], match: re.Match, position: int, raw_len: int):
    """Raw offset of the k-th character a literal replacement inserts: the
    matched character at that position, else the last matched one."""
    start, end = match.start(), match.end()
    if start + position < end:
        return index[start + position]
    if end > start:
        return index[end - 1]
    return index[start] if start < len(index) else raw_len


def _tracked_step(step, text: str, index: list[int], raw_len: int):
    pattern, replacement = step
    out_text: list[str] = []
    out_index: list[int] = []
    position = 0
    for match in pattern.finditer(text):
        out_text.append(text[position : match.start()])
        out_index.extend(index[position : match.start()])
        if isinstance(replacement, int):
            out_text.append(match.group(replacement))
            out_index.extend(index[match.start(replacement) : match.end(replacement)])
        else:
            out_text.append(replacement)
            out_index.extend(
                _literal_index(index, match, k, raw_len)
                for k in range(len(replacement))
            )
        position = match.end()
    out_text.append(text[position:])
    out_index.extend(index[position:])
    return "".join(out_text), out_index


def _tracked_strip(text: str, index: list[int]):
    lead = len(text) - len(text.lstrip())
    kept = text.strip()
    return kept, index[lead : lead + len(kept)]


@lru_cache(maxsize=16)
def cleaned_form(raw: str) -> Display:
    """The page text after extract_categories and extract_defaultsortkey, the
    text stage 03's title, original-title, reference and section readers
    read, with its map to the raw text."""
    raw = raw or ""
    text, index = raw, list(range(len(raw)))
    for step in (CATEGORY_STRIP, SORTKEY_STRIP):
        text, index = _tracked_step(step, text, index, len(raw))
        text, index = _tracked_strip(text, index)
    return Display(raw, text, tuple(index))


@lru_cache(maxsize=16)
def display_form(raw: str) -> Display:
    """The delivered text of a page with its map to the raw text.

    Runs exactly the steps stage 03 runs: extract_categories, then
    extract_defaultsortkey, then remove_wiki_markup, each with its strip.
    """
    cleaned = cleaned_form(raw)
    text, index = cleaned.text, list(cleaned.index)
    if text:
        for step in MARKUP_STEPS:
            text, index = _tracked_step(step, text, index, len(cleaned.raw))
        text, index = _tracked_strip(text, index)
    return Display(cleaned.raw, text, tuple(index))


def raw_span(form: Display, start: int, end: int) -> tuple[int, int]:
    """The raw span of the characters start to end of a tracked form."""
    if start >= end:
        position = form.index[start] if start < len(form.index) else len(form.raw)
        return position, position
    return form.index[start], form.index[end - 1] + 1


def _edges(value: str) -> tuple[str, str]:
    """Boundaries that keep a value from starting or ending inside a word, or
    a number inside a number ("659" in "659p." counts, in "1659" not)."""
    lead = trail = ""
    if value[:1].isdigit():
        lead = r"(?<!\d)"
    elif re.match(r"\w", value):
        lead = r"(?<!\w)"
    if value[-1:].isdigit():
        trail = r"(?!\d)"
    elif re.search(r"\w$", value):
        trail = r"(?!\w)"
    return lead, trail


def _word_pattern(value: str) -> re.Pattern[str]:
    lead, trail = _edges(value)
    return re.compile(lead + re.escape(value) + trail)


def _spaced_pattern(value: str) -> re.Pattern[str] | None:
    tokens = value.split()
    if len(tokens) < 2:
        return None
    lead, trail = _edges(value)
    return re.compile(lead + r"\s+".join(map(re.escape, tokens)) + trail)


def _derived_forms(value: str):
    """The patterns a value is found by where its exact form is absent, each
    with the derivation it declares: whitespace runs the display collapses or
    breaks, and wiki markup the display removes."""
    spaced = _spaced_pattern(value)
    if spaced is not None:
        yield spaced, "whitespace"
    if value.isdigit():
        # A number read from a notation with leading zeros ("pp. 001-003").
        yield re.compile(rf"(?<!\d)0+{value}(?!\d)"), "number"
    stripped = remove_wiki_markup(value)
    if stripped and stripped != value:
        yield _word_pattern(stripped), "markup"
        spaced = _spaced_pattern(stripped)
        if spaced is not None:
            yield spaced, "markup"


def _find(value: str, text: str, start: int, end: int):
    """The single occurrence of a value between start and end: (span,
    derivation), or (None, count) where it is absent (0) or repeated."""
    found = _occurrences(_word_pattern(value), text, start, end)
    if len(found) == 1:
        return found[0], None
    if found:
        return None, len(found)
    for pattern, derivation in _derived_forms(value):
        found = _occurrences(pattern, text, start, end)
        if len(found) == 1:
            return found[0], derivation
        if found:
            return None, len(found)
    return None, 0


def _trimmed(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _occurrences(pattern: re.Pattern[str], text: str, start: int, end: int):
    return [(m.start(), m.end()) for m in pattern.finditer(text, start, end)]


def gap(value: str, reason: str, **extra) -> dict:
    if reason not in GAP_REASONS:
        raise ValueError(f"undeclared gap reason {reason!r}")
    return {"value": value, "gap": reason, **extra}


def locate(
    value,
    display: Display,
    region: tuple[int, int] | None,
    derivation: str | None = None,
) -> dict:
    """The evidence entry of one value read from the raw region.

    ``derivation`` names the rule that turns the region's wording into the
    value where the value is no verbatim part of it (a language code, a
    mapped place); without it such a value is a gap.
    """
    value = str(value)
    text = display.text
    if region is None:
        return _search(value, display)
    start, end = _trimmed(text, *display.span(*region))
    if start >= end:
        raw_start, raw_end = region
        if display.raw.startswith("[[Category:", raw_start):
            return gap(value, "category-markup", rawStart=raw_start, rawEnd=raw_end)
        return gap(value, "not-displayed", rawStart=raw_start, rawEnd=raw_end)
    if text[start:end] == value:
        return {"value": value, "textStart": start, "textEnd": end}
    span, detail = _find(value, text, start, end)
    if span:
        return _entry(value, text, span, detail, "region")
    if detail:
        return gap(value, "repeated", count=detail)
    if derivation:
        return _entry(value, text, (start, end), derivation, None)
    return gap(value, "not-verbatim")


def _entry(value: str, text: str, span, derivation, locator) -> dict:
    entry = {"value": value, "textStart": span[0], "textEnd": span[1]}
    if derivation:
        if derivation not in DERIVATIONS:
            raise ValueError(f"undeclared derivation {derivation!r}")
        entry["derivedFrom"] = text[span[0] : span[1]]
        entry["derivation"] = derivation
    if locator:
        entry["locator"] = locator
    return entry


def _search(value: str, display: Display) -> dict:
    """The labelled fallback for a value no parser region carries."""
    span, detail = _find(value, display.text, 0, len(display.text))
    if span:
        return _entry(value, display.text, span, detail, "search")
    if detail:
        return gap(value, "repeated", count=detail)
    return gap(value, "not-verbatim")


def category_links(raw: str) -> list[tuple[str, int, int]]:
    """Every category link of the raw text with its name and raw span, in the
    order and with the names lib.wiki_parser.extract_categories reads."""
    links = []
    for match in CATEGORY_LINK_RE.finditer(raw or ""):
        name = category_name(match.group(1))
        if name:
            links.append((name, match.start(), match.end()))
    return links


def category_gap(value: str, spans: list[tuple[int, int]]) -> dict:
    """A value that stands only in category links: the raw range of the one
    link, or the number of links where several state it."""
    if len(spans) == 1:
        return gap(value, "category-markup", rawStart=spans[0][0], rawEnd=spans[0][1])
    return gap(value, "category-markup", count=len(spans))


def displayed_span(display: Display, raw_start: int, raw_end: int):
    """The displayed passage of a raw passage, trimmed of edge whitespace, or
    None where nothing of it is displayed."""
    start, end = _trimmed(display.text, *display.span(raw_start, raw_end))
    return (start, end) if start < end else None


def entry_holds(entry: dict, text: str) -> bool:
    """The invariant of one evidence entry against the displayed text."""
    if "gap" in entry:
        return (
            entry["gap"] in GAP_REASONS
            and "textStart" not in entry
            and "textEnd" not in entry
        )
    start, end = entry["textStart"], entry["textEnd"]
    if not 0 <= start < end <= len(text):
        return False
    if ("derivedFrom" in entry) != ("derivation" in entry):
        return False
    if "derivation" in entry and entry["derivation"] not in DERIVATIONS:
        return False
    return text[start:end] == entry.get("derivedFrom", entry["value"])


# The page-level fields of the frontend record whose values stage 03 reads
# from the text: frontend key -> (field_spans key, derivation of a value its
# region holds in another form).
RECORD_SCALAR_FIELDS = {
    "title": ("title", None),
    "originalTitle": ("original_title", None),
    "year": ("year", None),
    "publisher": ("publisher", "normalised"),
    "location": ("location", "normalised"),
    "pageCount": ("page_count", None),
    "translator": ("translator", "normalised"),
    "language": ("language", None),
    "languageCode": ("language", "language-code"),
    "mainCategory": ("main_category", None),
}
RECORD_LIST_FIELDS = {
    "categories": ("categories", None),
    "allYears": ("all_years", None),
    "allLocations": ("all_locations", None),
    "seeAlso": ("see_also", "link-target"),
    "reprints": ("reprints", None),
    "translations": ("translations", None),
    "contentItems": ("content_items", None),
}


def _list_entry(value, ordinal, total, candidates, display, derivation):
    """The entry of the ordinal-th of total equal list values, given the raw
    spans of the parser's readings of that value."""
    if len(candidates) == total:
        return locate(value, display, tuple(candidates[ordinal]), derivation)
    if not candidates:
        return locate(value, display, None)
    if display.raw.startswith("[[Category:", candidates[0][0]):
        return category_gap(str(value), [tuple(span) for span in candidates])
    return gap(str(value), "repeated", count=len(candidates))


def record_evidence(
    entry: dict,
    field_spans: dict,
    display: Display,
    page_title: str = "",
    sources: dict | None = None,
) -> dict:
    """The evidence of every page-level value of a frontend record.

    ``field_spans`` is stage 03's column: a scalar field's raw region, or a
    list field's [value, start, end] readings. ``sources`` maps (field,
    published list value) to the other forms it was read under: the
    reference a canonical See title was resolved from, the variants stage
    03c mapped to a place. A value without a region is located by the
    labelled search; a title taken from the page table is the gap page-title.
    """
    sources = sources or {}
    evidence: dict[str, list[dict]] = {}
    for key, (span_key, derivation) in RECORD_SCALAR_FIELDS.items():
        value = entry.get(key)
        if value in (None, ""):
            continue
        region = field_spans.get(span_key)
        if (
            region is None
            and key == "title"
            and str(value) == source_value(remove_wiki_markup(page_title))
        ):
            evidence[key] = [gap(str(value), "page-title")]
            continue
        region = tuple(region) if region else None
        evidence[key] = [locate(value, display, region, derivation)]
    for key, (span_key, derivation) in RECORD_LIST_FIELDS.items():
        values = entry.get(key) or []
        readings: dict[str, list] = {}
        for item, start, end in field_spans.get(span_key, []):
            readings.setdefault(source_value(str(item)), []).append((start, end))
        # Each published value with the other forms it was read under.
        names = [
            (
                source_value(str(value)),
                *(source_value(str(other)) for other in sources.get((key, value), [])),
            )
            for value in values
        ]
        seen: dict[tuple, int] = {}
        entries = []
        for value, name in zip(values, names, strict=True):
            ordinal = seen.get(name, 0)
            seen[name] = ordinal + 1
            found = sorted(span for form in name for span in readings.get(form, []))
            declared = derivation
            if found and not readings.get(name[0]):
                # Read only under another form (a mapped place).
                declared = derivation or "normalised"
            entries.append(
                _list_entry(value, ordinal, names.count(name), found, display, declared)
            )
        if entries:
            evidence[key] = entries
    citations = entry.get("printAddressCitations") or []
    if citations:
        evidence["printAddressCitations"] = [
            locate(
                citation["sourceValue"],
                display,
                (citation["sourceStart"], citation["sourceEnd"]),
            )
            for citation in citations
        ]
    return evidence
