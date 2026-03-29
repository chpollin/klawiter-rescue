# Project Plan

Research and implementation plan for the Klawiter Bibliography rescue project.
Each milestone contains precise tasks with checkboxes. Check off tasks as completed.

---

## M1: Knowledge Refactoring

Consolidate 10 German documentation files into 6 focused English documents.

**Files to create:**
- `data.md` ← Datenmodell + Datenqualitaet + Entitaetstypen
- `pipeline.md` ← Pipeline + MediaWiki-Datenbank + Encoding-Problem + Regex-Patterns
- `ontology.md` ← NEW (Schema.org mapping from Datenmodell + semantic modeling strategy)
- `reconciliation.md` ← NEW (Wikidata/GND enrichment strategy)
- `ui-design.md` ← Frontend (expanded with Stefan Zweig Digital design goals)
- `architecture.md` ← Architekturentscheidungen

**Files to remove:** Architekturentscheidungen.md, Datenmodell.md, Datenqualitaet.md, Encoding-Problem.md, Entitaetstypen.md, Frontend.md, Klawiter-Projekt.md, MediaWiki-Datenbank.md, Pipeline.md, Regex-Patterns.md

### Tasks

- [x] Write `data.md` — data model (JSON-LD fields, example entry), 16 entity types with distribution, field coverage table, quality metrics, known data problems
- [x] Write `pipeline.md` — source structure (MediaWiki 4-table chain, 8 BLOBs with size table), 6-step pipeline with data flow, encoding fix (root cause, line-wise approach, honesty check), regex patterns (all families with coverage), execution instructions
- [x] Write `ontology.md` — current `klawiter:` namespace, Schema.org mapping table, strategy for domain-specific extensions, namespace resolution plan
- [x] Write `reconciliation.md` — target authority systems (Wikidata, GND, VIAF, GeoNames), entity types to reconcile (works, persons, places, publishers), tooling (OpenRefine vs custom pipeline step), expected coverage
- [x] Write `ui-design.md` — current tech stack, views and URL schema, Stefan Zweig Digital design analysis, integration strategy, stable URI scheme, performance considerations
- [x] Write `architecture.md` — all 6 decisions with trade-offs (vocabulary, no-MySQL, vanilla JS, redirects, encoding-before-parsing, title fallback), translate to English
- [x] Remove 10 old German files
- [x] Verify all Obsidian wikilinks (`[[...]]`) work between new files

---

## M2: Repository Cleanup

Fix README.md and CLAUDE.md quality issues, finalize .gitignore.

### Tasks

- [x] Fix README.md — replace all broken umlauts (Eintrage→Einträge, etc.), add Credits section (Dr. Klawiter, Notre Dame), add License section, add link to live site (once deployed)
- [x] Reduce CLAUDE.md — remove project structure and pipeline sections (redundant with README), keep only: data flow, technical decisions summary, known limitations, path conventions
- [ ] Remove empty v2/ directory (once IDE releases lock)
- [x] Commit all M1+M2 changes

---

## M3: Pipeline Refactoring & Testing

Harden the extraction pipeline: eliminate code duplication, add comprehensive tests, improve weak extraction patterns.

### M3.1: Baseline — Capture current output

- [ ] Run full pipeline, save checksums of all intermediate CSVs and final klawiter.jsonld
- [ ] Save 50 representative entries (diverse types, languages, edge cases) as golden test fixtures

### M3.2: Config consolidation

- [x] Make all 6 scripts import paths from `pipeline/lib/config.py` — remove local `PROJECT_ROOT`, `INPUT_PATH`, `OUTPUT_PATH` definitions
- [x] Remove redundant `csv.field_size_limit()` calls from scripts 02–05 (already set globally in config.py)
- [x] Make all scripts use `config.setup_logging()` instead of local `logging.basicConfig()`
- [x] Expand extraction to ALL namespaces (6,725 pages including 420 Category pages)
- [x] Add `page_namespace` field through entire pipeline
- [x] Verify pipeline runs successfully (35.9s, 6,721/6,725 found)

### M3.3: Test infrastructure & pipeline refactoring

- [x] Create `tests/` directory with `conftest.py` (shared fixtures, Gemini client, real-data loader)
- [x] Write unit tests for patterns, wiki_parser, encoding (141 focused tests)
- [x] Write real-data tests: parametrized over 20 hand-labeled entries × 5 extractors (100 tests)
- [x] Write LLM-as-a-Judge tests: Gemini evaluates extraction quality on 10 entries (4 tests)
- [x] Write unit tests for `lib/vocabulary.py`: classify_time_period, category_to_entry_type, language_to_iso (19 tests)
- [x] Create `pytest.ini` with markers (`llm`) and PYTHONPATH config
- [x] Consolidate `OUTPUT_FIELDS` into `lib/config.py` as `PARSED_FIELDS`/`CLASSIFIED_FIELDS` (was duplicated in 3 files)
- [x] Add `csv_bool()`, `load_env()`, `MIN_CONTENT_LENGTH` to `lib/config.py` (eliminate duplication + magic numbers)
- [x] Move `PAGE_RANGE_RE`/`PARENS_PAGE_RE` to `lib/patterns.py` (was duplicated in 03b + verify.py)
- [x] Strengthen real-data tests: assert concrete values instead of just not-None
- [x] Verify all tests pass (264 passed, 6 skipped)

