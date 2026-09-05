---
title: Current Project Status
status: maintained
language: en
updated: 2026-09-05
---

# Current project status

**Assessment: approximately 6/10 as a completed scholarly research product.** Preservation and engineering are substantially stronger than this completion score: current page identities survive, the gate contracts pass, and the reviewed repair package closes concrete defects. Full bibliographic modelling, canonical curation propagation and product acceptance remain open. A green test suite does not certify every field.

This is the single current status/work list. [Production readiness](production-readiness.md) owns acceptance criteria; [Technical remediation](technical-remediation-2026-09-05.md) records implemented changes. Earlier reviews remain historical snapshots.

## Verified data snapshot — 5 September 2026

| Population | Current result | Evidence |
|---|---:|---|
| Current source pages / canonical records | 6,725 / 6,725 | [quality](../data/output/quality-report.json), [census](../data/output/census-report.json) |
| Redirects / frontend records | 1,546 / 5,179 | [frontend dataset](../docs/data/klawiter.json) |
| Bibliography entries visible in the interface | 4,751 | namespace 0, excluding redirects |
| Work / edition / source annotation nodes | 443 / 1,886 / 1,886 | [Gate 1 manifest](../data/output/editions/manifest.json) |
| Confirmed / proposed / contested editions | 75 / 1,810 / 1 | same manifest and graph |
| Prioritized edition / reconciliation review cases | 317 / 897 | [Gate 1](../data/output/editions/manifest.json), [Gate 2](../data/output/reconciliation/manifest.json) |
| Publishable location / work / agent links | 26 / 3 / 0 | [Gate 2 manifest](../data/output/reconciliation/manifest.json) |
| Open authority claims / edition binding claims | 5 / 1 | same manifest |
| Technically unresolved See-references | 12 of 1,213 | [review evidence](evaluations/2026-09-05/published-change-review.json) |

Four current pages lack text; only page 2979 is bibliographic. Earlier revisions, absent archived titles and uploaded image bytes are outside the current extracted content scope. See [Data](data.md).

| Flat main-namespace field | Populated | Coverage |
|---|---:|---:|
| Year | 4,429 | 93.2% |
| Language code | 4,309 | 90.7% |
| Publisher | 2,483 | 52.3% |
| Numbered extent | 2,435 | 51.3% |
| Translator | 1,920 | 40.4% |

Population is not extraction recall or accuracy. The extent count fell because 95 citation locators were removed from the volume-extent field. Language increased through source categories, without replacing existing published labels. These flat values may still describe different publications on one page.

## Implemented and checked

- Complete source fixtures, exact semantic inventories and mutation tests prevent false green results from missing inputs, lost sample coverage or arbitrary title suffixes.
- Source-reviewed parser repairs, language code mappings and redirect-chain resolution are regenerated into the dependent artifacts.
- Nested edition-summary and contested source evidence survive RDF conversion; the vocabulary publishes the missing terms.
- Correction replay validates document shape, target IDs and actual timestamp order and refuses partial frontend persistence after batch failure.
- Missing-language and multiple-value filter handover, repeated queue listeners, mobile navigation, result headings and badge contrast are repaired.
- The CI reproduction contract now checks committed stable gate manifests and every referenced input/artifact, including previously omitted candidate/queue files.
- Project knowledge is consolidated by responsibility; stale completion claims, archive counts, patch semantics and CI claims are corrected.
- The Explore dashboard is implemented: linked entry/coverage counts, decade and language/type filters, year controls and entry preview. Map and Connections retain the shared selection; malformed date URLs and keyboard focus are covered.

**Final locked-environment verification:** 615 default tests passed, zero skips; 53 Node behaviour tests and all 15 module syntax checks passed. Semantic diagnostics retain 139 passing and 31 failing assertions (14 extraction / 17 frontend); correct expectations were not weakened. Both production gates, Ruff, pre-commit and Python compilation passed. All 117 compared deterministic data/vocabulary files reproduced byte-identically. The reviewed-manifest checker passed against the explicit local reviewed snapshot. These are local pre-closeout results; the [Tests workflow](https://github.com/chpollin/klawiter-rescue/actions/workflows/tests.yml) records remote verification for each delivered commit.

The operator authorized the controlled repository and Obsidian handoff in [Journal Session 34](journal.md#2026-09-05--session-34-controlled-closeout). The implementation, matching reviewed manifests and maintained knowledge form one delivery. This handoff leaves scholarly acceptance and the version 1.0 release decision open.

Browser QA passed at 320, 390 and 1440 pixels, with exact filter handover/reload, keyboard selection, year validation and no horizontal overflow or page errors. Independent review checked 120 real-corpus filter combinations and rechecked the corrected date/focus edge cases. See [validation details](evaluations/2026-09-05/validation.json) and [dashboard QA](evaluations/2026-09-05/dashboard-browser-qa.json). This is targeted evidence, not complete accessibility certification or a measured mobile performance budget.

## Prioritized completion work

| Priority | Concrete next step | Completion evidence |
|---|---|---|
| P0 release | Prepare a reviewed public source package and reconcile publication metadata/scope; preserve archival originals separately | explicit package inventory and provenance, reviewed distribution scope, operator release decision |
| P1 data | Model publication/contribution-scoped facts on the concrete cases 1800, 1891, 4445 and 4209, then extend to the remaining corpus | independent source assertions for roles, imprints, language and extent; no cross-publication mixing |
| P1 provenance | Apply one released field correction consistently to canonical graphs, frontend, exports, history and reports | end-to-end replay and repeatability with a real source-bound fixture |
| P1 interface | Expose edition/source navigation and precise field-review scope; finish dashboard acceptance | research task finds the intended publication, evidence and usable citation with keyboard/mobile access |
| P1 source link | Adjudicate the original “Maria Stuart” redirect, which leads 26 references to an apparently unrelated review | reviewed target or preserved explicit uncertainty; see [literal evidence](evaluations/2026-09-05/published-change-review.json) |
| P2 QA | Broaden the stratified semantic sample, complete curation/export browser checks and measure representative performance/accessibility | declared sample protocol and device/task budgets with recorded results |

The 12 unresolved links need source-specific syntax/target review; technical resolution alone is insufficient. The preserved Maria Stuart anomaly demonstrates why. Do not automatically change it to a guessed target.

The owner can use the [five-case worksheet](evaluations/2026-09-05/owner-evaluation.md). The work/edition principle is already ratified; the evaluation concerns exact scholarly meaning and usability. Archive expansion, institutional adaptation identity and a new release are explicit scope/acceptance decisions, not inferred from this implementation session.
