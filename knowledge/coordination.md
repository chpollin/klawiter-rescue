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

## Orchestration

The research coordinator holds the overall plan ([Merged bibliography](print-wiki-merge.md), Plan and Milestones) and orchestrates the AI operator's work through the table below. The table holds only the dependencies between the two sessions. The milestones of the lab stay in [Lab frontend](lab-frontend.md) (Plan) and the steps of the merge in the plan. When a dependency is met, the session that delivers it messages the other; when the coordinator needs the operator's next result, it asks to be notified when the operator session goes idle instead of polling.

| Dependency | Delivered by | Needed for | Serves in the overall plan |
|---|---|---|---|
| verified regeneration of `docs/data` and `data/output` after the pipeline fixes | coordinator | lab L3 data preparation, blog B2 | correct wiki data as the base of every concordance |
| local print matches `data/print/derived/lab/print-links.json`, copied by the operator to the ignored `docs/lab/local/` | coordinator (p07) | lab print slot (E6) | next milestone, matches visible to the operator |
| `publicationId` on field matches | coordinator (p07) | edition-level print slot | step 7, matches at publication level |
| interface specification and its critical review (L2) | AI operator | coordinator's check of states, producer labels and print display against the model | steps 1 and 9, display of claim states |
| running prototypes and evaluation (L4 to L6) | AI operator | coordinator's integration of findings; the adjudication view of step 9 builds on what holds | step 9, adjudication through the curation interface |
| defects found in production data | either session | coordinator verifies, fixes and regenerates | correct wiki data |
| operator decision on the twenty fixture-based place decisions | operator | blog B1, display wording, data.md | step 1, meaning of `confirmed` |

A result of the AI operator enters canonical knowledge outside `lab-frontend.md` only after the coordinator has checked it against its evidence. A prototype element that becomes part of the plan, such as the producer labels or the side-by-side print pane, moves into the plan's step it serves by the coordinator's write-back.

## Decisions that stay with the operator

- Display vocabulary that would change the statement states (`proposed`, `confirmed`, `contested`) or their meaning. A display may name the producer next to the state (rule, LLM agent, person); a fourth state needs a decision.
- Whether a prototype replaces or extends the production frontend.
- Everything listed under Frame in the open questions of [Merged bibliography](print-wiki-merge.md).
