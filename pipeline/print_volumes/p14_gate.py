"""p14: the local print gate that a human measurement needs before it can count.

Checks, in this order, each stopping the run when it fails (--keep-going runs
the rest and still fails):

1. inputs: each PDF's SHA-256 starts with its prefix in sections.json, and each
   p01 lines file is p01's output of that PDF: the p01 report names the same
   full hash and its text hash is the hash of the lines file's text.
   leaks: no tracked file under LEAK_SCOPE (knowledge, snapshots, code,
   frontend code, README, CLAUDE.md) repeats LEAK_WORDS consecutive words of
   the print, so a quotation of print text in a versioned file fails whoever
   wrote it.
2. rebuild: p03 writes the entry and apparatus records twice from the same
   inputs, under different hash seeds, into gate/run-a and gate/run-b; every
   records file is byte-identical between the two. The live records are never
   written; whether they equal the rebuild is reported, not checked, because
   p13 already marks a decision on a changed entry as stale.
3. validate: p10 on the rebuilt records, with its line-coverage ledger: no p01
   line outside a record, every violation a listed exception, no stale
   exception.
4. samples: every identifier of each frozen sample (the review sample, its
   hard stratum and second-reviewer subset, both blind samples of p09, both
   benchmark samples, and the claim sheet of p09 once written) exists in the
   rebuilt records. A sample lists its identifiers as they stand now; its
   remap list ("remapped": [{"from", "to", "reason"}], in order) is the only
   admitted way one may change. Undoing the remaps recovers the identifiers as
   frozen, whose hash must equal the sample's pin in sample_pins.json, so that
   an identifier that moved or was replaced without a remap entry fails. The
   blind samples pin each row as well: its sample_id is the hash of the frozen
   identifier. Benchmark identifiers are PDF pages, fixed by the PDF hash; each
   must lie on a rebuilt record; claim identifiers are pinned only, since the
   gate does not rebuild p07.
   An identifier binds what it stood for only through its fingerprint
   (fingerprint): the entry's sha256, for an object with its span. The
   fingerprints as frozen stand in the supplementary sample files, and for the
   two samples frozen before them in sample-fingerprints.json, written once
   from the records by --pin; each set is pinned. A fingerprint that differs in
   the rebuild fails unless the sample's rehash list ("rehashed": [{"id",
   "from", "to", "reason"}], in order) records the change. The supplementary
   files of the review sample (pool sizes) and of the first blind sample
   (stratum sizes) must exist and agree with their samples.
5. export (--export, slow): p12 builds the JSON-LD from the rebuilt records
   twice, into gate/jsonld-a and gate/jsonld-b; both are byte-identical. SHACL
   validation stays with p12.

The run names its inputs with hashes: PDFs, lines files, sections.json, the
known exceptions, the LLM cache, the sample files and pins, the review log
(read by the export), the strand's code and uv.lock, and the git commit.

--pin writes the pin of every sample that has none, from the identifiers as
frozen, and of its fingerprints; it never replaces a pin. A pin changes only
by a reviewed edit of the versioned file.

Output: data/print/derived/gate/p14_gate.json (identifiers and hashes only)
and the rebuilds under data/print/derived/gate/.

Usage: python -m uv run python pipeline/print_volumes/p14_gate.py
       [--export] [--keep-going] [--pin]
"""

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from _common import (
    DERIVED_DIR,
    HERE,
    PRINT_DIR,
    PROJECT_ROOT,
    REPORT_DIR,
    SECTIONS,
    VOLUMES,
    lines_path,
)

