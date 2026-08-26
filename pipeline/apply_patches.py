#!/usr/bin/env python3
"""
Apply approved editor corrections onto the frontend dataset as a final overlay.

This is the write-back and audit step of the EIL editing interface (design:
knowledge/frontend.md, section "EIL Curation Interface"). It runs after
inject_provenance.py. Approved
corrections live as patch files under data/corrections/; the git history of
that folder, together with this overlay, is the audit trail.

For each correction the matching entry's field is set, its provenance is moved
to "editor", and an edit-history record preserving the machine original is
written. The entry's review status is raised to reflect human (approved) or
agent (agent_verified) verification.

The corrections store is authoritative: each run rebuilds an entry's
edit_history from the store rather than appending, so the step is idempotent
and a re-run of the base pipeline never loses or silently overwrites editor
values — they are reproduced on top of freshly built base data.

Patch format (v2), one object per change:
    {"pageId": int, "field": str, "action": "accept"|"correct"|"add",
     "oldValue": str|null, "newValue": str|null, "previousProvenance": str,
     "edited_by": str (role), "edited_at": ISO-8601, "source": "human"|"agent"}

Input:  docs/data/klawiter.json + data/corrections/*.json
Output: docs/data/klawiter.json (in place, only if any entry was touched)
        data/output/corrections-report.json
"""

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (
    OUTPUT_DIR,
    OUTPUT_FRONTEND_JSON,
    OUTPUT_PUBLISHABLE_LINKS,
    PROJECT_ROOT,
    setup_logging,
    write_json,
)

log = setup_logging(__name__)

CORRECTIONS_DIR = os.path.join(PROJECT_ROOT, "data", "corrections")
REPORT_PATH = os.path.join(OUTPUT_DIR, "corrections-report.json")

VALID_ACTIONS = {"accept", "correct", "add"}
VALID_SOURCES = {"human", "agent"}
# Mirrors Edit.TRACKED_FIELDS in docs/js/edit.js. A typo'd field name must not
# silently create a new key on the entry; extend this when the editor grows
# (title editing is planned as EIL Increment 4).
EDITABLE_FIELDS = {"publisher", "location", "translator", "pageCount"}
REQUIRED_KEYS = ("pageId", "field", "action", "edited_by", "edited_at", "source")


def validate_patch(patch):
    """Return a list of problems with a patch; empty list means valid."""
    problems = []
    for key in REQUIRED_KEYS:
        if key not in patch:
            problems.append(f"missing key '{key}'")
    if patch.get("action") not in VALID_ACTIONS:
        problems.append(
            f"action '{patch.get('action')}' not in {sorted(VALID_ACTIONS)}"
        )
    if patch.get("source") not in VALID_SOURCES:
        problems.append(
            f"source '{patch.get('source')}' not in {sorted(VALID_SOURCES)}"
        )
    if "field" in patch and patch["field"] not in EDITABLE_FIELDS:
        problems.append(f"field '{patch['field']}' not in {sorted(EDITABLE_FIELDS)}")
    if patch.get("action") == "add" and (patch.get("oldValue") or "").strip():
        problems.append("action 'add' but oldValue is non-empty")
    if patch.get("action") == "correct" and patch.get("newValue") in (
        None,
        "",
        patch.get("oldValue"),
    ):
        problems.append("action 'correct' but newValue is empty or equals oldValue")
    return problems


def _history_record(patch):
    return {
        "field": patch["field"],
        "action": patch["action"],
        "originalValue": patch.get("oldValue"),
        "newValue": patch.get("newValue"),
        "previousProvenance": patch.get("previousProvenance"),
        "edited_by": patch["edited_by"],
        "edited_at": patch["edited_at"],
        "source": patch["source"],
    }


