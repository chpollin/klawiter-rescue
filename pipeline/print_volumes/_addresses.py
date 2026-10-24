"""The compiler's address grammar: address tokens, their lists and ranges, and the notation before them.

An address is a section letter, an optional volume suffix and a number with an
optional letter (F 47, HA1 34, FA1 24a). Lists and ranges share the letter of
their head (A 70, 77, 85; G 851-854). Ranges wider than MAX_RANGE are not
expanded, as they are more likely misread tokens than real ranges. The
notation before an address (See, Rep:, Contents:, Correction to, Cont., a bare
bracket) types the reference; a list separator continues the type before it.
Shared by the address probe, the benchmark and the claim stage.
"""

import re
from collections import Counter

SUFFIX_TO_VOLUME = {"": "I", "A1": "A1", "A2": "A2"}
# Address head, then optional continuation items sharing its section letter.
# An item locator ("HA1 35[1], 38") stays inside the group only where the
# list goes on; a final one is read as the address's locator.
ITEM = r"\d{1,4}[a-z]?(?:\s?-\s?\d{1,4}[a-z]?)?\*?(?:\[\d{1,3}[a-z]?\](?=\s?(?:,|&)\s?\d))?"
# A letter after a page abbreviation, a series word or the dash of a page
# range is a page or series number ("pp. A345-A346", "Books C 10"), no address.
REFERENCE = re.compile(
    r"(?<![A-Za-z0-9])(?<!\bpp\. )(?<!\bp\. )(?<!\bS\. )(?<!\bBook )(?<!\bBooks )"
    r"(?<!\bLibrary )(?<!\bSeries )(?<!\d-)(?<!\d- )(?<!\d–)"
    # Joined lines may leave two spaces after the letter ("DA2  6").
    rf"([A-R])(A[12])?\s{{0,2}}({ITEM}(?:\s?(?:,|&)\s?{ITEM}(?![A-Za-z]))*)"
)
INTRO = (
    ("correction", re.compile(r"Correction to\s*$")),
    ("continuation", re.compile(r"Cont\.(?: of)?\s*$")),
    ("reprint", re.compile(r"(?:Rep|REP):\s*$")),
    ("contents", re.compile(r"Contents:\s*$")),
    ("see", re.compile(r"(?:See|see)(?: also)?:?\s*$")),
    ("index", re.compile(r"Index\s*$")),
    ("bracket", re.compile(r"\[\s*$")),
    ("list", re.compile(r"[/,&=]\s*$")),
)
MAX_RANGE = 60


def parse_items(group: str) -> tuple[list[tuple[int, str]], Counter]:
    """Target (number, letter) pairs of an address group, and the forms seen."""
    targets: list[tuple[int, str]] = []
    forms: Counter = Counter()
    parts = re.split(r"\s?(?:,|&)\s?", group)
    if len(parts) > 1:
        forms["list"] += 1
    for part in parts:
        if part.endswith("*"):
            forms["starred"] += 1
            part = part[:-1]
        if "-" in part:
            forms["range"] += 1
            low, high = (p.strip() for p in part.split("-", 1))
            lo, hi = (
                int(re.match(r"\d+", low).group()),
                int(re.match(r"\d+", high).group()),
            )
            if 0 < hi - lo <= MAX_RANGE:
                targets.extend((n, "") for n in range(lo, hi + 1))
            else:
                forms["range_unexpanded"] += 1
                targets.append((lo, ""))
            continue
        match = re.match(r"(\d+)([a-z]?)", part)
        if match.group(2):
            forms["letter_suffix"] += 1
        targets.append((int(match.group(1)), match.group(2)))
    return targets, forms


def intro_of(before: str) -> str:
    """Notation type introducing an address, from the text before it."""
    for name, pattern in INTRO:
        if pattern.search(before):
            return name
    return "inline"


def cited_addresses(text: str, own: str = "") -> set[str]:
    """Addresses a text cites; own is the unit's printed address, which cites nothing."""
    found = set()
    for match in REFERENCE.finditer(text):
        letter, suffix, group = match.groups()
        suffix = suffix or ""
        if suffix not in SUFFIX_TO_VOLUME:
            continue
        targets, _ = parse_items(group)
        found.update(f"{letter}{suffix} {n}{s}" for n, s in targets)
    found.discard(own)
    return found
