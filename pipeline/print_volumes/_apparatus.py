"""The apparatus of the volumes: indexes, front matter and tail, as records beside the entries.

Every line of a part that sections.json marks index, front or tail belongs to
exactly one apparatus record or is page furniture (running head, page
number), so that with the entry records every line of the three files is in a
record. Each record lists its pieces as [page, line, column, start, end], the
offsets of the piece in its p01 line, so that p10 can check that the pieces
rebuild the record and that every piece is held once. An index record is one
index entry: its term, the text before its first address, and its address
groups, read by the address grammar of the entries and resolved to entry
records. Front matter and tail are kept as passages, paragraphs held verbatim
and not read further; the errata of Addendum I are read by p05.

Furniture is a line at the top where its part sets running heads or page
numbers, measured over every page (FURNITURE_TOPS), that holds a page number
at one end; a size or a head zone does not separate it, because the indexes
of Addendum I start their text 13 pt under the head and the tail of Addendum
II starts it at the head's top on pages without one. No line at those tops
holds furniture and text both, so the line decides for its pieces.

The indexes of the main volume and Addendum I are set in two columns whose
lines share baselines, so p01 joins them into one line and opens a run at the
gutter. COLUMNS gives, per part, the x from which a piece belongs to the right
column. A page is read in horizontal blocks split at full-width headings, in
each block the left column before the right, each top to bottom; all indexes
of a volume form one stream, so that an entry running onto the next index's
first page stays one. An entry opens at the margin of its column where the
piece has the head shape of its index (HEADS) or follows a closed entry
without reading as a continuation; a piece set further in continues the entry
before it. The indexes of Addendum I set a blank line between entries
(GAP_OPENS), so there a gap opens an entry and, in the parts that never run
entries on without one (GAP_ONLY), its absence continues it. Where an address
list overran its column, the typesetting set it vertically, one glyph per line
at the column's right edge (a strip); a strip's glyphs join the entry that was
open when it began, or the entry opened beside it since, without spaces. A
passage opens at the top of each page and after a vertical gap wider than
PARAGRAPH_GAP times the part's median line pitch.

Identifiers follow the entries: "<volume>/<part slug>/p<page>l<line>", with
"c2" for an entry that opens in the right column, and one item "#1" per record.
"""

import hashlib
import re
from collections import Counter

from _common import COLUMN_GAP
from _fields import Reader, value