def apply_patches(entries, patches, location_links=None):
    """Apply patches to entries in place. Returns a report dict.

    entries: list of frontend entry dicts (mutated).
    patches: list of v2 patch dicts.

    Idempotent: an entry's edit_history is rebuilt from the patches that target
    it, not appended to, so repeated runs converge to the same result.
    """
    index = {e.get("sourcePageId"): e for e in entries}
    location_links = location_links or {}

    valid, invalid = [], []
    for p in patches:
        problems = validate_patch(p)
        (invalid if problems else valid).append((p, problems))

    by_page = defaultdict(list)
    not_found = []
    for p, _ in valid:
        if p["pageId"] in index:
            by_page[p["pageId"]].append(p)
        else:
            not_found.append({"pageId": p["pageId"], "field": p["field"]})

    by_action = {"accept": 0, "correct": 0, "add": 0}
    touched = 0
    mismatches = []
    for pid, plist in by_page.items():
        plist.sort(key=lambda p: p["edited_at"])  # chronological; last wins
        entry = index[pid]
        provenance = entry.setdefault("_provenance", {})
        history = []
        sources = []
        for p in plist:
            field, action = p["field"], p["action"]
            # The editor saw oldValue when deciding; if the freshly built base
            # value differs, the patch overwrites something the editor never
            # reviewed. Applied anyway (the store is authoritative) but
            # surfaced in the report. Matching newValue means the patch is
            # already applied (idempotent re-run), not a drift.
            current = _norm(entry.get(field))
            if current not in (_norm(p.get("oldValue")), _norm(p.get("newValue"))):
                mismatches.append(
                    {
                        "pageId": pid,
                        "field": field,
                        "patchOldValue": p.get("oldValue"),
                        "currentValue": entry.get(field),
                    }
                )
            if action in ("correct", "add"):
                entry[field] = p.get("newValue")
                if field == "location":
                    reviewed = location_links.get(p.get("newValue"), {})
                    if reviewed.get("uri"):
                        entry["locationSameAs"] = reviewed["uri"]
                    else:
                        entry.pop("locationSameAs", None)
            # 'accept' confirms the existing value without changing it
            provenance[field] = "editor"
            history.append(_history_record(p))
            sources.append(p["source"])
            by_action[action] += 1
        entry["edit_history"] = history
        last = plist[-1]
        status = "approved" if "human" in sources else "agent_verified"
        entry["review"] = {
            "status": status,
            "reviewed_by": last["edited_by"],
            "reviewed_at": last["edited_at"],
        }
        touched += 1

    return {
        "entries_touched": touched,
        "patches_applied": sum(by_action.values()),
        "by_action": by_action,
        "not_found": not_found,
        "old_value_mismatch": mismatches,
        "invalid": [{"patch": p, "problems": probs} for p, probs in invalid],
    }


def _norm(value):
    """Compare field values across None/''/int representations."""
    return "" if value is None else str(value)


def load_corrections(corrections_dir=CORRECTIONS_DIR):
    """Load and flatten all v2 patch files from the corrections directory."""
    patches = []
    if not os.path.isdir(corrections_dir):
        return patches
    for name in sorted(os.listdir(corrections_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(corrections_dir, name), encoding="utf-8") as f:
            doc = json.load(f)
        patches.extend(doc.get("patches", []))
    return patches


def main():
    patches = load_corrections()
    log.info(f"Loaded {len(patches)} correction(s) from {CORRECTIONS_DIR}")

    with open(OUTPUT_FRONTEND_JSON, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("entries", [])

    if os.path.exists(OUTPUT_PUBLISHABLE_LINKS):
        with open(OUTPUT_PUBLISHABLE_LINKS, encoding="utf-8") as f:
            location_links = json.load(f).get("locations", {})
    else:
        location_links = {}
    report = apply_patches(entries, patches, location_links)

    log.info(
        f"Entries touched: {report['entries_touched']}  "
        f"applied: {report['patches_applied']}  {report['by_action']}"
    )
    if report["not_found"]:
        log.warning(f"  patches for unknown pageId: {len(report['not_found'])}")
    if report["invalid"]:
        log.warning(f"  invalid patches skipped: {len(report['invalid'])}")
    if report["old_value_mismatch"]:
        log.warning(
            f"  patches whose oldValue no longer matches the base data: "
            f"{len(report['old_value_mismatch'])} (see report)"
        )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    write_json(REPORT_PATH, report, indent=2)

    # Only rewrite the dataset when something actually changed, so an empty
    # corrections store is a true no-op and leaves the file byte-identical.
    if report["entries_touched"]:
        write_json(OUTPUT_FRONTEND_JSON, data, separators=(",", ":"))
        log.info(f"Updated {OUTPUT_FRONTEND_JSON}")
    else:
        log.info("No corrections to apply; dataset unchanged.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
