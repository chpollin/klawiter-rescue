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

### Phase 4a: Foundation — CSS & HTML structure

Remove Tailwind, build custom CSS, restructure HTML for 4 views.

**Deliverable**: Styled but static page — correct colors, typography, layout. No JS changes yet.

- [ ] Write `docs/css/styles.css`: CSS custom properties (SZD palette), base typography (serif/sans-serif system), layout grid (header, sidebar, content, footer), all component styles (cards, badges, facets, chips, metadata table, action bar)
- [ ] Rewrite `docs/index.html`: Remove Tailwind CDN. 4 view containers (home, results, detail, stats). Burgundy header with nav (ÜBERSICHT · SUCHE · STATISTIKEN). Footer with credits. Mobile filter toggle preserved
- [ ] Verify: Page loads without Tailwind, correct colors and fonts visible

### Phase 4b: Startseite — Category Portal (S1, S2, S3)

**Deliverable**: Landing page with intro text, search field, category tiles grouped by Werke/Rezeption/Editionen.

- [ ] Create `docs/js/home.js`: Render category tiles from data (counts per entryType, namespace 0 only). Group tiles into 3 sections (Werke, Rezeption & Wirkung, Editionen). Render intro text. Render Kurzstatistik line. Prominent search field
- [ ] Update `docs/js/app.js`: Add `home` view to routing (`#` → home). Filter `pageNamespace !== 0` entries on load. Route category tile clicks to `#type=...`
- [ ] Verify: Landing page shows 15 category tiles with correct counts, search field works, tile click navigates to results

### Phase 4c: Stöbern — Search & Results (S4–S8)

**Deliverable**: Faceted search with redesigned result cards showing publisher/pages.

- [ ] Update `docs/js/app.js`: Result card template with 4 lines (badge+meta, title, publisher+pages, snippet). Sort options unchanged
- [ ] Update `docs/js/facets.js`: SZD-style facet items (serif, burgundy active state, gold headings). Keep same 4 facets (type, language, period, location)
- [ ] Verify: Search returns correct results, facets filter correctly, cards show all metadata, combined filters work

### Phase 4d: Detailansicht — SZD-style metadata (S9–S13)

**Deliverable**: Detail view with two-column metadata table, conditional sections, full bibliographic entry.

- [ ] Rewrite `docs/js/detail.js`: Two-column metadata table (burgundy labels, sans-serif values, horizontal rules). Conditional sections: Vollständiger Eintrag (monospace, cream bg), Nachdrucke, Übersetzungen, Inhalt, Siehe auch (as clickable links). Hide empty fields entirely. Entry type as gold uppercase heading above title
- [ ] Verify: Detail view shows all available fields. Empty fields are hidden. seeAlso links navigate to other entries. contentItems display as numbered list. Reprints/translations as bullet lists

### Phase 4e: Statistiken — Interactive Charts (S18–S20)

**Deliverable**: Statistics page with 4 charts, click-to-filter.

- [ ] Rewrite `docs/js/charts.js`: SZD color scheme (burgundy bars, gold for Zweig lifetime, earth tones for doughnut). Add location chart (top 15 cities, horizontal bars). All chart clicks → navigate to `#type=...`, `#language=...`, etc.
- [ ] Update `docs/js/app.js`: Add `stats` view to routing (`#stats`). Stat cards (burgundy numbers, gold labels)
- [ ] Verify: All 4 charts render correctly, clicking a bar/segment navigates to filtered results

### Phase 4f: Export & Actions (S14–S17)

**Deliverable**: Citation export, JSON-LD download, permalink copy in detail view action bar.

- [ ] Add BibTeX export: Generate `.bib` file from entry fields (author=Zweig, title, year, publisher, address=location, translator as note)
- [ ] Add RIS export: Generate `.ris` file (TY, TI, AU, PY, PB, CY, LA)
- [ ] JSON-LD download: Keep existing, style as action bar button
- [ ] Permalink: Copy `#entry={pageId}` URL to clipboard, show brief confirmation
- [ ] Full dataset export: Button on stats page to download complete JSON-LD
- [ ] Verify: All 3 export formats download correctly, permalink copies to clipboard

### Phase 4g: Frontend QA & Iteration

Fix issues discovered during first review.

- [x] Fix home search: navigate only on Enter, not on every keystroke
- [x] Hide filter chips in detail/stats/home views (only show in results)
- [x] Stats page: clear filters when navigating to stats, always show full dataset
- [x] Timeline: extend range to 1800 (was 1880, missed 61 pre-Zweig entries)
- [x] Expandable cards: detail content opens inline below card, no separate detail view needed for browsing
- [x] Improve `detail-bibentry`: sans-serif font, white background, better line-height for readability
- [x] Console logging: data summary printed on load (counts, coverage, quality issues)
- [ ] Full dataset export button on stats page

### Phase 4h: Frontend Refactoring

Clean up code quality after rapid prototyping. Goal: maintainable, well-structured code.

**CSS (`docs/css/styles.css`)**
- [ ] Group CSS by component (currently roughly grouped, could be cleaner)
- [ ] Remove unused styles (e.g., standalone `.detail-back` if expandable cards replace most detail navigation)
- [ ] Audit CSS custom properties: ensure all colors come from variables, no hardcoded hex
- [ ] Check all font-size values use a consistent scale (currently ad-hoc rem values)
- [ ] Test: verify no visual regressions after cleanup

**HTML (`docs/index.html`)**
- [ ] Remove `view-detail` container if fully replaced by expandable cards (keep `#entry=` route → auto-expand card in results)
- [ ] Add proper `<meta>` tags: description, og:title, og:description for link previews
- [ ] Add `.nojekyll` verification (already exists but confirm)
- [ ] Semantic HTML audit: use `<article>` for cards, `<nav>` for facets, `<section>` for views

**JavaScript Architecture**
- [ ] Extract shared constants (ENTRY_TYPE_LABELS, PERIOD_LABELS) into `js/constants.js`
- [ ] Extract helpers (esc, hl) into `js/utils.js`
- [ ] Move BibTeX/RIS/JSON-LD export logic from `detail.js` into `js/export.js`
- [ ] Review `app.js` — it handles routing, state, rendering, events, and logging. Split into: routing + state management in `app.js`, card rendering in a separate concern
- [ ] Add JSDoc comments to all public methods
- [ ] Test: verify all 4 views, search, filters, exports, expandable cards still work

**Data Quality (Pipeline)**
- [ ] Fix 14 entries with wiki markup in titles (''', [[, ]]) — pipeline step 03
- [ ] Investigate "München" encoding issue in location data — pipeline step 02
- [ ] Re-run pipeline after fixes, regenerate `klawiter.json`
- [ ] Update console logging assertions with corrected data

### Phase 4i: Manual Validation (deferred from M3.8)

Validate pipeline correctness by browsing entries in the redesigned frontend.

- [ ] Browse 50+ entries stratified by type, language, time period
- [ ] Compare displayed fields against raw wiki content
- [ ] Document accuracy, fix systematic errors

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
