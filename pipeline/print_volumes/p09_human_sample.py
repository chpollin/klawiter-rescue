"""p09: frozen blind samples of print entries for the human check of the concordance.

The concordance (p07) is measured against silver pairs, which only show what
the field route loses where text survived verbatim; they are a development
metric. Its precision, and its recall on re-keyed entries, need a person who
finds the wiki counterpart of a print entry without seeing any method output
(knowledge/print-wiki-merge.md, How results are checked). This script draws
those samples once and freezes them, and writes the claim sheet of the second,
non-blind phase.

Phase 1, blind. The sheets hold only the print entry (volume, address, PDF
page, text). The person records per entry the wiki page id of the same
publication (or of the work page holding it) in "wiki_page", or "none" in
"decision" if the wiki lacks it, or "unsure" there, plus a note (answers()).
The keys are written to separate files that the person does not open before
the sheets are complete; they hold identifiers, strata and sizes only.
p13_review.py compares the answers with the proposals the current claims
make for these entries at measurement time, since p07 changes after drawing.

- The first sample (2026-10-23) is stratified by volume and by what the
  concordance proposed then: a field match, only a title-year block, or no
  candidate, PER_STRATUM entries each, from numbered entries of kind "entry"
  that carry at least one object with a year. Its key froze the proposals of
  that day; the stratum sizes of the drawing were not kept, so --strata
  reconstructs them under the same rule from the oldest claims kept
  (BASELINE_CLAIMS) on the current records and writes them beside the key,
  with how many drawn entries the reconstruction puts in their recorded
  stratum. p13 weighs by them.
- --supplement draws a second sample from entries rule development has not
  seen (not the development sample, not held out by any other sample), with
  strata of its own on the current claims: field, title-year, none, and
  no-year for entries without a read year, which the first sample excluded.
  It draws enough field and title-year entries that each route reaches about
  TARGET_CLAIMS claims per volume on the claim sheet (at most
  CLAIMS_PER_ENTRY per entry and route), and NO_YEAR_PER_VOLUME entries
  without a year. Its key records the stratum sizes at drawing, each drawn
  entry's stratum under the first design and each first-sample entry's
  stratum under this one, so that p13 can weigh the union of both samples.

Phase 2, not blind. --claims-sheet runs only when both blind sheets are
complete: per entry and route it lists the current claims (all of them, or
CLAIMS_PER_ENTRY drawn with a fixed seed), each with its wiki page and line,
and the person marks each "right", "wrong" or "unsure". Only this gives claim
precision per route and volume. Alignment claims are listed but not
supplemented for: near-verbatim alignment is a deterministic check.

Every file is frozen: a second run refuses to overwrite it, so that rules are
never tuned on it.

Output (local, print text, rights unresolved): data/print/derived/samples/
concordance-blind-sheet(-2).csv, concordance-blind-key(-2).json,
concordance-blind-strata.json, concordance-claims-sheet.csv.

Usage: python -m uv run python pipeline/print_volumes/p09_human_sample.py
       [--strata | --supplement | --claims-sheet]
"""

import argparse
import csv
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from _common import DERIVED_DIR, VOLUMES
from _fields import summary
from _heldout import (
    BLIND_KEY_2,
    BLIND_SHEET_2,
    BLIND_STRATA,
    CLAIMS_SHEET,
    is_held_out,
)
from p14_gate import fingerprint, sha256_file

CLAIMS = DERIVED_DIR / "claims" / "concordance.jsonl"
BASELINE_CLAIMS = DERIVED_DIR / "baseline-p07" / "concordance.jsonl"
RECORDS = DERIVED_DIR / "records"
SAMPLES = DERIVED_DIR / "samples"
DEV = SAMPLES / "dev-sample.json"
SHEET = SAMPLES / "concordance-blind-sheet.csv"
KEY = SAMPLES / "concordance-blind-key.json"
SEED = 20261023
PER_STRATUM = 10
STRATA = ("field", "title-year", "none")
SUPPLEMENT_SEED = 20261029
SUPPLEMENT_STRATA = (*STRATA, "no-year")
CLAIMS_SEED = 20261030
CLAIMS_PER_ENTRY = 5
TARGET_CLAIMS = 40
NO_YEAR_PER_VOLUME = 10
ROUTES = {
    "samePublicationAs": "field",
    # Containment is no identity a blind answer could confirm; it is counted
    # apart and enters no measured route.
    "containedIn": "containment",
    "contains": "containment",
    "candidateFor": "title-year",
    "textAlignedWith": "alignment",
}
# The routes the supplement is sized for; alignment is deterministic.
MEASURED_ROUTES = ("field", "title-year")
SHEET_FIELDS = (
    "sample_id",
    "volume",
    "address",
    "pdf_page",
    "print_text",
    "wiki_page",
    "decision",
    "note",
)


