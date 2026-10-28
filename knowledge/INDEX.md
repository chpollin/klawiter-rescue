---
title: Stefan Zweig Bibliography (Klawiter) — Project Knowledge
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: maintained
language: en
created: 2026-04-12
updated: 2026-10-28
template:
  name: Vorlage Index
  version: 0.4
  url: https://dhcraft.org/Promptotyping/promptotyping-document/index
related: [status, plan, handoff, project, data, specification, design, governance, journal]
---

# Project knowledge

This index routes agents and people through the knowledge of the Stefan Zweig Bibliography (Klawiter), names the document responsible for each kind of change and defines the terms the documents share. Start with [Current status](status.md), which says what is verified, what remains open and which acceptance steps come next. The latest [Journal](journal.md) entry records the terminal working state.

## Documents

| Document | Function | Responsibility | Update |
|---|---|---|---|
| [Status](status.md) | project-specific status snapshot | current evidence snapshot with its date and source artifacts, honest completion assessment and the one place for volatile figures | after a verified change of data, gates or acceptance |
| [Plan](plan.md) | Planning | milestones with entry and exit conditions, tracks and the orchestration of parallel sessions, and the status tracker of future work | when work is accepted, reordered or finished |
| [Handoff](handoff.md) | Handoff | received results still waiting to be checked, integrated or rejected; a point leaves it with a journal record | on receipt or processing of a point |
| [Project](project.md) | Charter | origin, responsibilities, data integrity, research and publication frame, standards, how the bibliography is cited, licences and rights | when identity, mandate or rights change |
| [Data and model](data.md) | Material | source scope, entity levels, field meaning, statement states, provenance, uncertainty and curation boundaries | on a change of schema, source scope or statement states |
| [Pipeline architecture](pipeline-architecture.md) | Architecture | stages, transformations, dependencies and the reproducibility boundary of the production run; `pipeline/README.md` is its local quick entry | on a change of stages or boundaries |
| [Specification](specification.md) | Specification | user groups, research tasks with acceptance criteria, requirements of the interface, the requirements and acceptance of the card workbench, open questions | on a change of requirements or decisions |
| [Design](design.md) | Design | design stance, rule hierarchy, record desk, card workbench, page check tool, design system, accessibility minima and the departures of the committed code | on a change of the design system or a surface |
| [Frontend architecture](frontend-architecture.md) | Architecture | modules, routes, interactions, curation and export behaviour of the published reader | on a change of routes or contracts |
| [Testing](testing.md) | Quality Assurance | the one list of check commands, test layers including the frontend checks, oracle maintenance and the limits of what is asserted | on a change of checks or contracts |
| [Governance](governance.md) | Governance | ratified decisions, operator principles, what the operator accepts, release scope, parallel sessions and the rules of documentation | on an operator decision or a rule change |
| [Print volumes](print-volumes.md) | Domain Knowledge | structure, conventions, reference system and sigla of the three print-volume PDFs, and what a reader of the files has to expect | when a reading of the volumes is verified or corrected |
| [Print pipeline](print-pipeline.md) | Architecture of the print strand | stages, probes, benchmark, structured objects, reading gaps and reproduction of the print strand, with its figures in the local reports | on a change of stages or measurement |
| [Merged bibliography](print-wiki-merge.md) | Specification of the merge | record and claim model relating print and wiki, how results are checked, goal, measurement rules, steps and milestones | on a change of the merge model or its measurement |
| [Journal](journal.md) | Provenance | chronological decisions and completed sessions, newest first; old statements stay as history | after a substantively coherent transition |

The print documents carry no print text and paraphrase with PDF pages instead.

## Files outside the knowledge folder

| Files | Responsibility |
|---|---|
| `README.md` | setup, common commands, a concise project introduction and links |
| `CLAUDE.md` | the sole repository agent instruction; no parallel `AGENTS.md` |
| `pipeline/README.md` | local quick entry to the stages, linking back to [Pipeline architecture](pipeline-architecture.md) |
| `data/corrections/README.md` | exact patch-store examples, validation and replay semantics |
| `.github/ISSUE_TEMPLATE/*.md` | explicitly labelled proposals that point to the current scope and claim no implemented evaluation feature |
| `snapshots/*.md` | dated reviews and change records; a current-status pointer may be added, the original findings stay |
| `snapshots/evaluations/2026-09-05/` | independent review, owner worksheet and hashed evidence; the manifest hashes are maintained when bytes change |
| `snapshots/evaluations/2026-10-*/` | dated claim checks and reviews; their findings stay, and their closure is recorded in the responsible document |
| `data/output/edition-samples/REVIEW.md`, `data/output/unmatched_locations_review.md` | evidence tied to its sampled or generated data, preserved as an artifact |

## Storage zones

- `knowledge/` holds the maintained Promptotyping documents, including `handoff.md` as the process inbox.
- `snapshots/` holds dated reviews, audits and evaluation evidence, listed below.
- `data/output/` and `docs/data/` hold the generated artifacts of the production run, and `data/print/` the local print strand, which Git ignores.

