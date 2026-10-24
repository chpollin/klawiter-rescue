"""Draw the frozen review sample on which a person measures field correctness.

Schema validity and the invariants of p10 show that every value is span-bound
and consistent; whether it is the right value in its context only a person can
decide. The viewer records those decisions (review_server.py), and p13_review.py
measures correctness on this sample alone. It is stratified by volume and part,
PER_PART objects from distinct entries with a fixed seed. Entries that rule
development has seen never enter it: the held-out pages and the blind sample
(they stay reserved for their own measurements), the development sample, and
every entry with a listed p10 exception or violation. Once drawn, its entries
are held out from rule development as well (_heldout.py). The sample is frozen:
a second run refuses to overwrite it. It holds identifiers only.

Output: data/print/derived/samples/review-sample.json (local).

Usage: python -m uv run python pipeline/print_volumes/review_sample.py
"""

import json
import random
import sys
from pathlib import Path

from _common import DERIVED_DIR, VOLUMES
from _heldout import REVIEW_SAMPLE, is_held_out

HERE = Path(__file__).resolve().parent
RECORDS = DERIVED_DIR / "records"
DEV = DERIVED_DIR / "samples" / "dev-sample.json"
VIOLATIONS = DERIVED_DIR / "reports" / "p10_violations.jsonl"
SEED = 20261026
PER_PART = 3


def _seen() -> set[str]:
    """Entries that rule development has looked at."""
    seen = set()
    dev = json.loads(DEV.read_text("utf-8"))["units"]
    for parts in dev.values():
        for ids in parts.values():
            seen.update(ids)
    with VIOLATIONS.open(encoding="utf-8") as source:
        seen.update(json.loads(line)["object"].split("#")[0] for line in source)
    exceptions = json.loads((HERE / "known_exceptions.json").read_text("utf-8"))
    for invariant, ids in exceptions.items():
        if not invariant.startswith("_"):
            seen.update(i.split("#")[0] for i in ids)
    return seen


def main() -> int:
    if REVIEW_SAMPLE.exists():
        sys.exit(f"FEHLER: {REVIEW_SAMPLE} is frozen; not redrawn")
    seen = _seen()
    rng = random.Random(SEED)
    sample: dict[str, dict[str, list[str]]] = {}
    for volume in VOLUMES:
        pools: dict[str, list[list[str]]] = {}
        with (RECORDS / f"entries-{volume}.jsonl").open(encoding="utf-8") as source:
            for record in map(json.loads, source):
                if (
                    record["kind"] == "heading"
                    or not record["objects"]
                    or record["id"] in seen
                    or is_held_out(record)
                ):
                    continue
                pools.setdefault(record["part"], []).append(
                    [o["id"] for o in record["objects"]]
                )
        sample[volume] = {}
        for part, entries in sorted(pools.items()):
            # One object per entry, so that no entry weighs twice.
            chosen = rng.sample(entries, min(PER_PART, len(entries)))
            sample[volume][part] = sorted(rng.choice(objects) for objects in chosen)
        print(f"OK {volume}: {sum(map(len, sample[volume].values()))} objects")
    REVIEW_SAMPLE.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_SAMPLE.write_text(
        json.dumps({"seed": SEED, "perPart": PER_PART, "objects": sample}, indent=1),
        encoding="utf-8",
    )
    print(f"OK frozen -> {REVIEW_SAMPLE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
