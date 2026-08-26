#!/usr/bin/env python3
"""
Build the per-entry triage artifact for the EIL editing interface.

Increment 2 of the editing layer (design: knowledge/frontend.md, section "EIL
Curation Interface"; framing: knowledge/production-readiness.md). Bundles the
signals that already exist —
verify.py field flags and the census anomaly — into a compact per-entry hint
file the frontend shows the editor in edit mode. Provenance classes (regex /
llm / missing) are NOT duplicated here; the frontend already carries them per
entry and folds them into the same hint list client-side.

This is an attention aid over the data situation, not a quality or workflow
score: it records which data signals point at an entry, no rate, no ranking
number is derived or published (Korrektur-Protokoll principle: protocol, not
instrumentation).

Input:  data/output/verification-report.json (committed verify.py artifact)
        data/output/census-report.json       (committed census.py artifact)
Output: docs/data/triage.json
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import OUTPUT_DIR, PROJECT_ROOT, setup_logging, write_json

log = setup_logging(__name__)

VERIFICATION_REPORT = os.path.join(OUTPUT_DIR, "verification-report.json")
CENSUS_REPORT = os.path.join(OUTPUT_DIR, "census-report.json")
TRIAGE_PATH = os.path.join(PROJECT_ROOT, "docs", "data", "triage.json")

# verify.py speaks pipeline field names; the frontend speaks camelCase.
FIELD_NAME_MAP = {"page_count": "pageCount"}

# Fields whose verify flags reach the editor. year is excluded: it is neither
# provenance-tracked nor editable, and its false-negative list (allYears gaps)
# mostly restates the multi-edition limitation.
FLAGGED_FIELDS = ("title", "publisher", "location", "translator", "page_count")


def _frontend_field(name):
    return FIELD_NAME_MAP.get(name, name)


def build_triage(detailed_results, census_report):
    """Reduce verify.py detailed results + census anomalies to per-entry flags.

    Returns {pageId(str): flags} with only entries that carry at least one
    flag. Flag shapes (pinned by tests/test_triage.py):
      notInSource: [field, ...]        extracted value not found in raw text
      detectable:  {field: raw_value}  value detectable in raw text, absent in output
      census:      str                 census anomaly, human-readable reason
    """
    triage = {}

    def flags_for(pid):
        return triage.setdefault(str(pid), {})

    for result in detailed_results:
        pid = result.get("page_id")
        if pid is None:
            continue
        fields = result.get("fields", {})

        not_in_source = []
        detectable = {}
        for name in FLAGGED_FIELDS:
            f = fields.get(name)
            if isinstance(f, dict) and f.get("status") == "false_positive":
                not_in_source.append(_frontend_field(name))
            fn = fields.get(f"{name}_false_negative")
            if isinstance(fn, dict) and fn.get("detected_in_raw"):
                detectable[_frontend_field(name)] = fn["detected_in_raw"]

        if not_in_source:
            flags_for(pid)["notInSource"] = not_in_source
        if detectable:
            flags_for(pid)["detectable"] = detectable

    empty = (
        census_report.get("source", {})
        .get("empty_content_pages", {})
        .get("bibliographic_ns0", [])
    )
    for page in empty:
        flags_for(page["page_id"])["census"] = (
            "Quellseitig geleerte Seite (Census-Anomalie)"
        )

    return triage


def main():
    with open(VERIFICATION_REPORT, encoding="utf-8") as f:
        verification = json.load(f)
    with open(CENSUS_REPORT, encoding="utf-8") as f:
        census = json.load(f)

    triage = build_triage(verification.get("detailed_results", []), census)

    doc = {
        "_meta": {
            "sources": ["verification-report.json", "census-report.json"],
            "note": (
                "Per-entry attention hints from existing data signals; "
                "not a quality or workflow metric."
            ),
        },
        "entries": triage,
    }

    os.makedirs(os.path.dirname(TRIAGE_PATH), exist_ok=True)
    write_json(TRIAGE_PATH, doc, indent=1)
    log.info(f"Wrote {len(triage)} flagged entries to {TRIAGE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
