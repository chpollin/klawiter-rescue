"""p11: LLM offsets for print objects the rules cannot read, as a frozen trial and a cache.

The rules of p03 leave objects without any recognised citation form (no type).
This stage proposes, for such objects only, offsets into the object's text
(_llm.py: prompt, verification, merge). Three modes:

- plan (default): draw the trial once and freeze it, at most MAX_TRIAL objects
  without a type, stratified by volume, from the development sample first and
  then from the other records, never from held-out records (_heldout.py).
  Prints the number of objects and an estimate of the input tokens. No call.
- live: sends the frozen trial to the project's default model and writes the
  responses to the versioned cache after every call. It refuses unless the
  variable KLAWITER_PRINT_LLM_CONSENT is set to "operator-approved", an API
  key is present, and the trial holds at most MAX_TRIAL objects. The variable
  guards against an accidental run; it stands for the operator's consent only
  where the operator gave it for this run. Scaling beyond the trial needs a
  new consent.
- report: verifies every cached response against its object and reports
  accepted and rejected offsets per field; p03 merges accepted ones into empty
  fields on every run, so the normal run makes no model call.

Output: data/print/derived/samples/llm-trial.json (local, identifiers only),
pipeline/print_volumes/llm_cache.json (versioned, identifiers, keyed hashes
and offsets), data/print/derived/reports/p11_llm_spans.json.

Usage: python -m uv run python pipeline/print_volumes/p11_llm_spans.py [--live|--report]
"""

import argparse
import json
import os
import random
import sys
import time
from collections import Counter

from _common import DERIVED_DIR, PROJECT_ROOT, VOLUMES, write_report
from _heldout import is_held_out
from _llm import CACHE, PROMPT, PROMPT_ID, cache_key, load_cache, sha, verify

sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
from lib.llm_extract import MODEL_ID  # noqa: E402  the project's default model

RECORDS = DERIVED_DIR / "records"
DEV = DERIVED_DIR / "samples" / "dev-sample.json"
TRIAL = DERIVED_DIR / "samples" / "llm-trial.json"
MAX_TRIAL = 50
SEED = 20261026
CONSENT = "operator-approved"


def _untyped() -> dict[str, list[dict]]:
    found: dict[str, list[dict]] = {v: [] for v in VOLUMES}
    for volume in VOLUMES:
        with (RECORDS / f"entries-{volume}.jsonl").open(encoding="utf-8") as source:
            for record in map(json.loads, source):
                if record["kind"] != "entry" or is_held_out(record):
                    continue
                for obj in record["objects"]:
                    if not obj.get("types"):
                        found[volume].append(
                            {"id": obj["id"], "chars": len(obj["text"])}
                        )
    return found


def plan() -> int:
    if TRIAL.exists():
        trial = json.loads(TRIAL.read_text(encoding="utf-8"))
        print(f"OK trial frozen: {len(trial['objects'])} objects -> {TRIAL}")
    else:
        dev = json.loads(DEV.read_text(encoding="utf-8"))["units"]
        dev_ids = {i for parts in dev.values() for ids in parts.values() for i in ids}
        rng = random.Random(SEED)
        pools = _untyped()
        share = MAX_TRIAL // len(VOLUMES)
        chosen = []
        for volume in VOLUMES:
            pool = sorted(pools[volume], key=lambda o: o["id"])
            first = [o for o in pool if o["id"].split("#")[0] in dev_ids]
            rest = [o for o in pool if o["id"].split("#")[0] not in dev_ids]
            take = rng.sample(first, min(share, len(first)))
            take += rng.sample(rest, min(share - len(take), len(rest)))
            chosen.extend(take)
        trial = {"seed": SEED, "prompt_id": PROMPT_ID, "objects": chosen[:MAX_TRIAL]}
        TRIAL.parent.mkdir(parents=True, exist_ok=True)
        TRIAL.write_text(json.dumps(trial, indent=1), encoding="utf-8")
        print(f"OK trial drawn and frozen: {len(trial['objects'])} objects -> {TRIAL}")
    chars = sum(o["chars"] for o in trial["objects"]) + len(PROMPT) * len(
        trial["objects"]
    )
    print(
        f"OK model {MODEL_ID}; about {chars // 4} input tokens (4 characters per token)"
    )
    print(
        f"OK by volume: {dict(Counter(o['id'].split('/')[0] for o in trial['objects']))}"
    )
    return 0


