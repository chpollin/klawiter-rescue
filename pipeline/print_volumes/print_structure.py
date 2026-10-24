"""The structure of the print volumes for the start page of the local frontend.

The start page shows the compiler's sections A to R across the four states of
the bibliography: the main volume, the two addenda and the wiki. The wiki side
is public; the print side is derived from the print records and therefore stays
local. This script writes counts and number ranges only, no print text, to
data/print/derived/lab/print-structure.json and copies it to the ignored
docs/lab/local/, where the frontend looks for it on localhost.

Per volume and part: entries (records of kind entry), the highest entry number
read from the addresses, the PDF pages, and for an index the number of its
index entries. Parts outside A to R that hold entries (for example lists in the
Addendum II working file) are kept under their own name.

Usage: python -m uv run python pipeline/print_volumes/print_structure.py
"""

import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

from _common import DERIVED_DIR
from _schema import object_values

ROOT = Path(__file__).resolve().parents[2]
SECTIONS = Path(__file__).with_name("sections.json")
RECORDS = DERIVED_DIR / "records"
OUT = DERIVED_DIR / "lab" / "print-structure.json"
LOCAL = ROOT / "docs" / "lab" / "local" / "print-structure.json"
VIEWER = "http://127.0.0.1:8767/viewer/index.html"
# Object types that make an object a publication, the level the sources share;
# holdings, events, series, references and untyped objects are counted apart.
PUBLICATION_TYPES = {
    "book_edition",
    "periodical_contribution",
    "collection_contribution",
}
# The number at the end of an address: "F 61", "FA1 3", "AA2 12".
NUMBER = re.compile(r"(\d+)\s*$")


def volume_structure(volume: str, parts: list) -> tuple[dict, dict]:
    entries, highest = Counter(), Counter()
    totals = Counter()
    with (RECORDS / f"entries-{volume}.jsonl").open(encoding="utf-8") as source:
        for line in source:
            r = json.loads(line)
            totals["objects"] += len(r["objects"])
            totals["values"] += sum(1 for o in r["objects"] for _ in object_values(o))
            for o in r["objects"]:
                types = {t["value"] for t in o.get("types", [])}
                totals["publications" if types & PUBLICATION_TYPES else "other"] += 1
            if r["kind"] != "entry":
                continue
            totals["numbered" if r["address"] else "unnumbered"] += 1
            entries[r["part"]] += 1
            m = NUMBER.search(r["address"])
            if m:
                highest[r["part"]] = max(highest[r["part"]], int(m.group(1)))
    index = Counter()
    with (RECORDS / f"apparatus-{volume}.jsonl").open(encoding="utf-8") as source:
        for line in source:
            r = json.loads(line)
            if r["kind"] == "index":
                index[r["part"]] += len(r["objects"])
    out = {}
    for name, kind, first, last, *_ in parts:
        part = {"kind": kind, "pages": [first, last]}
        if kind == "body":
            part["entries"] = entries[name]
            if highest[name]:
                part["highest"] = highest[name]
        elif kind == "index":
            part["entries"] = index[name]
        else:
            continue
        out[name] = part
    totals["entries"] = sum(entries.values())
    return out, dict(totals)


def main() -> int:
    sections = json.loads(SECTIONS.read_text(encoding="utf-8"))["volumes"]
    structure = {
        "about": "Entries per part and totals of each print volume; counts only, local.",
        "viewer": VIEWER,
        "volumes": {},
        "totals": {},
    }
    for v, s in sections.items():
        structure["volumes"][v], structure["totals"][v] = volume_structure(
            v, s["parts"]
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(structure, indent=1), encoding="utf-8")
    if LOCAL.parent.exists():
        shutil.copyfile(OUT, LOCAL)
    counts = {
        v: sum(p["entries"] for p in s.values() if p["kind"] == "body")
        for v, s in structure["volumes"].items()
    }
    print(
        f"OK {OUT} and {LOCAL if LOCAL.exists() else 'no local copy'}: entries {counts}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
