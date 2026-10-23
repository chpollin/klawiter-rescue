"""Prepare the lab data under docs/lab/data/ (milestone L3 of knowledge/lab-frontend.md).

Data flow: a committed snapshot (default `HEAD`) of the published data is read
through Git, never from the working tree, so that a regeneration running in
parallel cannot mix two states. With `--worktree` the same files are read from
disk instead; use it only after the published data is stable.

Inputs: docs/data/klawiter.json, docs/data/publications/<id>.json,
docs/data/reconciliation.json, data/output/verification-report.json,
data/reconciliation/location-decisions.json, the provenance block of
data/provenance/llm-enrichment-cache.json and docs/js/constants.js.

Outputs in docs/lab/data/: meta.json, pages/<pageId>.json, works.json,
coverage.json, history/<pageId>.json, reference-records.json, report.json.
Every file carries `dataState`, the input commit and a content hash over the
inputs, so a citation can name the data state. Outputs hold no timestamps, so
two runs over the same snapshot are byte-identical.

Usage:
    python -m uv run python pipeline/lab/prepare_lab_data.py [--ref HEAD]
    python -m uv run python pipeline/lab/prepare_lab_data.py --worktree

Regime: flat script pipeline. The script is not part of the production run and
writes only to docs/lab/data/. Rules live in lab_rules.py and lab_works.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from lab_rules import (
    BOUNDARY_FIELDS,
    LABEL_MAPPING_NOTE,
    RULES_VERSION,
    Passage,
    boundary_check,
    link_sentence,
    normalise_title,
    parse_zweig_author_types,
    producer_label,
    value_occurrences,
)
from lab_works import build_works

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "lab" / "data"

KLAWITER = "docs/data/klawiter.json"
PUBLICATIONS_DIR = "docs/data/publications/"
RECONCILIATION = "docs/data/reconciliation.json"
VERIFICATION = "data/output/verification-report.json"
LOCATION_DECISIONS = "data/reconciliation/location-decisions.json"
LLM_CACHE = "data/provenance/llm-enrichment-cache.json"
CONSTANTS = "docs/js/constants.js"
FIXED_INPUTS = (
    KLAWITER,
    RECONCILIATION,
    VERIFICATION,
    LOCATION_DECISIONS,
    LLM_CACHE,
    CONSTANTS,
)

RECORD_FIELDS = (
    "title",
    "year",
    "publisher",
    "location",
    "language",
    "translator",
    "pageCount",
)
COVERAGE_FIELDS = (
    "year",
    "publisher",
    "location",
    "language",
    "translator",
    "pageCount",
)
VERIFICATION_FIELDS = {
    "publisher": "publisher",
    "location": "location",
    "translator": "translator",
    "pageCount": "page_count",
}
ORIGIN_LABELS = {
    "regex": "rule",
    "llm": "LLM gap fill",
    "editor": "editor",
    "missing": "no value recorded",
}
NO_VALUE_NOTE = (
    "no value recorded, a gap in the source and a value not extracted are not "
    "yet distinguished"
)
VERIFICATION_NOTE = (
    "the automatic check did not find this value in the raw text; the check "
    "covers page-level values only"
)
SEVERAL_YEARS_NOTE = (
    "the page has no publication breakdown and records several years, so its "
    "values may come from different publications"
)
EXTRA_LANGUAGE_WORDS = frozenset(
    "czechoslovakian rumanian romanian slovakian slovene byelorussian belarusian "
    "flemish latvian lithuanian icelandic macedonian malayalam tamil marathi "
    "gujarati kannada telugu punjabi sinhala sinhalese nepali mongolian kazakh "
    "kyrgyz kirghiz tajik turkmen uzbek uyghur uighur azerbaijani azeri tatar "
    "basque galician breton welsh irish luxembourgish frisian latin maltese "
    "kurdish pashto burmese khmer lao malay tagalog filipino swahili amharic "
    "oriya odia assamese sanskrit tibetan faroese sorbian romani bosnian "
    "occitan montenegrin moldavian malagasy belorussian aramaic chuvash "
    "karakalpak romansh faeroese egyptian tunisian".split()
) | frozenset({"telgu", "potuguese"})  # compiler spellings in the Translations sections
SUFFIX_WORDS = frozenset("volume volumes german essay essays film films".split())


@dataclass(frozen=True)
class Snapshot:
    ref: str
    commit: str
    worktree: bool
    files: dict[str, bytes]
    inputs_sha256: str

    def json(self, path: str):
        return json.loads(self.files[path].decode("utf-8"))

    def state(self) -> dict:
        return {
            "ref": "WORKTREE" if self.worktree else self.ref,
            "commit": self.commit,
            "worktree": self.worktree,
            "inputsSha256": self.inputs_sha256,
            "inputsSha256Short": self.inputs_sha256[:12],
            "rulesVersion": RULES_VERSION,
        }


# Reading the snapshot


def _git(*args: str, data: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, input=data, capture_output=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.decode()}")
    return result.stdout


def _cat_files(ref: str, paths: list[str]) -> dict[str, bytes]:
    """Read many blobs of one ref through a single `git cat-file --batch`."""
    request = "".join(f"{ref}:{p}\n" for p in paths).encode("utf-8")
    raw = _git("cat-file", "--batch", data=request)
    files, pos = {}, 0
    for path in paths:
        header_end = raw.index(b"\n", pos)
        header = raw[pos:header_end].decode()
        if header.endswith("missing"):
            raise FileNotFoundError(f"{ref}:{path} is missing")
        size = int(header.split()[2])
        start = header_end + 1
        files[path] = raw[start : start + size]
        pos = start + size + 1
    return files


def inputs_hash(files: dict[str, bytes]) -> str:
    """SHA-256 over path, length and bytes of every input, in path order."""
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.encode("utf-8") + b"\0")
        digest.update(str(len(files[path])).encode() + b"\0")
        digest.update(files[path])
    return digest.hexdigest()


def read_snapshot(ref: str, worktree: bool) -> Snapshot:
    commit = _git("rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()
    if worktree:
        pub_paths = sorted(
            f"{PUBLICATIONS_DIR}{p.name}"
            for p in (ROOT / PUBLICATIONS_DIR).glob("*.json")
        )
        paths = [*FIXED_INPUTS, *pub_paths]
        files = {p: (ROOT / p).read_bytes() for p in paths}
    else:
        listing = _git("ls-tree", "-r", "--name-only", ref, "--", PUBLICATIONS_DIR)
        pub_paths = sorted(
            p for p in listing.decode("utf-8").splitlines() if p.endswith(".json")
        )
        files = _cat_files(ref, [*FIXED_INPUTS, *pub_paths])
    return Snapshot(ref, commit, worktree, files, inputs_hash(files))


def read_baseline(snapshot: Snapshot) -> tuple[str | None, str | None, dict | None]:
    """The published records before the last change of klawiter.json.

    In ref mode the baseline is the parent of the last commit that changed
    klawiter.json, so the history shows what the latest regeneration changed.
    In worktree mode it is the committed state at HEAD.
    """
    if snapshot.worktree:
        changed_in, base = "WORKTREE", snapshot.commit
    else:
        log = _git("log", "-n", "1", "--format=%H", snapshot.ref, "--", KLAWITER)
        changed_in = log.decode().strip()
        if not changed_in:
            return None, None, None
        try:
            base = _git("rev-parse", "--verify", f"{changed_in}^").decode().strip()
        except RuntimeError:
            return changed_in, None, None
    data = json.loads(_cat_files(base, [KLAWITER])[KLAWITER].decode("utf-8"))
    pages = {
        e["sourcePageId"]: e for e in data["entries"] if e.get("pageNamespace") == 0
    }
    return changed_in, base, pages


# Context derived once from the snapshot


@dataclass
class Context:
    pages: dict[int, dict]
    pubs: dict[int, list]
    redirects: dict[str, int]
    verification: dict[int, dict]
    decisions: dict[str, dict]
    claims_by_place: dict[str, list]
    claims_by_page: dict[int, list]
    llm: dict
    zweig_types: frozenset[str]
    places: frozenset[str]
    suffix_words: frozenset[str]
    language_words: frozenset[str]
    duplicate_subjects: list[str]


def build_context(snap: Snapshot) -> Context:
    data = snap.json(KLAWITER)
    pages = {
        e["sourcePageId"]: e for e in data["entries"] if e.get("pageNamespace") == 0
    }
    pubs = {}
    for path, raw in snap.files.items():
        if path.startswith(PUBLICATIONS_DIR):
            side = json.loads(raw.decode("utf-8"))
            pubs[int(side["sourcePageId"])] = side.get("publications") or []

    verification = {
        r["page_id"]: r["fields"] for r in snap.json(VERIFICATION)["detailed_results"]
    }
    decisions, duplicates = {}, []
    for decision in snap.json(LOCATION_DECISIONS)["decisions"]:
        subject = decision["subject"]
        if subject in decisions:
            duplicates.append(subject)
        decisions.setdefault(subject, decision)

    recon = snap.json(RECONCILIATION)
    claims_by_place: dict[str, list] = defaultdict(list)
    claims_by_page: dict[int, list] = defaultdict(list)
    for claim in recon.get("contestedClaims", []) + recon.get("decidedClaims", []):
        subject = claim.get("subject") or {}
        if claim.get("entityType") == "location":
            claims_by_place[subject.get("name")].append(claim)
        elif claim.get("entityType") == "source-revision":
            page = str(subject.get("@id", "")).rsplit("/", 1)[-1]
            if page.isdigit():
                claims_by_page[int(page)].append(claim)

    llm = snap.json(LLM_CACHE).get("provenance", {})
    llm_meta = {k: llm.get(k) for k in ("model", "promptSha256", "frozenAt")}

    zweig = frozenset(parse_zweig_author_types(snap.files[CONSTANTS].decode("utf-8")))
    languages = {e.get("language") for e in pages.values() if e.get("language")}
    language_words = (
        frozenset(w.split()[0].casefold() for w in languages) | EXTRA_LANGUAGE_WORDS
    )
    suffix_words = SUFFIX_WORDS | {w.casefold() for w in languages}

    place_names = set()
    for entry in pages.values():
        for key in ("location",):
            if entry.get(key):
                place_names.add(entry[key])
        place_names.update(entry.get("allLocations") or [])
        place_names.update(entry.get("publicationPlaces") or [])
    for publications in pubs.values():
        for pub in publications:
            place_names.update(pub.get("places") or [])
    for subject in recon.get("locations", {}):
        # Candidate labels stay out: unreviewed candidates include non-places.
        place_names.add(subject)
    for decision in decisions.values():
        place_names.add(decision["subject"])
        if decision.get("label"):
            place_names.add(decision["label"])
    places = frozenset(normalise_title(p) for p in place_names if p)

    return Context(
        pages=pages,
        pubs=pubs,
        redirects=data.get("redirects") or {},
        verification=verification,
        decisions=decisions,
        claims_by_place=claims_by_place,
        claims_by_page=claims_by_page,
        llm=llm_meta,
        zweig_types=zweig,
        places=places,
        suffix_words=suffix_words,
        language_words=language_words,
        duplicate_subjects=duplicates,
    )


# Page files (prototype 1)


def passages_of(publications: list[dict]) -> list[Passage]:
    out = []
    for pub in publications:
        sl = pub.get("sourceSlice") or {}
        out.append(
            Passage(pub["id"], pub.get("year"), sl.get("textStart"), sl.get("textEnd"))
        )
    return out


def place_decision(
    ctx: Context, place: str | None, snapshot_link: str | None = None
) -> dict | None:
    """State and producer of the place's Wikidata link, with the decision record."""
    if not place:
        return None
    decision = ctx.decisions.get(place)
    claims = [claim_view(c) for c in ctx.claims_by_place.get(place, [])]
    if decision is None:
        return {
            "place": place,
            "state": None,
            "sentence": "Wikidata link: no decision recorded, no link",
            "decision": None,
            "claims": claims,
        }
    label = producer_label(decision)
    qid = decision.get("qid")
    return {
        "place": place,
        "state": label["state"],
        "producer": label["producer"],
        "link": label["link"],
        "qid": qid,
        "sentence": link_sentence(qid, label),
        "labelMapping": "provisional",
        "scopeNote": (
            "The decision applies to the Wikidata identity of the place name on "
            "every page that carries it, not to its assignment to a publication."
        ),
        "decision": {
            "decisionId": decision.get("decisionId"),
            "storedAction": decision.get("action"),
            "decider": decision.get("decidedBy"),
            "basis": decision.get("provenance"),
            "evidence": decision.get("evidence") or [],
            "date": decision.get("decidedAt") or "no date recorded",
            "supersedes": (decision.get("supersedes") or {}).get("decisionId"),
        },
        # Only the page-level record carries a published link in the snapshot.
        **({"snapshotPublishesLink": snapshot_link} if snapshot_link else {}),
        "claims": claims,
    }


