"""Page check data of the print strand: one PDF page with what p01 and p03 read from it.

The page check view (viewer/page.html) shows a PDF page beside every line p01
extracted from it and every record, object and value p03 read from those
lines. assemble() builds that page's data from the derived files; render()
draws the page as a PNG. review_server.py serves both under /check/.

Lines and records are joined here, since a p03 entry record names only its
first line: its text is its lines stripped and joined by one space, page
furniture left out (_objects.unit_text), so the record consumes the lines
from its first one whose text continues its own. An apparatus record names
its pieces of lines itself. A line no record holds is outside, by the
definition of the p10 ledger (p10_validate.lines_outside): every inked
character of an apparatus line lies in a piece, page furniture apart.

While a blind sheet of p09 has rows without an answer, a page holding an entry
of its sample is served without its readings (knowledge/design.md, Page check
tool): the blind check runs from the print entry alone, and the readings with
their wiki candidates would turn it into a check of the proposals.

Everything read and written here lies under data/print/ and holds print text
(rights unresolved); nothing is versioned. The PNG cache lies in
data/print/derived/check/.
"""

import io
import json
import re
import threading
from collections import Counter
from pathlib import Path

from _common import DERIVED_DIR, PRINT_DIR, SECTIONS, VOLUMES
from _heldout import BLIND_KEY, BLIND_KEY_2, BLIND_SHEET, BLIND_SHEET_2
from _lines import annotate
from _schema import object_values
from p09_human_sample import answers
from p10_validate import APPARATUS, apparatus_furniture

try:
    import pypdfium2 as pdfium
except ImportError:  # the print dependency group is not installed
    pdfium = None

RENDER_SCALE = 2.0
# p10 lets an entry skip at most this many foreign lines between two of its own.
MAX_SKIP = 4
# Shown to the person; the server logs how to install the renderer.
NO_RENDERER = "the server cannot render page images"
# The blind samples of p09 by their file names under samples/: key, sheet.
BLIND = ((BLIND_KEY.name, BLIND_SHEET.name), (BLIND_KEY_2.name, BLIND_SHEET_2.name))
WITHHELD = (
    "The readings of this page are withheld: it holds an entry of the blind "
    "sample in {sheets}, which still has rows without an answer, and that check "
    "runs from the print alone."
)
# The line roles of the page check, most specific first.
ROLES = ("outside", "furniture", "apparatus", "heading", "value", "record")
_DOC_LOCK = threading.Lock()  # pdfium is not thread-safe; hold it for every call
_DOCS: dict[str, object] = {}


def _document(path: Path):
    """The open pdfium document of a volume; the caller holds _DOC_LOCK."""
    key = str(path)
    if key not in _DOCS:
        _DOCS[key] = pdfium.PdfDocument(key)
    return _DOCS[key]


def _jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def entry_pieces(record: dict, lines: list[dict], at: dict) -> list[tuple]:
    """(line index, record start, record end, line start) per line of an entry record."""
    i = at.get((record["page"], record["line"]))
    text, pos, skipped, out = record["text"], 0, 0, []
    while i is not None and i < len(lines) and pos < len(text) and skipped <= MAX_SKIP:
        raw = lines[i]["text"]
        own = raw.strip()
        if own and not lines[i]["furniture"] and text.startswith(own, pos):
            out.append((i, pos, pos + len(own), len(raw) - len(raw.lstrip())))
            pos += len(own)
            skipped = 0
            if text.startswith(" ", pos):
                pos += 1
        elif own:
            skipped += 1
        i += 1
    return out


def apparatus_pieces(record: dict, lines: list[dict], at: dict) -> list[tuple]:
    """(line index, record start, record end, line start) per piece of an apparatus record.

    The pieces rebuild the record's text in order, each joined to the one
    before by one space or none (p10 _ledger); a piece that breaks the text
    ends the list."""
    text, pos, out = record["text"], 0, []
    for page, line, _column, a, b in record.get("lines", []):
        i = at.get((page, line))
        piece = lines[i]["text"][a:b] if i is not None else ""
        if not piece:
            break
        if pos == 0 and text.startswith(piece):
            start = 0
        elif pos and text.startswith(piece, pos):
            start = pos
        elif pos and text.startswith(" " + piece, pos):
            start = pos + 1
        else:
            break
        out.append((i, start, start + len(piece), a))
        pos = start + len(piece)
    return out


