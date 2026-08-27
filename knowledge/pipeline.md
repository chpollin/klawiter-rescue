---
title: Production Pipeline
aliases: [pipeline, extraction, transformation, production runner]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: complete
language: en
version: 1.1
tags: [pipeline, reproducibility, provenance]
created: 2026-03-29
updated: 2026-08-27
authors: [Christopher Pollin]
related: [data, testing, frontend, production-readiness]
---

# Production Pipeline

## Execution

The pinned environment and the complete production run are established with the following commands:

```bash
python -m pip install uv==0.12.5
python -m uv sync --locked
python -m uv run python pipeline/run_pipeline.py
```

The default run uses the versioned LLM cache, requires no API key and executes no network request. `--llm-mode off` disables the frozen enrichment. `--llm-mode live` is an explicit recomputation with `GEMINI_API_KEY`; its working cache becomes productive only after review and adoption into `data/provenance/`.

Partial ranges are selected via stage identifiers:

```bash
python -m uv run python pipeline/run_pipeline.py --from-stage 03 --to-stage gate2 --no-postprocess
```

The runner terminates on the first error. Paths come exclusively from `pipeline/lib/config.py`.

## Stages

| Stage | Input | Task | Main output |
|---|---|---|---|
| `01` | SQL and BLOBs | extract pages, slots and text addresses | `01_extracted.csv` |
| `01v` | dump and extract | enforce row identity dump = extract (stage 01 census, hard failure) | census check |
| `02` | extracted texts | repair UTF-8-as-Latin-1 mojibake | `02_encoding_fixed.csv` |
| `03` | repaired texts | parse wiki markup and bibliographic fields | `03_parsed.csv` |
| `03b` | parse result, frozen cache | fill missing fields only | `03b_llm_enriched.csv` |
| `03c` | enriched values | normalize values and discard inadmissible values | `03c_normalized.csv` |
| `04` | normalized values | classify entry types and periods | `04_classified.csv` |
| `gate1` | classified source, modelling decisions | produce work/edition graph and queue | `data/output/editions/` |
| `gate1v` | Gate 1 artifacts | check schema, selectors, IDs, queue and determinism | validation and EARL |
| `gate2` | Gate 1, location data, SZD index, decisions | produce candidates, claims and publishable links | `data/output/reconciliation/` |
| `05` | classified data, publishable links | produce JSON-LD and frontend data | `klawiter.jsonld`, `klawiter.json` |
| `06` | JSON-LD | produce schema and quality report | `quality-report.json` |

Thereafter follow round-trip verification, census, provenance projection, triage, patch replay, the generation of the dereferenceable vocabulary term pages together with the index page (both deterministic from the term register `docs/vocab/klawiter.ttl`, grouped by its banner sections) and the final Gate 2 check.

## Extraction and Encoding

Stage 01 reads MediaWiki tables and external text stores directly. A database server is not required. The extractor preserves page, text and BLOB IDs so that every later statement can be traced back to the source.

Stage 02 repairs known mojibake sequences section by section and idempotently. The repair is adopted only where the byte sequence validates as UTF-8. Deliberately present Unicode characters stay unchanged.

Stage 03 combines structural wiki parsing and evidence-bound patterns. With bold-set edition headers such as `[1939]` or `[ca. 1965]`, the MediaWiki page title stays authoritative; the header is not emitted as a work title. Empty source pages keep their page title as a stub.

## Frozen Enrichment

Stage 03b fills empty fields only. It overwrites no parser value. The production cache contains result, source identifier and model provenance. The output is checked again for type, occurrence and encoding. The separate local working cache is not part of the reproducible input.

Stage 03c normalizes places of publication, translators and pagination. It discards values whose form or value range violates the documented contract. Lower coverage is admissible where it removes an undocumented statement.

## Gate 1: Segmentation

`pipeline/lib/editions.py` selects the 443 multi-edition pages via the ratified header schema. Each block begins at an edition header and ends at the next header or at the end of the page. `pipeline/segment_editions.py` produces works, editions, exact text selectors, annotations, documented carriers and statement states.

The 76-case sample was reviewed by two independent agents and reconciled by an independent stronger verification agent. Corrections and the open adaptation case are held under `data/reconciliation/edition-modeling-decisions.json`. No uncertain case is confirmed automatically.

## Gate 2: Reconciliation

`pipeline/lib/reconciliation.py` forms candidates from four frozen sources, historical location candidates, independent location review, the SZD work index and the Wikidata comparison for translator and publisher names (`data/provenance/agent-reconciliation.json`, threshold five occurrences). Decision inputs under `data/reconciliation/` stay separate from these. The refreezing tools `reconcile_locations.py` and `reconcile_agents.py` contact the network only with the explicit switch `--i-am-refreezing`; the production run stays network-free.

The publication rule reads as follows. Only a documented `confirm` or `correct` decision produces a relation in `publishable-links.json`. `unresolved` produces a source-bound `klawiter:ContestedClaim`. `reject` preserves the negative decision, yet publishes no link.

Source occurrences are documented from `04_classified.csv` with page ID, text ID, line number, exact text and SHA-256. Multi-part location values use a documented component-set match. The same scan collects the occurrences of translator and publisher names via the field carrying the name, and names the field name in every occurrence; the Gate 2 check requires, for every agent subject with a candidate, either an occurrence or a spelled-out null finding. New curation patches replace no history; the previous decision is preserved in `supersedes`.

## Export and Interface

Stage 05 adopts from Gate 2 exclusively confirmed links. The flat JSON-LD file contains all 6,725 records. The frontend file removes redirects and adds a redirect map. `inject_provenance.py` adds field provenance from exactly the selected LLM mode.

`docs/data/reconciliation.json` is a deterministic projection of candidates, decisions, open claims and edition claims. Run timestamps are held only in audit and manifest artifacts and do not alter this public data file.

## Patch Replay

`pipeline/apply_patches.py` applies released field corrections from `data/corrections/`. Reconciliation patches are read in during the Gate 2 rebuild. Both patch kinds validate version, subject, action, evidence and permitted fields. The production run thereby stays fully reconstructible from source holdings and decisions.

## Repeatability

Gate 1 and Gate 2 rebuild their core documents inside the validators and compare the results. In addition, two complete production runs were executed with identical SHA-256 for the edition graph, both queues, all reconciliation core documents and the flat JSON-LD holdings. The UI reconciliation projection is likewise byte-identical across separate rebuilds.

Time-dependent fields are limited to manifests, PROV activities, EARL reports and run audits. They document the time of execution and are not part of the deterministic data core.

## Limits

- Four source pages have no delivered text body; one of them is bibliographic.
- The flat holdings stay structurally imprecise for 443 multi-edition pages.
- 19 entries without a parser value have no LLM result in the frozen cache.
- Live enrichment is deliberately not a component of the default run.
- External expert review can extend the agentic evidence, yet does not change the technical repeatability.

The current results and Operator Points are held in [[production-readiness]], the check commands and the limits of what is asserted in [[testing]].
