---
title: Quality Assurance
aliases: [testing, tests, validation, quality assurance]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: complete
language: en
version: 1.1
tags: [testing, validation, quality, evidence]
created: 2026-04-01
updated: 2026-08-27
authors: [Christopher Pollin]
related: [data, pipeline, frontend, production-readiness]
---

# Quality Assurance

## Check Commands

```bash
python -m uv run pytest -q
python -m uv run pytest -q -m semantic
python -m uv run pre-commit run --all-files
python -m compileall -q pipeline tests
node --test tests/*.test.js
git diff --check
```

The static checks (ruff check, ruff format) are defined in `.pre-commit-config.yaml`; CI runs the same hook set.

The default pytest set excludes the diagnostic individual assertions with the marker `semantic`. An aggregated bound nevertheless prevents the known semantic deviation count from rising unnoticed. The semantic suite is run separately and may report known, exactly documented deviations visibly.

## Test Layers

### Record Completeness

`pipeline/census.py` and `tests/test_census.py` check the identities source = JSON-LD and frontend = JSON-LD minus redirects. Missing, invented and duplicate records cause a failure. The one bibliographic page without a text body is explicitly bounded as a named stub.

### Schema and Value Ranges

`tests/test_schema.py` checks all records for types, year and page ranges, language codes, empty values, wiki markup and known encoding artifacts. This layer detects structural errors, yet cannot judge plausible but factually wrong values on its own.

### Consistency and Regression

`tests/test_consistency.py`, `tests/test_heuristic.py` and `tests/test_regression.py` check cross-relations, distributions and known error limits. `.github/baseline-metrics.json` contains the ratcheting-capable bounds. A demonstrated improvement lowers an error bound or raises the stable redirect resolution; a deterioration must not be frozen as a new baseline.

The title fallback uses MediaWiki page titles instead of edition headers as record titles; the redirect map additionally contains page-title aliases from stage 05, whereby the remaining broken `seeAlso` references are genuine red links. The frozen counts are held in `.github/baseline-metrics.json`.

### Extraction and Normalization Units

Unit and real-entry tests cover encoding, wiki parser, field patterns, vocabulary, normalization, patch replay, provenance and the production runner. Regression tests preserve the source-conditioned empty stub and the handling of `[ca. year]` headers.

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

`tests/test_reconciliation.py` secures the data contracts, `tests/contested_claims.test.js` the display and export of contested statements.

### Frontend Logic

Node tests check exact occurrences, snippet formation, triage priority, pending/editor suppression, reconciliation lookup, stably sorted export, the routing guard together with the editing-mode gate and the ordering of the candidate queue of the data quality workbench. Syntax checks run for all JavaScript modules. A browser smoke test remains a complementary visual check.

## Agentic Review

The edition sample comprises 76 segments from three complex pages. Two independent initial reviews worked against schema, source excerpt and hash. An independent stronger verification agent reconciled the deviations. The result confirms 75 segments and preserves one work binding as an open claim.

The location review examined the remaining low-scored cases independently. Confirmations and corrections were adopted as decisions. Five cases stayed open in domain terms and were materialized as contested claims.

Agentic decisions are traceable through reviewer, input hash, result and evidence file. A later external expert review is additional validation.

## Semantic Sample

`tests/wiki_ground_truth.json` contains ten entries with seven fields, checked against the earlier web presentation. The sample makes concrete field deviations visible, yet measures no corpus-wide error rate. Multi-edition pages dominate its known failures.

The per-field tests stay deliberately marked separately. The aggregated default-test bound in `.github/baseline-metrics.json` prevents a silent deterioration. After a documented correction, the bound is ratcheted downwards.

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
