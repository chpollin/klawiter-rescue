#!/usr/bin/env python3
"""
Measure the effect of the publication-line location fix in lib/patterns.py.

The fix constrains extract_location to read the bold '''[YEAR]: Publisher,
Location''' header first, so a city inside a chapter title (the "Weimar" class,
error class 1 in knowledge/testing.md) is no longer mistaken for the place of
publication.

This script isolates the regex change from everything else: it re-runs the
current extract_location over the same input the pipeline used (the raw_content
column of 03_parsed.csv, which is the encoding-fixed wiki text) and compares the
result against the location value that the previous extraction wrote into the
same file. Encoding is held constant on both sides, so the diff reflects the
location logic alone, not the mojibake repair.

It is read-only over the data and writes one report,
data/output/location-fix-report.json, so the numbers reported to the
Forschungsleitstelle are reproducible and git-citable rather than transient.

Deterministic: same inputs produce a byte-identical report.
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import OUTPUT_DIR, STEP_03_OUTPUT
from lib.patterns import extract_location

REPORT_PATH = os.path.join(OUTPUT_DIR, "location-fix-report.json")


def load_ns0_entries():
    """Yield (page_id, old_location, raw_content) for real bibliographic
    records: namespace 0, not a redirect."""
    csv.field_size_limit(10**8)
    with open(STEP_03_OUTPUT, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("page_namespace") != "0":
                continue
            if str(row.get("is_redirect")).lower() == "true":
                continue
            yield (
                int(row["page_id"]),
                (row.get("location") or "").strip(),
                row.get("raw_content") or "",
            )


def measure():
    unchanged = changed = gained = lost = 0
    changed_list = []
    gained_list = []
    lost_list = []
    weimar_total = 0
    weimar_corrected = []
    weimar_residual = []

    for pid, old, content in load_ns0_entries():
        new = (extract_location(content) or "").strip()
        if old == new:
            unchanged += 1
        elif old and new:
            changed += 1
            changed_list.append({"pageId": pid, "old": old, "new": new})
        elif not old and new:
            gained += 1
            gained_list.append({"pageId": pid, "new": new})
        else:  # old and not new
            lost += 1
            lost_list.append({"pageId": pid, "old": old})

        if old == "Weimar":
            weimar_total += 1
            if new != "Weimar":
                weimar_corrected.append({"pageId": pid, "new": new})
            else:
                weimar_residual.append(pid)

    total = unchanged + changed + gained + lost
    report = {
        "description": (
            "Effect of the publication-line location fix, measured by re-running "
            "extract_location over 03_parsed.csv raw_content and comparing to the "
            "previously extracted location column. Encoding held constant."
        ),
        "source": os.path.relpath(STEP_03_OUTPUT).replace(os.sep, "/"),
        "totals": {
            "ns0_records": total,
            "unchanged": unchanged,
            "changed": changed,
            "gained": gained,
            "lost": lost,
        },
        "weimar": {
            "old_value_weimar": weimar_total,
            "corrected": len(weimar_corrected),
            "residual": len(weimar_residual),
            "residual_pageIds": sorted(weimar_residual),
            "corrected_detail": sorted(weimar_corrected, key=lambda r: r["pageId"]),
        },
        "changed": sorted(changed_list, key=lambda r: r["pageId"]),
        "gained": sorted(gained_list, key=lambda r: r["pageId"]),
        "lost": sorted(lost_list, key=lambda r: r["pageId"]),
    }
    return report


def main():
    report = measure()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    t = report["totals"]
    w = report["weimar"]
    print(f"ns0 records: {t['ns0_records']}")
    print(
        f"unchanged {t['unchanged']}  changed {t['changed']}  "
        f"gained {t['gained']}  lost {t['lost']}"
    )
    print(
        f"weimar old={w['old_value_weimar']}  corrected={w['corrected']}  "
        f"residual={w['residual']} {w['residual_pageIds']}"
    )
    print(f"report written: {os.path.relpath(REPORT_PATH).replace(os.sep, '/')}")


if __name__ == "__main__":
    main()
