"""p03: turn the segmented print volumes into entry and object records with fields.

Reads the p01 lines, segments them with _segment.py and writes one record per
unit to data/print/derived/records/entries-<volume>.jsonl, following the record
model in knowledge/print-wiki-merge.md:

- entry: volume, part, page and line of its first line, printed address,
  kind (entry, reference, heading), unaltered text, its SHA-256, and the
  heading context it stands under (the latest headings of its part)
- objects: the publications the entry describes (_objects.split_objects),
  each with rule-based fields: title, author, year, imprint (place,
  publisher), translator, language from the heading context, and, where it
  has no imprint of its own, a link to the collection header whose imprints
  it inherits, kept apart from its own fields

Identifiers are stable as long as the p01 lines are: a numbered entry is
"<volume>/<part>/<number><suffix>" with "~2" for a repeated number, an
unnumbered unit "<volume>/<part>/p<page>l<line>", an object "<entry>#<n>".
Every field is a regex reading of the object text; empty means not found,
never inferred. Field accuracy is measured separately.

Output: records per volume and data/print/derived/reports/p03_records.json.

Usage: python -m uv run python pipeline/print_volumes/p03_records.py
"""

import hashlib
import json
import re
import sys
from collections import Counter

from _addresses import REFERENCE
from _common import DERIVED_DIR, SECTIONS, VOLUMES, load_lines, write_report
from _lines import START_NUMBER, annotate
from _objects import EXTENT_YEAR, split_objects, unit_kind, unit_text
from _segment import body_by_part, units, votes

RECORDS = DERIVED_DIR / "records"
# Collected works are the only part documented to group volumes under a header.
COLLECTION_PARTS = ("A",)
LANGUAGES = frozenset(
    "Albanian Arabic Armenian Azerbaijani Basque Bengali Bosnian Bulgarian "
    "Byelorussian Catalan Chinese Croatian Czech Danish Dutch English Esperanto "
    "Estonian Finnish Flemish French Galician Georgian German Greek Hebrew Hindi "
    "Hungarian Icelandic Indonesian Italian Japanese Kazakh Korean Latvian "
    "Lithuanian Macedonian Malayalam Marathi Moldavian Mongolian Norwegian "
    "Persian Polish Portuguese Romanian Rumanian Russian Serbian Serbo-Croatian "
    "Slovak Slovakian Slovenian Spanish Swedish Tamil Thai Turkish Ukrainian "
    "Urdu Uzbek Vietnamese Yiddish".split()
)
YEAR = re.compile(r"\b(1[5-9]\d\d|20[0-2]\d)\b")
IMPRINT = re.compile(
    r"(?<![\w-])(?P<place>[A-Z][\w.'’/ -]{1,40}?): "
    r"(?P<publisher>(?:[A-Z]\. )?[^.;:\[\]]{2,60}?), "
    r"[\[(]?(?P<year>1[5-9]\d\d|20[0-2]\d)"
)
TRANSLATOR = re.compile(r"\b(?:Tr\.|Trl\.|Translated by)\s*([^.\];]{3,80})")
AUTHOR = re.compile(r"^(?P<author>[A-ZÀ-Þ][^,.\[\]]{1,40}, [A-ZÀ-Þ][^.\[\]]{1,40})\.\s")
# A publisher of the object's own, even where the place was garbled by a
# substitute font ("\"stanbul: Varlik, 1954").
OWN_IMPRINT = re.compile(r"\S: [A-Z][^.;:\[\]]{1,60}, [\[(]?(1[5-9]|20)\d\d|\bVerlag\b")
QUOTED = re.compile(r"[\"“„‘']([^\"”“‘’']{3,200})[\"”“’']")
# An edition line under a work heading opens with its publisher and goes on
# with extent or printing ("Bertelsmann: 383p. Gütersloh, 1952", "S. Fischer:
# 1.-16. Tsd. 593/(1)p. Frankfurt am Main, 1951"); its title is the heading's.
EDITION_LINE = re.compile(
    r"^(?P<publisher>(?:[A-Z]\. )*[A-Z][^:.\[\]]{1,60}?):\s(?=[\[(]?\d)"
)
PLACE_YEAR = re.compile(
    r"(?<![\w-])(?P<place>[A-Z][\w'’/ -]{1,60}?), [\[(]?(?P<year>1[5-9]\d\d|20[0-2]\d)"
)
# A heading that only points elsewhere ("RAHEL RECHTET MIT GOTT. See A 169.")
# heads no editions.
REFERENCE_HEADING = re.compile(r"\bSee\b")
SECTION_HEADING = re.compile(r"^[A-Z]{1,3}\d? / ")
# Form and genre headings inside a language group ("INDIVIDUAL STORIES",
# "SELECTED WORKS", "NEWSPAPER ARTICLES") and citation lines set as headings
# do not end the group.
FORM_HEADING = re.compile(
    r"^(?:INDIVIDUAL|SELECTED|COLLECTED|BOOKS|PERIODICAL|NEWSPAPER|ADDENDUM"
    r"|EXCERPTS?|UPDATED|REPRINTS?|REVIEWS?|CONTENTS)\b|\d"
)
# Headings are set in capitals ("SERBO-CROATIAN"), so languages match folded.
LANGUAGE_BY_FOLD = {name.lower(): name for name in LANGUAGES}


