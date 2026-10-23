"""p04: every stored revision text of the wiki's main namespace, for alignment with print.

The overlap experiments (knowledge/print-volumes.md, Print and wiki) found that
Addendum II reached the wiki nearly verbatim in 2009-2011 and that runs of the
main volume were pasted verbatim for minutes in 2012-2017 before rewriting.
Such traces exist only in the revision history, so the alignment stage needs
all revisions, not only page_latest. This stage reuses the dump readers of the
production extraction (pipeline/01_extract.py) and writes one line per
main-namespace revision whose text the blobs hold:

    {"page", "title", "rev", "timestamp", "latest", "text"}

Text is decoded from the dump's Latin-1 reading to UTF-8 where it is valid
UTF-8; a text that is not (some stored texts end inside a multi-byte
character) keeps its Latin-1 reading and is counted. Revisions whose text is missing
from the blobs are counted, never invented.

Output: data/print/derived/wiki/revisions.jsonl and
data/print/derived/reports/p04_wiki_revisions.json.

Usage: python -m uv run python pipeline/print_volumes/p04_wiki_revisions.py
"""

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

from _common import DERIVED_DIR, write_report

PIPELINE = Path(__file__).resolve().parents[1]
WIKI = DERIVED_DIR / "wiki"
MAIN_NAMESPACE = 0


def _extract_module():
    """pipeline/01_extract.py, whose name is no valid module identifier."""
    sys.path.insert(0, str(PIPELINE))
    spec = importlib.util.spec_from_file_location(
        "extract01", PIPELINE / "01_extract.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _decode(text: str, stats: Counter) -> str:
    """UTF-8 reading of a Latin-1 decoded blob; invalid UTF-8 keeps its Latin-1 reading."""
    try:
        return text.encode("latin-1").decode("utf-8")
    except UnicodeError:
        # Some stored texts end inside a multi-byte character.
        stats["text_not_utf8"] += 1
        return text


def main() -> int:
    extract = _extract_module()
    with open(extract.SQL_DUMP_PATH, "rb") as source:
        sql_text = source.read().decode("latin-1")
    pages = extract.load_page_table(sql_text)
    slots = extract.load_slots_table(sql_text)
    contents = extract.load_content_table(sql_text)
    revisions = extract.load_revisions(sql_text)
    del sql_text
    texts: dict[int, str] = {}
    for blob_path in extract.BLOB_FILES:
        if not Path(blob_path).exists():
            sys.exit(f"FEHLER: blob file missing: {blob_path}")
        for text_id, data in extract.load_blob_index(blob_path).items():
            texts[text_id] = data["content"]

    stats: Counter = Counter()
    WIKI.mkdir(parents=True, exist_ok=True)
    out = WIKI / "revisions.jsonl"
    tmp = out.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as sink:
        for rev_id, rev in sorted(
            revisions.items(), key=lambda item: (item[1]["page"], item[1]["timestamp"])
        ):
            page = pages.get(rev["page"])
            if page is None or page["namespace"] != MAIN_NAMESPACE:
                stats["other_namespace_or_deleted_page"] += 1
                continue
            text_id = contents.get(slots.get(rev_id, -1))
            if text_id is None or text_id not in texts:
                stats["text_missing"] += 1
                continue
            row = {
                "page": rev["page"],
                "title": _decode(page["title"], stats),
                "rev": rev_id,
                "timestamp": rev["timestamp"],
                "latest": rev_id == page["page_latest"],
                "text": _decode(texts[text_id], stats),
            }
            sink.write(json.dumps(row, ensure_ascii=False) + "\n")
            stats["written"] += 1
    tmp.replace(out)
    print(f"OK {stats['written']} revisions written, {dict(stats)}")
    path = write_report("p04_wiki_revisions", dict(stats))
    print(f"OK report {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
