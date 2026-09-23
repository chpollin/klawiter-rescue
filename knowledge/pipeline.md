---
title: Production Pipeline
aliases: [pipeline, extraction, transformation, production runner]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: maintained
language: en
version: 1.1
tags: [pipeline, reproducibility, provenance]
created: 2026-03-29
updated: 2026-09-23
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

Stage 01 reads MediaWiki tables and external text stores directly. A database server is not required. The extractor preserves page, text and BLOB IDs so that every later statement can be traced back to the source. It decodes the page-link titles as UTF-8, which earlier arrived misread as Latin-1 and left every non-ASCII link target unresolvable. It also detects the pages the wiki's Redirect fixer account overwrote, walking back from `page_latest` over the fixer's revisions to the last human revision, and compares the result with `data/reconciliation/source-revision-decisions.json`. A restored page is extracted from that human revision, and any disagreement between detection and decisions stops the run. [Data](data.md#pages-overwritten-by-the-redirect-fixer) holds the rule and the cases.

Stage 02 repairs known mojibake sequences section by section and idempotently. The repair is adopted only where the byte sequence validates as UTF-8. Deliberately present Unicode characters stay unchanged.

Stage 03 combines structural wiki parsing and evidence-bound patterns. With bold-set edition headers such as `[1939]` or `[ca. 1965]`, the MediaWiki page title stays authoritative; the header is not emitted as a work title. The same fallback applies where the first line is a statement rather than a title, meaning a citation of an article in its container, a cross-reference, a credit, an extent, an imprint, an annotation, a label such as "Volume:" or a wiki heading (`NON_TITLE_CLASSES` in `03_parse_entries.py`). The corpus writes quotation marks escaped, so the quoted-title pattern rarely applies, and before this rule every article page carried its full citation as title. Empty source pages keep their page title as a stub.

## Frozen Enrichment

Stage 03b fills empty fields only. It overwrites no parser value. The production cache contains result, source identifier and model provenance. The output is checked again for type, occurrence and encoding: a value that arrived as a Latin-1 or CP1252 misreading of UTF-8 bytes is repaired by the byte round-trip and recorded under `encodingRepairs` in the enrichment report, one the round-trip cannot restore is dropped, and a publisher value stating a contribution credit is refused. `inject_provenance.py` turns each recorded repair into a field-scoped review hint on the entry it reached. The separate local working cache is not part of the reproducible input.

Stage 03c normalizes places of publication, translators and pagination. It discards values whose form or value range violates the documented contract. Lower coverage is admissible where it removes an undocumented statement.

## Gate 1: Segmentation

`pipeline/lib/editions.py` selects the ratified multi-edition corpus via the supported header schema. Since algorithm version 1.3 its header split keeps a place qualifier with its place and divides a co-imprint into publisher/place pairs, the same rule the publication layer applies, so edition nodes such as `54-1981-a` no longer carry a bare country as their place. Each block begins at an edition header and ends at the next header or at the end of the page. `pipeline/segment_editions.py` produces works, editions, exact text selectors, annotations, documented carriers and statement states.

The 76-case sample was reviewed by two independent agents and reconciled by an independent stronger verification agent. Corrections and the adaptation case are held under `data/reconciliation/edition-modeling-decisions.json`, where the adaptation case carries its resolution (decided by the main instance after delegation by the operator on 2026-09-22, revisable). No uncertain case is confirmed automatically, and a decided claim is applied only from a recorded `resolution`.

## Gate 2: Reconciliation

`pipeline/lib/reconciliation.py` forms candidates from four frozen sources, historical location candidates, independent location review, the SZD work index and the Wikidata comparison for translator and publisher names (`data/provenance/agent-reconciliation.json`, threshold five occurrences). Decision inputs under `data/reconciliation/` stay separate from these. The refreezing tools `reconcile_locations.py` and `reconcile_agents.py` contact the network only with the explicit switch `--i-am-refreezing`; the production run stays network-free.

The publication rule reads as follows. Only a documented `confirm` or `correct` decision produces a relation in `publishable-links.json`. `unresolved` produces a source-bound `klawiter:ContestedClaim`. `reject` preserves the negative decision, yet publishes no link.

Source occurrences are documented from `04_classified.csv` with page ID, text ID, line number, exact text and SHA-256. Multi-part location values use a documented component-set match, which counts only where one imprint contains every component. The same scan collects the occurrences of translator and publisher names via the field carrying the name, and names the field name in every occurrence; the Gate 2 check requires, for every agent subject with a candidate, either an occurrence or a spelled-out null finding. New curation patches replace no history; the previous decision is preserved in `supersedes`.

## Export and Interface

Stage 05 adopts from Gate 2 exclusively confirmed links. The flat JSON-LD file preserves all current page records. Its dataset description states the release scope, the compiler as creator, the responsible editor, the CC BY 4.0 licence and the version, which it reads from `pyproject.toml`, the single version source. A redirect withheld under a source-revision decision resolves no reference, and a restored page carries its decision as `sourceRevision` in the frontend record. The frontend file removes redirects and adds a redirect map. `inject_provenance.py` adds field provenance from exactly the selected LLM mode.

Stage 05 also builds the publication- and contribution-scoped layer of the frontend record. `lib/publications.py` segments the page's source text with `lib.editions.segment_page`, so the layer shares Gate 1's boundaries, identifiers and extents without changing the Gate 1 artifacts. It reads one further frozen input, the reviewed location stock `docs/data/locations.json`, which attests the place names that let a header with more than two comma segments be split into a publisher and several places. Stage 03 reads the same stock for the flat publisher, which follows the publication imprint. The records are written one file per source page into `docs/data/publications/`; the directory is rewritten on every run, so a page that loses its layer leaves no file behind. The main dataset keeps only the page-level summary, and `klawiter.jsonld` is unaffected. [Data](data.md) holds the field contract.

`docs/data/reconciliation.json` is a deterministic projection of candidates, decisions, open claims and edition claims. Run timestamps are held only in audit and manifest artifacts and do not alter this public data file.

## Patch Replay

`pipeline/apply_patches.py` applies released field corrections from `data/corrections/`. Reconciliation patches are read in during the Gate 2 rebuild. Field replay checks the versioned envelope, permitted fields/actions, positive integer targets and timezone-aware timestamps. Malformed inputs or unknown targets fail before frontend persistence; old-value drift is reported but remains authoritative replay. It does not independently verify a field patch against source evidence. Reconciliation has its separate subject/evidence contract. See the [patch-store contract](../data/corrections/README.md). Canonical field-correction propagation remains open.

## Repeatability

Gate 1 and Gate 2 rebuild their core documents inside the validators. CI then runs `pipeline/verify_committed_evidence.py`, reading the reviewed manifests directly from Git HEAD so regeneration cannot replace the reference. Every stable key/value must match, including source/input/code hashes, counts, validation and operator points. Only the run timestamp and hashes of the explicitly timestamped EARL/PROV/validation artifacts may differ; their files must still exist and match the current manifest hashes. All referenced input and artifact bytes are checked, including the ignored reconciliation candidates and review queue. The existing explicit Git-diff artifact list remains an additional comparison.

Historical repeated-run evidence remains in the journal and run audits. [Status](status.md) records the runtime and checks actually verified in this session. The latest full locked-uv rebuild reproduced all 117 compared deterministic files, including the ignored candidate/queue artifacts and vocabulary files. A local success is not a claim that remote CI has already run.

## Limits

- Four source pages have no delivered text body; one of them is bibliographic.
- Flat fields can mix publications, including compound pages outside Gate 1 selection.
- Frozen enrichment coverage is reported in `data/output/llm-enrichment-report.json`; it is not a guarantee of semantic completeness.
- Live enrichment is deliberately not a component of the default run.
- External expert review can extend the agentic evidence, yet does not change the technical repeatability.

The current results and Operator Points are held in [[production-readiness]], the check commands and the limits of what is asserted in [[testing]].
