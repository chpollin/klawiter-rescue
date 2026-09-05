---
title: Project completion review — 2026-09-05
status: complete
language: en
created: 2026-09-05
related: [review-0.9, production-readiness, testing, data, frontend]
---


> Historical review snapshot. The implemented follow-up is recorded in [Technical remediation](technical-remediation-2026-09-05.md); [Status](status.md) owns the current findings and next steps. Original observations below retain their review date.
# Project completion review

Reviewed commit: `1902abc` on `main`. The working tree was clean before the review. This is an assessment and acceptance plan; no production code, correction decisions or raw sources were changed. Intermediate stages were regenerated for verification. Findings were checked against code and artifacts, with targeted executable probes and a local browser inspection. The earlier [0.9 review](review-0.9.md) is useful background, but is not treated as proof by itself.

## Verdict

The project has a strong preservation and engineering foundation. Its complete current-page census, frozen enrichment inputs, explicit uncertainty, source selectors, test coverage and static deployment are worth retaining. It is a substantial release candidate. It is **not yet a fully extracted, fully modelled and validated scholarly bibliography**, and the frontend has demonstrable functional and accessibility defects.

The most important completion work is to connect source evidence, bibliographic entities, review scope and the user-facing record consistently. A broad redesign or another framework is not needed to address the verified defects.

| Question | Assessment | What the evidence establishes |
|---|---|---|
| Have all data been extracted? | Yes for the inventory of current pages; no for all historical content or all bibliographic statements. | 6,725 source page IDs survive exactly once. Extraction selects `page_latest`. Historical revisions and archived pages remain separate scope. |
| Have all data been modelled cleanly? | No. | The work/edition layer improves 443 pages, but misses other compound structures and important edition fields. Some RDF mappings and provenance remain incomplete. |
| Are all data in the frontend? | The intended current bibliography pages are present; the complete semantic model is not. | 4,751 main-namespace records are displayed. Editions, selectors and carrier structures are not independently browsable; even the work pointer is omitted from the frontend entry projection. |
| Is the frontend optimized and perfect? | No. It has a coherent visual design and useful functionality, with reproducible defects and unmeasured performance limits. | Filter handover fails, mobile navigation disappears, queue listeners accumulate, and badge contrast is insufficient. |
| What remains for completion? | Close the prioritized defects, ratify publication scope and prove acceptance against independent source and user tasks. | The acceptance matrix below makes completion finite and testable. |

## 1. What is complete, and what is not

The current artifacts give the following exact record accounting:

- 6,725 source pages, including 6,296 in namespace 0.
- 6,725 flat JSON-LD entries, including 1,546 redirects.
- 5,179 frontend records: the exact ID set of the JSON-LD non-redirects.
- 4,751 displayed namespace-0 entries; the other 428 frontend records are structural namespaces, deliberately outside the catalogue.
- 6,721 current pages have recovered text. Four have no matching text body; only one is bibliographic: page 2979, *A unidade espiritual do mundo*. Keeping its named stub is correct.

These are strong preservation results. They establish page identity, not that every paragraph was assigned to the correct bibliographic entity or that every extracted year is a publication year.

The raw dump contains 51,946 revision rows; 45,221 are beyond the 6,725 current-page selections. The archive contains 2,594 revision rows over 433 distinct namespace/title pairs. With the repository's title normalization, 207 main-namespace archived titles are absent from the current page table. Those 207 are the useful bibliographic triage population, not the total archive-row count. Archive recovery is already a deferred operator decision; it must either be included deliberately or excluded explicitly from the release claim. Uploaded image bytes are not among the delivered raw files, although the dump contains an image metadata record.

Sources: [extraction](../pipeline/01_extract.py), [census](../data/output/census-report.json), [scope](data.md). The current run of stages 01–04 independently reproduced the page census and the committed hashes of both `02_encoding_fixed.csv` and `04_classified.csv`.

### Field coverage is not extraction recall

For the 4,751 displayed bibliography entries:

| Field | Populated | Coverage |
|---|---:|---:|
| Title / title fallback | 4,751 | 100.0% |
| Publication year | 4,429 | 93.2% |
| Publication place | 4,265 | 89.8% |
| Language | 4,254 | 89.5% |
| Publisher | 2,483 | 52.3% |
| Extent / page count | 2,530 | 53.3% |
| Translator | 1,920 | 40.4% |
| Bibliographic citation | 4,719 | 99.3% |

