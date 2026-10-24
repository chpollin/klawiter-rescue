"""The apparatus of the volumes: indexes, front matter and tail, as records beside the entries.

Every line of a part that sections.json marks index, front or tail belongs to
exactly one apparatus record or is page furniture (running head, page
number), so that with the entry records every line of the three files is in a
record. An index record is one index entry: its term, the text before its
first address, and its address groups, read by the address grammar of the
entries and resolved to entry records. Front matter and tail are kept as
passages, paragraphs held verbatim and not read further; the errata of
Addendum I are read by p05.

The indexes of the main volume and Addendum I are set in two columns whose
lines share baselines, so p01 joins them into one line and opens a run at the
gutter. COLUMNS gives, per part, the x from which a piece belongs to the right
column; each column is read top to bottom, the left before the right, and all
indexes of a volume form one stream, so that an entry running onto the next
index's first page stays one. An entry opens at the margin of its column
where the piece has the head shape of its index (HEADS) or follows a closed
entry without reading as a continuation; a piece set further in continues
the entry before it. Where an address list overran its column, the
typesetting set it vertically, one glyph per line at the column's right edge
(a strip); a strip's glyphs join the entry that was open when it began,
without spaces. A passage opens at the top of each page and after a vertical
gap wider than PARAGRAPH_GAP times the part's median line pitch.

Identifiers follow the entries: "<volume>/<part slug>/p<page>l<line>", with
"c2" for an entry that opens in the right column, and one item "#1" per record.
"""

import hashlib
import re
from collections import Counter

from _common import COLUMN_GAP
from _fields import Reader, value
from _lines import DIGITS_ONLY, HEAD_ZONE, RUNNING_HEAD

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
MARGIN_TOLERANCE = 3.0
# A strip glyph sits this far right of its column's margin; a strip ends where
# its glyphs stop for more than three lines.
STRIP_INDENT = 40.0
STRIP_BREAK = 45.0
# The head of an index entry: an inverted name ("Surname, Forename, F 12"),
# and in the chronology, language and periodical indexes of the main volume a
# year, a language or a siglum or list number.
NAME_HEAD = re.compile(r"^[A-ZÀ-ÞĀ-Ž][\w'’.-]*(?:[ -][\w'’.-]+){0,3}, [A-ZÀ-ÞĀ-Ž]")
# The indexes of Addendum I give a term before a colon ("Title [D 1]: DA1 2",
# "Topic: FA1 3", "Term. See Index A1:Other term").
COLON_HEAD = re.compile(r"^[A-ZÀ-ÞĀ-Ž\"'„“‘(\[][^:]{0,120}?:")
HEADS = {
    ("I", "Index C"): re.compile(r"^1[89]\d\d\b"),
    ("I", "Index D"): re.compile(r"^[A-Z][a-z]+(?:-[A-Z][a-z]+)?\s+[A-R] ?\d"),
    ("I", "Index E"): re.compile(r"^(?:[A-Z]{3,6}\s|\d{1,3}\.\s)"),
    **{("A1", f"Index {x}"): COLON_HEAD for x in "ABCD"},
}
# Where a head opens an entry even when set further in than the margin.
INDENTED_HEADS = {("I", "Index C"), ("I", "Index D"), ("I", "Index E")}
# A piece that opens with one of CONTINUES continues the entry before it; an
# entry whose text ends as CLOSED is closed.
CONTINUES = re.compile(r"[a-zß-ÿ\d/,;)\]\-–.&]")
CLOSED = re.compile(r"(?:[.)\]]|\d[a-z]?\*?)$")
INDEX_HEADING = re.compile(r"^(?:INDEX|Index) [A-E]\b")
# The running heads of the indexes ("Index X / Title, etc. 900") may hold a
# period, which RUNNING_HEAD excludes.
INDEX_HEAD = re.compile(r"\bIndex [A-E] / ")
PARAGRAPH_GAP = 1.6
# Edge characters a term leaves to its address: "Term: BA1 1", "Term - L 2",
# "Title [D 3]".
TERM_TAIL = " ,;:-–[(/"


