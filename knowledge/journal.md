---
title: Journal
aliases: [work diary, sessions]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: historical
language: en
version: 0.5
tags: [journal]
created: 2026-03-29
updated: 2026-09-05
---

# Journal

Work journal of the Klawiter Bibliography. Every substantial session documents round, changes, decisions, open points and the next dependable re-entry.

---

## 2026-09-05 — Session 34: Controlled closeout

The operator requested an orderly end to the session, current project Markdown, an Obsidian ACTIVE-WORK update, and commit and push of the reviewed work. The matching implementation, generated gate evidence and maintained guides form the repository handoff. Earlier session and evaluation records retain their original pre-commit observations.

The final implementation is covered by Session 33's locked validation, with 615 default tests passing without skips, 53 Node tests passing and 31 retained semantic failures. Documentation-only closeout does not change those executable results. The closure checks cover Markdown links and evaluation hashes, the staged diff, and the gate manifests against the committed HEAD. Git history and the [Tests workflow](https://github.com/chpollin/klawiter-rescue/actions/workflows/tests.yml) provide the delivery and remote validation record.

The initial project commit `d345ee6` and the focused Vault commit `c122af3` were pushed and verified against their remote branches. All 27 project Markdown files, including the dependency provenance notice, have valid local targets across 208 checked links. All 21 inventoried evaluation files retain their recorded hashes, and the Vault's hard validation passed.

The first remote test job and Pages deployment passed. The new reproduction gate correctly rejected `inputs.locations.sha256`, exposing CRLF bytes in the local `docs/data/locations.json` against the already committed LF blob. The files are equal after line-ending normalization and parse to identical JSON. Closeout restored the existing committed input bytes locally and rebuilt Gate 2 evidence, preserving strict byte validation and all deterministic product data. A focused follow-up commit carries this correction; the historical pre-closeout snapshots remain unchanged.

Obsidian carries the current scholarly work state, project navigation and a completed-work note. Repository evidence remains authoritative for technical details. Unrelated concurrent Vault edits are outside this commit's scope. Commit/push authorization covers this handoff; scholarly acceptance, citation and release decisions remain open under [Production readiness](production-readiness.md).

Resume with the [five-case owner worksheet](evaluations/2026-09-05/owner-evaluation.md) and the prioritized [current work list](status.md). The next implementation should complete one publication-to-source-to-canonical-correction-to-citation path and validate it with a real source-bound fixture.

---

## 2026-09-05 — Session 33: Source repairs, dashboard and maintained knowledge

**Round.** The operator authorized autonomous implementation after the review, then requested a linked information-visualization dashboard and consolidation of project Markdown/knowledge. Independent agents reviewed source changes, dashboard invariants and documentation/CI contracts.
**Changed.** The source-preserving parser repairs improve Unicode/name boundaries, remove explicit page locators from extent and add category language gaps with registered subtags. Literal redirect chains replace decorated targets. RDF contexts/vocabulary retain nested summary and contested source evidence. Correction replay validates envelopes, positive IDs and timestamp ordering and fails before partial frontend persistence. Semantic oracle hash/inventory and exact title variants close demonstrated false-pass paths; six resolved rule cases were retired with source review. The CI verifier now compares stable reviewed gate manifests from HEAD and every referenced input/artifact, including ignored candidates/queues, with 22 mutation tests.
**Interface.** Explore now opens a coordinated dashboard at the compatible `#stats/timeline` route: entry/coverage cards, neutral decade histogram, linked language/type rankings, year inputs, filter chips and matching-entry preview. Map and Connections remain available. Multiple-value/missing-language handover, null-year boundaries, malformed restored dates, repeated queue listeners, mobile navigation, headings, contrast and keyboard focus were corrected. The old timeline implementation and obsolete styling were reduced. Counts explicitly describe source-page entries.
**Knowledge.** README and maintained guides have distinct responsibilities; [Status](status.md) owns current evidence and next steps, and [Documentation](documentation.md) owns Markdown maintenance. Historical reviews/journal/data-side reports are preserved with current-guide pointers; proposal templates no longer imply implemented evaluation features. Directory guides are English and reflect actual runner/patch behaviour. [Technical remediation](technical-remediation-2026-09-05.md) and the expanded evaluation manifest preserve reviewed changes, screenshots, source evidence and validation.
**Verified.** Locked uv installation succeeded. Final strict pytest: 615 passed, zero skips, 174 deselected; semantic: 139 passed and 31 retained failures. All 53 Node behaviour tests and 15 JS syntax checks pass. Ruff/pre-commit, compileall and diff checks pass. Full frozen production run: 176.4s, Gate 1/2 passed, 117 compared deterministic artifacts byte-identical against the reviewed prior build. The manifest verifier passes against the explicit local reviewed snapshot; no remote CI job was triggered. Browser QA at 320/390/1440px has no horizontal overflow or page errors; exact handover/reload, ranges and keyboard paths pass. Independent review verified 120 real-corpus filter combinations and rechecked the date/focus fixes.
**Decided.** Technical resolution is not scholarly correctness: the unchanged Maria Stuart redirect sends 26 references to an apparently unrelated review, now documented for adjudication. Name corrections on 1891 and 285 preserve the source occurrence but do not resolve publication scope; their expectations stay red. A failed prototype truncation of Anna. S. Kulisher was caught and quarantined generically. No raw source or released domain decision changed. The completion assessment remains approximately 6/10 because bibliographic modelling, canonical correction/provenance propagation and scholarly product acceptance remain open.
**Open.** Follow the finite work list in Status: public release/source scope, scoped publication/contribution facts, canonical curation, edition/evidence navigation and precise field-review meaning, source redirect adjudication, broader semantic and usability/accessibility/performance validation. Commit the already reviewed manifests with matching implementation/input/artifact changes when preparing the reviewable release change; no commit, push or deployment was made here.

**The one next step.** Use the five-case owner worksheet to settle concrete source scopes while implementing one complete publication → evidence → canonical correction → citation path, with end-to-end acceptance assertions.

---

## 2026-09-05 — Session 32: Blind source reviews and owner evaluation

