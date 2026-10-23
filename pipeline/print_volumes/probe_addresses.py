"""Probe 1, address census: which addresses exist and which references resolve.

Reads the p01 lines of all three volumes and answers three questions.

1. Entry starts. Per volume and section, the numbers printed at the entry
   margin form a sequence. The probe reports gaps, duplicates and backward
   steps, and compares the highest number with the compiler's own table of
   contents (toc_max in sections.json).
2. References. Every address token in body text (F 47, HA1 34, G 851-854,
   A 70, 77, 85, L 1596*, FA1 24a) is parsed into its target addresses, with
   lists and ranges expanded, and resolved against the entry starts of the
   volume its suffix names. Unresolved targets are listed with context; they
   point to a segmentation gap, a print error or a parsing gap.
3. Notation. The frequency of each address form and of the notation that
   introduces it (See, Rep:, Contents:, [Cont., [Correction to, bare bracket).

Output: data/print/derived/reports/probe_addresses.json and a summary on
stdout. The report carries text snippets and therefore stays local.

Usage: python -m uv run python pipeline/print_volumes/probe_addresses.py
"""

import re
import sys
from collections import Counter, defaultdict

from _common import SECTIONS, VOLUMES, load_lines, write_report
from _lines import START_NUMBER, annotate, is_stub, numbered_start

SUFFIX_TO_VOLUME = {"": "I", "A1": "A1", "A2": "A2"}
# Address head, then optional continuation items sharing its section letter.
ITEM = r"\d{1,4}[a-z]?(?:\s?-\s?\d{1,4}[a-z]?)?\*?"
REFERENCE = re.compile(
    rf"(?<![A-Za-z0-9])([A-R])(A[12])?\s?({ITEM}(?:\s?(?:,|&)\s?{ITEM}(?![A-Za-z]))*)"
)
INTRO = (
    ("correction", re.compile(r"Correction to\s*$")),
    ("continuation", re.compile(r"Cont\.(?: of)?\s*$")),
    ("reprint", re.compile(r"(?:Rep|REP):\s*$")),
    ("contents", re.compile(r"Contents:\s*$")),
    ("see", re.compile(r"(?:See|see)(?: also)?:?\s*$")),
    ("index", re.compile(r"Index\s*$")),
    ("bracket", re.compile(r"\[\s*$")),
    ("list", re.compile(r"[/,&=]\s*$")),
)
MAX_RANGE = 60


def _items(group: str) -> tuple[list[tuple[int, str]], Counter]:
    targets: list[tuple[int, str]] = []
    forms: Counter = Counter()
    parts = re.split(r"\s?(?:,|&)\s?", group)
    if len(parts) > 1:
        forms["list"] += 1
    for part in parts:
        if part.endswith("*"):
            forms["starred"] += 1
            part = part[:-1]
        if "-" in part:
            forms["range"] += 1
            low, high = (p.strip() for p in part.split("-", 1))
            lo, hi = (
                int(re.match(r"\d+", low).group()),
                int(re.match(r"\d+", high).group()),
            )
            if 0 < hi - lo <= MAX_RANGE:
                targets.extend((n, "") for n in range(lo, hi + 1))
            else:
                forms["range_unexpanded"] += 1
                targets.append((lo, ""))
            continue
        match = re.match(r"(\d+)([a-z]?)", part)
        if match.group(2):
            forms["letter_suffix"] += 1
        targets.append((int(match.group(1)), match.group(2)))
    return targets, forms


def _intro(before: str) -> str:
    for name, pattern in INTRO:
        if pattern.search(before):
            return name
    return "inline"


def _sequence(numbers: list[int]) -> dict:
    counts = Counter(numbers)
    top = max(numbers)
    return {
        "count": len(numbers),
        "max": top,
        "gaps": sorted(set(range(1, top + 1)) - set(numbers)),
        "duplicates": sorted(n for n, c in counts.items() if c > 1),
        "backward_steps": [[a, b] for a, b in zip(numbers, numbers[1:]) if b < a],
    }


