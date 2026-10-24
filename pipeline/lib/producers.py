"""Who produced a review decision, and whether that producer may confirm.

Only an exact deterministic rule or a person confirms; an LLM agent proposes
and never confirms (knowledge/production-readiness.md, Operator principles).
A decision by an LLM agent stays in its decision file as evidence, but it
publishes no link, closes no claim and confirms no edition.
"""

from __future__ import annotations

PERSON = "person"
RULE = "rule"
LLM_AGENT = "llm-agent"
CONFIRMING_PRODUCERS = frozenset({PERSON, RULE})

# Every decider the decision inputs name, by producer class. The register is
# closed: a decider absent from it fails the build, because a decision whose
# producer is unknown can be counted neither as a confirmation nor as a
# proposal. Revising whether a class confirms is a change of the operator
# principle, never of a decision file.
DECIDER_CLASSES = {
    # The location and work review of August and September 2026.
    "independent-verification-agent": LLM_AGENT,
    # The main agent of a session deciding under the operator's delegation.
    "main-instance": LLM_AGENT,
    "klawiter:agent/main-instance": LLM_AGENT,
    # The verifier of the edition sample reconciliation of 2026-08-21.
    "klawiter:agent/reconciliation-verifier": LLM_AGENT,
    # The role a released browser decision export names (docs/js/edit.js).
    "Editor (SZD)": PERSON,
}

# The decider of the edition sample reconciliation; its artifact names the
# verifier agent and two agent reviewers, no person.
EDITION_SAMPLE_DECIDER = "klawiter:agent/reconciliation-verifier"


def producer_class(decider: str) -> str:
    """The producer class of a decider, or a ValueError for an unknown one."""
    try:
        return DECIDER_CLASSES[decider]
    except KeyError:
        raise ValueError(f"Decider has no registered producer class: {decider!r}")


def may_confirm(decider: str) -> bool:
    """Whether the decider's class confirms rather than proposes."""
    return producer_class(decider) in CONFIRMING_PRODUCERS


def confirms(decision: dict) -> bool:
    """Whether a reconciliation decision produces a confirmed relation."""
    return decision["action"] in {"confirm", "correct"} and may_confirm(
        decision["decidedBy"]
    )
