"""Boundary variants and majority segmentation shared by probes 2 and 3.

Each variant decides for every body line whether it opens a new unit, from one
signal only, so that their agreement measures how far the structure is
determined by the layout:

- number: a numbered entry start or a stub at the part's entry margin
- indent: the line sits at the part's left margin (hanging indent)
- gap: the vertical gap to the previous line exceeds GAP_FACTOR times the
  part's median line pitch; at a page top no gap exists and the variant
  abstains, so that it does not merely repeat the indent signal there
- bold: the first font run is bold and the line sits at the left margin

Headings (mostly capitals, no leading number) open their own unit in every
variant and are counted separately.

The boundary decision (consensus) adds three rules from a survey of the
development pages (2026-10-23) to the vote:

- R1: a sub-item opener ("[5].", "[X].", "Vol. 2.", "Contents:", "Reprinted
  in:" and similar labels) never opens a unit; it starts an object inside one.
- R2: in a part without running numbers, a mid-page line opens a unit only
  after a vertical gap; bold alone is a title wrapping onto the next line.
- R3: at a page top of such a part, the line opens a unit when the previous
  page ends in a heading, or in closing punctuation that is no abbreviation
  and either falls short of the right margin or is followed by a bold opener
  after a non-bold end.
Parts with running numbers keep the majority of their informative variants,
ties opening a boundary, except that a line which is neither a numbered start
nor a stub and opens with a digit, a lowercase letter or a bracket continues
the entry ("1966), 307-312 [DAP].", "[RJS].").
"""

import re
from collections import Counter
from statistics import median

from _common import is_bold
from _lines import is_stub, numbered_start

GAP_FACTOR = 1.5
MAX_RATE = 0.8
VARIANTS = ("number", "indent", "gap", "bold")
LETTERS = re.compile(r"[^\W\d_]")
SUB_ITEM = re.compile(
    r"^(?:\[(?:\d+[a-z]?|X|[a-z])\]\s?\.|Vols?\.\s?\(?\d+\)?\.?\s|Kassette\b|"
    r"(?:Contents|Con-|Reprinted in|Printed in|Reviews? of|Reviews|Excerpts|EXCERPTS|"
    r"(?:Non-)?Fischer Editions/Reprints|Editions/Reprints|FIE|REP|EXC|REV|"
    r"TRANSLATIONS?)\s?:|of:|in:)"
)
CLOSED = re.compile(r"[.\])]\s*$")
ABBREVIATION = re.compile(
    r"\b(?:[A-Z]|Nos?|Vols?|pp?|Tr|Trl|[Ee]ds?|impr|ca|St|Dr)\.\s*$"
)
SHORT_LINE = 30
CONTINUATION_OPENER = re.compile(r"^[\d\[a-z(]")


def is_heading(line: dict) -> bool:
    text = line["text"].strip()
    letters = LETTERS.findall(text)
    if len(letters) < 3 or len(text) > 90 or numbered_start(line):
        return False
    # Sigla and citations in capitals ("[RJS].", "1966), 307-312 [DAP].") are
    # wrapped tails, not headings.
    if re.match(r"^[\d\[(]", text):
        return False
    upper = sum(1 for ch in letters if ch.isupper())
    return upper / len(letters) >= 0.8


def _part_geometry(lines: list[dict]) -> tuple[float, float]:
    """Left margin and median line pitch of one part's body lines."""
    xs = Counter(round(line["x0"]) for line in lines)
    floor = min(xs)
    common = [x for x, n in xs.items() if n >= 0.05 * len(lines)]
    left = min(common) if common else floor
    pitches = [
        b["top"] - a["top"]
        for a, b in zip(lines, lines[1:])
        if a["page"] == b["page"] and 0 < b["top"] - a["top"] < 40
    ]
    return left, median(pitches) if pitches else 14.0


def votes(body: list[dict]) -> list[dict]:
    """Attach per-variant boundary votes to each body line of one part."""
    left, pitch = _part_geometry(body)
    right = sorted(ln["x1"] for ln in body)[int(0.95 * (len(body) - 1))]
    has_numbers = any(numbered_start(line) or is_stub(line) for line in body)
    previous = None
    for line in body:
        line["numbered_part"] = has_numbers
        line["page_top"] = previous is None or previous["page"] != line["page"]
        line["previous"] = previous
        line["right"] = right
        at_left = abs(line["x0"] - left) <= 2
        new_page = previous is None or previous["page"] != line["page"]
        gap = None if new_page else line["top"] - previous["top"]
        line["heading"] = is_heading(line)
        line["votes"] = {
            "number": bool(numbered_start(line) or is_stub(line))
            if has_numbers
            else None,
            "indent": at_left,
            "gap": None if gap is None else gap > GAP_FACTOR * pitch,
            "bold": at_left and is_bold(line["runs"][0][0]),
        }
        previous = line
    active = _informative(body)
    for line in body:
        line["active"] = active
    return body


def _informative(body: list[dict]) -> tuple[str, ...]:
    """Variants whose boundary rate carries a signal in this part.

    A variant that fires on almost every line (no hanging indent) or on far
    fewer lines than the others (entry starts not set in bold) cannot
    separate entries there; counting it would turn every entry into residue.
    """
    rates = {}
    for variant in VARIANTS:
        cast = [ln["votes"][variant] for ln in body if ln["votes"][variant] is not None]
        if cast:
            rates[variant] = sum(cast) / len(body)
    reference = median(rates.values()) if rates else 0
    return tuple(v for v, rate in rates.items() if 0.25 * reference <= rate <= MAX_RATE)


def _page_top_start(line: dict) -> bool:
    """R3: decide a page-top line of an unnumbered part from the previous page."""
    previous = line["previous"]
    if previous is None or previous["heading"]:
        return True
    text = previous["text"].rstrip()
    if not CLOSED.search(text) or ABBREVIATION.search(text):
        return False
    short = previous["x1"] < line["right"] - SHORT_LINE
    bold_opener = is_bold(line["runs"][0][0]) and not is_bold(previous["runs"][-1][0])
    return short or bold_opener


def consensus(line: dict) -> bool:
    if line["heading"]:
        return True
    if SUB_ITEM.match(line["text"].lstrip()):
        return False
    if not line["numbered_part"]:
        if line["page_top"]:
            return _page_top_start(line)
        return bool(line["votes"]["gap"])
    if line["votes"]["number"] is False and CONTINUATION_OPENER.match(line["text"]):
        return False
    cast = [line["votes"][v] for v in line["active"] if line["votes"][v] is not None]
    return bool(cast) and any(cast) and sum(cast) * 2 >= len(cast)


def units(body: list[dict]) -> list[list[dict]]:
    """Group body lines into units at consensus boundaries."""
    groups: list[list[dict]] = []
    for line in body:
        if not groups or consensus(line):
            groups.append([line])
        else:
            groups[-1].append(line)
    return groups


def body_by_part(lines: list[dict]) -> dict[str, list[dict]]:
    parts: dict[str, list[dict]] = {}
    for line in lines:
        if line["kind"] == "body" and not line["furniture"]:
            parts.setdefault(line["part"], []).append(line)
    return parts