def _language_of(label: str) -> str:
    return LANGUAGE_BY_FOLD.get(label.strip("* .:").lower(), "")


def _language(headings: list[str]) -> str:
    for heading in reversed(headings):
        for word in re.findall(r"[A-Za-z-]+", heading):
            if word.lower() in LANGUAGE_BY_FOLD:
                return LANGUAGE_BY_FOLD[word.lower()]
    return ""


def _title_and_author(text: str) -> tuple[str, str]:
    body = re.sub(r"^\[[^\]]+\]\s?\.\s*", "", text)
    body = START_NUMBER.sub("", body, count=1).strip()
    author = ""
    match = AUTHOR.match(body)
    if match:
        author, body = match.group("author"), body[match.end() :]
    quoted = QUOTED.match(body.strip())
    if quoted:
        return quoted.group(1).strip(), author
    title = re.split(r"\.\s|\s\[|\s\d+(?:/\(?\d+\)?)?p\.", body, maxsplit=1)[0]
    return title.strip(" .")[:200], author


def _fields(text: str, headings: list[str]) -> dict:
    title, author = _title_and_author(text)
    # Address lists ("L 88, 120, 1585") must not yield years or imprints.
    plain = REFERENCE.sub(" ", text)
    imprint = IMPRINT.search(plain)
    year = imprint.group("year") if imprint else None
    if year is None:
        found = YEAR.search(plain)
        year = found.group(1) if found else None
    translator = TRANSLATOR.search(text)
    # The lazy place group can still start inside a preceding sentence.
    place = imprint.group("place").split(". ")[-1].strip() if imprint else ""
    publisher = imprint.group("publisher").strip() if imprint else ""
    body = START_NUMBER.sub("", text, count=1).strip()
    edition = None if imprint else EDITION_LINE.match(body)
    if edition:
        title, publisher = "", edition.group("publisher").strip()
        located = PLACE_YEAR.search(REFERENCE.sub(" ", body[edition.end() :]))
        if located:
            place, year = located.group("place").strip(), located.group("year")
    return {
        "title": title,
        "author": author,
        "year": int(year) if year else None,
        "place": place,
        "publisher": publisher,
        "translator": translator.group(1).strip() if translator else "",
        "language": _language(headings),
    }


def _imprints(text: str) -> str:
    """All imprints of a collection header, as printed ("A: B, 1939-1950 / ...")."""
    plain = REFERENCE.sub(" ", text)
    return " / ".join(
        f"{m.group('place').split('. ')[-1]}: {m.group('publisher')}, {m.group('year')}"
        for m in IMPRINT.finditer(plain)
    )