| Snapshot | Evidence |
|---|---|
| [Release review](../snapshots/release-review-2026-08-27.md) | August release review of version 0.9 |
| [Completion review, 5 September](../snapshots/project-review-2026-09-05.md) | source, model and frontend gaps and the original score |
| [Fixture review](../snapshots/test-fixture-review-2026-09-05.md) | complete twenty-page source fixtures and the initial mismatch inventory |
| [Independent evaluation](../snapshots/independent-evaluation-2026-09-05.md) | two blind source reviews and a test review |
| [Technical remediation](../snapshots/technical-remediation-2026-09-05.md) | implemented corrections, reviewed impact and verification |
| [Evaluation artifacts](../snapshots/evaluations/2026-09-05/manifest.json) | hashed source excerpts and machine-readable review results |
| [Owner worksheet](../snapshots/evaluations/2026-09-05/owner-evaluation.md) | five concrete domain and usability acceptance cases |
| [Test review](../snapshots/evaluations/2026-09-05/test-review.md) | independent review of the test refactoring of 5 September, with its file links made repository-relative |
| [Blog claim check](../snapshots/evaluations/2026-10-23/blog-v4-claims.md) | every statement of the blog post v4 against the repository at b0c63ea, German, with operator slots |
| [Print viewer review](../snapshots/evaluations/2026-10-24/print-viewer-review.md) | independent review of the print viewer and card board, with the findings that endanger the measurement |

These are dated observations. Follow their status links before acting on an old finding.

## Reading paths

- Re-entry: [Status](status.md) → [Handoff](handoff.md) → [Plan](plan.md) → latest [Journal](journal.md) → `git status -sb`.
- Data work: [Data and model](data.md) → [Pipeline architecture](pipeline-architecture.md) → [Testing](testing.md).
- Interface work: [Specification](specification.md) → [Design](design.md) → [Frontend architecture](frontend-architecture.md) → [Testing](testing.md).
- Print volumes: [Merged bibliography](print-wiki-merge.md) → [Print volumes](print-volumes.md) → [Print pipeline](print-pipeline.md) → [Data and model](data.md) → [Design](design.md#card-workbench).
- Acceptance and authority: [Governance](governance.md#what-the-operator-accepts) → [Merged bibliography](print-wiki-merge.md#goal) → [Status](status.md).

Code, versioned decisions and generated validation reports take precedence over descriptive documentation. Volatile counts come from the quality report, the gate manifests and the frontend dataset, and the current prose snapshot lives only in Status. A green technical gate does not establish complete extraction or scholarly accuracy.

## Convention

This knowledge base follows the [Promptotyping Document convention](https://dhcraft.org/Promptotyping/#konvention-v0.1), which governs the naming contract, the frontmatter schema, the routing of documents and their structural principles. Its registered deviations, the status values `maintained`, `historical` and `implementation-record` and the project-specific [Status](status.md), stand in [Governance](governance.md#status-vocabulary).

## Terms

### Confirmed

A source-bound statement decided by a person or confirmed by an exact deterministic rule. Only a `confirm` or `correct` by such a producer publishes a link, closes a claim or confirms an edition, and a test fixture confirms nothing.

Used in [Data and model](data.md#statement-states), [Governance](governance.md#operator-principles).

### Contested

An open statement with a stable claim identifier, source evidence, competing interpretations, review history and an open decision status. It stays visible in the final data and in the interface and never becomes a confirmed relation.

Used in [Data and model](data.md#statement-states), [Design](design.md#contested-block).

### Gap by rule

A field the binding rule emptied, recorded with the provenance `rule-gap` and the rule that `ruleGaps` names. It differs from a gap in the source, whose provenance is `missing`, and verification counts it apart from a false negative.

Used in [Data and model](data.md#provenance-and-review-scope), [Design](design.md#decisions-for-increment-2).

### Print address

The compiler's address of an entry in the printed bibliography, a section letter and a number, with `A1` or `A2` appended to the section letter in the addenda ("F 47", "HA1 34"). Research and the trade cite it, and the merged bibliography may carry it as a citable alias. A print address cited in a wiki page is read syntactically and asserts no identity with a print record.

Used in [Print volumes](print-volumes.md#reference-system), [Data and model](data.md#cited-print-addresses), [Project](project.md#how-the-bibliography-is-cited).

### Producer

The class of whoever produced or decided a statement, `person`, `rule` or `llm-agent`, kept apart from what was stated. `pipeline/lib/producers.py` is the closed register of deciders by producer class, and an unregistered decider fails the build. Only a person or an exact deterministic rule confirms.

Used in [Data and model](data.md#statement-states), [Governance](governance.md#operator-principles).

### Proposed

An unreviewed statement, or one decided by a Large Language Model (LLM) agent, including a decision taken under the operator's delegation. It may come from a rule, an LLM or a person, it may be shown with its passage and producer, and it publishes nothing and never overwrites a rule value.

Used in [Data and model](data.md#statement-states), [Governance](governance.md#operator-principles).
