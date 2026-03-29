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

## Phase 3: Unit Tests ✅

Built comprehensive test suite with real-data tests and LLM-as-a-Judge validation.

**Results**: 245 tests passed, 6 skipped, 0 failed (10.7s including Gemini API call).

| Test file | Tests | Focus |
|-----------|-------|-------|
| `test_encoding.py` | 13 | Mojibake detection/repair, HTML entities |
| `test_patterns.py` | 48 | All 8 extraction functions (year, publisher, location, page_count, translator, language) |
| `test_wiki_parser.py` | 80 | 12 parser functions (redirect, categories, title, reprints, translations, etc.) |
| `test_real_entries.py` | 100 | Parametrized over 20 hand-labeled entries × 5 field extractors |
| `test_llm_judge.py` | 4 | Gemini evaluates extraction quality on 10 diverse entries |

**LLM-Judge findings** (known limitations baseline):
- 10 "wrong" verdicts: title from `'''[year]: Publisher'''` headers (6×), mojibake-truncated fields (2×), page-range-as-count (2×)
- 13 "missed" verdicts: publisher/location from headers not extracted, `N/(M)p.` format, languages without `[[Category:]]`

### Tasks
- [x] Create `tests/conftest.py` with fixtures (sample entries + Gemini client + real-data loader)
- [x] Create `tests/test_patterns.py` — unit tests for `lib/patterns.py`
- [x] Create `tests/test_wiki_parser.py` — unit tests for `lib/wiki_parser.py`
- [x] Create `tests/test_encoding.py` — unit tests for `lib/encoding.py`
- [x] Create `tests/test_real_entries.py` — parametrized real-data tests
- [x] Create `tests/test_llm_judge.py` — LLM-as-a-Judge validation
- [x] Create `pytest.ini` — markers (`llm`), PYTHONPATH config
- [x] Run all tests, ensure they pass

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
