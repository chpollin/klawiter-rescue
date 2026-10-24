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
- withdraw: cancels the reviewer's own decision named in "supersedes".
- adjudicate: settles a disagreement between the first and the second
  reviewer of an object. It names both decisions in "settles" and the one that
  stands in "adopts", and is made by neither of the two (a third person or the
  operator). It settles two value decisions on one value (and names that value
  as its target), or one reviewer's "missing" or "boundary" against the
  other's "complete" on the object.

Every reviewer's decisions stand on their own: a value decision supersedes the
same reviewer's earlier one on the same object and path, "boundary" and
"complete" the same reviewer's earlier one of their kind, and a second
reviewer never replaces the first (in_force). The first reviewer of an object
is the one whose decisions on it were logged first, the second the next one
(reviewers); adjudicators are neither. The published state (effective), which
p12 exports, is the first reviewer's decisions with each valid adjudication
applied; p13 measures precision from the first reviewer and agreement from
the second (layers). The log keeps every line. A value decision names the
value as the reviewer saw it (path, value, span, source); when a rebuild
changes that value the decision is stale, stays in the log and is reported,
and no longer applies.

Corrections and added values are passages of the object's own entry: text
values equal their passage, a year's digits stand in it, a role, type or
language is a word of the closed vocabulary, and a flag (circa, year in
brackets) is the boolean true at the passage that shows it; a flag that does
not hold is a value that should not exist. A correction keeps the type of the
value it corrects and names no other field. An inherited value can be
confirmed, left open or marked as one that should not exist, because its
passage lies in another record; what it should have been goes into the note.
check() enforces these rules for every caller, the review server included.

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
from _schema import LANGUAGES, OBJECT_TYPES, ROLES, object_values
from annotated_types import Len
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, model_validator

REVIEW_DIR = PRINT_DIR / "review"
LOG = REVIEW_DIR / "decisions.jsonl"
VALUE_DECISIONS = ("confirm", "correct", "unresolved")
OBJECT_DECISIONS = ("missing", "boundary", "complete")
DECISIONS = (*VALUE_DECISIONS, *OBJECT_DECISIONS, "withdraw", "adjudicate")
DECISION_ID = r"^[0-9a-f]{32}$"
# The paths of p12: keys joined by ".", list positions in brackets.
PATH = r"^[a-z_]+(?:\[\d+\])?(?:\.[a-z_]+(?:\[\d+\])?)*$"
OBJECT_ID = r"^(I|A1|A2)/[A-R]/[^#\s]+#\d+$"
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
    supersedes: str | None = Field(default=None, pattern=DECISION_ID)
    settles: (
        Annotated[list[Annotated[str, Field(pattern=DECISION_ID)]], Len(2, 2)] | None
    ) = None
    adopts: str | None = Field(default=None, pattern=DECISION_ID)
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def _shape(self):
        d = self.decision
        if d == "adjudicate":
            if not self.settles or len(set(self.settles)) != 2:
                raise ValueError("an adjudication settles two distinct decisions")
            if self.adopts not in self.settles:
                raise ValueError("an adjudication adopts one of the two it settles")
        elif self.settles is not None or self.adopts is not None:
            raise ValueError("only an adjudication settles and adopts")
        if d in VALUE_DECISIONS and self.target is None:
            raise ValueError("a value decision names its target")
        if d in (*OBJECT_DECISIONS, "withdraw") and self.target is not None:
            raise ValueError("an object decision names no target")
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
    return dict(object_values(obj))


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
        ok = value is True
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
    c = decision.correction
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
        if c and c.field is not None and c.field != t.path:
            return "a correction names the field of the value it corrects"
        if c and c.span and t.source != obj["entry"]:
            return "an inherited value can only be marked as one that should not exist"
        if c and c.span and type(c.value) is not type(t.value):
            return f"a correction keeps the value's type ({type(t.value).__name__})"
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


def key_of(d: Decision) -> tuple:
    """What a decision is about, without its reviewer: a later decision of the
    same reviewer with the same key supersedes it."""
    if d.decision == "adjudicate":
        about = d.target.path if d.target else "/".join(sorted(d.settles))
        return (d.object, "adjudicate", about)
    if d.target:
        return (d.object, "value", d.target.path)
    if d.decision == "missing":
        return (d.object, "missing", d.id)
    return (d.object, d.decision)


def in_force(decisions: list[Decision]) -> dict[tuple, Decision]:
    """Every reviewer's decisions in force, keyed (reviewer, *key_of): each
    reviewer's own supersessions and withdrawals, never another's."""
    by_id = {d.id: d for d in decisions}
    active: dict[tuple, Decision] = {}
    keys: dict[str, tuple] = {}
    for d in decisions:
        if d.decision == "withdraw":
            withdrawn = by_id.get(d.supersedes)
            key = keys.get(d.supersedes)
            if (
                withdrawn is not None
                and withdrawn.reviewer == d.reviewer
                and active.get(key) is withdrawn
            ):
                del active[key]
            continue
        key = (d.reviewer, *key_of(d))
        active[key] = d
        keys[d.id] = key
    return active


