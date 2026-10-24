"""Draw the frozen development sample for the object fields, stratified by volume and part.

Rules for the structured object fields are written and inspected on this sample
only; the benchmark pages and the blind sample of p09 never enter it
(_heldout.py). Per volume and part it draws PER_PART units of kind entry or
reference with a fixed seed. The sample is frozen: a second run refuses to
overwrite it, so that it stays the same while the rules change. It holds record
identifiers only; the texts stay in the local records.

Output: data/print/derived/samples/dev-sample.json (local).

Usage: python -m uv run python pipeline/print_volumes/dev_sample.py
"""

import json
import random
import sys

from _common import DERIVED_DIR, VOLUMES
from _heldout import is_held_out

RECORDS = DERIVED_DIR / "records"
OUT = DERIVED_DIR / "samples" / "dev-sample.json"
SEED = 20261025
PER_PART = 8


def main() -> int:
    if OUT.exists():
        sys.exit(f"FEHLER: {OUT} is frozen; not redrawn")
    rng = random.Random(SEED)
    sample: dict[str, dict[str, list[str]]] = {}
    for volume in VOLUMES:
        pools: dict[str, list[str]] = {}
        with (RECORDS / f"entries-{volume}.jsonl").open(encoding="utf-8") as source:
            for record in map(json.loads, source):
                if record["kind"] == "heading" or is_held_out(record):
                    continue
                pools.setdefault(record["part"], []).append(record["id"])
        sample[volume] = {
            part: sorted(rng.sample(sorted(ids), min(PER_PART, len(ids))))
            for part, ids in sorted(pools.items())
        }
        print(f"OK {volume}: {sum(map(len, sample[volume].values()))} units")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"seed": SEED, "perPart": PER_PART, "units": sample}, indent=1),
        encoding="utf-8",
    )
    print(f"OK frozen -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