def _value_rows(obj: dict) -> list[dict]:
    rows = []
    for path, v in object_values(obj):
        inherited = path.startswith("inherited.")
        rows.append(
            {
                "field": path.removeprefix("inherited.") if inherited else path,
                "path": path,
                "inherited": inherited,
                "value": v.get("value"),
                "by": v.get("by"),
                "rule": v.get("rule"),
                "state": v.get("state"),
                "source": v.get("from") or obj["entry"],
                "span": list(v["span"]),
            }
        )
    return rows


class Volume:
    """One volume's lines and records, joined line by line."""

    def __init__(self, volume: str, lines: list[dict], entries: list, apparatus: list):
        self.volume = volume
        self.lines = annotate(lines, volume)
        self.at = {(ln["page"], ln["line"]): i for i, ln in enumerate(self.lines)}
        self.by_page: dict[int, list[int]] = {}
        for i, ln in enumerate(self.lines):
            self.by_page.setdefault(ln["page"], []).append(i)
        self.records: dict[str, dict] = {}
        self.pieces: dict[str, list[tuple]] = {}
        self.holders: dict[int, list[str]] = {}
        cover: dict[int, list[int]] = {}
        for record in entries:
            self._hold(record, entry_pieces(record, self.lines, self.at), False)
        for record in apparatus:
            pieces = apparatus_pieces(record, self.lines, self.at)
            self._hold(record, pieces, True)
            for i, ra, rb, la in pieces:
                chars = cover.setdefault(i, [0] * len(self.lines[i]["text"]))
                for k in range(la, min(la + rb - ra, len(chars))):
                    chars[k] += 1
        furniture = apparatus_furniture(self.lines)
        self.role: dict[int, str] = {}
        for i, ln in enumerate(self.lines):
            self.role[i] = self._role(i, ln, i in furniture, cover.get(i))

    def _hold(self, record: dict, pieces: list[tuple], apparatus: bool) -> None:
        record = {**record, "_apparatus": apparatus}
        self.records[record["id"]] = record
        self.pieces[record["id"]] = pieces
        for i, *_ in pieces:
            self.holders.setdefault(i, []).append(record["id"])

    def _role(self, i: int, ln: dict, app_furniture: bool, chars) -> str:
        if not ln["text"].strip():
            return "furniture"
        holders = [self.records[r] for r in self.holders.get(i, [])]
        if ln["kind"] in APPARATUS:
            if app_furniture:
                return "furniture"
            inked = [k for k, ch in enumerate(ln["text"]) if not ch.isspace()]
            held = chars is not None and all(chars[k] for k in inked)
            return "apparatus" if held else "outside"
        if ln["furniture"]:
            return "furniture"
        if not holders:
            return "outside"
        if all(r["kind"] in ("heading", "reference") for r in holders):
            return "heading"
        return "value" if self._carries_value(i, holders) else "record"

    def _carries_value(self, i: int, holders: list[dict]) -> bool:
        for record in holders:
            pieces = [p for p in self.pieces[record["id"]] if p[0] == i]
            for obj in record.get("objects", []):
                for row in _value_rows(obj):
                    if row["source"] != record["id"]:
                        continue
                    a, b = row["span"]
                    if any(a < rb and b > ra for _, ra, rb, _ in pieces):
                        return True
        return False

    def line_spans(self, record_id: str, span: list[int]) -> list[dict]:
        """The parts of a record's span as [start, end) offsets into its lines."""
        out = []
        a, b = span
        for i, ra, rb, la in self.pieces.get(record_id, []):
            if a < rb and b > ra:
                ln = self.lines[i]
                out.append(
                    {
                        "page": ln["page"],
                        "line": ln["line"],
                        "start": la + max(a, ra) - ra,
                        "end": la + min(b, rb) - ra,
                    }
                )
        return out


