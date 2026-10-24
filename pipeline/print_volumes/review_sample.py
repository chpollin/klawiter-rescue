"""Draw the frozen review sample on which a person measures field correctness, and its supplements.

Schema validity and the invariants of p10 show that every value is span-bound
and consistent; whether it is the right value in its context only a person can
decide. The viewer records those decisions (review_server.py), and p13_review.py
measures correctness on these samples alone. The review sample is stratified
by volume and part, PER_PART objects from distinct entries with a fixed seed.
Entries that rule development has seen never enter it: the held-out pages and
the blind sample (they stay reserved for their own measurements), the
development sample, and every entry with a listed p10 exception or violation.
Once drawn, its entries are held out from rule development as well
(_heldout.py). Every sample is frozen: a second run refuses to overwrite it.
Each holds identifiers, counts and fingerprints only (p14_gate.fingerprint).

The review sample (2026-10-24) draws PER_PART objects from parts of very
different size, so an unweighted figure lets a small part weigh as much as a
large one. Three supplements, drawn after it and before any decision:

--pools: per part the number of entries with objects, of hard entries among
  them (a p10 violation or a listed exception today) and of entries the
  drawing rule admits today, beside the objects drawn. p13 weighs each object
  of a part by (entries - hard) / drawn; the drawing frame is reconstructed
  from the current records, since the frame of the day was not kept.
--hard: the entries the review sample excluded because they carry a p10
  violation or a listed exception, outside the development sample and every
  held-out sample, one object per entry, up to HARD_PER_VOLUME per volume
  (today a census). p13 reports them apart and weighs them by pool / drawn.
--second: SECOND_SIZE objects of the review sample, allocated to the volumes
  in proportion and drawn with a fixed seed, which the second reviewer
  decides; agreement is measured on them only.

--protocol, after the three supplements and before any decision: the order in
which the review phase presents its objects, and the hidden repeat set.
- The first reviewer's queue is the review sample and the hard stratum mixed,
  in an order shuffled with PROTOCOL_SEED, so that neither the part nor the
  stratum shows from the position and fatigue does not fall on one part.
- The second reviewer's queue is the marked subset, shuffled on its own.
- REPEAT_SIZE objects of the review sample, drawn among those shown at least
  REPEAT_GAP places before the end, form the repeat set. Each comes back once
  in the first reviewer's queue, at a seeded position more than REPEAT_GAP
  places after its first showing, without its earlier decisions in
  view; the second judgement of its values is logged as a repeat (_review.py)
  and measures intra-rater consistency in p13. The queue does not mark which
  showing is a repeat; the viewer must not either.
The file holds identifiers, the seed and the hashes of the samples it orders.

Output (local): data/print/derived/samples/review-sample.json,
review-sample-pools.json, review-hard-sample.json, review-second-subset.json,
review-protocol.json.

Usage: python -m uv run python pipeline/print_volumes/review_sample.py
       [--pools | --hard | --second | --protocol]
"""

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

from _common import DERIVED_DIR, VOLUMES
from _heldout import (
    BLIND_KEY,
    REVIEW_HARD,
    REVIEW_POOLS,
    REVIEW_SAMPLE,
    REVIEW_SECOND,
    held_out_pages,
    is_held_out,
    review_objects,
)
from p14_gate import fingerprint, sha256_file

HERE = Path(__file__).resolve().parent
RECORDS = DERIVED_DIR / "records"
DEV = DERIVED_DIR / "samples" / "dev-sample.json"
VIOLATIONS = DERIVED_DIR / "reports" / "p10_violations.jsonl"
SEED = 20261026
PER_PART = 3
HARD_SEED = 20261027
HARD_PER_VOLUME = 20
SECOND_SEED = 20261028
SECOND_SIZE = 40
REVIEW_PROTOCOL = REVIEW_SAMPLE.parent / "review-protocol.json"
PROTOCOL_SEED = 20261031
# The repeat set costs ten objects of extra work; a gap of thirty objects puts
# other work between the two judgements, and p13 reports the actual interval
# from the log times.
REPEAT_SIZE = 10
REPEAT_GAP = 30


def _development() -> set[str]:
    dev = json.loads(DEV.read_text("utf-8"))["units"]
    return {i for parts in dev.values() for ids in parts.values() for i in ids}


def _hard() -> set[str]:
    """Entries with a p10 violation or a listed exception."""
    hard = set()
    with VIOLATIONS.open(encoding="utf-8") as source:
        hard.update(json.loads(line)["object"].split("#")[0] for line in source)
    exceptions = json.loads((HERE / "known_exceptions.json").read_text("utf-8"))
    for invariant, ids in exceptions.items():
        if not invariant.startswith("_"):
            hard.update(i.split("#")[0] for i in ids)
    return hard


