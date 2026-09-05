# Klawiter Bibliography — Repository Instructions

This file is the single repository-specific agent instruction. Do not create a parallel `AGENTS.md`. Domain and architectural rationale is held in `knowledge/`; executable usage notes are held in `README.md`.

## Entry

Before making changes:

1. Run `git status -sb` and check the current branch and the most recent commits. Preserve unknown changes as foreign or parallel work.
2. Read `knowledge/index.md` and `knowledge/status.md`, and use the reading path for the task at hand. The most recent entry in `knowledge/journal.md` holds the last terminal state.
3. Check the current code and the generated manifests against documentation statements. Take volatile figures exclusively from `data/output/quality-report.json`, `data/output/editions/manifest.json`, `data/output/reconciliation/manifest.json` and `docs/data/klawiter.json`.

## Data Integrity

Bibliographic values may be adopted only where they are documented in the MediaWiki source. A source-conditioned gap is a valid result. Authority-data IDs and derived geodata are admissible as soon as the underlying entity is documented in the source and the assignment is provenanced as a separate reconciliation decision.

The LLM stage works exclusively as a gap filler. It must not overwrite existing rule-based values. The default run uses `data/provenance/llm-enrichment-cache.json` and executes no model call. `--llm-mode live` is a deliberate, network-dependent recomputation; its result is frozen only after review and updated provenance.

Candidates, decisions and published relations are separate layers:

- `proposed` denotes a deterministic, unreviewed statement.
- `confirmed` denotes an exactly source-bound, reviewed statement.
- `contested` denotes an open statement with a stable claim ID, source reference, competing interpretations and review history.
- Only `confirm` and `correct` produce `schema:sameAs` or another confirmed relation. `unresolved` produces an open claim.

Contested statements remain visible in the final data model and in the interface. They must neither be discarded nor emitted as a confirmed relation.

## Production Run

Dependencies and commands run through the pinned uv environment:

```bash
python -m uv sync --locked
python -m uv run python pipeline/run_pipeline.py
```

The runner executes the stages `01`, `01v`, `02`, `03`, `03b`, `03c`, `04`, `gate1`, `gate1v`, `gate2`, `05`, `06` and thereafter `verify`, `census`, `provenance`, `triage`, `patches`, `vocab`, `gate2v` fail-fast. Partial ranges are selected with `--from-stage`, `--to-stage` and, where the run ends before `06`, with `--no-postprocess`. Numeric positional arguments are not supported.

Relevant layers:

- `pipeline/lib/config.py` is the single path definition.
- `pipeline/lib/editions.py` and `pipeline/segment_editions.py` produce the complete work/edition graph of the ratified multi-edition corpus.
- `pipeline/lib/reconciliation.py` and `pipeline/reconcile_entities.py` produce candidates, decisions, contested claims and publishable links.
- `pipeline/05_to_jsonld.py` reads exclusively the documented links from `data/output/reconciliation/publishable-links.json`.
- `pipeline/apply_patches.py` replays released field corrections. Reconciliation patches are read in during the Gate 2 rebuild and preserve a supersession chain.

## Verification Duty

After substantial changes, run at least the affected tests and validators. Before commit and push the following applies:

```bash
python -m uv run pytest -q
python -m uv run pytest -q -m semantic
python -m uv run ruff check pipeline tests
python -m uv run ruff format --check pipeline tests
python -m uv run python pipeline/run_pipeline.py
git diff --check
```

Gate 1 must pass SHACL, exact selectors and hashes, stable IDs, complete queue, claim contract and deterministic rebuild. Gate 2 must pass decision separation, contested claims, input hashes, JSON-LD and frontend projection as well as deterministic rebuild. Known semantic failures are documented and stay visible through fixed expectations.

## Code and Documentation Conventions

- Use Python 3.11+, uv, Ruff and pytest. Introduce no new tool where the existing layer carries the task.
- The frontend stays vanilla JavaScript and CSS without a build step. Libraries and fonts are held locally under `docs/vendor/` and `docs/fonts/`.
- Code comments are terse, English and describe only non-obvious constraints.
- Project documentation is English (operator decision 2026-08-27). German designations of historical sources and persistent identifiers stay unchanged.
- Write generated files through the responsible pipeline functions; decision inputs under `data/reconciliation/` and frozen external inputs under `data/provenance/` are versioned sources.
- Do not modify raw data under `data/raw/`. `data/intermediate/` and `data/output/entries/` are regenerable and gitignored.

## Known Limits

The flat holdings still model one MediaWiki page as one entry. The work/edition graph covers the ratified header-selected corpus; it does not fully model every compound page or every edition field. The frontend does not yet expose the complete edition graph, and field corrections/provenance are not propagated into every canonical artifact. Current counts, verified repairs and prioritized gaps belong in `knowledge/status.md`; the acceptance contract belongs in `knowledge/production-readiness.md`.

New publication formats, the Gate 3 wiki/print merge, institutionally content-changing decisions and live write-backs into external systems are not part of the production run.