def claim_view(claim: dict) -> dict:
    """Readings side by side with evidence lines and review history."""
    evidence = [
        {
            "pageId": e.get("sourcePageId"),
            "line": e.get("sourceLine"),
            "text": e.get("sourceText"),
            "matchMode": e.get("sourceMatchMode"),
        }
        for e in claim.get("sourceEvidence") or []
    ]
    return {
        "claimId": claim.get("claimId"),
        "entityType": claim.get("entityType"),
        "status": claim.get("claimStatus"),
        "decisionStatus": claim.get("decisionStatus"),
        "readings": [
            {
                "label": i.get("label"),
                "object": (i.get("proposedObject") or {}).get("@id")
                if isinstance(i.get("proposedObject"), dict)
                else i.get("proposedObject"),
                "status": i.get("status"),
            }
            for i in claim.get("interpretations") or []
        ],
        "evidence": evidence,
        "reviewHistory": [
            {
                "action": r.get("action") or r.get("outcome"),
                "decider": r.get("decidedBy") or r.get("reviewer"),
                "basis": r.get("basis"),
                "date": r.get("decidedAt") or "no date recorded",
                "evidence": r.get("evidence") or [],
            }
            for r in claim.get("reviewHistory") or []
        ],
    }


def _field(value, origin: str | None) -> dict:
    origin = origin or ("missing" if value in (None, "") else None)
    return {
        "value": value,
        "origin": origin,
        "originLabel": ORIGIN_LABELS.get(origin, origin),
        **({"note": NO_VALUE_NOTE} if value in (None, "") else {}),
    }


