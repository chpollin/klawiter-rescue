"""Read the objects an entry describes from its numbered items and their scope.

The survey of the development pages (2026-10-23) found that the bracketed
items "[1].", "[X].", "[a]." mean different things by the label that governs
them. Items under "Contents:" are contained works, never objects. Items under
an object label that opens their list (FIE, Rep:, Reprinted in, Printed in,
Editions/Reprints, Excerpts, Translations, REV:, "in [1].") and the unlabelled
items of correspondence (K) and reviews (M) are objects; an inline label
("REP: Frankfurter Anthologie [LA1 350]") governs no later item. An
unlabelled item elsewhere counts as an object when it opens with a section
code or carries a year, the two features that separate reprint items from
contents items.

Without object items, an entry describes one object if it carries a citation
(or a host address, or a located manuscript) and none if it is a heading or a
pure cross-reference. A label that introduces a further publication with a
citation of its own ("FIE: 266p. 1950", "Sub. eds./imprs. ...; 31.-40. Tsd.
...") splits an object, and "; " splits such a run between citations (rule of
2026-10-24; it answers error classes the second benchmark had documented, so
that sample measures it as development, not as held-out). Printings of one edition
without a label ("2. Auflage", "[Rep. 1931]") are not counted separately.
object_parts() keeps the governing label, which p03 records as the object's
relation.

The citation profile (imprints, periodical citations, host references, extent
with year) decides whether a unit is a pure cross-reference; a short See-unit
that dates nothing and holds no manuscript is one. It was first a measurement
of probe_signatures.py and is shared here by the record stage, the benchmark
and that probe.
"""

import re

from _common import MONTH
from _lines import STUB

# Item numbers run to three digits; "[1925]." is a year closing a sentence.
ITEM = re.compile(r"\[(\d{1,3}[a-z]?|X|[a-z])\]\s?\.\s*")
# Lists of contained works, of the pages that mention Zweig and of the
# letters an edition prints: their items are no objects.
CONTENTS = re.compile(
    r"\bContents(?:\s?\[[^\]]{1,40}\])?\s?[:.]|\bCon-\s*tents\s?:|\bContains\s?:"
    r"|\bZweig references\s?:|\bLetters, [^:]{3,60}:"
)
# "in [1]. ... [2]. ..." governs the whole list that follows "in".
OBJECT_LABEL = re.compile(
    r"\b(?:FIE|Rep|REP|EXC|Excerpts?|EXCERPTS|Reprinted(?: in| as)?|[Pp]rinted in|"
    r"(?:Non-)?Fischer Editions/Reprints|Editions/Reprints|TRANSLATIONS?|"
    r"Translations?|REV|Reviews?)\s?:"
    r"|\bin(?=\s*\[\d{1,3}[a-z]?\]\s?\.)"
)
# Labels that introduce another publication; the group name is its relation.
SPLIT_LABEL = re.compile(
    r"\b(?:(?P<reprint>Rep|REP|Reprinted(?: in| as)?)\s?:"
    r"|(?P<revised>Rev\. version|REV VERSION|Revised version)\s?:"
    r"|(?P<excerpt>EXC|EXCERPTS?|Excerpts?)\s?:"
    r"|(?P<translation>TRANSLATIONS?|Translations?)\s?:"
    r"|(?P<review>REV|Reviews?)\s?:"
    r"|(?P<edition>FIE|New edition|New ed\.|Further editions|Book editions?|"
    r"(?:Non-)?Fischer Editions/Reprints|Editions/Reprints)\s?:"
    r"|(?P<edition2>Sub\. (?:eds?|imprs?)\.(?:/imprs?\.)?))"
)
MANUSCRIPT = re.compile(r"\b(?:[Tt]ypescript|[Mm]anuscript|Typeschrift)\b")
LOCATED = re.compile(r"\b(?:is|are) located (?:in|at)\b")
HOST_ADDRESS = re.compile(
    r"(?:\bin |[\"”], )[A-R](?:A[12])? \d{1,4}[a-z]?\b|\bin\b[^\[]{2,120}\[[A-R](?:A[12])? ?\d{1,4}"
)
SECTION_CODE = re.compile(r"^[A-R](?:A[12])?(?:/[A-R]A[12])?\b")
YEAR = re.compile(r"\b(1[5-9]|20)\d\d\b")
CITATION = re.compile(
    r"[A-Z][\w.'’/ -]{1,40}: [^.;:\[\]]{2,60}?, [\[(]?(1[5-9]|20)\d\d"
    r"|\d{1,3}:\d{1,3}[a-z]? [(\[]|\b\d{1,2}\.? [A-Z][a-z]{2,8}\.? (1[89]|20)\d\d\b"
    r"|\b(1[5-9]|20)\d\d\b"
)
LISTED_PARTS = ("K", "M")
# Address lists ("see L 88, 120, 1585") carry numbers that look like years.
ADDRESS_LIST = re.compile(
    r"(?<![A-Za-z0-9])[A-R](?:A[12])? ?\d{1,4}[a-z]?(?:\s?[-,&/]\s?\d{1,4}[a-z]?)*"
)


