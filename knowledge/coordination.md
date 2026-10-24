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

## Tracks

The operator set on 2026-10-23 that the whole project advances together: the merged bibliography, the correctness of the published wiki data, the lab, the blog post, the DIA-XAI follow-up proposal and the vault knowledge, each tested, verified and reviewed critically before it counts, with milestones planned and reported. Each track has one owner and one plan.

| Track | Owner | Plan and milestones | Review before a milestone closes |
|---|---|---|---|
| Merged bibliography (print strand) | research coordinator | [Merged bibliography](print-wiki-merge.md), Milestones | independent agent review of method, code and document |
| Published wiki data | research coordinator | [Merged bibliography](print-wiki-merge.md), Wiki data true to their source passage; [Status](status.md) | full gate of CLAUDE.md, invariants over all records, fresh-context reviews of data fidelity, interface and tests after each fix batch |
| Lab frontend | AI operator | [Lab frontend](lab-frontend.md), L1 to L7 | independent reviews in the lab plan; coordinator's model check |
| Blog post | AI operator | [Lab frontend](lab-frontend.md), B1 to B4 | claim check against the artefacts; fresh-context review of the text commissioned by the coordinator |
| DIA-XAI proposal | AI operator drafts, operator decides | [Lab frontend](lab-frontend.md), A1 to A4; since 2026-10-23 the operator's team draft "Grounds for Use" is the basis, the agent draft v1.4 supplies material | fresh-context reviews of research question, argument and evidence commissioned by the coordinator |
| Vault knowledge | a session started in the vault | handoff list prepared by the coordinator; repository sessions read the vault, never write it | vault conventions and audit |

The coordinator reports to the operator as a short presentation per milestone reached and on request, with result, meaning, risks and the decisions needed.

## Orchestration

The research coordinator holds the overall plan ([Merged bibliography](print-wiki-merge.md), Plan and Milestones) and orchestrates the AI operator's work through the table below. The table holds only the dependencies between the two sessions. The milestones of the lab stay in [Lab frontend](lab-frontend.md) (Plan) and the steps of the merge in the plan. When a dependency is met, the session that delivers it messages the other; when the coordinator needs the operator's next result, it asks to be notified when the operator session goes idle instead of polling.

| Dependency | Delivered by | Needed for | Serves in the overall plan |
|---|---|---|---|
| verified regeneration of `docs/data` and `data/output` after the pipeline fixes | coordinator | lab L3 data preparation, blog B2 | correct wiki data as the base of every concordance |
| local print matches `data/print/derived/lab/print-links.json`, copied by the operator to the ignored `docs/lab/local/` | coordinator (p07) | lab print slot (E6) | next milestone, matches visible to the operator |
| `publicationIds` on field matches, delivered 2026-10-23 (a4dbd63) where the wiki line lies in a hash-verified publication slice | coordinator (p07) | edition-level print slot | step 7, matches at publication level |
| interface specification and its critical review (L2) | AI operator | coordinator's check of states, producer labels and print display against the model | steps 1 and 9, display of claim states |
| running prototypes and evaluation (L4 to L6) | AI operator | coordinator's integration of findings; the adjudication view of step 9 builds on what holds | step 9, adjudication through the curation interface |
| defects found in production data | either session | coordinator verifies, fixes and regenerates | correct wiki data |
| operator decision on the twenty fixture-based place decisions, taken 2026-10-23 (a fixture confirms nothing) | operator | blog B1, display wording, data.md | step 1, meaning of `confirmed` |
| operator decision whether delegation to LLM agents confirms; until then the producer is named next to the state | operator | blog B1, lab and production labels | step 1, meaning of `confirmed` |
| push and deploy of the local commits | operator | blog B4, proposal commit citations, public application | correct wiki data in public |

A result of the AI operator enters canonical knowledge outside `lab-frontend.md` only after the coordinator has checked it against its evidence. A prototype element that becomes part of the plan, such as the producer labels or the side-by-side print pane, moves into the plan's step it serves by the coordinator's write-back.

## State at the pause of 2026-10-23

Both sessions paused on 2026-10-23 at the operator's request; all commits are local and unpushed.

- Lab: on 2026-10-24 the AI operator reported L5 reached by agent walkthrough and one independent agent review, with no person involved (commits f348bf4 to 8ec4c12, local): editions by language and year in the work view, the provenance chain per value (S2.6), verification candidates at page-level gaps, search ordered by title, the agent label naming that no person decided, and record exports in a tested module. The coordinator confirmed the commits and the lab tests; the walkthrough figures stand as reported ([Lab frontend](lab-frontend.md)). Two production findings of that report wait for verification: the production label omits that no person decided, and some flat translator values carry a double space that no exact source occurrence matches.
- Print strand, 2026-10-24: every print object is a structured, validated record exported as validated JSON-LD with a provenance chain per value and shown in a local viewer, which records human review decisions into a separate layer measured on a frozen review sample ([Print volumes](print-volumes.md), Structured objects). Wrong-value classes of the fourth review are open, and no person has reviewed yet.
- Blog: v4 verified against the repository ([claim check](evaluations/2026-10-23/blog-v4-claims.md)); a v5 tab in the shared blog document awaits the operator's slots and the deploy.
- Proposal: the team draft "Grounds for Use" is the basis; a v1.7 with evidence corrections and new team questions lies with the operator; reviews and research reports are filed in the dia-xai repository.
- Wiki data: the frontend fix batch is committed; the pipeline fix batch (corpus-wide defects, invariants over all records) is verified and committed before the pause or resumed after it ([Status](status.md)).
- Print strand: concordance with publication resolution and ranking, field check, edition lines and language scope fixed, blind sample frozen and waiting for a person ([Merged bibliography](print-wiki-merge.md)).
- Open for a later round: one shared source for the producer vocabulary used by the production frontend and the lab labels; compaction of the journal.

## Decisions that stay with the operator

- Display vocabulary that would change the statement states (`proposed`, `confirmed`, `contested`) or their meaning. A display may name the producer next to the state (rule, LLM agent, person); a fourth state needs a decision.
- Whether a prototype replaces or extends the production frontend.
- Everything listed under Frame in the open questions of [Merged bibliography](print-wiki-merge.md).
