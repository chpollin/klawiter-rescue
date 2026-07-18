---
title: Testing
aliases: [test strategy, quality assurance, validation, field fidelity]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: complete
language: en
version: 0.3
tags: [testing, quality]
created: 2026-04-12
updated: 2026-07-18
authors: [Christopher Pollin]
related: [data, pipeline, frontend, production-readiness]
---

# Testing Strategy

Testing approach for the Klawiter extraction pipeline and frontend dataset. Developed in Session 11 (2026-04-12), informed by data pipeline testing research, bibliographic data validation practices, and manual verification against raw data.

## Problem Statement

A bibliographic data rescue pipeline has a specific failure mode: **silent data loss and silent data corruption**. A pipeline that loses 100 entries, puts a city name in the publisher field, or marks the author as translator will still produce valid JSON. The testing strategy must be designed around this risk.

## Three Questions

1. **Is all the data there?** (Completeness) — fully automatable
2. **Is each record well-formed?** (Structural validity) — fully automatable
3. **Is each record correct?** (Semantic accuracy) — requires judgment, only sample-testable

## Test Taxonomy

### A: Census — "Is the data there?"

**File**: `test_census.py` (13 tests)

Verifies: record counts, page_id presence, no duplicates, stub entries, frontend JSON structure.

Catches: silent data loss, deduplication failures, frontend filtering bugs.

Cannot catch: an entry that exists but has completely wrong content.

**Verified**: 5 page_ids traced from raw SQL through all intermediate CSVs to output JSON. Census correctly identifies page 2979 as stub (BLOB content empty).

### B: Schema — "Is each field valid?"

**File**: `test_schema.py` (14 tests)

Validates every entry (not a sample): entry types, year ranges (1800–2030), language codes (ISO 639), page counts (positive int ≤ 10,000), no wiki markup (`[[`, `__TOC__`), no mojibake, no empty strings, JSON-LD `@type` consistency.

Catches: markup leaking into output (found 20 cases, fixed to 0), mojibake, invalid codes.

Cannot catch: structurally valid but semantically wrong values (e.g. `publisher: "Leipzig"`).

**Verified**: Manually checked 5 entries. Schema correctly flags `__TOC__` titles and `]]` markup. Confirmed limitation: `pageCount: 289` from `pp. 289-325` passed schema check (valid int) but was semantically wrong (start page, not count).

### C: Consistency — "Do fields make sense together?"

**File**: `test_consistency.py` (6 tests)

Tests cross-field relationships: German + translator bounded (111 FPs), film + pageCount bounded (10), publisher != location, year/timePeriod consistency, seeAlso referential integrity (bounded at 1,140), no self-references.

Catches: implausible field combinations, referential integrity violations.

Cannot catch: subtle semantic errors where combinations are plausible but wrong.

**Verified**: German+translator FPs traced to raw content — many are Sammelwerk entries with sub-translations (e.g. `Translated by Stefan Zweig` in a collected works entry where Zweig translated Verhaeren). The 111 count is a mix of true FPs and legitimate-but-misleading extractions. Broken seeAlso refs are caused by: format suffixes ("/ Spanish"), cross-language title mismatches, and person names stored as references.

### D: Distribution — "Has the data shape changed?"

**File**: `test_regression.py` (19 tests)

Compares quality-report.json against frozen baseline: entry counts (±0.5%), critical field coverage (≤0.5pp drop), tracked field coverage (≤1pp drop), entry type distribution (±2%), year range bounds, issue severity.

Catches: coverage regressions, classification drift.

Cannot catch: offsetting errors (50 publishers lost, 50 wrong added = same coverage).

**Verified**: All 7 field coverage values manually recounted from output JSON. Exact match with baseline.

### E: Extraction — "Do the functions work?"

**Files**: `test_patterns.py` (36), `test_encoding.py` (13), `test_wiki_parser.py` (41), `test_vocabulary.py` (19), `test_real_entries.py` (160), `test_llm_judge.py` (4) — 273 total

Unit tests for extraction functions + 20 hand-labeled real entries + LLM judge on 10 entries.

Catches: regressions in specific functions, encoding edge cases.

Cannot catch: problems in the 4,731 entries not in the sample (0.4% coverage).

