"""What rule development must never look at: the benchmark pages and the human samples.

Both benchmark samples (bench/sample.json, bench/v2/sample.json) are held out by
page, the frozen blind samples of p09 (the first and its supplement) and the
review samples of the field check (review_sample.py: the review sample and its
stratum of hard entries) by entry. Development samples, notation
counts and any example printed while writing rules exclude them through
is_held_out, so that a later score on them still measures unseen material.
Version 1 was tuned on before it was declared development (bench_sample.py);
it stays excluded here as well, which costs a few pages and keeps one rule.
"""

import json
from functools import cache

from _common import DERIVED_DIR

BENCH = DERIVED_DIR / "bench"
SAMPLES = DERIVED_DIR / "samples"
BLIND_KEY = SAMPLES / "concordance-blind-key.json"
BLIND_SHEET = SAMPLES / "concordance-blind-sheet.csv"
BLIND_KEY_2 = SAMPLES / "concordance-blind-key-2.json"
BLIND_SHEET_2 = SAMPLES / "concordance-blind-sheet-2.csv"
BLIND_STRATA = SAMPLES / "concordance-blind-strata.json"
CLAIMS_SHEET = SAMPLES / "concordance-claims-sheet.csv"
REVIEW_SAMPLE = SAMPLES / "review-sample.json"
REVIEW_POOLS = SAMPLES / "review-sample-pools.json"
REVIEW_HARD = SAMPLES / "review-hard-sample.json"
REVIEW_SECOND = SAMPLES / "review-second-subset.json"


@cache
def review_objects() -> tuple[str, ...]:
    """Object identifiers of the frozen review sample, in volume and part order."""
    if not REVIEW_SAMPLE.exists():
        return ()
    parts = json.loads(REVIEW_SAMPLE.read_text("utf-8"))["objects"]
    return tuple(o for volume in parts.values() for ids in volume.values() for o in ids)


@cache
def held_out_pages() -> dict[str, frozenset[int]]:
    pages: dict[str, set[int]] = {}
    for path in (BENCH / "sample.json", BENCH / "v2" / "sample.json"):
        if path.exists():
            for volume, numbers in json.loads(path.read_text("utf-8"))["pages"].items():
                pages.setdefault(volume, set()).update(map(int, numbers))
    return {v: frozenset(p) for v, p in pages.items()}


@cache
def hard_objects() -> tuple[str, ...]:
    """Object identifiers of the frozen stratum of hard entries, by volume."""
    if not REVIEW_HARD.exists():
        return ()
    parts = json.loads(REVIEW_HARD.read_text("utf-8"))["objects"]
    return tuple(o for ids in parts.values() for o in ids)


@cache
def held_out_entries() -> frozenset[str]:
    entries = {o.split("#")[0] for o in (*review_objects(), *hard_objects())}
    for path in (BLIND_KEY, BLIND_KEY_2):
        if path.exists():
            key = json.loads(path.read_text("utf-8"))["key"]
            entries.update(row["printId"] for row in key.values())
    return frozenset(entries)


def is_held_out(record: dict) -> bool:
    """True for a record on a benchmark page or in a human sample."""
    if record["id"] in held_out_entries():
        return True
    pages = held_out_pages().get(record["volume"], frozenset())
    return any(p in pages for p in range(record["page"], record["page_end"] + 1))
