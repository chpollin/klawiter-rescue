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

## Phase 3: Unit Tests

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
