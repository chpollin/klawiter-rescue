"""Print-volume addresses the wiki text cites, read syntactically.

The compiler's printed bibliography gives every entry an address of section
and number, and the addenda append ``A1`` or ``A2`` to the section letter
("F 47", "HA1 34", "FA1 24a", "AA2 57"); knowledge/print-volumes.md describes
the scheme. Some wiki pages cite such addresses ("See F 533",
"[Der Amokläufer. F 1]", "GA1 85, p. 86"). This module extracts them as typed
references with their passage, for the later print/wiki concordance.

A cited address is resolved only syntactically into volume, section and entry
number. It is never matched against a print record and never asserts that the
wiki publication and the print entry are the same; its state is ``cites``. In
spot checks a cited address marked the translated work, a containment or a
looser relation, rarely the same publication (knowledge/print-volumes.md,
"Print and wiki").

What counts as a citation:
- an addendum address (``XA1 n``, ``XA2 n``) wherever it stands, because the
  code is specific enough;
- a main-volume address (``X n``) only in the compiler's citation notation:
  after "See", "Rep", "Cont." or "Correction to", inside a bracket at its start
  or after a full stop ("[Untergang eines Herzens. F 35]"), or continuing such
  a citation across separators and locators ("See H 670, G 131 & H 490").

Bare numbers after an address ("See G 201, 491, 492") stay unread, because the
notation does not say whether they are further entries or pages. Offsets are
character offsets into the page's source text in dump form, the text the
publication layer's ``sourceSlice`` addresses; text values have the dump's
quote escape resolved.
"""

from __future__ import annotations

import re

from lib.encoding import unescape_dump_quotes

CITATION_STATE = "cites"

# Section letters per volume, from the section scheme in
# knowledge/print-volumes.md: R exists only in Addendum I, Addendum II has no
# N, O, Q or R section.
_SECTIONS = {
    "": frozenset("ABCDEFGHIJKLMNOPQ"),
    "A1": frozenset("ABCDEFGHIJKLMNOPQR"),
    "A2": frozenset("ABCDEFGHIJKLMP"),
}
_VOLUMES = {"": "main-volume", "A1": "addendum-1", "A2": "addendum-2"}
# Addendum II numbers its entries only in AA2, DA2 and the symposia list (PA2);
# elsewhere code, title and year form the address, so a following number is a
# title word ("FA2 24 godziny 1928", page 560).
_NUMBERED_A2 = frozenset("ADP")

_ADDRESS_RE = re.compile(
    r"(?<![\w.\-/])(?P<section>[A-R])(?P<volume>A[12])?(?P<space> ?)"
    r"(?P<number>\d{1,4})(?P<suffix>[a-z])?(?:-(?P<end>\d{1,4})(?P<endsuffix>[a-z])?)?"
    r"(?![\w\-])"
)
_UNNUMBERED_A2_RE = re.compile(r"(?<![\w.\-/])(?P<section>[A-R])A2(?![\w\-])")
_TITLE_YEAR_RE = re.compile(r"\[\(?\d{4}\)?\]")
# "[A 8]" after a title, "Portuguese (A 74, 85, 98 / C 48, 49)" on page 2669.
_ENCLOSURES = (("bracket", "[", "]"), ("parenthesis", "(", ")"))
_SEE_BEFORE_RE = re.compile(
    r"(?:\b(?:See|see|SEE)(?:\s+also)?|\bRep(?:rinted)?|\bREP|\bCont\.(?:\s+of)?"
    r"|\bCorrection\s+to)\s*:?\s*$"
)
# What may stand between two addresses of one citation: separators, bare
# numbers, page/volume/number locators, a bracketed note and sentence stops.
_CONTINUATION_RE = re.compile(
    r"(?:[ \t,;&/=]|\band\b|\d+[a-z]?(?:-\d+[a-z]?)?|pp?\.|Vol\.|No\.|Nos\."
    r"|\(\d+\)|\[[^\[\]\n]*\]|\.(?=[ \t]))*"
)


def _enclosing(
    text: str, start: int, end: int, opening: str, closing: str
) -> tuple[int, int] | None:
    """The innermost bracket pair on the token's line that encloses it.

    A wiki link ("[[...]]") is no bracket of the citation notation.
    """
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    line_end = len(text) if line_end < 0 else line_end
    opener = text.rfind(opening, line_start, start)
    if opener < 0 or closing in text[opener:start]:
        return None
    closer = text.find(closing, end, line_end)
    if closer < 0 or opening in text[end:closer]:
        return None
    if text[opener - 1 : opener] == opening or text[closer + 1 : closer + 2] == closing:
        return None
    return opener, closer + 1


