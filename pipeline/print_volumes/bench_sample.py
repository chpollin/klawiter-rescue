"""Draw a held-out benchmark sample of print-volume pages.

Version 1 (data/print/derived/bench/sample.json) was the first sample. It is
proportional to section size and too small for the hard sections; since rules
were later tuned on its error classes, its pages now belong to development.

Version 2 (bench/v2/sample.json) is drawn before the rules are evaluated and
frozen: a second draw refuses to overwrite it. Per volume it takes one page
from each named hard section, then fills the quota by page share over all
body sections, never using version-1 pages. Each page records its stratum and
inclusion weight, so that scores can be reported per stratum and reweighted.
The hard sections are chosen from document knowledge (section structure and
the first benchmark), not from method output on candidate pages.

Usage: python -m uv run python pipeline/print_volumes/bench_sample.py --version 2
"""

import argparse
import json
import random
import sys

from _common import DERIVED_DIR, SECTIONS

BENCH = DERIVED_DIR / "bench"
PLANS = {
    1: {"seed": 20261023, "quota": {"I": 8, "A1": 6, "A2": 14}, "hard": {}},
    2: {
        "seed": 20261024,
        "quota": {"I": 12, "A1": 8, "A2": 24},
        # Sections with commentary, insertions, numbered runs or reprint lists.
        "hard": {
            "I": ["A", "E", "G", "K", "M"],
            "A1": ["H", "K", "M", "N"],
            "A2": ["A", "B", "D", "F", "G", "H", "K", "P"],
        },
    },
}


def _body_parts(volume: str) -> list[tuple[str, int, int]]:
    return [
        (name, first, last)
        for name, kind, first, last, *_ in SECTIONS["volumes"][volume]["parts"]
        if kind == "body"
    ]


def draw(version: int, exclude: dict[str, set[int]]) -> dict:
    plan = PLANS[version]
    rng = random.Random(plan["seed"])
    sample = {}
    for volume, quota in plan["quota"].items():
        parts = _body_parts(volume)
        taken: dict[int, dict] = {}
        banned = exclude.get(volume, set())
        for name in plan["hard"].get(volume, []):
            first, last = next((f, la) for n, f, la in parts if n == name)
            pool = [p for p in range(first, last + 1) if p not in banned]
            page = rng.choice(pool)
            taken[page] = {"stratum": f"hard:{name}", "weight": 1 / len(pool)}
        pages = [
            p
            for _, first, last in parts
            for p in range(first, last + 1)
            if p not in banned and p not in taken
        ]
        for page in rng.sample(pages, quota - len(taken)):
            taken[page] = {"stratum": "random", "weight": 1 / len(pages)}
        sample[volume] = dict(sorted(taken.items()))
    return sample


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", type=int, choices=sorted(PLANS), default=2)
    args = parser.parse_args()
    out = BENCH / (
        "sample.json" if args.version == 1 else f"v{args.version}/sample.json"
    )
    if out.exists():
        print(f"SKIP {out} exists and stays frozen")
        return 0
    exclude: dict[str, set[int]] = {}
    v1 = BENCH / "sample.json"
    if args.version > 1 and v1.exists():
        pages = json.loads(v1.read_text(encoding="utf-8"))["pages"]
        exclude = {v: set(map(int, p)) for v, p in pages.items()}
    sample = draw(args.version, exclude)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "version": args.version,
                "seed": PLANS[args.version]["seed"],
                "pages": {v: list(p) for v, p in sample.items()},
                "strata": sample,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    for volume, pages in sample.items():
        print(f"OK {volume}: {[(p, d['stratum']) for p, d in pages.items()]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
