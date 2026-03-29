# Journal

Work diary for the Klawiter Bibliography project. Each session documents what we did, what we learned, what ideas came up, and what's still open.

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
