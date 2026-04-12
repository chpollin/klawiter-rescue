# Klawiter Bibliography

**Live site: [chpollin.github.io/klawiter-rescue](https://chpollin.github.io/klawiter-rescue/)**

Extraction and structuring of the Stefan Zweig Bibliography (Dr. Randolph J. Klawiter, University of Notre Dame) from a decommissioned MediaWiki database as JSON-LD with a static web frontend.

## Status

| Metric | Value |
|--------|-------|
| Extracted entries | 6,295 / 6,296 (99.99%) |
| Mojibake fixed | 61.1% → 0% |
| Entity types | 16 classified (incl. redirect), 0.1% "other" |
| Field coverage (title) | 100% |
| JSON-LD | Schema.org + Dublin Core + `klawiter:` vocabulary blend |
| Frontend | Static site (GitHub Pages), Stefan Zweig Digital design language |

## Project Structure

```
pipeline/               Python pipeline (7 steps, no external dependencies)
docs/                   Frontend (GitHub Pages) — static HTML/JS/CSS
  js/                   13 JS modules (app, home, facets, detail, explore-*, export, pages, edit, …)
  css/styles.css        Custom CSS (Stefan Zweig Digital design language)
data/
  raw/                  MediaWiki SQL dump + 8 BLOB files (363 MB)
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
- No external dependencies (standard library only)
- Source files in `data/raw/` (zt_00–07, zweig_part_01.sql)
- Optional: `GEMINI_API_KEY` in `.env` for step 03b

## Output

| File | Description |
|------|-------------|
| `data/output/klawiter.jsonld` | Full dataset (6,296 entries, ~8 MB) |
| `data/output/entries/*.jsonld` | Individual files per entry |
| `data/output/quality-report.json` | Validation results |
| `docs/data/klawiter.json` | Frontend JSON (5,179 entries, ~9 MB) |

## Frontend

Static site under `docs/` (GitHub Pages), visually aligned with Stefan Zweig Digital:

- **Overview**: Category portal with tiles grouped by Works / Reception / Editions
- **Browse**: Full-text search (FlexSearch) + faceted filtering (type, language, period, location)
- **Detail**: Expandable cards with SZD-style metadata table, conditional sections
- **Explore**: Interactive D3.js visualization with 3 modes — Timeline (stacked area by language), Overview (linked small multiples with cross-filtering), Connections (force-directed graph of cross-references)
- **Export**: BibTeX, RIS, JSON-LD per entry + full dataset download
- **Content Pages**: About, Methodology, Help, Data Access, Imprint
- No framework, no build step

## Documentation

The `knowledge/` folder is an Obsidian vault with full project documentation:
project context, data model, pipeline, architecture decisions, ontology, frontend design, exploration interface, testing strategy, project journal, references.

## Credits

The bibliography was compiled by **Dr. Randolph J. Klawiter** (University of Notre Dame) over decades. It covers 6,296 entries on Stefan Zweig's work — first editions, translations, secondary literature, film adaptations, correspondence — in over 40 languages.

This project is connected to [Stefan Zweig Digital](https://stefanzweig.digital/) at the Stefan Zweig Centre Salzburg (University of Salzburg).

## License

- **Code** (pipeline, frontend): [MIT License](LICENSE)
- **Data** (bibliographic dataset): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

See [LICENSE](LICENSE) for details.
