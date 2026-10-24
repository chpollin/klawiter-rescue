"""The question layer: event shapes, the person-only answer, checks and fold."""

import pytest
from _questions import QuestionIn, fold, problem, stamp
from pydantic import ValidationError

ASK = {"event": "ask", "author": "a reviewer", "by": "person", "text": "Why?"}


def test_ask_needs_text_and_no_question():
    with pytest.raises(ValidationError):
        QuestionIn(**{**ASK, "text": " "})
    with pytest.raises(ValidationError):
        QuestionIn(**ASK, question="0" * 32)


def test_only_a_person_answers():
    q = "a" * 32
    with pytest.raises(ValidationError, match="only a person answers"):
        QuestionIn(
            event="answer",
            author="x",
            by="agent",
            question=q,
            resolution="keep-as-read",
        )
    with pytest.raises(ValidationError, match="resolution"):
        QuestionIn(event="answer", author="x", by="person", question=q)


def test_only_a_rule_or_agent_proposes_and_seeds():
    with pytest.raises(ValidationError, match="proposes"):
        QuestionIn(**ASK, proposal="this")
    with pytest.raises(ValidationError, match="key"):
        QuestionIn(**ASK, key="some-key")
    QuestionIn(**{**ASK, "by": "agent"}, proposal="this", key="some-key")


def test_case_ids_of_objects_and_apparatus_items():
    for oid in (
        "I/A/2#1",
        "A2/L/p1264l18#2",
        "I/index-a/p790l44#1",
        "A1/index-b/p441l3c2#1",
    ):
        QuestionIn(**ASK, cases=[{"object": oid}])
    with pytest.raises(ValidationError):
        QuestionIn(**ASK, cases=[{"object": "I/A/2"}])


def test_problem_checks_question_key_and_objects():
    asked = stamp(QuestionIn(**{**ASK, "by": "agent"}, key="k-one"))
    log = [asked]
    ids = {"I/A/2#1"}
    case = QuestionIn(
        event="case",
        author="x",
        by="person",
        question=asked.id,
        cases=[{"object": "I/A/2#1"}],
    )
    assert problem(case, log, ids) is None
    assert (
        problem(case.model_copy(update={"question": "b" * 32}), log, ids)
        == "no such question"
    )
    again = QuestionIn(**{**ASK, "by": "agent"}, key="k-one")
    assert problem(again, log, ids) == "a question with this key exists"
    unknown = QuestionIn(**ASK, cases=[{"object": "I/B/9#1"}])
    assert problem(unknown, log, ids) == "no such object: I/B/9#1"


def test_fold_categorize_cases_answer_reopen():
    asked = stamp(QuestionIn(**ASK, category="reading", cases=[{"object": "I/A/2#1"}]))
    q = asked.id
    events = [
        asked,
        stamp(
            QuestionIn(
                event="categorize",
                author="x",
                by="person",
                question=q,
                answerer="operator",
            )
        ),
        stamp(
            QuestionIn(
                event="case",
                author="x",
                by="person",
                question=q,
                cases=[{"object": "I/A/3#1", "path": "title"}],
            )
        ),
        stamp(
            QuestionIn(
                event="answer",
                author="x",
                by="person",
                question=q,
                resolution="change-rule",
                text="fix it",
            )
        ),
    ]
    s = fold(events)[q]
    assert (s["category"], s["answerer"]) == ("reading", "operator")
    assert [c["object"] for c in s["cases"]] == ["I/A/2#1", "I/A/3#1"]
    assert s["answer"]["resolution"] == "change-rule"
    events.append(
        stamp(QuestionIn(event="reopen", author="x", by="person", question=q))
    )
    s = fold(events)[q]
    assert s["answer"] is None and len(s["events"]) == 5