def publication_view(
    ctx: Context, pub: dict, text: str, passages: list[Passage]
) -> dict:
    prov = pub.get("provenance") or {}
    sl = pub.get("sourceSlice") or {}
    own = {pub["id"]}

    def located(value, origin_key: str) -> dict:
        row = _field(value, prov.get(origin_key))
        if value not in (None, ""):
            row["occurrences"] = value_occurrences(text, value, passages, own)
        return row

    translators = [
        c["name"] for c in pub.get("credits") or [] if c.get("role") == "translator"
    ]
    fields = {
        "publisher": located(pub.get("publisher"), "publisher"),
        "places": [located(p, "places") for p in pub.get("places") or []],
        "translators": [located(t, "credits") for t in translators],
        "extent": located((pub.get("extent") or {}).get("raw"), "extent"),
        "language": _field(pub.get("language"), prov.get("language")),
        "editionStatement": _field(
            pub.get("editionStatement"), prov.get("editionStatement")
        ),
        "series": _field(pub.get("series"), prov.get("series")),
    }
    return {
        "id": pub["id"],
        "year": pub.get("year"),
        "yearRaw": pub.get("yearRaw"),
        "title": pub.get("title"),
        "imprint": pub.get("imprint"),
        "editionId": pub.get("editionId"),
        "reviewStatus": pub.get("reviewStatus"),
        "editionAssignment": (
            f"edition assignment: {pub.get('reviewStatus')}"
            + ("" if pub.get("editionId") else ", outside the Gate 1 corpus")
        ),
        "textStart": sl.get("textStart"),
        "textEnd": sl.get("textEnd"),
        "passageLocated": sl.get("textStart") is not None,
        "sourceSliceSha256": sl.get("sha256"),
        "sourceSliceNote": (
            "computed over raw text the site does not publish, so a browser "
            "cannot verify it"
        ),
        "fields": fields,
        "placeDecisions": [place_decision(ctx, p) for p in pub.get("places") or []],
        "reviewFlags": pub.get("reviewFlags") or [],
    }