**Verified**: 3 entries traced end-to-end through the pipeline steps. Pipeline logic correct for clean entries (page 3). pageCount bug confirmed (page 7140: `pp. 111-118` → extracted 111 as start page). LLM enrichment verified (page 4868: translator correctly filled by Gemini).

## Bugs Found and Fixed

| Bug | Found by | Severity | Fix | Impact |
|-----|----------|----------|-----|--------|
| 14 titles = `__TOC__` | test_schema | High | Strip leading `__TOC__` in `extract_title()` | 14 → 0 |
| 7 titles with `]]`/`[[`/`'''` | test_schema | Medium | Clean orphaned wiki brackets + bold markers in `remove_wiki_markup()` | 20 → 7 → 0 |
| pageCount from pp.-ranges | Verification | High | Negative lookahead `(?!\s*[-–—]\s*\d)` in Pattern 2 | 81.6% → 79.2% (136 false extractions removed) |
| page 2979 documented as "missing" | test_census | Low | Updated to "stub" in all docs | Documentation corrected |

## Current State

The suite spans the test files below; the live test and file counts are whatever `pytest tests/ --collect-only` reports, which is the source of truth this table does not freeze. The per-file counts here are indicative of relative weight, not a maintained total.

```
test_real_entries.py        160  — 20 hand-labeled entries (parametrized)
test_semantic.py             70  — Wiki-verified ground truth (10 entries x 7 fields)
test_patterns.py             45  — Regex extraction functions (incl. location publication-header fix, Session 18)
test_wiki_parser.py          41  — Wiki parser functions
test_normalize_unit.py       26  — Normalization rules unit tests (Session 15)
test_encoding.py             20  — Encoding functions (incl. mojibake transliteration repair, Session 18)
test_vocabulary.py           19  — Classification mappings
test_regression.py           19  — Distribution stability vs baseline
test_schema.py               14  — Structural validity (every entry)
test_census.py               13  — Completeness (all entries present)
test_apply_patches.py         8  — Editor corrections overlay (write-back, edit history, idempotency; Session 17)
test_consistency.py           6  — Cross-field plausibility
test_wikidata_locations.py    6  — Wikidata reconciliation quality
test_triage.py                6  — Triage artifact contract (build_triage.py flag shapes vs edit.js; Session 21)
test_normalization.py         5  — Normalization data-quality assertions (Session 15)
test_heuristic.py             5  — Semantic heuristics (all entries)
test_llm_judge.py             4  — LLM quality judgment
test_patch_contract.py        4  — Frontend/backend v2 patch contract (edit.js export vs apply_patches; Session 19)
test_parse_entries.py         3  — Blanked-stub title (2979 show-with-title; Session 18)
test_frontend_logic.py        1  — Runs evidence_triage.test.js (Node VM over edit.js: evidence spans, hint ordering; Session 21; skips without node)
```

Two normalization test files complement each other: `test_normalize_unit.py` unit-tests the mapping rules in `pipeline/data/` (location variants, publisher reject patterns, translator suffix stripping, pageCount outliers), while `test_normalization.py` asserts the resulting data-quality properties on the output JSON.

### Centralized Known-Issue Thresholds

Bounded-count tests (German+translator FPs, film+pageCount, broken seeAlso refs, long titles, encoding-artifact titles, etc.) read their frozen thresholds from the `known_issues` section of `.github/baseline-metrics.json` rather than hard-coding numbers in test files. The baseline also carries `entry_type_distribution` for the regression tests. Lower is better — when extraction improves, the value in the baseline is lowered, which tightens the bound.

### F: Semantic — "Is the value correct?"

**Files**: `test_semantic.py` (70 tests), `test_heuristic.py` (5 tests)

Two layers:

1. **Ground truth** (`test_semantic.py`): 10 entries verified against the live wiki at klawiter.stefanzweig.digital. Each entry checked for 7 fields (title, year, publisher, location, language, translator, pageCount). Current result: 53 passed, 17 failed. Ground truth file: `tests/wiki_ground_truth.json`.

