"""p05: the errata pages of Addendum I as compiler correction claims against the main volume.

Addendum I opens with a list of errata to the main volume (PDF pp. 6-11, part
"Errata" in sections.json). Each erratum starts at the left margin with
"Page <printed page>" and continues in indented lines. After the page it names
its target: an entry address with an optional sub-item or line locator
("A 5, line 4", "K 38[2]", "M 69/27", "F 304 & 305", "K 445 and page 851"), a
label for unnumbered text ("Obras completas", an index heading), or nothing.
The correction follows as the compiler's own verbs: Read, For ... read, Add,
Omit, Transfer ... to, should be listed under, Renumber as, or plain prose.

Data flow: p01 lines (lines-A1.jsonl) -> erratum blocks (one per "Page" line
with its continuation lines, joined by single spaces, text unaltered) ->
segments (a block that corrects several entries, "A 167: ... A 168: ...", is
split before each further "<address>:") -> one claim per segment and target
address -> data/print/derived/claims/errata-claims.jsonl and the report
data/print/derived/reports/p05_errata.json.

Design decisions:
- The printed page numbers are those of the 1991 edition. The main-volume file
  is a later working state whose PDF pages drift away from them, so a target
  is resolved only by its address through the p03 address index, never by page.
- The predicate comes from the strongest operation the segment prints, in the
  closed set renumbersAs > movesTo > omitsFrom > addsTo > correctsReading >
  correctionOf. correctionOf covers prose corrections, hedged readings
  ("Possibly ... instead of ...") and reorderings, which state no replacement.
- Values are taken only where printed: quoted strings (nested quotes are
  balanced by position), an unquoted remainder after a colon ("Add: ..."), an
  address after Add, and year pairs written "1982, not 1981". Anything else
  stays in the evidence text only; no value is inferred.
- A segment without a resolvable address stays in the file with resolved
  false and a reason (front_matter, page_only, address_not_found).
- For resolved replacements, in_target records whether the printed wrong and
  right values occur in the target record's text. This is a substring test
  that hints at whether the file already carries the correction; it proves
  nothing for short values such as years.
- All claims are compiler claims by rule with the state "proposed"
  (knowledge/print-wiki-merge.md, Claims).

Usage: python -m uv run --group print python pipeline/print_volumes/p05_errata.py
"""

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from _common import DERIVED_DIR, load_lines, part_of, write_report

RECORDS = DERIVED_DIR / "records" / "entries-I.jsonl"
CLAIMS = DERIVED_DIR / "claims"
PRODUCER = {"class": "compiler", "method": "rule", "rule": "p05.errata"}
RUNNING_HEAD = re.compile(r"^(?:Errata \d+|\d+ Errata|ERRATA / SZ BIBLIOGRAPHY)$")
START = re.compile(r"^Page (?P<page>\d+|[ivxl]+)\b\s*")
MARGIN_MAX = 130.0
ADDR = r"[A-R] ?\d{1,4}[a-z]?"
TARGET = re.compile(
    rf"^(?P<head>{ADDR}(?:\s?\[[^\]]*\]|/\d+)?"
    rf"(?:\s?(?:&|and)\s?(?:{ADDR}|\d{{1,4}}[a-z]?|page \d+)(?:\s?\[[^\]]*\])?)*)"
    r"(?P<loc>,\s?(?:lines? [\d-]+|last line))?\s?:?\s*"
)
ADDRESS = re.compile(r"(?<![A-Za-z])([A-R]) ?(\d{1,4}[a-z]?)(?:\s?(\[[^\]]*\]|/\d+))?")
CONTINUED = re.compile(r"&\s?(\d{1,4}[a-z]?)\b")
EXTRA_PAGE = re.compile(r"and (page \d+)")
LABEL = re.compile(r'^(?!(?:Add|Read|Omit|Delete|For)\b)(?P<label>[^:"]{1,40}):\s*')
SPLIT = re.compile(rf'(?<=[".])\s+(?={ADDR}(?:\s?&\s?\d{{1,4}}[a-z]?)?\s?:)')
VERB = re.compile(
    r"\b(?P<verb>For|Correct to read|should read|Read|read|Correction to|Omit|Delete"
    r"|Eliminate|Add|add|Transfer|Renumber as|[Ss]hould be numbered"
    r"|should be listed(?: solely| as \w+)? under|should be alphabetically reversed"
    r"|Possibly)\b:?\s*|(?<![=\w])=\s*(?=\")"
)
NOT_QUOTED = re.compile(r'\s*,?\s*(?:and\s+)?not\b[^"]{0,30}?(?=")')
NOT_YEAR = re.compile(r"\b(\d{4}),?\s+(?:and\s+)?not\s+(\d{4})\b")
FOR_READ = re.compile(r"\s*read:?\s*")
READ_FOR = re.compile(r"\s*for\s*")
INSTEAD = re.compile(r"\s*instead of\s*")
TO_ADDRESS = re.compile(rf"\s*to\s+({ADDR})")
UNDER_ADDRESS = re.compile(rf"\s*({ADDR})")
AFTER_COLON = re.compile(r'^[^":]{0,40}:\s*(?P<rest>[^"]+?)\s*$')
BARE_ADDRESS = re.compile(rf"^({ADDR})\b")
AMPERSAND = re.compile(r'\s*&\s*(?=")')
TO_QUOTE = re.compile(r'\s*to\s+(?=")')
PREDICATE_ORDER = (
    ("renumber", "renumbersAs"),
    ("move", "movesTo"),
    ("omit", "omitsFrom"),
    ("add", "addsTo"),
    ("replace", "correctsReading"),
)
LOCATOR_MAX = 60


