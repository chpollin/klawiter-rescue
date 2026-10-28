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
---

# Project knowledge

Start with [Current status](status.md): what is verified, what remains open, and the next acceptance steps. The latest [Journal](journal.md) entry records the terminal working state.

## Maintained documents

| Document | Responsibility |
|---|---|
| [Status](status.md) | current evidence snapshot and honest completion assessment |
| [Plan](plan.md) | the two milestones, their entry and exit conditions and the status tracker of the work ahead |
| [Handoff](handoff.md) | the inbox of received results that still wait to be checked, integrated or rejected |
| [About](about.md) | origin, responsibilities, scholarly context, how the bibliography is cited, and publication mandate |
| [Data](data.md) | source scope, entity levels, field meaning, provenance and uncertainty |
| [Pipeline](pipeline.md) | transformations, dependencies and reproducibility boundaries |
| [Specification](specification.md) | user groups, research tasks with acceptance criteria, scholar-centred requirements and the open questions they raise |
| [Design](design.md) | design stance, rule hierarchy, the record desk and page check tool, token roles, component rules and the departures of the committed code |
| [Frontend](frontend.md) | routes, dashboard interactions, curation and export behaviour |
| [Testing](testing.md) | test contracts, oracle maintenance, browser validation and evidence limits |
| [Production readiness](production-readiness.md) | ratified decisions, operator principles, what the operator accepts, and measurable acceptance criteria |
| [Print volumes](print-volumes.md) | structure, conventions, reference system and sigla of the three print-volume PDFs, and what a reader of the files has to expect |
| [Print pipeline](print-pipeline.md) | stages, probes, benchmark, structured objects, reading gaps and reproduction of the print strand, with its figures in the local reports |
| [Print viewer](print-viewer.md) | the local card workbench in which persons review the print readings and the claims between records |
| [Merged bibliography](print-wiki-merge.md) | record and claim model relating print and wiki, how results are checked, goal, measurement rules, plan and milestones toward the merged Klawiter bibliography |
| [Coordination](coordination.md) | roles, path ownership and result reporting of the parallel sessions on this repository |
| [Documentation](documentation.md) | Markdown ownership, maintenance rules and historical/generated evidence |
| [Journal](journal.md) | chronological decisions and completed sessions |

[README](../README.md) owns setup and common commands. [CLAUDE.md](../CLAUDE.md) owns agent instructions. The [pipeline entry](../pipeline/README.md) and [patch-store contract](../data/corrections/README.md) serve their local directories.

## Review evidence

These are dated observations, not live task lists. Follow their status links before acting on an old finding.

| Record | Evidence |
|---|---|
| [Review 0.9](review-0.9.md) | August release review |
| [Completion review, 5 September](project-review-2026-09-05.md) | source/model/frontend gaps and original score |
| [Fixture review](test-fixture-review-2026-09-05.md) | complete twenty-page source fixtures and initial mismatch inventory |
| [Independent evaluation](independent-evaluation-2026-09-05.md) | two blind source reviews and test review |
| [Technical remediation](technical-remediation-2026-09-05.md) | implemented corrections, reviewed impact and verification |
| [Evaluation artifacts](evaluations/2026-09-05/manifest.json) | hashed source excerpts and machine-readable review results |
| [Owner worksheet](evaluations/2026-09-05/owner-evaluation.md) | five concrete domain and usability acceptance cases |
| [Test review](evaluations/2026-09-05/test-review.md) | independent review of the test refactoring of 5 September, with its file links made repository-relative |
| [Blog claim check](evaluations/2026-10-23/blog-v4-claims.md) | every statement of the blog post v4 against the repository at b0c63ea, German, with operator slots |
| [Print viewer review](evaluations/2026-10-24/print-viewer-review.md) | independent review of the print viewer and card board, with the findings that endanger the measurement |

## Reading paths

- Re-entry: [Status](status.md) → [Handoff](handoff.md) → [Plan](plan.md) → latest [Journal](journal.md) → `git status -sb`.
- Data work: [Data](data.md) → [Pipeline](pipeline.md) → [Testing](testing.md).
- Interface work: [Specification](specification.md) → [Design](design.md) → [Frontend](frontend.md) → [Print viewer](print-viewer.md) → [Testing](testing.md).
- Print volumes: [Merged bibliography](print-wiki-merge.md) → [Print volumes](print-volumes.md) → [Print pipeline](print-pipeline.md) → [Data](data.md) → [Print viewer](print-viewer.md).
- Acceptance: [Production readiness](production-readiness.md), What the operator accepts → [Merged bibliography](print-wiki-merge.md), Goal → [Status](status.md).

Code, versioned decisions and generated validation reports take precedence over descriptive documentation. Volatile counts come from the quality report, gate manifests and frontend dataset; the current prose snapshot lives only in Status. A green technical gate does not establish complete extraction or scholarly accuracy.
