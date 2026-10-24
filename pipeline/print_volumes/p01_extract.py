"""p01: extract every text line of the print-volume PDFs with coordinates and fonts.

Reads data/print/<file>.pdf, verifies its SHA-256 prefix against sections.json
and writes data/print/derived/lines-<volume>.jsonl, one record per line:
volume, page, line index, top, bottom, x0, x1, text, font runs and a defect
flag for WordPerfect substitute glyphs. A run is [font, size, x0, text, x1],
x1 the right edge of its last inked glyph; a new run opens at a change of
font or size and after a gap wider than COLUMN_GAP. Running heads and page numbers stay in
the output; later stages mark them instead of losing them.

Lines are built from pdfplumber's character objects rather than from
extract_text, because the x-position of the first character and the font runs
carry the structure (knowledge/print-volumes.md, Technical properties). A
character joins the current line when its top lies within Y_TOL of the line.
Two checks run per page: every non-space character of the page must reappear
in exactly one line (lossless), and the line count must stay the same for the
alternative tolerances in Y_TOL_VARIANTS (stability). Pages failing the second
check are reported, not repaired.

Usage: python -m uv run --group print python pipeline/print_volumes/p01_extract.py
       [--volume I|A1|A2] [--force]
"""

import argparse
import hashlib
import json
import sys
import time

from _common import (
    COLUMN_GAP,
    DEFECT_CHARS,
    DEFECT_FONT,
    PRINT_DIR,
    REPORT_DIR,
    SECTIONS,
    VOLUMES,
    lines_path,
    write_report,
)

Y_TOL = 2.0
Y_TOL_VARIANTS = (1.0, 3.0)
# A horizontal gap wider than this, without a space glyph, becomes one space.
SPACE_GAP = 2.0


def _group(chars: list[dict], y_tol: float) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for char in sorted(chars, key=lambda c: (round(c["top"], 1), c["x0"])):
        if rows and abs(char["top"] - rows[-1][0]["top"]) <= y_tol:
            rows[-1].append(char)
        else:
            rows.append([char])
    return [sorted(row, key=lambda c: c["x0"]) for row in rows]


def _line_record(volume: str, page: int, index: int, row: list[dict]) -> dict:
    text_parts: list[str] = []
    runs: list[list] = []
    previous = ink = None
    for char in row:
        glyph = char["text"]
        column = (
            ink is not None
            and not glyph.isspace()
            and char["x0"] - ink["x1"] > COLUMN_GAP
        )
        if (
            previous is not None
            and char["x0"] - previous["x1"] > SPACE_GAP
            and not glyph.isspace()
            and not previous["text"].isspace()
        ):
            text_parts.append(" ")
            if runs:
                runs[-1][3] += " "
        font = char["fontname"].split("+")[-1]
        size = round(char["size"], 1)
        if not runs or runs[-1][0] != font or runs[-1][1] != size or column:
            runs.append([font, size, round(char["x0"], 1), "", round(char["x1"], 1)])
        runs[-1][3] += glyph
        text_parts.append(glyph)
        previous = char
        if not glyph.isspace():
            ink = char
            runs[-1][4] = round(char["x1"], 1)
    text = "".join(text_parts)
    return {
        "volume": volume,
        "page": page,
        "line": index,
        "top": round(min(c["top"] for c in row), 1),
        "bottom": round(max(c["bottom"] for c in row), 1),
        "x0": round(row[0]["x0"], 1),
        "x1": round(max(c["x1"] for c in row), 1),
        "text": text,
        "runs": runs,
        "defect": bool(DEFECT_CHARS.search(text))
        or any(DEFECT_FONT.match(run[0]) for run in runs),
    }


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def extract(volume: str) -> dict:
    import pdfplumber  # heavy optional dependency, group "print"

    spec = SECTIONS["volumes"][volume]
    pdf_path = PRINT_DIR / spec["file"]
    if not pdf_path.exists():
        sys.exit(f"FEHLER: {pdf_path} missing, restore it from the SZD repository")
    sha = _sha256(pdf_path)
    if not sha.startswith(spec["sha256"]):
        sys.exit(f"FEHLER: {pdf_path} has SHA-256 {sha}, expected {spec['sha256']}…")

    out = lines_path(volume)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    errors: list[dict] = []
    unstable: list[dict] = []
    page_hashes: list[str] = []
    n_lines = n_defect = 0
    with pdfplumber.open(pdf_path) as pdf, tmp.open("w", encoding="utf-8") as sink:
        for page_no, page in enumerate(pdf.pages, start=1):
            try:
                chars = page.chars
                rows = _group(chars, Y_TOL)
                records = [
                    _line_record(volume, page_no, i, row) for i, row in enumerate(rows)
                ]
                expected = sum(1 for c in chars if not c["text"].isspace())
                kept = sum(1 for r in records for ch in r["text"] if not ch.isspace())
                if kept != expected:
                    errors.append(
                        {"page": page_no, "chars": expected, "in_lines": kept}
                    )
                counts = {str(tol): len(_group(chars, tol)) for tol in Y_TOL_VARIANTS}
                if any(n != len(rows) for n in counts.values()):
                    unstable.append({"page": page_no, str(Y_TOL): len(rows), **counts})
                for record in records:
                    sink.write(json.dumps(record, ensure_ascii=False) + "\n")
                    n_defect += record["defect"]
                n_lines += len(records)
                page_hashes.append(
                    hashlib.sha256(
                        "\n".join(r["text"] for r in records).encode("utf-8")
                    ).hexdigest()
                )
            except Exception as exc:  # one broken page must not stop the volume
                errors.append({"page": page_no, "error": repr(exc)})
        n_pages = len(pdf.pages)
    tmp.replace(out)
    return {
        "volume": volume,
        "file": spec["file"],
        "sha256": sha,
        "pages": n_pages,
        "lines": n_lines,
        "defect_lines": n_defect,
        "lossless_failures": errors,
        "tolerance_unstable_pages": unstable,
        "text_sha256": hashlib.sha256("".join(page_hashes).encode()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--volume", choices=VOLUMES, action="append")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    results = {}
    for volume in args.volume or VOLUMES:
        if lines_path(volume).exists() and not args.force:
            print(f"SKIP {volume}: {lines_path(volume).name} exists (--force)")
            continue
        start = time.monotonic()
        result = extract(volume)
        results[volume] = result
        print(
            f"OK {volume}: {result['pages']} pages, {result['lines']} lines, "
            f"{result['defect_lines']} defect lines, "
            f"{len(result['lossless_failures'])} lossless failures, "
            f"{len(result['tolerance_unstable_pages'])} tolerance-unstable pages, "
            f"{time.monotonic() - start:.0f}s"
        )
    if results:
        previous = REPORT_DIR / "p01_extract.json"
        merged = (
            json.loads(previous.read_text(encoding="utf-8"))
            if previous.exists()
            else {}
        )
        write_report("p01_extract", merged | results)
    failed = any(r["lossless_failures"] for r in results.values())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