GATE = DERIVED_DIR / "gate"
REPORT = GATE / "p14_gate.json"
PINS = HERE / "sample_pins.json"
SAMPLES = DERIVED_DIR / "samples"
REVIEW_SAMPLE = SAMPLES / "review-sample.json"
REVIEW_POOLS = SAMPLES / "review-sample-pools.json"
REVIEW_HARD = SAMPLES / "review-hard-sample.json"
REVIEW_SECOND = SAMPLES / "review-second-subset.json"
BLIND_KEY = SAMPLES / "concordance-blind-key.json"
BLIND_SHEET = SAMPLES / "concordance-blind-sheet.csv"
BLIND_KEY_2 = SAMPLES / "concordance-blind-key-2.json"
BLIND_SHEET_2 = SAMPLES / "concordance-blind-sheet-2.csv"
BLIND_STRATA = SAMPLES / "concordance-blind-strata.json"
CLAIMS_SHEET = SAMPLES / "concordance-claims-sheet.csv"
FINGERPRINTS = SAMPLES / "sample-fingerprints.json"
# The samples every measurement needs; the claim sheet follows the blind round.
REQUIRED = ("review", "review-hard", "review-second", "blind", "blind-2")
BENCH = {
    "bench-v1": DERIVED_DIR / "bench" / "sample.json",
    "bench-v2": DERIVED_DIR / "bench" / "v2" / "sample.json",
}
RECORD_FILES = tuple(
    f"{name}-{volume}.jsonl" for name in ("entries", "apparatus") for volume in VOLUMES
)
RUNS = ("run-a", "run-b")
HASH_SEEDS = ("1", "2")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def lines_text_hash(lines_file: Path, pages: int, skipped: set[int]) -> str:
    """p01's text hash recomputed from its lines file: per page the sha256 of
    its line texts joined by newlines, concatenated in page order. Pages that
    p01 could not read contribute nothing, as in p01."""
    by_page: dict[int, list[str]] = {}
    with lines_file.open(encoding="utf-8") as source:
        for line in map(json.loads, source):
            by_page.setdefault(line["page"], []).append(line["text"])
    hashes = [
        hashlib.sha256("\n".join(by_page.get(p, [])).encode("utf-8")).hexdigest()
        for p in range(1, pages + 1)
        if p not in skipped
    ]
    return hashlib.sha256("".join(hashes).encode()).hexdigest()


def input_failures(
    volumes: dict, pdf_hashes: dict[str, str], p01: dict, text_hashes: dict
) -> list[str]:
    """PDF hash prefixes against sections.json and lines files against p01.

    volumes is the "volumes" table of sections.json, pdf_hashes the full hash
    per volume (absent when the file is missing), p01 the p01 report and
    text_hashes the text hash recomputed from each lines file (absent when the
    file is missing)."""
    failures = []
    for volume, spec in volumes.items():
        full = pdf_hashes.get(volume)
        if full is None:
            failures.append(f"{volume}: {spec['file']} missing")
            continue
        if not full.startswith(spec["sha256"]):
            failures.append(
                f"{volume}: {spec['file']} has SHA-256 {full}, expected {spec['sha256']}..."
            )
        run = p01.get(volume)
        if run is None:
            failures.append(f"{volume}: the p01 report names no extraction")
            continue
        if run.get("sha256") != full:
            failures.append(
                f"{volume}: p01 extracted another file ({run.get('sha256')})"
            )
        text = text_hashes.get(volume)
        if text is None:
            failures.append(f"{volume}: lines file missing")
        elif text != run.get("text_sha256"):
            failures.append(
                f"{volume}: lines file is not p01's output (text hash {text}, "
                f"p01 {run.get('text_sha256')})"
            )
    return failures


def dir_differences(
    a: Path, b: Path, names: tuple[str, ...] | None = None
) -> list[str]:
    """Files that are missing from either tree or differ in a single byte.

    With names, exactly these files must exist in both; without, the trees
    are compared recursively."""
    if names is None:
        found_a = {p.relative_to(a).as_posix() for p in a.rglob("*") if p.is_file()}
        found_b = {p.relative_to(b).as_posix() for p in b.rglob("*") if p.is_file()}
        expected = found_a | found_b
        if not expected:
            return [f"{a.name} and {b.name} hold no files"]
    else:
        expected = set(names)
    out = []
    for name in sorted(expected):
        pa, pb = a / name, b / name
        if not pa.is_file() or not pb.is_file():
            missing = ", ".join(
                root.name for root, p in ((a, pa), (b, pb)) if not p.is_file()
            )
            out.append(f"{name}: missing in {missing}")
        elif sha256_file(pa) != sha256_file(pb):
            out.append(f"{name}: differs{_first_difference(pa, pb)}")
    return out


def _first_difference(a: Path, b: Path) -> str:
    with a.open("rb") as fa, b.open("rb") as fb:
        for n, (la, lb) in enumerate(zip(fa, fb), 1):
            if la != lb:
                return f" from line {n}"
    return " in length"


def p10_failures(report: dict, new: list, stale: list) -> list[str]:
    """The ledger holds every line and the violations are the listed ones."""
    failures = []
    outside = report.get("lines_outside_records")
    if outside is None:
        failures.append("p10 reported no line ledger")
    elif outside:
        failures.append(f"{outside} lines outside every record")
    failures += [f"new violation {inv} {oid}" for inv, oid in new]
    failures += [f"stale exception {inv} {oid}" for inv, oid in stale]
    return failures


def pin_of(identifiers: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(identifiers)).encode("utf-8")).hexdigest()


