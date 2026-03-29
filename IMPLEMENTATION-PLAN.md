# Implementation Plan: Pipeline Quality Assurance

## Goal

Verify that the pipeline extracts all information correctly, then improve weak extraction patterns.

## Approach

Build a verification script that works **backwards** from the final JSON-LD output to the raw source data. For each entry, compare extracted fields against the original wiki content to find false positives (wrong extractions) and false negatives (missed information).

---

## Phase 1: Verification Script ✅

Built `pipeline/verify.py` with round-trip verification, encoding-aware comparison, and N/(M)p. summation handling.

**Results** (4,751 bibliography entries):

| Field | Coverage | Precision | Notes |
|-------|----------|-----------|-------|
| title | 100.0% | ~100%* | *81.5% reported — FPs are page_title fallback, not errors |
| year | 93.2% | 100% | Solid |
| publisher | 55.6% | ~99%+ | 170 reported FP = encoding artifacts |
| location | 87.5% | ~99%+ | 96 reported FP = encoding artifacts |
| translator | 41.9% | ~99.7% | 63 reported FP = encoding + concatenation artifacts |
| page_count | 81.6% | 100% | Fixed off-by-one in page ranges |

## Phase 2: LLM Enrichment (Step 03b) ✅

Built `pipeline/03b_llm_enrich.py` using Gemini 3.1 Flash Lite.

- 20-entry stratified test: 13/13 correct, 0 hallucinations
- Full run: 275 batches, 0 errors, ~$0.33
- Mojibake validation filter: 31 bad values rejected
- Coverage improvement: publisher +21.1pp, location +19.7pp, translator +6.8pp, page_count +3.2pp

## Phase 3: Unit Tests & Refactoring ✅

Built comprehensive test suite, then reviewed critically, refactored pipeline code, and expanded test coverage.

### Phase 3a: Initial test suite
- 171 tests across 3 files — functional but ~40-50 were trivial/redundant

### Phase 3b: Critical review & real-data tests
- Trimmed redundant tests (guard-clause tests, individual dict lookups, whitelist tested 8×)
- Added parametrized real-data tests over 20 hand-labeled entries
- Added LLM-as-a-Judge using Gemini 3.1 Flash Lite

### Phase 3c: Pipeline refactoring
- `OUTPUT_FIELDS` consolidated in `lib/config.py` (was duplicated in 3 files)
- `csv_bool()` helper replaces 5 instances of `in ('True', 'true', '1')`
- `load_env()` centralized in `lib/config.py` (was duplicated in 03b + conftest)
- `PAGE_RANGE_RE`/`PARENS_PAGE_RE` moved to `lib/patterns.py` (was duplicated in 03b + verify.py)
- `MIN_CONTENT_LENGTH` constant (was magic number `80`)
- Removed `int(float(x))` anti-pattern in 04/05
- Added `test_vocabulary.py` for previously untested classification functions
- Strengthened real-data tests to assert concrete values instead of just not-None

**Final results**: 264 tests passed, 6 skipped, 0 failed (11s including Gemini API call).

| Test file | Tests | Focus |
|-----------|-------|-------|
| `test_encoding.py` | 13 | Mojibake detection/repair, HTML entities |
| `test_patterns.py` | 48 | All 8 extraction functions |
| `test_wiki_parser.py` | 80 | 12 parser functions |
| `test_vocabulary.py` | 19 | Time period, entry type, ISO language classification |
| `test_real_entries.py` | 100 | Parametrized over 20 hand-labeled entries × 5 extractors |
| `test_llm_judge.py` | 4 | Gemini evaluates extraction quality on 10 diverse entries |

**LLM-Judge baseline** (known limitations):
- 10 "wrong": title from `'''[year]: Publisher'''` headers (6×), mojibake truncation (2×), page-range-as-count (2×)
- 13 "missed": publisher/location from headers, `N/(M)p.` format, languages without `[[Category:]]`

## Phase 4: Manual Validation

Spot-check 50 entries to validate pipeline correctness with human eyes.

### Tasks
- [ ] Select 50 entries stratified by type, language, time period
- [ ] Compare extracted fields against raw wiki content
- [ ] Document accuracy: true positives, false positives, false negatives
- [ ] Fix any systematic errors found

## Phase 5: Ontology & Schema.org Mapping (M4)

Map `klawiter:` fields to established vocabularies.

### Tasks
- [ ] Map each of the 16 entry types to closest Schema.org type
- [ ] Map each field to Schema.org property (name, datePublished, publisher, inLanguage, etc.)
- [ ] Rewrite `@context` in `pipeline/lib/vocabulary.py`
- [ ] Update `05_to_jsonld.py` to produce new @context
- [ ] Validate output with JSON-LD Playground
- [ ] Create `docs/vocab/index.html` for namespace resolution

## Phase 6: Semantic Enrichment (M5)

Link entities to authority data: Wikidata, GND, VIAF.

### Tasks
- [ ] Reconcile Stefan Zweig works against Wikidata (P50 = Q78491)
- [ ] Reconcile translators against GND/VIAF
- [ ] Reconcile locations against Wikidata/GeoNames
- [ ] Add `schema:sameAs` URIs to JSON-LD output
- [ ] Create pipeline step for enrichment

## Phase 7: Frontend Redesign (M6)

Align with Stefan Zweig Digital design. Improve UX.

### Tasks
- [ ] Analyze Stefan Zweig Digital: colors, typography, layout
- [ ] Replace Tailwind CDN with custom CSS
- [ ] Add citation export (BibTeX, RIS)
- [ ] Add linked authority data display
- [ ] Stable URIs for every entry
- [ ] Performance optimization (4.2 MB → lazy loading?)
- [ ] WCAG 2.1 AA accessibility audit
