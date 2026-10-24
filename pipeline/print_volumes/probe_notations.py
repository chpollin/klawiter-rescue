"""Probe: which notations do the objects use, how often, per volume and part?

The inventory behind the field rules of p03 (knowledge/print-volumes.md, Entry
anatomy). Every notation is a regular expression counted once per object text
in which it occurs; units of kind reference count as their own column. Held-out
records (_heldout.py) are left out, so that the counts guide rule development
without exposing the benchmark or the blind sample. The counts locate a
notation; they do not measure a rule.

Output: data/print/derived/reports/probe_notations.json.

Usage: python -m uv run python pipeline/print_volumes/probe_notations.py
"""

import json
import re
import sys
from collections import Counter, defaultdict

from _common import DERIVED_DIR, VOLUMES, write_report
from _heldout import is_held_out

RECORDS = DERIVED_DIR / "records"
MONTH = r"(?:Jan|Feb|Mar|Apr|May|June?|July?|Aug|Sept?|Oct|Nov|Dec)[a-z]*\.?"
NOTATIONS = {
    "role:Tr.": r"\bTr\.",
    "role:Trl.": r"\bTrls?\.",
    "role:Translated by": r"\b[Tt]ranslated (?:\w+ )*by\b",
    "role:Ed.": r"\bEds?\.",
    "role:Edited by": r"\b[Ee]dited (?:\w+ )*by\b",
    "role:Intro.": r"\bIntro\.",
    "role:Frw./Pref.": r"\b(?:Frw|Pref)\.|\bForeword by\b|\bPreface by\b",
    "role:Aftw.": r"\bAftw\.|\b[Aa]fterword by\b",
    "role:Illus.": r"\bIllus\. [A-Z]|\b[Ii]llustrat(?:ed|ions) by\b",
    "role:Comp./Sel.": r"\b(?:Comp|Sel)\.|\b(?:Compiled|Selected) by\b",
    "role:Cover": r"\bCover(?: design| illustration)?(?: by)? [A-Z]",
    "role:combined": r"\b(?:Tr|Trl|Ed|Comp|Sel)\.?/[A-Z][a-z]+\.",
    "film:Dir.": r"\bDir\. [A-Z]",
    "imprint": r"[A-Z][\w.'’/ -]{1,40}: [^.;:\[\]]{2,60}?, [\[(]?(?:1[5-9]|20)\d\d",
    "imprint:bracketed-year": r": [^.;:\[\]]{2,60}?, [\[(](?:1[5-9]|20)\d\d[\])]",
    "imprint:several": r"\d\d / [A-Z][\w.'’ -]{1,40}: ",
    "edition-line": r"^\d*\s*[A-Z][^:.\[\]]{1,60}?: [\[(]?\d",
    "periodical:vol-issue": r"\d{1,3}:\d{1,4}[a-z]? [(\[]",
    "periodical:date": rf"\b\d{{1,2}}\.? {MONTH} (?:1[89]|20)\d\d\b",
    "periodical:siglum": r"(?<![\w-])[A-ZÄÖÜÉ]{4,8}, \d",
    "periodical:in-title-place": r"\bin [A-Z][^\[(]{2,80} \([A-Z][\w /.-]+\), ",
    "host:in-address": r"\bin\b[^\[]{2,120}\[[A-R](?:A[12])? ?\d{1,4}",
    "host:in-collection": r"\bin [A-Z][^\"“”]{2,120}\. Ed\. ",
    "extent:pages": r"\b\d+(?:/\(?\[?\d+\]?\)?)*\s?p\.",
    "extent:roman": r"\b[ivxlc]+/\d+",
    "extent:vols": r"\b\d+ vols\.",
    "extent:leaves": r"\b\d+ leaves\b",
    "extent:illus": r"\billus\.|\bIllustrated\b|\bport\.",
    "edition:Tsd.": r"\bTsd\.",
    "edition:Auflage": r"\bAuflage\b|\bimpr\.|\bimprs?\b",
    "edition:ed.": r"\b(?:\d+(?:st|nd|rd|th)|New|Rev\.|Large print|Pktbk\.) ed\.",
    "edition:Expl./copies": r"\bExpl\.|\bcopies\b",
    "edition:licensed": r"\bLic(?:\.|ensed) ed|\bLizenzausgabe\b",
    "edition:reprint": r"\[(?:Rep|REP)\.? \d{4}|\bReprinted \d{4}",
    "label:FIE": r"\bFIE\s?:",
    "label:Rep:": r"\b(?:Rep|REP)\s?:",
    "label:REV:": r"\bREV(?: VERSION)?\s?:",
    "label:EXC": r"\bEXC(?:ERPTS?)?\b",
    "label:Contents": r"\bCon-?\s?tents\s?:|\bContains\s?:",
    "label:Fischer Editions": r"Editions/Reprints\s?:",
    "label:Reprinted in": r"\bReprinted in\b",
    "series:paren": r"\d{4}[\])]? \([A-Z][^()]{2,60}, \d+\)",
    "series:bracket": r"\d{4}[\])]? \[[A-Z][^\[\]]{2,60}, \d+\]",
    "work-ref": r"\[(?:[A-R](?:A[12])? \d{1,4}[a-z]?)(?:[,/ ]+[A-R]?(?:A[12])? ?\d{1,4})*[\].]",
    "original-title": r"\[Orig\.|\[[^\]]{3,80}\. (?:Paris|London|Leipzig|Berlin|Bruxelles), \d{4}",
    "informant": r"\[[A-Z]{2,4}(?:/[A-Z]{2,4})?\]\.?\s*$|\[[A-Z]{2,4}\]",
    "repository": r"\b[A-Z]{2,5}: (?:Zweig|[A-Z][\w-]+) to\b",
    "auction": r"\b(?:Katalog|Auktion|Auction|Liste)\b",
    "manuscript": r"\b(?:typescript|manuscript|Typeschrift|Manuscript)\b",
    "event": r"\bPremiere\b|\bSymposium\b|\bExhibition\b|\bAusstellung\b|\bLesung\b|\breading\b",
}
COMPILED = {k: re.compile(v) for k, v in NOTATIONS.items()}


def main() -> int:
    report: dict = {}
    for volume in VOLUMES:
        counts: dict[str, Counter] = defaultdict(Counter)
        with (RECORDS / f"entries-{volume}.jsonl").open(encoding="utf-8") as source:
            for record in map(json.loads, source):
                if record["kind"] == "heading" or is_held_out(record):
                    continue
                part = record["part"]
                texts = (
                    [record["text"]]
                    if record["kind"] == "reference"
                    else [o["text"] for o in record["objects"]]
                )
                counts[part]["units"] += 1
                counts[part][f"{record['kind']}_objects"] += len(texts)
                for text in texts:
                    for name, pattern in COMPILED.items():
                        if pattern.search(text):
                            counts[part][name] += 1
        report[volume] = {part: dict(c) for part, c in sorted(counts.items())}
        total = Counter()
        for c in counts.values():
            total.update(c)
        report[volume]["_all"] = dict(total)
    path = write_report("probe_notations", report)
    print(f"OK report {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
