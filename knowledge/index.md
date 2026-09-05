---
title: Klawiter Bibliography — Project Knowledge
status: maintained
language: en
updated: 2026-09-05
---

# Project knowledge

Start with [Current status](status.md): what is verified, what remains open, and the next acceptance steps. The latest [Journal](journal.md) entry records the terminal working state. This index assigns one responsibility to each maintained document.

## Maintained documents

| Document | Responsibility |
|---|---|
| [Status](status.md) | current evidence snapshot, honest completion assessment and prioritized work |
| [About](about.md) | origin, responsibilities, scholarly context and publication mandate |
| [Data](data.md) | source scope, entity levels, field meaning, provenance and uncertainty |
| [Pipeline](pipeline.md) | transformations, dependencies and reproducibility boundaries |
| [Frontend](frontend.md) | routes, dashboard interactions, curation and export behaviour |
| [Testing](testing.md) | test contracts, oracle maintenance, browser validation and evidence limits |
| [Production readiness](production-readiness.md) | ratified decisions and measurable acceptance criteria |
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

## Reading paths

- Re-entry: [Status](status.md) → latest [Journal](journal.md) → `git status -sb`.
- Data work: [Data](data.md) → [Pipeline](pipeline.md) → [Testing](testing.md).
- Interface work: [Frontend](frontend.md) → [Testing](testing.md).
- Acceptance: [Production readiness](production-readiness.md) → [Status](status.md) → [owner worksheet](evaluations/2026-09-05/owner-evaluation.md).

Code, versioned decisions and generated validation reports take precedence over descriptive documentation. Volatile counts come from the quality report, gate manifests and frontend dataset; the current prose snapshot lives only in Status. A green technical gate does not establish complete extraction or scholarly accuracy.
