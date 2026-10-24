---
title: Current Project Status
status: maintained
language: en
updated: 2026-10-23
---

# Current project status

**Assessment: approximately 6/10 as a completed scholarly research product.** Preservation and engineering are substantially stronger than this completion score: current page identities survive, the gate contracts pass, and the reviewed repair package closes concrete defects. Full bibliographic modelling, canonical curation propagation and product acceptance remain open. A green test suite does not certify every field.

This is the single current status/work list. [Production readiness](production-readiness.md) owns acceptance criteria; [Technical remediation](technical-remediation-2026-09-05.md) records implemented changes. Earlier reviews remain historical snapshots.

## Verified data snapshot — 23 October 2026

The snapshot follows commit 51afa41 (evening of 23 October), which fixed the corpus-wide defects of the review round and added invariants over all records, on top of commit 7994ccb, which fixed five verified pipeline defects and implemented the operator's decision that a test fixture confirms nothing ([Journal](journal.md)).

| Population | Current result | Evidence |
|---|---:|---|
| Current source pages / canonical records | 6,725 / 6,725 | [quality](../data/output/quality-report.json), [census](../data/output/census-report.json) |
| Redirects / frontend records | 1,538 / 5,187 | redirects from the [quality report](../data/output/quality-report.json); the frontend's `_meta.redirectCount` reads 1,523: the redirect map merges title aliases, but keys that are now entry titles and keys that differed only by a dump quote escape are no longer separate (no key lost its resolution) |
| Bibliography entries visible in the interface | 4,758 | namespace 0, excluding redirects |
| Work / edition / source annotation nodes | 448 / 2,077 / 2,077 | [Gate 1 manifest](../data/output/editions/manifest.json) |
| Confirmed / proposed / contested editions | 76 / 2,001 / 0 | same manifest and graph |
| Prioritized edition / reconciliation review cases | 339 / 581 | [Gate 1](../data/output/editions/manifest.json), [Gate 2](../data/output/reconciliation/manifest.json) |
| Publishable location / work / agent links | 334 / 3 / 0 | [Gate 2 manifest](../data/output/reconciliation/manifest.json); the twenty places decided only by the test fixture are proposed again |
| Open authority / source-revision / edition claims | 12 / 10 / 0 | same manifest |
| Decided authority / edition claims | 5 / 1 | same manifest |
| Pages restored from before a Redirect fixer overwrite | 8 | `data/reconciliation/source-revision-decisions.json` |
| Unresolved See-references | 2 (pages 679, 7232) | [frontend dataset](../docs/data/klawiter.json) |
| Pages / publications / contributions in the publication layer | 1,665 / 3,273 / 13,884 | `_meta.publicationCoverage` in the [frontend dataset](../docs/data/klawiter.json), records under `docs/data/publications/` |
| Publication review flags (missing place / unresolved imprint / pagination) | 159 (68 / 65 / 26) | same field, `reviewFlags` per publication |