**Round.** The operator asked what to evaluate personally and whether subagents should verify the project. Two separate agents reviewed all twenty complete source texts without the current expectations, baselines or each other's findings; a third reviewed the tests and downstream values.
**Changed.** [[independent-evaluation-2026-09-05]] consolidates the findings. Full source-only input, both source reviews, test review, downstream comparison and five owner acceptance cases are preserved under `knowledge/evaluations/2026-09-05/`, with a hash manifest. The current fixture review and testing guide now qualify the earlier twenty-defect description. No production code, test expectations, decision inputs or generated product artifacts changed in this round.
**Verified.** Both source reviews cover all twenty IDs and five fields; their evidence snippets were checked verbatim against the shared input. The test reviewer reproduced 157 focused passing tests without skips and 133 passing / 37 failing semantic assertions without skips. Collection confirmed 521 default-selected tests; the full strict suite was not repeated after documentation-only changes. Five of the twenty rule mismatches already exactly match expected values in the shipped frontend through frozen enrichment. Pinned uv/Ruff and full pinned reproduction remain unverified locally.
**Decided.** Thirty-seven failing assertions do not establish thirty-seven product data errors. Some mismatches reflect competing scalar-selection policies across valid publications. The ratified work/edition decomposition remains in force; the owner should evaluate concrete boundaries, roles and research usability, not reapprove that principle. Agent agreement supports source interpretation but does not replace scholarly adjudication.
**Open.** Enforce the frontend semantic fixture's recorded hash and exact inventory; prevent arbitrary title suffixes from passing; retire resolved baseline cases; express ambiguous expectations at publication/contribution scope; obtain feedback on the five acceptance cases; correct confirmed source-role and Unicode defects with downstream verification.

**The one next step.** Close the two demonstrated false-pass paths in the semantic test guard while the owner evaluates the concrete bibliographic and interface cases.

---

## 2026-09-05 — Session 31: Complete source fixtures and explicit extraction failures

**Round.** The operator authorized the next test-improvement step: restore source context, activate skipped checks and assert null fields.
**Changed.** All twenty fixture texts were restored from complete normalized sources and checked directly against their BLOB/text IDs and stage-01 rows. The fixture now carries text hashes, source-line selectors, one hundred reviewed expectations and notes explaining citation scope and missing values. Parser-derived `existing` values and `needed` hints were removed. The ten range/truncation skips disappeared; page 162 was corrected to its explicit 254-page numbered extent, while the p. 425 locator on page 1999 is diagnosed as an incorrect count. The restored fixtures expose twenty existing rule defects (eleven missing values and nine incorrect ones); their source expectations and observed failures are separate. The default tests protect every field against new or changed failures using `.github/extraction-baseline.json`, and one hundred exact semantic assertions retain the defects as red diagnostics. The baseline is tied to the reviewed fixture hash and replacement-failure tests cover it. Stage-02 source rows are shared with edition tests. The optional LLM judge now selects stable page IDs and receives full texts; its historic live-judgment inventory still needs recalibration. [[test-fixture-review-2026-09-05]] records the concrete cases.
**Verified.** The strict default suite passed 521 tests with no skips, 174 deselections and one existing RDFLib deprecation warning in 20.73 s. Consolidating three repeated structural extractions into one per entry reduced the test count while the field assertions and source evidence expanded. The diagnostic semantic suite ran 170 assertions: 133 passed and 37 failed, comprising twenty newly exposed rule failures and the seventeen previous frontend failures. JUnit reports are in `test-results/`. Python compilation and whitespace checks passed. No production code or data artifacts changed, and no live LLM request was made. A further pinned Ruff download attempt timed out; uv/Ruff and a pinned CI run remain unverified locally.
**Decided.** The new case inventory describes failures already present in unchanged production code; it must not become a way to accept a future deterioration. Known observed values never serve as correct expected values. The test fixture scope is documented per record: it does not resolve the project's multi-edition modeling problem or estimate corpus-wide accuracy.
**Open.** Correct publisher context/boundaries, Unicode translator names, page locators versus extent, and missing language coverage. Rebuild downstream artifacts and validate the gates for each correction package. The remaining frontend/model review and browser acceptance work are still open.

**The one next step.** Implement the source-reviewed parser corrections, beginning with publisher context and truncated translator names, with a corpus-wide change report before updating generated artifacts.

---

## 2026-09-05 — Session 30: Completion review and test refactoring

**Round.** Review of extraction, model, frontend and acceptance evidence, followed by the operator's request to optimize and refactor the tests.
**Changed.** [[project-review-2026-09-05]] records the verified product gaps and acceptance criteria. Tests now discover all seven JavaScript behavior files and check all fifteen shipped JS modules. Required committed inputs fail when missing or malformed; `--require-test-inputs` and CI also require Node and regenerated stage CSVs, with isolated pytest runs proving those failure paths. Shared JSON/CSV fixtures and an ID index remove repeated reads. Edition tests share one build with per-test deep copies. Reconciliation retains its full integration build, checks occurrence completeness for all 101 agent subjects, and exercises unresolved person/publisher decisions using complete source evidence for each selected subject. Census compares the exact frontend/canonical non-redirect ID multisets. The semantic guard now permits only the existing page/field/value deviations recorded in `.github/semantic-baseline.json`, with replacement-regression checks. CI writes separate default and diagnostic semantic JUnit reports; only the diagnostic step is non-blocking.
**Verified.** On local Python 3.11.9 / Node 22.14.0, the final strict default run passed 527 tests, skipped the ten documented legacy fixture cases and deselected 74 semantic/LLM cases in 20.66 s. The pre-change default run took 35.17 s with 497 passing tests on the same machine; these are observed runs, not a controlled benchmark. The separate semantic run remained 53 passing and exactly 17 failing field assertions, matching the frozen cases. Python compilation, workflow YAML parsing and `git diff --check` passed. The final default JUnit report is in the ignored `test-results/` directory. One RDFLib deprecation warning remains. The pinned uv environment and Ruff were unavailable locally; installation/download attempts failed, so pinned lint/format checks and the full CI reproduction job remain unverified in this session.
**Decided.** Product completion remains approximately 6/10; a stronger green test gate does not resolve the data-model and interface defects. Preserve the known semantic failures as visible diagnostics and prohibit replacing them with new errors under an unchanged count. Repair legacy expectations only against independently reviewed source context, never by copying current extractor output. Raw inputs and generated product artifacts were not changed by the refactor.
**Open.** Repair the six range-label and four truncated-language fixture cases, strengthen null/LLM-only assertions, correct the 17 semantic failures, add browser acceptance coverage for filters/mobile navigation/queue lifecycle/export/curation, and run pinned checks in CI. The larger model/provenance/frontend completion work remains in the review.

**The one next step.** Restore complete source context and independently verified expectations for the twenty-entry extraction sample, then remove its ten skips and assert negative results explicitly.

