# Pipeline

Extracts bibliographic metadata from raw MediaWiki dumps into structured JSON-LD.

## Steps

| Step | Script | Description |
|------|--------|-------------|
| 01 | `01_extract.py` | Parse SQL dump + BLOBs → raw CSV |
| 02 | `02_fix_encoding.py` | Fix Mojibake (UTF-8 misread as Latin-1) |
| 03 | `03_parse_entries.py` | Extract metadata via regex (title, year, publisher, location, translator, page count, categories) |
| 03b | `03b_llm_enrich.py` | Fill extraction gaps via Gemini 3.1 Flash Lite *(optional)* |
| 04 | `04_classify.py` | Assign entry types + time periods |
| 05 | `05_to_jsonld.py` | Convert to JSON-LD + frontend JSON |
| 06 | `06_validate.py` | Quality report |
| — | `verify.py` | Round-trip verification (output vs. raw content) |
| — | `build_triage.py` | Reduce verify + census reports to `docs/data/triage.json` (EIL attention hints) |

## Usage

```bash
python run_pipeline.py          # all steps
python run_pipeline.py 3 6      # steps 3–6
python verify.py                # verification report
python build_triage.py          # regenerate docs/data/triage.json after verify/census
```

## Step 03b: LLM Enrichment

Requires `google-genai` and a Gemini API key:

```bash
pip install google-genai
echo "GEMINI_API_KEY=your-key" > .env   # in project root
```

- Model: `gemini-3.1-flash-lite-preview`
- Processes ~3,000 entries with missing fields (batches of 10)
- Structured JSON output via Pydantic schema
- Only fills empty fields — never overwrites regex results
- Cache in `data/intermediate/03b_llm_cache.json` for resume
- Cost: ~$0.33 per full run
- Step 04 auto-detects `03b` output, falls back to `03`

## Modules

| File | Purpose |
|------|---------|
| `lib/config.py` | Paths, CSV I/O, logging |
| `lib/patterns.py` | Regex extraction (year, publisher, location, translator, page count) |
| `lib/wiki_parser.py` | MediaWiki markup parsing (titles, categories, cross-references) |
| `lib/encoding.py` | Mojibake detection and repair |
| `lib/vocabulary.py` | Entry type mapping, language codes, JSON-LD context |
| `lib/llm_extract.py` | Gemini client, Pydantic schema, prompt, batch logic |