class Source:
    """The derived files of the print strand, read again when one of them changes."""

    def __init__(self, derived: Path = DERIVED_DIR, print_dir: Path = PRINT_DIR):
        self.derived = Path(derived)
        self.print_dir = Path(print_dir)
        self.cache = self.derived / "check"
        self.lock = threading.Lock()
        self.stamp = None
        self.volumes: dict[str, Volume] = {}
        self.links: dict = {}
        self.wiki_pages: dict = {}
        self.page_counts: dict[str, int] = {}
        self.withheld: dict[str, str] = {}

    def _files(self) -> list[Path]:
        records = self.derived / "records"
        files = [self.derived / "viewer" / "wiki_concordance.json"]
        files += [self.derived / "samples" / name for pair in BLIND for name in pair]
        for v in VOLUMES:
            files += [
                self.derived / f"lines-{v}.jsonl",
                records / f"entries-{v}.jsonl",
                records / f"apparatus-{v}.jsonl",
            ]
        return files

    def pdf(self, volume: str) -> Path:
        return self.print_dir / SECTIONS["volumes"][volume]["file"]

    def current(self) -> "Source":
        stamp = tuple(p.stat().st_mtime_ns if p.is_file() else 0 for p in self._files())
        with self.lock:
            if stamp != self.stamp:
                self._load()
                self.stamp = stamp
        return self

    def _load(self) -> None:
        records = self.derived / "records"
        self.volumes = {
            v: Volume(
                v,
                _jsonl(self.derived / f"lines-{v}.jsonl"),
                _jsonl(records / f"entries-{v}.jsonl"),
                _jsonl(records / f"apparatus-{v}.jsonl"),
            )
            for v in VOLUMES
        }
        concordance = self.derived / "viewer" / "wiki_concordance.json"
        data = (
            json.loads(concordance.read_text(encoding="utf-8"))
            if concordance.is_file()
            else {}
        )
        self.links = data.get("links", {})
        self.wiki_pages = data.get("pages", {})
        self.page_counts = {}
        for v, vol in self.volumes.items():
            count = max(vol.by_page, default=0)
            if pdfium is not None and self.pdf(v).is_file():
                with _DOC_LOCK:
                    count = len(_document(self.pdf(v)))
            self.page_counts[v] = count
        self.withheld = self._blind()

    def _blind(self) -> dict[str, str]:
        """Entry id -> sheet name for every entry of a blind sample whose sheet is open."""
        out = {}
        for key_name, sheet_name in BLIND:
            key = self.derived / "samples" / key_name
            if not key.is_file():
                continue
            found, problems = answers(self.derived / "samples" / sheet_name)
            if found and not problems and all(a is not None for a in found.values()):
                continue
            for row in json.loads(key.read_text(encoding="utf-8"))["key"].values():
                out[row["printId"]] = sheet_name
        return out

    def pages(self, volume: str) -> int:
        return self.current().page_counts.get(volume, 0)

    def find(self, query: str, limit: int = 20) -> list[dict]:
        """Records whose identifier or address is the query, or else begins with it."""
        wanted = re.sub(r"\s+", " ", query.split("#", 1)[0]).strip().casefold()
        found = []
        for vol in self.current().volumes.values():
            for record in vol.records.values():
                rid = record["id"].casefold()
                address = (record.get("address") or "").casefold()
                if wanted in (rid, address):
                    rank = 0
                elif rid.startswith(wanted) or (address and address.startswith(wanted)):
                    rank = 1
                else:
                    continue
                found.append(
                    (
                        rank,
                        {
                            "id": record["id"],
                            "volume": vol.volume,
                            "page": record["page"],
                            "address": record.get("address") or "",
                            "kind": record["kind"],
                        },
                    )
                )
        best = min((rank for rank, _ in found), default=0)
        return [item for rank, item in found if rank == best][:limit]

    def assemble(self, volume: str, page: int) -> dict:
        """The page's lines, the records holding them, and their objects with every value."""
        self.current()
        vol = self.volumes[volume]
        indices = vol.by_page.get(page, [])
        roles = Counter()
        lines = []
        for i in indices:
            ln = vol.lines[i]
            role = vol.role[i]
            roles[role] += 1
            lines.append(
                {
                    "line": ln["line"],
                    "top": ln["top"],
                    "bottom": ln["bottom"],
                    "x0": ln["x0"],
                    "x1": ln["x1"],
                    "text": ln["text"],
                    "defect": bool(ln.get("defect")),
                    "role": role,
                    "records": vol.holders.get(i, []),
                }
            )
        order: list[str] = []
        for i in indices:
            for rid in vol.holders.get(i, []):
                if rid not in order:
                    order.append(rid)
        has_image = pdfium is not None and self.pdf(volume).is_file()
        page_data = {
            "volume": volume,
            "page": page,
            "pages": self.page_counts.get(volume, 0),
            "size": self._size(volume, page) if has_image else None,
            "renderer": None if has_image else NO_RENDERER,
        }
        blind = sorted({self.withheld[rid] for rid in order if rid in self.withheld})
        if blind:
            # Not even the line roles: they tell which passages were read as values.
            return {
                **page_data,
                "withheld": WITHHELD.format(sheets=" and ".join(blind)),
                "roles": {},
                "lines": [],
                "records": [],
                "links": {},
                "wikiPages": {},
            }
        records = [self._record(vol, vol.records[rid], page) for rid in order]
        ids = {rid for rid in order} | {o["id"] for r in records for o in r["objects"]}
        links = {k: self.links[k] for k in sorted(ids) if k in self.links}
        wiki = {
            str(c["page"]): (self.wiki_pages.get(str(c["page"])) or {}).get("title", "")
            for link in links.values()
            for key in ("align", "same", "cand")
            for c in link.get(key, [])
            if c.get("page")
        }
        return {
            **page_data,
            "withheld": None,
            "roles": dict(roles),
            "lines": lines,
            "records": records,
            "links": links,
            "wikiPages": wiki,
        }

    def _record(self, vol: Volume, record: dict, page: int) -> dict:
        pages = sorted({vol.lines[i]["page"] for i, *_ in vol.pieces[record["id"]]})
        objects = []
        for n, obj in enumerate(record.get("objects", []), start=1):
            values = []
            for row in _value_rows(obj):
                spans = vol.line_spans(row["source"], row["span"])
                for s in spans:
                    if s["page"] != page:
                        # A passage on another page carries its line text, so
                        # that it can be read here.
                        line = vol.lines[vol.at[(s["page"], s["line"])]]
                        s["text"] = line["text"]
                values.append({**row, "lines": spans})
            objects.append(
                {
                    "id": obj["id"],
                    "position": n,
                    "address": obj.get("address") or "",
                    "kind": obj.get("kind"),
                    "span": obj.get("span"),
                    "values": values,
                }
            )
        return {
            "id": record["id"],
            "kind": record["kind"],
            "apparatus": record["_apparatus"],
            "part": record["part"],
            "address": record.get("address") or "",
            "page": record["page"],
            "pageEnd": record.get("page_end", record["page"]),
            "line": record["line"],
            "pages": pages,
            "context": record.get("context", []),
            "objects": objects,
        }

    def _size(self, volume: str, page: int) -> dict:
        with _DOC_LOCK:
            width, height = _document(self.pdf(volume))[page - 1].get_size()
        return {"width": width, "height": height}

    def render(self, volume: str, page: int) -> bytes:
        """The page as a PNG, from the cache in data/print/derived/check/ when present."""
        if pdfium is None:
            raise RuntimeError(NO_RENDERER)
        if not self.pdf(volume).is_file():
            raise RuntimeError(f"the PDF of volume {volume} is missing in data/print/")
        target = self.cache / f"{volume}-{page}.png"
        if target.is_file():
            return target.read_bytes()
        with _DOC_LOCK:
            image = (
                _document(self.pdf(volume))[page - 1]
                .render(scale=RENDER_SCALE)
                .to_pil()
            )
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        data = buffer.getvalue()
        self.cache.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(f".{threading.get_ident()}.tmp")
        tmp.write_bytes(data)
        tmp.replace(target)
        return data
