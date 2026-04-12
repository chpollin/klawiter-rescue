---
title: Journal
aliases: [work diary, sessions]
tags: [journal]
created: 2026-03-29
updated: 2026-04-12
---

# Journal

Work diary for the Klawiter Bibliography project. Each session documents what we did, what we learned, what ideas came up, and what's still open.

---

## 2026-04-12 — Session 12: JSON-LD Validation, Playground, Project Audit

### What we did

- **Data Integrity Principle** documented in CLAUDE.md: pipeline extracts only, never invents data. LLM audit confirmed 0 hallucinated values across 5 anti-hallucination layers.
- **JSON-LD @context fixed** (5 issues): removed incorrect `author @type:@id` coercion, typed `datePublished` as `xsd:gYear`, added `@version: 1.1`, mapped dataset-level properties as short aliases, added `@container:@list` for entries array.
- **JSON-LD validated with PyLD**: expansion, compaction, and N-Quads generation all pass. 53 triples per entry, author objects expand correctly.
- **JSON-LD Playground frontend** (`#jsonld`): interactive compact/expanded/triples view with entry search, random selection, syntax highlighting, vocabulary reference table.
- **Full project audit**: found 3 bugs (2 critical), 8 documentation inconsistencies, 4 refactoring opportunities.
- **Bugs fixed**: `06_validate.py`/`verify.py` read wrong key (`klawiter:entries` instead of `entries` — validation silently processed 0 entries); year validation had 4 different caps (unified to `config.MIN/MAX_VALID_YEAR`); `ABOUT_ZWEIG_TYPES` inconsistent across 3 files (aligned to pipeline as source of truth).
- **Refactoring**: `Export.jsonld()` now uses full @context via `JsonldPlayground._toCompactJsonld()`; removed duplicate `escapeHtml`; `PERIOD_RANGES` imported from `vocabulary.py` instead of duplicated; Windows encoding fix deduplicated.
- **Documentation corrected**: test count 311→326 in 5 files, architecture.md (Tailwind→CSS, Chart.js→D3, 4MB→9MB), ontology.md @context block, data.md quality report (32→442 info issues), testing.md seeAlso clarification, journal Session 12.

### What we found

| Finding | Severity | Fix |
|---------|----------|-----|
| `06_validate.py` reads 0 entries (wrong key) | Critical | `'klawiter:entries'` → `'entries'` |
| `ABOUT_ZWEIG_TYPES` 3 different definitions | Critical | Aligned to pipeline logic |
| Year caps: 2025/2030/2035/dynamic | High | Unified to `config.MIN/MAX_VALID_YEAR` |
| Test count wrong in 5 docs | Medium | All updated to 326 |
| architecture.md: Tailwind, Chart.js, 4 MB | Medium | Updated to CSS, D3.js, 9 MB |
| data.md quality report: 32 info → 442 | Medium | Corrected |
| ontology.md @context outdated | Medium | Mirrors current vocabulary.py |

### Learnings

1. **Silent validation failures are the worst bugs**: `06_validate.py` processed 0 entries and reported no errors because the fallback was `[]`. Always validate that inputs are non-empty.
2. **Constants defined in multiple places will drift**: `ABOUT_ZWEIG_TYPES` had 3 different definitions. The pipeline is the source of truth; frontend must mirror it.
3. **Documentation decays faster than code**: 8 inconsistencies accumulated over 3 sessions. Automated checks (grep for known numbers) would catch these.

---

## 2026-04-12 — Session 11: Testing Strategy Overhaul

### What we did

