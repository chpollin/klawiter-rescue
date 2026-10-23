"""Shared paths, section lookup and line access for the print-volume probes.

The print strand is a script pipeline outside the production run. Its inputs
are the three PDFs in data/print/ (gitignored, rights unresolved), and every
derived file goes to data/print/derived/, which the same ignore rule covers,
because lines and reports carry the compiler's text. Only aggregated findings
move into knowledge/print-volumes.md.
"""

import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
PRINT_DIR = PROJECT_ROOT / "data" / "print"
DERIVED_DIR = PRINT_DIR / "derived"
REPORT_DIR = DERIVED_DIR / "reports"
SECTIONS = json.loads((HERE / "sections.json").read_text(encoding="utf-8"))
VOLUMES = tuple(SECTIONS["volumes"])

# WordPerfect substitute fonts and the stand-ins they leave in the text layer.
DEFECT_CHARS = re.compile("[￿\x00─-╿]")
DEFECT_FONT = re.compile(r"^WP-")


def lines_path(volume: str) -> Path:
    return DERIVED_DIR / f"lines-{volume}.jsonl"


def load_lines(volume: str) -> list[dict]:
    path = lines_path(volume)
    if not path.exists():
        sys.exit(f"FEHLER: {path} missing, run p01_extract.py first")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def part_of(volume: str, page: int) -> tuple[str, str]:
    """Return (part name, kind) for a PDF page; the earlier part wins a boundary."""
    for name, kind, first, last in SECTIONS["volumes"][volume]["parts"]:
        if first <= page <= last:
            return name, kind
    return "unassigned", "front"


def by_page(lines: list[dict]) -> Iterator[tuple[int, list[dict]]]:
    page, bucket = None, []
    for line in lines:
        if line["page"] != page and bucket:
            yield page, bucket
            bucket = []
        page = line["page"]
        bucket.append(line)
    if bucket:
        yield page, bucket


def is_bold(font: str) -> bool:
    return "Bold" in font or "bold" in font


def write_report(name: str, payload: dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{name}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )
    tmp.replace(path)
    return path
