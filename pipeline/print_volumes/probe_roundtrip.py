"""Probe 2, roundtrip: do the units partition the lines, and how robust are they?

For every volume the probe assigns each p01 line exactly one role (furniture,
non-body part, heading, unit start, continuation). Two invariants guard the
code rather than the data: the roles rebuild the page texts with the p01 hash,
and each part's units, read in order without re-sorting, are contiguous and
reproduce the part's lines in their original order. It then compares the four single-signal boundary variants of
_segment.py per part: pairwise agreement (Jaccard over boundary sets), the share
of lines on which all signal-carrying variants agree, the residue of lines
on which they disagree, and that residue per consensus unit, the comparable
figure across files because continuation lines inflate the line share. The residue is what no single layout rule decides and
what review or a further rule has to settle.

Output: data/print/derived/reports/probe_roundtrip.json and a summary.

Usage: python -m uv run python pipeline/print_volumes/probe_roundtrip.py
"""

import hashlib
import json
import sys
from collections import Counter
from itertools import combinations

from _common import REPORT_DIR, VOLUMES, by_page, load_lines, write_report
from _lines import annotate
from _segment import VARIANTS, body_by_part, consensus, units, votes


def _text_hash(lines: list[dict]) -> str:
    pages = [
        hashlib.sha256("\n".join(r["text"] for r in page).encode("utf-8")).hexdigest()
        for _, page in by_page(lines)
    ]
    return hashlib.sha256("".join(pages).encode()).hexdigest()


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


def _part_report(body: list[dict]) -> dict:
    votes(body)
    active = list(body[0]["active"])
    silent = [v for v in VARIANTS if v not in active]
    sets = {
        v: {i for i, ln in enumerate(body) if ln["votes"][v] or ln["heading"]}
        for v in active
    }
    agree = residue = 0
    patterns: Counter = Counter()
    samples = []
    for line in body:
        cast = tuple(line["votes"][v] for v in active)
        if line["heading"] or len({c for c in cast if c is not None}) <= 1:
            agree += 1
            continue
        residue += 1
        key = "".join(
            "-" if c is None else v[0].upper() if c else v[0]
            for v, c in zip(active, cast)
        )
        patterns[key] += 1
        if len(samples) < 12:
            samples.append(
                {
                    "page": line["page"],
                    "votes": key,
                    "consensus": consensus(line),
                    "text": line["text"][:70],
                }
            )
    return {
        "lines": len(body),
        "headings": sum(ln["heading"] for ln in body),
        "units": len(units(body)),
        "variants": active,
        "silent_variants": silent,
        "jaccard": {
            f"{a}~{b}": round(_jaccard(sets[a], sets[b]), 3)
            for a, b in combinations(active, 2)
        },
        "agree_share": round(agree / len(body), 4),
        "residue": residue,
        "residue_patterns": dict(patterns.most_common(8)),
        "residue_sample": samples,
    }


def main() -> int:
    p01 = json.loads((REPORT_DIR / "p01_extract.json").read_text(encoding="utf-8"))
    report: dict = {}
    failures = 0
    for volume in VOLUMES:
        lines = annotate(load_lines(volume), volume)
        parts = body_by_part(lines)
        roles: Counter = Counter()
        for line in lines:
            if line["furniture"]:
                roles["furniture"] += 1
            elif line["kind"] != "body":
                roles[f"non-body:{line['kind']}"] += 1
        sections = {}
        ordered = True
        rebuilt: list[dict] = [
            ln for ln in lines if ln["furniture"] or ln["kind"] != "body"
        ]
        for part, body in parts.items():
            sections[part] = _part_report(body)
            flat = []
            for unit in units(body):
                roles["heading" if unit[0]["heading"] else "unit"] += 1
                roles["continuation"] += len(unit) - 1
                flat.extend(unit)
            ordered &= len(flat) == len(body) and all(
                a is b for a, b in zip(flat, body)
            )
            rebuilt.extend(flat)
        rebuilt.sort(key=lambda ln: (ln["page"], ln["line"]))
        partition = (
            len(rebuilt) == len(lines)
            and _text_hash(rebuilt) == p01[volume]["text_sha256"]
        )
        failures += not (partition and ordered)
        body_lines = sum(s["lines"] for s in sections.values())
        residue = sum(s["residue"] for s in sections.values())
        report[volume] = {
            "partition_invariant": partition,
            "order_invariant": ordered,
            "roles": dict(roles),
            "body_lines": body_lines,
            "residue": residue,
            "residue_share": round(residue / body_lines, 4),
            "residue_per_unit": round(
                residue / max(1, sum(s["units"] for s in sections.values())), 3
            ),
            "sections": sections,
        }
    path = write_report("probe_roundtrip", report)

    print("=" * 72)
    for volume, data in report.items():
        print(
            f"{volume}: partition={data['partition_invariant']} "
            f"order={data['order_invariant']} body={data['body_lines']} "
            f"residue/unit={data['residue_per_unit']} "
            f"residue={data['residue']} ({data['residue_share']:.1%}) roles={data['roles']}"
        )
        for part, s in sorted(data["sections"].items()):
            jac = " ".join(f"{k}={v}" for k, v in s["jaccard"].items())
            jac += f"  silent={','.join(s['silent_variants']) or '-'}"
            print(
                f"  {part:>3} lines={s['lines']:>6} units={s['units']:>5} "
                f"agree={s['agree_share']:.1%} residue={s['residue']:>5}  {jac}"
            )
    print(f"OK report {path}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
