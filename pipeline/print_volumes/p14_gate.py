"""p14: the local print gate that a human measurement needs before it can count.

Checks, in this order, each stopping the run when it fails (--keep-going runs
the rest and still fails):

1. inputs: each PDF's SHA-256 starts with its prefix in sections.json, and each
   p01 lines file is p01's output of that PDF: the p01 report names the same
   full hash and its text hash is the hash of the lines file's text.
   leaks: no tracked file under LEAK_SCOPE (knowledge, code, frontend code,
   README, CLAUDE.md) repeats LEAK_WORDS consecutive words of the print, so a
   quotation of print text in a versioned file fails whoever wrote it.
2. rebuild: p03 writes the entry and apparatus records twice from the same
   inputs, under different hash seeds, into gate/run-a and gate/run-b; every
   records file is byte-identical between the two. The live records are never
   written; whether they equal the rebuild is reported, not checked, because
   p13 already marks a decision on a changed entry as stale.
3. validate: p10 on the rebuilt records, with its line-coverage ledger: no p01
   line outside a record, every violation a listed exception, no stale
   exception.
4. samples: every identifier of each frozen sample (the review sample, the
   blind sample of p09, both benchmark samples) exists in the rebuilt records.
   A sample lists its identifiers as they stand now; its remap list
   ("remapped": [{"from", "to", "reason"}], in order) is the only admitted way
   one may change. Undoing the remaps recovers the identifiers as frozen, whose
   hash must equal the sample's pin in sample_pins.json, so that an identifier
   that moved or was replaced without a remap entry fails. The blind sample
   pins each row as well: its sample_id is the hash of the frozen identifier.
   Benchmark identifiers are PDF pages, fixed by the PDF hash; each must lie
   on a rebuilt record.
5. export (--export, slow): p12 builds the JSON-LD from the rebuilt records
   twice, into gate/jsonld-a and gate/jsonld-b; both are byte-identical. SHACL
   validation stays with p12.

The run names its inputs with hashes: PDFs, lines files, sections.json, the
known exceptions, the LLM cache, the sample files and pins, the review log
(read by the export), the strand's code and uv.lock, and the git commit.

--pin writes the pin of every sample that has none, from the identifiers as
frozen; it never replaces a pin. A pin changes only by a reviewed edit of the
versioned file.

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
BLIND_KEY = SAMPLES / "concordance-blind-key.json"
BLIND_SHEET = SAMPLES / "concordance-blind-sheet.csv"
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


# Twelve consecutive words are far longer than an address, a title or an
# imprint that knowledge and tests may name, and short enough to catch a
# quoted sentence.
LEAK_WORDS = 12
# Versioned paths that must never carry print text. Wiki-derived data and its
# fixtures are left out: the early wiki carried Addendum II text verbatim, so
# overlap there is the source, not a leak.
LEAK_SCOPE = (
    "knowledge/",
    "pipeline/",
    "docs/js/",
    "docs/css/",
    "docs/index.html",
    "README.md",
    "CLAUDE.md",
)
# The evaluations of September predate the print strand and quote wiki
# source excerpts, some of which the wiki took from the print.
LEAK_EXEMPT = ("knowledge/evaluations/2026-09-05/",)
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


def load_identifiers(records_dir: Path) -> tuple[set[str], set[str], dict[str, list]]:
    """Entry identifiers, object identifiers and per volume the page ranges of
    all records, from one records directory."""
    entries, objects, ranges = set(), set(), {v: [] for v in VOLUMES}
    for name in RECORD_FILES:
        with (records_dir / name).open(encoding="utf-8") as source:
            for record in map(json.loads, source):
                entries.add(record["id"])
                objects.update(o["id"] for o in record["objects"])
                ranges[record["volume"]].append((record["page"], record["page_end"]))
    return entries, objects, ranges


def frozen_samples() -> dict[str, dict]:
    """Every frozen sample: its listed identifiers, remap list and kind."""
    out = {}
    if REVIEW_SAMPLE.exists():
        data = json.loads(REVIEW_SAMPLE.read_text("utf-8"))
        out["review"] = {
            "file": REVIEW_SAMPLE,
            "kind": "object",
            "listed": [
                o
                for parts in data["objects"].values()
                for ids in parts.values()
                for o in ids
            ],
            "remaps": data.get("remapped", []),
        }
    if BLIND_KEY.exists():
        data = json.loads(BLIND_KEY.read_text("utf-8"))
        out["blind"] = {
            "file": BLIND_KEY,
            "kind": "entry",
            "listed": [row["printId"] for row in data["key"].values()],
            "remaps": data.get("remapped", []),
            "key": data["key"],
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


def _sheet_ids() -> set[str] | None:
    if not BLIND_SHEET.exists():
        return None
    with BLIND_SHEET.open(encoding="utf-8", newline="") as source:
        return {row["sample_id"] for row in csv.DictReader(source)}


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


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
        BLIND_KEY,
        BLIND_SHEET,
        *BENCH.values(),
        PINS,
        LOG,
        PROJECT_ROOT / "uv.lock",
    ]
    code = sorted(p for p in HERE.glob("*.py") if not p.name.startswith("test_"))
    code_hash = hashlib.sha256(
        "".join(f"{p.name}\t{sha256_file(p)}\n" for p in code).encode()
    ).hexdigest()
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
            "modules": len(code),
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
        entries, objects, ranges = load_identifiers(self.runs[0])

        def on_page(identifier: str) -> bool:
            volume, _, page = identifier.partition("/p")
            return page.isdigit() and any(
                a <= int(page) <= b for a, b in ranges.get(volume, [])
            )

        exists = {
            "object": objects.__contains__,
            "entry": entries.__contains__,
            "page": on_page,
        }
        pins = load_pins()
        failures, details = [], {}
        samples = frozen_samples()
        for name in ("review", "blind", *BENCH):
            if name not in samples:
                failures.append(f"{name}: sample file missing")
        for name, sample in samples.items():
            found = sample_failures(
                sample["listed"],
                sample["remaps"],
                pins.get(name, {}).get("sha256"),
                exists[sample["kind"]],
            )
            if name == "blind":
                found += blind_row_failures(
                    sample["key"], sample["remaps"], _sheet_ids()
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
                "failures": len(found),
            }
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


def write_pins() -> int:
    pins = load_pins()
    for name, sample in frozen_samples().items():
        frozen, problems = undo_remaps(sample["listed"], sample["remaps"])
        if problems:
            print(f"FEHLER {name}: {problems}")
            return 1
        if name in pins:
            same = pins[name]["sha256"] == pin_of(frozen)
            print(
                f"{'OK' if same else 'FEHLER'} {name}: pin kept{'' if same else ', differs'}"
            )
            continue
        pins[name] = {"identifiers": len(frozen), "sha256": pin_of(frozen)}
        print(f"OK {name}: pinned {len(frozen)} identifiers")
    pins["_about"] = (
        "Pins of the frozen samples (p14_gate.py): per sample the sha256 of its "
        "identifiers as frozen, sorted and joined by LF, after undoing its remap "
        "list. Hashes and counts only; written once by --pin, never replaced."
    )
    PINS.write_text(json.dumps(pins, indent=1, sort_keys=True) + "\n", encoding="utf-8")
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