An absent translator on a German original can be correct. A populated translator taken from a different edition is incorrect. Therefore neither 100% population nor the current percentages should be a release target by themselves. Use explicit states such as `not stated in source`, `not applicable`, `not yet extracted`, `ambiguous` and `confirmed`, with field-specific evidence.

The [verification report](../data/output/verification-report.json) flags 194 publisher, 44 location, 50 translator and one page-count occurrence mismatches: 289 field signals, not 289 proven factual errors or necessarily distinct entries. It also reports 186 publisher and two translator detection signals where no field was extracted. Several detector examples are noisy. These queues need adjudication, not automatic acceptance as missing facts.

The source comparison also accepts a plausible string from the wrong paragraph. The current semantic sample demonstrates this directly: page **1166** uses **1815** from the Waterloo subtitle as its publication year, although the citation says **Beijing, 1983**. Page **1308** turns **p. 23** into an extent of **23 pages**. Both currently receive an entry-level `agent_verified` status through their location decision.

## 2. Prioritized findings

Priority P0 blocks distributing an unreviewed release package. P1 blocks claiming the corresponding data or product capability is complete. P2 is important hardening or a deliberately bounded follow-up.

### P0 — Separate preserved raw data from public release data

The tracked `data/raw/zweig_part_03.sql` contains populated historical account records, including password hashes and authentication-token fields. These values are unnecessary for the bibliography. Their continued validity was not tested, and no values are reproduced in this review.

**Action:** retain the archival original unchanged under appropriate access, prepare a separate public bibliographic source package, inspect existing distribution/history, and have the owner assess any still-relevant credentials. Do not silently edit the archival original or rewrite Git history as part of a documentation review.

**Acceptance:** the public package has an explicit file/table allowlist, a sensitive-data scan, and a reproducible relationship to the preserved source. Its hashes identify the public release input; preservation hashes identify the original separately. Record responsibility for prior-distribution remediation.

### P1 — Publication facts and the selection of bibliographic units

The flat record can combine publication year, place, publisher and translator from different blocks. The 17 semantic failures are visible, but the default tests allow them up to a frozen ceiling. Page 1166's false year also reaches the homepage range and the timeline: the homepage calls the holdings “publications” dating from 1815, and the entry is classified as Pre-Zweig.

The edition graph covers the 443 pages matching a particular bold-year-header grammar. Pages **285**, **1667**, **1166** and **1308** are outside that graph. Page 285 contains an original publication, reprints and translations; page 1667 contains different correspondence and publication blocks. Thus implementing the existing edition graph in the frontend alone will not resolve all known mixing errors.

**Action:** distinguish source page, work, publication/edition, contribution within a carrier, and dated correspondence or historical subject matter. Inventory unsupported source structures. Fix known false assertions, or expose them as unresolved instead of as single publication facts. Preserve page numbers, ranges and extent separately.

**Acceptance:** each asserted publication field belongs to a source-bound publication block; each unsupported structure has an explicit status and queue entry. The 17 current discrepancies are individually fixed or adjudicated under a documented data contract. Merely raising a baseline or marking the tests expected failures is not acceptance.

Evidence: [semantic tests](../tests/test_semantic.py), [ground truth](../tests/wiki_ground_truth.json), [edition selection](../pipeline/lib/editions.py), [frontend data](../docs/data/klawiter.json).

### P1 — Complete the edition model and make it usable

There are 443 works, 1,886 editions and 1,886 annotations. Only 75 editions are confirmed, 1,810 are proposed and one is contested; 317 edition cases are prioritized for review. The confirmed sample is about 4% of editions and is concentrated in three pages, so it cannot estimate corpus-wide correctness.

Across **all 1,886 edition nodes**, there is **no structured `schema:translator` or `schema:inLanguage`**. Edition titles and contents are also not systematically represented as edition-level fields. This is a modelling gap, not evidence that the source lacks the information: page 409 names different translators inside different publication blocks.

The interface reads the flat entry file. `make_frontend_entry()` explicitly skips `decomposedAsWork`; no frontend record carries that pointer. Canonical graph downloads are linked on the Data page, and contested edition claims are visible, but users cannot browse each modelled edition with its own fields, selector and status. Citation exports likewise use the flat record's scalar fields.