2. **Heuristics** (`test_heuristic.py`): 5 pattern-based validators on all 4,751 entries. Each test bounds the violation count against the `known_issues` thresholds in `.github/baseline-metrics.json`:
   - 0 section-header titles (was 1,368 — fixed with page_title fallback)
   - 43 titles longer than 200 chars (encoding-guard cases, was 387)
   - 345 titles with encoding artifacts in page_title (Arabic/Cyrillic transliterations)
   - 0 publisher fields with wiki markup (was 20)
   - 0 publisher fields with metadata phrases (was 10)

   (The "pageCount looks like a year" bound is checked in the consistency/normalization tests, not here.)

Catches: wrong titles (section headers, full citations), wrong page counts (years, page numbers, start pages), wrong publishers (metadata text, wiki markup), cross-section contamination.

Cannot catch: semantic errors not covered by heuristic patterns or ground truth.

**Root cause**: Multi-edition wiki pages (one page containing multiple publications) cause systematic extraction failures. The pipeline treats each page as one flat entry, but Klawiter uses pages as containers.

## Field-Level Fidelity Findings

Record-level completeness is proven separately (no entry lost or invented, see [[data#record-census]]). The complementary question, whether the structured field values match the raw wiki source, was checked against the live frontend, where each entry displays its full source text directly beneath the extracted fields. The pipeline is correct on the common single-edition page; the field-level errors concentrate in four classes, two fixed and measured against committed artifacts, one systematic and open, one a faithful empty record.

### Error class 1: location from chapter titles ("Weimar")

The location extractor matched a city name anywhere in the entry text, including inside a chapter title. Records for non-German editions of "Sternstunden der Menschheit" carried location "Weimar" because the chapter "Die Marienbader Elegie. Goethe zwischen Karlsbad und Weimar" appears in every translation, and the error propagated into the Wikidata reconciliation. **Fixed**: location extraction is now constrained to the publication-line header (`'''[YEAR]: Publisher, Location'''`), accepting both colon and period separators, with headerless fallbacks that preserve a location rather than lose it. The change is in `pipeline/lib/patterns.py` (`extract_location`, `_clean_location`, `_location_from_header`) and locked by `tests/test_patterns.py` (`TestExtractLocation`). Measured by `pipeline/measure_location_fix.py` against the committed `data/output/location-fix-report.json`, deterministic over all namespace-0 records: no record's location is ever emptied, no changed or gained value is a publisher name, and the fix recovers hundreds of true non-Western locations (Sofia, Athens, Moskva, Tirana, Istanbul, Baku, Tbilisi, Tehran, Hanoi, Seoul) that the static city list never held. A residual handful of headerless "Weimar" cases and Latin-transliteration headers absent from the city list remain as later milestones. The fix is landed in code but not yet in the published frontend, which regenerates only on the next full pipeline run, held until the mojibake repair lands so the header location carries no surviving encoding artifacts.

### Error class 2: multi-edition flattening (open)

A wiki page can contain several publications, and the flat extraction draws each field from a different part of the page. Entry 11 ("Collected Works:") is the worst observed case: title is a section header, publisher a fragment of the English translation's line, location a stack of ten cities, pageCount the English edition's, translator the author. This is the known multi-edition limitation (see [[pipeline#known-limitations--multi-edition-pages]]). It is the dominant field-level error class and stays open; the scope decision is Gate 1 in [[production-readiness#gates]], because per-hand correction, flag-and-defer, and a separate decomposition project are genuinely different scopes.

### Error class 3: surviving title mojibake

The earlier repair removed gross field-level mojibake, but transliterated titles still carried double-encoded artifacts (entry 804: "Mardkutâyan asteghayin zhamerÄ"), because `fix_mojibake` only triggered on the C2/C3 lead bytes and never reached the Latin Extended diacritics of romanized Arabic, Greek, Vietnamese and Slavic titles. **Fixed**: `fix_mojibake` (`pipeline/lib/encoding.py`) now repairs each mojibake run independently and self-validates, so a clean accented letter before a Latin-1 guillemet is left untouched. Locked by `tests/test_encoding.py` (`TestMojibakeTransliteration`), including a clean-German guard and an idempotency check. Measured by `pipeline/measure_mojibake_repair.py` against the committed `data/output/mojibake-repair-report.json`, deterministic over all namespace-0 records: every detected run is repaired, none self-rejected, the repair is idempotent, and no repairable residual remains. Landed in code, not yet in the published frontend, and the title is still not an editable field (a separate editing milestone).

### Error class 4: the blanked stub (2979)

Entry 2979 surfaces as an untitled record with no fields because its source page was blanked at the source (rev_len 0), so nothing is extractable and it is unrecoverable from the dump. The census isolates it as the single anomaly (see [[data#record-census]]). It is a faithful representation of an empty source page, not an extraction error, and stays source-faithfully empty.

### Method and limits

This was a targeted pass, not exhaustive: it confirms the error classes and their mechanisms against named example entries and quantifies the Weimar class fully against a committed measurement artifact diffed across all namespace-0 records. It does not yet measure a per-field error rate across a stratified sample, which is the remaining calibration input the triage signal needs (tracked as the open M3.8 remainder in [[production-readiness#eil-editing-increments]]).

### Implications for the editing tool

The four currently editable fields (publisher, location, translator, pageCount) do not cover the title-repair classes (2 and 3), which require the title to become editable, and the multi-edition class requires the Gate 1 scope decision before the tool invests in it. The systematic classes also feed the triage signal, because a record whose location is "Weimar" or whose title is a section header is a high-attention case the surface ranks automatically (see [[frontend#the-uncertainty-surface]]).

## What We Can and Cannot Guarantee

**Automated guarantees:**
- All 5,179 entries present, no duplicates
- Every entry has valid type, year range, language code, page count range
- No mojibake in key fields
- Coverage metrics stable vs baseline
- Extraction functions work on known inputs
- Cross-field combinations bounded (German+translator, film+pageCount, seeAlso integrity)
- Heuristic semantic checks bounded (section-header titles, year-as-pageCount, metadata-as-publisher)

**Sample-based partial verification:**
- 10 entries wiki-verified with ground truth (53/70 fields correct = 76%)
- 20 entries extraction-tested (0.4% of corpus)
- 10 entries judged by LLM (0.2%)
- 5 entries manually verified end-to-end against raw data

**Remaining gaps:**
- Semantic accuracy: 76% on wiki-verified sample (17/70 fields wrong, mostly multi-edition pages)
- 345 titles with encoding artifacts in page_title (Arabic/Cyrillic transliterations)
- 43 titles >200 chars (encoding-guard cases — long but correct)
- 11 pageCount values that may be years
- 427 multi-edition pages (6.8%) where publisher/pageCount/year may come from wrong edition
- 111 German entries with translator (complex: sub-translations in collected works)
- seeAlso broken references bounded at 727 (was 1,140; reduced by title fix resolving more redirects)
- Pipeline reached diminishing returns on regex extraction (see [[pipeline#known-limitations--multi-edition-pages]])

## Key Principles

1. **Test the data, not the code.** The deliverable is `klawiter.json`. Code tests are means; data tests are ends.
2. **Validate every record, not a sample.** Schema validation is exhaustive; spot-checks are supplementary.
3. **Census before quality.** Detecting 50 missing entries is more important than one wrong publisher.
4. **Cross-field before single-field.** A German entry with translator is more suspicious than a non-German entry without one.
5. **Explicit over silent.** A test that passes by skipping its assertion is worse than no test.

## References

- [OpenCitations: Validating bibliographic data](https://arxiv.org/html/2504.12195) — 4-level validation (wellformedness, ID syntax, existence, semantics)
- [Golden Tests for Data-Driven APIs](https://medium.com/@nidhipandya1606/golden-tests-how-a-small-set-of-real-inputs-helped-me-keep-a-data-driven-api-correct-through-0926b6384e9f) — bug categories caught by golden files
- [Integration Tests for Python Data Pipelines](https://www.startdataengineering.com/post/python-datapipeline-integration-test/)
- [LOD Quality Assessment for GLAM](https://www.semantic-web-journal.net/system/files/swj4008.pdf) — completeness as core quality dimension
- [Pandera](https://pandera.readthedocs.io/) — DataFrame schema contracts
- [Hypothesis](https://github.com/HypothesisWorks/hypothesis) — property-based testing / fuzzing
- [Risk-Based Data Quality Testing (Vinted)](https://vinted.engineering/2026/03/11/risk-based-testing/) — threshold calibration
