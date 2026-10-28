# Klawiter Bibliography — Repository Instructions

This file is the single repository-specific agent instruction. Do not create a parallel `AGENTS.md`. Domain and architectural rationale is held in `knowledge/`; executable usage notes are held in `README.md`.

## Entry

Before making changes:

1. Run `git status -sb` and check the current branch and the most recent commits. Preserve unknown changes as foreign or parallel work.
2. Read `knowledge/INDEX.md`, then `knowledge/handoff.md` for the results still waiting to be integrated and `knowledge/plan.md` for the accepted work and its order, then `knowledge/status.md` and the document the index names for the task at hand. The most recent entry in `knowledge/journal.md` holds the last terminal state.
3. Before using a handoff point, check its source and current target, integrate its durable content into the responsible document, record the transition in `knowledge/journal.md` and remove the point. Accepted future work goes into `knowledge/plan.md`.
4. Check the current code and the generated manifests against documentation statements. Take volatile figures exclusively from `data/output/quality-report.json`, `data/output/editions/manifest.json`, `data/output/reconciliation/manifest.json` and `docs/data/klawiter.json`.

## Data Integrity

Bibliographic values may be adopted only where they are documented in the MediaWiki source. A source-conditioned gap is a valid result. Authority-data IDs and derived geodata are admissible as soon as the underlying entity is documented in the source and the assignment is provenanced as a separate reconciliation decision.

The LLM stage works exclusively as a gap filler. It must not overwrite existing rule-based values. The default run uses `data/provenance/llm-enrichment-cache.json` and executes no model call. `--llm-mode live` is a deliberate, network-dependent recomputation that runs only with the operator's explicit consent, and its result is frozen only after review and updated provenance.

Candidates, decisions and published relations are separate layers:

- `proposed` denotes a deterministic, unreviewed statement or the decision of an LLM agent.
- `confirmed` denotes an exactly source-bound, reviewed statement.
- `contested` denotes an open statement with a stable claim ID, source reference, competing interpretations and review history.
- Only `confirm` and `correct` by a person or an exact deterministic rule produce `schema:sameAs` or another confirmed relation. `unresolved` produces an open claim.

Contested statements remain visible in the final data model and in the interface. They must neither be discarded nor emitted as a confirmed relation.

Only a person or an exact deterministic rule confirms, and a test fixture confirms nothing. A decision of an LLM agent, including one taken under the operator's delegation, is a proposal. It stays in its decision file as evidence with its producer named, publishes nothing and closes no claim. `pipeline/lib/producers.py` is the closed register of deciders and their producer classes. A decider absent from it fails the build, and whether a class confirms changes only with the operator principle in `knowledge/governance.md`, never in a decision file.

## Production Run

Dependencies and commands run through the pinned uv environment:

```bash
python -m uv sync --locked
python -m uv run python pipeline/run_pipeline.py
```

The runner executes its stages fail-fast. Partial ranges are selected with `--from-stage`, `--to-stage` and, where the run ends before `06`, with `--no-postprocess`. Numeric positional arguments are not supported. Stages, their modules and the rebuild boundary are in `knowledge/pipeline-architecture.md`. `pipeline/lib/config.py` is the single path definition, and `pipeline/05_to_jsonld.py` reads authority links exclusively from `data/output/reconciliation/publishable-links.json`.

## Verification Duty

After substantial changes, run at least the affected tests and validators. Before a commit the following run in this order:

```bash
python -m uv run python pipeline/run_pipeline.py
python -m uv run pytest -q --require-test-inputs
python -m uv run pytest -q -m semantic --require-test-inputs
python -m uv run ruff check pipeline tests
python -m uv run ruff format --check pipeline tests
git diff --check
```

After a change to the print strand, these follow as well:

```bash
python -m uv run pytest -q pipeline/print_volumes
python -m uv run python pipeline/print_volumes/p14_gate.py --export
node pipeline/print_volumes/viewer/check_render.mjs
node pipeline/print_volumes/viewer/check_review.mjs
```

`knowledge/testing.md`, Check Commands, owns this list and explains the order, each flag and the browser smoke test `smoke.mjs` with its trial server.

Gate 1 must pass SHACL, exact selectors and hashes, stable IDs, complete queue, claim contract and deterministic rebuild. Gate 2 must pass decision separation, contested claims, input hashes, JSON-LD and frontend projection as well as deterministic rebuild. Known semantic failures are documented and stay visible through fixed expectations.

## Print Strand

The print strand reads the three print volumes into records and relates them to the wiki through proposed claims. It runs outside the production run under these rules:

- Print PDFs and everything derived from them stay under `data/print/`, which Git ignores because the rights are unresolved. No print text enters a versioned file, a commit or a public artifact, and development stays local until the operator instructs otherwise.
- The leak check of `pipeline/print_volumes/p14_gate.py` stays green. It fails on any versioned file in its scope, this file included, that repeats twelve consecutive words of the print.
- The frozen benchmark pages, the frozen review sample with its supplements and the blind samples of `p09_human_sample.py` with their sheets are never used for rule development. Rules are written and inspected on the development sample of `dev_sample.py`, and `_heldout.py` names what stays out.
- Every change of a reading rule or a proposal comes before the first review decision of the human round, because a later change makes decisions stale.
- The real review server (`review_server.py`, port 8767, log `data/print/review/decisions.jsonl`) records decisions only from a person. An agent that drives the workbench starts a trial server on another port with its own `--log` outside `data/print/review/`.
- `p11_llm_spans.py` runs only in its frozen mode unless the operator consents to a live run.

Its stages and how to reproduce them are in `knowledge/print-pipeline.md`, Stages and Reproducing the strand.

## Code and Documentation Conventions

- Use Python 3.11+, uv, Ruff and pytest. Introduce no new tool where the existing layer carries the task.
- The frontend stays vanilla JavaScript and CSS without a build step. Libraries and fonts are held locally under `docs/vendor/` and `docs/fonts/`.
- Code comments are terse, English and describe only non-obvious constraints.
- Project documentation is English (operator decision 2026-08-27). Dated reviews and evaluation evidence live under `snapshots/`, and a fact is updated as `knowledge/governance.md`, Documentation rules, describes. German designations of historical sources and persistent identifiers stay unchanged.
- Write generated files through the responsible pipeline functions; decision inputs under `data/reconciliation/` and frozen external inputs under `data/provenance/` are versioned sources.
- Do not modify raw data under `data/raw/`. `data/intermediate/` and `data/output/entries/` are regenerable and gitignored.

## Known Limits

New publication formats, the Gate 3 wiki/print merge, institutionally content-changing decisions and live write-backs into external systems are not part of the production run. The one exception, a frozen print-address file under `data/provenance/` without print text, enters only on the operator's release and under the conditions in `knowledge/governance.md`, Operator principles.

The flat holdings still model one MediaWiki page as one entry, and the interface does not yet expose the complete edition graph. Treat the gaps listed in `knowledge/status.md` as known limits rather than new bugs. The acceptance contract, the operator principles and the rules of documentation are in `knowledge/governance.md`.
