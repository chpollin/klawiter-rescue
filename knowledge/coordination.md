---
title: Coordination of parallel sessions
status: maintained
language: en
created: 2026-10-23
updated: 2026-10-23
related: [print-wiki-merge, frontend, journal]
---

# Coordination of parallel sessions

Since 2026-10-23 two sessions work on this repository at the same time, in one working tree. This document records who owns which paths, how results come back and who decides what. It adapts the Research Mission Control method of the operator's vault to this one project: two roles, no lane board, and the project's own knowledge documents as the only state. Coordination is kept to what prevents parallel writes and unchecked claims.

## Roles

Research coordinator
: Holds the plan of the merged Klawiter bibliography ([Merged bibliography](print-wiki-merge.md)) and the print strand, owns the shared knowledge documents, checks results of the other session against their evidence before they enter canonical knowledge, and prepares decisions for the operator.

AI operator
: Carries out a bounded assignment given by the operator, currently a scholar-centred frontend for the wiki data as prototypes with an evaluation. Writes only to its own paths and reports results with evidence.

Operator
: The human project owner. Decides goals, rights, publication, vocabulary that enters the data model, and acceptance. Agent reviews, including simulated user evaluations, never stand in for that acceptance.

## Paths

| Owner | Paths |
|---|---|
| Research coordinator | `pipeline/print_volumes/`, `data/print/` (local only), `knowledge/` except `lab-frontend.md` |
| AI operator | `docs/lab/`, `pipeline/lab/` (reads data, never part of the production run), `knowledge/lab-frontend.md` |
| Neither without a verified finding | production code and data (`pipeline/lib/`, `pipeline/*.py`, `docs/` outside `docs/lab/`, `data/` outside `data/print/`); changes there go through the research coordinator |

Each session stages its own files by explicit path and commits only its own units. Pushes stay with the operator.

## Messages and results

The sessions exchange messages directly (Claude Code cross-session messages). A message is transport, never state: what holds lives in commits and in the knowledge documents. A finding reported by one session counts as unverified for the other until it is checked against code or data. At the end of an assignment the AI operator returns a compact report with the fields state, result, evidence (paths, commits), verification, deviation, next action, at most one question for the operator, and blocker.

## Decisions that stay with the operator

- Display vocabulary that would change the statement states (`proposed`, `confirmed`, `contested`) or their meaning. A display may name the producer next to the state (rule, LLM agent, person); a fourth state needs a decision.
- Whether a prototype replaces or extends the production frontend.
- Everything listed under Frame in the open questions of [Merged bibliography](print-wiki-merge.md).
