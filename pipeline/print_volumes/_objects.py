"""Read the objects an entry describes from its numbered items and their scope.

The survey of the development pages (2026-10-23) found that the bracketed
items "[1].", "[X].", "[a]." mean different things by the label that governs
them. Items under "Contents:" are contained works, never objects. Items under
an object label (FIE, Rep:, Reprinted in, Printed in, Editions/Reprints,
Excerpts, "in [1].") and the unlabelled items of correspondence (K) and
reviews (M) are objects. An unlabelled item elsewhere counts as an object when
it opens with a section code or carries a year, the two features that
separate reprint items from contents items. A scope runs to the next label.

Without object items, an entry describes one object if it carries a citation
and none if it is a heading or a pure cross-reference. Printings of one
edition ("2. Auflage", "[Rep. 1931]") are not counted separately; this is a
deliberate simplification that the benchmark measures.
"""

import re

ITEM = re.compile(r"\[(\d+[a-z]?|X|[a-z])\]\s?\.\s*")
CONTENTS = re.compile(r"\bContents\s?:|\bCon-\s*tents\s?:|\bContains\s?:")
OBJECT_LABEL = re.compile(
    r"\b(?:FIE|Rep|REP|EXC|Excerpts?|EXCERPTS|Reprinted in|Printed in|"
    r"(?:Non-)?Fischer Editions/Reprints|Editions/Reprints|TRANSLATIONS?)\s?:"
    r"|\bin\s*$"
)
SECTION_CODE = re.compile(r"^[A-R](?:A[12])?(?:/[A-R]A[12])?\b")
YEAR = re.compile(r"\b(1[5-9]|20)\d\d\b")
CITATION = re.compile(
    r"[A-Z][\w.'’/ -]{1,40}: [^.;:\[\]]{2,60}?, [\[(]?(1[5-9]|20)\d\d"
    r"|\d{1,3}:\d{1,3}[a-z]? [(\[]|\b\d{1,2}\.? [A-Z][a-z]{2,8}\.? (1[89]|20)\d\d\b"
    r"|\b(1[5-9]|20)\d\d\b"
)
LISTED_PARTS = ("K", "M")


def count_objects(text: str, part: str, kind: str) -> int:
    """Number of objects a unit describes; kind is heading, reference or entry."""
    if kind in ("heading", "reference"):
        return 0
    items = list(ITEM.finditer(text))
    objects = 0
    for index, match in enumerate(items):
        before = text[: match.start()]
        contents = CONTENTS.search(before)
        label = None
        for found in OBJECT_LABEL.finditer(before):
            label = found
        if contents and (label is None or contents.start() > label.start()):
            continue
        end = items[index + 1].start() if index + 1 < len(items) else len(text)
        body = text[match.end() : end]
        if label is not None or part in LISTED_PARTS:
            objects += 1
        elif SECTION_CODE.match(body) or YEAR.search(body):
            objects += 1
    if objects and part in LISTED_PARTS:
        # The head of a letter or review entry names the correspondent or the
        # reviewed work; only its items are objects.
        return objects
    head = text[: items[0].start()] if items else text
    head = CONTENTS.split(head)[0]
    return objects + (1 if CITATION.search(head) else 0)