def undo_remaps(listed: list[str], remaps: list) -> tuple[list[str], list[str]]:
    """The identifiers as frozen, recovered by undoing the remaps last to first,
    and the problems of the remap list."""
    problems = []
    current = list(listed)
    if len(set(current)) != len(current):
        problems.append("the sample lists an identifier twice")
    for n, remap in reversed(list(enumerate(remaps))):
        old, new, reason = (
            (remap.get(k) for k in ("from", "to", "reason"))
            if isinstance(remap, dict)
            else (None, None, None)
        )
        if not all(isinstance(x, str) and x.strip() for x in (old, new, reason)):
            problems.append(f"remap {n} lacks its old identifier, new one or reason")
            continue
        if old == new:
            problems.append(f"remap {n} maps {old} onto itself")
        elif new not in current:
            problems.append(f"remap {n} {old} -> {new}: the sample does not list {new}")
        elif old in current:
            problems.append(f"remap {n} {old} -> {new}: the sample still lists {old}")
        else:
            current[current.index(new)] = old
    return current, problems


def sample_failures(
    listed: list[str],
    remaps: list,
    pin: str | None,
    exists: Callable[[str], bool],
) -> list[str]:
    """The identifier rule of a frozen sample against the rebuilt records."""
    frozen, failures = undo_remaps(listed, remaps)
    if pin is None:
        failures.append("the sample has no pin (p14_gate.py --pin)")
    elif not failures and pin_of(frozen) != pin:
        failures.append(
            "the frozen identifiers differ from their pin: an identifier changed "
            "without a remap entry"
        )
    moved = {r.get("to") for r in remaps if isinstance(r, dict)}
    for identifier in listed:
        if not exists(identifier):
            how = "its remap target" if identifier in moved else "it"
            failures.append(
                f"{identifier} is not in the rebuilt records; if {how} moved, "
                "record the old identifier, the new one and the reason in the "
                "remap list"
            )
    return failures


def blind_row_failures(
    key: dict, remaps: list, sheet_ids: set[str] | None
) -> list[str]:
    """Each row of the blind key is pinned by its sample_id, the hash of the
    entry identifier it was drawn as; the sheet holds the same rows."""
    failures = []
    for sample_id, row in sorted(key.items()):
        frozen = row["printId"]
        for remap in reversed(remaps):
            if isinstance(remap, dict) and remap.get("to") == frozen:
                frozen = remap.get("from") or frozen
        if hashlib.sha256(frozen.encode()).hexdigest()[:10] != sample_id:
            failures.append(
                f"row {sample_id}: {row['printId']} is not the entry it was drawn as"
            )
    if sheet_ids is None:
        failures.append("the blind sheet is missing")
    elif sheet_ids != set(key):
        failures.append(
            f"sheet and key differ in {len(sheet_ids ^ set(key))} sample identifiers"
        )
    return failures


def fingerprint(record: dict, object_id: str | None = None) -> str | None:
    """What a sample identifier stands for: the entry's sha256, and for an
    object its span in the entry as well; None for an object the record lacks."""
    if object_id is None:
        return record["sha256"]
    obj = next((o for o in record["objects"] if o["id"] == object_id), None)
    if obj is None:
        return None
    a, b = obj["span"]
    return f"{record['sha256']}:{a}-{b}"


def fingerprint_pin(fingerprints: dict[str, str]) -> str:
    lines = sorted(f"{i}\t{fp}" for i, fp in fingerprints.items())
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def current_identifier(frozen: str, remaps: list) -> str:
    """The identifier a frozen one stands under now, after the remaps in order."""
    for remap in remaps:
        if isinstance(remap, dict) and remap.get("from") == frozen:
            frozen = remap.get("to") or frozen
    return frozen


def fingerprint_failures(
    frozen_ids: list[str],
    fingerprints: dict[str, str] | None,
    rehashed: list,
    remaps: list,
    pin: str | None,
    current: Callable[[str], str | None],
) -> list[str]:
    """The fingerprint rule of a frozen sample: its fingerprints as frozen
    match their pin and cover the frozen identifiers, and each identifier's
    fingerprint in the rebuild equals the frozen one after the rehash list."""
    if fingerprints is None:
        return ["the sample has no fingerprints (p14_gate.py --pin)"]
    failures = []
    if pin is None:
        failures.append("the fingerprints have no pin (p14_gate.py --pin)")
    elif fingerprint_pin(fingerprints) != pin:
        failures.append("the fingerprints differ from their pin")
    if set(fingerprints) != set(frozen_ids):
        failures.append(
            f"fingerprints and frozen identifiers differ in "
            f"{len(set(fingerprints) ^ set(frozen_ids))} identifiers"
        )
    expected = dict(fingerprints)
    for n, change in enumerate(rehashed):
        ident, old, new, reason = (
            (change.get(k) for k in ("id", "from", "to", "reason"))
            if isinstance(change, dict)
            else (None, None, None, None)
        )
        if not all(isinstance(x, str) and x.strip() for x in (ident, old, new, reason)):
            failures.append(f"rehash {n} lacks its identifier, fingerprints or reason")
        elif expected.get(ident) != old:
            failures.append(f"rehash {n} of {ident} starts from another fingerprint")
        else:
            expected[ident] = new
    for ident, fp in sorted(expected.items()):
        now = current(current_identifier(ident, remaps))
        if now is not None and now != fp:
            failures.append(
                f"{ident}: what it stands for changed (entry text or object span); "
                "if the change keeps the publication, record it in the rehash list "
                "with the old and new fingerprint and the reason"
            )
    return failures


