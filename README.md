# Klawiter Bibliography

The Klawiter Bibliography opens up the Stefan Zweig bibliography compiled by Randolph J. Klawiter, drawn from a decommissioned MediaWiki database. The repository contains the reproducible extraction and modelling pipeline, the JSON-LD data, a static research interface and the evidence-bound curation layer.

The published interface is available at [chpollin.github.io/klawiter-rescue](https://chpollin.github.io/klawiter-rescue/).

## Subject and Data Holdings

The source data comprises 6,725 MediaWiki pages across several namespaces. Of these, 6,296 are bibliography pages in the main namespace. One page, `page_id 2979`, has no text body in the delivered BLOB files and is therefore retained as a documented stub.

The production run produces two complementary representations:

- The flat compatibility holdings contain 6,725 JSON-LD entries including 1,546 redirects. The interface uses 5,179 non-redirects and displays 4,751 entries from the main namespace.
- The work/edition model segments all 443 main-namespace pages with at least two ratified edition headers into 443 works, 1,886 editions and 1,886 source-bound Web Annotations. 75 editions are agentically confirmed, 1,810 remain proposals and one work binding is expressly contested.

Current figures are held in `data/output/quality-report.json`, `data/output/editions/manifest.json` and `data/output/reconciliation/manifest.json`.

## Data Model

The flat holdings use Schema.org, Dublin Core and the project-specific prefix `klawiter:`. Source identifiers, classification, provenance and curation status are retained on the entry. The vocabulary is documented under `docs/vocab/`.

The edition model separates four levels:

- `schema:CreativeWork` denotes the work of the respective MediaWiki page.
- `schema:Book` denotes a publication segmented out of an edition header.
- `oa:Annotation` connects each edition to its exact source excerpt via an `oa:TextPositionSelector`.
- `schema:PublicationVolume` denotes documented carrier occurrences only. These nodes assert no global identity across different collected volumes.

Contested relations are part of the final graph. A `klawiter:ContestedClaim` has a stable identifier, the exact source reference including SHA-256, at least two competing interpretations, the review history and `klawiter:decisionStatus = open`. A contested binding appears neither as `schema:exampleOfWork` nor as `schema:sameAs`. Confirmed relations and open statements therefore remain distinguishable both machine-readably and visually.

Reconciliation separates candidates, decisions and publishable links. The current state comprises 382 location subjects and 443 work subjects. 26 location links and three work links rest on documented `confirm` or `correct` decisions. Five open location decisions are emitted as contested claims. The complete prioritized review list contains 796 cases.

## Setup

Prerequisites are Python 3.11 or newer, Node.js for the frontend logic tests and the source files under `data/raw/`.

```bash
python -m pip install uv==0.12.5
python -m uv sync --locked
```

`uv.lock` pins the production and development dependencies. The default execution uses the versioned LLM cache and requires neither network access nor an API key.

## Production Run

```bash
python -m uv run python pipeline/run_pipeline.py
```

The command runs fail-fast:

1. SQL and BLOB extraction, encoding repair and wiki parsing;
2. application of the frozen LLM enrichment and rule-bound normalization;
3. classification;
4. work/edition segmentation with SHACL, selector, ID, queue and determinism checks;
5. entity reconciliation with separate candidate, decision, claim and publication layers;
6. JSON-LD and frontend export;
7. quality report, round-trip verification, census, provenance projection, triage, correction overlay and final reconciliation check.

Partial ranges can be run via stable stage identifiers:

```bash
python -m uv run python pipeline/run_pipeline.py --from-stage 03 --to-stage gate2 --no-postprocess
python -m uv run python pipeline/run_pipeline.py --llm-mode off
```

A new API call is possible only with `--llm-mode live`. This requires `GEMINI_API_KEY` to be set. Live results are reviewed before being adopted as new frozen provenance holdings.

## Validation

```bash
python -m uv run pytest -q
python -m uv run pytest -q -m semantic
python -m uv run pre-commit run --all-files
git diff --check
```

The static checks (ruff check, ruff format) are defined in `.pre-commit-config.yaml`; `python -m uv run pre-commit install` sets them up as a Git hook, and CI runs the same hook set.

The default set checks census, schema, consistency, regression, extraction rules, normalization, provenance, correction contracts, edition model, reconciliation, production runner and frontend logic. The semantic suite is marked separately; its remaining known failures are documented as limits and are not masked by relaxed assertions.

Gate 1 writes SHACL and EARL evidence to `data/output/editions/`. Gate 2 writes candidates, decisions, publishable links, contested claims, queue, PROV/EARL and manifest to `data/output/reconciliation/`. Both validators rebuild their results from the frozen inputs and compare them deterministically.

## Curation and Reconciliation

The local editing mode of the interface produces a combined curation document. Field changes use `patchVersion: 2`; reconciliation decisions use `reconciliationPatchVersion: 1`. Released files are held under `data/corrections/` and are re-applied on every production run.

Field corrections preserve the machine value in the `edit_history` and set the field provenance to `editor`. A new authority-data decision replaces the previous decision while preserving the supersession chain. `unresolved` materializes an open claim. Only `confirm` or `correct` produces a publishable link.

## Outputs and Export

| Artifact | Content |
|---|---|
| `data/output/klawiter.jsonld` | complete flat JSON-LD holdings |
| `data/output/entries/` | regenerable individual JSON-LD files |
| `docs/data/klawiter.json` | data basis of the static interface |
| `data/output/editions/work-editions.jsonld` | work/edition graph with source annotations and contested claims |
| `data/output/editions/review-queue.json` | complete Gate 1 review list |
| `data/output/reconciliation/` | candidates, decisions, claims, publishable links and evidence |
| `docs/data/reconciliation.json` | compact reconciliation and claim data for the interface |

The interface exports BibTeX and RIS for citation purposes. The single-entry JSON-LD export includes any contested edition claims with their interpretations and review actions. The complete frontend export contains both contested edition claims and contested authority-data claims. The canonical, fully validated graph artifacts remain the files under `data/output/`.

## Known Limits

- The flat holdings preserve the historical one-page-one-entry view. On multi-edition pages, its individual values may represent different publication blocks. For those pages, `data/output/editions/work-editions.jsonld` is the structurally more precise representation.
- Missing publisher, translator or pagination details are frequently a property of the source. The pipeline adds no bibliographic values without a documented occurrence.
- 1,810 segmented editions are deterministic proposals. Of these, Gate 1 carries 317 flagged or open cases in the prioritized review list; the agentic sample confirms only its 75 exactly reviewed selectors.
- The binding of `klawiter:edition/4916-2016-b` to the original work or to an independent graphic novel adaptation work remains open. Both interpretations are preserved in the claim `klawiter:claim/work-binding/4916-2016-b`.
- Reconciliation candidates are proposals. Unreviewed and contested candidates are shown in the data and the interface, yet are not published as confirmed authority-data links.
- A later external expert review extends the agentic evidence. It is not a prerequisite for the reproducibility of the present state.

## Repository and Re-entry

`CLAUDE.md` is the single repository-specific agent instruction. `knowledge/index.md` guides through the canonical project knowledge; the most recent entry in `knowledge/journal.md` holds the terminal production state. An additional `AGENTS.md` is not required.

The principal directories are:

```text
pipeline/        production and validation code
tests/           automated and semantic checks
data/raw/        unmodified MediaWiki source
data/output/     generated data and evidence artifacts
data/provenance/ frozen external and LLM inputs
data/reconciliation/ documented modelling and authority-data decisions
docs/            static interface
knowledge/       canonical project knowledge
```

## Citation, Credits and License

Randolph J. Klawiter compiled the underlying bibliography at the University of Notre Dame. Christopher Pollin is responsible for the digital edition. The machine-readable citation details are held in `CITATION.cff`.

The code is licensed under MIT. Documentation and the structured edition are licensed under CC BY 4.0. The source bibliography must be credited on reuse in accordance with `CITATION.cff`; details are given in `LICENSE`.