def _claim_id(*parts: str) -> str:
    return "claim:" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _norm(address: str) -> str:
    """'F47' and 'F 47' to the printed form 'F 47'."""
    return re.sub(r"^([A-R]) ?", r"\1 ", address)


def _blocks(lines: list[dict]) -> tuple[list[dict], list[dict]]:
    """Erratum blocks of the Errata part, and the lines that start none."""
    blocks: list[dict] = []
    stray: list[dict] = []
    for line in lines:
        if part_of("A1", line["page"], line["top"])[0] != "Errata":
            continue
        if RUNNING_HEAD.match(line["text"].strip()):
            continue
        if line["x0"] < MARGIN_MAX and START.match(line["text"]):
            blocks.append({"lines": [line]})
        elif blocks:
            blocks[-1]["lines"].append(line)
        else:
            stray.append(line)
    for block in blocks:
        block["text"] = " ".join(line["text"].strip() for line in block["lines"])
    return blocks, stray


def _quote_spans(text: str) -> list[tuple[int, int]]:
    """Outermost quoted spans; a quote opens after space or bracket before non-space."""
    spans, depth, start = [], 0, 0
    for i, char in enumerate(text):
        if char != '"':
            continue
        before = text[i - 1] if i else " "
        after = text[i + 1] if i + 1 < len(text) else " "
        opening = before in " ([/" and not after.isspace()
        if opening or depth == 0:
            if depth == 0:
                start = i
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                spans.append((start, i + 1))
    return spans


def _quote_at(text: str, pos: int, spans: list[tuple[int, int]]) -> tuple | None:
    for start, end in spans:
        if start == pos:
            return start, end, text[start + 1 : end - 1]
    return None


def _locator(body: str, start: int, verb_at: int) -> str | None:
    text = body[start:verb_at].strip(" .;:")
    return text if text and len(text) <= LOCATOR_MAX else None


