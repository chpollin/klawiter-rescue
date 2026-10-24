"""Structured statements of a page's translations section.

A translations section lists, under one bold heading per language, the
translations of the page's work: a quoted title, the volume it is printed in
with its place and year in a bracket, or a book with its own imprint. Each
printing becomes one statement whose every value carries the span of the
dump-form source text it was read from. A value the rules cannot read is
absent, and a language paragraph they cannot read at all still yields one
statement with its language and its passage, so no heading is lost.
"""

from __future__ import annotations

import hashlib
import re

from lib.encoding import unescape_dump_quotes
from lib.patterns import credited_name
from lib.vocabulary import language_to_iso
from lib.wiki_parser import _LANGUAGE_HEAD, _TRANSLATIONS_HEAD, _wiki_section

_HEADING_RE = re.compile(rf"(?m)^'''(?P<head>{_LANGUAGE_HEAD})")
# A qualifier the source sets after the bold heading ("'''Serbian'''
# (Serbo-Croatian):", page 7166; "'''Croatian:''' (Serbo-Croatian).", page 7224).
_QUALIFIER_RE = re.compile(r"\s*\((?P<qualifier>[^()\n]{2,40})\)\s*[:.]?")
# Two translations of one language are set apart by " // " (page 7224).
_TRANSLATION_SPLIT_RE = re.compile(r"\s+//\s+")
# A numbered printing of one translation ("in [1]. [[A]] […]. [2]. [[B]] […]").
_PRINTING_MARK_RE = re.compile(r"\[\d+\]\.")
_QUOTED_TITLE_RE = re.compile(r'\\"(?P<title>[^"\n]+?)\\"|“(?P<curly>[^”\n]+?)”')
_ITALIC_TITLE_RE = re.compile(r"(?<!')''(?P<title>[^'\n][^\n]*?)''(?!')")
# The volume a translation is printed in and the bracket after it.
_CONTAINER_RE = re.compile(
    r"(?:\[\[(?P<link>[^\]\n]+)\]\]|(?<!')''(?P<italic>[^'\n][^\n]*?)''(?!'))"
    r"\s*,?\s*\[(?P<bracket>[^\[\]\n]+)\]"
)
# A book's own imprint, "Place: Publisher, YEAR" ("Dimashq [Damascus]: Dār
# al-Yaqẓah …, 1950", page 4411).
_IMPRINT_RE = re.compile(
    r"(?:^|[.;\]]\s+)(?P<place>[^\W\d_][^:;.\n]{0,60}?):\s+"
    r"(?P<publisher>[^:\n]{2,120}?),\s*(?P<year>(?:1[789]|20)\d{2})\b"
)
_AFTER_IN_RE = re.compile(r"\bin\s*:?\s*$")
_PLAIN_LANGUAGE_RE = re.compile(
    r"^[:\s]*(?:''')?(?P<language>[A-Z][a-z]+)(?:''')?\s*[:,]?"
)
_CREDIT_RE = re.compile(r"\b[Tt]ranslated\s+(?:from\s+\w+\s+)?by\s+")
_YEAR_RE = re.compile(r"(?:1[789]|20)\d{2}")


def _span(base: int, match: re.Match, group: str | int = 0) -> list[int]:
    return [base + match.start(group), base + match.end(group)]


def _clean(value: str) -> str:
    return " ".join(unescape_dump_quotes(value).split())


def _bracket_fields(bracket: str, start: int) -> dict:
    """Place and year of the bracket after a volume ("[Paris, 1996]").

    The year is read only where the bracket states one four-digit year; a
    range, a list or a misprint ("[Athēna, 19556]", page 7224) stays as the
    raw year statement.
    """
    fields: dict = {}
    head, _, tail = bracket.rpartition(",")
    if not head:
        head, tail = bracket, ""
        number = re.search(r"(?:^|\s)(\d{4})$", bracket)
        if number:
            head, tail = bracket[: number.start()], number.group(1)
    place = head.strip()
    if place and not re.search(r"\d", place):
        offset = start + bracket.index(place)
        fields["place"] = (_clean(place), [offset, offset + len(place)])
    tail = tail.strip()
    if tail:
        offset = start + bracket.rindex(tail)
        span = [offset, offset + len(tail)]
        if re.fullmatch(r"\d{4}", tail) and _YEAR_RE.fullmatch(tail):
            fields["year"] = (int(tail), span)
        elif _YEAR_RE.search(tail):
            fields["yearRaw"] = (_clean(tail), span)
    return fields


def _translator(text: str, base: int) -> tuple[str, list[int]] | None:
    match = _CREDIT_RE.search(text)
    if not match:
        return None
    name = credited_name(text, match.end())
    if not name:
        return None
    start = base + match.end()
    return _clean(name), [start, start + len(name)]


def _container(text: str) -> re.Match | None:
    """The volume a printing stands in: after "in", or opening a numbered
    printing. An italic title with its gloss bracket ("''Al-Sāqiṭūn''
    [Creatures That Once Were Men]", page 4411) is no container."""
    for match in _CONTAINER_RE.finditer(text):
        before = text[: match.start()]
        if not before.strip() or _AFTER_IN_RE.search(before):
            return match
    return None


def _title(text: str, base: int) -> tuple[str, list[int]] | None:
    """The quoted title, or for a book without a container the italic one."""
    match = _QUOTED_TITLE_RE.search(text)
    group = "title"
    if match and match.group("title") is None:
        group = "curly"
    if not match:
        match = _ITALIC_TITLE_RE.search(text)
        group = "title"
    if not match:
        return None
    return _clean(match.group(group)), _span(base, match, group)