---

## 2026-08-27 — Session 29: External review of the 0.9 release candidate

**Round.** Review round, four parallel agents over pipeline, frontend, data model and tests/CI plus a CSS deep audit; read-only, nothing changed in code or data.
**Changed.** [[review-0.9]] created as the consolidated, verified finding list and registered in the index; no other file touched.
**Decided.** The findings split into a pre-acceptance package (real defects, publication metadata, trust chain, frontend robustness and accessibility) and a 1.1 stock (load-path split assessed as not worth it, pipeline consolidation, data-model honesty, broader reproducibility proof, CSS and documentation sweep); the weightiest pre-acceptance items are the redirect decoration in stage 04, the missing RDF provenance and the manifest comparison the reproduce job claims but does not perform. The test suite ran green locally during the review (497 passed, semantic failures exactly matching the baseline).
**Open.** Implementation of the pre-acceptance package awaits the operator's go; the publisher decision in finding 8 is an existing operator point.

---

## 2026-08-27 — Session 28: Frontend audit, redesign and versioning

**Round.** A four-agent audit of the whole frontend (texts and figures, core-view UX, explore views, code/performance/accessibility, together about 160 findings) followed by operator-steered implementation rounds, plus a versioning decision.
**Changed.** Information architecture rebuilt: navigation Overview, Explore, Data and About; About absorbs Methodology, Help and Imprint as anchored sections; a new Data page joins model explanation, specification, downloads and the JSON-LD playground; Data Quality is a Data sub-page (`#data/quality`, `#quality` redirects); legacy hashes redirect; the research-network bar and the home subcategories are gone. Explore rebuilt around a persistent sidebar with the mode switch on top and one filter system across all three visualizations; coverage texts moved off the drawing surface; the earlier repair round fixed zoom scales, selection hand-overs, the Sankey and map interaction defects, unified "Not recorded", and added keyboard paths, reduced motion and honest counts. Core views: search folds diacritics (latin:advanced), highlighting marks raw text, user actions create real history entries, the mobile facet drawer moves instead of cloning and traps focus, load failures render a retry state, D3 loads lazily, reconciliation loads on first need. Curation tool: edited fields render the pending value, the session chip says Edited, the candidate queue is a roving listbox with undo and expandable secondary candidates, failed optional data reads as not available. Design simplified per operator direction: text pages on white cards, one heading style, two button styles, colour reserved for meaning, monochrome type badges, three workbench tiles, two-column footer with GitHub mark, Promptotyping method link and Digital Humanities Craft credit with vendored logo. The vocabulary properties `contestedClaim` and `reviewAction` were renamed to `hasContestedClaim` and `hasReviewAction`, dissolving the case collision that served the wrong term pages; `docs/vocab/` joined the CI reproduction check, and its index page is generated from the term register. The repository documentation, including the full journal, is English. Stage 05 projects review decisions into the frontend data and the occurrence scan unlocked unresolved agent decisions (Session 27).
**Decided.** The current state is version 0.9, a technically complete release candidate; version 1.0 comes into being through operator acceptance and carries the release tag. Cross-view brushing stays deferred; the load-path split, the EIL session panel and the agentic pre-curation of the agent review stock were offered and not commissioned.
**Open.** Operator points: acceptance of 0.9 as 1.0, the work identity of the adaptation, the archive triage, the responsible publisher in the citation recommendation, the publication form after acceptance. Registered technical points: load-path split of the 10 MB entry file, EIL session panel, the initial-load weight of `reconciliation.json`, two titles with a stray Arabic diacritic.

**The one next step.** Operator review of the redesigned frontend and acceptance of 0.9 as version 1.0.

## 2026-08-27 — Session 27: Registered development points worked through

**Round.** Working through the open points registered after 1.0 on operator release, executed by two parallel agents (frontend, pipeline) with subsequent wiring.
**Changed.** Cosmetics round: language and direction attributes on titles (`dir="auto"` plus script subtag such as `ar-Latn`, because the holdings are transliterated throughout and blunt RTL would turn two titles the wrong way); sorting survives reload and back as a hash parameter, the default stays parameterless, triage sorting stays bound to the editing mode; home and facets moved fully to event delegation (fixes the apostrophe breakage class of the inline handlers). review field projection: stage 05 projects Gate 2 decisions and editor patches as a compact `review` field per entry (`frontendSchemaVersion` 1.1), the review status chip now shows Unreviewed, Agent-verified, Contested and Expert-reviewed, session state wins over data holdings. Occurrence scan: the location occurrence scan is generalized to translator and publisher names, all agent subjects carry source occurrences (`sourceOccurrences`, schema 1.1), the Gate 2 check `agentOccurrenceEvidence` requires evidence per candidate; `unresolved` is thereby unlocked for agents (card, queue button, key u) and produces a source-bound ContestedClaim as with locations.
**Decided.** Cross-view brushing deliberately deferred (complexity of a shared selection state without discernible benefit); `dir="auto"` instead of forced RTL after data review.
**Open.** `docs/data/reconciliation.json` grows to a good threefold through the line texts; should the initial load path suffer, the line texts are the candidate for shortening. Two titles with a stray Arabic diacritic as a normalization candidate. Remaining points and Operator Points in [[production-readiness]].

**The one next step.** Operator review of the frontend and acceptance of version 1.0.

## 2026-08-26/27 — Session 26: Remediation programme towards version 1.0

