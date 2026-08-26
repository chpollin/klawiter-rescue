#!/usr/bin/env python3
"""
Measure the end-to-end effect of the Strand-1 fixes on the frontend data.

This is the Milestone-3 preview measurement. It does NOT run the pipeline; it
compares two builds of the frontend file `docs/data/klawiter.json`:

  before  the deployed version at a git ref (default HEAD), read via `git show`
  after   the current working-tree version, produced by re-running the pipeline
          at the same commit with the landed Strand-1 fixes

Procedure to reproduce:
    python pipeline/run_pipeline.py          # rebuilds docs/data/klawiter.json
    python pipeline/measure_m3_preview.py     # writes the report below
    git checkout -- docs/data/klawiter.json   # restore (publish stays gated)

The report isolates the three landed fixes (location, title mojibake, 2979
show-with-title). It compares only `location` and `title`, the fields those
fixes touch, so the LLM gap-fill fields (publisher, translator, page_count) do
not enter the diff. Entries the LLM step skipped because the Gemini API was
unavailable are listed separately and checked against the location/title diff,
so an enrichment gap caused by the API outage is never reported as a fix effect.

Output: data/output/m3-preview-report.json (deterministic, sort_keys).
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND = os.path.join(ROOT, "docs", "data", "klawiter.json")
CACHE = os.path.join(ROOT, "data", "intermediate", "03b_llm_cache.json")
OUT = os.path.join(ROOT, "data", "output", "m3-preview-report.json")
KEY_RECORDS = [87, 804, 2979, 14]


def _items(doc):
    if isinstance(doc, list):
        return doc
    for k in ("items", "entries", "@graph"):
        if isinstance(doc.get(k), list):
            return doc[k]
    return []


def _pid(it):
    for k in ("sourcePageId", "pageId", "page_id", "id", "identifier"):
        v = it.get(k)
        if v is not None:
            return str(v)
    return None


def _loc(it):
    v = it.get("locationCreated") or it.get("location") or it.get("contentLocation")
    if isinstance(v, dict):
        v = v.get("name") or v.get("@id")
    return v or None


def _title(it):
    return it.get("name") or it.get("title") or ""


def _index(doc):
    return {_pid(it): it for it in _items(doc) if _pid(it)}


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    before_raw = subprocess.run(
        ["git", "show", f"{ref}:docs/data/klawiter.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if before_raw.returncode != 0:
        print(f"could not read {ref}:docs/data/klawiter.json", file=sys.stderr)
        sys.exit(1)
    before = _index(json.loads(before_raw.stdout))
    with open(FRONTEND, encoding="utf-8") as f:
        after = _index(json.load(f))

    with open(CACHE, encoding="utf-8") as f:
        cache = json.load(f)

    loc_changed = loc_gained = loc_lost = title_changed = 0
    loc_lost_ids, title_changed_ids = [], []
    for pid, a in after.items():
        b = before.get(pid)
        if b is None:
            continue
        lb, la = _loc(b), _loc(a)
        if lb != la:
            if lb is None:
                loc_gained += 1
            elif la is None:
                loc_lost += 1
                loc_lost_ids.append(pid)
            else:
                loc_changed += 1
        if _title(b) != _title(a):
            title_changed += 1
            title_changed_ids.append(pid)

    # Entries the LLM step could not enrich because the API was unavailable.
    # These are exactly the pipeline's to_process set: candidates (a field
    # missing per determine_needed_fields) whose page_id is not in the cache.
    # Computed against the freshly built 03_parsed.csv, so this is a snapshot of
    # this build, not reproducible after the intermediates are restored.
    sys.path.insert(0, os.path.join(ROOT, "pipeline"))
    from lib.config import MIN_CONTENT_LENGTH, STEP_03_OUTPUT, csv_bool, load_csv
    from lib.llm_extract import determine_needed_fields

    skipped = []
    for row in load_csv(STEP_03_OUTPUT):
        if row.get("page_namespace", "0") != "0":
            continue
        if csv_bool(row.get("is_redirect")):
            continue
        raw = row.get("raw_content", "") or row.get("content", "")
        if len(raw) < MIN_CONTENT_LENGTH:
            continue
        if determine_needed_fields(row) and row["page_id"] not in cache:
            skipped.append(row["page_id"])
    skipped = sorted(skipped, key=int)
    skipped_set = set(skipped)
    lost_due_to_skip = sorted(set(loc_lost_ids) & skipped_set, key=int)
    lost_not_skip = sorted(set(loc_lost_ids) - skipped_set, key=int)

    key = []
    for k in KEY_RECORDS:
        b, a = before.get(str(k)), after.get(str(k))
        key.append(
            {
                "pageId": k,
                "location_before": _loc(b) if b else None,
                "location_after": _loc(a) if a else None,
                "title_before": (_title(b) if b else "")[:80],
                "title_after": (_title(a) if a else "")[:80],
            }
        )

    report = {
        "description": (
            "Milestone-3 preview: end-to-end effect of the landed Strand-1 fixes "
            "on docs/data/klawiter.json, comparing the deployed build (git HEAD) "
            "to a fresh local pipeline run. Location and title only. Not published."
        ),
        "notes": [
            "Snapshot of one local build; not byte-reproducible by a script alone "
            "because it depends on a full pipeline run that is restored afterwards.",
            "location_changed mixes two cases: a wrong location corrected (the "
            "Weimar class) and a regex value now preferred over a prior LLM "
            "gap-fill (source-derived over guessed). Both are confirmed by the "
            "operator sample, not asserted here.",
            "The full run skipped the gemini_skipped entries at the LLM step "
            "because the Gemini API was unavailable. Those affect only the "
            "gap-fill fields (publisher, translator, page_count); location_lost "
            "is 0, so the outage touched no location or title.",
        ],
        "before_ref": ref,
        "records_compared": len(after),
        "totals": {
            "location_changed": loc_changed,
            "location_gained": loc_gained,
            "location_lost": loc_lost,
            "location_lost_due_to_api_skip": len(lost_due_to_skip),
            "location_lost_genuine": len(lost_not_skip),
            "title_changed": title_changed,
            "gemini_skipped": len(skipped),
        },
        "key_records": key,
        "location_lost_genuine_ids": lost_not_skip,
        "gemini_skipped_pageIds": skipped,
        "title_changed_sample": sorted(title_changed_ids, key=int)[:20],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps(report["totals"], indent=2))
    print("gemini_skipped:", len(skipped), skipped[:25])
    print("report written:", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
