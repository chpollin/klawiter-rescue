---
title: Journal
aliases: [work diary, sessions]
tags: [journal]
created: 2026-03-29
updated: 2026-06-12
---

# Journal

Work diary for the Klawiter Bibliography project. Each session documents what we did, what we learned, what ideas came up, and what's still open.

---

## 2026-06-21 — Session 17: Record Census + EIL Editing Design (Forschungsleitstelle-Lane)

Portfolio-Runde der Forschungsleitstelle, Lane klawiter-rescue. Operator-Auftrag mit zwei Straengen: die Datenintegritaet vom SQL-Quelldump bis ins Frontend verifizieren, und parallel den Ausbau des In-Tool-Editierens fuer die Expert-in-the-Loop-Kontrolle entwerfen.

**Datenintegritaet (Strang 1)**

- `pipeline/census.py` gebaut: reproduzierbare Record-Rekonziliation ueber drei Schichten (`01_extracted.csv` -> `klawiter.jsonld` -> `klawiter.json`), Report nach `data/output/census-report.json`. Fuenf Identitaeten, alle PASS: JSON-LD 1:1 mit Quelle (6.725/6.725, kein Verlust, kein erfundener Datensatz, keine Dublette); Frontend = JSON-LD minus 1.546 Redirects = 5.179; ns0 6.296 = 4.751 angezeigt + 1.545 Redirects; genau 1 leere bibliografische Seite == genau 1 namenloser angezeigter Eintrag.
- Die offene Frage aus Session 1 ("The 1 missing entry") abschliessend geklaert. page_id 2979 ("A unidade espiritual do mundo"): Revisionsgeschichte-Trace zeigt drei Revisionen, die letzte (rev 18324, page_latest) mit `rev_len = 0` — die Seite wurde drei Minuten nach Anlage geblankt. Nur zwei Kategorie-Stub-Revisionen ueberleben in den BLOBs. Kein Pipeline-Fehler, sondern quellseitiger Verlust; bibliografischer Inhalt wurde nie im Dump erhalten. Der Titel steht in der `zweig_page`-Tabelle.
- Die anderen drei leeren Seiten sind nicht-bibliografisch (CSS-Systemseite, leere armenische Kategorie, Bildbeschreibung), also irrelevant fuer die Bibliografie.

**EIL-Editier-Design (Strang 2)**

- `knowledge/eil-editing.md`: Zielentwurf fuer den Ausbau von `edit.js`. Editierbereich auf alle adjudizierbaren Felder, drei getypte Aktionen Accept/Correct/Add (EQUALIS-Triade), Unsicherheits-Oberflaeche gespeist aus Provenance-Badges + verify.py-Flags + Census-Anomalien, Persistenz in drei Schichten (localStorage, Patch v2 mit Aktionstyp/Zeitstempel/Editor, apply_patches-Pipelineschritt mit neuem Provenance-Zustand `editor`), Nachvollziehbarkeit als EQUALIS-Messsubstrat. Fuenf Build-Inkremente, minimaler naechster Schritt = Inkrement 1.
- DIA-XAI-Anbindung explizit gemacht: die Oberflaeche traegt Frontier- wie lokale Modelle ohne Aenderung, weil der Editor extrahierte Werte unabhaengig vom erzeugenden Modell adjudiziert und der Provenance-Zustand die Methode festhaelt.
- Rueckschreib- und Audit-Schicht implementiert (`pipeline/apply_patches.py` plus 8 Unit-Tests, alle gruen): Overlay-Schritt nach `inject_provenance`, wendet Korrekturen aus dem versionierten Store `data/corrections/` an, setzt Provenance auf `editor`, baut Edit-History pro Feld (Maschinen-Original erhalten), hebt den Review-Status (approved/agent_verified). Idempotent, Store ist autoritativ, leerer Store ist byte-identisches No-Op. Das ist der browser- und gate-unabhaengige Teil von Inkrement 1/4; der Frontend-Code wartet auf Browser-Sichtung.

**Entscheidungen**

