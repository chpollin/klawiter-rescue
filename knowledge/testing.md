---
title: Quality Assurance
aliases: [testing, tests, validation, quality assurance]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: maintained
language: en
version: 1.2
tags: [testing, validation, quality, evidence]
created: 2026-04-01
updated: 2026-09-05
authors: [Christopher Pollin]
related: [data, pipeline, frontend, production-readiness]
---

# Quality Assurance

## Check Commands

```bash
python -m uv run pytest -q
python -m uv run python pipeline/run_pipeline.py --to-stage 04 --no-postprocess
python -m uv run pytest -q --require-test-inputs --durations=10
python -m uv run pytest -q -m semantic
python -m uv run pre-commit run --all-files
python -m compileall -q pipeline tests
git diff --check
```

The static checks (ruff check, ruff format) are defined in `.pre-commit-config.yaml`; CI runs the same hook set.

The default pytest set excludes the `llm` and `semantic` markers. It still checks the exact known deviations: page ID, field and observed mismatching value must match `.github/semantic-baseline.json` for the frontend or `.github/extraction-baseline.json` for the rule extractors. A repaired case cannot conceal a new failure elsewhere. The separate semantic suite keeps the individual failures red. Both use the same exact comparison, allowing only explicitly recorded source-backed title variants.

Committed JSON exports, metrics and hand-reviewed fixtures are required. Missing or malformed files fail rather than skip, and the sample never falls back to an untracked intermediate. Node.js and the regenerable stage CSVs may be absent for a partial local run; `--require-test-inputs` or `CI=true` makes their absence an error. Unknown markers/configuration keys also fail. Isolated pytest runs in `tests/test_test_inputs.py` verify these failure paths without touching the real data.

CI runs the strict default suite, then the semantic diagnostics with `continue-on-error` because they retain known failures. Both produce JUnit artifacts in `test-results/`. Only the diagnostics are non-blocking; the exact semantic regression guard runs in the blocking default suite.

## Test Layers

### Record Completeness

`pipeline/census.py` and `tests/test_census.py` check the identities source = JSON-LD and frontend = JSON-LD minus redirects. Missing, invented and duplicate records cause a failure. The one bibliographic page without a text body is explicitly bounded as a named stub.

### Schema and Value Ranges

`tests/test_schema.py` checks all records for types, year and page ranges, language codes, empty values, wiki markup and known encoding artifacts. This layer detects structural errors, yet cannot judge plausible but factually wrong values on its own.

### Consistency and Regression

`tests/test_consistency.py`, `tests/test_heuristic.py` and `tests/test_regression.py` check cross-relations, distributions and known error limits. `.github/baseline-metrics.json` contains the ratcheting-capable bounds. A demonstrated improvement lowers an error bound or raises the stable redirect resolution; a deterioration must not be frozen as a new baseline.

The title fallback uses MediaWiki page titles instead of edition headers as record titles; the redirect map additionally contains page-title aliases from stage 05. An unresolved `seeAlso` reference is a diagnostic signal and must not be called a genuine source red link without source adjudication. The frozen counts are held in `.github/baseline-metrics.json`.

### Extraction and Normalization Units

Unit and real-entry tests cover encoding, wiki parser, field patterns, vocabulary, normalization, patch replay, provenance and the production runner. Regression tests preserve the source-conditioned empty stub and the handling of `[ca. year]` headers.

`tests/test_sample_20.json` now contains the complete normalized source text for all twenty records, source BLOB/text IDs, raw and normalized text hashes, and one hundred reviewed expectations for publisher, location, translator, numbered-page extent and category language. Positive expectations carry exact source-line selectors; null expectations have explicit review notes. The fixtures are compared against complete stage-02 rows. Their texts were also checked directly against the raw BLOB records during restoration.

The old `existing` extraction snapshots and `needed` hints were removed. Every field now receives both a default regression check and an exact semantic diagnostic, including null values. These are field-level checks with documented scope: bibliographic fields follow the first cited item unless the note states an ambiguity, while category language tests the first language-bearing category. They do not establish edition-level coherence for an entire multi-edition page. In particular, the bilingual thesis page 4445 has an Arabic category before German, independently of the first German thesis imprint.

The initial restored fixture exposed twenty rule/expectation disagreements against unchanged production code. The [fixture review](test-fixture-review-2026-09-05.md) and [independent evaluation](independent-evaluation-2026-09-05.md) preserve that historical inventory. Source-reviewed remediation subsequently resolved six cases and retained fourteen. `.github/extraction-baseline.json` records their exact observed values separately from the unchanged correct expectations. Partial name-transcription improvements on pages 1891 and 285 are documented without accepting their unresolved publication scope.

