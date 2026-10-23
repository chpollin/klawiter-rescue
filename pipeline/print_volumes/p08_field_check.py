"""p08: field agreement of print and wiki on silver pairs, a check of both sources.

A silver pair (p07) is a print entry whose distinctive text stood near-verbatim
in some revision of one wiki page. The wiki text of such a pair descends from
the compiler's print file (Addendum II reached the early wiki nearly verbatim),
so the two are not independent witnesses of the publication. They are two
independent extractions of related text: the print strand reads the PDF, the
production pipeline reads the wiki. Comparing their fields therefore checks
both extractors, field by field, without a human gold standard; agreement
shows consistency, not correctness against the book. A
disagreement says that at least one side is wrong, not which; the cases are
written out for inspection, and only a person or a further rule decides them.

The wiki side is the publication of the published frontend layer
(docs/data/publications/<page>.json) whose year equals the print object's
year; pages without that layer fall back to the flat record, reported apart,
because the flat fields are the ones the review of 2026-10-23 found taken from
the wrong passage on such pages.

Alignment, year and title establish the counterpart; page and year alone do
not, because in the main volume the aligned text is often a translation or
review list pasted into a work page. Pairs whose titles differ are counted,
not compared, and the remaining fields are compared on the rest.

Field rules (all on folded tokens, see p07._tokens):
- title (identity gate): the shorter token list is contained in the longer
  one, or the first TITLE_WORDS tokens are equal.
- publisher, place: share at least one distinctive token (p07.GENERIC and
  tokens shorter than p07.MIN_FIELD_TOKEN do not count).
- translator: the surnames (last token) of some print and wiki translator match.
- extent: the numbered page count of the wiki equals a page number of the
  print extent.

Output: data/print/derived/reports/p08_field_check.json and
data/print/derived/reports/p08_field_check_cases.jsonl (local, print text).

Usage: python -m uv run python pipeline/print_volumes/p08_field_check.py
"""

import json
import sys
from collections import Counter, defaultdict

from _common import DERIVED_DIR, PROJECT_ROOT, REPORT_DIR, VOLUMES, write_report
from p07_concordance import EXTENT, GENERIC, MIN_FIELD_TOKEN, SILVER, _tokens

CLAIMS = DERIVED_DIR / "claims" / "concordance.jsonl"
RECORDS = DERIVED_DIR / "records"
PUBLICATIONS = PROJECT_ROOT / "docs" / "data" / "publications"
FLAT = PROJECT_ROOT / "docs" / "data" / "klawiter.json"
TITLE_WORDS = 4
FIELDS = ("title", "publisher", "place", "translator", "extent")


def _silver_pairs() -> list[tuple[str, int]]:
    if not CLAIMS.exists():
        sys.exit(f"FEHLER: {CLAIMS} missing; run p07_concordance.py first")
    pairs = []
    with CLAIMS.open(encoding="utf-8") as source:
        for claim in map(json.loads, source):
            if (
                claim["predicate"] == "textAlignedWith"
                and claim["evidence"]["score"] >= SILVER
            ):
                page = int(claim["object"].rsplit("/", 1)[1])
                pairs.append((claim["subject"], page))
    return pairs


def _entries() -> dict[str, dict]:
    entries = {}
    for volume in VOLUMES:
        with (RECORDS / f"entries-{volume}.jsonl").open(encoding="utf-8") as source:
            for record in map(json.loads, source):
                entries[record["id"]] = record
    return entries


def _distinct(value: str | None) -> set[str]:
    return {
        t
        for t in _tokens(value or "")
        if len(t) >= MIN_FIELD_TOKEN and t not in GENERIC and not t.isdigit()
    }


def _title_agrees(a: str, b: str) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    short, long_ = sorted((ta, tb), key=len)
    joined = " " + " ".join(long_) + " "
    return (" " + " ".join(short) + " ") in joined or ta[:TITLE_WORDS] == tb[
        :TITLE_WORDS
    ]


def _title_defect(title: str) -> bool:
    """A print title that is no title: a lone initial ("G"), or an imprint or
    extent read as title ("Büchergilde Gutenberg: 411/[1]p"), as printing lines
    under a collection header in the main volume yield. Counted as a print
    field defect, not compared."""
    tokens = _tokens(title)
    return (
        not tokens
        or len("".join(tokens)) < 3
        or bool(EXTENT.search(title))
        # "Bertelsmann:" opens a printing line whose title is the header's.
        or title.rstrip().endswith(":")
        or title.lstrip().upper().startswith(("EXCERPTS", "CONTENTS"))
    )


def _surnames(names: list[str]) -> set[str]:
    return {_tokens(n)[-1] for n in names if _tokens(n)}


def _print_side(obj: dict) -> dict:
    fields = obj["fields"]
    numbers = set()
    for groups in EXTENT.findall(obj["text"]):
        for part in groups:
            numbers.update(int(n) for n in _tokens(part) if n.isdigit())
    return {
        "title": fields.get("title") or (obj.get("inherited") or {}).get("title", ""),
        "publisher": fields.get("publisher") or "",
        "place": fields.get("place") or "",
        "translator": [fields["translator"]] if fields.get("translator") else [],
        "extent": numbers,
    }


