# Klawiter Bibliography

**Live site: [chpollin.github.io/klawiter-rescue](https://chpollin.github.io/klawiter-rescue/)**

Extraction and structuring of the Stefan Zweig Bibliography (Dr. Randolph J. Klawiter, University of Notre Dame) from a decommissioned MediaWiki database as JSON-LD with a static web frontend.

## Status

| Metric | Value |
|--------|-------|
| Extracted entries | 6,295 / 6,296 (99.98%) |
| Mojibake fixed | 61.1% → 0% |
| Entity types | 16 classified (incl. redirect), 0.1% "other" |
| Field coverage (title) | 100% |
| JSON-LD | Schema.org + Dublin Core + `klawiter:` vocabulary blend |
| Frontend | Static site (GitHub Pages), Stefan Zweig Digital design language |

Two entry counts appear throughout: **6,296** = bibliography pages in MediaWiki namespace 0 (the source corpus); **5,179** = non-redirect entries across all namespaces in the frontend JSON (`docs/data/klawiter.json`), of which 4,751 namespace-0 entries are displayed in the UI. The full JSON-LD dataset (`data/output/klawiter.jsonld`) additionally carries 1,546 redirect entries, for 6,725 total records.

## Project Structure

```
pipeline/               Python pipeline (8 steps, standard library; optional LLM step needs extras)
docs/                   Frontend (GitHub Pages) — static HTML/JS/CSS
  js/                   JS modules (app, home, facets, detail, explore-*, export, pages, edit, …)
  css/styles.css        Custom CSS (Stefan Zweig Digital design language)
data/
  raw/                  MediaWiki SQL dump + 8 BLOB files
  intermediate/         Pipeline intermediate steps (CSV, gitignored)
  output/               JSON-LD full dataset + individual files
knowledge/              Project documentation (Obsidian vault)
```

## Pipeline

```
data/raw/zt_00–07 + zweig_part_01.sql
  ↓ 01_extract.py        SQL dump + BLOB parsing without MySQL
  ↓ 02_fix_encoding.py   Mojibake repair (Latin-1 → UTF-8)
  ↓ 03_parse_entries.py   Wiki markup → structured fields
  ↓ 03b_llm_enrich.py    LLM metadata gap-filling (Gemini 3.1 Flash Lite, optional)
  ↓ 03c_normalize.py     Auditable normalization (location/publisher/translator/pageCount)
  ↓ 04_classify.py       Entity type + time period classification
  ↓ 05_to_jsonld.py      JSON-LD conversion
  ↓ 06_validate.py       Quality report
```

### Running

```bash
# Full pipeline
python pipeline/run_pipeline.py

# From step 3
python pipeline/run_pipeline.py 3

# Steps 2 to 4
python pipeline/run_pipeline.py 2 4
```

### Requirements

- Python 3.10+
- Standard library only for the core steps; the optional step 03b needs `google-genai` and `pydantic`
- Source files in `data/raw/` (zt_00–07, zweig_part_01.sql)
- Optional: `GEMINI_API_KEY` in `.env` for step 03b

## Output

| File | Description |
|------|-------------|
| `data/output/klawiter.jsonld` | Full JSON-LD dataset (6,725 records incl. 1,546 redirects, ~12 MB) |
| `data/output/entries/*.jsonld` | Individual files per entry |
| `data/output/quality-report.json` | Validation results |
| `docs/data/klawiter.json` | Frontend JSON (5,179 non-redirect entries, ~9 MB) |

## Data Model

Output is **JSON-LD** using a vocabulary blend of [Schema.org](https://schema.org/), [Dublin Core](https://www.dublincore.org/), and a domain-specific `klawiter:` namespace for types and provenance that the standard vocabularies do not cover (e.g. `dramatic-reading`, `symposium`, MediaWiki source IDs). Each of the 16 entry types maps to a Schema.org type (`Book`, `Article`, `Play`, `Movie`, …). The `klawiter:` namespace is documented at [`docs/vocab/`](docs/vocab/index.html) (live: [chpollin.github.io/klawiter-rescue/vocab/](https://chpollin.github.io/klawiter-rescue/vocab/)), and the `@context` plus an interactive compact/expanded/triples view are available in the JSON-LD Playground on the live site.

## Provenance and Curation

Every tracked field carries where its value came from, and the record keeps the trail from machine extraction through human verification.

**Production provenance.** Each entry in `docs/data/klawiter.json` has a `_provenance` object labelling publisher, location, translator and pageCount as `regex` (rule-based extraction), `llm` (Gemini gap-fill under anti-hallucination constraints) or `missing` (no value extracted). The labels come from `pipeline/inject_provenance.py`, which diffs the regex output against the LLM cache, so a cached value that the gap-fill merge never used is not counted as LLM-produced.

**Verification provenance.** The Expert-in-the-Loop editor (`docs/js/edit.js`, localhost-gated) types every interaction as Accept, Correct or Add. After an Accept or Correct the field's provenance moves to `editor` and the entry gains a `review` block (`approved` for human review, `agent_verified` for an automatic check), so the label says both how the machine produced the value and that a person confirmed it. `pipeline/build_triage.py` condenses the committed `verify.py` and `census.py` reports into `docs/data/triage.json`, which ranks the per-entry checking hints from the census anomaly down to the empty field.

**Correction history.** Edits leave the editor as a `patchVersion: 2` JSON patch document; nothing is written into the dataset from the browser. Approved patches live under `data/corrections/`, where the git history of the folder is the audit trail. `pipeline/apply_patches.py` replays them as the final overlay, moving the field's provenance to `editor` and preserving the machine original in an `edit_history` record. The store is authoritative, so the overlay is idempotent and a fresh pipeline run never silently overwrites an editor value. `.github/workflows/validate-patch.yml` checks patch files on pull requests with the same validator the overlay uses.

## Frontend

Static site under `docs/` (GitHub Pages), visually aligned with Stefan Zweig Digital:

- **Overview**: Category portal with tiles grouped by Works / Reception / Editions
- **Browse**: Full-text search (FlexSearch) + faceted filtering (type, language, period, location)
- **Detail**: Expandable cards with SZD-style metadata table, conditional sections
- **Explore**: Interactive D3.js visualization with 3 modes — Timeline (Bars/Sparklines/Ranks by language), Geography (interactive globe/flat map with Wikidata-linked locations), Connections (force-directed graph of cross-references)
- **Export**: BibTeX, RIS, JSON-LD per entry + full dataset download
- **Content Pages**: About, Methodology, Help, Data Access, JSON-LD Playground, Imprint
- No framework, no build step; search, visualization libraries and fonts are vendored under `docs/vendor/` and `docs/fonts/`, so the page loads without an external request

## Documentation

The `knowledge/` folder is an Obsidian vault with full project documentation:
project context, data model, pipeline, architecture decisions, ontology, frontend design, exploration interface, testing strategy, project journal, references.

## Credits

The bibliography was compiled by **Dr. Randolph J. Klawiter** (University of Notre Dame) over decades. It covers 6,296 entries on Stefan Zweig's work — first editions, translations, secondary literature, film adaptations, correspondence — in over 40 languages.

This project is connected to [Stefan Zweig Digital](https://stefanzweig.digital/) at the Stefan Zweig Centre Salzburg (University of Salzburg).

## Citation

If you use this dataset or software, please cite it. Machine-readable citation metadata is provided in [`CITATION.cff`](CITATION.cff) (GitHub renders a "Cite this repository" button in the sidebar). It credits Dr. Randolph J. Klawiter (University of Notre Dame) as the bibliography's compiler and Christopher Pollin (University of Graz) for the digital edition, and links the repository and live site.

## Licence

- **Code** (pipeline, frontend): [MIT](LICENSE).
- **Documentation, knowledge documents, and the structured digital edition (JSON-LD dataset)**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Underlying bibliography**: the source bibliography was compiled at the University of Notre Dame; when reusing the data, credit the source compilation as described under Credits and Citation above.

See [LICENSE](LICENSE) for the code licence.