def _tokens(text: str) -> list[dict]:
    tokens = []
    for match in _ADDRESS_RE.finditer(text):
        section, volume = match.group("section"), match.group("volume") or ""
        if section not in _SECTIONS[volume]:
            continue
        if volume == "A2" and section not in _NUMBERED_A2:
            continue
        if volume and not match.group("space"):
            continue
        # "[A 1936 handwritten letter]", "[A 1962 Arabic film]": the article
        # and a year. An address is never followed by a word.
        rest = text[match.end() : match.end() + 8]
        if rest[:1] in (" ", "\t") and rest.lstrip(" \t")[:1].isalpha():
            continue
        # "See A1 43, p. 18" (page 2154) does not say whether A 1, A 143 or an
        # addendum is meant; an unspaced token followed by a number is unread.
        if not match.group("space") and rest[:1] == " " and rest[1:2].isdigit():
            continue
        number = match.group("number") + (match.group("suffix") or "")
        token = {
            "printAddress": f"{section}{volume} {number}",
            "printVolume": _VOLUMES[volume],
            "printSection": section,
            "printEntryNumber": int(match.group("number")),
            "start": match.start(),
            "end": match.end(),
            "addendum": bool(volume),
            "spaced": bool(match.group("space")),
        }
        if match.group("end"):
            end = match.group("end") + (match.group("endsuffix") or "")
            token["printAddress"] += f"-{end}"
            token["printEntryNumberEnd"] = int(match.group("end"))
        tokens.append(token)
    for match in _UNNUMBERED_A2_RE.finditer(text):
        if match.group("section") in _NUMBERED_A2:
            continue
        tokens.append(
            {
                "printAddress": f"{match.group('section')}A2",
                "printVolume": "addendum-2",
                "printSection": match.group("section"),
                "start": match.start(),
                "end": match.end(),
                "addendum": True,
                "spaced": True,
            }
        )
    return sorted(tokens, key=lambda token: token["start"])


def cited_print_addresses(text: str) -> list[dict]:
    """Every print address the source text cites, in source order."""
    text = text or ""
    citations: list[dict] = []
    previous: dict | None = None
    for token in _tokens(text):
        start, end = token["start"], token["end"]
        line_start = text.rfind("\n", 0, start) + 1
        keyword = _SEE_BEFORE_RE.search(text, line_start, start)
        enclosing = None
        for name, opening, closing in _ENCLOSURES:
            span = _enclosing(text, start, end, opening, closing)
            if span is None:
                continue
            lead = text[span[0] + 1 : start]
            # At the start of the bracket, or after a full stop inside it
            # ("[Untergang eines Herzens. F 35]").
            if not lead.strip() or lead.rstrip(" \t").endswith("."):
                enclosing = (name, span)
                break
        continues = (
            previous is not None
            and previous["_end"] <= start
            and "\n" not in text[previous["_end"] : start]
            and _CONTINUATION_RE.fullmatch(text, previous["_end"], start) is not None
        )
        if keyword:
            notation, passage = "see", [keyword.start(), end]
        elif not token["spaced"]:
            # "See D11, 38": the unspaced form is read only right after "See".
            continue
        elif continues:
            notation, passage = previous["citationNotation"], previous["_passage"]
            if notation in ("see", "plain"):
                passage[1] = end
        elif enclosing:
            notation, passage = enclosing[0], list(enclosing[1])
        elif token["addendum"]:
            notation, passage = "plain", [start, end]
        else:
            continue
        citation = {
            key: token[key]
            for key in (
                "printAddress",
                "printVolume",
                "printSection",
                "printEntryNumber",
                "printEntryNumberEnd",
            )
            if key in token
        }
        citation.update(
            citationState=CITATION_STATE,
            citationNotation=notation,
            sourceValue=text[start:end],
            sourceStart=start,
            sourceEnd=end,
            _end=end,
            _passage=passage,
        )
        citations.append(citation)
        previous = citation
    starts = [citation["sourceStart"] for citation in citations] + [len(text)]
    for index, citation in enumerate(citations):
        passage_start, passage_end = citation.pop("_passage")
        del citation["_end"]
        if "printEntryNumber" not in citation:
            # An unnumbered Addendum II address is code, title and year: the
            # passage runs to the year bracket that follows on the same line
            # before the next address ("LA2 Stefan Zweig - Triumph und Tragik
            # [1992]").
            end = citation["sourceEnd"]
            line_end = text.find("\n", end)
            line_end = len(text) if line_end < 0 else line_end
            year = _TITLE_YEAR_RE.search(
                text, end, min(line_end, end + 200, starts[index + 1])
            )
            if year:
                passage_end = max(passage_end, year.end())
        citation["passageText"] = unescape_dump_quotes(text[passage_start:passage_end])
        citation["passageStart"] = passage_start
        citation["passageEnd"] = passage_end
    return citations