def page_view(ctx: Context, pid: int, membership: dict) -> dict:
    entry = ctx.pages[pid]
    text = entry.get("fullBibliographicEntry") or ""
    publications = ctx.pubs.get(pid) or []
    passages = passages_of(publications)
    prov = entry.get("_provenance") or {}
    year_ids = {p.pub_id for p in passages if p.year == entry.get("year")}
    verification = ctx.verification.get(pid, {})

    record = {}
    for field in RECORD_FIELDS:
        value = entry.get(field)
        row = _field(value, prov.get(field))
        if field in BOUNDARY_FIELDS and value not in (None, ""):
            row["occurrences"] = value_occurrences(text, value, passages, year_ids)
            vfield = VERIFICATION_FIELDS[field]
            if (verification.get(vfield) or {}).get("status") == "false_positive":
                row["verificationNote"] = VERIFICATION_NOTE
        record[field] = row

    check = boundary_check(
        text, entry.get("year"), passages, {f: entry.get(f) for f in BOUNDARY_FIELDS}
    )
    for field, result in check.get("fields", {}).items():
        record[field]["boundary"] = result

    years = entry.get("allYears") or []
    claims = [claim_view(c) for c in ctx.claims_by_page.get(pid, [])]
    return {
        "pageId": pid,
        "title": entry["title"],
        "entryType": entry["entryType"],
        "language": entry.get("language"),
        "languageCode": entry.get("languageCode"),
        "publicationLanguages": entry.get("publicationLanguages") or [],
        "pageKind": entry.get("pageKind"),
        "allYears": years,
        "source": {
            "note": "plain text the pipeline derived from the wiki page",
            "textId": entry.get("sourceTextId"),
            "text": text,
            "restoredRevision": entry.get("sourceRevision"),
            "restoredNote": (
                "the page is published from the last human revision before a "
                "Redirect fixer overwrite"
                if entry.get("sourceRevision")
                else None
            ),
        },
        "publications": [
            publication_view(ctx, p, text, passages) for p in publications
        ],
        "record": {
            "note": (
                "one record for the whole page, used by search and exports; it "
                "can combine values of different publications"
            ),
            "fields": record,
            "yearPublications": sorted(year_ids),
        },
        "boundaryCheck": {k: v for k, v in check.items() if k != "fields"},
        "severalYearsWithoutBreakdown": (
            {"note": SEVERAL_YEARS_NOTE}
            if not publications and len(years) > 1
            else None
        ),
        "placeDecision": place_decision(
            ctx, entry.get("location"), entry.get("locationSameAs")
        ),
        "pageClaims": claims,
        "works": membership.get(pid, []),
    }


