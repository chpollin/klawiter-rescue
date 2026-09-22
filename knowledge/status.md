---
title: Current Project Status
status: maintained
language: en
updated: 2026-09-22
---

# Current project status

**Assessment: approximately 6/10 as a completed scholarly research product.** Preservation and engineering are substantially stronger than this completion score: current page identities survive, the gate contracts pass, and the reviewed repair package closes concrete defects. Full bibliographic modelling, canonical curation propagation and product acceptance remain open. A green test suite does not certify every field.

This is the single current status/work list. [Production readiness](production-readiness.md) owns acceptance criteria; [Technical remediation](technical-remediation-2026-09-05.md) records implemented changes. Earlier reviews remain historical snapshots.

## Verified data snapshot — 5 September 2026, graph rows updated 22 September

| Population | Current result | Evidence |
|---|---:|---|
| Current source pages / canonical records | 6,725 / 6,725 | [quality](../data/output/quality-report.json), [census](../data/output/census-report.json) |
| Redirects / frontend records | 1,546 / 5,179 | [frontend dataset](../docs/data/klawiter.json) |
| Bibliography entries visible in the interface | 4,751 | namespace 0, excluding redirects |
| Work / edition / source annotation nodes | 444 / 1,886 / 1,886 | [Gate 1 manifest](../data/output/editions/manifest.json) |
| Confirmed / proposed / contested editions | 76 / 1,810 / 0 | same manifest and graph |
| Prioritized edition / reconciliation review cases | 316 / 897 | [Gate 1](../data/output/editions/manifest.json), [Gate 2](../data/output/reconciliation/manifest.json) |
| Publishable location / work / agent links | 26 / 3 / 0 | [Gate 2 manifest](../data/output/reconciliation/manifest.json) |
| Open authority claims / edition binding claims | 5 / 0, the one binding claim decided on 22 September | same manifest |
| Technically unresolved See-references | 12 of 1,213 | [review evidence](evaluations/2026-09-05/published-change-review.json) |
| Pages / publications / contributions in the publication layer | 1,659 / 3,102 / 14,312 | `_meta.publicationCoverage` in the [frontend dataset](../docs/data/klawiter.json), records under `docs/data/publications/` |
| Publication review flags held open as claims | 735 | same field, `reviewFlags` per publication |

