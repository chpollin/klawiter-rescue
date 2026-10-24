"""What rule development must never look at: the benchmark pages and the human samples.

Both benchmark samples (bench/sample.json, bench/v2/sample.json) are held out by
page, the frozen blind sample of p09 and the review sample of the field check
(review_sample.py) by entry. Development samples, notation
counts and any example printed while writing rules exclude them through
is_held_out, so that a later score on them still measures unseen material.
Version 1 was tuned on before it was declared development (bench_sample.py);
it stays excluded here as well, which costs a few pages and keeps one rule.
"""

import json
from functools import cache

from _common import DERIVED_DIR

BENCH = DERIVED_DIR / "bench"
BLIND_KEY = DERIVED_DIR / "samples" / "concordance-blind-key.json"
REVIEW_SAMPLE = DERIVED_DIR / "samples" / "review-sample.json"


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
def held_out_entries() -> frozenset[str]:
    entries = {o.split("#")[0] for o in review_objects()}
    if BLIND_KEY.exists():
        key = json.loads(BLIND_KEY.read_text("utf-8"))["key"]
        entries.update(row["printId"] for row in key.values())
    return frozenset(entries)


def is_held_out(record: dict) -> bool:
    """True for a record on a benchmark page or in a human sample."""
    if record["id"] in held_out_entries():
        return True
    pages = held_out_pages().get(record["volume"], frozenset())
    return any(p in pages for p in range(record["page"], record["page_end"] + 1))