def sample_id(entry: str) -> str:
    return hashlib.sha256(entry.encode()).hexdigest()[:10]


def claims_by_entry(path: Path = CLAIMS, wanted: set[str] | None = None) -> dict:
    """Per print entry and route its claims as (claim id, wiki page, wiki line)."""
    out: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    with path.open(encoding="utf-8") as source:
        for claim in map(json.loads, source):
            entry = claim["subject"].split("#", 1)[0]
            if wanted is not None and entry not in wanted:
                continue
            evidence = claim["evidence"]
            page = evidence.get("wiki_page") or int(claim["object"].rsplit("/", 1)[1])
            out[entry][ROUTES[claim["predicate"]]].append(
                (claim["id"], page, evidence.get("wiki_line", ""))
            )
    return out


def proposals(path: Path = CLAIMS, wanted: set[str] | None = None) -> dict:
    """Per print entry: wiki pages proposed by route."""
    return {
        entry: {route: {page for _, page, _ in rows} for route, rows in routes.items()}
        for entry, routes in claims_by_entry(path, wanted).items()
    }


def stratum(routes: dict) -> str:
    if routes.get("field"):
        return "field"
    return "title-year" if routes.get("title-year") else "none"


def capped(routes: dict, route: str) -> int:
    return min(CLAIMS_PER_ENTRY, len(routes.get(route, ())))


def frame(volume: str):
    """The numbered entries of kind "entry" of a volume, with whether an
    object carries a read year."""
    with (RECORDS / f"entries-{volume}.jsonl").open(encoding="utf-8") as source:
        for record in map(json.loads, source):
            if record["kind"] == "entry" and record["address"]:
                yield record, any(summary(o)["year"] for o in record["objects"])


def sheet_row(record: dict, volume: str) -> dict:
    return {
        "sample_id": sample_id(record["id"]),
        "volume": volume,
        "address": record["address"],
        "pdf_page": record["page"],
        "print_text": record["text"],
        "wiki_page": "",
        "decision": "",
        "note": "",
    }


def _write_sheet(path: Path, rows: list[dict], fields=SHEET_FIELDS) -> None:
    with path.open("w", encoding="utf-8", newline="") as sink:
        writer = csv.DictWriter(sink, fieldnames=list(fields))
        writer.writeheader()
        writer.writerows(rows)


def _refuse(*paths: Path) -> None:
    for path in paths:
        if path.exists():
            sys.exit(f"FEHLER: {path} is frozen; not redrawn")


def answers(path: Path) -> tuple[dict[str, tuple | None], list[str]]:
    """The person's answers of a blind sheet by sample_id: ("page", id),
    ("none",), ("unsure",) or None while open, and the rows that break the
    convention (a page and a "none" at once, an unknown decision)."""
    out, problems = {}, []
    if not path.exists():
        return out, problems
    with path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            page = (row.get("wiki_page") or "").strip()
            decision = (row.get("decision") or "").strip().lower()
            sid = row["sample_id"]
            if page and page.isdigit() and decision in ("", "page"):
                out[sid] = ("page", int(page))
            elif not page and decision in ("none", "unsure"):
                out[sid] = (decision,)
            elif not page and not decision:
                out[sid] = None
            else:
                out[sid] = None
                problems.append(
                    f"{path.name} row {sid}: wiki_page a page id, or decision none or unsure"
                )
    return out, problems


def claim_answers(path: Path = CLAIMS_SHEET) -> tuple[list[dict], list[str]]:
    """The rows of the claim sheet with the person's decision normalised."""
    rows, problems = [], []
    if not path.exists():
        return rows, problems
    with path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            decision = (row.get("decision") or "").strip().lower()
            if decision not in ("", "right", "wrong", "unsure"):
                problems.append(
                    f"claim {row['claim_id']}: decision right, wrong or unsure"
                )
                decision = ""
            rows.append({**row, "decision": decision or None})
    return rows, problems


