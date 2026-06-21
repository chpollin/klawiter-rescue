---
title: Testing
aliases: [test strategy, quality assurance]
tags: [testing, quality]
created: 2026-04-12
updated: 2026-06-12
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

## Current State (468 tests across 18 files, 2026-06-21)

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
test_normalization.py         5  — Normalization data-quality assertions (Session 15)
test_heuristic.py             5  — Semantic heuristics (all entries)
test_llm_judge.py             4  — LLM quality judgment
test_patch_contract.py        4  — Frontend/backend v2 patch contract (edit.js export vs apply_patches; Session 19)
test_parse_entries.py         3  — Blanked-stub title (2979 show-with-title; Session 18)
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

See [[references#data-pipeline-testing]] for full citations.
