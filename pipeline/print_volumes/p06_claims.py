"""p06: compiler reference claims within print and first concordance candidates to the wiki.

Reads the p03 records (data/print/derived/records/entries-<volume>.jsonl) and
the wiki publication layer (docs/data/publications/*.json, read only), and
writes two claim files to data/print/derived/claims/:

- compiler-claims.jsonl: every address the compiler printed inside an entry,
  typed by the notation that introduces it (See, Rep:, Contents:, Correction
  to, Cont., a bracketed work reference, an untyped inline address). A list
  continuation ("F 1, 6-8 / L 68") keeps the type of the address before it. The
  target is resolved to a record identifier where the addressed entry exists;
  otherwise the claim stays unresolved and is listed.
- concordance-candidates.jsonl: pairs of a print object and a wiki publication
  whose normalised titles and years are equal.

Every claim carries subject, predicate, object, evidence (record, SHA-256 of
its text, character offsets), a typed producer and the state "proposed". The
compiler's notation is read by exact rule, but its precision is not measured
yet, so no claim is confirmed here (knowledge/print-wiki-merge.md, Claims).
Title-and-year equality is an editorial rule whose precision is unknown; its
candidates are a first measure of overlap, not identities. Print titles suffer
from substitute-font damage to diacritics, so print-wiki overlap is a lower
bound.

Output: the claim files and data/print/derived/reports/p06_claims.json.

Usage: python -m uv run python pipeline/print_volumes/p06_claims.py
"""

import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from _addresses import REFERENCE, SUFFIX_TO_VOLUME, intro_of, parse_items
from _common import DERIVED_DIR, SECTIONS, VOLUMES, write_report

RECORDS = DERIVED_DIR / "records"
CLAIMS = DERIVED_DIR / "claims"
WIKI_PUBLICATIONS = Path(__file__).resolve().parents[2] / "docs/data/publications"
PREDICATES = {
    "correction": "correctionOf",
    "continuation": "continuationOf",
    "reprint": "reprintedIn",
    "contents": "contains",
    "see": "seeAlso",
    "bracket": "relatedWork",
    "index": "indexEntry",
    "inline": "relatedTo",
}
COMPILER = {"class": "compiler", "method": "rule", "rule": "p06.address-notation"}
TITLE_YEAR = {"class": "editorial", "method": "rule", "rule": "p06.title-year"}
TITLE_KEY_CHARS = 40
MIN_TITLE_KEY = 6


def _claim_id(*parts: str) -> str:
    return "claim:" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _load_records() -> dict[str, list[dict]]:
    result = {}
    for volume in VOLUMES:
        path = RECORDS / f"entries-{volume}.jsonl"
        if not path.exists():
            sys.exit(f"FEHLER: {path} missing; run p03_records.py first")
        with path.open(encoding="utf-8") as source:
            result[volume] = [json.loads(line) for line in source]
    return result


def _address_index(records: dict[str, list[dict]]) -> dict[str, str]:
    """Printed address ("F 47", "HA1 34") to record identifier, first wins."""
    index: dict[str, str] = {}
    for volume_records in records.values():
        for record in volume_records:
            if record["address"]:
                index.setdefault(record["address"], record["id"])
    return index


def _compiler_claims(record: dict, index: dict[str, str]) -> list[dict]:
    text = record["text"]
    claims = []
    kind = "inline"
    for match in REFERENCE.finditer(text):
        letter, suffix, group = match.groups()
        suffix = suffix or ""
        if suffix not in SUFFIX_TO_VOLUME:
            continue
        if match.start() == 0 and record["address"]:
            continue  # the entry's own printed address
        found = intro_of(text[max(0, match.start() - 40) : match.start()])
        if found != "list":
            kind = found
        if record["kind"] == "reference" and kind == "inline":
            kind = "see"
        targets, _ = parse_items(group)
        for number, letter_suffix in targets:
            address = f"{letter}{suffix} {number}{letter_suffix}"
            if address == record["address"]:
                continue
            target = index.get(address)
            claims.append(
                {
                    "id": _claim_id(record["id"], str(match.start()), address),
                    "subject": record["id"],
                    "predicate": PREDICATES[kind],
                    "object": target,
                    "object_address": address,
                    "resolved": target is not None,
                    "evidence": {
                        "record": record["id"],
                        "sha256": record["sha256"],
                        "start": match.start(),
                        "end": match.end(),
                        "text": match.group(0),
                    },
                    "producer": COMPILER,
                    "state": "proposed",
                }
            )
    return claims


def _title_key(title: str) -> str:
    plain = unicodedata.normalize("NFKD", title)
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-z]", "", plain.lower())[:TITLE_KEY_CHARS]