The [technical remediation](technical-remediation-2026-09-05.md) distinguishes rule changes from published changes and explains why removing citation locators lowers extent coverage legitimately. No test tolerance was widened to accept deteriorating output.

### Work/Edition Gate

Gate 1 checks the complete graph:

- SHACL for work, edition, annotation, carrier, claim, interpretation, ReviewAction and work identity candidate;
- exact text selectors and SHA-256;
- stable and unique identifiers;
- complete prioritized queue;
- separation of confirmed relations and contested claims;
- deterministic rebuild from frozen inputs.

The results are recorded in `validation-report.json` and EARL.

### Reconciliation Gate

Gate 2 checks:

- complete separation of candidate, decision, open claim and publishable link;
- exact source evidence for every unresolved case;
- occurrences or a spelled-out null finding for every agent subject with a candidate;
- supersession history for decision patches;
- input hashes for edition graph, location data, review, decisions, SZD index and classified source;
- identical JSON-LD and frontend projection;
- deterministic rebuild.

`tests/test_reconciliation.py` secures the data contracts, `tests/contested_claims.test.js` the display and export of contested statements. Source-page occurrence completeness is checked for every frozen agent subject. The complete reconciliation builds once per session. The unresolved-agent decision tests each reuse one real person or publisher and all its source rows, then compare its evidence with the full integration result; they do not rebuild unrelated work and location candidates.

### RDF field preservation

`tests/test_rdf_field_preservation.py` expands JSON-LD with RDFLib and asserts the exact nested source-summary and contested-evidence literals, links and registered vocabulary terms. A valid top-level JSON document alone does not detect a child property silently dropped during RDF expansion.

### Frontend Logic

`tests/test_frontend_logic.py` automatically discovers every `tests/*.test.js` behavior file and runs `node --check` for every `docs/js/*.js` module. Adding a file needs no manual Python bridge entry. Node tests cover occurrences, snippets, triage, editor sessions, search normalization, reconciliation, export, routing and queue order. These checks exercise logic and syntax; they do not prove DOM interactions, accessibility or performance in a browser.

Frontend, canonical JSON-LD and classified rows are shared session fixtures. Semantic diagnosis and its default guard use the same comparison and page-ID index. Edition tests share one corpus build but receive deep copies, so review overlays cannot leak between tests.

## Agentic Review

The edition sample comprises 76 segments from three complex pages. Two independent initial reviews worked against schema, source excerpt and hash. An independent stronger verification agent reconciled the deviations. The result confirms 75 segments and preserves one work binding as an open claim.

The location review examined the remaining low-scored cases independently. Confirmations and corrections were adopted as decisions. Five cases stayed open in domain terms and were materialized as contested claims.

Agentic decisions are traceable through reviewer, input hash, result and evidence file. A later external expert review is additional validation.

## Semantic Sample

The semantic suite has two distinct targets: seventy frontend field assertions from the ten records in `tests/wiki_ground_truth.json`, and one hundred rule-extraction assertions from the twenty complete texts in `tests/test_sample_20.json`. The former retains its seventeen known deviations; the latter retains fourteen rule/expectation mismatches after the reviewed repairs. The resulting thirty-one failing assertions are not thirty-one demonstrated product data errors: they span different layers and include unresolved field-selection contracts. Neither selected sample estimates a corpus-wide error rate.

The per-field tests stay deliberately marked separately. `.github/semantic-baseline.json` names the exact known cases and records the input hash, ten page IDs, seven fields and the commit at which failures were observed. Collection rejects a changed fixture hash, a removed/replaced/duplicate page or a missing field; the default guard also checks its comparison inventory. Isolated mutation tests demonstrate that changing only the hash cannot conceal lost coverage. Its mismatch count must agree with `.github/baseline-metrics.json`. A replacement on another page/field or a changed mismatching value fails the default gate.

Titles require exact equality with the expected title or an explicit per-entry `accepted_title_variants` value. Page 285 permits its exact source page title with the `(VIST)` disambiguator; stage-02 metadata verifies that variant. Invented suffixes, extensions of that variant, and transferring its suffix to another page fail both checks. No generic prefix or suffix stripping is used.

When changing a reference fixture, review the source and field scope first, document the reason beside the expectation, and update the fixture hash. Change the page/field inventory only when the intended sample changes. When correcting production output, remove resolved cases from the mismatch list and lower the bound after source review. Resolved cases emit a warning until retirement; the same old value could otherwise recur without a new failure. Never regenerate expectations or mismatch allowances from failing output to make a run pass.

