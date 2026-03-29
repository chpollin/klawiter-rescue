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

## Phase 4: Frontend Redesign (M6)

Redesign the frontend to match Stefan Zweig Digital's visual language. See `knowledge/design.md` for full specification, `knowledge/user-stories.md` for user stories (S1–S20).

### Phase 4a: Foundation — CSS & HTML structure ✅

- [x] Custom CSS with SZD palette (burgundy/gold/cream), serif/sans-serif typography
- [x] HTML with 4 views, burgundy header, footer with credits, meta tags

### Phase 4b: Startseite — Category Portal (S1–S3) ✅

- [x] Category tiles grouped by Works / Reception & Impact / Editions
- [x] Intro text, prominent search field, summary stats line

### Phase 4c: Search & Results (S4–S8) ✅

- [x] Expandable result cards (badge, title, publisher, snippet)
- [x] SZD-style facets (serif, burgundy active state, gold headings)

### Phase 4d: Detail View (S9–S13) ✅

- [x] Two-column metadata table, conditional sections (reprints, translations, contents, see-also)
- [x] Inline expansion in result cards (no separate detail page for browsing)

### Phase 4e: Statistics (S18–S20) ✅

- [x] 4 charts (timeline, languages, locations, types) with click-to-filter
- [x] Timeline from 1800, gold highlight for Zweig's lifetime decades

### Phase 4f: Export & Actions (S14–S17) ✅

- [x] BibTeX + RIS export (correct author logic for secondary literature)
- [x] JSON-LD per entry + full dataset download on stats page
- [x] Permalink copy to clipboard

### Phase 4g: QA, Iteration & Refactoring ✅

- [x] Home search: Enter only, no premature redirect
- [x] Filter chips hidden outside results view
- [x] Stats page: clears filters, always shows full dataset
- [x] Expandable cards with slide animation
- [x] Console data logging (counts, coverage, quality issues)
- [x] JS modules: `constants.js`, `utils.js`, `export.js` extracted
- [x] CSS variables audit (no hardcoded colors)
- [x] Meta tags (og:title, og:description)
- [x] Semantic HTML (`<nav>` for facets)

### Phase 4h: Remaining Data Quality (Pipeline)

- [x] Fix wiki markup in titles (''', [[, ]]) — `remove_wiki_markup()` in step 03
- [x] Investigate "München" encoding issue — verified correct UTF-8 throughout pipeline, terminal display artifact only
- [x] Re-run pipeline after fixes, regenerate `klawiter.json`

### Phase 4i: Automated Validation ✅

Systematic validation of all 4,751 ns0 non-redirect entries + stratified sample of 84 entries across all 20 types.

**Issues found and fixed:**
- Translator fields leaking across newlines into subsequent sections (34 entries → 0). Root cause: `\s` in regex character class matched `\n`. Fixed by restricting to `[ \t]`.
- Trailing `'''` wiki markup in translator names (5 entries → 0). Fixed by stripping `'''...` suffixes in `extract_translator()`.
- München encoding: verified correct UTF-8 throughout pipeline (terminal display artifact, not a data issue).

**Final validation results:**
| Metric | Value |
|--------|-------|
| Missing title | 1 (page_id 2979, text not in BLOBs) |
| Wiki markup in title | 1 (edge case: `"See:'''` is part of the title) |
| Year as originalTitle | 0 (was 272, fixed) |
| Translator with markup | 0 (was 34, fixed) |

**Remaining**: Manual browse-through of 50+ entries in the frontend for visual spot-checking (deferred to user).

### Phase 4j: Manual Validation (deferred)

- [ ] Browse 50+ entries in frontend, stratified by type, language, time period
- [ ] Compare displayed fields against raw wiki content
- [ ] Document accuracy observations

## Phase 5: Ontology & Schema.org Mapping (M4) ✅

Implemented Schema.org + Dublin Core + klawiter: vocabulary blend.

### Completed
- [x] Map all 16 entry types to Schema.org types (Book, Article, Play, Movie, Event, etc.)
- [x] Map all fields to Schema.org/DC properties (name, datePublished, publisher, inLanguage, etc.)
- [x] Rewrite `@context` in `pipeline/lib/vocabulary.py` with Schema.org + DC + klawiter: blend
- [x] Update `05_to_jsonld.py` to produce new @context with dual `@type` arrays
- [x] Create `docs/vocab/index.html` for namespace resolution
- [ ] Validate output with JSON-LD Playground (deferred)

## Phase 6: Semantic Enrichment (M5)

Link entities to authority data: Wikidata, GND, VIAF.

### Tasks
- [ ] Reconcile Stefan Zweig works against Wikidata (P50 = Q78491)
- [ ] Reconcile translators against GND/VIAF
- [ ] Reconcile locations against Wikidata/GeoNames
- [ ] Add `schema:sameAs` URIs to JSON-LD output
- [ ] Create pipeline step for enrichment

## Phase 7: Frontend Redesign (M6) ✅

Redesigned to match Stefan Zweig Digital visual language. See `knowledge/design.md`.

### Completed
- [x] Custom CSS with SZD palette (burgundy/gold/cream), serif/sans-serif typography
- [x] Replace Tailwind CDN with custom CSS (1,200+ lines)
- [x] Citation export: BibTeX, RIS, JSON-LD, permalink
- [x] Stable URIs (`#entry={page_id}`) with redirect resolution
- [x] 5 content pages: About, Methodology, Help, Data Access, Imprint
- [x] Navigation with dropdown menu and footer links

### Remaining
- [ ] Linked authority data display (depends on M5)
- [ ] Performance optimization (~9 MB JSON → lazy loading?)
- [ ] WCAG 2.1 AA accessibility audit

## Phase 8: Deployment & Publication (M7) — partial ✅

### Completed
- [x] GitHub Pages live at `https://chpollin.github.io/klawiter-rescue/`
- [x] Fix namespace URI across all files (was `klawiter-rescue.github.io`, now `chpollin.github.io/klawiter-rescue`)
- [x] Fix GitHub repository link in footer (was `chrstncrrnd`, now `chpollin`)
- [x] Add LICENSE file (MIT for code, CC BY 4.0 for data)
- [x] Add CITATION.cff for academic citation
- [x] Update README.md with live URL and license section
- [x] Regenerate JSON-LD and frontend JSON with corrected namespace

### Remaining
- [ ] Test live deployment (all routes, search, data loading)
- [ ] Consider Zenodo deposit for DOI
- [ ] Coordinate link from Stefan Zweig Digital
- [ ] Announce / publish

## Phase 9: Interactive Exploration Interface ✅

Replaced the generic Chart.js dashboard with D3.js v7 exploration tool.

### Completed
- [x] Design concept and research questions (`knowledge/exploration.md`)
- [x] Shared controller (`explore.js`) with mode switching, state management, detail panel
- [x] Timeline mode (`explore-timeline.js`): stacked area chart (year × language) with brushing
- [x] Overview mode (`explore-overview.js`): 4 linked small multiples with cross-filtering
- [x] Connections mode (`explore-network.js`): force-directed graph of seeAlso links
- [x] Migration from Chart.js to D3.js v7 (CDN swap, charts.js deleted)
- [x] UX fixes: overflow, state reset, Unknown filter, legend layout, brush hint
- [x] Frontend refactoring: BibTeX dedup, titleMap, countByField, wiki section extractor

### Remaining
- [ ] True streamgraph offset (`stackOffsetWiggle`) as option
- [ ] Mobile-optimized network view (degrade to list)
- [ ] Linked authority data in network graph (depends on M5)
