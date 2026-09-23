---
title: Production Readiness and Acceptance
status: maintained
language: en
updated: 2026-09-23
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
| Public release | curated source package, consistent metadata, explicit release scope and acceptance | release scope set on 22 and 23 September (see below); `CITATION.cff`, `.zenodo.json`, licence texts, third-party notices and the source inventory aligned on 23 September, and release archives exclude `data/raw`; rights basis confirmed and institution named by the operator on 23 September; the dump stays in the public Git history and the title is set by operator decision; the acceptances remain |

Technical verification compares implementation with these contracts. Validation compares the product with real scholarly questions and users' interpretation of the source. Neither replaces the other.

## Control loops

The development loop identifies error classes, reviews corpus-wide changes and reruns affected tests plus dependent gates. Lower field population is acceptable when a false assertion is removed. Baselines record exact remaining failures and reviewed improvements; they must not absorb new regressions.

The curation loop reviews individual fields, editions and authority candidates against exact evidence. Browser changes remain local until a released patch is integrated and rebuilt. A reviewed place does not certify an entry's year or translator.

## Decisions requiring domain or publication responsibility

On 22 September the operator delegated four open questions to the main instance. Its answers are recorded with the provenance "decided by the main instance after delegation by the operator on 2026-09-22, revisable" and are listed here with their place of record.

- Worksheet cases 1 to 4 accept the display as it stood that day, recorded in the [worksheet](evaluations/2026-09-05/owner-evaluation.md#responses). Case 5 remains with the operator.
- The author of a citation follows the role in the source, as described in [Frontend](frontend.md#export).
- The graphic novel on page 4916 is a work of its own, an adaptation of the Schachnovelle with a change of medium, whose German edition translates the French graphic novel of 2015. The claim is resolved in `data/reconciliation/edition-modeling-decisions.json`, see [Data](data.md#statement-states).
- The archive triage is outside version 1.0, see the release scope below.

On 23 September the operator approved the recommended course after four read-only reviews. The domain decisions of that round carry the provenance "decided by the main instance after delegation by the operator on 2026-09-23, revisable".

- A page the wiki's Redirect fixer overwrote with an unrelated redirect is published from the compiler's last revision before the overwrite, and the fixer redirect resolves no reference. Where that revision is not delivered, the redirect is withheld under an open claim. See [Data](data.md#pages-overwritten-by-the-redirect-fixer).
- The 26 Maria Stuart references resolve to the restored page 35.
- The compound place claims "Sofija, Varna", "Varna, Sofija" and "Bloemfontein, Kaapstad" are decided as two places each, and their components are confirmed. Tyresö and Saint-Aignan stay open.
- Systematic false review flags are removed by rule for version 1.0. Genuine source conflicts stay open claims, and version 1.0 does not require their resolution.
- Editing per publication stays outside version 1.0.

The operator confirmed on 23 September that permission to publish the compiled content under CC BY 4.0 exists and named the Literaturarchiv Salzburg as the institution the edition is published with. The archival dump stays in the public Git history by the operator's decision of the same day, and release archives still leave it out. The operator also set the title "Stefan Zweig Bibliography", after the wiki, cited as "Stefan Zweig Bibliography (Klawiter)", and ruled that the publication is not called a digital edition. The acceptances remain with the operator and the partners.

The release declaration and the publication form after acceptance remain with the responsible people. These decisions do not prevent bounded technical repairs or source transcription checks.

## Release scope

Version 1.0 covers the current pages of the wiki. The titles that the wiki's deletion archive and log record as deleted and that are absent from the current page table are excluded from the project scope of version 1.0 (decided by the main instance after delegation by the operator on 2026-09-22, revisable). A deletion was an editorial decision of the compiler, a large part of these titles are duplicates, renamed pages or empty pages, and one of them is a private message. The raw originals under `data/raw/` stay unchanged. A later read-only triage list of these titles is possible as a separate work package and is not part of 1.0. Eight current pages are published from the compiler's last revision before an overwrite by the wiki's Redirect fixer, the only departure from the current page state (decided by the main instance after delegation by the operator on 2026-09-23, revisable).

Use the [five-case worksheet](evaluations/2026-09-05/owner-evaluation.md) to evaluate concrete edition boundaries, contribution roles, conflicting imprints and the research workflow. The questions are not a request to reapprove the work/edition principle.

## Evidence ownership

- [Data](data.md): source and entity contracts, statuses and correction limits.
- [Pipeline](pipeline.md): stage order, inputs and deterministic boundary.
- [Testing](testing.md): executable checks, independent samples and CI limits.
- [Frontend](frontend.md): user-facing behaviour and export scope.
- [Status](status.md): one prioritized current work list and current artifact links.
- Dated reviews and `knowledge/evaluations/`: observations at a particular state, preserved without silently rewriting history.
