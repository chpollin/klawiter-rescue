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
- [ ] Commit all M1+M2 changes

---

## M3: Pipeline Refactoring & Testing

Harden the extraction pipeline: eliminate code duplication, add comprehensive tests, improve weak extraction patterns.

### M3.1: Baseline — Capture current output

- [ ] Run full pipeline, save checksums of all intermediate CSVs and final klawiter.jsonld
- [ ] Save 50 representative entries (diverse types, languages, edge cases) as golden test fixtures

### M3.2: Config consolidation

- [ ] Make all 6 scripts import paths from `pipeline/lib/config.py` — remove local `PROJECT_ROOT`, `INPUT_PATH`, `OUTPUT_PATH` definitions
- [ ] Remove redundant `csv.field_size_limit()` calls from scripts 02–05 (already set globally in config.py)
- [ ] Make all scripts use `config.setup_logging()` instead of local `logging.basicConfig()`
- [ ] Verify pipeline output matches baseline checksums

### M3.3: Test infrastructure

- [ ] Create `tests/` directory with `conftest.py` (shared fixtures: sample entries, known-good extractions)
- [ ] Write unit tests for `lib/patterns.py` — test each extraction function with known inputs/outputs:
  - [ ] `extract_year` — normal years, edge cases (page numbers like 1234), no-year entries
  - [ ] `extract_publisher` — all 3 pattern families, international publishers, false negatives
  - [ ] `extract_location` — known cities, multi-location entries, locations not in list
  - [ ] `extract_page_count` — "432 p.", "pp. 9-86", "293 Seiten", edge cases
  - [ ] `extract_translator` — all 8 patterns (5 languages), names with particles ("van der Berg")
  - [ ] `extract_language_from_category` — standard categories, edge cases
- [ ] Write unit tests for `lib/wiki_parser.py`:
  - [ ] `parse_redirect` — standard redirects, edge cases
  - [ ] `extract_categories` — single/multiple categories, cleanup
  - [ ] `extract_title` — bold titles, bracket-title rejection, page_title fallback
  - [ ] `extract_see_references`, `extract_reprints`, `extract_translations_block`, `extract_contents_block`
  - [ ] `extract_structured_data` — full entry parsing (3-5 representative entries)
- [ ] Write unit tests for `lib/encoding.py`:
  - [ ] `has_mojibake` — positive/negative detection
  - [ ] `fix_encoding` — known mojibake pairs (ä→Ã¤ etc.), mixed clean/corrupted lines
- [ ] Write integration test: run full pipeline on 50 fixture entries, compare output against golden files
- [ ] Verify all tests pass

### M3.4: Improve extraction coverage

- [ ] Analyze 100 entries where publisher is NULL — identify missing patterns
- [ ] Add publisher patterns: international naming (e.g. Japanese, Arabic publishers), patterns without explicit "Verlag/Press" label
- [ ] Analyze 100 entries where translator is NULL but entry type suggests translation
- [ ] Add translator patterns: non-Latin scripts, abbreviated forms, multi-translator entries
- [ ] Re-run pipeline, measure coverage improvement
- [ ] Update tests for new patterns
- [ ] Investigate the 1 missing entry (not found in any BLOB)
- [ ] Investigate 33 remaining bracket titles — can more be resolved?
- [ ] Update `data.md` with new quality metrics

### M3.5: Manual validation

- [ ] Select 50 entries stratified by type, language, time period
- [ ] Compare extracted title, year, publisher, location against raw wiki content
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

## M6: Frontend Redesign

Align with Stefan Zweig Digital design. Improve UX. Ensure performance.

### M6.1: Design analysis

- [ ] Analyze Stefan Zweig Digital: colors, typography, layout patterns, navigation
- [ ] Create design specification: color palette, font stack, component styles
- [ ] Document in `ui-design.md`

### M6.2: HTML/CSS redesign

- [ ] Replace Tailwind CDN with custom CSS matching Stefan Zweig Digital
- [ ] Redesign header/navigation to match Stefan Zweig Digital branding
- [ ] Redesign entry cards and detail view
- [ ] Redesign dashboard/statistics view
- [ ] Ensure responsive design (mobile/tablet/desktop)
- [ ] Add proper footer with credits, license, links

### M6.3: UX improvements

- [ ] Add citation export (BibTeX, RIS) for individual entries
- [ ] Add linked authority data display (Wikidata/GND links in detail view)
- [ ] Improve search: show result count, better empty states
- [ ] Add breadcrumb navigation
- [ ] Add "About" page with project context and credits

### M6.4: Stable URIs

- [ ] Define URI scheme: `#entry/{page_id}` or path-based with 404.html fallback
- [ ] Ensure every entry has a stable, shareable URL
- [ ] Support old wiki title resolution via redirect map
- [ ] Add `<link rel="canonical">` per entry view

### M6.5: Performance

- [ ] Measure initial load time (4.2 MB JSON)
- [ ] Evaluate: lazy loading, chunked data, or gzip-only approach
- [ ] If needed: split data into index (lightweight) + detail (on-demand)
- [ ] Test on slow connection (3G throttle in DevTools)

### M6.6: Accessibility

- [ ] WCAG 2.1 AA audit: color contrast, keyboard navigation, screen reader labels
- [ ] Add ARIA landmarks and labels
- [ ] Test with screen reader

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
M1 (Knowledge) ──→ M2 (Cleanup) ──→ M3 (Pipeline) ──→ M4 (Ontology) ──→ M5 (Enrichment) ──→ M6 (Frontend) ──→ M7 (Deploy)
                                         ↓                                        ↓
                                    M3 can start              M6 design (M6.1) can start
                                    in parallel               in parallel with M4/M5
                                    with M1/M2
```

M1+M2 are quick (documentation). M3 is the foundation and must be solid before M4. M4 determines the data structure for M5. M6 design work (M6.1) can happen in parallel with M4/M5, but implementation (M6.2+) depends on finalized data model. M7 is the final step.
