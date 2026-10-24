"""Seed the question log with the data-cleaning questions the strand has found.

The questions come from the open questions of knowledge/print-volumes.md, the
open cases of the apparatus reading, the rule gaps and source defects listed in
known_exceptions.json and the open classes of the fifth review. They are asked
by an LLM agent (the session that wrote this script), so each is a proposal: a
category and answerer as the agent sees them, sometimes a proposed answer, and
cases found by the probes below, which are candidates, not a census. A person
answers in the viewer. Each question has a stable key, so a rerun adds only
questions not yet asked. No print text stands here; cases are identifiers.

Usage: python -m uv run python pipeline/print_volumes/questions_seed.py [--log PATH]
"""

import argparse
import json
import re
import sys
from pathlib import Path

import _questions
from _common import DERIVED_DIR
from _questions import Case, QuestionIn, append, load_log, object_ids, problem, stamp

RECORDS = DERIVED_DIR / "records"
EXCEPTIONS = Path(__file__).with_name("known_exceptions.json")
AUTHOR = "print strand session"

# Probes over the index items; candidates for a person to look at.
NOTE_AFTER_NUMBER = re.compile(r"\d\s?\[(?:No\.|See )")
FOUR_DIGITS = re.compile(r"(?<![A-Za-z])([A-KM-R]) ?(\d{4})(?!\d)")
RANGE = re.compile(r"(?<!\d)(\d{1,4})-(\d{1,4})(?!\d)")
RANGE_LIMIT = 60


def index_items():
    for path in sorted(RECORDS.glob("apparatus-*.jsonl")):
        with path.open(encoding="utf-8") as source:
            for line in source:
                for o in json.loads(line)["objects"]:
                    if o["kind"] == "index":
                        yield o


def probes() -> dict[str, list[Case]]:
    found = {"note": [], "four": [], "range": [], "heading": []}
    for o in index_items():
        text = o["text"]
        read = " ".join(r["address"]["value"] for r in o.get("references", []))
        if NOTE_AFTER_NUMBER.search(text):
            found["note"].append(Case(object=o["id"]))
        if any(m.group(2) not in read for m in FOUR_DIGITS.finditer(text)):
            found["four"].append(Case(object=o["id"]))
        if any(
            int(m.group(2)) - int(m.group(1)) > RANGE_LIMIT and m.group(0) not in read
            for m in RANGE.finditer(text)
        ):
            found["range"].append(Case(object=o["id"]))
        letters = sum(ch.isalpha() for ch in text)
        if not o.get("references") and text.upper() == text and letters > 5:
            found["heading"].append(Case(object=o["id"], path="term"))
    return found


def exceptions(match) -> list[Case]:
    shape = json.loads(EXCEPTIONS.read_text(encoding="utf-8"))["shape"]
    return [
        Case(object=oid, note=reason[:300])
        for oid, reason in sorted(shape.items())
        if match(reason)
    ]


