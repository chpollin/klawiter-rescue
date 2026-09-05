---
title: Production Readiness and Acceptance
status: maintained
language: en
updated: 2026-09-05
related: [status, data, pipeline, testing, frontend, journal]
---

# Production readiness and acceptance

A reproducible data core and an accepted research product are different milestones. The current implementation and open work are recorded in [Status](status.md); this document owns the durable acceptance contract and ratified decisions. “Technically complete” is not an adequate description while known model, provenance and interface gaps remain.

## Ratified scope

The July 2026 decisions, ratified on 19 July, remain in force:

1. Decompose multi-edition pages into work and edition.
2. Include reconciliation in the deliverable.
3. Treat the wiki/print merge as a later stage.
4. Use versioned patch export as the canonical write-back route.

On 21 August, independent agentic source review and reconciliation became the initial evidence; external scholarly review adds validation. Contested cases were explicitly retained as final-data objects, distinguishable from confirmed relations. The exact decisions and their chronology remain in [Journal](journal.md).

The 27 August publication frame described version 0.9 as the release candidate and reserved 1.0 acceptance and its tag for the operator. Do not infer a new release from document frontmatter, a filename, a passing test count or this refactor. A separate Klawiter paper and blog post are outside the repository mandate. Live external write-backs, the wiki/print merge and institutional work-identity decisions remain separate work.

The operator's 5 September request explicitly reopens Explore as an interactive dashboard with linked information visualizations. Earlier documentation deferring cross-view interaction is superseded by that request.

## Acceptance matrix

| Capability | Required evidence | Current evidence and remaining work |
|---|---|---|
| Current-source preservation | exact source/canonical/frontend ID reconciliation; documented stubs | census and default tests; historical and archived content must remain explicitly scoped |
| Correct bibliographic units | source-bound publications/contributions with coherent field scope | Gate 1 segmentation exists; graph field coverage and compound pages outside its grammar remain open |
| Uncertainty and authority links | proposed/confirmed/contested separation; exact evidence and deterministic decisions | Gate 1/2 validators; scholarly adjudication of open cases remains distinct |
| Canonical curation | one released correction reaches all intended graphs, exports, histories and reports | frontend replay is hardened; full propagation is still open |
| Research interface | exact filter handover, source access, useful visualizations, clear review scope, edition navigation | browser/Node evidence for implemented paths; edition browsing and full task acceptance remain open |
| Accessibility and performance | keyboard/touch paths, readable contrast, mobile fit, representative device/network budgets | targeted checks support specific paths; no comprehensive certification or performance budget yet |
| Repeatability | locked environment, both gate checks, reviewed deterministic artifact comparison | full local locked-uv rebuild and reviewed-manifest checks pass; remote CI execution remains distinct |
| Public release | curated source package, consistent metadata, explicit release scope and acceptance | operator/publication work remains; archival originals stay unchanged |

Technical verification compares implementation with these contracts. Validation compares the product with real scholarly questions and users' interpretation of the source. Neither replaces the other.

## Control loops

The development loop identifies error classes, reviews corpus-wide changes and reruns affected tests plus dependent gates. Lower field population is acceptable when a false assertion is removed. Baselines record exact remaining failures and reviewed improvements; they must not absorb new regressions.

The curation loop reviews individual fields, editions and authority candidates against exact evidence. Browser changes remain local until a released patch is integrated and rebuilt. A reviewed place does not certify an entry's year or translator.

## Decisions requiring domain or publication responsibility

The existing adaptation claim preserves the unresolved work identity without data loss. Its final identity, the release declaration, public archive scope and publication/citation form remain with the responsible people. These decisions do not prevent bounded technical repairs or source transcription checks.

Use the [five-case worksheet](evaluations/2026-09-05/owner-evaluation.md) to evaluate concrete edition boundaries, contribution roles, conflicting imprints and the research workflow. The questions are not a request to reapprove the work/edition principle.

## Evidence ownership

- [Data](data.md): source and entity contracts, statuses and correction limits.
- [Pipeline](pipeline.md): stage order, inputs and deterministic boundary.
- [Testing](testing.md): executable checks, independent samples and CI limits.
- [Frontend](frontend.md): user-facing behaviour and export scope.
- [Status](status.md): one prioritized current work list and current artifact links.
- Dated reviews and `knowledge/evaluations/`: observations at a particular state, preserved without silently rewriting history.
