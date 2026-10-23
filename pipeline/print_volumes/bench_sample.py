"""Draw the held-out benchmark sample of print-volume pages.

The sample is stratified: every body part of a volume contributes pages in
proportion to its size, with at least one page, up to the volume's quota, and
the draw is seeded so that it is reproducible. Addendum II receives the largest
quota because its structure is the least determined (probe_roundtrip.py).

These pages form the test set. Rules must not be tuned on them; development
uses any other page. Human or agent annotators label them blind, without
access to the rules or the probe results, and bench_compare.py scores the
segmentation against those labels.

Output: data/print/derived/bench/sample.json

Usage: python -m uv run python pipeline/print_volumes/bench_sample.py
"""

import json
import random
import sys

from _common import DERIVED_DIR, SECTIONS

SEED = 20261023
QUOTA = {"I": 8, "A1": 6, "A2": 14}


def draw() -> dict:
    rng = random.Random(SEED)
    sample = {}
    for volume, quota in QUOTA.items():
        parts = [
            (name, first, last)
            for name, kind, first, last in SECTIONS["volumes"][volume]["parts"]
            if kind == "body"
        ]
        total = sum(last - first + 1 for _, first, last in parts)
        weighted = sorted(parts, key=lambda p: (p[2] - p[1] + 1) / total, reverse=True)
        pages: list[int] = []
        for name, first, last in weighted:
            share = max(1, round(quota * (last - first + 1) / total))
            pool = [p for p in range(first, last + 1) if p not in pages]
            pages.extend(rng.sample(pool, min(share, len(pool))))
            if len(pages) >= quota:
                break
        sample[volume] = sorted(pages[:quota])
    return sample


def main() -> int:
    sample = draw()
    out = DERIVED_DIR / "bench" / "sample.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"seed": SEED, "pages": sample}, indent=1), encoding="utf-8"
    )
    for volume, pages in sample.items():
        print(f"OK {volume}: {pages}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
