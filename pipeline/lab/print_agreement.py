"""Compare wiki values with their candidate print entries (story S6.2), local only.

Input: the per-page print matches under docs/lab/local/print/ that
split_print_links.py writes, and the prepared lab pages under
docs/lab/data/pages/. Output: docs/lab/local/agreement/<pageId>.json and
docs/lab/local/agreement/index.json. The step runs only when the print index
exists, and it writes nothing outside docs/lab/local/, because the print text
and everything derived from it stay unpublished while the rights are
unresolved.

Rules, each a lab rule and not reviewed:

- Candidate print entries of a publication are the field matches and the
  alignment matches whose `publicationIds` name it (the print strand's
  assignment), plus alignment matches without `publicationIds` that this step
  attaches to the publication whose passage they cover. Matches by title and
  year alone never take part, because they are noisy.
- Attachment: the share of the passage's word trigrams (folded with
  fold_search) that also occur in the print entry. The publications with the
  highest share are attached if that share is at least ATTACH_MIN_SHARE; a tie
  attaches all of them as candidates. Trigrams are used because the print
  entry puts the imprint after the title while the wiki puts it first.
- A value occurs in a print entry when every comma-separated part occurs
  there with the occurrence rules of S2.1 (exact, case-sensitive, word
  boundaries). Print text is matched as extracted, so a value not found may
  be an extraction error and is never read as a disagreement.

No agreement raises a state or merges a value; the interface shows each
result as a proposed statement of a lab rule.

Usage:
    python -m uv run python pipeline/lab/print_agreement.py [--print DIR] [--pages DIR] [--out DIR]

Regime: flat script pipeline, not part of the production run.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from lab_rules import find_occurrences, fold_search, split_parts
from split_print_links import REPO, assert_untracked

DEFAULT_PRINT = REPO / "docs" / "lab" / "local" / "print"
DEFAULT_PAGES = REPO / "docs" / "lab" / "data" / "pages"
DEFAULT_OUT = REPO / "docs" / "lab" / "local" / "agreement"
ATTACH_MIN_SHARE = 0.5
CANDIDATE_ROUTES = ("field", "alignment")
VALUE_FIELDS = (
    ("publisher", "publisher"),
    ("places", "place"),
    ("translators", "translator"),
    ("extent", "extent"),
)


def trigrams(text: str) -> set[tuple[str, str, str]]:
    words = fold_search(text).split()
    return {tuple(words[i : i + 3]) for i in range(len(words) - 2)}


def attach_alignment(entry_text: str, passages: dict[str, str]) -> dict:
    """Publications whose passage the print entry covers best, with the share."""
    entry = trigrams(entry_text)
    shares = {}
    for pub_id, passage in passages.items():
        grams = trigrams(passage)
        if grams:
            shares[pub_id] = len(grams & entry) / len(grams)
    if not shares:
        return {"publicationIds": [], "share": None}
    best = max(shares.values())
    if best < ATTACH_MIN_SHARE:
        return {"publicationIds": [], "share": round(best, 3)}
    ids = sorted(p for p, s in shares.items() if s == best)
    return {"publicationIds": ids, "share": round(best, 3)}


def occurs_in(entry_text: str, value: object) -> bool:
    """Every part of the value occurs in the entry, with the rules of S2.1."""
    parts = split_parts(value)
    return bool(parts) and all(find_occurrences(entry_text, part) for part in parts)


def publication_values(pub: dict) -> list[dict]:
    """The located values of a publication: publisher, places, translators, extent."""
    rows = []
    for key, field in VALUE_FIELDS:
        cells = pub["fields"][key]
        for index, cell in enumerate(cells if isinstance(cells, list) else [cells]):
            if cell.get("value") not in (None, ""):
                rows.append({"field": field, "index": index, "value": cell["value"]})
    return rows


def page_agreement(page: dict, matches: list[dict]) -> dict:
    """Candidate entries per publication and, per value, the entries holding it."""
    text = page["source"]["text"]
    passages = {
        p["id"]: text[p["textStart"] : p["textEnd"]]
        for p in page["publications"]
        if p.get("textStart") is not None and p.get("textEnd") is not None
    }
    own = {p["id"] for p in page["publications"]}
    attachments = {}
    candidates: dict[str, list[dict]] = {pid: [] for pid in own}
    for m in matches:
        if m.get("route") not in CANDIDATE_ROUTES:
            continue
        named = [p for p in m.get("publicationIds") or [] if p in own]
        by = "print strand"
        if not named and m["route"] == "alignment":
            attached = attach_alignment(m.get("text") or "", passages)
            attachments[m["printId"]] = attached
            named, by = attached["publicationIds"], "lab rule"
        for pub_id in named:
            candidates[pub_id].append(
                {
                    "printId": m["printId"],
                    "route": m["route"],
                    "candidates": len(named),
                    "attachedBy": by,
                }
            )
    texts = {m["printId"]: m.get("text") or "" for m in matches}
    publications = {}
    for pub in page["publications"]:
        entries = candidates[pub["id"]]
        if not entries:
            continue
        values = [
            row
            | {
                "foundIn": [
                    e["printId"]
                    for e in entries
                    if occurs_in(texts[e["printId"]], row["value"])
                ]
            }
            for row in publication_values(pub)
        ]
        publications[pub["id"]] = {"entries": entries, "values": values}
    return {
        "pageId": page["pageId"],
        "attachments": attachments,
        "publications": publications,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--print", dest="print_dir", type=Path, default=DEFAULT_PRINT)
    parser.add_argument("--pages", type=Path, default=DEFAULT_PAGES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if not (args.print_dir / "index.json").exists():
        sys.exit(f"no local print index at {args.print_dir}; nothing to compare")
    assert_untracked(args.out)

    counts: Counter[str] = Counter()
    errors = []
    results = {}
    for path in sorted(args.print_dir.glob("*.json")):
        if path.name == "index.json":
            continue
        try:
            matches = json.loads(path.read_text(encoding="utf-8")).get("print") or []
            page_file = args.pages / path.name
            if not page_file.exists():
                counts["printPagesWithoutLabPage"] += 1
                continue
            page = json.loads(page_file.read_text(encoding="utf-8"))
            result = page_agreement(page, matches)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append({"file": path.name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        if not result["publications"] and not result["attachments"]:
            continue
        results[path.stem] = result
        counts["alignmentUnnamed"] += len(result["attachments"])
        counts["alignmentAttached"] += sum(
            1 for a in result["attachments"].values() if a["publicationIds"]
        )
        for pub in result["publications"].values():
            counts["publicationsWithCandidates"] += 1
            counts["valuesChecked"] += len(pub["values"])
            counts["valuesFound"] += sum(1 for v in pub["values"] if v["foundIn"])

    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    for stem, result in results.items():
        (args.out / f"{stem}.json").write_text(
            json.dumps(result, ensure_ascii=False), encoding="utf-8"
        )
    index = {
        "state": "proposed, lab rule, not reviewed",
        "attachMinShare": ATTACH_MIN_SHARE,
        "pages": len(results),
        "counts": dict(sorted(counts.items())),
        "errors": errors,
    }
    (args.out / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"wrote {len(results)} page files to {args.out}: {index['counts']}")
    if errors:
        sys.exit(f"{len(errors)} print files failed, see {args.out / 'index.json'}")


if __name__ == "__main__":
    main()