- Census als drittes Verifikationswerkzeug neben verify.py (Wert-Korrektheit) und 06_validate.py (Qualitaet); es deckt die bisher unbewiesene Achse Record-Vollstaendigkeit ab.
- 2979 nicht eigenmaechtig gefixt: zeigen-mit-Titel versus ausschliessen ist eine editorische Entscheidung, dem Operator vorgelegt.
- Kein Pipeline-Neulauf in dieser Runde; Output-Regeneration gehoert in einen dedizierten Full-Run-Commit mit der 2979-Entscheidung.

**Offen**: Operator-Entscheidungen zu 2979 und zum Bau der Editier-Inkremente (siehe [[HANDOFF]]).

## 2026-06-12 — Session 16: Full-Codebase Refactoring (Multi-Agent)

### What we did

1. **Four-lane analysis** (parallel Opus agents: pipeline, frontend, tests, docs) producing verified findings with file:line evidence, then two implementation waves on disjoint areas.
2. **Frontend cleanup**: deleted dead `explore-overview.js` (orphaned since Session 14f, would crash on missing `CHART_DIMS.overview`; uncommitted rework discarded, saved as patch in `c:\tmp`), removed its CSS blocks and two unreachable methods (`Explore._renderDetailSummary`, `ExploreTimeline.toggleProvenance`), deleted empty `v2/`. New `utils.topN()` replaces the count-sort-slice pattern at the 4 semantically identical call sites; network filter listener unified with the geography pattern (named handler, removeEventListener, re-entrancy guard).
3. **Pipeline cleanup (behavior-neutral)**: `03c_normalize.py` aligned with the step pattern (config constants, atomic `write_csv`, named thresholds); created missing `publisher_normalize.json` (the publisher variant path was silently a no-op); removed 7 dead imports in `verify.py` and unused proximity parameters in `reconcile_locations.py`; centralized `EXTRACTED_FIELDS` in config.
4. **Test refactoring**: new `tests/test_normalize_unit.py` (26 unit tests for all six 03c functions, written *before* touching 03c). Activated two always-skipping regression tests (`entry_type_distribution` added to baseline; `year_range_sane` now checks the real key). Centralized scattered `KNOWN_*` constants into `known_issues` in `baseline-metrics.json`; tests now load the normalization mapping tables instead of duplicating them. Removed two redundant/obsolete tests. Ratcheted `broken_see_also_refs` 727→622 (real data improvement).
5. **Documentation refactoring**: unified stale numbers everywhere (tests 326/328/397→437, 7→8 steps, Overview→Geography, locations 402→395 = pre-normalization value); resolved the "Wikidata/GND/VIAF out of scope" vs. implemented-reconciliation contradiction (canonical line: LOD linking allowed and implemented, inventing values forbidden); removed the duplicated test taxonomy from pipeline.md (single source: testing.md); README gained Citation and Data Model sections plus entry-count disambiguation; index.md Open Items synced with journal.

### What we learned

- **Numbers drift because they are hardcoded in 2–4 places.** Every stale count (tests, coverage, locations) had a single correct source (baseline-metrics.json, pytest collection, the data itself). The docs now follow a responsibility matrix: numbers live in one file, others link.
- **Always-skipping tests are worse than no tests** — two regression tests suggested coverage that never executed (missing baseline key, wrong report key). Activating them cost three lines each.
- **Deliberately not done**: mojibake regex consolidation, language-list dedup, SQL parser unification — not provably behavior-neutral without a pipeline re-run; documented in the analysis reports instead.

### Numbers

| Metric | Before | After |
|--------|--------|-------|
| Tests collected | 413 (docs said 397) | 437 |
| Dead JS module | 373 LOC | 0 |
| 03c unit coverage | 0 direct tests | 26 |
| Always-skipping regression tests | 2 | 0 |
| broken seeAlso refs baseline | 727 | 622 |
| Test result (non-LLM) | — | 408 passed, 15 pre-existing semantic failures, 10 skipped |

### Follow-up (same day)