def slug(part: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", part.lower()).strip("-")


def is_furniture(line: dict) -> bool:
    """Running heads and page numbers; unlike the entries' rule, size is no
    criterion, because the indexes of Addendum I are set in 10 pt."""
    text = line["text"].strip()
    if not text:
        return True
    if line["top"] < 50:
        return True
    if line["top"] < HEAD_ZONE and (
        RUNNING_HEAD.match(text) or INDEX_HEAD.search(text)
    ):
        return True
    return bool(DIGITS_ONLY.match(text)) and (line["top"] < 90 or line["top"] > 700)


def segments(line: dict, gutter: float | None) -> list[dict]:
    """The pieces of a line between gaps wider than COLUMN_GAP, each with its
    x and its column (2 from the gutter on)."""
    pieces: list[dict] = []
    offset, ink = 0, None
    for run in line["runs"]:
        x0, text, x1 = run[2], run[3], run[4]
        if not pieces or (ink is not None and x0 - ink > COLUMN_GAP):
            pieces.append({"start": offset, "x0": x0})
        offset += len(text)
        pieces[-1]["end"] = offset
        if text.strip():
            ink = x1
    out = []
    for p in pieces:
        text = line["text"][p["start"] : p["end"]]
        if text.strip():
            column = 2 if gutter is not None and p["x0"] >= gutter else 1
            # lead: the first piece of its column in the line, where an
            # entry can open (a title after a siglum, "SIGLA  SIG Title", cannot).
            lead = not out or out[-1]["column"] != column
            out.append(
                {**line, "text": text, "x0": p["x0"], "column": column, "lead": lead}
            )
    return out


def _heading(text: str) -> bool:
    """A heading set in capitals ("INDEX X / TITLE", "B1 TOPICS"); an
    address list ("12 / L 3") has capitals but no word of them."""
    return text.isupper() and bool(re.search(r"[A-Z]{3}", text))


def _opens(piece: dict, unit: list[dict] | None, head: re.Pattern) -> bool:
    """Whether a piece at its column's margin opens an index entry.

    Continuation lines stand at the margin as often as indented in the
    indexes of the main volume and Addendum I, so the margin alone does not
    decide: a piece opens where it has the head shape of its index (a name, a
    year, a siglum), or where the entry before it is closed and the piece
    does not read as a continuation.
    """
    text = piece["text"].strip()
    if unit is None or head.match(text) or _heading(text):
        return True
    if CONTINUES.match(text):
        return False
    before = unit_text(unit)
    return (
        bool(CLOSED.search(before))
        or _heading(before)
        or " See " in before
        or bool(INDEX_HEADING.match(before))
    )


def _index_units(pieces: list[dict]) -> list[list[dict]]:
    """Entries per column of all indexes of a volume, so that an entry running
    onto the first page of the next index stays one; a strip (one glyph per
    line far right of the margin, where a list wrapped vertically) continues
    the entry open when it began."""
    units: list[list[dict]] = []
    by_page: dict[tuple[int, int], list[dict]] = {}
    for piece in pieces:
        by_page.setdefault((piece["page"], piece["column"]), []).append(piece)
    for key in sorted(by_page):
        column = by_page[key]
        lines = [p["x0"] for p in column if len(p["text"].strip()) > 1]
        margin = min(lines or [p["x0"] for p in column])
        owner, strip_top = None, None
        for piece in column:
            head = HEADS.get((piece["volume"], piece["part"]), NAME_HEAD)
            strip = (
                len(piece["text"].strip()) == 1 and piece["x0"] > margin + STRIP_INDENT
            )
            piece["strip"] = strip
            indented_head = (piece["volume"], piece["part"]) in INDENTED_HEADS and bool(
                head.match(piece["text"].strip())
            )
            if strip:
                if owner is None or piece["top"] - strip_top > STRIP_BREAK:
                    owner = units[-1] if units else None
                if owner is None:
                    units.append([piece])
                    owner = units[-1]
                else:
                    owner.append(piece)
                strip_top = piece["top"]
            elif units and (
                not piece["lead"]
                # A head of the chronology, language or periodical index
                # opens even indented (the numbered almanacs of Index E).
                or (piece["x0"] > margin + MARGIN_TOLERANCE and not indented_head)
                or not _opens(piece, units[-1], head)
            ):
                units[-1].append(piece)
            else:
                units.append([piece])
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
    references = Reader(record, (0, len(text)), {"index": index}).addresses(
        0, len(text)
    )
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
    apparatus lines, the furniture among them and the characters kept, which
    must equal those of the non-furniture lines (checked here).
    """
    # One stream for all indexes of the volume, one per other part.
    streams: dict[str, list[dict]] = {}
    count: Counter = Counter()
    for line in lines:
        if line["kind"] not in APPARATUS_KINDS:
            continue
        count["lines"] += 1
        if is_furniture(line):
            count["furniture"] += 1
            continue
        count["chars"] += len(line["text"].strip().replace(" ", ""))
        key = "index" if line["kind"] == "index" else line["part"]
        gutter = COLUMNS.get((volume, line["part"]))
        streams.setdefault(key, []).extend(segments(line, gutter))
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
