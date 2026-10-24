"""Data-cleaning questions about the print records: the model, the log and its fold.

Review decisions (_review.py) say whether one value is right. Many problems are
larger than a value: a printed convention whose meaning is unknown, a reading
class that recurs across entries, a case the data model cannot hold. Such a
question is recorded once, with the cases it concerns, categorised by what kind
of problem it is and by who can answer it, and answered by a person with a
resolution. Rules and LLM agents may ask questions and propose an answer; only
a person answers, so an answer is never taken from a proposal.

The log is append-only, data/print/review/questions.jsonl, local like all print
data because cases point into the print text. Events:
- ask: a new question with its text, optional category, answerer and cases;
  a rule or agent may add a proposed answer.
- categorize: a new category or answerer for a question.
- case: further cases for a question.
- answer: a person's resolution and answer text; a later answer replaces it.
- reopen: the question is open again.
"""

import json
import os
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from _common import PRINT_DIR
from _review import PATH
from _schema import APPARATUS_ID
from annotated_types import Len
from pydantic import BaseModel, ConfigDict, Field, model_validator

LOG = PRINT_DIR / "review" / "questions.jsonl"
# The kind of problem; the viewer explains each in its help page.
CATEGORIES = (
    "reading",
    "boundary",
    "notation",
    "source",
    "model",
    "vocabulary",
    "concordance",
    "other",
)
# Who can settle it, as the open questions of knowledge/ name them.
ANSWERERS = ("operator", "domain-expert", "data-analysis", "printed-copy")
RESOLUTIONS = (
    "change-rule",
    "change-model",
    "keep-as-read",
    "source-error",
    "needs-expert",
    "out-of-scope",
)
EVENTS = ("ask", "categorize", "case", "answer", "reopen")
CASE_ID = rf"^(?:(I|A1|A2)/[A-R]/[^#\s]+|{APPARATUS_ID})#\d+$"


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class Case(_Strict):
    """An object a question concerns, optionally one of its values."""

    object: str = Field(pattern=CASE_ID, max_length=120)
    path: str | None = Field(default=None, pattern=PATH, max_length=200)
    note: str = Field(default="", max_length=300)


class QuestionIn(_Strict):
    """What the viewer or a seeding rule submits."""

    event: Literal[EVENTS]
    author: str = Field(min_length=1, max_length=80)
    by: Literal["person", "rule", "agent"]
    question: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    text: str = Field(default="", max_length=2000)
    category: Literal[CATEGORIES] | None = None
    answerer: Literal[ANSWERERS] | None = None
    cases: Annotated[list[Case], Len(0, 2000)] = []
    proposal: str = Field(default="", max_length=2000)
    resolution: Literal[RESOLUTIONS] | None = None
    # A seeding rule's stable name for its question, so a rerun adds nothing.
    key: str | None = Field(default=None, pattern=r"^[a-z0-9-]{3,80}$")

    @model_validator(mode="after")
    def _shape(self):
        e = self.event
        if (e == "ask") == (self.question is not None):
            raise ValueError("ask starts a question; every other event names one")
        if e == "ask" and not self.text.strip():
            raise ValueError("a question has its text")
        if e == "categorize" and not (self.category or self.answerer):
            raise ValueError("categorize sets a category or an answerer")
        if e == "case" and not self.cases:
            raise ValueError("case adds at least one case")
        if e == "answer":
            if self.by != "person":
                raise ValueError("only a person answers")
            if self.resolution is None:
                raise ValueError("an answer has its resolution")
        elif self.resolution is not None:
            raise ValueError(f"{e} carries no resolution")
        if self.proposal and (e != "ask" or self.by == "person"):
            raise ValueError("only a rule or agent proposes, when it asks")
        if self.key and (e != "ask" or self.by == "person"):
            raise ValueError("only a seeding rule's question has a key")
        if e not in ("ask", "case") and self.cases:
            raise ValueError(f"{e} carries no cases")
        return self


class Question(QuestionIn):
    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    at: str = Field(pattern=r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


def stamp(event: QuestionIn) -> Question:
    """The stored form: identifier and time are the server's, never the browser's."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return Question(**event.model_dump(), id=uuid.uuid4().hex, at=now)


def load_log(log=None) -> list[Question]:
    """Every logged event in order; a malformed line is an error, never skipped."""
    log = log or LOG
    if not log.exists():
        return []
    out = []
    with log.open(encoding="utf-8") as source:
        for n, line in enumerate(source, 1):
            if line.strip():
                try:
                    out.append(Question.model_validate_json(line))
                except ValueError as e:
                    raise ValueError(f"{log}:{n}: {e}") from e
    return out


def append(event: Question, log=None) -> None:
    log = log or LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as sink:
        sink.write(event.model_dump_json(exclude_none=True) + "\n")
        sink.flush()
        os.fsync(sink.fileno())


def problem(event: QuestionIn, log: list[Question], ids: set[str]) -> str | None:
    """None when the event applies to the log and the current records, else why."""
    asked = {q.id for q in log if q.event == "ask"}
    if event.question and event.question not in asked:
        return "no such question"
    if event.key and any(q.key == event.key for q in log):
        return "a question with this key exists"
    unknown = [c.object for c in event.cases if c.object not in ids]
    if unknown:
        return f"no such object: {unknown[0]}"
    return None


def fold(log: list[Question]) -> dict[str, dict]:
    """The current state of every question, in the order they were asked."""
    state: dict[str, dict] = {}
    for q in log:
        if q.event == "ask":
            state[q.id] = {
                "id": q.id,
                "text": q.text,
                "asked": {"author": q.author, "by": q.by, "at": q.at},
                "category": q.category,
                "answerer": q.answerer,
                "cases": [c.model_dump(exclude_none=True) for c in q.cases],
                "proposal": q.proposal,
                "answer": None,
                "events": [],
            }
        s = state[q.question or q.id]
        if q.event == "categorize":
            s["category"] = q.category or s["category"]
            s["answerer"] = q.answerer or s["answerer"]
        elif q.event == "case":
            s["cases"] += [c.model_dump(exclude_none=True) for c in q.cases]
        elif q.event == "answer":
            s["answer"] = {
                "resolution": q.resolution,
                "text": q.text,
                "author": q.author,
                "at": q.at,
            }
        elif q.event == "reopen":
            s["answer"] = None
        s["events"].append(
            {
                "event": q.event,
                "author": q.author,
                "by": q.by,
                "at": q.at,
                "category": q.category,
                "answerer": q.answerer,
                "resolution": q.resolution,
                "cases": len(q.cases),
            }
        )
    return state


def object_ids(records_dir) -> set[str]:
    """The identifiers of every print object and apparatus item."""
    ids = set()
    for path in sorted(records_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as source:
            for line in source:
                ids.update(o["id"] for o in json.loads(line)["objects"])
    return ids