def _seen() -> set[str]:
    """Entries that rule development has looked at."""
    return _development() | _hard()


def _records(volume: str):
    with (RECORDS / f"entries-{volume}.jsonl").open(encoding="utf-8") as source:
        yield from map(json.loads, source)


def _freeze(path: Path, payload: dict) -> None:
    if path.exists():
        sys.exit(f"FEHLER: {path} is frozen; not redrawn")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"OK frozen -> {path}")


def _fingerprints(object_ids) -> dict[str, str]:
    """Per object identifier its fingerprint in the current records."""
    wanted = {o.split("#")[0] for o in object_ids}
    records = {r["id"]: r for v in VOLUMES for r in _records(v) if r["id"] in wanted}
    return {o: fingerprint(records[o.split("#")[0]], o) for o in sorted(object_ids)}


def draw_review() -> int:
    if REVIEW_SAMPLE.exists():
        sys.exit(f"FEHLER: {REVIEW_SAMPLE} is frozen; not redrawn")
    seen = _seen()
    rng = random.Random(SEED)
    sample: dict[str, dict[str, list[str]]] = {}
    for volume in VOLUMES:
        pools: dict[str, list[list[str]]] = {}
        for record in _records(volume):
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
    _freeze(REVIEW_SAMPLE, {"seed": SEED, "perPart": PER_PART, "objects": sample})
    return 0


def pools() -> dict:
    """Per volume and part: entries with objects, hard ones among them, the
    entries the review sample's rule admits today, and the objects drawn."""
    drawn = json.loads(REVIEW_SAMPLE.read_text("utf-8"))["objects"]
    sampled = {o.split("#")[0] for o in review_objects()}
    dev, hard = _development(), _hard()
    blind = {
        row["printId"]
        for row in json.loads(BLIND_KEY.read_text("utf-8"))["key"].values()
    }
    pages = held_out_pages()
    out: dict[str, dict[str, dict]] = {}
    for volume in VOLUMES:
        count: dict[str, Counter] = {}
        bench = pages.get(volume, frozenset())
        for r in _records(volume):
            if r["kind"] == "heading" or not r["objects"]:
                continue
            c = count.setdefault(r["part"], Counter())
            c["entries"] += 1
            c["hard"] += r["id"] in hard
            # The rule of the drawing on today's records: neither seen nor held
            # out by another sample; the sample's own entries were admitted.
            on_bench = any(p in bench for p in range(r["page"], r["page_end"] + 1))
            c["eligible"] += r["id"] in sampled or not (
                r["id"] in dev or r["id"] in hard or r["id"] in blind or on_bench
            )
        out[volume] = {
            part: {
                "entries": c["entries"],
                "hard": c["hard"],
                "eligible": c["eligible"],
                "drawn": len(drawn.get(volume, {}).get(part, [])),
            }
            for part, c in sorted(count.items())
        }
    return out


def draw_pools() -> int:
    table = pools()
    for volume, parts in table.items():
        lacking = [
            p for p, c in parts.items() if c["drawn"] and c["entries"] <= c["hard"]
        ]
        if lacking:
            sys.exit(
                f"FEHLER {volume}: parts {lacking} hold no entry outside the hard ones"
            )
    _freeze(
        REVIEW_POOLS,
        {
            "about": "Per volume and part of the review sample: entries with objects, "
            "hard entries among them (p10 violation or listed exception at writing), "
            "entries the drawing rule admits on the records at writing (the frame of "
            "the drawing was not kept), and objects drawn. Counts only.",
            "sample": REVIEW_SAMPLE.name,
            "parts": table,
        },
    )
    return 0


def draw_hard() -> int:
    dev, hard = _development(), _hard()
    rng = random.Random(HARD_SEED)
    sample: dict[str, list[str]] = {}
    sizes: dict[str, dict] = {}
    for volume in VOLUMES:
        pool = sorted(
            (r["id"], [o["id"] for o in r["objects"]])
            for r in _records(volume)
            if r["id"] in hard
            and r["kind"] != "heading"
            and r["objects"]
            and r["id"] not in dev
            and not is_held_out(r)
        )
        chosen = rng.sample(pool, min(HARD_PER_VOLUME, len(pool)))
        sample[volume] = sorted(rng.choice(objects) for _, objects in chosen)
        sizes[volume] = {"pool": len(pool), "drawn": len(sample[volume])}
        print(f"OK {volume}: {len(sample[volume])} of {len(pool)} hard entries")
    ids = [o for ids in sample.values() for o in ids]
    _freeze(
        REVIEW_HARD,
        {
            "about": "Entries the review sample excluded (p10 violation or listed "
            "exception), outside the development sample and every held-out sample; "
            "one object per entry. Reported apart from the review sample.",
            "seed": HARD_SEED,
            "perVolume": HARD_PER_VOLUME,
            "pools": sizes,
            "objects": sample,
            "fingerprints": _fingerprints(ids),
            "remapped": [],
            "rehashed": [],
        },
    )
    return 0


