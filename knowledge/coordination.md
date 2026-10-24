---
title: Coordination of parallel sessions
status: maintained
language: en
created: 2026-10-23
updated: 2026-10-24
related: [print-wiki-merge, frontend, journal]
---

# Coordination of parallel sessions

Since 2026-10-23 two sessions work on this repository at the same time, in one working tree. This document records who owns which paths, how results come back and who decides what. It adapts the Research Mission Control method of the operator's vault to this one project: two roles, no lane board, and the project's own knowledge documents as the only state. Coordination is kept to what prevents parallel writes and unchecked claims.

## Roles

Research coordinator
: Holds the plan of the merged Klawiter bibliography ([Merged bibliography](print-wiki-merge.md)) and the print strand, owns the shared knowledge documents, checks results of the other session against their evidence before they enter canonical knowledge, and prepares decisions for the operator.

AI operator
: Carries out a bounded assignment given by the operator, since 2026-10-24 the interface of both strands: the production frontend and the card workbench of the print strand. Its first assignment is the record card with the provenance chain of every value. Writes only to its own paths, takes data as the pipelines write them, and reports results with evidence. The research coordinator checks each result against the tests, the record coverage test and read screenshots before it is committed.

Operator
: The human project owner. Decides goals, rights, publication, vocabulary that enters the data model, and acceptance. Agent reviews, including simulated user evaluations, never stand in for that acceptance.

## Paths

| Owner | Paths |
|---|---|
| Research coordinator | `pipeline/print_volumes/` except the interface files of `viewer/`, `data/print/` (local only), `knowledge/` |
| AI operator | `docs/index.html`, `docs/js/`, `docs/css/`, and in `pipeline/print_volumes/viewer/` the files `cards.html`, `cards.js`, `cards.css` and `render.js` |
| Neither without a verified finding | production code and data (`pipeline/lib/`, `pipeline/*.py`, `docs/data/`, `docs/vocab/`, `data/` outside `data/print/`); changes there go through the research coordinator |

The AI operator's paths pass to it once the running repair of the card workbench and the running wiki data batch, which also changes `docs/js/` and `docs/css/`, are committed, so that no two sessions write the same file. A change the interface needs in the data (a field, a projection, a producer label) goes to the research coordinator as a request with its reason. The checks `check_render.mjs`, `check_review.mjs` and `smoke.mjs` stay with the research coordinator, because they are the acceptance of the interface and not part of it.

Each session stages its own files by explicit path and commits only its own units. Pushes stay with the operator.

## Messages and results

The sessions exchange messages directly (Claude Code cross-session messages). A message is transport, never state: what holds lives in commits and in the knowledge documents. A finding reported by one session counts as unverified for the other until it is checked against code or data. At the end of an assignment the AI operator returns a compact report with the fields state, result, evidence (paths, commits), verification, deviation, next action, at most one question for the operator, and blocker.

## Tracks

The operator set on 2026-10-23 that the whole project advances together: the merged bibliography, the correctness of the published wiki data, the interface, the blog post, the DIA-XAI follow-up proposal and the vault knowledge, each tested, verified and reviewed critically before it counts, with milestones planned and reported. Each track has one owner and one plan.

| Track | Owner | Plan and milestones | Review before a milestone closes |
|---|---|---|---|
| Merged bibliography (print strand) | research coordinator | [Merged bibliography](print-wiki-merge.md), Milestones | independent agent review of method, code and document |
| Published wiki data | research coordinator | [Merged bibliography](print-wiki-merge.md), Wiki data true to their source passage; [Status](status.md) | full gate of CLAUDE.md, invariants over all records, fresh-context reviews of data fidelity, interface and tests after each fix batch |
| Interface | AI operator, from 2026-10-24 | [Merged bibliography](print-wiki-merge.md), Interface milestones; [Print viewer](print-viewer.md); [Frontend](frontend.md) | tests, record coverage test and read screenshots by the coordinator; a fresh-context review of the interface before a milestone closes |
| Blog post | AI operator | drafted outside the repository, claims checked against it, deployed by the operator | claim check against the artefacts; fresh-context review of the text commissioned by the coordinator |
| DIA-XAI proposal | AI operator drafts, operator decides | kept in the dia-xai repository; since 2026-10-23 the operator's team draft "Grounds for Use" is the basis, the agent draft v1.4 supplies material | fresh-context reviews of research question, argument and evidence commissioned by the coordinator |
| Vault knowledge | a session started in the vault | handoff list prepared by the coordinator; repository sessions read the vault, never write it | vault conventions and audit |

The coordinator reports to the operator as a short presentation per milestone reached and on request, with result, meaning, risks and the decisions needed.

## Orchestration

The research coordinator holds the overall plan ([Merged bibliography](print-wiki-merge.md), Plan and Milestones) and orchestrates the AI operator's work through the table below. The table holds only the dependencies between the two sessions. When a dependency is met, the session that delivers it messages the other; when the coordinator needs the operator's next result, it asks to be notified when the operator session goes idle instead of polling.

| Dependency | Delivered by | Needed for | Serves in the overall plan |
|---|---|---|---|
| verified regeneration of `docs/data` and `data/output` after the pipeline fixes | coordinator | interface, blog post | correct wiki data as the base of every concordance |
| `publicationIds` on field matches, delivered 2026-10-23 (a4dbd63) where the wiki line lies in a hash-verified publication slice | coordinator (p07) | edition-level print slot | step 7, matches at publication level |
| committed repair of the card workbench | coordinator | handover of the interface paths | interface milestone One reader |
| record card with the provenance chain of every value | AI operator | coordinator's check against tests, record coverage and screenshots | Goal, every value with passage, producer and state |
| defects found in production data | either session | coordinator verifies, fixes and regenerates | correct wiki data |
| operator decision on the twenty fixture-based place decisions, taken 2026-10-23 (a fixture confirms nothing) | operator | blog post, display wording, data.md | step 1, meaning of `confirmed` |
| decision whether delegation to LLM agents confirms, taken 2026-10-24 under the operator principles (it does not; agent decisions are proposals) | main instance | blog post, production labels | step 1, meaning of `confirmed` |
| push and deploy of the local commits | operator | blog post, proposal commit citations, public application | correct wiki data in public |

A result of the AI operator enters canonical knowledge only after the coordinator has checked it against its evidence. A prototype element that becomes part of the plan, such as the producer labels or the side-by-side print pane, moves into the plan's step it serves by the coordinator's write-back.

## Decisions that stay with the operator

- Display vocabulary that would change the statement states (`proposed`, `confirmed`, `contested`) or their meaning. A display may name the producer next to the state (rule, LLM agent, person); a fourth state needs a decision.
- Everything listed in [Production readiness](production-readiness.md), What the operator accepts.