APPARATUS_KINDS = ("index", "front", "tail")
# Gutter per two-column index part: pieces from this x on are the right
# column. Measured from the run positions of p01 over every page of the part.
COLUMNS: dict[tuple[str, str], float] = {
    # Columns at 72 and 291; strips at 250 and 471.
    ("I", "Index A"): 280.0,
    ("I", "Index B"): 280.0,
    # Columns at 105 and 315, continuations 20 further in.
    ("A1", "Index A"): 300.0,
    ("A1", "Index B"): 300.0,
    ("A1", "Index C"): 300.0,
    ("A1", "Index D"): 300.0,
}
# The tops of the furniture lines per volume and part ("*" for the other
# parts), measured over every apparatus page: the main volume sets a 9 pt
# running head with its page number at 72.4 over each index and tail page;
# Addendum I a 12 pt head at 44.2 over its indexes and at 30.8 over errata and
# abbreviations, and the page numbers of its front matter at 728.0, where the
# contents run from 30.8; Addendum II heads its tail pages at 66.7 or 67.8 and
# 73.1, some of them only.
FURNITURE_TOPS: dict[str, dict[str, tuple[float, ...]]] = {
    "I": {"*": (72.4,)},
    "A1": {
        "Front matter": (728.0,),
        "Errata": (30.8,),
        "Abbreviations": (30.8,),
        "*": (44.2,),
    },
    "A2": {"P 1981": (66.7, 67.8), "*": (73.1,)},
}
FURNITURE_TOLERANCE = 1.0
# A running head carries its page number at one end ("Title 12", "12 Title",
# "12Title"); a page number line holds nothing else ("12", "vii").
FURNITURE_SHAPE = re.compile(r"^\d{1,4} ?[A-Z]|\D \d{1,4}$|^(?:\d{1,4}|[ivxlc]{1,7})$")
MARGIN_TOLERANCE = 3.0
# A strip glyph sits this far right of its column's margin; a strip ends where
# its glyphs stop for more than three lines.
STRIP_INDENT = 40.0
STRIP_BREAK = 45.0
# A heading spans the gutter from the left column this far at least.
FULL_WIDTH = 20.0
# A gap wider than this many line pitches before a piece is a blank line.
ENTRY_GAP = 1.5
# The head of an index entry: an inverted name ("Surname, Forename, F 12"),
# and in the chronology, language and periodical indexes of the main volume a
# year, a language or a siglum or list number.
NAME_HEAD = re.compile(r"^[A-ZÀ-ÞĀ-Ž][\w'’.-]*(?:[ -][\w'’.-]+){0,3}, [A-ZÀ-ÞĀ-Ž]")
# The indexes of Addendum I give a term before a colon ("Title [D 1]: DA1 2",
# "Topic: FA1 3", "Term. See Index A1:Other term"); a bracket opens a
# sub-entry ("[2]. Topic: GA1 5") or a continuation ("[H 3]: GA1 5"), no entry.
COLON_HEAD = re.compile(r"^[A-ZÀ-ÞĀ-Ž\"'„“‘(][^:]{0,120}?:")
HEADS = {
    ("I", "Index C"): re.compile(r"^1[89]\d\d\b"),
    ("I", "Index D"): re.compile(r"^[A-Z][a-z]+(?:-[A-Z][a-z]+)?\s+[A-R] ?\d"),
    ("I", "Index E"): re.compile(r"^(?:[A-Z]{3,6}\s|\d{1,3}\.\s)"),
    **{("A1", f"Index {x}"): COLON_HEAD for x in "ABCD"},
}
# Where a head opens an entry even when set further in than the margin.
INDENTED_HEADS = {("I", "Index C"), ("I", "Index D"), ("I", "Index E")}
# Parts that set a blank line before every entry, measured from the gaps in
# their columns; GAP_ONLY never runs one entry on to the next without it,
# while proper names run on and keep the blank line for a new letter.
GAP_OPENS = {("A1", f"Index {x}") for x in "ABCD"}
GAP_ONLY = {("A1", f"Index {x}") for x in "ABC"}
# A piece that opens with one of CONTINUES continues the entry before it; an
# entry whose text ends as CLOSED is closed.
CONTINUES = re.compile(r"[a-zß-ÿ\d/,;)\]\-–.&]")
CLOSED = re.compile(r"(?:[.)\]]|\d[a-z]?\*?)$")
INDEX_HEADING = re.compile(r"^(?:INDEX|Index) [A-E]\b")
# A cross reference waits for its target: the entry ends in "See", "See
# Index", an index label, or the piece opens with the label ("A5:Term").
SEE_PENDING = re.compile(r"(?:\bSee(?: also)?|\bIndex(?:es)?|\b[A-E][1-7]?\s?:)\s*$")
LABEL_START = re.compile(r"^(?:Index(?:es)? ?)?[A-E][1-7]?\s?:")
# The substitute font of the main volume prints Ž as "å" ("åname, E., G 5").
SUBSTITUTE_CAPITAL = {"å": "Z"}
ROMAN = re.compile(r"[IVXLCDM]+")
PARAGRAPH_GAP = 1.6
# Edge characters a term leaves to its address: "Term: BA1 1", "Term - L 2",
# "Title [D 3]".
TERM_TAIL = " ,;:-–[(/"
# The label of an index cross reference ("See Index A5:Term", "See Indexes A4
# & A5:Term", "A4-A7:Term", letter-spaced "A 4 :Term"), which the address
# grammar would read as an address.
INDEX_LABEL = re.compile(
    r"(?<!\w)[A-E](?: ?[1-7])?(?= ?(?:[&-] ?[A-E](?: ?[1-7])? ?)?:)"
)
# A bracket after an item number is that item's locator ("HA1 3[No. 4], 5",
# "PA1 3[B4]"), never an address; a title's year before its main-volume
# address ("Title 1927 [H 3]: GA1 5") and a bracketed cross reference ("[See
# D 2]") are not item locators.
ITEM_BRACKET = re.compile(
    r"(?<![\w])\d{1,4}[a-z]?\*?(\s?\[(?!See\b)[^\[\]]*\])(?!\s?:)"
)
LIST_GOES_ON = re.compile(r"\s?[,&]\s{0,2}\d")
# Justified address lines of the main volume index are letter-spaced in the
# text layer ("G 1 2 , 1 4"): a space between two digits that stand alone;
# joined lines leave a second space after a list comma ("L 5,  6").
SPACED_DIGIT = re.compile(
    r"(?<=\d)(?<![^\s,\-/]\d) (?=\d(?:[\s,\-/]|$))|(?<=[,&] ) (?=\d)"
)


