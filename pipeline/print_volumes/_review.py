"""Human review of the print objects: the decision model, the log and its checks.

Schema validity and the p10 invariants show that every value is span-bound and
consistent; whether it is the right value in its context only a person can
decide. Those decisions form a layer of their own beside the rule values, which
they never overwrite, in the manner of the reconciliation's candidates and
decisions: a value stays as the rules read it, and its review state and the
decision travel with it into the JSON-LD (p12) and the viewer.

Decisions on a value:
- confirm: the value is right in its context.
- correct: the value is wrong; the correction is a passage of the object's own
  entry, or carries no passage when the value should not exist at all.
- unresolved: the reviewer cannot decide; the value stays an open statement.
Decisions on an object:
- missing: a value the object should carry, with its field and passage.
- boundary: the object is split or joined wrongly (note).
- complete: every value was decided and every missing value added; only
  complete objects of the review sample enter the measurement (p13_review.py).
- withdraw: cancels the decision named in "supersedes".

A value decision supersedes the earlier one on the same object and path, and
"boundary" and "complete" the earlier one of their kind; the log keeps every
line. A value decision names the value as the reviewer saw it (path, value,
span, source); when a rebuild changes that value the decision is stale, stays
in the log and is reported, and no longer applies.

Corrections and added values are passages of the object's own entry: text
values equal their passage, a year's digits stand in it, a role, type or
language is a word of the closed vocabulary. An inherited value can be
confirmed, left open or removed; what it should have been goes into the note.

Decisions arrive from the browser through review_server.py, which validates
them with these strict models and assigns identifier and time. The log is
data/print/review/decisions.jsonl, local like all print data, because
corrections quote the print text.
"""

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from _common import PRINT_DIR
from _schema import LANGUAGES, OBJECT_TYPES, ROLES
from annotated_types import Len
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, model_validator

REVIEW_DIR = PRINT_DIR / "review"
LOG = REVIEW_DIR / "decisions.jsonl"
VALUE_DECISIONS = ("confirm", "correct", "unresolved")
OBJECT_DECISIONS = ("missing", "boundary", "complete")
DECISIONS = (*VALUE_DECISIONS, *OBJECT_DECISIONS, "withdraw")
# The paths of p12: keys joined by ".", list positions in brackets.
PATH = r"^[a-z_]+(?:\[\d+\])?(?:\.[a-z_]+(?:\[\d+\])?)*$"
OBJECT_ID = r"^(I|A1|A2)/[A-R]/[^#\s]+#\d+$"
BASE_KEYS = ("id", "entry", "entry_sha256", "volume", "part", "address", "span", "text")
# The fields a reviewer can add as missing, by family; p13 counts misses so.
MISSING_FIELDS = (
    "title",
    "subtitle",
    "original_title",
    "language",
    "persons.name",
    "persons.roles",
    "imprints.place",
    "imprints.publisher",
    "imprints.year",
    "extent.raw",
    "series.title",
    "series.number",
    "edition_notes.text",
    "periodicals.title",
    "periodicals.siglum",
    "periodicals.date",
    "periodicals.pages",
    "hosts.title",
    "hosts.pages",
    "contents.title",
    "holdings.repository",
    "event.date",
    "event.place",
    "notes",
)
YEAR_LEAVES = ("year", "year_end", "years")
FLAG_LEAVES = ("year_bracketed", "circa")

Span = Annotated[list[NonNegativeInt], Len(2, 2)]


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", populate_by_name=True)


class ValueRef(_Strict):
    """The value a decision is about, as the reviewer saw it."""

    path: str = Field(pattern=PATH, max_length=200)
    value: str | int | bool
    span: Span
    source: str = Field(min_length=1, max_length=120)


class Correction(_Strict):
    """A corrected or added value: a passage of the object's own entry."""

    field: str | None = Field(default=None, pattern=PATH, max_length=200)
    value: str | int | bool | None = None
    span: Span | None = None

    @model_validator(mode="after")
    def _paired(self):
        if (self.value is None) != (self.span is None):
            raise ValueError("a correction has both value and span, or neither")
        if self.span and self.span[0] >= self.span[1]:
            raise ValueError("empty correction span")
        return self


class DecisionIn(_Strict):
    """What the viewer submits."""

    object: str = Field(pattern=OBJECT_ID, max_length=120)
    entry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer: str = Field(min_length=1, max_length=80)
    decision: Literal[DECISIONS]
    target: ValueRef | None = None
    correction: Correction | None = None
    supersedes: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def _shape(self):
        d = self.decision
        if (d in VALUE_DECISIONS) != (self.target is not None):
            raise ValueError(
                "a value decision names its target, an object decision none"
            )
        if d == "correct" and self.correction is None:
            raise ValueError("a correction carries its corrected value or none")
        if d == "missing" and not (
            self.correction and self.correction.field and self.correction.span
        ):
            raise ValueError("a missing value names its field, value and passage")
        if d not in ("correct", "missing") and self.correction is not None:
            raise ValueError(f"{d} carries no correction")
        if (d == "withdraw") != (self.supersedes is not None):
            raise ValueError(
                "withdraw names the decision it cancels, and only withdraw"
            )
        if d == "boundary" and not self.note.strip():
            raise ValueError("a boundary decision says in its note what is wrong")
        return self