def main() -> int:
    starts: dict[str, dict[str, set]] = {}
    report: dict = {"volumes": {}}
    all_lines = {}
    for volume in VOLUMES:
        lines = annotate(load_lines(volume), volume)
        all_lines[volume] = lines
        sequence: dict[str, list[int]] = defaultdict(list)
        keys: dict[str, set] = defaultdict(set)
        stubs: Counter = Counter()
        for line in lines:
            start = numbered_start(line)
            if start:
                sequence[line["part"]].append(start[0])
                keys[line["part"]].add(start)
                keys[line["part"]].add((start[0], ""))
            elif is_stub(line):
                stubs[line["part"]] += 1
        starts[volume] = keys
        toc = SECTIONS["volumes"][volume].get("toc_max", {})
        sections = {}
        for part, numbers in sequence.items():
            info = _sequence(numbers)
            info["toc_max"] = toc.get(part)
            info["stubs"] = stubs[part]
            for key in ("gaps", "duplicates", "backward_steps"):
                info[f"n_{key}"] = len(info[key])
                info[key] = info[key][:40]
            sections[part] = info
        report["volumes"][volume] = {"sections": sections}

    forms: Counter = Counter()
    intros: Counter = Counter()
    resolution: dict[str, Counter] = defaultdict(Counter)
    unresolved: list[dict] = []
    for volume, lines in all_lines.items():
        for line in lines:
            if line["furniture"] or line["kind"] != "body":
                continue
            text = line["text"]
            skip = START_NUMBER.match(text).end() if numbered_start(line) else 0
            for match in REFERENCE.finditer(text, skip):
                letter, suffix, group = match.groups()
                suffix = suffix or ""
                target_volume = SUFFIX_TO_VOLUME[suffix]
                targets, item_forms = _items(group)
                forms.update(item_forms)
                forms[f"suffix_{suffix or 'none'}"] += 1
                intros[_intro(text[: match.start()])] += 1
                for number, letter_suffix in targets:
                    key = f"{volume}->{target_volume}"
                    if (number, letter_suffix) in starts[target_volume].get(letter, ()):
                        resolution[key]["resolved"] += 1
                    elif not starts[target_volume].get(letter):
                        resolution[key]["no_numbered_section"] += 1
                    else:
                        resolution[key]["unresolved"] += 1
                        if len(unresolved) < 400:
                            unresolved.append(
                                {
                                    "in": f"{volume} p{line['page']}",
                                    "target": f"{letter}{suffix} {number}{letter_suffix}",
                                    "context": text[
                                        max(0, match.start() - 30) : match.end() + 10
                                    ],
                                }
                            )
    report["references"] = {
        "forms": dict(forms),
        "introduced_by": dict(intros),
        "resolution": {k: dict(v) for k, v in resolution.items()},
        "unresolved_sample": unresolved,
    }
    path = write_report("probe_addresses", report)

    print("=" * 72)
    for volume, data in report["volumes"].items():
        total = sum(s["count"] for s in data["sections"].values())
        print(f"{volume}: {total} numbered entry starts")
        for part, s in sorted(data["sections"].items()):
            flag = "" if s["toc_max"] in (None, s["max"]) else f"  TOC {s['toc_max']}"
            print(
                f"  {part:>3} n={s['count']:>5} max={s['max']:>5} "
                f"gaps={s['n_gaps']:>3} dup={s['n_duplicates']:>2} "
                f"back={s['n_backward_steps']:>2} stubs={s['stubs']:>3}{flag}"
            )
    print("-" * 72)
    for key, counts in sorted(report["references"]["resolution"].items()):
        total = sum(counts.values())
        ok = counts.get("resolved", 0)
        print(f"{key}: {total} targets, {ok} resolved ({ok / total:.1%}), {counts}")
    print(f"forms: {dict(forms)}")
    print(f"introduced by: {dict(intros)}")
    print(f"OK report {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
