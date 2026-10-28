---
title: Current Project Status
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: maintained
language: en
created: 2026-09-05
updated: 2026-10-24
---

# Current project status

**Assessment: approximately 6/10 as a completed scholarly research product.** Preservation and engineering are substantially stronger than this completion score: current page identities survive, the gate contracts pass, and the reviewed repair package closes concrete defects. Full bibliographic modelling, canonical curation propagation and product acceptance remain open. A green test suite does not certify every field.

This is the current status snapshot; future work lives in [Plan](plan.md) and received findings in [Handoff](handoff.md). [Governance](governance.md) owns acceptance criteria; [Technical remediation](../snapshots/technical-remediation-2026-09-05.md) records implemented changes. Earlier reviews remain historical snapshots.

## Verified data snapshot — 24 October 2026

The snapshot follows commit 64cbaea of 24 October. Since 71a0fe0 every decision of an LLM agent is a proposal, so no link is published and no edition or claim is confirmed until a person or an exact rule decides, flat values no rule binds are gaps by rule, and 181 pages carry translation statements. 64cbaea dates every page by its first and last human revision, keeps a gap by rule apart from a source gap, resolves redirects in the main namespace and reports 74 broken ones in `data/output/unresolved-redirects.json`, and moves Gate 1 to algorithm 1.5, which takes page 3757 out of the multi-edition corpus. Earlier rounds stand in the [Journal](journal.md).

| Population | Current result | Evidence |
|---|---:|---|
| Current source pages / canonical records | 6,725 / 6,725 | [quality](../data/output/quality-report.json), [census](../data/output/census-report.json) |
| Redirects / frontend records | 1,538 / 5,187 | redirects from the [quality report](../data/output/quality-report.json); the frontend's `_meta.redirectCount` reads 1,517: the map merges title aliases, resolves in the main namespace only and leaves out the redirects whose target no current page carries, which the [unresolved-redirects report](../data/output/unresolved-redirects.json) lists with their kind |
| Bibliography entries visible in the interface | 4,758 | namespace 0, excluding redirects |
| Work / edition / source annotation nodes | 446 / 2,054 / 2,054 (and 1 candidate work) | [Gate 1 manifest](../data/output/editions/manifest.json) |
| Confirmed / proposed / contested editions | 0 / 2,053 / 1 | same manifest and graph |
| Prioritized edition / reconciliation review cases | 332 / 929 | [Gate 1](../data/output/editions/manifest.json), [Gate 2](../data/output/reconciliation/manifest.json) |
| Publishable location / work / agent links | 0 / 0 / 0 | [Gate 2 manifest](../data/output/reconciliation/manifest.json); the twenty places decided only by the test fixture are proposed again |
| Open authority / source-revision / edition claims | 17 / 10 / 1 | same manifest |
| Decided authority / edition claims | 0 / 0 | same manifest |
| Pages restored from before a Redirect fixer overwrite | 8 | `data/reconciliation/source-revision-decisions.json` |
| Unresolved See-references | 2 (pages 679, 7232) | [frontend dataset](../docs/data/klawiter.json) |
| Pages / publications / contributions in the publication layer | 1,665 / 3,273 / 13,884 | `_meta.publicationCoverage` in the [frontend dataset](../docs/data/klawiter.json), records under `docs/data/publications/` |
| Publication review flags (missing place / unresolved imprint / pagination) | 159 (68 / 65 / 26) | same field, `reviewFlags` per publication |

Four current pages lack text; only page 2979 is bibliographic. Earlier revisions, absent archived titles and uploaded image bytes are outside the current extracted content scope. The titles that the wiki recorded as deleted and that are absent from the current page table are excluded from version 1.0 ([Governance](governance.md#release-scope)). See [Data](data.md).

| Flat main-namespace field | Populated | Coverage |
|---|---:|---:|
| Year | 4,425 | 93.0% |
| Language code | 4,478 | 94.1% |
| Place | 3,749 | 78.8% |
| Publisher | 2,066 | 43.4% |
| Numbered extent | 2,335 | 49.1% |
| Translator | 1,743 | 36.6% |

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

- Wiki data. The defect classes of the review round of 23 October are fixed at their root causes, each with a real-record test and an invariant over all records. Every content page states its wiki page kind and the print addresses its text cites. Under the operator principles of 24 October, flat fields that no rule binds to the described publication become gaps and decisions of LLM agents are proposals; the batch that implements both is committed (71a0fe0), and what remains of the milestone stands in [Plan](plan.md). Open received findings wait in [Handoff](handoff.md).
- Print strand. Every object and every apparatus item of the three volumes is a validated, span-bound record, exported locally as JSON-LD with one provenance chain per value, under a local gate. The measurement design is corrected and its samples are frozen while the review log is empty. No person has reviewed yet, so field correctness is unmeasured ([Print pipeline](print-pipeline.md), Structured objects). The concordance runs on two routes and is projected for the viewer with its claim states.
- Interfaces. The reader has Overview, Records and Documentation (increment 1, 53b9397). Records is the first cut of the record desk: one card component for wiki and print records with a visible provenance chain per value, print records only through the review server (cb13e6c); its browser review and remaining gaps are open in [Plan](plan.md). The local page check tool shows a PDF page beside every line and value read from it. The research coordinator builds the interface ([Governance](governance.md#parallel-sessions)).
- Acceptance. What the operator accepts and decides is listed in [Governance](governance.md), What the operator accepts.

The verification history of each round stands in the [Journal](journal.md), the September closeout in its entry of 2026-09-05.

Browser QA passed at 320, 390 and 1440 pixels, with exact filter handover/reload, keyboard selection, year validation and no horizontal overflow or page errors. Independent review checked 120 real-corpus filter combinations and rechecked the corrected date/focus edge cases. See [validation details](../snapshots/evaluations/2026-09-05/validation.json) and [dashboard QA](../snapshots/evaluations/2026-09-05/dashboard-browser-qa.json). This is targeted evidence, not complete accessibility certification or a measured mobile performance budget.

## Work ahead

The work still to be done, in its order and with its exit conditions, lives in [Plan](plan.md).

The two remaining unresolved See-references name titles no current page carries and stay open. The Maria Stuart case showed that a technically resolved reference can still point to the wrong page, so a resolution rests on the source revision history, never on a guessed target.

The [five-case worksheet](../snapshots/evaluations/2026-09-05/owner-evaluation.md) records the responses to cases 1 to 4. Case 5, the operator's own research task on the interface, was withdrawn by the operator on 23 September and is not a release condition. The decisions of 22 and 23 September were taken under delegation and stay revisable; the release itself remains an acceptance decision.
