"""p10: validate every print object against the schema and the invariants, and measure coverage.

Each object of the p03 records is validated by the strict models of
_schema.py, then checked by rules over all objects (knowledge/print-wiki-merge.md,
How results are checked):

- span: every span lies inside the text of its source record ("from", or the
  object's entry), and the object's text is its span of the entry, whose hash
  the object carries.
- verbatim: a text value equals its passage; a year equals the digits of its
  passage; a flag spans its bracket or "ca."; a role spans its credit word (or
  the head name the rule names); a language spans a name that folds to it.
- scope: a value without "from" lies inside the object's span; "inherited"
  occurs only inside the inherited block and every value there is inherited
  from an existing record; an inherited language comes from a heading of the
  same part before the entry.
- derivation: types follow from the fields (_fields.derive_types); a relation
  or reference kind follows from its printed label.
- addresses: every target is the record of that address.
- year: within the bounds of the volume's state.
- rule: every rule names a rule defined in _fields.py or p03_records.py.
- shape: checks written apart from the readers, so that a wrong value can
  fail although it is verbatim and in scope: a title is no date, siglum,
  edition statement or inverted name; a periodical's date holds a digit; a
  place holds no digit and is no siglum; a name holds no digit; a publisher
  holds no credit.

- lines: every p01 line outside the page furniture is held by an entry or an
  apparatus record, so that no text of the three files is left out.
- apparatus: every index, front matter and tail item (_apparatus.py) holds
  the model, its record's text and hash, verbatim values in its record, index
  reference kinds on their address, a term before the first address, and
  address targets that are the records of their addresses.

The checks above verify consistency and provenance; they cannot show that a
value is the right one, which only a person's sample measures (p09). The shape
checks catch classes of wrong values, not every wrong value.

Known exceptions are listed by object identifier and reason in
known_exceptions.json; a violation outside the list fails, and a listed case
that no longer fails must leave the list. Coverage is reported per volume,
type and field as the share of objects holding the field; it measures what the
rules read, not whether it is right.

Output: data/print/derived/reports/p10_validate.json and
p10_violations.jsonl (local, ids and rule names only).

Usage: python -m uv run python pipeline/print_volumes/p10_validate.py
"""

import json
import re
import sys
from collections import Counter, defaultdict

from _apparatus import is_furniture as apparatus_furniture
from _apparatus import segments
from _common import DERIVED_DIR, HERE, REPORT_DIR, VOLUMES, load_lines, write_report
from _fields import (
    LANGUAGE_BY_FOLD,
    MARKER,
    ROLE_WORDS,
    derive_types,
    marker_kind,
)
from _lines import annotate
from _llm import PROMPT_ID
from _objects import ITEM, SPLIT_LABEL, _label_kind
from _schema import ApparatusItem, PrintObject, iter_values, object_values
from pydantic import ValidationError

