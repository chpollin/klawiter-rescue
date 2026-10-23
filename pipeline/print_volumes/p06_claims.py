"""p06: compiler reference claims within print.

Reads the p03 records (data/print/derived/records/entries-<volume>.jsonl) and
writes data/print/derived/claims/compiler-claims.jsonl: every address the
compiler printed inside an entry, typed by the notation that introduces it
(See, Rep:, Contents:, Correction to, Cont., a bracketed work reference, an
untyped inline address). A list continuation ("F 1, 6-8 / L 68") keeps the type
of the address before it. The target is resolved to a record identifier where
the addressed entry exists; otherwise the claim stays unresolved and is listed.
The concordance with the wiki is p07_concordance.py.

Every claim carries subject, predicate, object, evidence (record, SHA-256 of
its text, character offsets), a typed producer and the state "proposed". The
compiler's notation is read by exact rule, but its precision is not measured
yet, so no claim is confirmed here (knowledge/print-wiki-merge.md, Claims).

Output: the claim file and data/print/derived/reports/p06_claims.json.

Usage: python -m uv run python pipeline/print_volumes/p06_claims.py
"""

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from _addresses import REFERENCE, SUFFIX_TO_VOLUME, intro_of, parse_items
from _common import DERIVED_DIR, SECTIONS, VOLUMES, write_report

RECORDS = DERIVED_DIR / "records"
CLAIMS = DERIVED_DIR / "claims"
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
        "sections": {v: SECTIONS["volumes"][v]["suffix"] for v in VOLUMES},
    }
    path = write_report("p06_claims", report)
    print(f"OK report {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