def _wiki_index() -> tuple[dict[tuple[str, int], list[dict]], dict]:
    """Title-year keys of the wiki: segmented publications, then flat pages.

    The publication layer covers only the segmented multi-edition pages; for
    every other bibliographic page the page's own title and year stand in.
    """
    index: dict[tuple[str, int], list[dict]] = defaultdict(list)
    pages_with_publications: set[int] = set()

    def add(key_title: str, year: object, row: dict) -> None:
        key = _title_key(key_title or "")
        if len(key) >= MIN_TITLE_KEY and isinstance(year, int):
            index[(key, year)].append(row)

    for path in sorted(WIKI_PUBLICATIONS.glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        for publication in page.get("publications", []):
            pages_with_publications.add(page["sourcePageId"])
            add(
                publication.get("title"),
                publication.get("year"),
                {
                    "id": publication["id"],
                    "page": page["sourcePageId"],
                    "title": publication.get("title"),
                    "year": publication.get("year"),
                    "sha256": publication.get("sourceSlice", {}).get("sha256"),
                },
            )
    flat = json.loads((WIKI_PUBLICATIONS.parent / "klawiter.json").read_text("utf-8"))
    bibliographic = [
        e
        for e in flat["entries"]
        if "klawiter:WikiInfrastructurePage" not in e.get("@type", [])
    ]
    for entry in bibliographic:
        if entry["sourcePageId"] in pages_with_publications:
            continue
        add(
            entry.get("title"),
            entry.get("year"),
            {
                "id": entry["@id"],
                "page": entry["sourcePageId"],
                "title": entry.get("title"),
                "year": entry.get("year"),
                "sha256": None,
            },
        )
    return index, {
        "bibliographic_pages": len(bibliographic),
        "pages_with_publication_layer": len(pages_with_publications),
    }


def _concordance(
    records: dict[str, list[dict]], wiki: dict[tuple[str, int], list[dict]]
) -> tuple[list[dict], dict]:
    candidates = []
    stats: dict = {}
    wiki_hit: set[str] = set()
    for volume, volume_records in records.items():
        counts: Counter = Counter()
        by_part: dict[str, Counter] = defaultdict(Counter)
        for record in volume_records:
            for obj in record["objects"]:
                fields = obj["fields"]
                key = _title_key(fields["title"] or "")
                counts["objects"] += 1
                by_part[record["part"]]["objects"] += 1
                if len(key) < MIN_TITLE_KEY or not fields["year"]:
                    counts["unkeyed"] += 1
                    continue
                counts["keyed"] += 1
                matches = wiki.get((key, fields["year"]), [])
                if not matches:
                    continue
                counts["matched"] += 1
                by_part[record["part"]]["matched"] += 1
                counts["ambiguous"] += len(matches) > 1
                for publication in matches:
                    wiki_hit.add(publication["page"])
                    candidates.append(
                        {
                            "id": _claim_id(obj["id"], publication["id"]),
                            "subject": obj["id"],
                            "predicate": "samePublicationAs",
                            "object": publication["id"],
                            "evidence": {
                                "print": {
                                    "record": record["id"],
                                    "sha256": record["sha256"],
                                    "title": fields["title"],
                                    "year": fields["year"],
                                },
                                "wiki": publication,
                                "key": key,
                            },
                            "producer": TITLE_YEAR,
                            "state": "proposed",
                            "alternatives": len(matches),
                        }
                    )
        stats[volume] = {
            **dict(counts),
            "matched_share_of_keyed": round(
                counts["matched"] / max(1, counts["keyed"]), 3
            ),
            "by_part": {
                part: {
                    **dict(c),
                    "share": round(c["matched"] / max(1, c["objects"]), 3),
                }
                for part, c in sorted(by_part.items())
            },
        }
    stats["wiki_pages_matched"] = len(wiki_hit)
    return candidates, stats


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as sink:
        for row in rows:
            sink.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def main() -> int:
    CLAIMS.mkdir(parents=True, exist_ok=True)
    records = _load_records()
    index = _address_index(records)
    claims = [
        claim
        for volume_records in records.values()
        for record in volume_records
        if record["kind"] != "heading"
        for claim in _compiler_claims(record, index)
    ]
    _write_jsonl(CLAIMS / "compiler-claims.jsonl", claims)
    by_predicate = Counter(c["predicate"] for c in claims)
    unresolved = Counter(
        c["object_address"].split(" ")[0] for c in claims if not c["resolved"]
    )
    by_target_volume = Counter(
        (
            c["subject"].split("/")[0],
            SUFFIX_TO_VOLUME[
                re.match(r"[A-R](A[12])?", c["object_address"]).group(1) or ""
            ],
        )
        for c in claims
    )
    print(
        f"OK compiler claims: {len(claims)}, resolved "
        f"{sum(c['resolved'] for c in claims)}, by predicate {dict(by_predicate)}"
    )

    wiki, wiki_scope = _wiki_index()
    candidates, overlap = _concordance(records, wiki)
    _write_jsonl(CLAIMS / "concordance-candidates.jsonl", candidates)
    overlap.update(wiki_scope)
    overlap["wiki_keys"] = len(wiki)
    for volume in VOLUMES:
        s = overlap[volume]
        print(
            f"OK {volume}: objects {s['objects']}, keyed {s.get('keyed', 0)}, "
            f"with wiki candidate {s.get('matched', 0)} "
            f"({s['matched_share_of_keyed']:.0%} of keyed), "
            f"ambiguous {s.get('ambiguous', 0)}"
        )
    print(
        f"OK wiki pages with a print candidate: "
        f"{overlap['wiki_pages_matched']} of {wiki_scope['bibliographic_pages']}"
    )
    report = {
        "compiler_claims": {
            "total": len(claims),
            "resolved": sum(c["resolved"] for c in claims),
            "by_predicate": dict(by_predicate),
            "unresolved_by_section_code": dict(unresolved.most_common()),
            "by_volume_pair": {
                f"{a}->{b}": n for (a, b), n in by_target_volume.items()
            },
        },
        "concordance": overlap,
        "sections": {v: SECTIONS["volumes"][v]["suffix"] for v in VOLUMES},
    }
    path = write_report("p06_claims", report)
    print(f"OK report {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