RECORDS = DERIVED_DIR / "records"
EXCEPTIONS = HERE / "known_exceptions.json"
# Latest year each file can hold: insertions in the main volume run to 2001,
# Addendum I appeared in 1999, the Addendum II file closes in 2009 with
# entries announced to 2011.
YEAR_BOUNDS = {"I": (1450, 2001), "A1": (1450, 1999), "A2": (1450, 2012)}
HEAD_ROLES = {
    "p03.head-author": "author",
    "p03.head-contributor": "contributor",
    "p03.review-author": "author",
    "p03.reviewed-author": "author",
    "p03.speaker": "contributor",
}
# Shape checks, deliberately not shared with _fields.py.
MONTHS = (
    r"(?:january|february|march|april|may|june|july|august|september|october|"
    r"november|december|jan\.|feb\.|mar\.|apr\.|jun\.|jul\.|aug\.|sept?\.|oct\.|nov\.|dec\.)"
)
DATE_ONLY = re.compile(
    rf"^(?=.*\d)[\d\s.,/-]*\b{MONTHS}(?![a-z])[\d\s.,/-]*(?:\b{MONTHS}(?![a-z])[\d\s.,/-]*)?$"
    r"|^\d{1,2}\.\s?\d{1,2}\.\s?\d{4}$",
    re.IGNORECASE,
)
EDITION_ONLY = re.compile(
    r"^(?:\d+(?:st|nd|rd|th)|New|Rev\.|Revised|Large print|Pktbk\.|Prbk\.|Paperback|Special|"
    r"Book ?[Cc]lub)\s(?:ed|impr|edition)|^\(?\d+\.\s?(?:-\s?\d+\.\s?)?(?:Tsd|Auflage)|"
    r"^(?:New|First|Second|Third|\d+(?:st|nd|rd|th))(?: private)? printing\b|^Microcard\b|^NB$",
    re.IGNORECASE,
)
SIGLUM_ONLY = re.compile(r"^[A-Z]{2,6}$")
CODE_START = re.compile(r"^[A-R]{1,2}A2(?:[\s/]|$)")
ISSUE_ONLY = re.compile(r"^(?:No|Nr|Nos|pp?)\.?$")
INVERTED_NAME = re.compile(
    r"^[A-ZÀ-ÞĀ-ž][\w'’-]+(?:[ -][A-ZÀ-ÞĀ-ž][\w'’-]+)?, (?:[A-ZÀ-ÞĀ-ž][\w'’-]*\.?\s?){1,4}$"
)
EXTENT_IN = re.compile(r"\b\d+(?:/[\[(]\d+[\])])?p\b|\b\d+\.-\d+\. Tsd")
CITATION_TAIL = re.compile(r"(?:1[5-9]|20)\d\d, pp?\b|,\s(?:pp?|S)\.?$")
_FN = r"[A-ZÀ-ÞĀ-ž][a-zß-ÿā-ž'’-]+"
NAME_LIST = re.compile(rf"^{_FN} {_FN}(?:, {_FN} {_FN})+$")
NAME_LEAD = re.compile(rf"^{_FN}(?:[ -]{_FN})?, (?:{_FN}|[A-Z]\.)(?: [A-Z]\.)*\.\s")
PAGES_SHAPE = re.compile(r"[\dIVXLCivxlc]")
CREDIT_WORD = re.compile(
    r"\b(?:Trl?s?|Eds?|Intro|Frw|Aftw|Illus)\.|\b(?:Translated|Edited) by\b"
)
RULE_SOURCES = ("_fields.py", "p03_records.py", "_apparatus.py")


def _known_rules() -> tuple[set[str], tuple[str, ...]]:
    literal, prefixes = set(), []
    for name in RULE_SOURCES:
        source = (HERE / name).read_text(encoding="utf-8")
        literal.update(re.findall(r"\"(p0[36]\.[a-z0-9-]+)\"", source))
        prefixes.extend(re.findall(r"f\"(p0[36]\.[a-z0-9-]+-)\{", source))
    return literal, tuple(prefixes)


def _values(node, path=""):
    """(path, value dict) for every value inside node; an object's base keys are left out."""
    return object_values(node) if path == "" else iter_values(node, path)


def check_object(
    obj: dict,
    record: dict,
    texts: dict,
    records: dict,
    order: dict,
    rules: tuple[set, tuple],
) -> list[tuple[str, str]]:
    """Violations of one object as (invariant, detail)."""
    out = []
    try:
        PrintObject.model_validate(obj)
    except ValidationError as error:
        return [
            ("schema", str(error.errors()[0]["loc"]) + " " + error.errors()[0]["msg"])
        ]
    entry_text = record["text"]
    s, e = obj["span"]
    if obj["entry_sha256"] != record["sha256"] or entry_text[s:e] != obj["text"]:
        out.append(("span", "object text or hash"))
    literal, prefixes = rules
    for path, v in _values(obj):
        source = v.get("from")
        text = texts.get(source) if source else entry_text
        a, b = v["span"]
        if text is None:
            out.append(("scope", f"{path}: unknown record {source}"))
            continue
        if not (0 <= a < b <= len(text)):
            out.append(("span", f"{path}: outside its source"))
            continue
        passage = text[a:b]
        rule = v["rule"]
        if not (
            rule in literal or rule.startswith(prefixes) or rule == f"llm:{PROMPT_ID}"
        ):
            out.append(("rule", f"{path}: {rule}"))
        inside_inherited = path.startswith("inherited")
        if (v["by"] == "inherited") != inside_inherited:
            out.append(
                ("scope", f"{path}: inherited outside the block or own value inside")
            )
        if not source and not (s <= a and b <= e):
            out.append(("scope", f"{path}: own value outside the object span"))
        out.extend(_verbatim(path, v, passage))
    for path, v in _values(obj.get("inherited", {}), "inherited"):
        if path.startswith("inherited.language"):
            heading = records.get(v["from"])
            if (
                not heading
                or heading["kind"] != "heading"
                or heading["part"] != record["part"]
                or heading["volume"] != record["volume"]
                or order[heading["id"]] >= order[record["id"]]
            ):
                out.append(
                    ("language-scope", "heading not before the entry in its part")
                )
    expected = derive_types(obj, record)
    if [t["value"] for t in obj.get("types", [])] != expected:
        out.append(("types", f"stored differ from derived {expected}"))
    for t in obj.get("types", []):
        if t["span"] != obj["span"]:
            out.append(("types", "type span is not the object span"))
    out.extend(_kinds(obj, texts, entry_text))
    out.extend(_shape(obj))
    for path, address in _addresses(obj):
        for target in address["targets"]:
            rec = records.get(target.get("record")) if target.get("record") else None
            if target.get("record") and (
                not rec or rec["address"] != target["normalized"]
            ):
                out.append(("address", f"{path}: target {target['record']}"))
    low, high = YEAR_BOUNDS[record["volume"]]
    for path, v in _values(obj):
        if (
            path.split(".")[-1].startswith(("year", "years"))
            and type(v["value"]) is int
        ):
            if not (low <= v["value"] <= high):
                out.append(("year", f"{path}: {v['value']}"))
    return out