def draw() -> int:
    _refuse(SHEET, KEY)
    if not CLAIMS.exists():
        sys.exit(f"FEHLER: {CLAIMS} missing; run p07_concordance.py first")
    proposed = proposals()
    rng = random.Random(SEED)
    rows, key, sizes = [], {}, {}
    for volume in VOLUMES:
        pools: dict[str, list[dict]] = {s: [] for s in STRATA}
        for record, has_year in frame(volume):
            if has_year:
                pools[stratum(proposed.get(record["id"], {}))].append(record)
        sizes[volume] = {s: len(p) for s, p in pools.items()}
        for s in STRATA:
            pool = sorted(pools[s], key=lambda r: r["id"])
            for record in rng.sample(pool, min(PER_STRATUM, len(pool))):
                rows.append(sheet_row(record, volume))
                key[rows[-1]["sample_id"]] = {
                    "printId": record["id"],
                    "stratum": s,
                    "proposed": {
                        r: sorted(p) for r, p in proposed.get(record["id"], {}).items()
                    },
                }
    # Shuffle so that strata are not visible from the order of the sheet.
    rng.shuffle(rows)
    SAMPLES.mkdir(parents=True, exist_ok=True)
    _write_sheet(SHEET, rows)
    KEY.write_text(
        json.dumps(
            {"seed": SEED, "perStratum": PER_STRATUM, "sizes": sizes, "key": key},
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"OK {len(rows)} entries frozen -> {SHEET}")
    print(f"OK key (do not open before the sheet is complete) -> {KEY}")
    return 0


def first_key() -> dict:
    return json.loads(KEY.read_text("utf-8"))["key"]


def draw_strata() -> int:
    _refuse(BLIND_STRATA)
    key = first_key()
    old = proposals(BASELINE_CLAIMS)
    sizes, agree = {}, {}
    recorded = {row["printId"]: row["stratum"] for row in key.values()}
    for volume in VOLUMES:
        count, same = Counter(), Counter()
        for record, has_year in frame(volume):
            if not has_year:
                continue
            s = stratum(old.get(record["id"], {}))
            count[s] += 1
            if record["id"] in recorded:
                same["drawn"] += 1
                same["same_stratum"] += recorded[record["id"]] == s
        sizes[volume] = {s: count[s] for s in STRATA}
        agree[volume] = dict(same)
        print(
            f"OK {volume}: sizes {sizes[volume]}, drawn in their stratum {agree[volume]}"
        )
    BLIND_STRATA.write_text(
        json.dumps(
            {
                "about": "Stratum sizes of the first blind sample, reconstructed: the "
                "sizes of 2026-10-23 were not kept, so p09's pool and stratum rule is "
                "applied to the oldest claims kept and the records at writing. "
                "drawnInTheirStratum counts the drawn entries the reconstruction puts "
                "in the stratum they were drawn in. Counts and hashes only.",
                "reconstructed": True,
                "claims": {
                    "file": BASELINE_CLAIMS.relative_to(DERIVED_DIR).as_posix(),
                    "sha256": sha256_file(BASELINE_CLAIMS),
                },
                "records": {
                    p.name: sha256_file(p)
                    for p in sorted(RECORDS.glob("entries-*.jsonl"))
                },
                "perStratum": PER_STRATUM,
                "sizes": sizes,
                "drawnInTheirStratum": agree,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"OK frozen -> {BLIND_STRATA}")
    return 0


def supplement_sizes(
    pools: dict[str, list[dict]], have: dict[str, int]
) -> dict[str, int]:
    """Entries to draw per stratum of one volume: enough field and title-year
    entries for TARGET_CLAIMS claims of their route on the claim sheet, given
    the claims the first sample already has, and the no-year quota."""
    out = {s: 0 for s in SUPPLEMENT_STRATA}
    for route in MEASURED_ROUTES:
        pool = pools[route]
        need = TARGET_CLAIMS - have.get(route, 0)
        if need <= 0 or not pool:
            continue
        mean = sum(capped(r["routes"], route) for r in pool) / len(pool)
        out[route] = min(len(pool), math.ceil(need / mean))
    out["no-year"] = min(NO_YEAR_PER_VOLUME, len(pools["no-year"]))
    return out


def draw_supplement() -> int:
    _refuse(BLIND_SHEET_2, BLIND_KEY_2)
    if not BLIND_STRATA.exists():
        sys.exit(f"FEHLER: {BLIND_STRATA} missing; run --strata first")
    first = first_key()
    current = claims_by_entry()
    old = proposals(BASELINE_CLAIMS)
    dev = {
        i
        for parts in json.loads(DEV.read_text("utf-8"))["units"].values()
        for ids in parts.values()
        for i in ids
    }
    first_ids = {row["printId"]: sid for sid, row in first.items()}
    rng = random.Random(SUPPLEMENT_SEED)
    rows, key, sizes, first_rows, prints = [], {}, {}, {}, {}
    for volume in VOLUMES:
        pools: dict[str, list[dict]] = {s: [] for s in SUPPLEMENT_STRATA}
        have: Counter = Counter()
        for record, has_year in frame(volume):
            routes = current.get(record["id"], {})
            s = stratum(routes) if has_year else "no-year"
            if record["id"] in first_ids:
                first_rows[first_ids[record["id"]]] = s
                for route in MEASURED_ROUTES:
                    have[route] += capped(routes, route)
                continue
            if record["id"] in dev or is_held_out(record):
                continue
            pools[s].append({"record": record, "routes": routes, "has_year": has_year})
        wanted = supplement_sizes(pools, have)
        sizes[volume] = {
            s: {"pool": len(pools[s]), "drawn": wanted[s]} for s in SUPPLEMENT_STRATA
        }
        for s in SUPPLEMENT_STRATA:
            pool = sorted(pools[s], key=lambda u: u["record"]["id"])
            for unit in rng.sample(pool, wanted[s]):
                record = unit["record"]
                rows.append(sheet_row(record, volume))
                first_design = (
                    stratum(old.get(record["id"], {}))
                    if unit["has_year"]
                    else "outside"
                )
                key[rows[-1]["sample_id"]] = {
                    "printId": record["id"],
                    "stratum": s,
                    "firstDesignStratum": first_design,
                }
                prints[record["id"]] = fingerprint(record)
        print(f"OK {volume}: {sizes[volume]}, first sample capped claims {dict(have)}")
    missing = set(first) - set(first_rows)
    if missing:
        sys.exit(f"FEHLER: {len(missing)} first-sample entries not in the records")
    rng.shuffle(rows)
    _write_sheet(BLIND_SHEET_2, rows)
    BLIND_KEY_2.write_text(
        json.dumps(
            {
                "about": "Supplementary blind sample: strata on the claims at drawing, "
                "sizes at drawing, each drawn entry's stratum under the first design "
                "(reconstructed as in concordance-blind-strata.json; outside for an "
                "entry without a year) and each first-sample row's stratum under this "
                "design. Identifiers, strata, sizes and fingerprints only.",
                "seed": SUPPLEMENT_SEED,
                "claimsPerEntry": CLAIMS_PER_ENTRY,
                "targetClaims": TARGET_CLAIMS,
                "sizes": sizes,
                "claims_sha256": sha256_file(CLAIMS),
                "firstSampleStrata": dict(sorted(first_rows.items())),
                "key": key,
                "fingerprints": dict(sorted(prints.items())),
                "remapped": [],
                "rehashed": [],
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"OK {len(rows)} entries frozen -> {BLIND_SHEET_2}")
    print(f"OK key (do not open before the sheet is complete) -> {BLIND_KEY_2}")
    return 0


CLAIM_FIELDS = (
    "claim_id",
    "sample_id",
    "volume",
    "address",
    "pdf_page",
    "print_text",
    "route",
    "wiki_page",
    "wiki_line",
    "claims_of_route",
    "drawn_of_route",
    "decision",
    "note",
)


def draw_claims_sheet() -> int:
    _refuse(CLAIMS_SHEET)
    keys = {**first_key(), **json.loads(BLIND_KEY_2.read_text("utf-8"))["key"]}
    for sheet in (SHEET, BLIND_SHEET_2):
        found, problems = answers(sheet)
        open_rows = sum(1 for a in found.values() if a is None)
        if problems or open_rows or not found:
            sys.exit(
                f"FEHLER: {sheet.name} is not complete ({open_rows} open, "
                f"{len(problems)} malformed); phase 2 waits for the blind phase"
            )
    entries = {row["printId"]: sid for sid, row in keys.items()}
    current = claims_by_entry(wanted=set(entries))
    records = {}
    for volume in VOLUMES:
        for record, _ in frame(volume):
            if record["id"] in entries:
                records[record["id"]] = record
    rng = random.Random(CLAIMS_SEED)
    rows = []
    for entry in sorted(entries):
        record = records[entry]
        for route, claims in sorted(current.get(entry, {}).items()):
            chosen = sorted(claims)
            if len(chosen) > CLAIMS_PER_ENTRY:
                chosen = sorted(rng.sample(chosen, CLAIMS_PER_ENTRY))
            for claim_id, page, line in chosen:
                rows.append(
                    {
                        "claim_id": claim_id,
                        "sample_id": entries[entry],
                        "volume": record["volume"],
                        "address": record["address"],
                        "pdf_page": record["page"],
                        "print_text": record["text"],
                        "route": route,
                        "wiki_page": page,
                        "wiki_line": line,
                        "claims_of_route": len(claims),
                        "drawn_of_route": len(chosen),
                        "decision": "",
                        "note": "",
                    }
                )
    rng.shuffle(rows)
    _write_sheet(CLAIMS_SHEET, rows, CLAIM_FIELDS)
    print(f"OK {len(rows)} claims frozen -> {CLAIMS_SHEET}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--strata", action="store_true", help="reconstruct the first sizes"
    )
    group.add_argument("--supplement", action="store_true", help="draw the supplement")
    group.add_argument(
        "--claims-sheet", action="store_true", help="write the phase-2 claim sheet"
    )
    args = parser.parse_args()
    if args.strata:
        return draw_strata()
    if args.supplement:
        return draw_supplement()
    if args.claims_sheet:
        return draw_claims_sheet()
    return draw()


if __name__ == "__main__":
    sys.exit(main())