def questions() -> list[dict]:
    found = probes()
    return [
        {
            "key": "index-note-after-number",
            "category": "notation",
            "answerer": "operator",
            "text": "Does a bracketed note after an index number, an item number or a"
            " 'See' reference, name a target of its own?",
            "proposal": "A bracketed full address ('See' with section and number) is"
            " a target of its own; an item number is a note on the target before it.",
            "cases": found["note"],
        },
        {
            "key": "index-four-digit-addresses",
            "category": "reading",
            "answerer": "data-analysis",
            "text": "Are four-digit numbers after a section letter other than L in"
            " the indexes addresses the grammar should read, or years and pages?",
            "proposal": "Read them as addresses where that section has an entry of"
            " that number; list the rest.",
            "cases": found["four"],
        },
        {
            "key": "index-wide-ranges",
            "category": "reading",
            "answerer": "data-analysis",
            "text": f"Is an index range wider than {RANGE_LIMIT} numbers one printed"
            " range or a misread?",
            "cases": found["range"],
        },
        {
            "key": "index-headings-as-entries",
            "category": "boundary",
            "answerer": "data-analysis",
            "text": "Index headings of the main volume are read as index entries"
            " with a term. Should they be records of their own kind?",
            "proposal": "Read them as headings, like the part headings of the"
            " entries, so that no term holds a heading.",
            "cases": found["heading"],
        },
        {
            "key": "index-a-strips",
            "category": "boundary",
            "answerer": "printed-copy",
            "text": "Does joining each vertical strip of Index A to the entry open"
            " where it begins match the printed book?",
        },
        {
            "key": "known-rule-gaps",
            "category": "reading",
            "answerer": "data-analysis",
            "text": "The listed rule gaps of the shape checks: fix each at its rule,"
            " or keep it as a listed exception?",
            "cases": exceptions(lambda r: "rule gap" in r),
        },
        {
            "key": "substitute-font-defects",
            "category": "source",
            "answerer": "operator",
            "text": "Values with a substitute-font defect read as a digit: keep them"
            " verbatim as printed, or record the intended letter as a correction?",
            "proposal": "Keep the value verbatim and add a correction in the review"
            " layer, so the rule value stays bound to its passage.",
            "cases": exceptions(lambda r: "substitute-font" in r),
        },
        {
            "key": "a2-language-headings-glued",
            "category": "boundary",
            "answerer": "data-analysis",
            "text": "Addendum II: language headings glued to the first entry after"
            " them (fifth review). Which rule separates them?",
        },
        {
            "key": "lost-hosts",
            "category": "reading",
            "answerer": "data-analysis",
            "text": "Contributions whose host is not read (fifth review): where is"
            " the host printed, and which rule reaches it?",
        },
        {
            "key": "forename-first-host-authors",
            "category": "reading",
            "answerer": "data-analysis",
            "text": "Host authors named forename first are read as the host title"
            " (fifth review). Which rule tells them apart?",
            "cases": exceptions(lambda r: "forename first" in r),
        },
        {
            "key": "main-k-letter-editions",
            "category": "model",
            "answerer": "operator",
            "text": "Letter editions in section K of the main volume: one object per"
            " edition, or letters as contents of one edition (fifth review)?",
        },
        {
            "key": "starred-references",
            "category": "notation",
            "answerer": "domain-expert",
            "text": "What does an asterisk after a reference address mean?",
        },
        {
            "key": "section-d-end",
            "category": "source",
            "answerer": "printed-copy",
            "text": "Section D of the main volume ends at 223 while the transcribed"
            " contents give 227, and an erratum of Addendum I corrects D 224. Which"
            " entries does the file lack?",
        },
        {
            "key": "main-volume-state",
            "category": "source",
            "answerer": "printed-copy",
            "text": "Which state of the main volume does the file represent, given"
            " the insertions after 1991?",
        },
        {
            "key": "missing-abbreviations",
            "category": "notation",
            "answerer": "data-analysis",
            "text": "Does the open-access bibliography of 1965 resolve the sigla of"
            " the main volume that its abbreviation list lacks?",
        },
        {
            "key": "unnumbered-units",
            "category": "model",
            "answerer": "operator",
            "text": "Do unnumbered units, collection headers and commentary"
            " paragraphs in E, become entries of their own or context of the"
            " following entries?",
        },
        {
            "key": "post-1991-insertions",
            "category": "concordance",
            "answerer": "data-analysis",
            "text": "How do the insertions after 1991 in the main volume relate to"
            " Addendum I and to the wiki?",
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log", type=Path, default=_questions.LOG)
    args = parser.parse_args()
    log_path = args.log.resolve()
    log = load_log(log_path)
    ids = object_ids(RECORDS)
    added = 0
    for q in questions():
        event = QuestionIn(event="ask", author=AUTHOR, by="agent", **q)
        reason = problem(event, log, ids)
        if reason == "a question with this key exists":
            continue
        if reason:
            raise ValueError(f"{q['key']}: {reason}")
        stored = stamp(event)
        append(stored, log_path)
        log.append(stored)
        added += 1
    print(f"OK {added} questions added, {len(log)} events in {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