def _shape(obj: dict) -> list[tuple[str, str]]:
    out = []
    reference = any(t["value"] == "reference" for t in obj.get("types", []))
    head = obj.get("subject") or any(
        r["rule"].startswith(("p03.head-", "p03.credit"))
        and r["span"][0] < (obj.get("title") or {}).get("span", [0])[0]
        for p in obj.get("persons", [])
        for r in p["roles"]
    )
    for path, v in _values(obj):
        val, field = v["value"], re.sub(r"\[\d+\]", "", path).split(".")[-1]
        if not isinstance(val, str):
            continue
        # A title moved into a host is checked like the object's own title.
        host_title = bool(re.fullmatch(r"(?:hosts|periodicals)\[\d+\]\.title", path))
        if field in ("title", "subtitle"):
            if DATE_ONLY.match(val):
                out.append(("shape", f"{path}: a date"))
            elif (
                (path == "title" and obj["part"] == "K")
                or (host_title and obj["part"] != "K")
            ) and SIGLUM_ONLY.match(val):
                # Main-volume titles stand in capitals ("AMOK"); in letters a
                # capital word before a colon names a repository. A host in
                # capitals is a periodical siglum, except in letters, which
                # cite their editions by siglum ("KA2 SIGL, pp. 6-7").
                out.append(("shape", f"{path}: a siglum"))
            elif EDITION_ONLY.match(val):
                out.append(("shape", f"{path}: an edition statement"))
            elif (path == "title" or host_title) and (
                CODE_START.match(val) or ISSUE_ONLY.match(val)
            ):
                # A title that opens with a section code or names an issue
                # cites a host or an issue.
                out.append(("shape", f"{path}: a code or an issue"))
            elif (path == "title" or host_title) and CITATION_TAIL.search(val):
                out.append(("shape", f"{path}: holds an imprint or pages"))
            elif host_title and (NAME_LIST.match(val) or NAME_LEAD.match(val)):
                # A host title is no list of names and opens with no inverted
                # name sentence ("Surname, Forename. Title").
                out.append(("shape", f"{path}: names"))
            elif (
                path == "title"
                and v["rule"] == "p03.title"
                and not reference
                and not head
                and INVERTED_NAME.match(val)
            ):
                # A quoted title may be an inverted name (a lexicon article
                # "Zweig, Stefan"); an unquoted one with no head read before
                # it is a missed head name.
                out.append(("shape", f"{path}: an inverted name"))
        elif (
            field == "date"
            and path.startswith("periodicals")
            and not re.search(r"\d", val)
            and not (
                path != "periodicals[0].date"
                and any(re.fullmatch(MONTHS, s, re.I) for s in (val, val + "."))
            )
        ):
            # A continued issue "No. 8 (Aug.)" may give the month alone.
            out.append(("shape", f"{path}: no digit"))
        elif field == "pages" and not PAGES_SHAPE.search(val):
            out.append(("shape", f"{path}: no page"))
        elif field == "place" and (re.search(r"\d", val) or SIGLUM_ONLY.match(val)):
            out.append(("shape", f"{path}: no place"))
        elif field == "name" and (re.search(r"\d", val) or len(val) > 80):
            out.append(("shape", f"{path}: no name"))
        elif field == "publisher" and (
            CREDIT_WORD.search(val) or len(val) > 120 or EXTENT_IN.search(val)
        ):
            out.append(("shape", f"{path}: a credit, an extent or a sentence"))
    return out