class Decision(DecisionIn):
    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    at: str = Field(pattern=r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


def stamp(decision: DecisionIn) -> Decision:
    """The stored form: identifier and time are the server's, never the browser's."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return Decision(**decision.model_dump(by_alias=True), id=uuid.uuid4().hex, at=now)


def value_paths(obj: dict) -> dict[str, dict]:
    """Every value of an object by its p12 path ("persons[0].roles[1]")."""
    out: dict[str, dict] = {}

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            if "span" in node and "by" in node:
                out[path] = node
                return
            for key, child in node.items():
                walk(child, f"{path}.{key}")
        elif isinstance(node, list):
            for i, child in enumerate(node):
                walk(child, f"{path}[{i}]")

    for key, child in obj.items():
        if key not in BASE_KEYS:
            walk(child, key)
    return out


def _leaf(path: str) -> str:
    return re.sub(r"\[\d+\]", "", path).split(".")[-1]


def _correction_problem(path: str, value, span: list[int], text: str) -> str | None:
    a, b = span
    if b > len(text):
        return "correction span beyond the entry text"
    passage = text[a:b]
    leaf = _leaf(path)
    if leaf in YEAR_LEAVES:
        ok = type(value) is int and str(value) in passage
    elif leaf in FLAG_LEAVES:
        ok = type(value) is bool
    elif leaf == "roles":
        ok = value in ROLES
    elif leaf == "types":
        ok = value in OBJECT_TYPES
    elif leaf == "language":
        ok = value in LANGUAGES
    elif leaf == "kind":
        ok = isinstance(value, str) and bool(value)
    else:
        ok = value == passage
    return None if ok else f"correction value does not follow from its passage ({leaf})"


def check(decision: Decision | DecisionIn, records: dict[str, dict]) -> str | None:
    """None when the decision applies to the current records, else the reason."""
    entry_id = decision.object.split("#")[0]
    record = records.get(entry_id)
    obj = (
        next((o for o in record["objects"] if o["id"] == decision.object), None)
        if record
        else None
    )
    if obj is None:
        return "no such object"
    if record["sha256"] != decision.entry_sha256:
        return "stale: the entry text changed"
    if decision.target:
        t = decision.target
        current = value_paths(obj).get(t.path)
        if (
            current is None
            or current["value"] != t.value
            or type(current["value"]) is not type(t.value)
            or current["span"] != t.span
            or (current.get("from") or obj["entry"]) != t.source
        ):
            return "stale: the value changed"
    c = decision.correction
    if c and c.span:
        field = c.field or (decision.target.path if decision.target else None)
        if field is None:
            return "correction without field"
        return _correction_problem(field, c.value, c.span, record["text"])
    return None


def load_log() -> list[Decision]:
    """Every logged decision in order; a malformed line is an error, never skipped."""
    if not LOG.exists():
        return []
    out = []
    with LOG.open(encoding="utf-8") as source:
        for n, line in enumerate(source, 1):
            if line.strip():
                try:
                    out.append(Decision.model_validate_json(line))
                except ValueError as e:
                    raise ValueError(f"{LOG}:{n}: {e}") from e
    return out


def append(decision: Decision) -> None:
    import os

    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as sink:
        sink.write(decision.model_dump_json(by_alias=True, exclude_none=True) + "\n")
        sink.flush()
        os.fsync(sink.fileno())


def effective(decisions: list[Decision]) -> dict[tuple, Decision]:
    """The decisions in force, after supersession and withdrawal, by key."""
    by_id = {d.id: d for d in decisions}
    active: dict[tuple, Decision] = {}
    key_of: dict[str, tuple] = {}
    for d in decisions:
        if d.decision == "withdraw":
            key = key_of.get(d.supersedes)
            if key and active.get(key) is by_id.get(d.supersedes):
                del active[key]
            continue
        if d.target:
            key = (d.object, "value", d.target.path)
        elif d.decision == "missing":
            key = (d.object, "missing", d.id)
        else:
            key = (d.object, d.decision)
        active[key] = d
        key_of[d.id] = key
    return active


def load_records(records_dir) -> dict[str, dict]:
    records = {}
    for path in sorted(records_dir.glob("entries-*.jsonl")):
        with path.open(encoding="utf-8") as source:
            for line in source:
                r = json.loads(line)
                records[r["id"]] = r
    return records