def pools_failures(pools: dict | None, review: dict | None) -> list[str]:
    """The pool sizes of the review sample name its parts and drawn counts."""
    if pools is None:
        return ["review-pools: the pool sizes are missing (review_sample.py --pools)"]
    if review is None:
        return []
    drawn = {
        (v, p): len(ids)
        for v, parts in review["objects"].items()
        for p, ids in parts.items()
    }
    listed = {
        (v, p): c["drawn"]
        for v, parts in pools["parts"].items()
        for p, c in parts.items()
    }
    out = []
    for (v, p), n in sorted(drawn.items()):
        c = pools["parts"].get(v, {}).get(p)
        if c is None or c["drawn"] != n:
            out.append(f"review-pools: {v}/{p} does not hold the {n} objects drawn")
        elif c["entries"] - c["hard"] <= 0:
            out.append(f"review-pools: {v}/{p} has no weight")
    out += [
        f"review-pools: {v}/{p} names objects the sample lacks"
        for (v, p), n in sorted(listed.items())
        if n and (v, p) not in drawn
    ]
    return out


def strata_failures(strata: dict | None, key: dict | None) -> list[str]:
    """The stratum sizes of the first blind sample cover its strata."""
    if strata is None:
        return [
            "blind-strata: the stratum sizes are missing (p09_human_sample.py --strata)"
        ]
    if key is None:
        return []
    out = []
    for row in key.values():
        volume = row["printId"].split("/")[0]
        if not strata["sizes"].get(volume, {}).get(row["stratum"]):
            out.append(f"blind-strata: no size for {volume} {row['stratum']}")
    return sorted(set(out))


# Twelve consecutive words are far longer than an address, a title or an
# imprint that knowledge and tests may name, and short enough to catch a
# quoted sentence.
LEAK_WORDS = 12
# Versioned paths that must never carry print text. Wiki-derived data and its
# fixtures are left out: the early wiki carried Addendum II text verbatim, so
# overlap there is the source, not a leak.
LEAK_SCOPE = (
    "knowledge/",
    "snapshots/",
    "pipeline/",
    "docs/js/",
    "docs/css/",
    "docs/index.html",
    "README.md",
    "CLAUDE.md",
)
# The evaluations of September predate the print strand and quote wiki
# source excerpts, some of which the wiki took from the print.
LEAK_EXEMPT = ("snapshots/evaluations/2026-09-05/",)
# Structural labels that are long enough to match, such as a section title of
# the 1991 contents, are admitted one by one as the sha256 of the matched
# words, so the list itself holds no print text.
LEAK_ALLOWED = HERE / "leak_allowed.json"
WORD = re.compile(r"\w+")


def shingle_hash(words: tuple[str, ...]) -> str:
    return hashlib.sha256(" ".join(words).encode("utf-8")).hexdigest()


def allowed_shingles() -> set[str]:
    if not LEAK_ALLOWED.exists():
        return set()
    data = json.loads(LEAK_ALLOWED.read_text("utf-8"))
    return {key for key in data if not key.startswith("_")}


def shingles(words: list[str], size: int = LEAK_WORDS) -> set[tuple[str, ...]]:
    return {tuple(words[i : i + size]) for i in range(len(words) - size + 1)}


def print_shingles(line_texts: list[list[str]]) -> set[tuple[str, ...]]:
    """Word shingles of the print, each volume read as one stream of its lines,
    so that a sentence across a line break is caught too."""
    out = set()
    for texts in line_texts:
        out |= shingles(WORD.findall(" ".join(texts).lower()))
    return out


def leak_failures(
    files: dict[str, str],
    print_set: set[tuple[str, ...]],
    allowed: frozenset[str] = frozenset(),
) -> list[str]:
    """Files whose text repeats LEAK_WORDS consecutive words of the print that
    are no admitted label; the report names file and line, never the words."""
    failures = []
    for name, text in sorted(files.items()):
        words, starts = [], []
        for number, line in enumerate(text.splitlines(), 1):
            found = WORD.findall(line.lower())
            words += found
            starts += [number] * len(found)
        for i in range(len(words) - LEAK_WORDS + 1):
            run = tuple(words[i : i + LEAK_WORDS])
            if run in print_set and shingle_hash(run) not in allowed:
                failures.append(
                    f"{name}:{starts[i]} repeats {LEAK_WORDS} consecutive words of the print"
                )
                break
    return failures


