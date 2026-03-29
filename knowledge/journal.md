# Journal

Work diary for the Klawiter Bibliography project. Each session documents what we did, what we learned, what ideas came up, and what's still open.

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