def _verbatim(path: str, v: dict, passage: str) -> list[tuple[str, str]]:
    val, field = v["value"], path.split(".")[-1]
    field = re.sub(r"\[\d+\]$", "", field)
    if isinstance(val, bool):
        ok = (
            (passage[:1] in "[(" and passage[-1:] in "])")
            if "bracketed" in field
            else passage == "ca."
        )
        return [] if ok else [("verbatim", f"{path}: flag passage")]
    if isinstance(val, int):
        return [] if passage == str(val) else [("verbatim", f"{path}: year passage")]
    if path.endswith(("types", "kind")) or re.search(r"types\[\d+\]$", path):
        return []
    if re.search(r"roles\[\d+\]$", path):
        if v["rule"] in HEAD_ROLES:
            return (
                []
                if HEAD_ROLES[v["rule"]] == val
                else [("verbatim", f"{path}: head role")]
            )
        word = passage.rstrip(".").lower()
        return (
            []
            if ROLE_WORDS.get(word) == val
            else [("verbatim", f"{path}: role word '{word}'")]
        )
    if path.endswith("language"):
        return (
            []
            if LANGUAGE_BY_FOLD.get(passage.lower()) == val
            else [("verbatim", f"{path}: language")]
        )
    return (
        [] if passage == val else [("verbatim", f"{path}: text differs from passage")]
    )


def _kinds(obj: dict, texts: dict, entry_text: str) -> list[tuple[str, str]]:
    out = []
    relation = obj.get("relation")
    if relation:
        k = relation["kind"]
        text = texts.get(k.get("from")) if k.get("from") else entry_text
        a, b = k["span"]
        if k["rule"] == "p03.relation-label":
            m = SPLIT_LABEL.match(text, a)
            if not m or _label_kind(m) != k["value"]:
                out.append(("kind", "relation label"))
        elif k["value"] != "item" or not (
            ITEM.match(text, a) or text[a:b].strip() in ("in", "") or ":" in text[a:b]
        ):
            out.append(("kind", "relation item"))
    for i, ref in enumerate(obj.get("references", [])):
        k = ref["kind"]
        a, b = k["span"]
        passage = entry_text[a:b]
        if k["rule"] == "p03.reference-marker":
            m = MARKER.fullmatch(passage + " ") or MARKER.search(passage)
            if not m or marker_kind(m.group("marker")) != k["value"]:
                out.append(("kind", f"references[{i}] marker"))
        elif k["rule"] == "p03.reference-inline" and (
            k["value"] != "related" or k["span"] != ref["address"]["span"]
        ):
            out.append(("kind", f"references[{i}] inline"))
    return out