def _operations(body: str) -> list[dict]:
    """Corrections the body prints, with verbatim values only."""
    spans = _quote_spans(body)
    inside = [False] * (len(body) + 1)
    for start, end in spans:
        for i in range(start, end):
            inside[i] = True
    ops: list[dict] = []
    consumed: set[int] = set()
    pos = 0
    last_end = 0
    while (match := VERB.search(body, pos)) is not None:
        pos = match.end()
        if inside[match.start()]:
            continue
        verb = match.group("verb") or "="
        op: dict = {"verb": verb}
        quote = _quote_at(body, match.end(), spans)
        tail = body[quote[1] :] if quote else ""
        if verb == "For":
            second = FOR_READ.match(tail) if quote else None
            right = _quote_at(body, quote[1] + second.end(), spans) if second else None
            if not right:
                continue
            op.update(op="replace", wrong=quote[2], right=right[2])
            consumed.update({quote[0], right[0]})
            pos = right[1]
        elif verb in ("Read", "read", "Correct to read", "should read", "="):
            op["op"] = "replace"
            if quote:
                op["right"] = quote[2]
                consumed.add(quote[0])
                pos = quote[1]
                second = READ_FOR.match(tail)
                wrong = (
                    _quote_at(body, quote[1] + second.end(), spans) if second else None
                )
                if wrong:
                    op["wrong"] = wrong[2]
                    consumed.add(wrong[0])
                    pos = wrong[1]
                # 'Read "A" & "B"' prints two readings under one verb.
                while (more := AMPERSAND.match(body, pos)) and (
                    extra := _quote_at(body, more.end(), spans)
                ):
                    if shared := _locator(body, last_end, match.start()):
                        op["locator"] = shared
                    ops.append(op)
                    op = {"verb": verb, "op": "replace", "right": extra[2]}
                    consumed.add(extra[0])
                    pos = extra[1]
            else:
                op["right"] = None
        elif verb == "Possibly":
            second = INSTEAD.match(tail) if quote else None
            wrong = _quote_at(body, quote[1] + second.end(), spans) if second else None
            if not wrong:
                continue
            op.update(op="query", right=quote[2], wrong=wrong[2])
            consumed.update({quote[0], wrong[0]})
            pos = wrong[1]
        elif verb == "Correction to":
            if not quote:
                continue
            op.update(op="replace", wrong=quote[2], right=None)
            consumed.add(quote[0])
            pos = quote[1]
        elif verb in ("Omit", "Delete", "Eliminate", "Add", "add"):
            op["op"] = "add" if verb in ("Add", "add") else "omit"
            colon = AFTER_COLON.match(body[match.start() :])
            bare = BARE_ADDRESS.match(body[match.end() :])
            if quote:
                op["value"] = quote[2]
                consumed.add(quote[0])
                pos = quote[1]
            elif colon:
                op.update(value=colon.group("rest"), unquoted=True)
                pos = len(body)
            elif bare:
                op.update(value=_norm(bare.group(1)), unquoted=True)
                pos = match.end() + bare.end()
                into = TO_QUOTE.match(body, pos)
                heading = _quote_at(body, into.end(), spans) if into else None
                if heading:
                    op["to"] = heading[2]
                    consumed.add(heading[0])
                    pos = heading[1]
            else:
                op["value"] = None
        elif verb == "Transfer":
            dest = TO_ADDRESS.match(tail) if quote else None
            if not dest:
                continue
            op.update(op="move", item=quote[2], destination=_norm(dest.group(1)))
            consumed.add(quote[0])
            pos = quote[1] + dest.end()
        elif verb.startswith("should be listed"):
            dest = UNDER_ADDRESS.match(body[match.end() :])
            if not dest:
                continue
            before = [s for s in spans if s[1] <= match.start()]
            item = body[before[-1][0] + 1 : before[-1][1] - 1] if before else None
            op.update(op="move", item=item, destination=_norm(dest.group(1)))
            if before:
                consumed.add(before[-1][0])
            pos = match.end() + dest.end()
        elif verb in ("Renumber as", "Should be numbered", "should be numbered"):
            if not quote:
                continue
            op.update(op="renumber", destination=quote[2])
            consumed.add(quote[0])
            pos = quote[1]
        elif verb == "should be alphabetically reversed":
            op["op"] = "reorder"
        locator = _locator(body, last_end, match.start())
        if locator and op["op"] not in ("move", "renumber", "reorder"):
            op["locator"] = locator
        ops.append(op)
        last_end = pos
    for start, end in spans:
        if start in consumed:
            continue
        negation = NOT_QUOTED.match(body, end)
        wrong = _quote_at(body, negation.end(), spans) if negation else None
        if wrong and wrong[0] not in consumed:
            ops.append(
                {
                    "op": "replace",
                    "verb": "not",
                    "right": body[start + 1 : end - 1],
                    "wrong": wrong[2],
                }
            )
            consumed.update({start, wrong[0]})
    for match in NOT_YEAR.finditer(body):
        if not inside[match.start()]:
            ops.append(
                {
                    "op": "replace",
                    "verb": "not",
                    "right": match.group(1),
                    "wrong": match.group(2),
                    "unquoted": True,
                }
            )
    return ops or [{"op": "note"}]


def _predicate(ops: list[dict]) -> str:
    kinds = {op["op"] for op in ops}
    for kind, predicate in PREDICATE_ORDER:
        if kind in kinds:
            return predicate
    return "correctionOf"


def _targets(segment: str) -> tuple[list[str], dict, str]:
    """Target addresses, the target locator and the body after the target."""
    match = TARGET.match(segment)
    if match:
        head = match.group("head")
        addresses, sub = [], []
        letter = ""
        for found in ADDRESS.finditer(head):
            letter = found.group(1)
            addresses.append(f"{letter} {found.group(2)}")
            if found.group(3):
                sub.append(found.group(3))
        for found in CONTINUED.finditer(head):
            if not re.match(r"[A-R]", head[found.start(1) - 1 : found.start(1)]):
                addresses.append(f"{letter} {found.group(1)}")
        locator = {}
        if sub:
            locator["subitem"] = sub[0] if len(sub) == 1 else sub
        if match.group("loc"):
            locator["line"] = match.group("loc").strip(" ,")
        pages = EXTRA_PAGE.findall(head)
        if pages:
            locator["also"] = pages
        return addresses, locator, segment[match.end() :]
    label = LABEL.match(segment)
    if label:
        return [], {"label": label.group("label").strip()}, segment[label.end() :]
    return [], {}, segment