# Works, coverage, histories, reference records


def membership_index(works: list[dict]) -> dict[int, list]:
    index: dict[int, list] = defaultdict(list)
    for work in works:
        ref = {"workId": work["workId"], "title": work["title"]}
        for member in work["anchor"]["members"]:
            index[member["pageId"]].append(ref | {"part": "anchor"})
        for pid in work["linkedByCompiler"]["pageIds"]:
            index[pid].append(ref | {"part": "linked by the compiler"})
        for pid in work["citingTitleInBrackets"]["pageIds"]:
            index[pid].append(
                ref | {"part": "cites the title in brackets, lab rule, not reviewed"}
            )
    return index


def coverage(ctx: Context, works: list[dict]) -> dict:
    denominator = sorted(
        p for p, e in ctx.pages.items() if e["entryType"] in ctx.zweig_types
    )
    fields = {}
    for field in COVERAGE_FIELDS:
        recorded, absent, llm = [], [], []
        for pid in denominator:
            entry = ctx.pages[pid]
            if entry.get(field) in (None, ""):
                absent.append(pid)
            else:
                recorded.append(pid)
                if (entry.get("_provenance") or {}).get(field) == "llm":
                    llm.append(pid)
        fields[field] = {
            "valueRecorded": {"count": len(recorded), "pageIds": recorded},
            "noValueRecorded": {
                "count": len(absent),
                "pageIds": absent,
                "note": NO_VALUE_NOTE,
            },
            "llmGapFills": {"count": len(llm), "pageIds": llm},
        }
    false_negatives = {}
    for field, key in (
        ("publisher", "publisher_false_negative"),
        ("translator", "translator_false_negative"),
    ):
        ids = [p for p in denominator if key in ctx.verification.get(p, {})]
        false_negatives[field] = {
            "count": len(ids),
            "pageIds": ids,
            "note": "values the verification stage found in the raw text that the record lacks",
        }
    reached = set()
    for work in works:
        reached |= {m["pageId"] for m in work["anchor"]["members"]}
        reached |= set(work["linkedByCompiler"]["pageIds"])
        reached |= set(work["citingTitleInBrackets"]["pageIds"])
    unreached: dict[str, list] = defaultdict(list)
    for pid in denominator:
        if pid not in reached:
            unreached[ctx.pages[pid]["entryType"]].append(pid)
    reached_in = sorted(reached & set(denominator))
    return {
        "denominator": {
            "unit": "namespace-0 pages whose entry type belongs to ZWEIG_AUTHOR_TYPES",
            "entryTypes": sorted(ctx.zweig_types),
            "count": len(denominator),
            "pageIds": denominator,
        },
        "fields": fields,
        "verificationFalseNegatives": false_negatives,
        "workViews": {
            "reached": {"count": len(reached_in), "pageIds": reached_in},
            "unreachedByEntryType": {
                k: {"count": len(v), "pageIds": v} for k, v in sorted(unreached.items())
            },
        },
    }


def _record_values(entry: dict | None) -> dict:
    if entry is None:
        return {}
    prov = entry.get("_provenance") or {}
    return {
        f: {"value": entry.get(f), "origin": prov.get(f)} for f in RECORD_FIELDS
    } | {"locationSameAs": {"value": entry.get("locationSameAs"), "origin": None}}