def slug(part: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", part.lower()).strip("-")


def is_furniture(line: dict) -> bool:
    """Running heads and page numbers: a line at a furniture top of its part
    that holds a page number at one end."""
    tops = FURNITURE_TOPS.get(line["volume"], {})
    tops = tops.get(line["part"], tops.get("*", ()))
    return any(abs(line["top"] - top) <= FURNITURE_TOLERANCE for top in tops) and bool(
        FURNITURE_SHAPE.search(line["text"].strip())
    )


def segments(line: dict, gutter: float | None) -> list[dict]:
    """The pieces of a line between gaps wider than COLUMN_GAP, each with its
    x0 and x1, its column (2 from the gutter on) and its span in the line
    text without edge spaces."""
    pieces: list[dict] = []
    offset, ink = 0, None
    for run in line["runs"]:
        x0, text, x1 = run[2], run[3], run[4]
        # A run after leading spaces opens a piece of its own, so that its x0
        # is where the ink starts.
        if not pieces or ink is None or x0 - ink > COLUMN_GAP:
            pieces.append({"start": offset, "x0": x0, "x1": x0})
            ink = None
        offset += len(text)
        pieces[-1]["end"] = offset
        if text.strip():
            ink = pieces[-1]["x1"] = x1
    out = []
    for p in pieces:
        raw = line["text"][p["start"] : p["end"]]
        text = raw.strip()
        if text:
            column = 2 if gutter is not None and p["x0"] >= gutter else 1
            # lead: the first piece of its column in the line, where an
            # entry can open (a title after a siglum, "SIGLA  SIG Title", cannot).
            lead = not out or out[-1]["column"] != column
            start = p["start"] + len(raw) - len(raw.lstrip())
            out.append(
                {
                    **line,
                    "text": text,
                    "x0": p["x0"],
                    "x1": p["x1"],
                    "column": column,
                    "lead": lead,
                    "span": (start, start + len(text)),
                }
            )
    return out


def _heading(text: str) -> bool:
    """A heading set in capitals ("INDEX X / TITLE", "B1 TOPICS"); an
    address list ("12 / L 3"), a Roman numeral ("III] / BA1 5") or a
    bracketed label ("FA1 2[EXC]") has capitals but no word of them."""
    if not text.isupper():
        return False
    bare = re.sub(r"\[[^\[\]]*\]?|^[^\[]*\]", " ", text)
    return any(not ROMAN.fullmatch(w) for w in re.findall(r"[A-Z]{3,}", bare))


def _probe(text: str) -> str:
    """The text as its heads are matched, a substitute capital restored."""
    first = SUBSTITUTE_CAPITAL.get(text[:1])
    return first + text[1:] if first else text


def _opens(piece: dict, unit: list[dict] | None, head: re.Pattern) -> bool:
    """Whether a piece at its column's margin opens an index entry.

    Continuation lines stand at the margin as often as indented in the
    indexes of the main volume and Addendum I, so the margin alone does not
    decide: a piece opens where it has the head shape of its index (a name, a
    year, a siglum), or where the entry before it is closed and the piece
    does not read as a continuation. A cross reference that waits for its
    target never closes.
    """
    text = _probe(piece["text"])
    if unit is None or _heading(text):
        return True
    before = unit_text(unit)
    if SEE_PENDING.search(before) or LABEL_START.match(text):
        return False
    if head.match(text):
        return True
    if CONTINUES.match(text):
        return False
    return (
        bool(CLOSED.search(before))
        or _heading(before)
        or " See " in before
        or bool(INDEX_HEADING.match(before))
    )


def _pitch(pieces: list[dict]) -> float:
    """The most frequent distance between successive lines of a page."""
    tops: dict[int, set[float]] = {}
    for piece in pieces:
        tops.setdefault(piece["page"], set()).add(piece["top"])
    steps = Counter(
        round(b - a)
        for page in tops.values()
        for a, b in zip(sorted(page), sorted(page)[1:])
    )
    return steps.most_common(1)[0][0] if steps else 14


def _blocks(pieces: list[dict]) -> None:
    """Number each piece's horizontal block on its page: a full-width
    heading opens a block, which is read before the columns below it. It is
    the only piece of its line, in the left column, and runs across the
    gutter or is set in capitals; a short one ("D1 GROUP") still spans the
    page, as both columns start again under it."""
    by_line: dict[tuple[int, int], list[dict]] = {}
    for piece in pieces:
        by_line.setdefault((piece["page"], piece["line"]), []).append(piece)
    splits: dict[int, list[float]] = {}
    for (page, _), line in by_line.items():
        gutter = COLUMNS.get((line[0]["volume"], line[0]["part"]))
        if (
            gutter is not None
            and len(line) == 1
            and line[0]["column"] == 1
            and (line[0]["x1"] > gutter + FULL_WIDTH or _heading(line[0]["text"]))
        ):
            splits.setdefault(page, []).append(line[0]["top"])
    for piece in pieces:
        piece["block"] = sum(
            top <= piece["top"] for top in splits.get(piece["page"], [])
        )


def _index_units(pieces: list[dict]) -> list[list[dict]]:
    """Entries per block and column of all indexes of a volume, so that an
    entry running onto the first page of the next index stays one; a strip
    (one glyph per line far right of the margin, where a list wrapped
    vertically) continues the entry open when it began, or one opened beside
    it since."""
    units: list[list[dict]] = []
    pitch = _pitch(pieces)
    _blocks(pieces)
    by_column: dict[tuple[int, int, int], list[dict]] = {}
    margins: dict[tuple[int, int], list[float]] = {}
    for piece in pieces:
        key = (piece["page"], piece["block"], piece["column"])
        by_column.setdefault(key, []).append(piece)
        if len(piece["text"]) > 1:
            margins.setdefault((piece["page"], piece["column"]), []).append(piece["x0"])
    for key in sorted(by_column):
        column = by_column[key]
        page, _, number = key
        margin = min(margins.get((page, number)) or [p["x0"] for p in column])
        owner, strip_top, above = None, None, None
        for piece in column:
            part = (piece["volume"], piece["part"])
            head = HEADS.get(part, NAME_HEAD)
            text = piece["text"]
            strip = len(text) == 1 and piece["x0"] > margin + STRIP_INDENT
            piece["strip"] = strip
            if strip:
                if owner is None or piece["top"] - strip_top > STRIP_BREAK:
                    owner = units[-1] if units else None
                if owner is None:
                    units.append([piece])
                    owner = units[-1]
                else:
                    owner.append(piece)
                strip_top = piece["top"]
                continue
            first = above is None
            gap = not first and piece["top"] - above > ENTRY_GAP * pitch
            above = piece["top"]
            indented_head = part in INDENTED_HEADS and bool(head.match(_probe(text)))
            if not units:
                opens = True
            elif not piece["lead"]:
                opens = False
            elif piece["x0"] > margin + MARGIN_TOLERANCE and not indented_head:
                # A head of the chronology, language or periodical index
                # opens even indented (the numbered almanacs of Index E).
                opens = False
            elif part in GAP_OPENS and gap:
                opens = True
            elif part in GAP_ONLY and not first:
                opens = _heading(text)
            else:
                opens = _opens(piece, units[-1], head)
            if opens:
                units.append([piece])
                owner = None
            else:
                units[-1].append(piece)
    return units


def unit_text(unit: list[dict]) -> str:
    """Pieces joined by a space, the glyphs of one strip without one."""
    text = unit[0]["text"].strip()
    for previous, piece in zip(unit, unit[1:]):
        joint = "" if piece.get("strip") and previous.get("strip") else " "
        text += joint + piece["text"].strip()
    return text


def _passage_units(pieces: list[dict]) -> list[list[dict]]:
    pitches = Counter(
        round(b["top"] - a["top"])
        for a, b in zip(pieces, pieces[1:])
        if a["page"] == b["page"] and b["top"] > a["top"]
    )
    pitch = pitches.most_common(1)[0][0] if pitches else 14
    units: list[list[dict]] = []
    previous = None
    for piece in pieces:
        if (
            previous is None
            or piece["page"] != previous["page"]
            or piece["top"] - previous["top"] > PARAGRAPH_GAP * pitch
        ):
            units.append([piece])
        else:
            units[-1].append(piece)
        previous = piece
    return units


def _term_end(text: str, end: int) -> int:
    while end > 0 and text[end - 1] in TERM_TAIL:
        end -= 1
    return end


def _masked(text: str) -> tuple[str, list[int]]:
    """The text as its addresses are read, and each masked offset's offset in
    text: index labels and the contents of item locators are overwritten, so
    that they read as no address, and a locator a list goes on after and the
    spaces of letter-spaced digits are cut out, so that the group goes on."""
    edits: list[tuple[int, int, str]] = [
        (m.start(), m.end(), "") for m in SPACED_DIGIT.finditer(text)
    ]
    for m in INDEX_LABEL.finditer(text):
        edits.append((m.start(), m.end(), "x" * (m.end() - m.start())))
    for m in ITEM_BRACKET.finditer(text):
        a, b = m.span(1)
        if LIST_GOES_ON.match(text, b):
            edits.append((a, b, ""))
        else:
            inner = text.index("[", a) + 1
            edits.append((inner, b - 1, "x" * (b - 1 - inner)))
    out, back, pos = [], [], 0
    for a, b, replacement in sorted(edits):
        if a < pos:
            continue
        out.append(text[pos:a] + replacement)
        back.extend(range(pos, a + len(replacement)))
        pos = b
    out.append(text[pos:])
    back.extend(range(pos, len(text) + 1))
    return "".join(out), back


def _item(record: dict, index: dict[str, str]) -> dict:
    text = record["text"]
    item = {
        "id": record["id"] + "#1",
        "entry": record["id"],
        "entry_sha256": record["sha256"],
        "volume": record["volume"],
        "part": record["part"],
        "address": "",
        "kind": record["kind"],
        "span": [0, len(text)],
        "text": text,
    }
    if record["kind"] != "index":
        item["passage"] = value(text, 0, len(text), "p03.apparatus-passage")
        return item
    masked, back = _masked(text)
    reader = Reader({**record, "text": masked}, (0, len(masked)), {"index": index})
    references = reader.addresses(0, len(masked))
    for ref in references:
        for key in ("address", "locator"):
            if key in ref:
                a, b = ref[key]["span"]
                a, b = back[a], back[b - 1] + 1
                ref[key]["value"], ref[key]["span"] = text[a:b], [a, b]
    first = references[0]["address"]["span"][0] if references else len(text)
    start, end = 0, _term_end(text, first)
    while start < end and text[start] == " ":
        start += 1
    if end > start:
        item["term"] = value(text[start:end], start, end, "p03.index-term")
    for ref in references:
        a, b = ref["address"]["span"]
        ref["kind"] = value("index", a, b, "p03.index-reference")
    if references:
        item["references"] = references
    return item


def apparatus_records(
    lines: list[dict], volume: str, index: dict[str, str]
) -> tuple[list[dict], dict]:
    """Records of the index, front and tail parts of one volume, and a line count.

    lines are the annotated p01 lines of the volume. The count holds the
    apparatus lines, the furniture and empty ones among them and the characters kept,
    which must equal those of the pieces outside the furniture (checked here).
    """
    # One stream for all indexes of the volume, one per other part.
    streams: dict[str, list[dict]] = {}
    count: Counter = Counter({"lines": 0, "furniture": 0})
    for line in lines:
        if line["kind"] not in APPARATUS_KINDS:
            continue
        count["lines"] += 1
        pieces = (
            []
            if is_furniture(line)
            else segments(line, COLUMNS.get((volume, line["part"])))
        )
        if not pieces:
            count["furniture"] += 1
            continue
        count["chars"] += sum(len(p["text"].replace(" ", "")) for p in pieces)
        key = "index" if line["kind"] == "index" else line["part"]
        streams.setdefault(key, []).extend(pieces)
    records: list[dict] = []
    for key, pieces in streams.items():
        units = _index_units(pieces) if key == "index" else _passage_units(pieces)
        for unit in units:
            first = unit[0]
            part, kind = first["part"], first["kind"]
            rid = f"{volume}/{slug(part)}/p{first['page']}l{first['line']}"
            if first["column"] == 2:
                rid += "c2"
            text = unit_text(unit)
            count["kept"] += len(text.replace(" ", ""))
            record = {
                "id": rid,
                "volume": volume,
                "part": part,
                "page": first["page"],
                "line": first["line"],
                "column": first["column"],
                "page_end": unit[-1]["page"],
                "address": "",
                "kind": kind,
                "text": text,
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "context": [],
                "lines": [
                    [p["page"], p["line"], p["column"], *p["span"]] for p in unit
                ],
            }
            record["objects"] = [_item(record, index)]
            records.append(record)
    ids = Counter(r["id"] for r in records)
    if max(ids.values(), default=1) > 1:
        raise ValueError(f"{volume}: repeated apparatus ids {ids.most_common(3)}")
    if count["kept"] != count["chars"]:
        raise ValueError(
            f"{volume}: apparatus records keep {count['kept']} of {count['chars']} characters"
        )
    return records, dict(count)