Four current pages lack text; only page 2979 is bibliographic. Earlier revisions, absent archived titles and uploaded image bytes are outside the current extracted content scope. The titles that the wiki recorded as deleted and that are absent from the current page table are excluded from version 1.0 ([Production readiness](production-readiness.md#release-scope)). See [Data](data.md).

| Flat main-namespace field | Populated | Coverage |
|---|---:|---:|
| Year | 4,429 | 93.2% |
| Language code | 4,309 | 90.7% |
| Publisher | 2,634 | 55.4% |
| Numbered extent | 2,435 | 51.3% |
| Translator | 1,919 | 40.4% |

Population is not extraction recall or accuracy. The extent count fell because 95 citation locators were removed from the volume-extent field. Publisher rose because the flat field now follows the publication imprint of the source header. Translator lost one value whose encoding could not be restored. These flat values still describe one publication per page; the publication layer says which publication each fact belongs to, and 237 entries with an empty flat translator document a translation credit there. No flat publisher, place or translator value carries mojibake any more.

## Implemented and checked

- Complete source fixtures, exact semantic inventories and mutation tests prevent false green results from missing inputs, lost sample coverage or arbitrary title suffixes.
- Source-reviewed parser repairs, language code mappings and redirect-chain resolution are regenerated into the dependent artifacts.
- Nested edition-summary and contested source evidence survive RDF conversion; the vocabulary publishes the missing terms.
- Correction replay validates document shape, target IDs and actual timestamp order and refuses partial frontend persistence after batch failure.
- Missing-language and multiple-value filter handover, repeated queue listeners, mobile navigation, result headings and badge contrast are repaired.
- The CI reproduction contract now checks committed stable gate manifests and every referenced input/artifact, including previously omitted candidate/queue files.
- Project knowledge is consolidated by responsibility; stale completion claims, archive counts, patch semantics and CI claims are corrected.
- Publication- and contribution-scoped facts reach the frontend record for every page whose source carries a publication header, with roles, imprint, language, extent notation, contributions and per-field provenance bound to their own source slice. The four owner cases are covered by source-bound fixtures. The records live in per-page files under `docs/data/publications/`, so the main dataset stays at 2.1 megabytes gzipped.
- The flat publisher follows the publication imprint, a contribution credit is refused as a publisher, and enrichment values that arrived as a misreading of UTF-8 bytes are repaired or dropped, each repair carrying a field-scoped review hint.
- The Explore dashboard is implemented: linked entry/coverage counts, decade and language/type filters, year controls and entry preview. Map and Connections retain the shared selection; malformed date URLs and keyboard focus are covered.

**Final locked-environment verification (8 September):** 708 default tests passed, zero skips; the Node behaviour suites and all module syntax checks passed. Semantic diagnostics now retain 147 passing and 23 failing assertions; the bounded default gate holds 16 reviewed deviations. Correct expectations were not weakened; the one reviewed change records that page 6342 reports the imprint spelling of the delivered source rather than that of the live wiki page. Both production gates, Ruff, pre-commit and Python compilation passed. All 117 compared deterministic data/vocabulary files reproduced byte-identically. The reviewed-manifest checker passed against the explicit local reviewed snapshot. These are local pre-closeout results; the [Tests workflow](https://github.com/chpollin/klawiter-rescue/actions/workflows/tests.yml) records remote verification for each delivered commit.

The operator authorized the controlled repository and Obsidian handoff in [Journal Session 34](journal.md#2026-09-05--session-34-controlled-closeout). The implementation, matching reviewed manifests and maintained knowledge form one delivery. This handoff leaves scholarly acceptance and the version 1.0 release decision open.

The first remote run on `d345ee6` passed the test job and Pages deployment but detected a Gate 2 input hash mismatch. The local `locations.json` still had CRLF line endings, whereas its committed blob used LF. Closeout aligned the local bytes with the existing Git blob and regenerated Gate 2 evidence. Parsed location data and deterministic product artifacts remain unchanged. The linked workflow records verification of the follow-up commit.

On 22 September the four worksheet cases on pages 1800, 1891, 4445 and 4209 are accepted as displayed, the citation author follows the role in the source, the graphic novel on page 4916 is a work of its own and the archive triage is excluded from version 1.0, each decided by the main instance after delegation by the operator on 2026-09-22, revisable. After the change the default suite, the semantic diagnostics with an unchanged set of retained failures, the Node behaviour suites, Ruff and a full production run with both gates passed. The committed-evidence check reports the intended manifest drift until the regenerated manifests are committed with the code. See [Journal](journal.md).

Browser QA passed at 320, 390 and 1440 pixels, with exact filter handover/reload, keyboard selection, year validation and no horizontal overflow or page errors. Independent review checked 120 real-corpus filter combinations and rechecked the corrected date/focus edge cases. See [validation details](evaluations/2026-09-05/validation.json) and [dashboard QA](evaluations/2026-09-05/dashboard-browser-qa.json). This is targeted evidence, not complete accessibility certification or a measured mobile performance budget.

## Prioritized completion work

| Priority | Concrete next step | Completion evidence |
|---|---|---|
| P0 release | Prepare a reviewed public source package and reconcile publication metadata/scope; preserve archival originals separately | explicit package inventory and provenance, reviewed distribution scope, operator release decision; editorship (Digital Humanities Craft with Christopher Pollin) and release form (operator acceptance yields 0.9.1, partner acceptance yields 1.0 with Git tag plus Zenodo DOI) decided 2026-09-08, see [journal](journal.md); titles recorded as deleted in the wiki excluded from 1.0 (decided by the main instance after delegation by the operator on 2026-09-22, revisable), see [release scope](production-readiness.md#release-scope) |
| P1 data | Done for the four cases 1800, 1891, 4445 and 4209, whose display the worksheet accepts since 22 September, and extended to every page with a publication header; the two flat-layer defects are repaired, and the rules leave 231 imprint splits, 385 pagination discrepancies and 119 missing places as open claims | source-bound fixtures and the contract in [Data](data.md); flag codes and counts in the [frontend dataset](../docs/data/klawiter.json), see [journal](journal.md) |
| P1 citation | Give each publication of a page its own citable address, since both editions on page 1800 are cited with the same page URL; carry the translators of contributions into the citation export, since page 1891 exports none of its three contribution translators and the flat translator field names only the first | a permalink per publication that a citation carries; a contribution-scoped translator in BibTeX/RIS with a source-bound fixture |
| P1 provenance | Apply one released field correction consistently to canonical graphs, frontend, exports, history and reports | end-to-end replay and repeatability with a real source-bound fixture |
| P1 interface | Card, list, facets and Explore flattened and put on the publication layer on 2026-09-08, after an operator review on a phone and an independent before/after review; edit mode names its page-record scope, while editing per publication awaits a patch-contract extension | operator's own run of the worksheet task on the new interface (case 5, open); decision on the patch-contract extension; see [journal](journal.md) |
| P1 source link | Adjudicate the original “Maria Stuart” redirect, which leads 26 references to an apparently unrelated review | reviewed target or preserved explicit uncertainty; see [literal evidence](evaluations/2026-09-05/published-change-review.json) |
| P2 QA | Broaden the stratified semantic sample, complete curation/export browser checks and measure representative performance/accessibility | declared sample protocol and device/task budgets with recorded results |

The 12 unresolved links need source-specific syntax/target review; technical resolution alone is insufficient. The preserved Maria Stuart anomaly demonstrates why. Do not automatically change it to a guessed target.

The [five-case worksheet](evaluations/2026-09-05/owner-evaluation.md) records the responses to cases 1 to 4. Case 5, the operator's own research task on the interface, remains open. The adaptation identity and the archive scope were decided on 22 September under delegation and stay revisable; the release itself remains an acceptance decision.
