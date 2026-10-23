"""Split the local print matches into one file per wiki page for the lab (story S6.1).

Input: data/print/derived/lab/print-links.json, produced by the print strand.
Output: docs/lab/local/print/<pageId>.json and docs/lab/local/print/index.json.

Both paths are gitignored, because the rights to the print volumes are
unresolved. The browser cannot load the whole input, so each lab page fetches
only its own file. Matches stay as the print strand wrote them; every match is
proposed, none is confirmed.

Usage:
    python -m uv run python pipeline/lab/split_print_links.py [--src PATH] [--out DIR]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_SRC = REPO / "data" / "print" / "derived" / "lab" / "print-links.json"
DEFAULT_OUT = REPO / "docs" / "lab" / "local" / "print"


def split(data: dict) -> tuple[dict, dict[str, dict]]:
    """Return the index and one record per page id."""
    pages = data["pages"]
    files: dict[str, dict] = {}
    routes: Counter[str] = Counter()
    per_page: dict[str, dict] = {}
    for page_id, entry in pages.items():
        matches = entry.get("print", [])
        page_routes = Counter(m.get("route", "unknown") for m in matches)
        routes.update(page_routes)
        files[page_id] = {
            "pageId": page_id,
            "title": entry.get("title"),
            "print": matches,
        }
        per_page[page_id] = {
            "matches": len(matches),
            "routes": dict(sorted(page_routes.items())),
        }
    index = {
        "about": data.get("about", ""),
        "state": "proposed",
        "pages": len(files),
        "matchesByRoute": dict(sorted(routes.items())),
        "perPage": dict(
            sorted(
                per_page.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0
            )
        ),
    }
    return index, files


LOCAL = REPO / "docs" / "lab" / "local"


def assert_untracked(out: Path) -> None:
    """Refuse an output folder outside docs/lab/local/, tracked or not ignored.

    Trust boundary: print text and everything derived from it must never enter
    Git or the published lab while the rights are unresolved.
    """
    resolved = out.resolve()
    if not resolved.is_relative_to(LOCAL.resolve()):
        sys.exit(f"refusing to write: {out} lies outside {LOCAL}")
    rel = resolved.relative_to(REPO)
    tracked = subprocess.run(
        ["git", "ls-files", "--", rel.as_posix()],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    ignored = (
        subprocess.run(
            ["git", "check-ignore", "-q", (rel / "index.json").as_posix()], cwd=REPO
        ).returncode
        == 0
    )
    if tracked or not ignored:
        sys.exit(f"refusing to write: {rel} is tracked or not ignored")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if not args.src.exists():
        sys.exit(f"no print matches at {args.src}; the print pane will say so")
    assert_untracked(args.out)
    index, files = split(json.loads(args.src.read_text(encoding="utf-8")))
    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    for page_id, record in files.items():
        (args.out / f"{page_id}.json").write_text(
            json.dumps(record, ensure_ascii=False), encoding="utf-8"
        )
    (args.out / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(
        f"wrote {len(files)} page files, routes {index['matchesByRoute']} to {args.out}"
    )


if __name__ == "__main__":
    main()