def _wiki_publication(pub: dict) -> dict:
    extent = (pub.get("extent") or {}).get("numbered")
    return {
        "title": pub.get("title") or "",
        "publisher": pub.get("publisher") or "",
        "place": " ".join(pub.get("places") or []),
        "translator": [
            c["name"] for c in pub.get("credits") or [] if c.get("role") == "translator"
        ],
        "extent": {extent} if extent else set(),
    }


def _wiki_flat(entry: dict) -> dict:
    count = entry.get("pageCount")
    return {
        "title": entry.get("title") or "",
        "publisher": entry.get("publisher") or "",
        "place": entry.get("location") or "",
        "translator": [entry["translator"]] if entry.get("translator") else [],
        "extent": {count} if isinstance(count, int) else set(),
    }


def _compare(p: dict, w: dict) -> dict[str, str]:
    out = {}
    for field in FIELDS:
        pv, wv = p[field], w[field]
        if not pv and not wv:
            out[field] = "both_missing"
        elif not pv:
            out[field] = "wiki_only"
        elif not wv:
            out[field] = "print_only"
        elif field == "title":
            out[field] = "agree" if _title_agrees(pv, wv) else "differ"
        elif field in ("publisher", "place"):
            out[field] = "agree" if _distinct(pv) & _distinct(wv) else "differ"
        elif field == "translator":
            out[field] = "agree" if _surnames(pv) & _surnames(wv) else "differ"
        else:
            out[field] = "agree" if pv & wv else "differ"
    return out


def main() -> int:
    pairs = _silver_pairs()
    entries = _entries()
    flat = {
        e["sourcePageId"]: e for e in json.loads(FLAT.read_text("utf-8"))["entries"]
    }
    tally: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    pair_stats: dict[str, Counter] = defaultdict(Counter)
    cases = []
    for entry_id, page in pairs:
        entry = entries[entry_id]
        volume = entry["volume"]
        path = PUBLICATIONS / f"{page}.json"
        pubs = (
            json.loads(path.read_text("utf-8"))["publications"] if path.exists() else []
        )
        for obj in entry["objects"]:
            year = obj["fields"].get("year")
            if not year:
                pair_stats[volume]["objects_without_year"] += 1
                continue
            printed = _print_side(obj)
            if _title_defect(printed["title"]):
                pair_stats[volume]["print_title_defect"] += 1
                continue
            if pubs:
                same = [p for p in pubs if p.get("year") == year]
                if not same:
                    pair_stats[volume]["no_wiki_publication_of_that_year"] += 1
                    continue
                if len(same) > 1:
                    pair_stats[volume]["several_wiki_publications_of_that_year"] += 1
                # The pair is page-level; among the page's publications of that
                # year the best-agreeing one is taken as the counterpart. This
                # favours agreement, so the rate is an upper bound for such pages.
                best = max(
                    same,
                    key=lambda p: list(
                        _compare(printed, _wiki_publication(p)).values()
                    ).count("agree"),
                )
                layer, wiki, wiki_id = (
                    "publication",
                    _wiki_publication(best),
                    best["id"],
                )
            elif page in flat:
                if flat[page].get("year") != year:
                    pair_stats[volume]["flat_year_differs"] += 1
                    continue
                layer, wiki, wiki_id = "flat", _wiki_flat(flat[page]), f"page/{page}"
            else:
                pair_stats[volume]["wiki_page_not_published"] += 1
                continue
            result = _compare(printed, wiki)
            # Alignment, year and title together establish the counterpart.
            # Page and year alone do not: in the main volume the near-verbatim
            # text is often a translation or review list pasted into a work
            # page, whose publications are other books.
            if result.pop("title") != "agree":
                pair_stats[volume][f"no_counterpart_by_title_{layer}"] += 1
                continue
            pair_stats[volume][f"compared_{layer}"] += 1
            for field, outcome in result.items():
                tally[f"{volume}/{layer}"][field][outcome] += 1
            if "differ" in result.values():
                cases.append(
                    {
                        "print": obj["id"],
                        "wiki": wiki_id,
                        "layer": layer,
                        "differ": sorted(f for f, o in result.items() if o == "differ"),
                        "printFields": {
                            k: v
                            for k, v in obj["fields"].items()
                            if v and k != "author"
                        },
                        "wikiFields": {
                            k: sorted(v) if isinstance(v, set) else v
                            for k, v in wiki.items()
                            if v
                        },
                    }
                )

    def rate(counter: Counter) -> float | None:
        both = counter["agree"] + counter["differ"]
        return round(counter["agree"] / both, 3) if both else None

    report = {
        "about": "Agreement of print and wiki fields on silver pairs (near-verbatim "
        "alignment). Agreement between two extractions, not correctness; a "
        "disagreement means at least one side is wrong.",
        "silver_pairs": len(pairs),
        "pairs": {v: dict(c) for v, c in sorted(pair_stats.items())},
        "fields": {
            key: {
                field: {**dict(counts), "agreement": rate(counts)}
                for field, counts in fields.items()
            }
            for key, fields in sorted(tally.items())
        },
        "cases_with_disagreement": len(cases),
    }
    write_report("p08_field_check", report)
    out = REPORT_DIR / "p08_field_check_cases.jsonl"
    with out.open("w", encoding="utf-8") as sink:
        for case in cases:
            sink.write(json.dumps(case, ensure_ascii=False) + "\n")
    for key, fields in report["fields"].items():
        line = ", ".join(f"{f} {v['agreement']}" for f, v in fields.items())
        print(f"OK {key}: {line}")
    print(f"OK {len(cases)} cases with a disagreement -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
