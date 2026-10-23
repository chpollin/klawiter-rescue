"""p09: frozen blind sample of print entries for the human check of the concordance.

The concordance (p07) is measured against silver pairs, which only show what
the field route loses where text survived verbatim. Its precision, and its
recall on re-keyed entries, need a person who finds the wiki counterpart of a
print entry without seeing any method output (knowledge/print-wiki-merge.md,
How results are checked). This script draws that sample once and freezes it.

Design:
- Stratified by volume and by what the concordance proposed: entries with a
  field match, entries with only a title-year block, entries with no
  candidate. The last stratum measures what both routes miss.
- PER_STRATUM entries per volume and stratum, drawn with a fixed seed from
  numbered entries of kind "entry" that carry at least one object with a year.
- The sheet the person fills holds only the print entry (volume, address, PDF
  page, text). The key with the concordance's proposals is written to a
  separate file that the person does not open before the sheet is complete.
- The sample is frozen: a second run refuses to overwrite it, so that rules
  are never tuned on it.

The person records per entry the wiki page id of the same publication (or of
the work page holding it), "none" if the wiki lacks it, or "unsure", plus a
note. The comparison with the key gives precision and recall per route and
volume.

Output (local, print text, rights unresolved):
data/print/derived/samples/concordance-blind-sheet.csv,
data/print/derived/samples/concordance-blind-key.json.

Usage: python -m uv run python pipeline/print_volumes/p09_human_sample.py
"""

import csv
import hashlib
import json
import random
import sys
from collections import defaultdict

from _common import DERIVED_DIR, VOLUMES

CLAIMS = DERIVED_DIR / "claims" / "concordance.jsonl"
RECORDS = DERIVED_DIR / "records"
SAMPLES = DERIVED_DIR / "samples"
SHEET = SAMPLES / "concordance-blind-sheet.csv"
KEY = SAMPLES / "concordance-blind-key.json"
SEED = 20261023
PER_STRATUM = 10
STRATA = ("field", "title-year", "none")


def _proposals() -> dict[str, dict]:
    """Per print entry: wiki pages proposed by route."""
    by_entry: dict[str, dict] = defaultdict(lambda: defaultdict(set))
    with CLAIMS.open(encoding="utf-8") as source:
        for claim in map(json.loads, source):
            entry = claim["subject"].split("#", 1)[0]
            page = claim["evidence"].get("wiki_page") or int(
                claim["object"].rsplit("/", 1)[1]
            )
            route = {
                "samePublicationAs": "field",
                "candidateFor": "title-year",
                "textAlignedWith": "alignment",
            }[claim["predicate"]]
            by_entry[entry][route].add(page)
    return by_entry


def main() -> int:
    if SHEET.exists() or KEY.exists():
        sys.exit(f"FEHLER: {SAMPLES} already holds a frozen sample; not redrawn")
    if not CLAIMS.exists():
        sys.exit(f"FEHLER: {CLAIMS} missing; run p07_concordance.py first")
    proposals = _proposals()
    rng = random.Random(SEED)
    rows, key = [], {}
    for volume in VOLUMES:
        pools: dict[str, list[dict]] = {s: [] for s in STRATA}
        with (RECORDS / f"entries-{volume}.jsonl").open(encoding="utf-8") as source:
            for record in map(json.loads, source):
                if record["kind"] != "entry" or not record["address"]:
                    continue
                if not any(o["fields"].get("year") for o in record["objects"]):
                    continue
                routes = proposals.get(record["id"], {})
                stratum = (
                    "field"
                    if routes.get("field")
                    else "title-year"
                    if routes.get("title-year")
                    else "none"
                )
                pools[stratum].append(record)
        for stratum in STRATA:
            pool = sorted(pools[stratum], key=lambda r: r["id"])
            for record in rng.sample(pool, min(PER_STRATUM, len(pool))):
                rows.append(
                    {
                        "sample_id": hashlib.sha256(record["id"].encode()).hexdigest()[
                            :10
                        ],
                        "volume": volume,
                        "address": record["address"],
                        "pdf_page": record["page"],
                        "print_text": record["text"],
                        "wiki_page": "",
                        "decision": "",
                        "note": "",
                    }
                )
                key[rows[-1]["sample_id"]] = {
                    "printId": record["id"],
                    "stratum": stratum,
                    "proposed": {
                        r: sorted(p) for r, p in proposals.get(record["id"], {}).items()
                    },
                }
    # Shuffle so that strata are not visible from the order of the sheet.
    rng.shuffle(rows)
    SAMPLES.mkdir(parents=True, exist_ok=True)
    with SHEET.open("w", encoding="utf-8", newline="") as sink:
        writer = csv.DictWriter(sink, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    KEY.write_text(
        json.dumps({"seed": SEED, "perStratum": PER_STRATUM, "key": key}, indent=1),
        encoding="utf-8",
    )
    print(f"OK {len(rows)} entries frozen -> {SHEET}")
    print(f"OK key (do not open before the sheet is complete) -> {KEY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