def _printing(text: str, base: int, head: tuple[str, int]) -> dict:
    """The values of one printing passage, each with its span; the head of
    its translation supplies a title and a credit the passage lacks."""
    values: dict = {}
    head_text, head_base = head
    title = _title(text, base) or _title(head_text, head_base)
    if title:
        values["title"] = title
    container = _container(text)
    if container:
        group = "link" if container.group("link") is not None else "italic"
        name = container.group(group).split("|")[0]
        values["container"] = (_clean(name), _span(base, container, group))
        bracket_start = base + container.start("bracket")
        values.update(_bracket_fields(container.group("bracket"), bracket_start))
    else:
        imprint = _IMPRINT_RE.search(text)
        if imprint:
            values["place"] = (
                _clean(imprint.group("place")),
                _span(base, imprint, "place"),
            )
            values["publisher"] = (
                _clean(imprint.group("publisher")),
                _span(base, imprint, "publisher"),
            )
            values["year"] = (int(imprint.group("year")), _span(base, imprint, "year"))
    translator = _translator(text, base) or _translator(head_text, head_base)
    if translator:
        values["translator"] = translator
    return values


def _slice(text: str, start: int, end: int) -> dict:
    return {
        "start": start,
        "end": end,
        "sha256": hashlib.sha256(text[start:end].encode("utf-8")).hexdigest(),
    }


def _unheaded_statements(text: str, body_start: int, body: str) -> list[dict]:
    """A section without bold language headings, one statement per line.

    Such sections set the language plainly ("Italian: [[Uomini e destini]]
    [1993]", page 160) or indented ("::'''Bulgarian'''", page 5118), or list
    print addresses per language (page 2154). The language is read only where
    a known language name opens the line; every other value as in a headed
    section.
    """
    statements = []
    for line in re.finditer(r"[^\n]+", body):
        stripped = line.group(0).strip()
        if not stripped or stripped.startswith("<"):
            continue
        base = body_start + line.start()
        statement: dict = {}
        spans: dict = {}
        opening = _PLAIN_LANGUAGE_RE.match(line.group(0))
        if opening and language_to_iso(opening.group("language")):
            statement["language"] = opening.group("language")
            statement["languageCode"] = language_to_iso(opening.group("language"))
            spans["language"] = _span(base, opening, "language")
        for field, (value, span) in _printing(line.group(0), base, ("", base)).items():
            statement[field] = value
            spans[field] = span
        statement["spans"] = spans
        statement["sourceSlice"] = _slice(
            text, base, base + len(line.group(0).rstrip())
        )
        statements.append(statement)
    return statements


def translation_statements(text: str) -> list[dict]:
    """Every translation the page's translations section lists, one statement
    per printing, in source order."""
    block = _wiki_section(text or "", _TRANSLATIONS_HEAD, _LANGUAGE_HEAD)
    if not block:
        return []
    body_start, body_end = block.start(1), block.end(1)
    body = text[body_start:body_end]
    headings = list(_HEADING_RE.finditer(body))
    if not headings:
        return _unheaded_statements(text, body_start, body)
    statements = []
    for index, heading in enumerate(headings):
        segment_start = body_start + heading.end()
        segment_end = (
            body_start + headings[index + 1].start()
            if index + 1 < len(headings)
            else body_end
        )
        label = heading.group("head").rstrip(":'")
        head_start = body_start + heading.start("head")
        language_span = [head_start, head_start + len(label)]
        segment = text[segment_start:segment_end]
        qualifier = _QUALIFIER_RE.match(segment)
        offset = 0
        if qualifier:
            label = f"{label} ({qualifier.group('qualifier')})"
            offset = qualifier.end()
        language = {"language": label}
        code = language_to_iso(label)
        if code:
            language["languageCode"] = code
        stripped = segment.rstrip()
        content = segment[offset : len(stripped)]
        content_base = segment_start + offset
        read = []
        position = 0
        for part in _TRANSLATION_SPLIT_RE.split(content):
            part_start = content.index(part, position)
            position = part_start + len(part)
            part_base = content_base + part_start
            marks = list(_PRINTING_MARK_RE.finditer(part))
            if marks:
                head = (part[: marks[0].start()], part_base)
                pieces = [
                    (
                        mark.end(),
                        marks[i + 1].start() if i + 1 < len(marks) else len(part),
                    )
                    for i, mark in enumerate(marks)
                ]
                # The first printing can stand before the first number ("in
                # [[A]] […]. [2]. [[B]] […]", page 7166).
                if _container(head[0]):
                    pieces.insert(0, (0, marks[0].start()))
            else:
                head = ("", part_base)
                pieces = [(0, len(part))]
            for start, end in pieces:
                values = _printing(part[start:end], part_base + start, head)
                if not values:
                    continue
                statement = {**language}
                spans = {"language": language_span}
                for field, (value, span) in values.items():
                    statement[field] = value
                    spans[field] = span
                statement["spans"] = spans
                statement["sourceSlice"] = _slice(
                    text, part_base + start, part_base + end
                )
                read.append(statement)
        if not read:
            # A paragraph the rules cannot read keeps its language and passage.
            read.append(
                {
                    **language,
                    "spans": {"language": language_span},
                    "sourceSlice": _slice(
                        text, segment_start, segment_start + len(stripped)
                    ),
                }
            )
        statements.extend(read)
    return statements