- **Critical audit of existing 280 tests**: Identified structural weaknesses — unit tests against handcrafted fixtures, silent skip-logic in real-entry tests, broken regression test (`test_year_range_sane` didn't check year ranges), 100-entry spot-check on 5,179 entries.
- **Web research**: Data pipeline testing best practices (OpenCitations bibliographic validation, golden file testing, Pandera schema contracts, Hypothesis fuzzing, risk-based threshold calibration).
- **New knowledge document**: `knowledge/testing.md` — 5-category test taxonomy with honest assessment of what each category can and cannot detect.
- **New test_census.py** (14 tests): Completeness verification — exact entry counts, no duplicates, known stubs, required fields on every entry, frontend JSON structure.
- **New test_schema.py** (14 tests): Schema validation over all 5,179 entries — entry types, year ranges, language codes, page counts, wiki markup residue, mojibake, empty strings, JSON-LD type consistency.
- **New test_consistency.py** (6 tests): Cross-field plausibility — German+translator bounded (111 FPs), film+pageCount bounded (10), publisher≠location, year/timePeriod consistency, seeAlso referential integrity (717 broken refs bounded), no self-references.
- **Overhauled test_regression.py**: Fixed broken `test_year_range_sane`, sharpened thresholds (2pp→1pp, 1%→0.5%), extended spot-check to all entries, added entry type distribution stability test.
- **Overhauled test_real_entries.py**: Removed silent skip-logic, LLM-only fields as xfail instead of pass-by-doing-nothing.
- **Updated CLAUDE.md, plan.md**: 314→ tests, 5-category strategy, page 2979 as stub, 20 markup titles documented.

### What we found

| Finding | Count | Detected by |
|---------|-------|-------------|
| Titles = `__TOC__` (title extraction failure) | 14 | test_schema |
| Titles with `]]`/`[[` markup | 6 | test_schema |
| German entries with translator (regex FP) | 111 | test_consistency |
| Broken seeAlso cross-references | 717 / 1,213 | test_consistency |
| Films with pageCount | 10 | test_consistency |
| Publisher == Location | 1 | test_consistency |
| Page 2979 exists as stub (docs said "missing") | 1 | test_census |

### What we learned

1. **Testing the functions ≠ testing the data.** 280 unit/pattern tests proved the regex works on cherry-picked strings. Zero tests asked whether the actual output contained all entries or had correct field values.
2. **Shape correctness ≠ content correctness.** A publisher field containing a city name passes all schema checks. Only cross-field consistency tests can flag implausible combinations.
3. **Silent test passes are worse than no tests.** The old `test_real_entries.py` had 160 tests, many of which asserted nothing due to skip-logic. This gave false confidence.
4. **The biggest gap is semantic accuracy.** We test 20 of 4,751 entries (0.4%) for correctness. Completeness and structure are fully automated; accuracy requires judgment.

### Next steps

- Fix the 20 markup titles in the pipeline (title extraction bug)
- Investigate 111 German translator false positives (regex improvement)
- Expand real-entry sample from 20 to 50 entries
- Improve seeAlso matching (717 broken refs partly a suffix-matching problem)

---

## 2026-03-31 — Session 10: Frontend Cleanup, Data Quality Analysis & Regression Testing

### What we did

- **Frontend refactoring** (12 files, 6 phases):
  - Unified color palette: `COLORS` constant in constants.js as single source of truth (fixed CSS `#631a34` vs JS `#7A1B2D` mismatch)
  - Deduplicated code: wired up unused `countByField()` at 6 call sites, eliminated redundant titleMap in ExploreNetwork, reused `downloadBlob()` in Edit module
  - Performance: replaced DOM-based `esc()` with regex (~10x faster), fixed asymmetric sort fallbacks (`?? Infinity`)
  - Security: added SRI hashes to FlexSearch and D3 CDN scripts
  - Replaced inline `onclick` handlers with event delegation on results list and filter chips
  - Removed ~50 lines dead CSS, added ARIA labels to all 6 D3 SVGs, added `og:url` meta tag
  - Extracted `CHART_DIMS` constant for magic numbers in explore modules

- **Data quality deep-dive** (3 parallel investigations):
  - **Title precision**: 880 "false positives" in verify.py were a methodology issue, not extraction errors. page_title fallbacks are metadata — they correctly don't appear in raw content. Real precision ~95%+
  - **Publisher gap**: 44% missing = 15-20% legitimately absent (anthology poems, journal articles) + 80-85% structural (implicit `[[Collection]] [City, Year]` format, only 1.7% contain publisher keywords)
  - **Regression testing**: zero system-level checks existed before this session

- **Regression testing infrastructure** (3 new files):
  - `.github/baseline-metrics.json`: frozen coverage snapshot for comparison
  - `tests/test_regression.py`: 18 tests (entry counts, field coverage thresholds, severity bounds, frontend integrity)
  - Extended `.github/workflows/validate-patch.yml` with regression checks and quality report comparison

- **Title extraction improvements**:
  - `verify.py`: new `correct_fallback` status for page_title-sourced titles (fixes misleading 81.5% precision)
  - `03_parse_entries.py`: when `[year]:` pattern detected, search for second bold block as real title before falling back to page_title
  - `wiki_parser.py`: added removal of `__TOC__`, `__NOTOC__`, `__FORCETOC__`, `{{DEFAULTSORT:...}}`
  - 10 new tests (wiki parser + regression), total: 270 → 280

### What we learned

1. **Verification must match extraction methodology**: verify.py did a blind "value in raw text?" check without knowing the pipeline uses page_title fallback. This produced 880 phantom false positives. Always ensure verification tools understand the extraction strategy.
2. **Not every coverage gap is a bug**: The 44% publisher gap is mostly structural — anthology poems and journal articles genuinely lack standalone publishers. Distinguishing "not extracted" from "not present" requires entry-type-aware analysis.
3. **Unit tests ≠ regression safety**: 270 extraction tests caught individual pattern bugs but couldn't detect if overall coverage silently degraded. System-level baseline comparison is essential for data pipelines.
4. **CSS/JS color sync in vanilla projects**: Without CSS-in-JS or a build step, color values drift. A shared constants file (`COLORS`) is the simplest workaround.

### What's next

- **Re-run pipeline**: Apply title extraction improvements to actual data, measure impact
- **M3.8**: Manual validation — browse 50+ entries in live frontend

---

## 2026-03-29 — Session 9: Interactive Exploration Interface & Refactoring

### What we did

- **D3.js exploration interface**: Replaced the generic Chart.js dashboard with a 3-mode interactive visualization built on D3.js v7:
  - **Timeline**: Stacked area chart (year × language) with brushing, biographical annotations (born/exile/death), lifetime gold band
  - **Overview**: 4 linked small multiples (decade histogram, type treemap, language bars, location lollipop) with cross-filtering
  - **Connections**: Force-directed graph of seeAlso cross-references (~469 nodes, ~496 edges) with drag, zoom, neighbor highlighting
  - Shared detail panel showing selected entries across all modes
- **UX improvements**: Replaced "(Klawiter)" subtitle with "Digital Edition", hid duplicate header search on home, renamed explore link, added Zotero guide to Help page
- **Exploration fixes**: Fixed network overflow, detail panel state persistence, "Unknown" language in timeline, legend/annotation overlap, force bounds
- **Refactoring** (5 changes):
  - Deduplicated BibTeX field-building in export.js
  - Replaced O(n) title search with O(1) titleMap in detail.js
  - Added countByField() utility to utils.js
  - Unified 3 wiki section extractors into one generic function in wiki_parser.py
  - Moved encoding comparison utilities from verify.py to lib/encoding.py
- **Documentation**: Created `knowledge/exploration.md` with full design concept, research questions, visualization rationale, and DH references

### What we learned

- Generic dashboard visualizations don't serve academic research — researchers need purpose-built exploration tools with specific research questions in mind
- D3.js via CDN works well for static sites; the stacked area chart immediately tells the Zweig reception story (German dominance → global spread → Chinese boom)
- Network graphs from seeAlso data are sparser than expected (~496 resolved edges from 1,213 references) due to unresolved title references
- "Unknown" language entries (~500) dominated the timeline visualization and needed to be folded into "Other"

### What's next

- **M3.8**: Manual validation (browse 50+ entries in live frontend)
- **Explore refinement**: Consider adding a true streamgraph offset, improving mobile experience

---

## 2026-03-29 — Session 8: Deployment Preparation & Namespace Fix

### What we did

- **Namespace URI fix**: Changed all references from `klawiter-rescue.github.io` to `chpollin.github.io/klawiter-rescue` across 10 files (vocabulary.py, export.js, pages.js, vocab/index.html, data.md, ontology.md, CLAUDE.md)
- **GitHub link fix**: Footer link corrected from `chrstncrrnd/klawiter-rescue` to `chpollin/klawiter-rescue`
- **LICENSE file**: Created dual-license (MIT for code, CC BY 4.0 for data)
- **CITATION.cff**: Created for academic citation (Klawiter + Pollin as authors)
- **README.md**: Added live URL and updated license section (was "To be clarified")
- **Pipeline regeneration**: Steps 05+06 re-run to produce JSON-LD and frontend JSON with corrected namespace
- **Documentation update**: Updated CLAUDE.md (test count 260→270, 9→10 JS modules, live URL), plan.md (M7 tasks checked), IMPLEMENTATION-PLAN.md (Phase 8 added)
- **Tests verified**: 264 passed, 6 skipped, 0 failed

### What we learned

- The namespace URI had been set to `klawiter-rescue.github.io` (as if the repo were deployed as an organization page), but the actual deployment is at `chpollin.github.io/klawiter-rescue/` (project page under personal account). This affected JSON-LD @context resolution and all hardcoded URLs in content pages.
- The GitHub footer link pointed to a different user (`chrstncrrnd`) — likely a leftover from an earlier contributor.

### What's next

- **M3.8**: Manual validation — browse 50+ entries in live frontend, spot-check against wiki source
- **M7 remaining**: Live deployment testing, Zenodo DOI, announcement

---

## 2026-03-29 — Session 7: Design Alignment, Verbund Navigation & EIL Curation Interface

### What we did

**Design alignment**: Adopted GAMS institutional color palette across all Verbund sites. Switched typography to Source Serif 4 (headings) + Source Sans 3 (body) for consistency with the broader Stefan Zweig Digital ecosystem.

**Verbund navigation bar**: Implemented a shared top navigation bar connecting three sites (SZD, Klawiter Bibliography, planned Nachlass portal). Provides unified cross-site navigation for the Zweig Forschungsverbund.

**SZD site updates**: Translated the SZD frontend to English. Refactored the visualization module. Redesigned the dashboard with an ontology-focused layout emphasizing CIDOC-CRM relationships.

**Klawiter landing page redesign**: Replaced the flat category list with expandable category groups. Added "Browse Catalogue" and "Explore" navigation paths for different user workflows.

**EIL curation interface**:
- `pipeline/inject_provenance.py`: Diffs regex output (03_parsed.csv) against LLM cache (03b_llm_cache.json) to generate per-field provenance metadata (`_provenance` object with values regex/llm/missing for publisher, location, translator, pageCount). Injects into `docs/data/klawiter.json`.
- `docs/js/edit.js`: Localhost-only edit mode for inline field editing with provenance awareness. Edits are collected as JSON patches, not written directly to the dataset.
- Provenance badges: Visual indicators showing extraction source (regex/llm/missing) on metadata fields.
- JSON patch export: Curators review and export edits as structured patches.
- `.github/workflows/validate.yml`: GitHub Actions workflow running pipeline validation on PRs to ensure data integrity.

### Learnings

- **Provenance tracking enables trust**: Showing users whether a field was extracted by regex (high confidence) or LLM (needs review) makes the curation workflow transparent. The "missing" label directs attention to entries that need manual enrichment.
- **Localhost-only editing is a pragmatic security model**: No authentication needed for a static site — the edit interface simply doesn't load on the public deployment.
- **Shared navigation requires coordination**: The Verbund nav bar links to three separate GitHub Pages deployments. URL structure must be stable across all sites.

---

## 2026-03-29 — Session 6: Knowledge Base Audit & Documentation Refactoring

### What we did

**Knowledge base audit**: Systematically reviewed all 11 Obsidian vault files, README.md, CLAUDE.md, and IMPLEMENTATION-PLAN.md against the actual code and data output.

**Found 18 factual inaccuracies** across all docs:
- M4 (Ontology) marked as "pending" — was fully implemented
- "15 entry types" in multiple files — correct count is 16 (incl. redirect)
- "6 pipeline stages" in pipeline.md — correct is 7
- "~4 MB JSON" in ui-design.md — actual is ~9 MB
- "Vocabulary blend planned" in CLAUDE.md, architecture.md — is implemented
- "8 JS modules" — now 9 (pages.js added)
- 5 content pages (About, Methodology, Help, Data, Imprint) undocumented
- Journal missing Sessions 4–5
- SZD attributed to "University of Graz" in vocab doc — correct is University of Salzburg

**Fixed all files**: README.md, CLAUDE.md, IMPLEMENTATION-PLAN.md, pipeline.md, architecture.md, ui-design.md, data.md, ontology.md, plan.md, design.md, dataflow.md, journal.md.

**Plan consolidation**: M4 marked as ✅ in both plan.md and IMPLEMENTATION-PLAN.md. Dependency diagram updated to show actual completion order.

### Learnings

- **Documentation debt accumulates fast**: All docs were written on the same day, but 3 major features (ontology implementation, frontend redesign, content pages) shipped without updating them. The docs were internally consistent but collectively outdated.
- **Cross-referencing matters**: Isolated vault files (journal.md, dataflow.md) had no wikilinks and were effectively invisible within the knowledge graph. Adding `[[links]]` integrates them.
- **Two plan files create confusion**: `IMPLEMENTATION-PLAN.md` (task-oriented, phased) and `knowledge/plan.md` (milestone-oriented, M1–M7) described the same work differently. Keeping them aligned requires discipline.

---

## 2026-03-29 — Session 5: Frontend Content Pages & Data Quality Fixes

### What we did

**5 content pages** built for the frontend (`docs/js/pages.js`):
- **About** (`#about`): Klawiter's biography, the original wiki, the rescue project, connection to SZD
- **Methodology** (`#methodology`): Pipeline steps, encoding repair, LLM enrichment with coverage table, quality assurance, known limitations
- **Help** (`#help`): Search, filtering, sorting, entry details, export formats, FAQ
- **Data Access** (`#data`): Dataset download button, field table, vocabulary docs, license, citation
- **Imprint** (`#imprint`): Credits, citation recommendation, license, contact, technical info

**Navigation**: Added "About" link + "More" dropdown (Methodology, Help, Data, Imprint) to header. Footer gets new "Information" column with all 5 page links. Mobile: accessible via footer.

**Vocabulary/data quality review**: Compared `docs/vocab/index.html` against actual `@context` in `pipeline/lib/vocabulary.py` and JSON-LD output.

**Pipeline fixes**:
- `extract_original_title()`: Rejected bare years as original titles (272 false positives → 0)
- `remove_wiki_markup()`: Added section header stripping (`==text==` → `text`) and unpaired bold marker removal (28 titles with markup → 1)
- `vocabulary.py`: Added `@container: @set` for `allYears` and `allLocations`

**Vocab doc corrections**: `sameAs` marked as "planned", `schema:Message` annotated, SZD → University of Salzburg, range types corrected.

**Automated validation**: Systematic validation of all 4,751 ns0 entries + stratified sample of 84 entries across 20 types. Found and fixed translator regex leaking across newlines (34 entries with markup in translator field → 0). München encoding verified correct (terminal display artifact).

**Pipeline re-run**: Steps 3–6, 10.5s, all data regenerated. 260 tests pass, 0 fail.

### Learnings

- **Vocab docs must be verified against code**: The vocab page claimed `sameAs` was "used" but no entry had it. The only way to catch this is automated checks against the actual output.
- **Schema.org is more complete than expected**: Both `schema:Play` and `schema:Collection` exist — initial assumptions that they were missing were wrong. Always verify before changing type mappings.
- **Wiki markup in titles has a long tail**: The `remove_wiki_markup()` function handled paired `'''bold'''` but not section headers (`==text==`) or unpaired markers. Edge cases accumulate.
- **`\s` in regex character classes matches newlines**: The translator patterns used `\s` which includes `\n`, causing matches to span across line breaks into subsequent sections. Using `[ \t]` instead restricts to horizontal whitespace.

### Files created/modified
- `docs/js/pages.js` — NEW: 5 content page renderers
- `docs/index.html` — view container, navigation, footer, script tag
- `docs/js/app.js` — page routing, view toggling, dropdown logic
- `docs/css/styles.css` — page content typography, nav dropdown, table styles
- `pipeline/lib/wiki_parser.py` — `extract_original_title()` + `remove_wiki_markup()` fixes
- `pipeline/lib/vocabulary.py` — `@container` for allYears/allLocations
- `docs/vocab/index.html` — 4 documentation corrections

---

## 2026-03-29 — Session 4: Frontend Redesign & Schema.org Vocabulary

### What we did

**Frontend redesign** to match Stefan Zweig Digital visual language:
- Custom CSS (1,000+ lines) with SZD palette: burgundy #7A1B2D, gold #B8963E, cream #FAF8F3
- Serif/sans-serif typography system (Georgia + system sans-serif)
- 4-view architecture: Overview (category portal), Browse (faceted search), Detail (expandable cards), Statistics
- 8 JS modules extracted from monolithic app.js: constants, utils, export, app, home, facets, detail, charts
- Category tiles grouped by Works / Reception & Impact / Editions
- Expandable result cards with inline detail rendering
- Interactive Chart.js charts with click-to-filter
- BibTeX + RIS export with correct author logic (Stefan Zweig for primary, omitted for secondary)
- Responsive design: mobile filter panel, sticky header, skip-link

**Schema.org + Dublin Core vocabulary blend** implemented in `pipeline/lib/vocabulary.py`:
- 16 entry types mapped to Schema.org types (`schema:Book`, `schema:Article`, `schema:Play`, etc.)
- Standard fields via Schema.org (name, datePublished, publisher, inLanguage, numberOfPages, translator, locationCreated)
- `dcterms:bibliographicCitation` for full original text
- `klawiter:` namespace for domain-specific fields (entryType, timePeriod, categories, contentItems, etc.)
- Stefan Zweig as `schema:Person` with Wikidata `sameAs` link (Q78491)
- `05_to_jsonld.py` rewritten to use the new vocabulary

**Namespace documentation**: Created `docs/vocab/index.html` with complete vocabulary reference.

### Learnings

- **The category portal approach works**: Users familiar with the original MediaWiki navigate by category tiles exactly as expected. The landing page is an orientation tool, not a dashboard.
- **Expandable cards are better than separate detail pages**: Inline expansion keeps context (the user sees where they are in the results list). This matches how users actually browse bibliographies.
- **Dual-type arrays are elegant**: `@type: ["schema:Book", "klawiter:FictionEntry"]` gives standard interoperability while preserving domain specificity. No information is lost.

### Files created/modified
- `docs/index.html` — complete restructure (4 views, semantic HTML)
- `docs/css/styles.css` — NEW: 1,000+ lines custom CSS
- `docs/js/app.js` — state management, routing, search, expandable cards
- `docs/js/home.js` — category portal
- `docs/js/charts.js` — statistics charts
- `docs/js/detail.js` — metadata table, conditional sections
- `docs/js/facets.js` — faceted navigation
- `docs/js/export.js` — BibTeX, RIS, JSON-LD, permalink
- `docs/js/utils.js` — esc(), hl(), downloadBlob()
- `docs/js/constants.js` — shared labels, groupings
- `pipeline/lib/vocabulary.py` — rewritten with Schema.org blend
- `pipeline/05_to_jsonld.py` — rewritten for new vocabulary
- `docs/vocab/index.html` — NEW: vocabulary namespace page

---

## 2026-03-29 — Session 3: Test Suite & LLM-as-a-Judge

### What we did

**Phase 3: Test suite** (from IMPLEMENTATION-PLAN.md)
- Built initial test suite: 171 tests across 3 files (test_patterns.py, test_wiki_parser.py, test_encoding.py)
- Critically reviewed all tests — identified ~40-50 as trivial or redundant (guard-clause tests for every function, dictionary lookups tested individually, language whitelist tested 8×)

**Test refactoring**
- Trimmed redundant tests: test_encoding.py 36→13, test_patterns.py 58→48
- Fixed weakened title tests to test actual pipeline flow (categories stripped before title extraction)
- **Result**: leaner, more focused unit tests

**Real-data tests** (`tests/test_real_entries.py`)
- Parametrized over 20 hand-labeled entries from `test_sample_20.json`
- Tests 5 extractors per entry: location, publisher, translator, page_count, language
- Plus structural tests: not-redirect, has-clean-content, categories-extracted
- 6 skips for fixture/text mismatches (truncated text doesn't contain expected data)

**LLM-as-a-Judge** (`tests/test_llm_judge.py`)
- Gemini 3.1 Flash Lite evaluates extraction quality on 10 diverse entries
- Structured output via Pydantic: each field judged as correct/wrong/missed/not_applicable
- Findings establish a baseline of known limitations:
  - 10 "wrong": title from `'''[year]: Publisher'''` headers (6×), mojibake truncation (2×), page-range-as-count (2×)
  - 13 "missed": publisher/location from headers, `N/(M)p.` format, languages without `[[Category:]]`
- Tests assert: no *unexpected* wrong extractions, ≥60% correct/not_applicable

**Infrastructure**
- Created `pytest.ini` with `llm` marker and PYTHONPATH config
- Tests runnable separately: `pytest -m "not llm"` (fast) vs `pytest -m llm` (API call)

### Learnings

- **Redundant tests create false confidence**: 171 tests sounded impressive, but many tested `if not x: return None` eight times. The real-data tests found more issues than all guard-clause tests combined.
- **LLM-as-a-Judge is surprisingly effective**: For ~$0.001, Gemini identified 10 concrete extraction errors and 13 coverage gaps. It catches semantic issues (wrong publisher name, truncated translator) that pattern-based tests can't.
- **Fixture text truncation matters**: The `test_sample_20.json` entries have truncated text that doesn't always contain the same information the full pipeline had. This caused 6 false test failures that needed skips.
- **LLM non-determinism in testing**: The judge produces slightly different verdicts on repeated runs. The `_KNOWN_WRONG` set handles this — if the LLM finds something new, the test fails and forces investigation. If it misses a known issue, a warning fires.

### Files created/modified
- `pytest.ini` — test configuration
- `tests/conftest.py` — fixtures (real-data loader, Gemini client, wiki content samples)
- `tests/test_patterns.py` — trimmed unit tests (48)
- `tests/test_wiki_parser.py` — fixed + trimmed unit tests (80)
- `tests/test_encoding.py` — trimmed unit tests (13)
- `tests/test_real_entries.py` — parametrized real-data tests (100)
- `tests/test_llm_judge.py` — LLM-as-a-Judge validation (4)

---

## 2026-03-29 — Session 2: Pipeline Quality Assurance & LLM Enrichment

### What we did

**Phase 1: Verification script** (`pipeline/verify.py`)
- Built round-trip verification: loads final JSON-LD, compares each extracted field against raw wiki content from step 02
- Detects false positives (extracted but not in raw) and false negatives (in raw but not extracted)
- Added broader pattern detection beyond existing regex for publisher (`City: Publisher` pattern) and translator (abbreviations like `Übers.`, `trad.`)

**Verification results** (4,751 bibliography entries):
| Field | Coverage | Precision | FP | FN |
|---|---|---|---|---|
| title | 100% | 81.4%* | 885 | 0 |
| year | 93.2% | 100% | 0 | 0 |
| publisher | 34.5% | 100% | 0 | 86 |
| location | 67.8% | 100% | 0 | 0 |
| translator | 35.1% | 100% | 0 | 2 |
| page_count | 78.4% | 100% | 0 | 0 |

*Title 81.4%: not real FPs — titles come from `page_title` fallback, not from content.

**Phase 2: LLM enrichment step** (`pipeline/03b_llm_enrich.py`)
- Designed and built Step 03b using Gemini 3.1 Flash Lite for gap-filling
- Pydantic schema for structured JSON output (publisher, location, translator, page_count)
- Merge rule: LLM only fills empty fields, never overwrites regex results
- Cache-based resume support, rate limiting, validation layer

**Testing**:
- 5-entry quick test: all correct
- 20-entry stratified sample covering: isolated missing fields, 7 languages (EN/FR/RU/ZH/JA/AR/ES), standard/non-standard formats, short texts, German negative tests
- Result: 13/13 correct extractions, 0 hallucinations, all negative tests passed

### Learnings

- **Verification circularity**: Using the same regex patterns to detect false negatives finds nothing — the patterns already extracted what they can. Broader heuristics or LLM needed for true FN detection.
- **LLM conservative by design**: The prompt "Extract ONLY what is explicitly stated / Do NOT guess" produces zero hallucinations across all tests. The model correctly returns null for See-references, film entries, and German originals.
- **Encoding artifacts pass through**: LLM faithfully extracts text with Mojibake (e.g. "KavkazskiÄ­ Krai") — it doesn't fix encoding, which is correct since that's step 02's job.

### Files created/modified
- `pipeline/verify.py` — verification script
- `pipeline/03b_llm_enrich.py` — LLM enrichment step
- `pipeline/lib/llm_extract.py` — Gemini client, schema, prompt, batch logic
- `pipeline/lib/config.py` — added `STEP_03B_OUTPUT`
- `pipeline/04_classify.py` — reads from 03b with fallback to 03
- `pipeline/run_pipeline.py` — added step 03b
- `.env` — Gemini API key (gitignored)
- `.gitignore` — added `.env`

---

## 2026-03-29 — Session 1b: Raw Data Verification

### What we did

Ran two parallel analysis agents to cross-verify raw source data against pipeline extraction logic:
- Agent 1: Analyzed all files in `data/raw/` — file sizes, SQL structure, BLOB format, text ID counts
- Agent 2: Analyzed `pipeline/01_extract.py` — extraction logic, namespace filtering, BLOB parsing, coverage

### Learnings

- **Pipeline is verified correct**: All 6,296 namespace-0 pages are processed. 6,295 find their content in BLOBs (99.98%).
- **The missing entry is identified**: page_id 2979, text_id 18046, "A unidade espiritual do mundo" (Portuguese edition). The text_id exists in the database mapping but is absent from all 8 BLOB files — this is a source data issue, not a pipeline bug.
- **429 non-namespace-0 pages are excluded by design**: Most notably **420 Category pages** (namespace 14). These contain category descriptions and hierarchies that could be valuable metadata but are not bibliography entries.
- **SQL dump files 02 and 03 are correctly ignored**: `zweig_part_02.sql` is just the empty `zweig_text` table schema. `zweig_part_03.sql` contains system metadata (4 user accounts, 47 update log entries, 48 watchlist records) — none relevant to bibliography.
- **BLOBs contain 53,016 text entries** across all 8 files, covering all historical revisions. Pipeline correctly extracts only the latest revision per page (via `page_latest`).
- **BLOB file sizes were wrong in documentation**: Previously listed as 28–44 MB, actual sizes are 27–49 MB. Updated in pipeline.md.

### Ideas & open threads

- **420 Category pages**: Should we extract these? They could provide richer category descriptions for the frontend (currently categories are just labels). Would need a separate extraction step or expanding namespace filter.
- **Historical revisions**: 45,650 earlier versions are discarded. Could be interesting for a "history of the bibliography" analysis, but not needed for the current project scope.
- **The missing Portuguese entry**: Could try to recover by searching the BLOB files for the page title string rather than the text_id. Might be a text_id mismatch from a re-import.

---

## 2026-03-29 — Session 1: Repository Restructuring & Planning

### What we did

**Phase 1: Analysis**
- Explored the entire repository — v1 root-level files (5 Python scripts, 6 output directories, 2 old web UI attempts, 4 markdown docs, 1 log) and v2/ (pipeline, frontend, knowledge base, data outputs)
- Identified that v2 is the current, production-ready system; everything at root level is legacy
- Assessed what's still useful: raw source data (working/), the rest is superseded

**Phase 2: Repository restructuring**
- Promoted v2/ contents to root level:
  - `v2/pipeline/` → `pipeline/`
  - `v2/frontend/` → `docs/` (for GitHub Pages deployment)
  - `v2/data/` → `data/`
  - `working/` → `data/raw/`
  - `v2/knowledge/` → `knowledge/`
- Updated path references in all 7 pipeline scripts:
  - `WORKING_DIR` → `RAW_DIR` pointing to `data/raw/`
  - `BASE_DIR` → `PROJECT_ROOT` (consistent naming)
  - Frontend output path → `docs/data/klawiter.json`
- Deleted all legacy files: 5 old Python scripts, analysis_output/, analysis_results/, bibliography_analysis/, bibliography_cleaned/, rebuild-wiki/, rebuild-wiki-o3/, old markdown docs, log file
- Removed REPORT.md (redundant with README + knowledge docs)
- Created new .gitignore (intermediate data, entry files, __pycache__, .obsidian/)

**Phase 3: Knowledge base refactoring (M1)**
- Consolidated 10 German documentation files into 6 focused English documents:
  - `data.md` ← Datenmodell + Datenqualitaet + Entitaetstypen (data model, entity types, field coverage, quality issues)
  - `pipeline.md` ← Pipeline + MediaWiki-Datenbank + Encoding-Problem + Regex-Patterns (source structure, 6 pipeline stages, encoding fix details, all regex patterns with coverage stats)
  - `architecture.md` ← Architekturentscheidungen (6 decisions with rationale and trade-offs)
  - `ontology.md` ← NEW (current klawiter: namespace, Schema.org mapping table, target @context design, namespace resolution plan)
  - `reconciliation.md` ← NEW (Wikidata/GND/VIAF/GeoNames strategy, entities to reconcile, tooling options, data model integration)
  - `ui-design.md` ← Frontend expanded (current tech stack, views, Stefan Zweig Digital integration goals, stable URIs, performance, accessibility)
- Verified all Obsidian wikilinks between files resolve correctly
- Removed Klawiter-Projekt.md (redundant with README.md)

**Phase 4: Project planning**
- Created `plan.md` with 7 milestones, 80+ tasks with checkboxes
- Defined dependency chain: M1 → M2 → M3 → M4 → M5 → M6 → M7
- Discussed project goals: data rescue, structured JSON-LD, semantic enrichment, static frontend matching Stefan Zweig Digital

**Commit**: `9640dde` — 119 files changed, 51,631 deletions, 1,225 additions

### Learnings

- **Duplicate path definitions**: Each pipeline script defined its own BASE_DIR/WORKING_DIR instead of importing from config.py. This made the restructuring harder than necessary. Partially fixed (renamed to PROJECT_ROOT), full consolidation to config.py imports is planned for M3.2.
- **The honesty check pattern**: The project's first encoding fix claimed "0% Mojibake" but only checked 7 common patterns — 9.1% actually remained. The revised fix and its verification use the same regex. Lesson: the verification must always be broader than the repair. This is documented in pipeline.md as a cautionary tale.
- **CLAUDE.md drift**: The CLAUDE.md was entirely about the v1 system (MySQL-based extraction, old scripts). It had become actively misleading. Lesson: documentation that falls out of sync with code is worse than no documentation.
- **Windows case-insensitivity**: git mv from `Pipeline.md` to `pipeline.md` doesn't work on Windows because the filesystem treats them as the same file. Had to delete first, then create new.
- **IDE file locks**: VS Code held `v2/frontend/` open, preventing deletion. Not critical — empty directories aren't tracked by git.
- **README umlaut problem**: When writing the README.md, all German umlauts were lost (Einträge → Eintrage, etc.). Systematic issue that needs fixing in M2.

### Ideas & open threads

- **Data validation against source**: Nobody has manually checked whether extracted content actually matches the original wiki. 50-entry spot check is in the plan (M3.5) but should happen early — if systematic errors exist, everything downstream is affected.
- **The 1 missing entry**: 1 of 6,296 pages couldn't be found in any BLOB. Worth investigating — is it a page with no content? A namespace issue? A BLOB parsing edge case?
- **Publisher extraction at 34.5%**: This is the weakest field. Three approaches: (a) more regex patterns, (b) NER, (c) use structured position in wiki markup — publisher often appears on a specific line within the `<lst>` block. Option (c) hasn't been explored and might be the most reliable.
- **Translator false-positive trade-off**: Old extraction had 69% coverage / 46% false positives. Current has 35% / 0%. Could there be a middle ground — e.g. a confidence score per extraction?
- **JSON-LD namespace**: `klawiter-rescue.github.io/vocab/` doesn't resolve. Blocker for proper Linked Data. Needs a vocab document at `docs/vocab/index.html`.
- **Stefan Zweig Digital integration**: We want the frontend to visually match their design but haven't analyzed the site yet. Prerequisite for M6. Need to coordinate with the project team.
- **License**: Unclear who holds rights to the bibliography data. Dr. Klawiter compiled it, Notre Dame hosted it. Need to clarify before publishing.
- **Performance**: 4.2 MB JSON → ~800 KB gzipped. Probably fine, but needs real measurement on mobile.
- **GitHub Pages limitations**: No server-side content negotiation for JSON-LD namespace. May need a redirect hack for vocab URL.
- **FAIR principles**: Currently missing: persistent identifier (F), standard vocabulary (I), license (R). All addressable in M4+M7.
- **Obsidian as documentation tool**: The knowledge/ folder works well as an Obsidian vault with wikilinks between docs. Could also serve as a pattern for other DH projects.