def history(ctx: Context, pid: int, page: dict, baseline: tuple) -> dict:
    entry = ctx.pages[pid]
    prov = entry.get("_provenance") or {}
    changed_in, base_commit, base_pages = baseline
    llm_fields = [f for f in RECORD_FIELDS if prov.get(f) == "llm"]
    repaired = [
        f
        for f in entry.get("reviewFlags") or []
        if f.get("code") == "encoding-repaired"
    ]
    after_parse = {
        f: (
            {
                "value": None,
                "note": "empty after the rule stage (implied by the gap-filler contract)",
            }
            if prov.get(f) == "llm"
            else {"value": entry.get(f), "origin": prov.get(f)}
        )
        for f in RECORD_FIELDS
    }
    record = page["record"]["fields"]
    place = page["placeDecision"]
    stages = [
        {
            "stage": 1,
            "name": "Wiki text",
            "actor": "MediaWiki dump, current revision of the page",
            "values": {
                "textId": entry.get("sourceTextId"),
                "textLength": len(entry.get("fullBibliographicEntry") or ""),
                "restoredRevision": entry.get("sourceRevision"),
            },
            "notStored": [
                "the raw wikitext with markup is not published; the lab shows the "
                "plain text the pipeline derived from it",
                "source slice hashes are computed over that raw text and cannot "
                "be verified in a browser",
            ],
        },
        {
            "stage": 2,
            "name": "Repair",
            "actor": "rule (encoding repair)",
            "values": {"encodingRepaired": [f["field"] for f in repaired]},
            "change": bool(repaired),
            "summary": None if repaired else "no change on this record recorded",
            "notStored": ["the text and values before repair are not published"],
        },
        {
            "stage": 3,
            "name": "Parse",
            "actor": "rule",
            "values": after_parse,
            "publications": len(ctx.pubs.get(pid) or []),
            "notStored": [
                "intermediate stage outputs (data/intermediate) are regenerable "
                "and not tracked; the values after this stage are inferred from "
                "the published origins"
            ],
        },
        {
            "stage": 4,
            "name": "Fill gaps",
            "actor": f"LLM {ctx.llm.get('model')}, answers frozen on {ctx.llm.get('frozenAt')}",
            "promptTemplateSha256": ctx.llm.get("promptSha256"),
            "values": {f: record[f] for f in llm_fields},
            "change": bool(llm_fields),
            "summary": None if llm_fields else "no change on this record",
            "notStored": [
                "per-record prompt and raw response not stored, prompt template hash recorded"
            ],
        },
        {
            "stage": 5,
            "name": "Link places",
            "actor": (place or {}).get("producer") or "no decision",
            "values": place,
            "notStored": (
                ["no decision date recorded"]
                if place
                and (place.get("decision") or {}).get("date") == "no date recorded"
                else []
            ),
        },
        {
            "stage": 6,
            "name": "Published record",
            "actor": "pipeline stages 05 and 06, patch replay",
            "values": {
                f: {
                    k: record[f].get(k)
                    for k in ("value", "origin", "verificationNote", "boundary")
                    if k in record[f]
                }
                for f in RECORD_FIELDS
            },
            "editorFields": [f for f in RECORD_FIELDS if prov.get(f) == "editor"],
        },
    ]
    changes = []
    if base_pages is not None:
        before, after = _record_values(base_pages.get(pid)), _record_values(entry)
        for field in after:
            if before.get(field) != after.get(field):
                changes.append(
                    {
                        "field": field,
                        "before": before.get(field),
                        "beforeCommit": base_commit,
                        "after": after.get(field),
                        "afterCommit": changed_in,
                    }
                )
    stages[-1]["changesSinceBaseline"] = changes
    stages[-1]["baseline"] = {
        "commit": base_commit,
        "changedIn": changed_in,
        "note": (
            "baseline is the published data before the last commit that changed "
            "docs/data/klawiter.json"
            if base_commit
            else "no baseline available"
        ),
    }
    return {"pageId": pid, "title": entry["title"], "stages": stages}


def select_reference_records(ctx: Context, page_views: dict[int, dict]) -> dict:
    fires, several, contested = [], [], []
    for pid in sorted(page_views):
        view = page_views[pid]
        fields = view["record"]["fields"]
        firing = [
            f for f in BOUNDARY_FIELDS if (fields[f].get("boundary") or {}).get("fires")
        ]
        if view["publications"] and firing and pid != 448:
            rule_firing = any(fields[f]["origin"] == "regex" for f in firing)
            fires.append((not rule_firing, len(view["publications"]), pid))
        if view["severalYearsWithoutBreakdown"]:
            recorded = sum(
                1 for f in BOUNDARY_FIELDS if fields[f]["value"] not in (None, "")
            )
            several.append((-recorded, pid))
        place = view["placeDecision"]
        if (
            place
            and fields["location"]["origin"] == "regex"
            and any(c["status"] == "contested" for c in place["claims"])
        ):
            contested.append((pid,))
    fires.sort()
    several.sort()

    def pick(rows: list, rule: str) -> dict:
        return {
            "pageId": rows[0][-1] if rows else None,
            "selectionRule": rule,
            "candidates": {"count": len(rows), "pageIds": sorted(r[-1] for r in rows)},
        }

    return {
        "classes": {
            "breakdownBoundaryFires": pick(
                fires,
                "page with a publication breakdown whose boundary check fires; a "
                "rule-extracted firing value first, then fewest publications, "
                "then lowest page id; page 448 excluded as it is listed apart",
            ),
            "noBreakdownSeveralYears": pick(
                several,
                "page without a publication breakdown carrying several years; most "
                "recorded boundary fields first, then lowest page id",
            ),
            "contestedPlaceRuleValue": pick(
                contested,
                "page whose rule-extracted place has an open contested claim; lowest page id",
            ),
        },
        "page448": {
            "pageId": 448,
            "reason": "the case changed by the October pipeline fixes",
        },
    }


# Report