**Action:** add an edition section on each covered source page, with stable links, publication fields, evidence and scoped status. Extract edition-level language, translator and title where evidenced. Offer edition-specific citation/export. For ambiguous unsplit pages, avoid presenting or exporting a synthetic publication as established.

**Acceptance:** all 443 graph-backed pages expose their work and edition links; all 1,886 editions are reachable with the correct status and source span. Search, filters and exports identify whether they operate on pages, works or publications. Every model field has a documented disposition: rendered, searchable, downloadable, derived, or deliberately excluded.

Evidence: [edition manifest](../data/output/editions/manifest.json), [canonical graph](../data/output/editions/work-editions.jsonld), [projection](../pipeline/05_to_jsonld.py), [detail rendering](../docs/js/detail.js), [exports](../docs/js/export.js).

### P1 — Scope review claims and preserve canonical correction history

2,434 frontend entries have `review.status = agent_verified`. This is predominantly the effect of shared location-name decisions, not full verification of 2,434 entries. The visible status chip does not make that distinction. Pages 1166 and 1308 are concrete counterexamples to interpreting the chip as a record-quality guarantee.

Field provenance is present in the frontend but absent from all 6,725 flat canonical entries. `apply_patches.py` writes corrected fields and edit history only to the frontend JSON. The corrections store is currently empty, so this is a verified pipeline design gap rather than an observed disagreement between an existing human correction and the graph. Once used, this route can leave the citable dataset with the old value and the interface with the new one; quality/triage reports are also built before the overlay.

The patch validator accepts a string page ID and a non-timestamp `edited_at`. A probe with page ID `"3"` was accepted, applied zero changes to integer ID 3, and returned `not_found`. The production entry point logs these failures but returns 0. Mixed-offset timestamps are sorted as strings.

**Action:** use field- and occurrence-scoped review labels with decision IDs; project provenance into canonical RDF; establish one authoritative correction path and rebuild dependent projections and reports from it. Require valid ID types and parsed timestamps, and fail the run when an authoritative patch cannot be applied.

**Acceptance:** one correction fixture produces the same value, review identity and history in the canonical dataset, UI and exports. Invalid or unknown-target patches fail. An untouched field cannot inherit a “verified” meaning from another field's authority match.

Evidence: [review projection](../pipeline/05_to_jsonld.py), [patches](../pipeline/apply_patches.py), [provenance injection](../pipeline/inject_provenance.py), [runner ordering](../pipeline/run_pipeline.py).

### P1 — Repair redirect identity and reference resolution

Stage 04 decorates redirect targets with ` (→ page_id)` in the data field. All 1,546 published redirect targets contain this decoration, and 655 alias-map keys contain it. Stage 05 subsequently tries to resolve the decorated string as a plain title.

Of the 120 currently unresolved frontend references, a read-only probe that removes the decoration and rebuilds the resolver resolves **108**. The remaining 12 were not adjudicated as genuine red links in this review. Therefore the documentation's assertion that all 120 are genuine source red links is false.

**Action:** keep target titles and resolved IDs in separate fields; test aliases, redirect chains and unresolved targets against the source link table. Rebuild artifacts and lower the verified regression bound.

**Acceptance:** every recoverable reference resolves to the correct record, no alias contains presentation decoration, and residual failures have an explicit source-based reason.

Evidence: [classification](../pipeline/04_classify.py), [reference resolver](../pipeline/05_to_jsonld.py), [source-table tests](../tests/test_source_tables.py).

### P1 — Close RDF loss and semantic-range gaps