6. **Browser smoke test (Playwright)**: all three explore modes render, cross-view filtering works (Leipzig bubble → chip → filtered network community view), 18× rapid tab switching and a filter-toggle storm produced 0 errors (the rebuilt listener holds), deep link + back/forward restore the mode, dead module returns 404. One expected console warning (stub page_id 2979).
7. **`locationSameAs` implemented** (Session 15 follow-up): step 05 loads `locations.json` and emits `klawiter:locationSameAs` (`@type: @id`, Wikidata entity URI) for the primary location — 4,013 of 4,162 located non-redirect entries (~96%). Pipeline re-run 05→06→inject_provenance, diff-verified: no other changes. Detail view renders a discreet Wikidata link; vocab page and ontology.md document the property.
8. **22 unmatched locations triaged** into `data/output/unmatched_locations_review.md` (editor review template): 17 match candidates (e.g. T'aipei→Q1867, Lannuon→Q207581), 3 ambiguous two-place strings, 1 mojibake (RĀ«ga→Riga via location_normalize.json), 1 genuinely ambiguous (Saint-Aignan). Noted: apostrophe encoding differs between klawiter.json (U+2019) and locations.json (U+0027) — relevant for any mapping work.

### What's next

- EIL verification workflow (DIA-XAI deliverable) as the next major work package
- Editor review of `unmatched_locations_review.md` (Accept/Correct decisions are domain calls)
- Fill `publisher_normalize.json` with real variant mappings via the editor loop

---

## 2026-04-12 — Session 15: Geography, Timeline Modes, Normalization, Wikidata

### What we did

1. **Geography view (L2, 816 LOC)**: Orthographic globe (`d3.geoOrthographic`) with flat map toggle (`d3.geoNaturalEarth1`), drag-to-rotate, scroll-to-zoom. Semantic zoom at 2× base scale: ~82 country-aggregated bubbles (zoom-out) → ~366 city bubbles (zoom-in). Click dims non-selected to 0.35 opacity with filter chip + cross-view event. Interactive legend, animated decade playback, city labels at zoom, improved ocean/land contrast.
2. **Wikidata reconciliation**: `reconcile_locations.py` (293 LOC). Two-phase: Reconciliation API (en + de endpoints) → SPARQL metadata enrichment. 360/382 locations matched (94.2%). `locations.json` enriched with `wikidataId`, `wikidataLabel`, `wikidataScore`, `countryQid`. 22 unmatched logged in `locations_reconciliation_log.json`. 6 tests against 20-entry ground truth.
3. **Timeline modes (L1)**: Three visualization modes: Bars (default, decade-aggregated when >50-year extent), Sparklines (small multiples per language/type with individual Y-scales), Ranks (bump chart showing language rank per decade). Stream mode removed — `curveBasis` smooths discrete data, `stackOffsetWiggle` removes baseline, no analytical value (Cleveland & McGill 1984).
4. **URL state persistence**: Hash-based state encoding: `#stats/timeline?years=1920-1940&chart=sparklines&language=German`. `replaceState` for brush updates, `pushState` for tab switches, `popstate` listener for back/forward. `_lastHash` guard prevents double-processing.
5. **Global provenance toggle**: `Explore.filters.showProvenance` checkbox in filter chips, persists across tab switches via URL state.
6. **Pipeline 03c normalization** (187 LOC): Auditable normalization via external mapping tables. Location variants (7 mappings, 45 entries), publisher garbage rejection (regex patterns, 160 entries), translator cleanup (mojibake + suffix stripping, 193 entries), pageCount outlier rejection (>2000 and year-like, 12 entries). 5 regression tests.
7. **Systematic field profiling**: All 8 data fields profiled for normalization candidates.

### What we learned

- **Country codes were missing entirely** — semantic zoom in geography was an empty shell until all 382 locations were geocoded with ISO Alpha-2 country codes. Wikidata reconciliation solved this and provided LOD-linkable Q-IDs as a bonus.
- **Stream visualization was analytically weak** — curveBasis interpolation smooths discrete yearly counts into false continuity, stackOffsetWiggle removes the meaningful zero baseline. Bars + Sparklines + Ranks serve the three research questions better: total comparison (Bars), individual trends (Sparklines), relative dominance shifts (Ranks).
- **Normalization must be a separate pipeline step** — mixing extraction and cleanup in 03_parse_entries.py made both harder to test. Step 03c with external config files (JSON) is auditable and doesn't violate the Data Integrity Principle.
- **Publisher coverage drops are correct** — 55.5% → 52.2% because garbage (edition numbers, metadata strings) was removed, not because valid publishers were lost.

### Numbers

| Metric | Before | After |
|--------|--------|-------|
| Timeline LOC | 288 | 746 |
| Geography LOC | 0 | 816 |
| explore.js LOC | 484 | 567 |
| Pipeline steps | 7 (01–06 + verify) | 8 (+ 03c normalize) |
| Wikidata matches | 0/382 | 360/382 (94.2%) |
| Publisher coverage | 55.5% | 52.2% (garbage removed) |
| Translator cleaned | — | 193 entries |
| Tests | 317 | 328 |

### What's next

- Browser-test all new features (Sparklines, Ranks, Globe/Flat toggle, semantic zoom)
- 22 unmatched locations: manual review
- `locationSameAs` field with Wikidata URIs in JSON-LD output
- L3 Connections: status update needed
- Multi-edition decomposition (LLM-based, separate project)

---

## 2026-04-12 — Session 14f: Timeline Redesign

### What we did

1. **Timeline rewrite**: Stacked area → stacked bars. Discrete bibliographic data represented as bars per year, not interpolated curves. Full-width layout (detail panel only on selection).
2. **Layer toggle**: "by Language" (default) or "by Type" showing 16 entry types as stacked bar layers.
3. **Provenance overlay**: Toggle shows per-year ratio of regex/LLM/missing provenance as semi-transparent layer.
4. **Semantic zoom**: X-axis adapts to brush extent: decades (>80 years) → 5-year ticks (30–80) → individual years (<30). Data aggregation: decade bars (>50 years) → year bars (<50 years).
5. **5 annotations**: Born 1881, WWI 1914, Exile 1933, WWII 1939, Death 1942. Collision avoidance for overlapping labels.
6. **Brush cross-view events**: `explore:filterChange` custom event on `document`, consumed by Geography and Connections views.
7. **Overview mode removed**: Tab, panel, script tag, setMode handler, CHART_DIMS constant — all deleted. Three modes remain: Timeline, Geography, Connections.
8. **Dead code cleanup**: Removed `_drawLegend()`, duplicate filter chip.

### What we learned

- **Stacked area was wrong for this data** — bibliographic entries are discrete counts per year, not continuous flows. Bars represent the data honestly.
- **Overview was redundant** — the Timeline with layer toggle + semantic zoom covers what Overview's small multiples showed, with better interaction (brush, cross-view events).
- **Provenance overlay works as Developer-in-the-Loop tool** — shows immediately where data quality varies over time (pre-1900 entries have more missing fields).

### Numbers

| Metric | Before | After |
|--------|--------|-------|
| Timeline LOC | 288 | 496 |
| Explore.js LOC | 484 | 567 |
| Visualization modes | 4 (Timeline, Overview, Geography, Connections) | 3 (Timeline, Geography, Connections) |
| Annotations | 3 (Born, Exile, Death) | 5 (+ WWI, WWII) |

### What's next

- Add more visualization modes (Sparklines, Ranks) → Session 15
- Browser-test layer toggle and provenance overlay

---

## 2026-04-12 — Session 14: Semantic Testing, Extraction Fixes, Pipeline Limits

### What we did

1. **Frontend data verification**: Added `_meta` block to `klawiter.json` (pipeline-generated baseline), replaced verbose `logDataSummary()` with compact `verifyData()` in app.js, injected `_provenance` data (43.1% regex, 11.8% LLM, 45.3% missing).
2. **10-entry wiki verification**: Compared 10 strategically selected entries against the live wiki at klawiter.stefanzweig.digital. Found 23% of fields wrong, 12% problematic. Root cause: multi-edition wiki pages.
3. **Semantic testing layer**: Created `test_semantic.py` (70 tests, 10 entries x 7 fields) and `test_heuristic.py` (6 pattern-based validators on all 4,751 entries). Ground truth in `tests/wiki_ground_truth.json`.
4. **5 extraction fixes**: Title fallback to page_title (1,368 section headers → 0), PageCount `N/(M)p.` pattern + parenthesized lookahead fix, Publisher markup cleanup + metadata rejection.
5. **Encoding guard**: If page_title has encoding artifacts AND extracted title was only rejected for length (not section header), keep the extracted title.
6. **Documentation**: Updated all knowledge docs, added multi-edition limitation to pipeline.md.

### What we learned

- The pipeline is at the **natural limit of regex-based extraction**. Further regex fixes shift problems (wrong value A → wrong value B) rather than solving them.
- **427 multi-edition pages** (6.8%) cause systematic extraction errors. The pipeline treats each page as one flat entry, but Klawiter's bibliography uses pages as containers for multiple publications.
- **page_title** (MediaWiki metadata) is more reliable than extracted titles. The fallback was the highest-impact fix.
- **Semantic tests** are the most valuable addition — they quantify what's wrong and prevent regressions.

### Numbers

| Metric | Before | After |
|--------|--------|-------|
| Section-header titles | 1,368 | 0 |
| Markup in titles | 7 | 0 |
| Publisher markup | 20 | 0 |
| Publisher metadata | 10 | 0 |
| Year-as-pageCount | 27 | 11 |
| Redirects resolved | 430 | 1,210 |
| Broken seeAlso | 1,140 | 727 |
| Tests | 326 | 392 |
| Semantic accuracy | n/a | 53/70 (76%) |

### What's next

- Expand ground truth from 10 to 30+ entries (stratified by type/language)
- Browse the frontend systematically to find remaining issues
- Consider LLM-based edition-block segmentation for multi-edition pages (separate project)
- WCAG 2.1 AA audit, performance measurement

---

## 2026-04-12 — Session 15: Timeline Modes, Pipeline Normalization, Data Analysis

### What we did

1. **Timeline visualization overhaul**: Replaced Bars/Stream toggle with three analytically grounded modes: Bars (decade-aggregated at full extent), Sparklines (small multiples per language — addresses Forschungsfrage 2 via individual baselines, Cleveland & McGill 1984), Ranks (bump chart showing language rank per decade). Stream mode removed (curveBasis smoothed discrete data, stackOffsetWiggle removed baseline, no analytical advantage).
2. **Global provenance toggle**: Moved from Timeline-local to `Explore.filters.showProvenance`. Checkbox in shared filter chips area, persists across tab switches.
3. **URL hash state persistence**: Full explore state encoded in URL (`#stats/timeline?years=1920-1940&chart=sparklines`). replaceState for brush, pushState for tab switches, popstate listener for back/forward, _lastHash guard against double-processing.
4. **Pipeline step 03c (normalization)**: New step with auditable mapping tables in `pipeline/data/`. Location variant mapping (7 rules, 45 entries), publisher garbage rejection (8 patterns, 160 entries), translator mojibake fix + afterword/foreword suffix stripping (193 entries), pageCount outlier rejection (12 entries).
5. **Systematic data profiling**: Analyzed all 8 fields for normalization issues. Found publisher critically broken (1,616 variants, 81% singletons, 245 garbage), translator has 3 distinct problems (mojibake, multi-person, non-person content), location has 5 fixable variant groups.
6. **5 normalization tests** with bounded thresholds.

### What we learned

- **Stacked charts cannot answer language comparison questions** — non-adjacent layers share neither baseline nor top. Small multiples and bump charts are structurally better encodings for this data.
- **Decade aggregation** at full extent (21 bars instead of 140) is the single most impactful readability improvement.
- **Publisher normalization is the largest remaining data quality problem** — but clustering 1,316 singletons requires manual review, not automation.
- **Normalization as a separate pipeline step** (03c) keeps extraction and standardization as distinct responsibilities with auditable mapping tables.

### Numbers

| Metric | Before | After |
|--------|--------|-------|
| Timeline modes | Bars + Stream | Bars + Sparklines + Ranks |
| Publisher coverage | 55.5% | 52.2% (160 garbage removed) |
| PageCount coverage | 53.5% | 53.3% (12 outliers removed) |
| Locations normalized | — | 45 (7 variant mappings) |
| Translators cleaned | — | 193 (mojibake + suffixes) |
| Tests | 392 | 397 |

### What's next

- Browser-test Sparklines and Ranks modes (only Bars confirmed via screenshot)
- Publisher clustering (1,316 singletons → ~300 canonical forms, requires manual review)
- Language detection for Film/Symposium/Translation entries (0% coverage)
- seeAlso resolution (155 broken references)

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