Four current pages lack text; only page 2979 is bibliographic. Earlier revisions, absent archived titles and uploaded image bytes are outside the current extracted content scope. The titles that the wiki recorded as deleted and that are absent from the current page table are excluded from version 1.0 ([Production readiness](production-readiness.md#release-scope)). See [Data](data.md).

| Flat main-namespace field | Populated | Coverage |
|---|---:|---:|
| Year | 4,425 | 93.0% |
| Language code | 4,478 | 94.1% |
| Publisher | 2,439 | 51.3% |
| Numbered extent | 2,335 | 49.1% |
| Translator | 1,948 | 40.9% |

In the evening of 23 October the fields fell further where values came from the wrong passage: publishers that were editor credits or prose, years from titles, glosses and life spans, page counts of later editions and LLM page counts without a source token, and translator credits from the translations section of German pages. Language rose because category languages now map through the vocabulary. These are corrections, not losses: a gap is a valid result, and a value from the wrong passage is not. Population is not extraction recall or accuracy. On 23 October translator rose because credit names with Latin Extended letters are read by rule, publisher fell because prose fragments are no longer read as labels and LLM values without a source occurrence are rejected, and extent changed on 119 pages because the earliest extent in the text wins over a later edition's. These flat values still describe one publication per page; the publication layer says which publication each fact belongs to, and 237 entries with an empty flat translator document a translation credit there. No flat publisher, place or translator value carries mojibake any more.

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

## Strands since 23 October

- Wiki data. The defect classes of the review round of 23 October are fixed at their root causes, each with a real-record test and an invariant over all records, and the semantic diagnostics keep 18 failures. Every content page states its wiki page kind and the print addresses its text cites (frontend schema 1.7). Open is the operator's decision on flat fields of pages without edition headers ([Merged bibliography](print-wiki-merge.md), Wiki data true to their source passage). The editions counted as confirmed and the published place links rest on agent reconciliation under the operator's delegation, and whether that counts as `confirmed` is open ([Data](data.md)).
- Print strand. Every object and every apparatus item of the three volumes is a validated, span-bound record, exported locally as JSON-LD with one provenance chain per value. No person has reviewed yet, so field correctness is unmeasured ([Print volumes](print-volumes.md), Structured objects). The concordance with the wiki runs on two routes and is projected for the viewer with its claim states.
- Interfaces. The production frontend opens with the compiler's sections across the four sources and shows a reading pane beside the result list ([Frontend](frontend.md)). The card workbench of the [Print viewer](print-viewer.md) is the local review instrument.

The verification history of each round stands in the [Journal](journal.md), the September closeout in [Session 34](journal.md#2026-09-05--session-34-controlled-closeout).

Browser QA passed at 320, 390 and 1440 pixels, with exact filter handover/reload, keyboard selection, year validation and no horizontal overflow or page errors. Independent review checked 120 real-corpus filter combinations and rechecked the corrected date/focus edge cases. See [validation details](evaluations/2026-09-05/validation.json) and [dashboard QA](evaluations/2026-09-05/dashboard-browser-qa.json). This is targeted evidence, not complete accessibility certification or a measured mobile performance budget.

## Prioritized completion work

| Priority | Concrete next step | Completion evidence |
|---|---|---|
| P0 release | Release metadata settled: title "Stefan Zweig Bibliography", cited as "Stefan Zweig Bibliography (Klawiter)", no longer called a digital edition (operator decision of 23 September) | done; the operator decided on 23 September that `data/raw` stays in the public Git history as the documented research source, although `zweig_part_03.sql` holds the wiki's user table with password hashes and `zweig_part_01.sql` two IP addresses in its recent-changes table; the operator confirmed on 23 September that permission to publish the compiled content under CC BY 4.0 exists and named the Literaturarchiv Salzburg as the institution the bibliography is published with; `CITATION.cff`, licence texts and third-party notices are in place since 23 September |
| P0 acceptance | None outstanding. On 23 September the operator withdrew worksheet case 5, the partner acceptance and the Zenodo deposit; a Git tag remains the operator's decision | operator decision |
| P1 provenance | Apply one released field correction consistently to canonical graphs, frontend, exports, history and reports | end-to-end replay and repeatability with a real source-bound fixture |
| P1 editing | Editing per publication stays outside version 1.0 (decided by the main instance after delegation by the operator on 2026-09-23, revisable), because no released correction exists yet and the acceptance contract asks for propagation of a page-level correction | a patch contract that binds a publication id to its source-slice hash, when a correction needs it |
| P2 data | Page 1875 keeps its six volumes in one publication, because splitting sets would move the ratified segmentation of seven Gate 1 pages | source-bound fixture after a Gate 1 segmentation decision |
| P2 QA | Broaden the stratified semantic sample, complete curation/export browser checks and measure representative performance/accessibility | declared sample protocol and device/task budgets with recorded results |

The two remaining unresolved See-references name titles no current page carries and stay open. The Maria Stuart case showed that a technically resolved reference can still point to the wrong page, so a resolution rests on the source revision history, never on a guessed target.

The [five-case worksheet](evaluations/2026-09-05/owner-evaluation.md) records the responses to cases 1 to 4. Case 5, the operator's own research task on the interface, was withdrawn by the operator on 23 September and is not a release condition. The decisions of 22 and 23 September were taken under delegation and stay revisable; the release itself remains an acceptance decision.
