"""p03: turn the segmented print volumes into entry records and structured objects.

Reads the p01 lines, segments them with _segment.py and writes one record per
unit to data/print/derived/records/entries-<volume>.jsonl, following the record
model in knowledge/print-wiki-merge.md:

- entry: volume, part, page and line of its first line, printed address,
  kind (entry, reference, heading), unaltered text, its SHA-256, and the
  heading context it stands under (the latest headings of its part)
- objects: what the entry describes (_objects.object_parts), each a structured
  print object of _schema.py: every value cut from the entry text with its
  span, its producer and its rule (_fields.py); values from a collection
  header, a work or language heading or the head of a letter or review entry
  stand apart under "inherited" and name their record. A cross-reference unit
  is one object of type reference, a collection header an object of type
  collection.

Identifiers are stable as long as the p01 lines are: a numbered entry is
"<volume>/<part>/<number><suffix>" with "~2" for a repeated number, an
unnumbered unit "<volume>/<part>/p<page>l<line>", an object "<entry>#<n>".
Addresses resolve to entry identifiers through one index over all three
volumes. Empty means not found, never inferred; field accuracy is measured
separately (p07, p08, p09) and the schema and invariants are checked by p10.

Output: records per volume, pipeline/print_volumes/schema/print-object.schema.json
(versioned, no print text) and data/print/derived/reports/p03_records.json.

Usage: python -m uv run python pipeline/print_volumes/p03_records.py [--out DIR]
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from _addresses import REFERENCE
from _common import DERIVED_DIR, HERE, SECTIONS, VOLUMES, load_lines, write_report
from _fields import (
    EDITION_LINE,
    LANGUAGE_BY_FOLD,
    NUMBER_PREFIX,
    Reader,
    derive_types,
    inherit,
    language_value,
    place_lexicon,
    text_value,
    value,
)
from _lines import annotate
from _llm import apply_cache, load_cache
from _objects import SPLIT_LABEL, object_parts, unit_kind, unit_text
from _schema import json_schema
from _segment import body_by_part, units, votes

RECORDS = DERIVED_DIR / "records"
SCHEMA_FILE = HERE / "schema" / "print-object.schema.json"
# Collected works are the only part documented to group volumes under a header.
COLLECTION_PARTS = ("A",)
REFERENCE_HEADING = re.compile(r"\bSee\b")
SECTION_HEADING = re.compile(r"^[A-Z]{1,3}\d? / ")
# Form and genre headings inside a language group ("INDIVIDUAL STORIES",
# "SELECTED WORKS", "NEWSPAPER ARTICLES") and citation lines set as headings
# do not end the group.
FORM_HEADING = re.compile(
    r"^(?:INDIVIDUAL|SELECTED|COLLECTED|BOOKS|PERIODICAL|NEWSPAPER|ADDENDUM"
    r"|EXCERPTS?|UPDATED|REPRINTS?|REVIEWS?|CONTENTS|BOXED|VOLUMES)\b|\d",
    re.IGNORECASE,
)
REVIEWS_HEADING = re.compile(r"^REVIEWS?\b")
LETTERS_HEADING = re.compile(r"^(?:INDIVIDUAL|COLLECTED) LETTERS\b|^REPOSITORIES\b")
WORK_WITH_ADDRESS = re.compile(r"^[^\[\]]{3,}\s\[(?:See )?[A-R](?:A[12])? ?\d")
LANGUAGE_WORD = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)?")
EXTENT_YEAR = re.compile(r"\d+(?:/\(?\d+\)?)?p\. \[?(1[5-9]\d\d|20[0-2]\d)\b")
OWN_IMPRINT = re.compile(r"\S: [A-Z][^.;:\[\]]{1,60}, [\[(]?(1[5-9]|20)\d\d|\bVerlag\b")


def _language_in(heading: dict) -> tuple[int, int, str] | None:
    for m in LANGUAGE_WORD.finditer(heading["text"]):
        if m.group().lower() in LANGUAGE_BY_FOLD:
            return m.start(), m.end(), LANGUAGE_BY_FOLD[m.group().lower()]
    return None


def _label_span(text: str) -> tuple[int, int]:
    a, b = 0, len(text)
    while a < b and text[a] in "* .":
        a += 1
    while b > a and text[b - 1] in "* .:":
        b -= 1
    return a, b


def _address(volume: str, part: str, line: dict) -> str:
    number, suffix = line["start"]
    code = part + SECTIONS["volumes"][volume]["suffix"]
    return f"{code} {number}{suffix}"


def _soft_heading(unit: list[dict], text: str, kind: str, parts: list) -> bool:
    """A one-line unnumbered unit without objects is a heading set in mixed case
    ("Spanish", "Marsyas und Apoll" in the Arial headings of B to E)."""
    return (
        kind == "entry"
        and not parts
        and len(unit) == 1
        and not unit[0]["start"]
        and len(text) <= 60
        and bool(re.search(r"[^\W\d_]{3}", text))
    )


def segment(volume: str) -> list[dict]:
    """Records of one volume with object spans and the context each object reads."""
    lines = annotate(load_lines(volume), volume)
    records: list[dict] = []
    seen: Counter = Counter()
    for part, body in body_by_part(lines).items():
        votes(body)
        headings: list[str] = []
        collection: dict | None = None
        work: dict | None = None
        scope: list[dict] = []
        # The numbered entry that edition lines continue ("110 SCHACHNOVELLE."
        # before "111 Publisher: ...").
        lead: str | None = None
        for unit in units(body):
            first = unit[0]
            text = unit_text(unit)
            kind = unit_kind(unit, text)
            if first["start"]:
                key = f"{volume}/{part}/{first['start'][0]}{first['start'][1]}"
                address = _address(volume, part, first)
            else:
                key = f"{volume}/{part}/p{first['page']}l{first['line']}"
                address = ""
            seen[key] += 1
            if seen[key] > 1:
                key = f"{key}~{seen[key]}"
            parts = object_parts(text, part, kind)
            if _soft_heading(unit, text, kind, parts):
                kind = "heading"
            if kind == "reference":
                parts = [{"span": (0, len(text)), "label": None}]
            record = {
                "id": key,
                "volume": volume,
                "part": part,
                "page": first["page"],
                "line": first["line"],
                "page_end": unit[-1]["page"],
                "address": address,
                "kind": kind,
                "text": text,
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "context": list(headings[-3:]),
                "_parts": parts,
                "_work": work,
                "_scope": list(scope),
                "_collection": None,
                "_lead": None,
            }
            records.append(record)
            if first["start"] and kind == "entry":
                number = NUMBER_PREFIX.match(text)
                rest = text[number.end() if number else 0 :]
                letters = re.findall(r"[^\W\d_]", rest[:20])
                if EDITION_LINE.match(rest):
                    record["_lead"] = lead
                elif letters and sum(c.isupper() for c in letters) >= 0.8 * len(
                    letters
                ):
                    # The main volume sets the edition a line continues in
                    # capitals ("110 SCHACHNOVELLE."); a mixed-case line that
                    # opens with a publisher is itself an edition line.
                    lead = key
            if kind == "heading":
                lead = None
                headings.append(text)
                heading = {"id": key, "text": text}
                label = text.strip("* .")
                if SECTION_HEADING.match(label) or LETTERS_HEADING.match(label):
                    # A section or a division of the letters (collected,
                    # individual, repositories) ends every language group.
                    work, scope = None, [heading]
                elif WORK_WITH_ADDRESS.search(label):
                    # "ADAM LUX [E 5 / EA1 1 / NA1 1]" names the reviewed or
                    # translated work by its addresses.
                    work, scope = heading, [heading]
                elif REFERENCE_HEADING.search(label):
                    # A cross-reference set as heading points to another
                    # work; it heads no editions but stays in its group.
                    work = None
                elif len(re.sub(r"[^A-Za-z]", "", REFERENCE.sub(" ", label))) < 4:
                    # An address list under the work heading ("D 29 / H 37,
                    # 113") keeps the work it follows.
                    pass
                elif (
                    _language_in(heading)
                    and len(label.split()) <= 4
                    or FORM_HEADING.search(label)
                ):
                    # A language heading groups translations under the work.
                    scope.append(heading)
                else:
                    work, scope = heading, [heading]
                continue
            if (
                not first["start"]
                and parts
                and part in COLLECTION_PARTS
                and OWN_IMPRINT.search(text)
            ):
                # An unnumbered unit with its own imprint heads the numbered
                # volumes that follow it (collection header).
                record["collection"] = True
                collection = record
            elif collection and first["start"]:
                record["_collection"] = collection
    return records


def _heading_reader(heading: dict, index: dict) -> Reader:
    entry = {"id": heading["id"], "text": heading["text"], "address": "", "part": ""}
    return Reader(entry, (0, len(heading["text"])), {"index": index})


def _inherited(
    record: dict, obj: dict, span, ctx: dict, index: dict, heads: dict
) -> dict:
    inherited: dict = {}
    scope = record["_scope"]
    for heading in reversed(scope):
        found = _language_in(heading)
        if found:
            a, b, _ = found
            inherited["language"] = language_value(
                heading["text"],
                a,
                b,
                "p03.language-heading",
                by="inherited",
                source=heading["id"],
            )
            break
    lead = record["_lead"]
    if (
        ctx.get("edition_line")
        and not obj.get("title")
        and lead
        and heads.get(f"title:{lead}")
    ):
        inherited["title"] = inherit(heads[f"title:{lead}"], lead)
    work = record["_work"]
    if work:
        a, b = _label_span(work["text"])
        cut = re.search(r"\s[\[(]", work["text"][a:b])
        title_end = a + cut.start() if cut else b
        if ctx.get("edition_line") and not obj.get("title"):
            inherited["title"] = text_value(
                work["text"],
                a,
                title_end,
                "p03.work-heading",
                by="inherited",
                source=work["id"],
            )
        if record["part"] == "M":
            # A review heading names the reviewed work.
            inherited["subject"] = text_value(
                work["text"],
                a,
                title_end,
                "p03.review-heading",
                by="inherited",
                source=work["id"],
            )
        refs = _heading_reader(work, index).addresses(0, len(work["text"]))
        if refs:
            inherited["work_refs"] = inherit(refs, work["id"])
    collection = record["_collection"]
    # Only the volume itself inherits from its header, not its later printings.
    if (
        collection
        and not obj.get("relation")
        and not obj.get("imprints")
        and not OWN_IMPRINT.search(record["text"][span[0] : span[1]])
    ):
        header = heads.get(collection["id"])
        if header:
            for key in ("imprints", "persons"):
                if header.get(key):
                    inherited[key] = inherit(header[key], collection["id"])
            if header.get("title"):
                inherited["series"] = [
                    {"title": inherit(header["title"], collection["id"])}
                ]
    if span[0] > 0 and record["part"] in ("K", "M"):
        head_end = record["_head_end"]
        head = record["text"][:head_end]
        reader = Reader(record, (0, head_end), {"index": index})
        pos = reader._prefixes(0)
        name_end = re.search(r"\s\[|\s\(|\.\s|:\s|$", head[pos:])
        subject = text_value(
            record["text"],
            pos,
            pos + name_end.start(),
            "p03.entry-head",
            by="inherited",
            source=record["id"],
        )
        if (
            subject
            and re.search(r"[^\W\d_]{3}", subject["value"])
            and not LANGUAGE_BY_FOLD.get(subject["value"].lower())
            and not subject["value"].startswith("See")
        ):
            inherited["subject"] = subject
        refs = reader.addresses(0, head_end)
        if refs:
            inherited.setdefault("work_refs", []).extend(inherit(refs, record["id"]))
    return {k: v for k, v in inherited.items() if v}


def _relation(record: dict, n: int, span, label, first_id: str | None) -> dict | None:
    if not label:
        return None
    a, b, kind = label
    source = record["id"] if b <= span[0] else None
    rule = (
        "p03.relation-label"
        if SPLIT_LABEL.match(record["text"], a)
        else "p03.relation-item"
    )
    relation = {"kind": value(kind, a, b, rule, source=source)}
    if first_id and n > 1:
        relation["target"] = first_id
    return relation


def structure(
    records: list[dict],
    index: dict,
    llm_cache: dict,
    stats_llm: Counter,
    places: frozenset[str] = frozenset(),
) -> None:
    """Fill every record's objects with the structured fields."""
    heads: dict[str, dict] = {}
    for record in records:
        parts = record.pop("_parts")
        record["_head_end"] = parts[0]["span"][0] if parts else 0
        objects = []
        first_id = None
        for n, part in enumerate(parts, start=1):
            span = part["span"]
            nxt = parts[n]["span"][0] if n < len(parts) else len(record["text"])
            ctx = {
                "index": index,
                "places": places,
                "next_object_start": nxt,
                "label_kind": part["label"][2] if part["label"] else None,
            }
            if record["_work"]:
                ctx["work"] = record["_work"]["id"]
            for heading in reversed(record["_scope"]):
                found = _language_in(heading)
                if found:
                    ctx["language"] = found[2]
                    break
            fields = Reader(record, span, ctx).run()
            obj = {
                "id": f"{record['id']}#{n}",
                "entry": record["id"],
                "entry_sha256": record["sha256"],
                "volume": record["volume"],
                "part": record["part"],
                "address": record["address"],
                "span": list(span),
                "text": record["text"][span[0] : span[1]],
                **fields,
            }
            if not obj.get("imprints"):
                year = EXTENT_YEAR.search(record["text"], span[0], span[1])
                if year and not obj.get("periodicals") and not obj.get("hosts"):
                    # A volume whose imprint stands in its collection header
                    # gives its year after the extent ("757/(3)p. 1983").
                    obj["imprints"] = [
                        {
                            "year": value(
                                int(year.group(1)),
                                year.start(1),
                                year.end(1),
                                "p03.extent-year",
                            )
                        }
                    ]
            relation = _relation(record, n, span, part["label"], first_id)
            if relation:
                obj["relation"] = relation
            elif n == 1:
                first_id = obj["id"]
            inherited = _inherited(record, obj, span, ctx, index, heads)
            if inherited:
                obj["inherited"] = inherited
            # Offsets a model proposed fill only what neither the rules nor
            # the inheritance filled, as proposals (_llm.py).
            if apply_cache(obj, llm_cache):
                stats_llm[record["volume"]] += 1
            # A REVIEWS heading holds until the next language heading; the
            # reviews of one language do not make the next language's articles
            # reviews.
            last_review = max(
                (
                    i
                    for i, h in enumerate(record["_scope"])
                    if REVIEWS_HEADING.match(h["text"].strip("* "))
                ),
                default=-1,
            )
            last_language = max(
                (i for i, h in enumerate(record["_scope"]) if _language_in(h)),
                default=-1,
            )
            if last_review > last_language:
                record["reviews_heading"] = True
            types = derive_types(obj, record)
            if types:
                obj["types"] = [
                    value(t, span[0], span[1], f"p03.type-{t}") for t in types
                ]
            objects.append(obj)
        if record.get("collection") and objects:
            heads[record["id"]] = objects[0]
        if objects and objects[0].get("title") and not objects[0].get("relation"):
            heads[f"title:{record['id']}"] = objects[0]["title"]
        record["objects"] = objects
        for key in ("_work", "_scope", "_collection", "_head_end", "_lead"):
            record.pop(key)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=RECORDS,
        help="records directory; another one is a trial run that leaves records, "
        "schema and report in place (for comparing a refactoring by diff)",
    )
    args = parser.parse_args()
    trial = args.out.resolve() != RECORDS.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    SCHEMA_FILE.parent.mkdir(exist_ok=True)
    if not trial:
        SCHEMA_FILE.write_text(
            json.dumps(json_schema(), ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
    by_volume = {volume: segment(volume) for volume in VOLUMES}
    index: dict[str, str] = {}
    for records in by_volume.values():
        for record in records:
            if record["address"] and record["kind"] != "heading":
                index.setdefault(record["address"], record["id"])
    places = place_lexicon(r["text"] for rs in by_volume.values() for r in rs)
    report = {}
    llm_cache = load_cache()
    stats_llm: Counter = Counter()
    for volume, records in by_volume.items():
        structure(records, index, llm_cache, stats_llm, places)
        out = args.out / f"entries-{volume}.jsonl"
        tmp = out.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as sink:
            for record in records:
                sink.write(json.dumps(record, ensure_ascii=False) + "\n")
        tmp.replace(out)
        kinds = Counter(r["kind"] for r in records)
        objects = [o for r in records for o in r["objects"]]
        report[volume] = {
            "units": len(records),
            **dict(kinds),
            "numbered": sum(bool(r["address"]) for r in records),
            "objects": len(objects),
            "objects_inheriting": sum(1 for o in objects if o.get("inherited")),
            "objects_with_llm_proposals": stats_llm[volume],
        }
        print(
            f"OK {volume}: {len(records)} units, {kinds['entry']} entries, "
            f"{kinds['reference']} references, {kinds['heading']} headings, "
            f"{len(objects)} objects"
        )
    if trial:
        print(f"OK trial records in {args.out}")
        return 0
    path = write_report("p03_records", report)
    print(f"OK schema {SCHEMA_FILE}")
    print(f"OK report {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