### Remaining Test Work

The ten legacy skips have been removed. The source disproved the old range-only exception for page 162: its book has 254 numbered pages, whereas page 1999 only has citation locators, including p. 425. Complete texts restored the four truncated language contexts. Null fields are now explicit assertions. The oracle inventory and title-comparison gaps are closed. Settle ambiguous expectations at publication/contribution scope, correct confirmed extraction defects, retire resolved baseline cases and require their exact semantic assertions to pass. Do not copy extractor output into expected values.

The optional live LLM judge now selects stable page IDs and receives complete texts rather than 500-character fragments. Its historical model-judgment inventory has not been recalibrated; no live API call was made during this refactor. Deterministic source expectations provide the test oracle, subject to the explicit scope limitations and unresolved interpretations documented in [[independent-evaluation-2026-09-05]].

Browser checks now exercise missing-language and multiple-value handover, reload/back state, visible navigation and absence of horizontal overflow at 320, 390 and 1280 pixels. Queue lifecycle is covered by repeated-render Node tests. Dashboard acceptance and its exact evidence are recorded in [Status](status.md). Broader browser validation of exports and correction persistence remains open. A broader stratified semantic sample and measured accessibility/performance budgets are still needed before claiming product acceptance. Passing the refactored suite does not close those gaps.

## CI reproduction boundary

Gate 1 and Gate 2 rebuild their core documents inside the validators. CI then runs `pipeline/verify_committed_evidence.py`, reading the reviewed manifests directly from Git HEAD so regeneration cannot replace the reference. Every stable key/value must match, including source/input/code hashes, counts, validation and operator points. Only the run timestamp and hashes of the explicitly timestamped EARL/PROV/validation artifacts may differ; their files must still exist and match the current manifest hashes. All referenced input and artifact bytes are checked, including the ignored reconciliation candidates and review queue. The existing explicit Git-diff artifact list remains an additional comparison.

`tests/test_committed_evidence.py` exercises missing files/keys, changed candidate/queue bytes with and without refreshed hashes, changed stable input/count/code metadata, JSON type changes and the allowed timestamp-only differences. A missing source cannot turn into a green empty check.

Freeze a reviewed semantic change by committing both current gate manifests with the matching code, inputs and generated outputs. Before that commit, comparison against HEAD correctly detects the pending change. For local review only, `--reference-dir <snapshot-root>` accepts the already reviewed manifests at their repository-relative paths. It does not update the reference or alter production artifacts. CI uses HEAD and no override.

Before freezing evidence on an existing Windows checkout, inspect referenced tracked text inputs with `git ls-files --eol`. An older working copy can retain CRLF bytes after `.gitattributes` starts requiring LF, even when `git diff` is empty. Confirm that normalizing those bytes produces the exact committed blob before aligning the local copy and rebuilding the affected gate. Keep raw archival bytes unchanged. Session 34 records the location-input mismatch caught by the first remote reproduction check.

## Production Evidence

| Evidence | Statement |
|---|---|
| `data/output/quality-report.json` | record counts, coverage and schema notes |
| `data/output/verification-report.json` | occurrence-based field verification |
| `data/output/census-report.json` | lossless record chain |
| `data/output/editions/validation-report.json` | Gate 1 contract |
| `data/output/reconciliation/validation-report.json` | Gate 2 contract |
| `data/output/*/earl.jsonld` | machine-readable check results |
| `data/output/audits/` | baseline, repeatability and independent final check |

## Limits of What Is Asserted

Automatically documented are record completeness, schema, known bounds, selector integrity, decision separation and repeatability of the data core. Agentically documented are the documented sample and low-score decisions.

Two structural limits of the round-trip verification must be named. First, the circularity. `verify.py` checks extracted values against the same raw text from which they were extracted; a systematically wrong string that is present in the text passes the check. The comparison documents fidelity to the source, no factual correctness. Second, the substring weakness of the `correct` definition. A value counts as documented as soon as it occurs as a substring in the raw text; a shortened value, or one originating from the wrong edition block, can thereby count as correct, especially on multi-edition pages. For that reason the occurrence display in the editing mode makes multiple occurrences explicit.

Not documented are a corpus-wide factual accuracy rate, the institutional work identity of the graphic novel adaptation and the correctness of unreviewed candidates (including the new translator and publisher review stock). The complete queues keep these cases visible. [[production-readiness]] names the remaining Operator Points.
