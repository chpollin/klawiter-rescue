---
title: Testing
aliases: [test strategy, quality assurance]
tags: [testing, quality]
created: 2026-04-12
updated: 2026-04-12
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

**File**: `test_census.py` (14 tests)

Verifies: record counts, page_id presence, no duplicates, stub entries, frontend JSON structure.

Catches: silent data loss, deduplication failures, frontend filtering bugs.

Cannot catch: an entry that exists but has completely wrong content.

**Verified**: 5 page_ids traced from raw SQL through all intermediate CSVs to output JSON. Census correctly identifies page 2979 as stub (BLOB content empty).

### B: Schema — "Is each field valid?"

**File**: `test_schema.py` (14 tests)

Validates every entry (not a sample): entry types, year ranges (1800–2030), language codes (ISO 639), page counts (positive int ≤ 10,000), no wiki markup (`[[`, `__TOC__`), no mojibake, no empty strings, JSON-LD `@type` consistency.

Catches: markup leaking into output (found 20 cases, fixed to 6), mojibake, invalid codes.

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

**Files**: `test_patterns.py` (35), `test_encoding.py` (13), `test_wiki_parser.py` (41), `test_vocabulary.py` (19), `test_real_entries.py` (160), `test_llm_judge.py` (4) — 272 total

Unit tests for extraction functions + 20 hand-labeled real entries + LLM judge on 10 entries.

Catches: regressions in specific functions, encoding edge cases.

Cannot catch: problems in the 4,731 entries not in the sample (0.4% coverage).

**Verified**: 3 entries traced end-to-end through all 5 pipeline steps. Pipeline logic correct for clean entries (page 3). pageCount bug confirmed (page 7140: `pp. 111-118` → extracted 111 as start page). LLM enrichment verified (page 4868: translator correctly filled by Gemini).

## Bugs Found and Fixed

| Bug | Found by | Severity | Fix | Impact |
|-----|----------|----------|-----|--------|
| 14 titles = `__TOC__` | test_schema | High | Strip leading `__TOC__` in `extract_title()` | 14 → 0 |
| 6 titles with `]]` | test_schema | Medium | Clean orphaned `]]` in quoted title extraction | 20 → 6 remaining |
| pageCount from pp.-ranges | Verification | High | Negative lookahead `(?!\s*[-–—]\s*\d)` in Pattern 2 | 81.6% → 79.2% (136 false extractions removed) |
| page 2979 documented as "missing" | test_census | Low | Updated to "stub" in all docs | Documentation corrected |

## Current State (326 tests, 2026-04-12)

```
test_census.py        14  — Completeness (all entries present)
test_schema.py        14  — Structural validity (every entry)
test_consistency.py    6  — Cross-field plausibility
test_regression.py    19  — Distribution stability vs baseline
test_encoding.py      13  — Encoding functions
test_patterns.py      36  — Regex extraction functions
test_wiki_parser.py   41  — Wiki parser functions
test_vocabulary.py    19  — Classification mappings
test_real_entries.py  160  — 20 hand-labeled entries
test_llm_judge.py      4  — LLM quality judgment
```

## What We Can and Cannot Guarantee

**Automated guarantees:**
- All 5,179 entries present, no duplicates
- Every entry has valid type, year range, language code, page count range
- No mojibake in key fields
- Coverage metrics stable vs baseline
- Extraction functions work on known inputs
- Cross-field combinations bounded (German+translator, film+pageCount, seeAlso integrity)

**Sample-based partial verification:**
- 20 entries correct (0.4% of corpus)
- 10 entries judged by LLM (0.2%)
- 5 entries manually verified end-to-end against raw data

**Remaining gaps:**
- Semantic accuracy on 99.6% of entries untested
- 6 titles still contain `]]` markup (source-text issues)
- 111 German entries with translator (complex: sub-translations in collected works)
- seeAlso broken references bounded at 1,140 (format/matching problem — language suffixes like "/ Spanish")
- 976 titles changed on pipeline re-run due to bold-match fallback logic in `03_parse_entries.py` (pre-existing, not caused by Session 11 fixes)

## Key Principles

1. **Test the data, not the code.** The deliverable is `klawiter.json`. Code tests are means; data tests are ends.
2. **Validate every record, not a sample.** Schema validation is exhaustive; spot-checks are supplementary.
3. **Census before quality.** Detecting 50 missing entries is more important than one wrong publisher.
4. **Cross-field before single-field.** A German entry with translator is more suspicious than a non-German entry without one.
5. **Explicit over silent.** A test that passes by skipping its assertion is worse than no test.

## References

See [[references#data-pipeline-testing]] for full citations.