def versioned_texts() -> dict[str, str]:
    """The tracked files in LEAK_SCOPE that decode as text."""
    listed = subprocess.run(
        ["git", "ls-files", "-z", *LEAK_SCOPE],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    out = {}
    for name in filter(None, listed.split("\0")):
        if name.startswith(LEAK_EXEMPT):
            continue
        path = PROJECT_ROOT / name
        try:
            out[name] = path.read_text("utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return out


def load_identifiers(
    records_dir: Path,
) -> tuple[set[str], set[str], dict[str, list], dict[str, str]]:
    """Entry identifiers, object identifiers, per volume the page ranges of
    all records, and the fingerprint of every entry and object, from one
    records directory."""
    entries, objects, ranges = set(), set(), {v: [] for v in VOLUMES}
    prints: dict[str, str] = {}
    for name in RECORD_FILES:
        with (records_dir / name).open(encoding="utf-8") as source:
            for record in map(json.loads, source):
                entries.add(record["id"])
                prints[record["id"]] = fingerprint(record)
                for o in record["objects"]:
                    objects.add(o["id"])
                    prints[o["id"]] = fingerprint(record, o["id"])
                ranges[record["volume"]].append((record["page"], record["page_end"]))
    return entries, objects, ranges, prints


def _json(path: Path) -> dict | None:
    return json.loads(path.read_text("utf-8")) if path.exists() else None


def _object_ids(objects) -> list[str]:
    """The identifiers of a sample's "objects", by volume and part, by volume,
    or as a plain list."""
    if isinstance(objects, list):
        return list(objects)
    out = []
    for group in objects.values():
        if isinstance(group, dict):
            out += [o for ids in group.values() for o in ids]
        else:
            out += list(group)
    return out


def frozen_samples() -> dict[str, dict]:
    """Every frozen sample: its listed identifiers, remap list and kind, and
    for review and blind samples its fingerprints and rehash list."""
    out = {}
    sidecar = _json(FINGERPRINTS) or {}
    for name, path in (
        ("review", REVIEW_SAMPLE),
        ("review-hard", REVIEW_HARD),
        ("review-second", REVIEW_SECOND),
    ):
        data = _json(path)
        if data is None:
            continue
        own = sidecar.get(name, {}) if "fingerprints" not in data else data
        out[name] = {
            "file": path,
            "kind": "object",
            "listed": _object_ids(data["objects"]),
            "remaps": data.get("remapped", []),
            "fingerprints": own.get("fingerprints"),
            "rehashed": own.get("rehashed", []),
        }
    for name, path, sheet in (
        ("blind", BLIND_KEY, BLIND_SHEET),
        ("blind-2", BLIND_KEY_2, BLIND_SHEET_2),
    ):
        data = _json(path)
        if data is None:
            continue
        own = sidecar.get(name, {}) if "fingerprints" not in data else data
        out[name] = {
            "file": path,
            "kind": "entry",
            "listed": [row["printId"] for row in data["key"].values()],
            "remaps": data.get("remapped", []),
            "key": data["key"],
            "sheet": sheet,
            "fingerprints": own.get("fingerprints"),
            "rehashed": own.get("rehashed", []),
        }
    if CLAIMS_SHEET.exists():
        with CLAIMS_SHEET.open(encoding="utf-8", newline="") as source:
            ids = [row["claim_id"] for row in csv.DictReader(source)]
        out["claims"] = {
            "file": CLAIMS_SHEET,
            "kind": "claim",
            "listed": ids,
            "remaps": [],
        }
    for name, path in BENCH.items():
        if path.exists():
            data = json.loads(path.read_text("utf-8"))
            out[name] = {
                "file": path,
                "kind": "page",
                "listed": [
                    f"{volume}/p{page}"
                    for volume, pages in data["pages"].items()
                    for page in pages
                ],
                "remaps": data.get("remapped", []),
            }
    return out


def load_pins() -> dict:
    return json.loads(PINS.read_text("utf-8")) if PINS.exists() else {}


def _sheet_ids(sheet: Path) -> set[str] | None:
    if not sheet.exists():
        return None
    with sheet.open(encoding="utf-8", newline="") as source:
        return {row["sample_id"] for row in csv.DictReader(source)}


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def strand_code_hash() -> tuple[str, int]:
    """The hash of the strand's modules (tests left out) and their number."""
    code = sorted(p for p in HERE.glob("*.py") if not p.name.startswith("test_"))
    digest = hashlib.sha256(
        "".join(f"{p.name}\t{sha256_file(p)}\n" for p in code).encode()
    ).hexdigest()
    return digest, len(code)


def inputs() -> dict:
    """Every input of the run with its hash; "absent" for a missing file."""

    def h(path: Path) -> str:
        return sha256_file(path) if path.is_file() else "absent"

    from _llm import CACHE
    from _review import LOG

    named = [
        *(PRINT_DIR / SECTIONS["volumes"][v]["file"] for v in VOLUMES),
        *(lines_path(v) for v in VOLUMES),
        REPORT_DIR / "p01_extract.json",
        HERE / "sections.json",
        HERE / "known_exceptions.json",
        CACHE,
        REVIEW_SAMPLE,
        REVIEW_POOLS,
        REVIEW_HARD,
        REVIEW_SECOND,
        BLIND_KEY,
        BLIND_SHEET,
        BLIND_KEY_2,
        BLIND_SHEET_2,
        BLIND_STRATA,
        CLAIMS_SHEET,
        FINGERPRINTS,
        *BENCH.values(),
        PINS,
        HERE / "confirmation_rule.json",
        LOG,
        PROJECT_ROOT / "uv.lock",
    ]
    code_hash, modules = strand_code_hash()
    git = {}
    try:
        git["commit"] = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        git["changed_in_strand"] = subprocess.run(
            ["git", "status", "--porcelain", "--", _rel(HERE)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError) as e:
        git["error"] = repr(e)
    return {
        "files": {_rel(p): h(p) for p in named},
        "code": {
            "sha256": code_hash,
            "hashOf": "one line per module of the strand (tests left out), sorted "
            "by name: name TAB sha256 LF",
            "modules": modules,
        },
        "git": git,
    }


class Gate:
    """The checks share the rebuild directory; each returns its failures and
    details."""

    def __init__(self, export: bool):
        self.export = export
        self.runs = [GATE / name for name in RUNS]
        self.rebuilt = False

    def check_inputs(self) -> tuple[list[str], dict]:
        p01_path = REPORT_DIR / "p01_extract.json"
        p01 = json.loads(p01_path.read_text("utf-8")) if p01_path.exists() else {}
        pdf, text = {}, {}
        for volume in VOLUMES:
            spec = SECTIONS["volumes"][volume]
            path = PRINT_DIR / spec["file"]
            if path.is_file():
                pdf[volume] = sha256_file(path)
            run = p01.get(volume, {})
            if lines_path(volume).is_file() and "pages" in run:
                skipped = {
                    f["page"] for f in run.get("lossless_failures", []) if "error" in f
                }
                text[volume] = lines_text_hash(
                    lines_path(volume), run["pages"], skipped
                )
        failures = input_failures(SECTIONS["volumes"], pdf, p01, text)
        return failures, {"pdf_sha256": pdf, "lines_text_sha256": text}

    def check_rebuild(self) -> tuple[list[str], dict]:
        failures = []
        for run, seed in zip(self.runs, HASH_SEEDS):
            # Only the gate's own folders are ever removed.
            if run.resolve().parent != GATE.resolve():
                raise RuntimeError(f"{run} lies outside {GATE}")
            if run.exists():
                shutil.rmtree(run)
            done = subprocess.run(
                [sys.executable, str(HERE / "p03_records.py"), "--out", str(run)],
                env={**os.environ, "PYTHONHASHSEED": seed},
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if done.returncode:
                failures.append(f"p03 into {run.name} exited {done.returncode}")
        if failures:
            return failures, {}
        self.rebuilt = True
        failures = dir_differences(*self.runs, RECORD_FILES)
        live = dir_differences(self.runs[0], DERIVED_DIR / "records", RECORD_FILES)
        return failures, {
            "records": {
                name: sha256_file(self.runs[0] / name)
                for name in RECORD_FILES
                if (self.runs[0] / name).is_file()
            },
            "hash_seeds": list(HASH_SEEDS),
            "live_records_differ_from_rebuild": live,
        }

    def check_validate(self) -> tuple[list[str], dict]:
        if not self.rebuilt:
            return ["not run: no rebuilt records"], {}
        # p10 reads its records directory from a module constant; pointing it
        # at the rebuild leaves the live report and records alone. Upgrade
        # path: a records-directory argument to p10.validate().
        import p10_validate

        saved = p10_validate.RECORDS
        p10_validate.RECORDS = self.runs[0]
        try:
            report, _violations, new, stale = p10_validate.validate()
        finally:
            p10_validate.RECORDS = saved
        details = {
            k: report.get(k)
            for k in (
                "objects",
                "lines",
                "lines_outside_records",
                "violations",
                "violations_listed",
                "violations_new",
                "exceptions_stale",
            )
        }
        return p10_failures(report, new, stale), details

    def check_samples(self) -> tuple[list[str], dict]:
        if not self.rebuilt:
            return ["not run: no rebuilt records"], {}
        entries, objects, ranges, prints = load_identifiers(self.runs[0])

        def on_page(identifier: str) -> bool:
            volume, _, page = identifier.partition("/p")
            return page.isdigit() and any(
                a <= int(page) <= b for a, b in ranges.get(volume, [])
            )

        exists = {
            "object": objects.__contains__,
            "entry": entries.__contains__,
            "page": on_page,
            # The gate does not rebuild p07; claim identifiers are pinned only.
            "claim": lambda _identifier: True,
        }
        pins = load_pins()
        failures, details = [], {}
        samples = frozen_samples()
        for name in (*REQUIRED, *BENCH):
            if name not in samples:
                failures.append(f"{name}: sample file missing")
        for name, sample in samples.items():
            found = sample_failures(
                sample["listed"],
                sample["remaps"],
                pins.get(name, {}).get("sha256"),
                exists[sample["kind"]],
            )
            if "key" in sample:
                found += blind_row_failures(
                    sample["key"], sample["remaps"], _sheet_ids(sample["sheet"])
                )
            if "fingerprints" in sample:
                frozen, _ = undo_remaps(sample["listed"], sample["remaps"])
                found += fingerprint_failures(
                    frozen,
                    sample["fingerprints"],
                    sample["rehashed"],
                    sample["remaps"],
                    pins.get(f"{name}:fingerprints", {}).get("sha256"),
                    prints.get,
                )
            failures += [f"{name}: {f}" for f in found]
            details[name] = {
                "file": _rel(sample["file"]),
                "identifiers": len(sample["listed"]),
                "remapped": [
                    {k: r.get(k) for k in ("from", "to", "reason")}
                    for r in sample["remaps"]
                    if isinstance(r, dict)
                ],
                "rehashed": [
                    {k: r.get(k) for k in ("id", "reason")}
                    for r in sample.get("rehashed", [])
                    if isinstance(r, dict)
                ],
                "failures": len(found),
            }
        if "review-second" in samples and "review" in samples:
            outside = set(samples["review-second"]["listed"]) - set(
                samples["review"]["listed"]
            )
            failures += [
                f"review-second: {o} is no object of the review sample"
                for o in sorted(outside)
            ]
        failures += pools_failures(_json(REVIEW_POOLS), _json(REVIEW_SAMPLE))
        blind = _json(BLIND_KEY)
        failures += strata_failures(_json(BLIND_STRATA), blind and blind["key"])
        return failures, details

    def check_export(self) -> tuple[list[str], dict]:
        if not self.rebuilt:
            return ["not run: no rebuilt records"], {}
        # p12 reads and writes through module constants; build() alone writes
        # only into OUT, so the live viewer and JSON-LD stay untouched.
        import p12_jsonld

        saved = p12_jsonld.RECORDS, p12_jsonld.OUT
        outs = [GATE / "jsonld-a", GATE / "jsonld-b"]
        try:
            p12_jsonld.RECORDS = self.runs[0]
            for out in outs:
                p12_jsonld.OUT = out
                p12_jsonld.build()
        finally:
            p12_jsonld.RECORDS, p12_jsonld.OUT = saved
        files = sum(1 for p in outs[0].rglob("*") if p.is_file())
        return dir_differences(*outs), {"files": files}

    def check_leaks(self) -> tuple[list[str], dict]:
        streams = []
        for volume in VOLUMES:
            with lines_path(volume).open(encoding="utf-8") as source:
                streams.append([json.loads(line)["text"] for line in source])
        files = versioned_texts()
        allowed = frozenset(allowed_shingles())
        return leak_failures(files, print_shingles(streams), allowed), {
            "files": len(files),
            "words": LEAK_WORDS,
            "scope": list(LEAK_SCOPE),
            "exempt": list(LEAK_EXEMPT),
            "allowed": len(allowed),
        }

    def checks(self) -> list[tuple[str, Callable]]:
        out = [
            ("inputs", self.check_inputs),
            ("leaks", self.check_leaks),
            ("rebuild", self.check_rebuild),
            ("validate", self.check_validate),
            ("samples", self.check_samples),
        ]
        if self.export:
            out.append(("export", self.check_export))
        return out


def run_checks(checks: list[tuple[str, Callable]], keep_going: bool) -> dict:
    """Run the checks in order; the first failure stops the run unless
    keep_going. A check that raises fails with the exception's name."""
    results = {}
    for name, check in checks:
        try:
            failures, details = check()
        except Exception as e:  # a broken input fails the gate, it never passes
            failures, details = [f"raised {e!r}"], {}
        results[name] = {"ok": not failures, "failures": failures, **details}
        print(f"{'OK' if not failures else 'FEHLER'} {name}")
        for f in failures[:20]:
            print(f"  {f}")
        if failures and not keep_going:
            break
    for name, _ in checks:
        results.setdefault(name, {"ok": None, "failures": ["not run"]})
    return results


def write_fingerprints(samples: dict[str, dict], records_dir: Path) -> int:
    """Write the fingerprints of the samples frozen before fingerprints
    existed, once, from the current records; never replaced."""
    sidecar = _json(FINGERPRINTS) or {}
    missing = [
        n
        for n, s in samples.items()
        if "fingerprints" in s and s["fingerprints"] is None
    ]
    if not missing:
        return 0
    *_, prints = load_identifiers(records_dir)
    for name in missing:
        sample = samples[name]
        frozen, _ = undo_remaps(sample["listed"], sample["remaps"])
        found = {i: prints.get(current_identifier(i, sample["remaps"])) for i in frozen}
        lacking = sorted(i for i, fp in found.items() if fp is None)
        if lacking:
            print(f"FEHLER {name}: not in the records: {lacking[:5]}")
            return 1
        sidecar[name] = {"fingerprints": dict(sorted(found.items())), "rehashed": []}
        sample["fingerprints"] = sidecar[name]["fingerprints"]
        print(f"OK {name}: fingerprints of {len(found)} identifiers written")
    sidecar["_about"] = (
        "Fingerprints of the samples frozen before fingerprints existed, written "
        "once from the records (p14_gate.py --pin): per frozen identifier the "
        "entry's sha256, for an object with its span. A change is recorded in the "
        "sample's rehashed list, never by editing a fingerprint."
    )
    FINGERPRINTS.write_text(json.dumps(sidecar, indent=1, sort_keys=True), "utf-8")
    return 0


def write_pins(records_dir: Path = DERIVED_DIR / "records") -> int:
    pins = load_pins()
    samples = frozen_samples()
    for name, sample in samples.items():
        _, problems = undo_remaps(sample["listed"], sample["remaps"])
        if problems:
            print(f"FEHLER {name}: {problems}")
            return 1
    if write_fingerprints(samples, records_dir):
        return 1
    wanted = {}
    for name, sample in samples.items():
        frozen, _ = undo_remaps(sample["listed"], sample["remaps"])
        wanted[name] = {"identifiers": len(frozen), "sha256": pin_of(frozen)}
        if sample.get("fingerprints") is not None:
            wanted[f"{name}:fingerprints"] = {
                "identifiers": len(sample["fingerprints"]),
                "sha256": fingerprint_pin(sample["fingerprints"]),
            }
    for name, pin in wanted.items():
        if name in pins:
            same = pins[name]["sha256"] == pin["sha256"]
            print(
                f"{'OK' if same else 'FEHLER'} {name}: pin kept{'' if same else ', differs'}"
            )
            continue
        pins[name] = pin
        print(f"OK {name}: pinned {pin['identifiers']} identifiers")
    pins["_about"] = (
        "Pins of the frozen samples (p14_gate.py): per sample the sha256 of its "
        "identifiers as frozen, sorted and joined by LF, after undoing its remap "
        "list, and per sample with fingerprints (<name>:fingerprints) the sha256 of "
        "its lines identifier TAB fingerprint as frozen, sorted and joined by LF. "
        "Hashes and counts only; written once by --pin, never replaced."
    )
    PINS.write_text(
        json.dumps(pins, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--export", action="store_true", help="also rebuild the JSON-LD twice"
    )
    parser.add_argument("--keep-going", action="store_true", help="run every check")
    parser.add_argument(
        "--pin", action="store_true", help="pin the samples that have none"
    )
    args = parser.parse_args()
    if args.pin:
        return write_pins()
    GATE.mkdir(parents=True, exist_ok=True)
    gate = Gate(args.export)
    report = {
        "about": "Local print gate: PDF and lines provenance, two byte-identical "
        "rebuilds, p10 with the line ledger, the identifier rule of the frozen "
        "samples, and with --export two byte-identical JSON-LD builds.",
        "inputs": inputs(),
        "export": args.export,
        "checks": run_checks(gate.checks(), args.keep_going),
    }
    report["ok"] = all(c["ok"] for c in report["checks"].values())
    tmp = REPORT.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True), "utf-8"
    )
    tmp.replace(REPORT)
    print(f"{'OK' if report['ok'] else 'FEHLER'} gate -> {REPORT}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