def _addresses(node, path=""):
    if isinstance(node, dict):
        if "targets" in node and "address" in node:
            yield path, node
        for key, child in node.items():
            yield from _addresses(child, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for i, child in enumerate(node):
            yield from _addresses(child, f"{path}[{i}]")


COVERAGE_FIELDS = (
    "types",
    "title",
    "subtitle",
    "original_title",
    "variant_titles",
    "subject",
    "language",
    "work_refs",
    "persons",
    "imprints",
    "extent",
    "edition_notes",
    "series",
    "periodicals",
    "hosts",
    "reviewed",
    "event",
    "contents",
    "informants",
    "holdings",
    "notes",
    "references",
    "relation",
)


def _coverage_row(objects: list[dict]) -> dict:
    n = len(objects)
    row: dict = {"objects": n}
    for field in COVERAGE_FIELDS:
        row[field] = (
            round(sum(bool(o.get(field)) for o in objects) / n, 3) if n else None
        )
    for sub in ("place", "publisher", "year"):
        row[f"imprint.{sub}"] = (
            round(
                sum(any(i.get(sub) for i in o.get("imprints", [])) for o in objects)
                / n,
                3,
            )
            if n
            else None
        )
    for role in (
        "author",
        "translator",
        "editor",
        "introduction",
        "afterword",
        "illustrator",
        "contributor",
    ):
        row[f"role.{role}"] = (
            round(
                sum(
                    any(
                        r["value"] == role
                        for p in o.get("persons", [])
                        for r in p["roles"]
                    )
                    for o in objects
                )
                / n,
                3,
            )
            if n
            else None
        )
    row["inherited.language"] = (
        round(
            sum(bool((o.get("inherited") or {}).get("language")) for o in objects) / n,
            3,
        )
        if n
        else None
    )
    row["inherited.any"] = (
        round(sum(bool(o.get("inherited")) for o in objects) / n, 3) if n else None
    )
    return row


def check_item(item: dict, record: dict, records: dict, rules) -> list[tuple[str, str]]:
    """Violations of one apparatus item (_apparatus.py): model, hash, spans,
    rules, verbatim values, index reference kinds and address targets."""
    try:
        ApparatusItem.model_validate(item)
    except ValidationError as error:
        return [
            ("schema", str(error.errors()[0]["loc"]) + " " + error.errors()[0]["msg"])
        ]
    out = []
    text = record["text"]
    if item["entry_sha256"] != record["sha256"] or item["text"] != text:
        out.append(("span", "item text or hash"))
    literal, prefixes = rules
    for path, v in object_values(item):
        a, b = v["span"]
        if v.get("from") or v["by"] not in ("rule", "compiler"):
            out.append(
                ("scope", f"{path}: apparatus values are read from their record")
            )
        if not (0 <= a < b <= len(text)):
            out.append(("span", f"{path}: outside its record"))
            continue
        if not (v["rule"] in literal or v["rule"].startswith(prefixes)):
            out.append(("rule", f"{path}: {v['rule']}"))
        out.extend(_verbatim(path, v, text[a:b]))
    for i, ref in enumerate(item.get("references", [])):
        kind = ref["kind"]
        if kind["value"] != "index" or kind["span"] != ref["address"]["span"]:
            out.append(("kind", f"references[{i}] index"))
    term = item.get("term")
    if term and item.get("references"):
        if term["span"][1] > item["references"][0]["address"]["span"][0]:
            out.append(("scope", "term runs into its first address"))
    for path, address in _addresses(item):
        for target in address["targets"]:
            rec = records.get(target.get("record")) if target.get("record") else None
            if target.get("record") and (
                not rec or rec["address"] != target["normalized"]
            ):
                out.append(("address", f"{path}: target {target['record']}"))
    return out


def lines_outside(records: dict, apparatus: dict) -> tuple[list[str], Counter]:
    """p01 lines no record holds, apart from page furniture, and a line count.

    A record's text is its lines joined, furniture dropped, so each record
    consumes the lines from its first one whose text continues its own
    (whitespace ignored, at most a few foreign lines skipped). An apparatus
    record of a two-column index holds pieces of lines, so its lines count
    as held when all of their text lies in apparatus records of the page.
    """
    squash = re.compile(r"\s+")
    outside, count = [], Counter()
    for volume in VOLUMES:
        lines = annotate(load_lines(volume), volume)
        at = {(ln["page"], ln["line"]): i for i, ln in enumerate(lines)}
        text = [squash.sub("", ln["text"]) for ln in lines]
        held = [False] * len(lines)
        for record in records.values():
            if record["volume"] != volume:
                continue
            i, skipped = at[(record["page"], record["line"])], 0
            rest = squash.sub("", record["text"])
            while rest and i < len(lines) and skipped <= 4:
                if text[i] and rest.startswith(text[i]):
                    held[i], rest, skipped = True, rest[len(text[i]) :], 0
                elif text[i] and text[i].startswith(rest):
                    held[i], rest = True, ""
                elif text[i]:
                    skipped += 1
                i += 1
        pages: dict[int, str] = {}
        for record in apparatus.values():
            if record["volume"] == volume:
                for page in range(record["page"], record["page_end"] + 1):
                    pages[page] = pages.get(page, "") + squash.sub("", record["text"])
        for i, ln in enumerate(lines):
            if not text[i]:
                continue
            count["lines"] += 1
            if ln["kind"] in ("index", "front", "tail"):
                if apparatus_furniture(ln):
                    count["furniture"] += 1
                    continue
                # The pieces of a line stand in reading order of their column.
                pieces = [squash.sub("", p["text"]) for p in segments(ln, None)]
                held[i] = all(p in pages.get(ln["page"], "") for p in pieces)
            elif ln["furniture"]:
                count["furniture"] += 1
                continue
            if not held[i]:
                outside.append(f"{volume}/p{ln['page']}l{ln['line']}")
    return outside, count


def load_apparatus() -> dict:
    found = {}
    for volume in VOLUMES:
        path = RECORDS / f"apparatus-{volume}.jsonl"
        with path.open(encoding="utf-8") as source:
            for record in map(json.loads, source):
                found[record["id"]] = record
    return found


def load_all() -> tuple[dict, dict, dict]:
    records, order, texts = {}, {}, {}
    for volume in VOLUMES:
        with (RECORDS / f"entries-{volume}.jsonl").open(encoding="utf-8") as source:
            for n, record in enumerate(map(json.loads, source)):
                records[record["id"]] = record
                order[record["id"]] = (volume, n)
                texts[record["id"]] = record["text"]
    return records, order, texts


def validate() -> tuple[dict, list[dict]]:
    records, order, texts = load_all()
    rules = _known_rules()
    known = (
        json.loads(EXCEPTIONS.read_text(encoding="utf-8"))
        if EXCEPTIONS.exists()
        else {}
    )
    violations: list[dict] = []
    by_type: dict = defaultdict(list)
    for record in records.values():
        for obj in record["objects"]:
            for invariant, detail in check_object(
                obj, record, texts, records, order, rules
            ):
                violations.append(
                    {"object": obj["id"], "invariant": invariant, "detail": detail}
                )
            types = [t["value"] for t in obj.get("types", [])] or ["(none)"]
            by_type[(record["volume"], "_all")].append(obj)
            for t in types:
                by_type[(record["volume"], t)].append(obj)
    apparatus = load_apparatus()
    items: Counter = Counter()
    for record in apparatus.values():
        for item in record["objects"]:
            items[(record["volume"], record["kind"])] += 1
            for invariant, detail in check_item(item, record, records, rules):
                violations.append(
                    {"object": item["id"], "invariant": invariant, "detail": detail}
                )
    outside, line_count = lines_outside(records, apparatus)
    violations.extend(
        {"object": line, "invariant": "lines", "detail": "held by no record"}
        for line in outside
    )
    listed = {
        (inv, oid)
        for inv, cases in known.items()
        if not inv.startswith("_")
        for oid in cases
    }
    found = {(v["invariant"], v["object"]) for v in violations}
    new = sorted(found - listed)
    stale = sorted(listed - found)
    coverage: dict = defaultdict(dict)
    for (volume, t), objects in sorted(by_type.items()):
        coverage[volume][t] = _coverage_row(objects)
    report = {
        "about": "Schema validation and invariants over all print objects; coverage is "
        "the share of objects holding a field, a reading rate, not correctness.",
        "objects": sum(len(r["objects"]) for r in records.values()),
        "apparatus_items": {f"{v}/{k}": n for (v, k), n in sorted(items.items())},
        "lines": dict(line_count),
        "lines_outside_records": len(outside),
        "violations": dict(Counter(v["invariant"] for v in violations)),
        "violations_listed": len(found & listed),
        "violations_new": len(new),
        "exceptions_stale": len(stale),
        "coverage": coverage,
    }
    return report, violations, new, stale


def main() -> int:
    report, violations, new, stale = validate()
    write_report("p10_validate", report)
    with (REPORT_DIR / "p10_violations.jsonl").open("w", encoding="utf-8") as sink:
        for v in violations:
            sink.write(json.dumps(v, ensure_ascii=False) + "\n")
    print(
        f"OK {report['objects']} objects, "
        f"{sum(report['apparatus_items'].values())} apparatus items, "
        f"{report['lines']['lines']} lines of which {report['lines_outside_records']} "
        f"outside every record; violations {report['violations']}"
    )
    for invariant, oid in new[:20]:
        print(f"NEW {invariant} {oid}")
    for invariant, oid in stale[:20]:
        print(f"STALE {invariant} {oid}")
    if new or stale:
        print(f"FEHLER {len(new)} new violations, {len(stale)} stale exceptions")
        return 1
    print("OK every violation is a listed exception")
    return 0


if __name__ == "__main__":
    sys.exit(main())
