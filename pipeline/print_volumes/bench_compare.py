"""Score the segmentation against blind gold annotations of the benchmark pages.

Reads data/print/derived/bench/sample.json and one folder per annotator
(bench/gold-<name>/<volume>-p<page>.json, written without access to the rules)
and compares three things per page:

- boundaries: which body lines open a unit. A gold unit is located by its
  first words; precision, recall and F1 count located unit starts.
- publications: the number of objects a unit describes, as gold count versus
  the citation count of probe_signatures.py, compared as classes 0, 1 and 2+.
- references: the addresses a unit cites, as sets per unit.

Every pair of annotators is scored the same way, so the agreement between
annotators bounds what a method can be expected to reach. Gold units that
cannot be located are listed rather than dropped.

Output: data/print/derived/reports/bench_compare.json and a summary.

Usage: python -m uv run python pipeline/print_volumes/bench_compare.py [--bench v2]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from itertools import combinations

from _common import DERIVED_DIR, load_lines, write_report
from _lines import annotate
from _segment import body_by_part, units, votes
from probe_addresses import REFERENCE, SUFFIX_TO_VOLUME, _items
from probe_signatures import _classify, _profile

BENCH = DERIVED_DIR / "bench"
METHOD = "method"


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-z]", "", text.lower())


def _locate(first_words: str, page_lines: list[dict]) -> int | None:
    key = _norm(first_words)[:24]
    if len(key) < 4:
        return None
    for index, line in enumerate(page_lines):
        text = _norm(line["text"])
        if text.startswith(key) or (len(text) >= 8 and key.startswith(text[:24])):
            return index
    for index, line in enumerate(page_lines):
        if key[:12] and key[:12] in _norm(line["text"]):
            return index
    return None


def _addresses(text: str) -> set[str]:
    found = set()
    for match in REFERENCE.finditer(text):
        letter, suffix, group = match.groups()
        suffix = suffix or ""
        if suffix not in SUFFIX_TO_VOLUME:
            continue
        targets, _ = _items(group)
        found.update(f"{letter}{suffix} {n}{s}" for n, s in targets)
    return found


def _pub_class(count: int) -> str:
    return "0" if count <= 0 else "1" if count == 1 else "2+"


def _method_pages(volume: str, pages: set[int]) -> dict[int, dict]:
    """Per sampled page: body lines, method boundaries and unit facts."""
    lines = annotate(load_lines(volume), volume)
    result: dict[int, dict] = {}
    for body in body_by_part(lines).values():
        votes(body)
        for unit in units(body):
            text = " ".join(ln["text"].strip() for ln in unit)
            profile = _profile(text)
            kind = _classify(text, profile)
            citations = sum(
                profile[k] for k in ("imprints", "periodicals", "hosts", "extent_years")
            )
            publications = 0 if kind == "reference" or unit[0]["heading"] else citations
            publications = max(publications, profile["subitems"])
            for line in unit:
                if line["page"] not in pages:
                    continue
                page = result.setdefault(line["page"], {"lines": [], "units": {}})
                page["lines"].append(line)
                if line is unit[0] or line["page"] != unit[0]["page"]:
                    page["units"].setdefault(
                        id(unit),
                        {
                            "line": line,
                            "starts": line is unit[0],
                            "publications": publications,
                            "references": _addresses(text),
                        },
                    )
    for page in result.values():
        page["lines"].sort(key=lambda ln: ln["line"])
        order = {id(ln): i for i, ln in enumerate(page["lines"])}
        page["starts"] = {
            order[id(u["line"])]: u for u in page["units"].values() if u["starts"]
        }
    return result


def _gold_starts(gold: dict, page_lines: list[dict]) -> tuple[dict, list]:
    starts, missing = {}, []
    for unit in gold["units"]:
        if not unit.get("starts_on_this_page", True):
            continue
        index = _locate(unit["first_words"], page_lines)
        if index is None:
            missing.append(unit["first_words"])
        else:
            starts[index] = {
                "publications": int(unit.get("publications") or 0),
                "references": {r.strip() for r in unit.get("references") or []},
            }
    return starts, missing


def _score(a: dict, b: dict) -> dict:
    """Boundary P/R/F1 of b against reference a, plus agreement on shared starts."""
    shared = set(a) & set(b)
    precision = len(shared) / len(b) if b else 1.0
    recall = len(shared) / len(a) if a else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    pub = sum(
        _pub_class(a[i]["publications"]) == _pub_class(b[i]["publications"])
        for i in shared
    )
    ref_tp = sum(len(a[i]["references"] & b[i]["references"]) for i in shared)
    ref_a = sum(len(a[i]["references"]) for i in shared)
    ref_b = sum(len(b[i]["references"]) for i in shared)
    return {
        "reference_starts": len(a),
        "compared_starts": len(b),
        "shared": len(shared),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "publication_class_agreement": round(pub / len(shared), 3) if shared else None,
        "reference_recall": round(ref_tp / ref_a, 3) if ref_a else None,
        "reference_precision": round(ref_tp / ref_b, 3) if ref_b else None,
    }


def _pool(rows: list[dict]) -> dict:
    keys = ("reference_starts", "compared_starts", "shared")
    total = {k: sum(r[k] for r in rows) for k in keys}
    p = total["shared"] / total["compared_starts"] if total["compared_starts"] else 0
    r = total["shared"] / total["reference_starts"] if total["reference_starts"] else 0
    total["precision"] = round(p, 3)
    total["recall"] = round(r, 3)
    total["f1"] = round(2 * p * r / (p + r), 3) if p + r else 0.0
    for key in (
        "publication_class_agreement",
        "reference_recall",
        "reference_precision",
    ):
        weighted = [(row[key], row["shared"]) for row in rows if row[key] is not None]
        n = sum(w for _, w in weighted)
        total[key] = round(sum(v * w for v, w in weighted) / n, 3) if n else None
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--bench", default="", help="sub-folder of bench/, e.g. v2; empty for v1"
    )
    args = parser.parse_args()
    bench = BENCH / args.bench if args.bench else BENCH
    sample = json.loads((bench / "sample.json").read_text(encoding="utf-8"))["pages"]
    annotators = sorted(p.name[5:] for p in bench.glob("gold-*") if p.is_dir())
    if not annotators:
        sys.exit("FEHLER: no gold-* folders under data/print/derived/bench")
    rows: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    missing: list[dict] = []
    absent: list[str] = []
    for volume, pages in sample.items():
        pages = [int(p) for p in pages]
        method = _method_pages(volume, set(pages))
        for page in pages:
            page_lines = method.get(page, {}).get("lines", [])
            sources = {METHOD: method.get(page, {}).get("starts", {})}
            for name in annotators:
                path = bench / f"gold-{name}" / f"{volume}-p{page}.json"
                if not path.exists():
                    absent.append(f"{name}:{volume}-p{page}")
                    continue
                gold = json.loads(path.read_text(encoding="utf-8"))
                starts, lost = _gold_starts(gold, page_lines)
                sources[name] = starts
                missing.extend(
                    {"annotator": name, "page": f"{volume}-p{page}", "first_words": w}
                    for w in lost
                )
            for ref, other in combinations(sorted(sources), 2):
                if METHOD in (ref, other):
                    gold_name = other if ref == METHOD else ref
                    key = f"{METHOD} vs {gold_name}"
                    row = _score(sources[gold_name], sources[METHOD])
                else:
                    key = f"{ref} vs {other}"
                    row = _score(sources[ref], sources[other])
                rows[key][volume].append(row)
                rows[key]["all"].append(row)
    report = {
        "annotators": annotators,
        "scores": {
            key: {volume: _pool(r) for volume, r in by_volume.items()}
            for key, by_volume in rows.items()
        },
        "unlocated_gold_units": missing,
        "absent_gold_pages": absent,
    }
    path = write_report(
        f"bench_compare{'_' + args.bench if args.bench else ''}", report
    )

    print("=" * 72)
    for key, by_volume in report["scores"].items():
        print(key)
        for volume, s in by_volume.items():
            print(
                f"  {volume:>3} starts ref={s['reference_starts']:>4} "
                f"cmp={s['compared_starts']:>4} P={s['precision']:.2f} "
                f"R={s['recall']:.2f} F1={s['f1']:.2f} "
                f"pub={s['publication_class_agreement']} "
                f"refR={s['reference_recall']} refP={s['reference_precision']}"
            )
    print(f"unlocated gold units: {len(missing)}, absent gold pages: {len(absent)}")
    print(f"OK report {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