def _load_index() -> tuple[dict[str, dict], Counter]:
    if not RECORDS.exists():
        sys.exit(f"FEHLER: {RECORDS} missing; run p03_records.py first")
    index: dict[str, dict] = {}
    seen: Counter = Counter()
    with RECORDS.open(encoding="utf-8") as source:
        for line in source:
            record = json.loads(line)
            if record["address"]:
                seen[record["address"]] += 1
                index.setdefault(record["address"], record)
    return index, seen


def _claims_for(block: dict, index: dict, seen: Counter) -> list[dict]:
    first, last = block["lines"][0], block["lines"][-1]
    text = block["text"]
    start = START.match(text)
    page = start.group("page")
    subject = f"A1/Errata/p{first['page']}l{first['line']}"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    rest_at = start.end()
    cuts = [rest_at] + [rest_at + m.end() for m in SPLIT.finditer(text[rest_at:])]
    claims = []
    for seg_start, seg_end in zip(cuts, cuts[1:] + [len(text)], strict=True):
        segment = text[seg_start:seg_end].rstrip()
        addresses, locator, body = _targets(segment)
        ops = _operations(body)
        for op in ops:
            if op.get("destination"):
                found = index.get(op["destination"])
                op["destination_object"] = found["id"] if found else None
        correction = {"printed_page": page, "operations": ops, **locator}
        evidence = {
            "volume": "A1",
            "page": first["page"],
            "line": first["line"],
            "page_end": last["page"],
            "line_end": last["line"],
            "sha256": digest,
            "start": seg_start,
            "end": seg_start + len(segment),
            "text": segment,
        }
        for address in addresses or [None]:
            record = index.get(address) if address else None
            claim = {
                "id": _claim_id(subject, str(seg_start), address or f"page {page}"),
                "subject": subject,
                "predicate": _predicate(ops),
                "object": record["id"] if record else None,
                "object_address": address,
                "resolved": record is not None,
                "correction": correction,
                "evidence": evidence,
                "producer": PRODUCER,
                "state": "proposed",
            }
            if record is None:
                claim["unresolved_reason"] = (
                    "address_not_found"
                    if address
                    else "front_matter"
                    if not page.isdigit()
                    else "page_only"
                )
            else:
                if seen[address] > 1:
                    claim["ambiguous_address"] = seen[address]
                checks = [
                    {
                        side: op[side] in record["text"]
                        for side in ("wrong", "right")
                        if op.get(side)
                    }
                    for op in ops
                    if op["op"] == "replace"
                ]
                if any(checks):
                    claim["in_target"] = checks
            claims.append(claim)
    return claims


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as sink:
        for row in rows:
            sink.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def main() -> int:
    blocks, stray = _blocks(load_lines("A1"))
    if not blocks:
        print("FEHLER: no erratum blocks found in the Errata part of A1")
        return 1
    if stray:
        print(f"FEHLER: {len(stray)} errata lines before the first 'Page' line")
        return 1
    index, seen = _load_index()
    claims = [claim for block in blocks for claim in _claims_for(block, index, seen)]
    CLAIMS.mkdir(parents=True, exist_ok=True)
    _write_jsonl(CLAIMS / "errata-claims.jsonl", claims)

    segments = {(c["subject"], c["evidence"]["start"]) for c in claims}
    by_predicate = Counter(c["predicate"] for c in claims)
    by_operation = Counter(
        op["op"] for c in claims for op in c["correction"]["operations"]
    )
    reasons = Counter(c.get("unresolved_reason") for c in claims if not c["resolved"])
    unresolved = [
        {
            "subject": c["subject"],
            "printed_page": c["correction"]["printed_page"],
            "address": c["object_address"],
            "reason": c["unresolved_reason"],
        }
        for c in claims
        if not c["resolved"]
    ]
    print(
        f"OK errata blocks {len(blocks)}, segments {len(segments)}, claims "
        f"{len(claims)}, resolved {sum(c['resolved'] for c in claims)}"
    )
    print(f"OK by predicate {dict(by_predicate)}")
    print(f"OK unresolved by reason {dict(reasons)}")
    report = {
        "blocks": len(blocks),
        "segments": len(segments),
        "claims": len(claims),
        "resolved": sum(c["resolved"] for c in claims),
        "by_predicate": dict(by_predicate),
        "by_operation": dict(by_operation),
        "unresolved_by_reason": dict(reasons),
        "unresolved": unresolved,
        "ambiguous_targets": sum("ambiguous_address" in c for c in claims),
    }
    path = write_report("p05_errata", report)
    print(f"OK report {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