**Round.** Implementation of the completion programme approved by the operator after five independent reviews (modelling, data completeness, test situation, architecture, frontend). Eight phases from baseline securing to final verification, eleven milestone commits, each green on both CI jobs.
**Changed.** Baseline secured and the gravest finding fixed: six missing container terms let the edition graph expand to six RDF triples, SHACL was checking an empty graph; after the fix the same file expands to over 47,000 triples and passes for real, permanently secured by triple lower bounds in stage 06. New CI job `reproduce` proves the byte-identical reproduction of the deterministic artifact set from the committed raw sources on every push; `.gitattributes` plus LF-normalized code hashes make the provenance platform-independent. Safety net: refreezing tools (`reconcile_locations.py`, newly `reconcile_agents.py`) contact the network only with `--i-am-refreezing`. Three data improvements with oracles from the dump itself: categories exactly against `zweig_categorylinks` (sort keys, double spaces, first-letter capitalization), cross-reference repair via `zweig_pagelinks` and page-title aliases in the redirect map (broken references are now genuine red links), hard stage 01 census as pipeline step `01v`. Full modelling round: edition graph declared the canonical data publication, flat layer declared a derived projection; resource nodes for publisher, translator and location; one Zweig entity with a canonical Wikidata IRI; language tags; unified contested claim model across both gates; vocabulary v3 with 90 dereferenceable term pages; SHACL over the flat layer as well; frozen Wikidata candidates for translator and publisher names as a new fail-closed review stock. Frontend remediated and extended by the curation view: data quality workbench `#quality` (completeness matrix, work stocks, candidate queue with keyboard and subject reach), Connections as a ranking of the most referenced entries instead of the bubble graph, compact entry cards without duplicates, routing guard, editing-mode gate in the setter, escaped playground highlighting, vendored map geometry (no external host any more), uniformly English vocabulary. Residual hardening: paths centralized in `lib/config.py`, header grammar with a single origin (`[ca. YEAR]` parses the same everywhere, two entries more precise), line folding once instead of per subject, pre-commit in CI and README. Evidence freeze on measured values including corrected resolution semantics of the cross-reference bound and a new publisher mojibake bound. A fresh-clone probe found the single gap in the reproducibility claim: the hand-labelled sample `test_sample_20.json` lay only untracked locally; now versioned under `tests/`.
**Decided.** Edition graph primary (machine-readable via the dataset coupling); all four user roles of equal rank, genuine conflicts of aim go to the operator; agent candidates without `unresolved` until an occurrence scan supplies source evidence; 1.0 is a technical state, external expert review follows thereafter; publication and citation form only after complete operator acceptance.
**Open.** The registered points in [[production-readiness]] (archive triage, frontend cosmetics round, review field projection, occurrence scan, agent review stock, external expert review) and the Operator Points (work identity of the adaptation, acceptance of 1.0, publication form).

**The one next step.** Operator review of the frontend and acceptance of version 1.0.

## 2026-08-21 — Session 25: Publication lines integrated into canonical project knowledge

**Round.** Knowledge consolidation following the decision to close the undertaking externally tracked as "Paper 2 Klawiter" and the Klawiter blog post as independent publication lines.
**Changed.** The domain substance is distributed across its durable contexts. `about.md` records contribution, publication status and DIA-XAI role; `pipeline.md` makes the method precise and corrects the outdated outsourcing of work/edition segmentation and reconciliation into separate projects; `frontend.md` names the boundary between public resource and local, auditable curation; `testing.md` separates artifact checking and qualitative DIA-XAI analysis; `data.md` distinguishes the already captured correction episodes from the still open aggregated protocol read-out; `production-readiness.md` binds the findings to the resource and the DIA-XAI tool. Index, README and repository instruction point to the canonical publication status. Two remaining references to the consolidated files `edition-model.md` and `eil-editing.md` now point to `production-readiness.md` and `frontend.md`. The search in the current working tree and in the git history found no explicit repository references to "Paper 2" or the blog post that would additionally have had to be removed.
**Decided.** A separate Klawiter paper and Klawiter blog post no longer produce publication or writing tasks. Method, two-loop architecture, gold standard, correction protocol, work/edition model and provenance layers are preserved as project knowledge and as a contribution to the project-wide DIA-XAI synthesis. The digital bibliography, the dataset, the software and the vocabulary remain citable publication artifacts.
**Open.** The domain product tasks stay unchanged. They include the editor's review of the segmentation drafts, the full run after that review, reconciliation at the edition level and the still open EIL increments. From the closed publication lines no open point remains.

**The one next step.** Review of `data/output/edition-samples/REVIEW.md` by the editor; on release, full run of the segmentation across all pages identified as multi-edition.

## 2026-07-30 — Session 24: Maintenance round, drift reconciliation knowledge against artifacts, antrag-eval hooks

**Round.** Maintenance and verification round without subagents, triggered from the proposal workspace, because the repository is opened by reviewers as preliminary work.
**Changed.** Test run verified (403 green, 10 skips, 74 deselected; `-m semantic` still 17 red by design, congruent with the documented bound). Drift between knowledge and the committed artifacts cleaned up: redirect resolution 1,210 to 1,224, broken seeAlso references 727 to 619, German-plus-translator 111 to 110, field coverage table and regex-only column brought to the state of the delivered run, provenance distribution recomputed from `klawiter.json`, language distribution adopted from the quality report, `klawiter.jsonld` as 6,725 instead of 6,296 entries, CSV column counts (27/29), regression threshold of critical fields 1pp instead of 0.5pp, test file table extended by `test_inject_provenance.py` and counts brought up to date, pytest invocations adjusted to the actual `addopts`. Two statements refuted as outdated and corrected: the location fix and mojibake repair are contained in the delivered dataset (no record still carries the pre-fix value, entry 804 is repaired), and the blanked stub 2979 already carries its title. The frontend document said CDN for FlexSearch, D3 and Google Fonts, whereas everything is in fact vendored under `docs/vendor/` and `docs/fonts/`. README extended by a section Provenance and Curation (production provenance per field, verification provenance with `editor` label and review block, patch v2 correction history as an audit trail). Dead document pointers in the code redirected to the consolidated documents (`eil-editing.md`, `validation.md` in four scripts and `edit.js`). Three issue templates created under `.github/ISSUE_TEMPLATE/` for the planned evaluation hooks (four-tuple protocol export, provenance export, gold standard hook), label `antrag-eval` created in the remote.
**Decided.** Volatile figures stay in the knowledge documents where they carry a finding, yet are kept against the committed artifacts; the regex-only column is marked as a stage value of the same run, because `data/intermediate/` is gitignored and cannot be recomputed by reviewers.
**Open.** Bracket title residual count (33 against ~15 in the same document) not resolvable without a new run; `corrections-report.json` is present in an older version without the `old_value_mismatch` key and is not git-tracked; the evaluation hooks are described as templates, not built.

**The one next step.** Unchanged, the review of `data/output/edition-samples/REVIEW.md` by the editor.

## 2026-07-18 — Session 23: Review fixes, knowledge consolidation, gate decisions, sample gate (Research Mission Control lane)