def bracket_check(works: list[dict], reference_titles: list[str]) -> list[dict]:
    rows = []
    rng = random.Random(0)
    by_key = {w["titleKey"]: w for w in works}
    for key in reference_titles:
        work = by_key.get(key)
        if work is None:
            rows.append({"titleKey": key, "work": None})
            continue
        rel3 = work["citingTitleInBrackets"]
        hits = [
            {
                "pageId": r["pageId"],
                "title": r["title"],
                "bracket": r["bracket"],
                "entryType": r["entryType"],
            }
            for langs in rel3["byEntryType"].values()
            for group in langs.values()
            for r in group["rows"]
        ]
        hits.sort(key=lambda r: r["pageId"])
        sample = sorted(rng.sample(hits, min(10, len(hits))), key=lambda r: r["pageId"])
        rows.append(
            {
                "titleKey": key,
                "workId": work["workId"],
                "hits": len(hits),
                "alsoLinked": rel3["alsoLinkedCount"],
                "hitsByEntryType": {
                    t: sum(g["count"]["pages"] for g in langs.values())
                    for t, langs in rel3["byEntryType"].items()
                },
                "excludedByClass": {
                    k: v["count"] for k, v in rel3["excludedBrackets"].items()
                },
                "possiblySameTitle": [
                    {
                        "pageId": r["pageId"],
                        "title": r["title"],
                        "bracket": r["bracket"],
                    }
                    for r in rel3["possiblySameTitle"]["rows"]
                ],
                "sampleForManualReview": sample,
                "linkedByCompilerPages": work["linkedByCompiler"]["count"]["pages"],
                "linkedNotCitingInBrackets": len(
                    set(work["linkedByCompiler"]["pageIds"]) - set(rel3["pageIds"])
                ),
            }
        )
    return rows


def boundary_counts(page_views: dict[int, dict]) -> dict:
    fired = Counter()
    fired_pages: dict[str, list] = defaultdict(list)
    not_run = Counter()
    ran = 0
    for pid, view in sorted(page_views.items()):
        check = view["boundaryCheck"]
        if not view["publications"]:
            continue
        if not check["run"]:
            not_run[check["reason"]] += 1
            continue
        ran += 1
        for field in BOUNDARY_FIELDS:
            if (view["record"]["fields"][field].get("boundary") or {}).get("fires"):
                fired[field] += 1
                fired_pages[field].append(pid)
    return {
        "pagesWithBreakdown": sum(1 for v in page_views.values() if v["publications"]),
        "checkRan": ran,
        "checkNotRunByReason": dict(sorted(not_run.items())),
        "firesByField": {
            f: {"pages": fired[f], "pageIds": fired_pages[f]} for f in BOUNDARY_FIELDS
        },
    }


# Writing