The edition graph expands to **47,569 RDF triples**, so this is not the former empty-graph failure. Nevertheless the five unqualified child keys of each `pageSummaries` object have no context mapping. Its counts and source-text IDs disappear in RDF conversion. The contested-authority graph likewise loses unqualified source evidence fields such as `sourceText`, `sourceTextId` and `sourceMatchMode`. A triple-count floor cannot detect this selective loss. See the [JSON-LD specification](https://www.w3.org/TR/json-ld11/).

A recursive check of explicit `klawiter:` property keys in the three data artifacts found five missing from the published Turtle term register: `bindingStatus`, `headerSeries`, `reviewContract`, `reviewDecision`, `reviewEvidenceSha256`.

The flat graph also uses raw citation strings for `hasPart` and `workTranslation`, whose declared ranges describe creative works. Preserve raw citation text in explicitly textual properties and emit semantic relations when their targets are represented. See [Schema.org hasPart](https://schema.org/hasPart) and [workTranslation](https://schema.org/workTranslation). Author attribution also reaches 428 structural, non-bibliographic entries; restrict or document this inference.

**Acceptance:** recursively verify that every intended semantic field survives JSON-LD-to-RDF conversion, every used project term is registered, and property objects match the declared model. Check populated target classes and field-level assertions as well as SHACL conformance and triple totals.

### P1 — Fix frontend behavior before polishing

| Defect | Reproduction / evidence | Required acceptance check |
|---|---|---|
| Explore → results loses missing-language selection | In the browser, select “Not recorded 497”, then “View all 497 entries”: results show 0. `_resultParams()` also keeps only the first language and first type in multi-select. | Exact ID equality between the selected chart population and the opened result list, for missing values and every supported filter combination. |
| Queue listeners accumulate | Three calls of `_renderAgentQueue()` register three listeners on the persistent host; one synthetic key event invokes the handler three times. | One key event causes one handler invocation after repeated render/decision/undo cycles. This review does not claim that one keypress necessarily decides three different subjects. |
| Main navigation disappears on mobile | At a 390 × 844 viewport, `.site-nav` is hidden by the max-width-640 rule, with no replacement menu. Explore has no link in the footer. | All primary destinations remain discoverable and keyboard accessible at narrow widths. |
| Local mobile header overflows | At the same viewport, client width is 375 px with the scrollbar; document width is 390 px. The local Edit button extends beyond the content viewport. | No horizontal page overflow at agreed widths, in reading and local curation mode. This observation is specifically from localhost. |
| Badge text contrast is insufficient | Browser-computed `#6B6B6B` on `#EDE8DF`, 11 px; calculated contrast 4.37:1. | Verify normal-size text contrast and all focus/hover states after correction. |
| Results view lacks a primary heading | Browser DOM shows a status label and subsequent h3 detail sections, with no visible result-view h1. | One meaningful h1 for the active view and a coherent heading hierarchy. |

Evidence: [Explore handover](../docs/js/explore.js), [queue](../docs/js/curate.js), [responsive CSS](../docs/css/styles.css), [application](../docs/js/app.js).

The layout is visually coherent and source details, citations, facets and uncertainty are useful capabilities. Keep these strengths. Optional-data rendering errors and malformed-claim guards from the earlier review remain useful hardening items, but were not exhaustively fault-injected in this session.

### P1/P2 — Finish the reproducibility and publication contract

The repository already has a valuable full-rebuild CI job. However its byte-comparison allowlist omits timestamped manifests and reports. Regenerated candidate/queue hashes are checked against the manifest generated in the same run, not against the committed manifest with volatile fields normalized. Thus the advertised frozen candidate/review-stock comparison is incomplete. Stages 01–04 also provide no explicit per-raw-file SHA-256 root manifest.

Only five of seven Node test files are bridged into pytest/CI. `edit_session.test.js` and `search_logic.test.js` pass when run directly but are not included in that bridge. Syntax-check every frontend module and discover the Node test set rather than enumerating it manually.

Publication metadata is inconsistent: `pyproject.toml` says 1.0.0 while the declared acceptance state is 0.9; `CITATION.cff` describes a dataset under MIT while the README/site declare CC BY 4.0 for data; `LICENSE` only contains MIT text. The CFF has an empty ORCID and an old release date. README's 796 reconciliation cases are stale: the current manifest has **897**, including 101 agent subjects. There are 26 publishable location links, three work links and zero agent links. Release metadata and publisher responsibility need one consistent decision and validation.

**Acceptance:** compare all intended deterministic artifacts, including normalized manifest content and expected inventory; fail on unintended missing/new artifacts; verify source-package hashes; run every Node file and syntax check in CI; validate citation metadata; issue a versioned release with a fixed artifact list, source scope, license scopes, changelog and responsible maintainer. DOI registration is an additional publication step if selected, not a prerequisite for testing the software.

Evidence: [CI](../.github/workflows/tests.yml), [Node bridge](../tests/test_frontend_logic.py), [citation metadata](../CITATION.cff), [reconciliation manifest](../data/output/reconciliation/manifest.json).

## 3. Verification and validation for acceptance

Verification asks whether the implementation preserves and transforms what its contract specifies. Validation asks whether those contracts and results are bibliographically correct and useful to researchers. A passing SHACL report or a reproducible mistake answers only part of the first question.

| Gate | Work and owner role | Measurable acceptance evidence |
|---|---|---|
| A — Scope and release safety | Owner + preservation responsibility | A signed scope statement distinguishes current pages, historical revisions, archived titles, images and print/wiki merging. Every source file/table has a preservation and publication disposition. Public package contains no account/authentication payload. |
| B — Correct data assertions | Data engineer + bibliography reviewer | Known semantic cases adjudicated; date/extent/block errors fixed or explicitly unresolved. A complete structural census includes source patterns outside the current 443-page selection. Each retained ambiguity has a stable case ID. |
| C — Model and correction integrity | Data engineer | Field-level evidence, RDF round-trip assertions, vocabulary coverage, exact selectors/hashes, bidirectional link projection, patch replay and determinism checks pass. Curated values agree across canonical data, UI, citations and quality reports. |
| D — Frontend feature coverage | Frontend engineer + researcher/editor | All published model units have a documented UI/export disposition. Browser tests cover lookup, diacritics, combined facets, missing values, chart handover, back/reload, edition selection, citation export, local edit/undo/export, contested cases and failed loads. |
| E — Independent factual validation | Bibliographic/language expertise | Source-based stratified sample with a frozen selection seed, independent annotations and adjudication. Report field precision, recall among source-present facts, edition-boundary and work-binding accuracy, with uncertainty and error examples. |
| F — Product and release acceptance | Owner + representative users | Agreed research tasks complete without help; mobile/keyboard and accessibility checks pass; cold/warm performance measured under fixed conditions; clean installation and complete frozen rebuild succeed; release documentation matches artifact hashes and counts. |

### Sampling that can support a factual claim

Keep the ten-entry semantic fixture as a regression set, but do not treat it as a representative quality estimate. Add a held-out sample stratified by entry type, source structure, language/script, extraction route (rules/LLM/editor), and ambiguity. Oversample difficult cases for diagnosis, and use design weights if reporting an overall estimate. Separate random evaluation from deliberately selected regression cases.

A practical starting proposal is 200–400 sampled source pages, with all their publication blocks reviewed; size should follow the desired error bound and the amount of clustering within pages. Have two reviewers independently annotate a meaningful subset, record disagreements and adjudicate against the source. Frozen model outputs are not independent ground truth. A comparison against an external catalogue can add evidence, but catalogue disagreement must itself be examined rather than silently overwritten.

Suggested release targets to ratify, not measured achievements: at least 98% precision for title/publication year and 95% for other asserted core fields, with a separately reported recall target for facts actually present in the source. Publish confidence intervals and stratum results. If the evidence does not support a target, reduce the claim or mark the relevant records as proposals. Do not label the entire corpus verified on the basis of a sample.

### Performance and accessibility

The entry file is 10,189,702 bytes (9.72 MiB); local gzip measurement is 2,113,496 bytes (2.02 MiB). Reconciliation adds 1,391,513 bytes uncompressed on demand. These are file measurements, not observed production transfer sizes or load times. The current lazy loading and index preparation are useful; they do not establish mobile performance.

Measure cold load, first usable search, subsequent query/filter latency and chart interaction under a named mobile CPU/network profile, then repeat with a warm cache. Set a search/filter response budget (for example p95 below 200 ms on the agreed reference setup) and a first-usable-search budget before deciding whether to split the corpus, move indexing to a worker or make source text lazy. Those architectural changes should follow evidence, not replace the correctness fixes.

Test widths 320, 390, 768 and desktop, keyboard-only navigation, zoom/reflow, focus visibility and screen-reader reading order. Add automated accessibility checks, then manually verify menus, facets, chart alternatives and the editor. A screenshot and an automated score alone cannot establish accessibility conformance.

## 4. Work order and a finite definition of done

1. **Make the release scope explicit and resolve raw-data distribution.** This is a publication responsibility with a small technical manifest/packaging task.
2. **Fix correctness and integrity defects.** Redirects, publication-year/extent mistakes, patch failures, review labels, RDF term loss and canonical correction propagation come first.
3. **Complete the agreed bibliographic model and its frontend projection.** Add usable edition records and cover or explicitly queue the compound structures that the current selector misses. Preserve source-conditioned gaps.
4. **Repair interaction and accessibility, then measure performance.** Add regression tests that exercise the failing journeys; retain the existing design where it works.
5. **Run independent validation and a clean release rehearsal.** Produce one acceptance bundle containing the commit, environment/lockfile, input/output hashes, all gate/test results, semantic sample results, browser/task checks, known limitations and owner acceptance.

Completion does **not** require every source to contain every field, every authority candidate to be confirmed, or every scholarly disagreement to be resolved. It requires every claimed capability to be demonstrated, every relevant source structure to have a disposition, and all remaining uncertainty to be represented accurately. The 897 reconciliation cases, 317 edition cases and the open adaptation binding may remain documented proposals/claims in a clearly labelled technical release. They cannot support a claim of complete scholarly curation. Deferred archive triage and print/wiki merging require explicit scope decisions, not an open-ended promise to do everything.

## 5. Verification performed in this review

| Check | Result and limit |
|---|---|
| Initial repository state | Clean `main`, commit `1902abc`; no production fixes applied. |
| Extraction through classification | `python pipeline/run_pipeline.py --to-stage 04 --no-postprocess` passed in 52.1 s with frozen enrichment. Stage 01 census: 6,725 IDs, zero failures. |
| Intermediate reproducibility | SHA-256 for stages 02 and 04 equals the committed gate manifests: `ccad2060…` and `1d9a9d59…`. |
| Default pytest after regeneration | **497 passed, 10 skipped, 74 deselected**. Six skips concern page-range fixtures and four concern truncated language fixtures. |
| Semantic pytest | **17 failed, 53 passed, 511 deselected**; exactly the known aggregate bound. These are real test failures, not a passing semantic gate. |
| All Node test files | **43 passed, zero failures**, using `node --test tests/*.test.js`. |
| JavaScript syntax | Every `docs/js/*.js` passed `node --check`. |
| Targeted probes | Exact frontend ID equality; redirect decoration and resolver repair; permissive patch validation; accumulating queue handlers; RDF conversion loss; missing term definitions; edition field coverage; source archive accounting. |
| Browser | Local Chromium-based in-app browser, default 1280 × 720 and 390 × 844 override. Inspected home, Explore, missing-language handover and entry 1166; confirmed the review chip and publication-year display. Narrow-view navigation/overflow and badge computed styles checked. No errors/warnings were captured in the inspected detail journey. |
| Full pinned rebuild / fresh SHACL validation | **Not completed.** Local Python has no `uv`, `ruff` or `pyshacl`. Installing pinned uv failed on a download timeout; an explicit-index attempt also failed. Gate 1 invocation fails on missing `pyshacl`. The committed gate reports remain historical evidence, not a fresh pass from this session. |
| Ruff / pre-commit | Not verified in the pinned environment; local Ruff is absent. |

The successful Python checks used the available Python 3.11.9 environment, not the pinned uv environment. Node was v22.14.0. No live LLM calls, authority write-backs, editorial decisions or publication actions were performed. This review does not claim a production-network performance benchmark, a complete cross-browser test, a screen-reader audit, a bibliographic census of every statement, or a statistically valid corpus error rate.

### Clarifications to the earlier review

- The suspicious `Ä`/`â` substitutions are in `strip_encoding_artifacts()`, a loose comparison helper. A direct probe leaves `Änderung` and `château` unchanged under `fix_encoding()`, but changes them in that comparison helper. Its equivalence logic needs repair; this probe does not establish corruption of legitimate source text by stage 02.
- The queue probe proves repeated handler execution. It does not independently establish the earlier claim that multiple different subjects are decided by one keypress.
- Directly measured structural author attribution is 428 non-main-namespace records. The simple redirect repair probe recovers 108 of 120 unresolved reference occurrences. The current explicit-property vocabulary gap includes `headerSeries`, for five missing terms in total.
- “207 archived pages” is best stated as 207 absent current main-namespace titles under the tested normalization, not 207 archive rows or all historical objects.

These distinctions matter because the review should hold its own claims to the same evidential standard it asks of the bibliography.