def reviewers(decisions: list[Decision]) -> dict[str, list[str]]:
    """Per object its reviewers in the order of their first decision on it,
    counting only reviewers with a decision in force there; adjudicators and
    withdrawals do not make a reviewer."""
    holding = {
        (k[0], k[1])
        for k, d in in_force(decisions).items()
        if d.decision != "adjudicate"
    }
    order: dict[str, list[str]] = {}
    for d in decisions:
        if d.decision in ("withdraw", "adjudicate"):
            continue
        seen = order.setdefault(d.object, [])
        if d.reviewer not in seen and (d.reviewer, d.object) in holding:
            seen.append(d.reviewer)
    return order


def _same(a: Decision, b: Decision) -> bool:
    return a.decision == b.decision and a.correction == b.correction


def adjudication_problem(
    d: Decision | DecisionIn,
    decisions: list[Decision],
    force: dict[tuple, Decision] | None = None,
    order: dict[str, list[str]] | None = None,
) -> str | None:
    """None when the adjudication settles a disagreement in force between the
    first and the second reviewer of its object, else the reason."""
    force = in_force(decisions) if force is None else force
    order = reviewers(decisions) if order is None else order
    by_id = {x.id: x for x in decisions}
    settled = [by_id.get(i) for i in d.settles]
    if None in settled:
        return "settles an unknown decision"
    a, b = settled
    if a.object != d.object or b.object != d.object:
        return "settles decisions on its own object only"
    if a.reviewer == b.reviewer:
        return "settles the decisions of two reviewers"
    if d.reviewer in (a.reviewer, b.reviewer):
        return "an adjudicator is neither of the two reviewers"
    if set(order.get(d.object, [])[:2]) != {a.reviewer, b.reviewer}:
        return "settles the first and the second reviewer's decisions"
    kinds = {a.decision, b.decision}
    if kinds <= set(VALUE_DECISIONS):
        if d.target is None or not (a.target.path == b.target.path == d.target.path):
            return "settles two decisions on the value it names"
        if _same(a, b):
            return "the two decisions agree; there is nothing to settle"
    elif d.target is not None or not (
        "complete" in kinds and kinds - {"complete"} <= {"missing", "boundary"}
    ):
        return (
            "settles two value decisions on one value, or a missing value or a "
            "boundary against complete"
        )
    for x in settled:
        if force.get((x.reviewer, *key_of(x))) is not x:
            return "stale: a settled decision was superseded or withdrawn"
    return None


def layers(decisions: list[Decision]) -> dict:
    """The decisions in force, keyed by key_of, as the first reviewer, the
    second reviewer and the adjudicated state hold them, with the valid
    adjudications and the invalid ones with their reasons.

    The adjudicated state is the first reviewer's with each valid adjudication
    applied: an adopted value decision stands for the value, an adopted missing
    value or boundary of the second reviewer is added, and a rejected missing
    value or boundary of the first reviewer is dropped; "complete" is never
    dropped, since it states that every value was decided."""
    force = in_force(decisions)
    order = reviewers(decisions)
    by_role: list[dict[tuple, Decision]] = [{}, {}]
    for (reviewer, *key), d in force.items():
        if d.decision == "adjudicate":
            continue
        roles = order.get(d.object, [])
        if reviewer in roles[:2]:
            by_role[roles.index(reviewer)][tuple(key)] = d
    first, second = by_role
    valid: dict[tuple, Decision] = {}
    invalid = []
    for d in decisions:
        if d.decision != "adjudicate" or force.get((d.reviewer, *key_of(d))) is not d:
            continue
        problem = adjudication_problem(d, decisions, force, order)
        if problem:
            invalid.append((d, problem))
        else:
            # A later adjudication of the same disagreement replaces an earlier one.
            valid[key_of(d)] = d
    by_id = {d.id: d for d in decisions}
    adjudicated = dict(first)
    for adj in valid.values():
        adopted = by_id[adj.adopts]
        for x in (by_id[i] for i in adj.settles):
            if x is not adopted and x.decision in ("missing", "boundary"):
                adjudicated.pop(key_of(x), None)
        if adopted.decision != "complete":
            adjudicated[key_of(adopted)] = adopted
    return {
        "first": first,
        "second": second,
        "adjudicated": adjudicated,
        "adjudications": valid,
        "invalid_adjudications": invalid,
        "order": order,
    }


def effective(decisions: list[Decision]) -> dict[tuple, Decision]:
    """The published review state by key: the first reviewer's decisions in
    force, after each valid adjudication (layers)."""
    return layers(decisions)["adjudicated"]


def load_records(records_dir) -> dict[str, dict]:
    records = {}
    for path in sorted(records_dir.glob("entries-*.jsonl")):
        with path.open(encoding="utf-8") as source:
            for line in source:
                r = json.loads(line)
                records[r["id"]] = r
    return records