def _address(volume: str, part: str, line: dict) -> str:
    number, suffix = line["start"]
    code = part + SECTIONS["volumes"][volume]["suffix"]
    return f"{code} {number}{suffix}"


def build(volume: str) -> tuple[list[dict], Counter]:
    lines = annotate(load_lines(volume), volume)
    stats: Counter = Counter()
    records: list[dict] = []
    seen: Counter = Counter()
    for part, body in body_by_part(lines).items():
        votes(body)
        headings: list[str] = []
        collection: dict | None = None
        work: dict | None = None
        scope: list[str] = []
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
            context = list(headings[-3:])
            objects = []
            for n, span in enumerate(split_objects(text, part, kind), start=1):
                # The language comes from headings within the current work or
                # section only; a translation group ends at the next work.
                fields = _fields(span, scope)
                inherited = None
                if (
                    collection
                    and not fields["publisher"]
                    and not OWN_IMPRINT.search(span)
                    and EXTENT_YEAR.search(span)
                ):
                    # Inherited values stay apart from the object's own
                    # reading; a header may carry several imprints by period.
                    inherited = {
                        "from": collection["id"],
                        "imprint": collection["imprint"],
                    }
                elif work and not fields["title"] and fields["publisher"]:
                    # An edition line takes its title from the work heading.
                    inherited = {"from": work["id"], "title": work["title"]}
                objects.append(
                    {
                        "id": f"{key}#{n}",
                        "text": span,
                        "fields": fields,
                        "inherited": inherited,
                    }
                )
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
                "context": context,
                "objects": objects,
            }
            records.append(record)
            stats[kind] += 1
            stats["objects"] += len(objects)
            stats["numbered"] += bool(address)
            stats["objects_inheriting"] += sum(1 for o in objects if o["inherited"])
            if kind == "heading":
                headings.append(text)
                label = text.strip("* .")
                if SECTION_HEADING.match(label):
                    work, scope = None, [text]
                elif REFERENCE_HEADING.search(label):
                    # A cross-reference set as heading points to another
                    # work; it heads no editions but stays in its group.
                    work = None
                elif len(re.sub(r"[^A-Za-z]", "", REFERENCE.sub(" ", label))) < 4:
                    # An address list under the work heading ("D 29 / H 37,
                    # 113") keeps the work it follows.
                    pass
                elif _language_of(label) or FORM_HEADING.search(label):
                    # A language heading groups translations under the work.
                    scope.append(text)
                else:
                    work, scope = {"id": key, "title": label}, [text]
            elif not first["start"] and objects and part in COLLECTION_PARTS:
                # An unnumbered unit with its own imprint heads the numbered
                # volumes that follow it (collection header). Elsewhere an
                # unnumbered unit is an entry of its own, not a header.
                head = objects[0]["fields"]
                collection = (
                    {"id": key, "imprint": _imprints(objects[0]["text"])}
                    if head["publisher"]
                    else collection
                )
    return records, stats


def main() -> int:
    RECORDS.mkdir(parents=True, exist_ok=True)
    report = {}
    for volume in VOLUMES:
        records, stats = build(volume)
        out = RECORDS / f"entries-{volume}.jsonl"
        tmp = out.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as sink:
            for record in records:
                sink.write(json.dumps(record, ensure_ascii=False) + "\n")
        tmp.replace(out)
        objects = [o for r in records for o in r["objects"]]
        filled = Counter(k for o in objects for k, v in o["fields"].items() if v)
        report[volume] = {
            "units": len(records),
            **dict(stats),
            "field_fill": {
                k: round(v / max(1, len(objects)), 3) for k, v in filled.items()
            },
        }
        print(
            f"OK {volume}: {len(records)} units, {stats['entry']} entries, "
            f"{stats['reference']} references, {stats['heading']} headings, "
            f"{stats['objects']} objects ({stats['objects_inheriting']} inheriting)"
        )
    path = write_report("p03_records", report)
    print(f"OK report {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