def write_json(path: Path, payload: dict, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload,
        ensure_ascii=False,
        indent=None if compact else 1,
        separators=(",", ":") if compact else None,
    )
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text + "\n", encoding="utf-8")
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--ref", default="HEAD", help="Git ref to read the inputs from")
    parser.add_argument(
        "--worktree",
        action="store_true",
        help="read the inputs from the working tree instead of a Git ref",
    )
    parser.add_argument("--out", type=Path, default=OUT, help="output directory")
    args = parser.parse_args(argv)

    snap = read_snapshot(args.ref, args.worktree)
    state = snap.state()
    print(
        f"OK snapshot {state['ref']} {snap.commit[:12]} inputs {state['inputsSha256Short']}"
    )
    ctx = build_context(snap)
    baseline = read_baseline(snap)
    if ctx.duplicate_subjects:
        print(
            f"WARNUNG duplicate decision subjects: {ctx.duplicate_subjects}",
            file=sys.stderr,
        )

    built = build_works(
        ctx.pages,
        ctx.pubs,
        ctx.redirects,
        ctx.zweig_types,
        ctx.places,
        ctx.suffix_words,
        ctx.language_words,
    )
    works = built["works"]
    membership = membership_index(works)

    errors, page_views = [], {}
    for pid in sorted(ctx.pages):
        try:
            page_views[pid] = page_view(ctx, pid, membership)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append({"pageId": pid, "error": f"{type(exc).__name__}: {exc}"})

    out: Path = args.out
    for sub in ("pages", "history"):
        if (out / sub).exists():
            shutil.rmtree(out / sub)
    for pid, view in page_views.items():
        write_json(
            out / "pages" / f"{pid}.json", {"dataState": state, **view}, compact=True
        )

    refs = select_reference_records(ctx, page_views)
    ref_ids = [c["pageId"] for c in refs["classes"].values() if c["pageId"]] + [448]
    for pid in dict.fromkeys(ref_ids):
        write_json(
            out / "history" / f"{pid}.json",
            {"dataState": state, **history(ctx, pid, page_views[pid], baseline)},
        )
    write_json(out / "reference-records.json", {"dataState": state, **refs})

    cov = coverage(ctx, works)
    write_json(out / "coverage.json", {"dataState": state, **cov})
    write_json(
        out / "works.json",
        {
            "dataState": state,
            "rules": {
                "anchor": "VIST page plus German pages of Zweig's own works with the same title key or linked by the VIST page; without a VIST page, German pages of Zweig's own works that are linked or cited in brackets, same-key pages grouped",
                "relation3": "first bracket after the page title on the same line, at most a short subtitle without digits between; NFKC, straight apostrophes, case folding, suffix and genre-word removal on both sides",
                "excludedClasses": [
                    "year-or-number",
                    "several-titles",
                    "place",
                    "english-gloss",
                ],
                "decisionsBeyondSpec": "see the module docstring of pipeline/lab/lab_works.py",
            },
            "works": works,
            "bracketClasses": built["bracketClasses"],
            "unresolvedSeeAlso": built["unresolvedSeeAlso"],
        },
    )

    reference_titles = [
        "ungeduld des herzens",
        "schachnovelle",
        "brief einer unbekannten",
    ]
    report = {
        "dataState": state,
        "bracketRuleCheck": bracket_check(works, reference_titles),
        "bracketClassesGlobal": {
            k: v["count"] for k, v in built["bracketClasses"].items()
        },
        "pagesWithoutTitleBracket": len(ctx.pages) - len(built["brackets"]),
        "boundaryCheck": boundary_counts(page_views),
        "coverage": {
            "denominator": cov["denominator"]["count"],
            "fields": {
                f: {
                    k: v[k]["count"]
                    for k in ("valueRecorded", "noValueRecorded", "llmGapFills")
                }
                for f, v in cov["fields"].items()
            },
            "verificationFalseNegatives": {
                f: v["count"] for f, v in cov["verificationFalseNegatives"].items()
            },
            "workViewsReach": cov["workViews"]["reached"]["count"],
            "unreachedByEntryType": {
                k: v["count"]
                for k, v in cov["workViews"]["unreachedByEntryType"].items()
            },
        },
        "works": {
            "count": len(works),
            "vistAnchors": sum(1 for w in works if w["anchor"]["vist"]),
            "otherAnchors": sum(1 for w in works if not w["anchor"]["vist"]),
        },
        "referenceRecords": {k: v["pageId"] for k, v in refs["classes"].items()}
        | {"page448": 448},
        "translationLabelLinesUnrecognised": [
            line for w in works for line in w["listedAsText"]["unrecognisedLabelLines"]
        ],
        "duplicateDecisionSubjects": ctx.duplicate_subjects,
        "labelMapping": LABEL_MAPPING_NOTE,
        "errors": errors,
    }
    write_json(out / "report.json", report)
    write_json(
        out / "meta.json",
        {
            "dataState": state,
            "inputs": sorted(snap.files),
            "inputsHashRule": "SHA-256 over path, NUL, byte length, NUL and bytes of every input, in path order",
            "llm": ctx.llm,
            "labelMapping": LABEL_MAPPING_NOTE,
            "fixtureDecision": (
                "The twenty decisions of repository-ground-truth-fixture read as "
                "proposed per the operator decision of 2026-10-23, whatever the "
                "snapshot stores."
            ),
            "baseline": {"changedIn": baseline[0], "commit": baseline[1]},
            "counts": {
                "pages": len(page_views),
                "pagesWithBreakdown": sum(
                    1 for v in page_views.values() if v["publications"]
                ),
                "publications": sum(len(v) for v in ctx.pubs.values()),
                "works": len(works),
                "histories": len(dict.fromkeys(ref_ids)),
                "zweigAuthorPages": cov["denominator"]["count"],
            },
        },
    )

    print_report(report)
    if errors:
        print(f"FEHLER {len(errors)} pages failed, see report.json", file=sys.stderr)
        return 1
    print(f"OK wrote {out}")
    return 0


def print_report(report: dict) -> None:
    print("-" * 60)
    for row in report["bracketRuleCheck"]:
        if row.get("workId") is None:
            print(f"WARNUNG no work for {row['titleKey']}", file=sys.stderr)
            continue
        print(
            f"bracket {row['titleKey']}: hits {row['hits']}, also linked "
            f"{row['alsoLinked']}, excluded {row['excludedByClass']}, possibly "
            f"same title {len(row['possiblySameTitle'])}"
        )
    bc = report["boundaryCheck"]
    print(
        f"boundary: breakdown pages {bc['pagesWithBreakdown']}, ran {bc['checkRan']}, "
        f"not run {bc['checkNotRunByReason']}"
    )
    print(
        "boundary fires: "
        + ", ".join(f"{f} {v['pages']}" for f, v in bc["firesByField"].items())
    )
    cov = report["coverage"]
    print(
        f"coverage denominator {cov['denominator']}, work views reach {cov['workViewsReach']}"
    )
    for field, counts in cov["fields"].items():
        print(f"  {field}: {counts}")
    print(f"works {report['works']}, reference records {report['referenceRecords']}")
    print("-" * 60)


if __name__ == "__main__":
    sys.exit(main())