### M3.4: Verification & Quality Assurance

- [x] Build `pipeline/verify.py` — round-trip verification (JSON-LD output vs raw content)
- [x] Verify all regex extractions: 100% precision across all fields
- [x] Identify false negatives: 86 publisher, 2 translator missed by regex
- [x] Build implementation plan for LLM-based enrichment

### M3.5: LLM-based Extraction (Gemini 3.1 Flash Lite)

- [x] Build `pipeline/03b_llm_enrich.py` — LLM metadata enrichment step
- [x] Build `pipeline/lib/llm_extract.py` — Gemini client, Pydantic schema, batch logic
- [x] Test with 5-entry quick test (all correct)
- [x] Test with 20-entry stratified sample (13/13 correct, 0 hallucinations)
- [x] Full LLM run (~3,000 entries, 275 batches, ~$0.33, 0 errors)
- [x] Results: publisher 34.5%→55.6%, location 67.8%→87.5%, translator 35.1%→41.9%, page_count 78.4%→81.6%

### M3.6: Fix LLM extraction issues

- [x] Analyze false positives with sub-agents (publisher, location, translator, page_count)
- [x] Finding: 0 hallucinations — all FPs are encoding comparison artifacts
- [x] Fix: reject mojibake in LLM validation (31 values filtered)
- [x] Fix: page count off-by-one in page range calculation (11 FP → 1 FP)
- [x] Fix: encoding-aware comparison + N/(M)p. summation in verify.py
- [ ] Remaining: ~170 publisher + ~96 location FP (encoding diffs in verification, not real errors)

### M3.7: Improve extraction coverage further

- [ ] Analyze entries still missing publisher (~44%) — which have it in text vs legitimately missing?
- [ ] Analyze entries still missing translator (~58%) — which are translations without detected translator?
- [ ] Investigate the 1 missing entry (not found in any BLOB)
- [ ] Investigate 33 remaining bracket titles
- [ ] Update `data.md` with new quality metrics

### M3.8: Manual validation (deferred to after M6)

Manual validation is more effective once entries are visible in the frontend.
Moved to after M6 — validate by browsing entries in the UI.

- [ ] Browse 50+ entries in frontend, stratified by type, language, time period
- [ ] Compare displayed fields against raw wiki content
- [ ] Document accuracy: true positives, false positives, false negatives
- [ ] Fix any systematic extraction errors found

---

## M4: Ontology & Data Model

Design a proper semantic model: Schema.org where possible, `klawiter:` extensions where needed.

### M4.1: Vocabulary analysis

- [ ] Map each of the 16 entry types to closest Schema.org type (Book, Article, Movie, etc.)
- [ ] Identify types without Schema.org equivalent (dramatic-reading, symposium, foreword)
- [ ] Map each field to Schema.org property (name, datePublished, publisher, inLanguage, etc.)
- [ ] Identify fields without Schema.org equivalent
- [ ] Document mapping in `ontology.md`

### M4.2: JSON-LD @context redesign

- [ ] Rewrite `@context` in `pipeline/lib/vocabulary.py`:
  - Use `schema:` for standard properties (name, datePublished, publisher, inLanguage, etc.)
  - Use `klawiter:` only for domain-specific extensions (entryType, timePeriod, contentItems, etc.)
  - Add `dcterms:` for provenance fields (source, identifier)