def _objects(ids: set[str]) -> dict[str, dict]:
    found = {}
    for volume in VOLUMES:
        with (RECORDS / f"entries-{volume}.jsonl").open(encoding="utf-8") as source:
            for record in map(json.loads, source):
                for obj in record["objects"]:
                    if obj["id"] in ids:
                        found[obj["id"]] = obj
    return found


def live() -> int:
    if os.environ.get("KLAWITER_PRINT_LLM_CONSENT") != CONSENT:
        sys.exit("FEHLER: live mode needs the operator's consent for this run")
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("FEHLER: GEMINI_API_KEY missing")
    if not TRIAL.exists():
        sys.exit("FEHLER: no frozen trial; run the plan first")
    trial = json.loads(TRIAL.read_text(encoding="utf-8"))
    if len(trial["objects"]) > MAX_TRIAL:
        sys.exit("FEHLER: the trial exceeds the consented size")
    from google import genai
    from pydantic import BaseModel

    class PersonSpan(BaseModel):
        name: list[int] | None = None
        role: list[int] | None = None

    class Spans(BaseModel):
        title: list[int] | None = None
        subtitle: list[int] | None = None
        place: list[int] | None = None
        publisher: list[int] | None = None
        year: list[int] | None = None
        periodical: list[int] | None = None
        date: list[int] | None = None
        pages: list[int] | None = None
        persons: list[PersonSpan] = []

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    cache = load_cache()
    objects = _objects({o["id"] for o in trial["objects"]})
    for n, (oid, obj) in enumerate(sorted(objects.items()), start=1):
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[
                {
                    "role": "user",
                    "parts": [{"text": f"{PROMPT}\nOBJECT:\n{obj['text']}"}],
                }
            ],
            config={"response_mime_type": "application/json", "response_schema": Spans},
        )
        parsed = Spans.model_validate_json(response.text).model_dump(exclude_none=True)
        # No plain hash of the object text enters the versioned cache.
        cache["entries"][oid] = {
            "key": cache_key(MODEL_ID, obj["text"], create=True),
            "model": MODEL_ID,
            "prompt_sha256": sha(PROMPT),
            "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "response": parsed,
        }
        # Written after every call, so that an interruption keeps what was paid.
        CACHE.write_text(
            json.dumps(cache, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"OK {n}/{len(objects)} {oid}")
        time.sleep(0.5)
    print(f"OK cache -> {CACHE}")
    return report()


def report() -> int:
    cache = load_cache()
    objects = _objects(set(cache.get("entries", {})))
    accepted: Counter = Counter()
    rejected: Counter = Counter()
    stale = 0
    for oid, entry in cache.get("entries", {}).items():
        obj = objects.get(oid)
        if not obj or entry["key"] != cache_key(entry["model"], obj["text"]):
            stale += 1
            continue
        proposed, problems = verify(obj, entry["response"])
        accepted.update(proposed)
        rejected.update(p.split(":")[0] for p in problems)
    result = {
        "about": "Offsets proposed by the model for objects without a type, checked by rule; "
        "accepted values are proposals, not confirmations.",
        "model": MODEL_ID,
        "prompt_id": PROMPT_ID,
        "cached_objects": len(cache.get("entries", {})),
        "stale": stale,
        "accepted_by_field": dict(accepted),
        "rejected_by_field": dict(rejected),
    }
    write_report("p11_llm_spans", result)
    print(
        f"OK {result['cached_objects']} cached, accepted {dict(accepted)}, rejected {dict(rejected)}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.live:
        return live()
    if args.report:
        return report()
    return plan()


if __name__ == "__main__":
    sys.exit(main())
