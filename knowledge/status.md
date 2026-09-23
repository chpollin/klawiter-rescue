---
title: Current Project Status
status: maintained
language: en
updated: 2026-09-23
---

# Current project status

**Assessment: approximately 6/10 as a completed scholarly research product.** Preservation and engineering are substantially stronger than this completion score: current page identities survive, the gate contracts pass, and the reviewed repair package closes concrete defects. Full bibliographic modelling, canonical curation propagation and product acceptance remain open. A green test suite does not certify every field.

This is the single current status/work list. [Production readiness](production-readiness.md) owns acceptance criteria; [Technical remediation](technical-remediation-2026-09-05.md) records implemented changes. Earlier reviews remain historical snapshots.

## Verified data snapshot — 23 September 2026

| Population | Current result | Evidence |
|---|---:|---|
| Current source pages / canonical records | 6,725 / 6,725 | [quality](../data/output/quality-report.json), [census](../data/output/census-report.json) |
| Redirects / frontend records | 1,538 / 5,187 | [frontend dataset](../docs/data/klawiter.json) |
| Bibliography entries visible in the interface | 4,758 | namespace 0, excluding redirects |
| Work / edition / source annotation nodes | 448 / 2,077 / 2,077 | [Gate 1 manifest](../data/output/editions/manifest.json) |
| Confirmed / proposed / contested editions | 76 / 2,001 / 0 | same manifest and graph |
| Prioritized edition / reconciliation review cases | 339 / 895 | [Gate 1](../data/output/editions/manifest.json), [Gate 2](../data/output/reconciliation/manifest.json) |
| Publishable location / work / agent links | 29 / 3 / 0 | [Gate 2 manifest](../data/output/reconciliation/manifest.json) |
| Open authority / source-revision / edition claims | 2 / 10 / 0 | same manifest |
| Decided authority / edition claims | 3 / 1 | same manifest |
| Pages restored from before a Redirect fixer overwrite | 8 | `data/reconciliation/source-revision-decisions.json` |
| Unresolved See-references | 2 (pages 679, 7232) | [frontend dataset](../docs/data/klawiter.json) |
| Pages / publications / contributions in the publication layer | 1,665 / 3,273 / 13,904 | `_meta.publicationCoverage` in the [frontend dataset](../docs/data/klawiter.json), records under `docs/data/publications/` |
| Publication review flags (missing place / unresolved imprint / pagination) | 173 (82 / 65 / 26) | same field, `reviewFlags` per publication |

Four current pages lack text; only page 2979 is bibliographic. Earlier revisions, absent archived titles and uploaded image bytes are outside the current extracted content scope. The titles that the wiki recorded as deleted and that are absent from the current page table are excluded from version 1.0 ([Production readiness](production-readiness.md#release-scope)). See [Data](data.md).

| Flat main-namespace field | Populated | Coverage |
|---|---:|---:|
| Year | 4,435 | 93.2% |
| Language code | 4,314 | 90.7% |
| Publisher | 2,640 | 55.5% |
| Numbered extent | 2,440 | 51.3% |
| Translator | 1,921 | 40.4% |

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

On 23 September four read-only reviews (the Maria Stuart redirect, the separation of statement states, the public release package, and a machine run of worksheet case 5) led to one repair round, with the operator's approval of the recommended course, each domain decision recorded as decided by the main instance after delegation by the operator on 2026-09-23, revisable. Pages overwritten by the wiki's Redirect fixer are published from the compiler's last revision, the 26 Maria Stuart references lead to page 35, the compound place claims are decided as two places each, the publication-layer rules no longer raise flags for qualified places, co-imprints or the unnumbered pages of an extent, and the interface states the scope of each review, the state of each edition and every open or decided claim where it applies. Citations carry a permalink per publication, contribution translators, notes and correct RIS roles. After the round the default suite, the semantic diagnostics with the same 23 retained failures, the Node behaviour suites, Ruff, a full production run with both gates and the committed-evidence check passed. See [Journal](journal.md).

Browser QA passed at 320, 390 and 1440 pixels, with exact filter handover/reload, keyboard selection, year validation and no horizontal overflow or page errors. Independent review checked 120 real-corpus filter combinations and rechecked the corrected date/focus edge cases. See [validation details](evaluations/2026-09-05/validation.json) and [dashboard QA](evaluations/2026-09-05/dashboard-browser-qa.json). This is targeted evidence, not complete accessibility certification or a measured mobile performance budget.

## Prioritized completion work

| Priority | Concrete next step | Completion evidence |
|---|---|---|
| P0 release | Release metadata settled: title "Stefan Zweig Bibliography", cited as "Stefan Zweig Bibliography (Klawiter)", no longer called a digital edition (operator decision of 23 September) | done; the operator decided on 23 September that `data/raw` stays in the public Git history as the documented research source, although `zweig_part_03.sql` holds the wiki's user table with password hashes and `zweig_part_01.sql` two IP addresses in its recent-changes table; the operator confirmed on 23 September that permission to publish the compiled content under CC BY 4.0 exists and named the Literaturarchiv Salzburg as the institution the edition is published with; `.gitattributes` already keeps `data/raw` out of release archives, `CITATION.cff`, `.zenodo.json`, licence texts and third-party notices are in place since 23 September |
| P0 acceptance | The partner acceptance through the [partner worksheet](evaluations/2026-09-23/partner-evaluation.md) yields 1.0 with Git tag and Zenodo DOI; worksheet case 5 was withdrawn by the operator on 23 September | partner responses; release authorization |
| P1 provenance | Apply one released field correction consistently to canonical graphs, frontend, exports, history and reports | end-to-end replay and repeatability with a real source-bound fixture |
| P1 editing | Editing per publication stays outside version 1.0 (decided by the main instance after delegation by the operator on 2026-09-23, revisable), because no released correction exists yet and the acceptance contract asks for propagation of a page-level correction | a patch contract that binds a publication id to its source-slice hash, when a correction needs it |
| P0 Zenodo | Enable the GitHub repository in the Zenodo account, then publish a GitHub release; `.zenodo.json` files the record in the `dhcraft` community | operator action in Zenodo and on GitHub |
| P2 data | Page 1875 still merges six volumes into one publication, page 2083 reads page lines of its French edition as contents, and 145 main-namespace titles are taken from a cross-reference, translation or imprint line instead of the page title (class of pages 5839, 212, 586) | source-bound fixtures after a Gate 1 segmentation decision |
| P2 QA | Broaden the stratified semantic sample, complete curation/export browser checks and measure representative performance/accessibility | declared sample protocol and device/task budgets with recorded results |

The two remaining unresolved See-references name titles no current page carries and stay open. The Maria Stuart case showed that a technically resolved reference can still point to the wrong page, so a resolution rests on the source revision history, never on a guessed target.

The [five-case worksheet](evaluations/2026-09-05/owner-evaluation.md) records the responses to cases 1 to 4. Case 5, the operator's own research task on the interface, was withdrawn by the operator on 23 September and is not a release condition. The decisions of 22 and 23 September were taken under delegation and stay revisable; the release itself remains an acceptance decision.