**Round.** Implementation and decision round with the operator, orchestrated with subagents.
**Changed.** Pipeline review fixes landed (provenance diff against regex output instead of cache presence, atomic JSON writes, visible SQL skips, mojibake guard, plus unit tests); baseline brought up to the June data state; `klawiter:` vocabulary published machine-readably (Turtle + JSON-LD); knowledge folder consolidated from 16 to 8 documents (ontology into data, ADRs into pipeline/frontend, exploration and EIL specification into frontend, edition model into production-readiness, error classes into testing; HANDOFF, references, validation dissolved); CLAUDE.md and README freed of volatile quantities; Gate 1 sample gate executed (`pipeline/segment_editions.py`, 76 edition drafts, block delimitation 76/76 adversarially verified, `data/output/edition-samples/REVIEW.md`).
**Decided.** All four operator gates (see [[production-readiness#Operator Decisions (2026-07-18)]]): Gate 1 decompose, Gate 2 reconciliation fully into production readiness, Gate 3 print merge a later development stage, Gate 4 patch export canonical with write-back as a later convenience layer. Journal in compact format from now on.
**Open.** Editor review of the segmentation drafts together with in-depth decisions before the full run; PROV layer for `klawiter.jsonld`; llmprov neighbourhood check; three header cleaning cases from the verification.

**The one next step.** Review of `data/output/edition-samples/REVIEW.md` by the editor; on release, full run of the segmentation across all pages identified as multi-edition.

## 2026-07-18 — Session 22: Modelling round work/edition

**Round.** Purely conceptual modelling round with the operator, no implementation, no pipeline run.
**Changed.** Work/edition model of the multi-edition pages incorporated as a knowledge document, [[production-readiness#Gate 1: Work/Edition Model]] work package 1 reformulated to target model plus segmentation plus verification, gate section extended by decision basis and gate order, [[data#Work/Edition Model]] extended by a reference section.
**Decided.** Multi-edition is a level error, not an extraction error; the wiki page describes a work, the `'''[year]:'''` blocks describe editions, first-match-wins makes publisher/location/year systematically unreliable and manual correction does not heal that (bracket titles are the same symptom). Target model work/edition with schema.org (`workExample`/`exampleOfWork`), FRBR/LRM and BIBFRAME conceptually, no ontology change; evidence per edition as W3C Web Annotation, provenance as a PROV-O sidecar with `_provenance` as a derived frontend short form, validation layer as SHACL plus EARL/DQV, publishable PROV profile `llmprov`; a stable source-derivable ID schema `klawiter:edition/{pageId}-{year}-{letter}` as a precondition, so that resegmentation does not scramble editor patches and citability. Approach via an editor-reviewed sample gate before the full run.
**Open.** The four operator gate questions stay unchanged, Gate 1 precedes Gates 2 and 3; to be put to the editor are impression sublines as separate nodes or structured description and collected-volume occurrences via `schema:isPartOf`; the neighbourhood check of the `llmprov` profile is outstanding.

## 2026-07-18 — Session 21: EIL editor increments 2 and 3

**Round.** Implementation round after operator release, built was only what hangs on no gate question.
**Changed.** Increment 2 review hints per entry, new step `pipeline/build_triage.py` reduces the committed verify and census reports to `docs/data/triage.json` (`notInSource`, `detectable` with add candidate, `census` for 2979), `edit.js` bundles them into a hint list ordered by signal class with chip, field marker and edit sorting. Increment 3 source evidence per field, in edit mode the value-carrying source text excerpt stands next to each of the four tracked fields, marked whitespace-tolerantly, multiple hits are counted (makes multi-edition ambiguity visible at the field), fallback to the whole source text. Verification in three layers (Python triage pin, JS logic pin, browser on localhost).
**Decided.** Deliberately no metric, no score, a hint expires as soon as the field is adjudicated; until calibration, the class ordering is the documented review priority, no empirical signal; `triage.json` is built from committed reports and regenerated after every pipeline run.
**Open.** Increment 4 local write-back and editable titles hang on the gate questions; the triage calibration awaits the stratified field sample.

## 2026-07-18 — Session 20: Concept round, EQUALIS removal, knowledge refactor

**Round.** Purely conceptual round after an operator decision, no implementation, no pipeline runs.
**Changed.** EQUALIS as an evaluation framework removed without residue from the knowledge holdings and switched everywhere to the hermeneutic-qualitative framing, the earlier ratio-as-evidence-of-success formulation replaced by the protocol framing (the metrics section in [[data#Correction Protocol]] is now called Correction Protocol, a documentation basis instead of a measuring instrument); knowledge folder refactored according to the Promptotyping convention, `index.md` freed of volatile status figures and made self-supporting; concept document `production-readiness.md` created with current state, the two loops, the provenance layers regex/llm/missing as the verification basis, the gold standard as a measurable building block, six ordered work packages and four operator gate questions.
**Decided.** Evaluation is hermeneutic-qualitative, the only measurable building block is the gold standard verified in the tool, the ratio is no evidence of success; no knowledge document deleted or merged, because no genuine redundancy exists; the operational state lives, by convention, outside the navigation document.
**Open.** The four gate questions (curate multi-edition or defer it, reconciliation depth, wiki print merge in scope, model route in the deliverable state); additionally whether the knowledge frontmatter is lifted repository-wide onto the Promptotyping mandatory core, deliberately not touched in this round.

## 2026-06-21 — Session 19: EIL editor increment 1

**Round.** Implementation round after an operator direction decision, strand 2 (expert editing layer) instead of further data-fidelity hardening.
**Changed.** `docs/js/edit.js` raised from the thin v1 demo to the full increment 1 model, every field interaction typed as Accept/Correct/Add (distinguished via provenance and initial value), every action carries the full v2 edit history form, three-status review per entry as a chip, pending edits reload-proof in localStorage, Save exports a `patchVersion: 2` document for `apply_patches.py`; `detail.js` renders editable cell, action controls, review chip and the full source text as an evidence panel. Verification via a patch contract pin (JS export against Python apply) and a browser review on localhost.
**Decided.** Silent divergence fixed, the backend wrote provenance `editor` while the frontend knew only `expert`, now canonically `editor` with `expert` as an alias; the deploying push stays an operator gate, bundled with the M3 data publish, the editor code is localhost-only and inert for visitors.
**Open.** Increment 2 (calibrated triage signal), increment 3 (raw wiki per field), increment 4 (local write-back endpoint).

---

## 2026-06-21 — Session 18: Location fix and mojibake repair landed

**Round.** Milestone round, two fixes built, tested, secured to main, milestone 3 scoped and verified locally as a preview.
**Changed.** Location fix landed in `extract_location` and measured deterministically via `measure_location_fix.py` (443 changed, 795 newly gained, 0 lost; 43 of the 48 Weimar cases moved to the real source location, 5 headerless or a non-listed transliteration). A dot-separator addendum prevented a header fallback from grabbing a publisher name as a location. Mojibake repair of the transliteration block reworked as a run-wise redecode instead of line decoding, self-validating and idempotent (62,351 runs repaired, 0 self-rejected, 0 remaining); the empty-content branch now shows page 2979 with `page_title` "A unidade espiritual do mundo". All three secured by unit tests, no new red colouring.
**Decided.** Do not commit half-finished, the location fix couples to the mojibake repair, because residual mojibake reaches the location on class 3 entries; no block whitelist guard for mojibake, because it would have discarded 5 legitimate non-Latin repairs; the M3 full run is decoupled and purely executing, yet must reuse the committed LLM cache, because the Gemini API fails in the environment.
**Open.** M3 is verified locally (`m3-preview-report.json`, end to end 0 locations and 0 titles lost), yet unpublished; the publish push awaits operator release, because it deploys live.

## 2026-06-21 — Session 17: Record census and EIL editing design

**Round.** Portfolio round with two strands, verify data integrity from the SQL through to the frontend and design the in-tool editing layer.
**Changed.** `pipeline/census.py` built, reproducible record reconciliation across three layers, five identities all PASS (JSON-LD 1:1 with the source, no loss, no duplicate, no invented record); editing design as a knowledge document (three typed actions, uncertainty surface from provenance/verify/census, persistence in three layers, correction protocol, five increments) with an explicit DIA-XAI connection; write-back and audit layer `apply_patches.py` implemented (overlay after inject_provenance, provenance `editor`, edit history per field, idempotent, an empty store is a no-op). Addenda in the round: frontend validation with four confirmed field error classes; all external JS and font dependencies vendored locally into the repository; Weimar fix designed and measured.
**Decided.** The 2979 question from session 1 conclusively settled, source-side loss through blanking three minutes after creation, no pipeline error; census as a third verification tool alongside verify.py and 06_validate.py for the record completeness axis; 2979 not fixed unilaterally, show-with-title versus exclude is an editorial matter; a data rescue tool must not depend on external CDN availability (a shared browser cache contaminated the CORS headers); the Weimar fix lands only together with its three cleanup subproblems and the mojibake repair.
**Open.** Operator decisions on 2979 and on building the editing increments.

## 2026-06-12 — Session 16: Full-codebase refactoring (multi-agent)

**Round.** Four-lane analysis with parallel agents, then two implementation waves on disjoint areas.
**Changed.** Frontend decluttered (dead `explore-overview.js` and two unreachable methods removed, `utils.topN()` replaced four identical call sites, network filter listeners unified); behaviour-neutral pipeline cleanup (`03c_normalize.py` aligned to the step pattern, missing `publisher_normalize.json` created, dead imports removed, `EXTRACTED_FIELDS` centralized); tests refactored (`test_normalize_unit.py` written before touching 03c, two always-skipped regression tests activated, `KNOWN_*` centralized in `baseline-metrics.json`, `broken_see_also_refs` ratcheted 727 to 622 as a genuine data improvement); outdated figures unified document-wide and the reconciliation contradiction resolved (LOD linking permitted and implemented, inventing values forbidden). Browser smoke test green; `locationSameAs` emitted as a Wikidata URI per primary location; 22 unmatched locations triaged into a review template.
**Decided.** Figures drift because they are hard-coded in several places, hence a responsibility matrix with one source each; always-skipped tests are worse than none; deliberately not done were mojibake regex consolidation, language list dedup and SQL parser unification, because without a new pipeline run they are not provably behaviour-neutral.
**Open.** EIL verification workflow as the next work package; editor review of the unmatched locations; fill `publisher_normalize.json` with real variants via the editor loop.

---

## 2026-04-12 — Session 15: Geography, timeline modes, normalization, Wikidata

**Round.** Implementation round exploration and data quality (summarizes the two session 15 entries of the day).
**Changed.** Geography view with an orthographic globe and a flat map toggle plus semantic zoom (country to city bubbles); Wikidata reconciliation via `reconcile_locations.py` (360/382 matched, `locations.json` enriched with Q-IDs and country codes); three timeline modes bars/sparklines/ranks instead of stream, global provenance toggle, hash-based URL state persistence; pipeline step 03c normalization with auditable external mapping tables (location variants, publisher garbage rejection, translator cleanup, pageCount outliers); all 8 fields profiled for normalization candidates, publisher identified as the largest residual problem (1,316 singletons require manual review).
**Decided.** Country codes were missing entirely and made the semantic zoom an empty shell, reconciliation solved that and delivered LOD Q-IDs as a bonus; stream visually weak, because curveBasis smooths discrete data and stackOffsetWiggle removes the zero line, bars/sparklines/ranks serve the three research questions better; normalization as a separate step keeps extraction and cleaning separable and does not violate the data integrity principle; the publisher coverage drop 55.5 to 52.2 percent is correct, garbage removed instead of valid publishers.
**Open.** Test new features in the browser (sparklines, ranks, globe, semantic zoom); publisher clustering by manual review; language for film/symposium/translation; seeAlso resolution; `locationSameAs` into the JSON-LD output; multi-edition decomposition.

---

## 2026-04-12 — Session 14f: Timeline redesign

**Round.** Implementation round timeline rebuild.
**Changed.** Stacked area to stacked bars (discrete bibliographic counts per year instead of interpolated curves), layer toggle by language or type, provenance overlay per year, semantic zoom via the brush extent, five biographical annotations with collision avoidance, brush cross-view events for Geography and Connections; overview mode together with dead code removed, three modes remain.
**Decided.** Stacked area was wrong for discrete count data, bars represent it honestly; overview was redundant, the timeline with layer toggle and zoom covers it with better interaction; the provenance overlay works as a Developer-in-the-Loop tool, because it shows where data quality varies over time.
**Open.** Further modes sparklines and ranks; test layer toggle and provenance overlay in the browser.

---

## 2026-04-12 — Session 14: Semantic testing, extraction fixes, pipeline limit

**Round.** Implementation and analysis round data fidelity.
**Changed.** `_provenance` block and compact data verification brought into the frontend; 10 entries compared against the live wiki (23 percent of the fields wrong); semantic testing layer created (`test_semantic.py`, `test_heuristic.py`, ground truth); five extraction fixes, the title fallback to `page_title` with the greatest effect (1,368 section headers to 0), plus pageCount and publisher cleanup and an encoding guard.
**Decided.** The pipeline is at the natural limit of regex extraction, further fixes shift errors (value A to value B) instead of solving them; the 427 multi-edition pages (6.8 percent) cause systematic errors, because the page as a container of several publications is treated as one flat entry; `page_title` is more reliable than extracted titles; semantic tests are the most valuable addition, because they quantify what is wrong and prevent regressions.
**Open.** Extend ground truth from 10 to 30+ in a stratified way; go through the frontend systematically; consider LLM-based edition block segmentation; WCAG 2.1 AA audit and performance measurement.

---

## 2026-04-12 — Session 12: JSON-LD validation, playground, project audit

**Round.** Implementation and audit round JSON-LD and codebase.
**Changed.** Data integrity principle documented in CLAUDE.md (LLM audit confirms 0 hallucinated values across five anti-hallucination layers); JSON-LD @context corrected in five points and validated with PyLD (expansion, compaction, N-Quads pass); JSON-LD playground frontend built; project audit found three bugs and several documentation inconsistencies. Bugs fixed, among them the critical wrong key in `06_validate.py`/`verify.py`, which silently processed 0 entries, as well as four different year caps and three diverging `ABOUT_ZWEIG_TYPES` definitions.
**Decided.** Silent validation failures are the worst bugs, because the fallback `[]` reports no error, always check inputs for non-emptiness; constants defined more than once drift, the pipeline is the source and the frontend mirrors; documentation decays faster than code, automated grep checks on known figures caught that.
**Open.** Nothing named beyond the running data quality strands.

---

## 2026-04-12 — Session 11: Testing strategy revised

**Round.** Implementation round test strategy after a critical audit of the existing 280 tests.
**Changed.** `knowledge/testing.md` created with an honest taxonomy; three new data test files across all entries (`test_census.py` completeness, `test_schema.py` schema, `test_consistency.py` cross-field plausibility); regression and real-entry tests revised (broken `test_year_range_sane` fixed, thresholds sharpened, silent skip logic removed). Findings drawn in as bounded known errors (14 `__TOC__` titles, 6 markup titles, 111 German translator FPs, 717 broken seeAlso refs, 10 films with pageCount, page 2979 as a stub which the documentation wrongly listed as "missing").
**Decided.** Testing functions is not testing data, the 280 unit tests proved the regex on cherry-picked strings, none asked about completeness or field values; formal correctness is not content correctness, only cross-field tests flag implausible combinations; silent test passes are worse than no tests; the largest gap remains semantic accuracy, because only a fraction of the entries is checked for correctness.
**Open.** Fix the 20 markup titles in the pipeline; investigate the 111 German translator FPs; extend the real-entry sample from 20 to 50; improve seeAlso matching.

---

## 2026-03-31 — Session 10: Frontend cleanup, data quality, regression tests

**Round.** Implementation and analysis round frontend and data quality.
**Changed.** Frontend refactored across 12 files (`COLORS` as the single colour source against the CSS/JS mismatch, unused helpers wired up, `esc()` ~10x faster via regex, SRI hashes, event delegation, ARIA labels); data quality deepened in three investigations (title precision, publisher gap, missing system checks); regression test infrastructure created (`baseline-metrics.json`, 18 tests, CI extension); title extraction improved (`correct_fallback` status, second bold block before the page_title fallback, `__TOC__` removal).
**Decided.** Verification must match the extraction methodology, verify.py blindly checked "value in raw text" without knowing the page_title fallback and produced 880 phantom FPs; not every coverage gap is a bug, the 44 percent publisher gap is predominantly structural (anthology poems, journal articles without a publisher of their own); unit tests are no regression safety, system baseline comparison is essential for data pipelines; colour values drift without a build step, a shared constants file is the simplest remedy.
**Open.** Re-run the pipeline with the title improvements and measure the effect; M3.8 manual validation of 50+ entries in the live frontend.

---

## 2026-03-29 — Session 9: Interactive exploration interface and refactoring

**Round.** Implementation round exploration.
**Changed.** Generic Chart.js dashboard replaced by a D3 v7 exploration with three modes (timeline with stacked area and biographical annotations, overview with four linked small multiples, connections as a force graph of the seeAlso references with ~496 resolved edges) plus a shared detail panel; UX and exploration fixes; five refactorings (BibTeX dedup, O(1) titleMap, `countByField()`, generic wiki section extractor, encoding utilities moved); exploration design as a knowledge document with research questions and DH references.
**Decided.** Generic dashboards do not serve academic research, researchers need purpose-built tools with concrete research questions; D3 via CDN carries static pages well and the timeline immediately tells the Zweig reception history; seeAlso networks are thinner than expected on account of unresolved title references; the ~500 "Unknown" language entries dominated the timeline and were folded into "Other".
**Open.** M3.8 manual validation; exploration refinement (real streamgraph offset, mobile experience).

---

## 2026-03-29 — Session 8: Deployment preparation and namespace fix

**Round.** Implementation round deployment.
**Changed.** Namespace URI corrected across 10 files from `klawiter-rescue.github.io` to `chpollin.github.io/klawiter-rescue`, GitHub footer link corrected from a foreign user to `chpollin`, LICENSE created as a dual license and CITATION.cff created, README extended by the live URL and license, JSON-LD and frontend JSON regenerated via steps 05/06; tests green.
**Decided.** The URI had wrongly been set as an organization page, the real deployment is a project page under the personal account, which affected @context resolution and all hard-coded URLs; the footer link pointed to an earlier contributor.
**Open.** M3.8 manual validation with wiki comparison; M7 remainder live deployment test, Zenodo DOI, announcement.

---

## 2026-03-29 — Session 7: Design alignment, consortium navigation, EIL curation interface

**Round.** Implementation round design and curation.
**Changed.** GAMS colour palette and Source Serif/Sans typography adopted across the consortium sites, shared consortium navigation bar across three sites, SZD frontend translated into English and dashboard rebuilt along CIDOC-CRM lines, Klawiter landing page moved to expandable category groups with browse and explore paths; EIL curation built (`inject_provenance.py` diffs regex against the LLM cache into `_provenance` regex/llm/missing, `edit.js` as a localhost-only edit mode with JSON patch export, provenance badges, validation workflow on PRs).
**Decided.** Provenance tracking creates trust by making the extraction source visible and letting "missing" direct attention; localhost-only editing is a pragmatic security model for a static site without auth; shared navigation across three Pages deployments demands a stable URL structure.
**Open.** Nothing named beyond the running strands.

---

## 2026-03-29 — Session 6: Knowledge base audit and documentation refactoring

**Round.** Audit round documentation.
**Changed.** All vault files, README, CLAUDE.md and the implementation plan checked against code and data output, 18 factual inaccuracies found and fixed across all files (ontology wrongly "pending", 15 instead of 16 entry types, 6 instead of 7 stages, 4 instead of 9 MB, missing sessions 4–5, SZD institution wrong), plan consolidation with a corrected dependency diagram.
**Decided.** Documentation debt accumulates fast, three features shipped on the same creation day without a documentation update, the docs were internally consistent yet collectively outdated; cross-referencing counts, isolated vault files without wikilinks are invisible in the knowledge graph; two planning files create confusion and demand discipline.
**Open.** Nothing named.

---

## 2026-03-29 — Session 5: Frontend content pages and data quality fixes

**Round.** Implementation round content pages and data quality.
**Changed.** Five content pages (About, Methodology, Help, Data Access, Imprint) with navigation and footer column; vocabulary checked against the real `@context`; pipeline fixes (bare years rejected as original titles 272 to 0, section headers and unpaired bold markers removed from titles, `@container: @set` added); automated validation of all ns0 entries found and fixed a translator regex leak across line breaks (34 to 0); pipeline re-run, tests green.
**Decided.** Vocabulary docs must be verified against the code, the page claimed `sameAs` as used although no entry carried it; Schema.org is more complete than assumed, `Play` and `Collection` exist; markup in titles has a long tail; `\s` in regex character classes matches line breaks, `[ \t]` correctly restricts to horizontal whitespace.
**Open.** Nothing named.

---

## 2026-03-29 — Session 4: Frontend redesign and Schema.org vocabulary

**Round.** Implementation round frontend and vocabulary.
**Changed.** Frontend aligned to the SZD visual language (own CSS with SZD palette, serif/sans system, four-view architecture, eight JS modules extracted from the monolith, expandable result cards, clickable charts, BibTeX/RIS export with correct author logic, responsive); Schema.org plus Dublin Core vocabulary implemented in `vocabulary.py` (16 entry types onto Schema.org types, standard fields via Schema.org, `dcterms:bibliographicCitation`, `klawiter:` namespace, Stefan Zweig as `schema:Person` with a Wikidata link), `05_to_jsonld.py` rewritten onto it, vocabulary namespace page created.
**Decided.** The category portal approach carries, MediaWiki-familiar users navigate by tiles as expected, the landing page is orientation and no dashboard; expandable cards beat separate detail pages, because they hold context; dual type arrays are elegant, `@type` with a Schema.org type and a klawiter type gives interoperability without loss of information.
**Open.** Nothing named.

---

## 2026-03-29 — Session 3: Test suite and LLM-as-a-judge

**Round.** Implementation round tests.
**Changed.** Initial suite of 171 tests built, then critically trimmed (redundant guard clause and whitelist tests removed, weakened title tests fixed onto the real pipeline flow); real-data tests across 20 hand-labelled entries with five extractors; LLM-as-a-judge (`test_llm_judge.py`) with Gemini and structured Pydantic output, establishing a baseline of known limits (10 wrong, 13 missed); pytest markers to separate fast and API tests.
**Decided.** Redundant tests create false confidence, 171 tests sounded like a lot, the real-data tests found more than all guard clause tests together; LLM-as-a-judge is effective and catches semantic errors that pattern tests do not see; fixture text truncation produced six false failures; LLM non-determinism is handled via a known-wrong set that turns red on anything new.
**Open.** Nothing named.

---

## 2026-03-29 — Session 2: Pipeline quality assurance and LLM enrichment

**Round.** Implementation round verification and LLM.
**Changed.** `verify.py` built as round-trip verification (every field against the raw wiki, FP and FN detection, broader patterns for publisher and translator), results reported per field with coverage and precision; step 03b `03b_llm_enrich.py` designed and built with Gemini as a gap filler (Pydantic schema, merge rule fills only empty fields and never overwrites regex, cache resume, validation); tested across a 20-entry stratum, 13/13 correct, 0 hallucinations, all negative tests passed.
**Decided.** Verification circularity, the same regex patterns used for FN detection find nothing, that requires broader heuristics or an LLM; the LLM is conservative by prompt and returns null for see references, films and German originals; encoding artifacts pass through untouched, because mojibake repair is step 02's task.
**Open.** Nothing named.

---

## 2026-03-29 — Session 1b: Raw data verification

**Round.** Analysis round, two parallel agents verify the raw source against the extraction logic.
**Changed.** Analysis only, no code; BLOB file sizes corrected in pipeline.md.
**Decided.** The pipeline is correct, all 6,296 ns0 pages are processed, 6,295 find their content in the BLOBs; the one missing entry is page_id 2979 (text_id 18046, Portuguese edition), a source data problem, because the text_id lies in no BLOB; the 429 non-ns0 pages are excluded by design, among them 420 category pages; the SQL dumps 02 and 03 are correctly ignored (empty schema, system metadata); only the respective latest revision per page is extracted.
**Open.** Whether the 420 category pages are extracted for richer descriptions; whether the discarded historical revisions are ever needed; whether the missing Portuguese entry can be recovered via a title search in the BLOB instead of via the text_id.

---

## 2026-03-29 — Session 1: Repository restructuring and planning

**Round.** Milestone round, founding of the current project structure.
**Changed.** Repository restructured (v2 contents promoted to root level, `frontend` to `docs` for Pages, `working` to `data/raw`, path references adjusted in all seven scripts, all legacy files deleted, new .gitignore); knowledge base refactored (10 German documents consolidated into focused English ones, new ontology and reconciliation documents, wikilinks verified); `plan.md` created with seven milestones and a dependency chain.
**Decided.** Duplicated path definitions made the restructuring harder, full consolidation to config.py imports planned; verification must always be broader than the repair, the first encoding fix claimed 0 percent mojibake yet checked only seven patterns, 9.1 percent remained; an outdated CLAUDE.md is worse than none, because it actively misleads; Windows case insensitivity and IDE file locks as pitfalls.
**Open.** Manual validation against the source (50-entry sample, should happen early); the one missing entry; publisher extraction at 34.5 percent as the weakest field with three approaches; translator FP trade-off and possible confidence scores; non-resolving JSON-LD namespace URI; SZD integration and design alignment; unclarified data license; performance measurement on mobile; missing content negotiation on Pages; missing FAIR building blocks (PID, standard vocabulary, license).
