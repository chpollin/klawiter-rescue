# Implementation Plan: Pipeline Quality Assurance

## Goal

Verify that the pipeline extracts all information correctly, then improve weak extraction patterns.

## Approach

Build a verification script that works **backwards** from the final JSON-LD output to the raw source data. For each entry, compare extracted fields against the original wiki content to find false positives (wrong extractions) and false negatives (missed information).

---

## Phase 1: Verification Script

Build `pipeline/verify.py` that:
1. Loads `data/output/klawiter.jsonld` (final output)
2. Loads the raw BLOB content for each entry (via `sourceBlobId` + `sourceTextId`)
3. For each extracted field, checks if the value actually appears in the raw content
4. Reports: correct extractions, false positives, false negatives, coverage gaps

### Tasks
- [ ] Create `pipeline/verify.py` with round-trip verification logic
- [ ] Verify title extraction: does `klawiter:title` appear in raw content?
- [ ] Verify year extraction: does `klawiter:year` appear in raw content?
- [ ] Verify publisher: does extracted publisher string appear in raw content?
- [ ] Verify location: does extracted location appear in raw content?
- [ ] Verify translator: does extracted translator appear in raw content?
- [ ] Detect false negatives: scan raw content for publisher/location/year patterns NOT captured
- [ ] Generate verification report as JSON (`data/output/verification-report.json`)
- [ ] Run and analyze results

## Phase 2: Unit Tests

Build test suite for extraction functions using real examples from the dataset.

### Tasks
- [ ] Create `tests/conftest.py` with fixtures (sample raw entries + expected extractions)
- [ ] Create `tests/test_patterns.py` — unit tests for `lib/patterns.py`:
  - `extract_year`, `extract_publisher`, `extract_location`
  - `extract_page_count`, `extract_translator`, `extract_language_from_category`
- [ ] Create `tests/test_wiki_parser.py` — unit tests for `lib/wiki_parser.py`:
  - `parse_redirect`, `extract_categories`, `extract_title`
  - `extract_see_references`, `extract_reprints`, `extract_structured_data`
- [ ] Create `tests/test_encoding.py` — unit tests for `lib/encoding.py`:
  - `has_mojibake`, `fix_encoding`
- [ ] Run all tests, ensure they pass

## Phase 3: Improve Extraction Patterns

Based on verification results from Phase 1, improve weak patterns.

### Tasks
- [ ] Analyze verification report: which fields have highest false negative rate?
- [ ] Improve publisher patterns (currently 34.5% coverage)
- [ ] Improve translator patterns (currently 35.1% coverage)
- [ ] Re-run pipeline after pattern improvements
- [ ] Re-run verification to measure improvement
- [ ] Update tests for new patterns