def _stripped(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _depths(text: str) -> list[int]:
    """Bracket depth before each character, so that labels inside notes are skipped."""
    depths, depth = [], 0
    for ch in text:
        depths.append(depth)
        if ch in "[(":
            depth += 1
        elif ch in "])" and depth:
            depth -= 1
    return depths


def _label_kind(match: re.Match) -> str:
    return next(k for k, v in match.groupdict().items() if v).rstrip("0123456789")


def _split_at_labels(
    text: str, span: tuple[int, int], depths: list[int]
) -> list[tuple[tuple[int, int], tuple[int, int, str] | None]]:
    """A label that introduces a further publication with a citation of its own
    ("FIE: 266p. 1950", "Sub. eds./imprs. 302p. Berlin: Singer, No date; 31.-40.
    Tsd. ...") starts an object; one that only heads numbered items or
    addresses does not. Such a run splits again at "; " between citations."""
    start, end = span
    labels = [
        m
        for m in SPLIT_LABEL.finditer(text, start, end)
        if depths[m.start()] == depths[start]
    ]
    pieces: list[tuple[tuple[int, int], tuple[int, int, str] | None]] = []
    cut, governing = start, None
    for index, label in enumerate(labels):
        stop = labels[index + 1].start() if index + 1 < len(labels) else end
        body = text[label.end() : stop]
        # REV: introduces the reviewed work, which is cited, not described.
        if (
            _label_kind(label) == "review"
            or ITEM.match(body.lstrip())
            or not YEAR.search(ADDRESS_LIST.sub(" ", body))
        ):
            continue
        pieces.append(((cut, label.start()), governing))
        governing = (label.start(), label.end(), _label_kind(label))
        cut = label.end()
        for semi in re.finditer(r";\s", body):
            at = label.end() + semi.start()
            rest = text[at + 1 : stop]
            if depths[at] == depths[start] and (
                YEAR.search(ADDRESS_LIST.sub(" ", rest)) or ": " in rest
            ):
                pieces.append(((cut, at), governing))
                cut = at + 1
    pieces.append(((cut, end), governing))
    out = []
    for (a, b), label in pieces:
        a, b = _stripped(text, a, b)
        if b > a and re.search(r"[^\W\d_]", text[a:b]):
            out.append(((a, b), label))
    return out


def object_parts(text: str, part: str, kind: str) -> list[dict]:
    """The objects a unit describes, in reading order: {"span", "label"}.

    The head of the entry (before its first numbered item, without a Contents
    list) is an object when it carries a citation; each object item runs to the
    next numbered item, and a label with a citation of its own splits an object
    further (_split_at_labels). "label" is (start, end, kind) of the printed
    label that governs the object, or None. kind is heading, reference or
    entry.
    """
    if kind in ("heading", "reference"):
        return []
    depths = _depths(text)
    items = list(ITEM.finditer(text))
    spans: list[tuple[tuple[int, int], tuple[int, int, str] | None]] = []
    for index, match in enumerate(items):
        before = text[: match.start()]
        contents = CONTENTS.search(before)
        label = None
        for found in OBJECT_LABEL.finditer(before):
            # A label governs a list only where it opens one ("Rep: [1]. ...");
            # an inline "REP: Title [LA1 350]" ends with its
            # sentence.
            if ITEM.match(text[found.end() :].lstrip()):
                label = found
        if contents and (label is None or contents.start() > label.start()):
            continue
        end = items[index + 1].start() if index + 1 < len(items) else len(text)
        body = text[match.end() : end]
        governing = None
        if label is not None:
            kind_of = SPLIT_LABEL.match(text, label.start())
            governing = (
                label.start(),
                label.end(),
                _label_kind(kind_of) if kind_of else "item",
            )
        elif part in LISTED_PARTS:
            governing = (match.start(), match.end(), "item")
        if (
            label is not None
            or part in LISTED_PARTS
            or (SECTION_CODE.match(body) or YEAR.search(body))
        ):
            spans.append((_stripped(text, match.start(), end), governing))
    if not (spans and part in LISTED_PARTS):
        # The head of a letter or review entry names the correspondent or the
        # reviewed work; only its items are objects.
        head_end = items[0].start() if items else len(text)
        contents = CONTENTS.search(text[:head_end])
        if contents:
            head_end = contents.start()
        head = text[:head_end]
        # A first printing cited by its host address ("in D 2, p. 8",
        # "\"...\", B 6, pp. 42-43") and a located manuscript carry no year.
        if (
            CITATION.search(ADDRESS_LIST.sub(" ", head))
            or HOST_ADDRESS.search(head)
            or (MANUSCRIPT.search(head) and LOCATED.search(head))
        ):
            spans.insert(0, (_stripped(text, 0, head_end), None))
    parts = []
    for span, governing in spans:
        for piece, label in _split_at_labels(text, span, depths):
            parts.append({"span": piece, "label": label or governing})
    return parts


def object_spans(text: str, part: str, kind: str) -> list[tuple[int, int]]:
    return [p["span"] for p in object_parts(text, part, kind)]


def split_objects(text: str, part: str, kind: str) -> list[str]:
    """Texts of the objects a unit describes (object_parts, sliced)."""
    return [text[s:e] for s, e in object_spans(text, part, kind)]


def unit_text(lines: list[dict]) -> str:
    """The text of a unit or of its lines on one page, lines joined by a space."""
    return " ".join(ln["text"].strip() for ln in lines)


def unit_kind(unit: list[dict], text: str) -> str:
    """heading (a single heading line), reference (a stub or a bare See) or entry."""
    if unit[0]["heading"] and len(unit) == 1:
        return "heading"
    if classify_unit(text, citation_profile(text)) == "reference":
        return "reference"
    return "entry"


# Citation forms of a unit, used to tell a pure cross-reference from an entry.
IMPRINT = re.compile(
    r"(?<![\w-])[A-Z][\w.'’/ -]{1,40}: [^.;:\[\]]{2,60}?, [\[(]?(1[5-9]|20)\d\d"
)
PERIODICAL = re.compile(
    rf"\d{{1,3}}:\d{{1,3}}[a-z]? \(|\b\d{{1,2}}\.? {MONTH} (1[89]|20)\d\d\b"
)
# A contribution citing its host volume by address: "in Title [BA1 5]".
HOST = re.compile(r"\bin\b[^\[]{2,120}\[[A-R](?:A[12])? ?\d{1,4}")
# A volume whose imprint stands once in a collection header: "757/(3)p. 1983."
EXTENT_YEAR = re.compile(r"\d+(?:/\(?\d+\)?)?p\. \[?(1[5-9]|20)\d\d\b")
SUBITEM = re.compile(r"\[\d{1,2}\]\.")
SIGLUM = re.compile(r"\[([A-Z][A-Za-z]{1,4})\]")
MARKERS = {
    "Tr.": re.compile(r"\bTr\."),
    "Rep:": re.compile(r"\b(?:Rep|REP):"),
    "REV:": re.compile(r"\bREV:"),
    "EXC": re.compile(r"\bEXC\b"),
    "FAC": re.compile(r"\bFAC\b"),
    "Contents:": re.compile(r"\bContents:"),
    "See": re.compile(r"\bSee\b"),
    "Frw.": re.compile(r"\bFrw\."),
    "Aftw.": re.compile(r"\bAftw\."),
    "Tsd.": re.compile(r"\bTsd\."),
}


# The imprint of a reviewed book belongs to the review, not to a further object.
REVIEWED = re.compile(r"\bREV:.*?\b(1[5-9]|20)\d\d\b")


def citation_profile(text: str) -> dict:
    own = REVIEWED.sub("REV:", text)
    # Numbered items of a Contents list are contained works, not publications.
    listed = own.split("Contents:", 1)[0]
    return {
        "imprints": len(IMPRINT.findall(own)),
        "periodicals": len(PERIODICAL.findall(own)),
        "hosts": len(HOST.findall(own)),
        "extent_years": len(EXTENT_YEAR.findall(own)),
        "subitems": len(SUBITEM.findall(listed)),
        "markers": [m for m, rx in MARKERS.items() if rx.search(text)],
        "sigla": SIGLUM.findall(text),
    }


def classify_unit(text: str, profile: dict) -> str:
    citations = sum(
        profile[k] for k in ("imprints", "periodicals", "hosts", "extent_years")
    )
    # A short See-unit is a pure cross-reference only if it dates nothing and
    # holds nothing; an edition whose imprint the citation forms miss
    # ("638p. Place: Publ. Abbrev. ..., 1957. ... See L 1743") still carries
    # its year, a located manuscript its holding.
    if STUB.match(text) or (
        citations == 0
        and "See" in profile["markers"]
        and len(text) < 200
        and not YEAR.search(ADDRESS_LIST.sub(" ", text))
        and not MANUSCRIPT.search(text)
    ):
        return "reference"
    if profile["subitems"] >= 2 or citations >= 2:
        return "multi"
    if citations == 1:
        return "single"
    return "note"
