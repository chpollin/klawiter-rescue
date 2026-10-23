"""Boundary variants and majority segmentation shared by probes 2 and 3.

Each variant decides for every body line whether it opens a new unit, from one
signal only, so that their agreement measures how far the structure is
determined by the layout:

- number: a numbered entry start or a stub at the part's entry margin
- indent: the line sits at the part's left margin (hanging indent)
- gap: the vertical gap to the previous line exceeds GAP_FACTOR times the
  part's median line pitch; at a page top, where no gap exists, the line
  opens a unit when it sits at the left margin
- bold: the first font run is bold and the line sits at the left margin

Headings (mostly capitals, no leading number) open their own unit in every
variant and are counted separately. The consensus boundary is the majority
of the variants that carry a signal in the part (see _informative); ties
open a boundary.
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


def is_heading(line: dict) -> bool:
    text = line["text"].strip()
    letters = LETTERS.findall(text)
    if len(letters) < 3 or len(text) > 90 or numbered_start(line):
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
    has_numbers = any(numbered_start(line) or is_stub(line) for line in body)
    previous = None
    for line in body:
        at_left = abs(line["x0"] - left) <= 2
        new_page = previous is None or previous["page"] != line["page"]
        gap = None if new_page else line["top"] - previous["top"]
        line["heading"] = is_heading(line)
        line["votes"] = {
            "number": bool(numbered_start(line) or is_stub(line))
            if has_numbers
            else None,
            "indent": at_left,
            "gap": at_left if gap is None else gap > GAP_FACTOR * pitch,
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


def consensus(line: dict) -> bool:
    if line["heading"]:
        return True
    cast = [line["votes"][v] for v in line["active"]]
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