def allocate(sizes: dict[str, int], total: int) -> dict[str, int]:
    """Proportional allocation by largest remainder, never above a stratum's size."""
    whole = sum(sizes.values())
    quota = {k: total * n / whole for k, n in sizes.items()}
    out = {k: min(int(q), sizes[k]) for k, q in quota.items()}
    for k in sorted(quota, key=lambda k: (out[k] - quota[k], k)):
        if sum(out.values()) >= min(total, whole):
            break
        if out[k] < sizes[k]:
            out[k] += 1
    return out


def draw_second() -> int:
    by_volume = {
        v: sorted(o for ids in parts.values() for o in ids)
        for v, parts in json.loads(REVIEW_SAMPLE.read_text("utf-8"))["objects"].items()
    }
    share = allocate({v: len(ids) for v, ids in by_volume.items()}, SECOND_SIZE)
    rng = random.Random(SECOND_SEED)
    chosen = sorted(o for v in VOLUMES for o in rng.sample(by_volume[v], share[v]))
    print(f"OK second reviewer: {share}")
    _freeze(
        REVIEW_SECOND,
        {
            "about": "Objects of the review sample the second reviewer decides, "
            "marked before any decision; agreement is measured on them only.",
            "seed": SECOND_SEED,
            "size": SECOND_SIZE,
            "perVolume": share,
            "objects": chosen,
            "fingerprints": _fingerprints(chosen),
            "remapped": [],
            "rehashed": [],
        },
    )
    return 0


def protocol(
    review: list[str],
    hard: list[str],
    second: list[str],
    seed: int = PROTOCOL_SEED,
    repeats: int = REPEAT_SIZE,
    gap: int = REPEAT_GAP,
) -> dict:
    """The queues of the review phase and the repeat set, from sorted inputs
    and one seed, so that the same samples always give the same protocol."""
    rng = random.Random(seed)
    first = sorted({*review, *hard})
    rng.shuffle(first)
    # Only an object shown early enough leaves room for its repeat behind the gap.
    room = sorted(set(review) & set(first[: max(0, len(first) - gap)]))
    repeat = sorted(rng.sample(room, min(repeats, len(room))))
    queue = [{"object": o, "repeat": False} for o in first]
    for o in rng.sample(repeat, len(repeat)):
        at = next(i for i, q in enumerate(queue) if q["object"] == o) + gap + 1
        queue.insert(rng.randint(at, len(queue)), {"object": o, "repeat": True})
    other = sorted(second)
    rng.shuffle(other)
    return {
        "seed": seed,
        "repeatSize": len(repeat),
        "repeatGap": gap,
        "queues": {
            "first": [q["object"] for q in queue],
            "second": other,
        },
        "repeatPositions": [i for i, q in enumerate(queue) if q["repeat"]],
        "repeat": repeat,
    }


def draw_protocol() -> int:
    sources = (REVIEW_SAMPLE, REVIEW_HARD, REVIEW_SECOND)
    if not all(p.exists() for p in sources):
        sys.exit("FEHLER: the review sample and its supplements come first")
    hard = json.loads(REVIEW_HARD.read_text("utf-8"))["objects"]
    second = json.loads(REVIEW_SECOND.read_text("utf-8"))["objects"]
    plan = protocol(
        list(review_objects()), [o for ids in hard.values() for o in ids], second
    )
    print(
        f"OK first queue {len(plan['queues']['first'])} showings with "
        f"{plan['repeatSize']} repeats, second queue {len(plan['queues']['second'])}"
    )
    _freeze(
        REVIEW_PROTOCOL,
        {
            "about": "Order of the review phase: the first reviewer's queue (review "
            "sample and hard stratum mixed, each repeat object shown a second time "
            "at repeatPositions, unmarked to the reviewer) and the second "
            "reviewer's queue (the marked subset), shuffled with the seed; the "
            "repeat set measures intra-rater consistency. Identifiers and hashes "
            "only.",
            **plan,
            "sources": {p.name: sha256_file(p) for p in sources},
        },
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--pools", action="store_true", help="freeze the pool sizes")
    group.add_argument("--hard", action="store_true", help="draw the hard stratum")
    group.add_argument("--second", action="store_true", help="mark the second subset")
    group.add_argument(
        "--protocol", action="store_true", help="freeze the order and repeat set"
    )
    args = parser.parse_args()
    if args.pools:
        return draw_pools()
    if args.hard:
        return draw_hard()
    if args.second:
        return draw_second()
    if args.protocol:
        return draw_protocol()
    return draw_review()


if __name__ == "__main__":
    sys.exit(main())