- [ ] Define `@type` mapping: `klawiter:FictionEntry` → also `schema:Book`, etc.
- [ ] Update `05_to_jsonld.py` to produce new @context
- [ ] Validate output with JSON-LD Playground (https://json-ld.org/playground/)
- [ ] Update tests for new JSON-LD structure

### M4.3: Namespace resolution

- [ ] Create `docs/vocab/index.html` — human-readable vocabulary definition
- [ ] Configure content negotiation or redirect so `klawiter-rescue.github.io/vocab/` resolves
- [ ] Update namespace URL in @context if needed

### M4.4: Update frontend data format

- [ ] Ensure `docs/data/klawiter.json` reflects new field names (if changed)
- [ ] Update frontend JS to use new field names
- [ ] Verify frontend still works

---

## M5: Semantic Enrichment & Reconciliation

Link entities to authority data: Wikidata, GND, VIAF, GeoNames.

### M5.1: Strategy & tooling

- [ ] Decide tooling: OpenRefine reconciliation vs custom Python script vs SPARQL queries
- [ ] Define reconciliation priority: works > persons > places > publishers
- [ ] Document strategy in `reconciliation.md`

### M5.2: Work reconciliation (Wikidata)

- [ ] Extract unique work titles from dataset
- [ ] Query Wikidata for Stefan Zweig works (P50 = Q78491)
- [ ] Match extracted titles against Wikidata labels/aliases
- [ ] Manual review of ambiguous matches
- [ ] Add `schema:sameAs` with Wikidata URIs to matched entries
- [ ] Document coverage: how many works matched

### M5.3: Person reconciliation (GND/VIAF)

- [ ] Stefan Zweig: add GND (118637479), VIAF, Wikidata (Q78491) to dataset metadata
- [ ] Extract unique translator names
- [ ] Reconcile translators against GND/VIAF (batch SPARQL or API)
- [ ] Add authority URIs to matched persons
- [ ] Document coverage

### M5.4: Place reconciliation (Wikidata/GeoNames)

- [ ] Extract unique locations from dataset (~100 cities)
- [ ] Match against Wikidata (P31=Q515) or GeoNames
- [ ] Add `schema:sameAs` or GeoNames URI to location fields
- [ ] Document coverage

### M5.5: Publisher reconciliation (GND/Wikidata)

- [ ] Extract unique publisher names
- [ ] Reconcile against GND (publisher authority) or Wikidata
- [ ] Add authority URIs where matched
- [ ] Document coverage

### M5.6: Pipeline integration

- [ ] Create new pipeline step `07_enrich.py` (or integrate into existing step)
- [ ] Store reconciliation results as JSON mapping files in `data/`
- [ ] Add reconciled URIs to JSON-LD output
- [ ] Update frontend JSON to include authority links
- [ ] Update tests

---

## M6: Frontend Redesign ✅

Redesigned to match Stefan Zweig Digital visual language. See [[design]] and [[user-stories]].

### M6.1: Design & User Stories ✅

- [x] Analyze Stefan Zweig Digital: colors (burgundy/gold/cream), typography, layout
- [x] Create design specification → `knowledge/design.md`
- [x] Create user stories (S1–S20, 3 personas) → `knowledge/user-stories.md`

### M6.2: HTML/CSS/JS Redesign ✅

- [x] Replace Tailwind CDN with custom CSS (SZD palette, serif/sans-serif system)
- [x] 4-view architecture: Overview (category portal), Browse (faceted search), Detail (expandable cards), Statistics
- [x] All UI text in English
- [x] Footer with credits (Klawiter, Notre Dame, SZD)
- [x] 8 JS modules: constants, utils, export, app, home, facets, detail, charts

### M6.3: UX & Features ✅

- [x] Citation export: BibTeX + RIS (correct author logic for primary vs secondary literature)
- [x] JSON-LD export per entry + full dataset download
- [x] Permalink copy to clipboard
- [x] Expandable result cards (inline detail, no separate page)
- [x] Interactive charts with click-to-filter
- [x] Console data logging for verification
- [ ] Linked authority data display (depends on M5)

### M6.4: Stable URIs ✅

- [x] Hash-based scheme: `#entry={page_id}`
- [x] Redirect resolution via redirects map
- [x] Permalink copy button

### M6.5: Performance (deferred)

- [ ] Measure initial load time (~8 MB JSON)
- [ ] Evaluate lazy loading if needed

### M6.6: Accessibility (deferred)

- [ ] WCAG 2.1 AA audit
- [ ] ARIA landmarks and labels

---

## M7: Deployment & Publication

Ship it. Make it citable. Make it findable.

### Tasks

- [ ] Configure GitHub Pages: source = `docs/` on `main` branch
- [ ] Test live deployment: verify all routes, search, data loading
- [ ] Add LICENSE file (choose: CC BY 4.0 for data, MIT for code — or clarify with rights holder)
- [ ] Add CITATION.cff for academic citation
- [ ] Consider Zenodo deposit for DOI
- [ ] Add link from Stefan Zweig Digital to Klawiter bibliography (coordinate with project team)
- [ ] Final README update with live URL and citation info
- [ ] Announce / publish

---

## Dependencies

```
M1 (Knowledge) ──→ M2 (Cleanup) ──→ M3 (Pipeline) ──→ M6 (Frontend) ──→ M3.8 (Validation) ──→ M4 (Ontology) ──→ M5 (Enrichment) ──→ M7 (Deploy)
```

**Revised order** (2026-03-29): M6 (Frontend Redesign) moves before M4/M5. Rationale:
- The pipeline data is stable (264 tests, LLM enrichment done)
- Manual validation (M3.8) is easier in the browser than in JSON files
- Ontology changes (M4) only affect JSON-LD keys, not the display
- Frontend progress is motivating and makes the project tangible

M4/M5 can still happen before M7 — the frontend JS adapts to new field names easily.
