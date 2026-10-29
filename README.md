# Stefan Zweig Bibliography (Klawiter)

A source-bound reconstruction of Randolph J. Klawiter's Stefan Zweig bibliography from a decommissioned MediaWiki. This repository contains the extraction pipeline, structured data, static research interface and review evidence.

- [Public interface](https://chpollin.github.io/klawiter-rescue/)
- [Current status and next steps](knowledge/status.md)
- [Project knowledge](knowledge/INDEX.md)

## Purpose

The repository preserves the current-page inventory of the wiki and models it as bibliographic data. Complete bibliographic modelling and product acceptance remain open: a wiki page can describe several publications, while search and citation still use a flat page record. The work/edition graph is a complementary, source-anchored representation of the selected multi-edition corpus. A second, local strand reads Klawiter's three printed volumes as the ground for a merged bibliography. Counts and current acceptance evidence belong in [Status](knowledge/status.md), with links to the generated reports.

## Data and rights

[Data and model](knowledge/data.md) owns the entity definitions, source scope and uncertainty contract. Only reviewed `confirm` or `correct` reconciliation decisions publish authority links. Decisions of LLM agents, delegated ones included, are proposals that stay as evidence with their producer named and publish nothing, because only a person or an exact deterministic rule confirms. Proposed and contested statements remain distinguishable, with source evidence and review history.

| Location | Responsibility |
|---|---|
| `data/raw/` | unchanged archival source; not a ready-made public release package |
| `data/provenance/`, `data/reconciliation/` | frozen inputs and documented decisions |
| `data/corrections/` | released field and reconciliation patches |
| `data/intermediate/`, `data/output/entries/` | regenerable, ignored intermediate and individual-entry files |
| `data/output/klawiter.jsonld` | complete flat JSON-LD holdings |
| `data/output/editions/`, `data/output/reconciliation/` | structured graphs, queues, claims and gate evidence |
| `docs/data/`, `docs/vocab/` | frontend projections and vocabulary publication |
| `pipeline/`, `tests/`, `docs/` | pipeline, checks and static interface |
| `knowledge/` | maintained project knowledge |
| `snapshots/` | dated reviews and evaluation evidence |

Field patches currently update the frontend projection, history and review state. They do not update every canonical graph or report; closing this propagation gap is an acceptance task. Reconciliation patches are applied before the Gate 2 rebuild. See the [patch-store contract](data/corrections/README.md).

BibTeX and RIS exports cite flat records. Browser JSON-LD exports and the full canonical graphs have different scopes, documented in [Frontend architecture](knowledge/frontend-architecture.md).

The rights in the printed volumes are unresolved. The PDFs and everything derived from them stay under `data/print/`, which Git ignores, and nothing of the print strand is published until the operator decides so. [Project](knowledge/project.md) holds the rights and publication frame.

## Use

### Run locally

Python 3.11+, Node.js for frontend tests, and the delivered source files under `data/raw/` are required. Run commands from the repository root.

```bash
python -m pip install uv==0.12.5
python -m uv sync --locked
python -m uv run python pipeline/run_pipeline.py
python -m http.server 8000 --directory docs
```

Open [localhost:8000](http://localhost:8000/). Curation is available on localhost; changes are stored in the browser and exported as patches.

`uv.lock` pins the runtime and development dependencies. The default pipeline uses the versioned LLM cache and makes no model or network call. It fails at the first unsuccessful stage. [Pipeline architecture](knowledge/pipeline-architecture.md) documents each stage, its inputs and rebuild boundary.

```bash
python -m uv run python pipeline/run_pipeline.py --from-stage 03 --to-stage gate2 --no-postprocess
python -m uv run python pipeline/run_pipeline.py --llm-mode off
```

`--llm-mode live` deliberately recomputes model results, requires `GEMINI_API_KEY` and may incur API charges. Review its output before replacing frozen inputs.

### Verify changes

```bash
python -m uv run python pipeline/run_pipeline.py
python -m uv run pytest -q --require-test-inputs
python -m uv run pytest -q -m semantic --require-test-inputs
python -m uv run ruff check pipeline tests
python -m uv run ruff format --check pipeline tests
git diff --check
```

The default suite blocks new or changed failures against exact reviewed page/field/value inventories. The semantic suite deliberately retains known source/expectation disagreements as red assertions; it is not an acceptance score. Missing committed test inputs fail, and `--require-test-inputs` also fails on a missing Node.js or missing stage CSVs, which the production run writes. [Testing](knowledge/testing.md), Check Commands, holds the complete list with the checks of the print strand and explains fixtures, independent evidence, CI and the limits of these checks.

### Print volumes (local)

The print strand reads Klawiter's three printed volumes into records with stable identifiers and relates them to the wiki through proposed claims. Rebuilding it needs the three PDFs. [Print volumes](knowledge/print-volumes.md) describes their source and structure, [Print pipeline](knowledge/print-pipeline.md) the stages and how to reproduce them.

```bash
python -m uv run --group print python pipeline/print_volumes/review_server.py
python -m uv run python pipeline/print_volumes/p14_gate.py --export
```

The review server listens on 127.0.0.1 only, by default on port 8767. The card workbench opens at [127.0.0.1:8767/viewer/cards.html](http://127.0.0.1:8767/viewer/cards.html), where a person decides whether a value read from the print is right in its context, and the page check at [127.0.0.1:8767/viewer/page.html](http://127.0.0.1:8767/viewer/page.html) shows a PDF page beside every line and value read from it. The same server serves the interface from `docs/` at its root. Decisions go to `data/print/review/decisions.jsonl`, so a trial run takes another `--port` and its own `--log`. The gate checks the inputs against their hashes, a deterministic rebuild, validation, the frozen samples and that no versioned file repeats print text. [Card workbench](knowledge/design.md#card-workbench) describes the workbench, and [Testing](knowledge/testing.md) lists the further checks of the strand.

## How this was built

The repository was built with [Promptotyping](https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin), a working practice in which LLM coding agents implement from maintained project knowledge and a person keeps the decisions on sources, model and acceptance. The harness was Claude Code. The commit trailers name Claude Opus 4.6 from March to April 2026, Claude Fable 5 from June to August, Claude Opus 4.8 in June and July, Claude Fable 5.1 in September and Claude Opus 5.5 from September onwards as coding agents, and one independent audit of August 2026 was run by an OpenAI Codex agent (`data/output/audits/final-independent-verification.json`). The pipeline's own LLM stage, a gap filler for fields no rule reads, runs from a frozen cache by default and recomputes with Gemini only on a deliberate live run. Project knowledge lives in [`knowledge/`](knowledge/INDEX.md), and [`CLAUDE.md`](CLAUDE.md) translates it into instructions for the agents.

Checking is layered. Verification runs a fixed check order of production run, default and semantic test suites, Ruff and a whitespace check, and Gate 1 and Gate 2 validate their graphs with SHACL and record EARL reports ([Testing](knowledge/testing.md)). Agentic review, by independent agents on sampled decisions and in dated reviews under `snapshots/`, produces proposals and findings that confirm nothing, since the closed producer register `pipeline/lib/producers.py` lets only a person or an exact deterministic rule confirm. Scholarly validation of values happens through a person's decisions in the interface and the card workbench ([Governance](knowledge/governance.md)). Commit `2a9dbaa` is the state before the knowledge base was aligned with the Promptotyping document templates on 2026-10-28. The episodes in which a check reported success it had not earned are recorded in the [Journal](knowledge/journal.md) and the commit history.

## Limits

The known limits stand in [Status](knowledge/status.md), whose self-assessment rates the project lower as a completed scholarly research product than as preservation and engineering work. Edition confirmations and authority links depend on a person's decisions; their current figures are in the [Gate 1](data/output/editions/manifest.json) and [Gate 2](data/output/reconciliation/manifest.json) manifests. Search and citation still use one flat record per wiki page, and the complete edition graph is not yet independently browsable in the interface. The print strand stays local while the rights in the printed volumes are unresolved.

## Licence and citation

Randolph J. Klawiter compiled the source bibliography; Christopher Pollin (Digital Humanities Craft) is responsible for the data rescue and publication. `CITATION.cff` contains citation details. Code is MIT-licensed; documentation and the structured data are CC BY 4.0. The license texts are `LICENSE` (MIT) and `LICENSES/CC-BY-4.0.txt`, third-party components are listed in `docs/vendor/NOTICE.md`, and reuse credits the bibliographic source. Release scope, metadata consistency and acceptance are tracked in [Governance](knowledge/governance.md#release-scope).

## Contributing

`CLAUDE.md` is the sole repository-specific agent instruction. Start from the [knowledge index](knowledge/INDEX.md), which routes to the [Handoff](knowledge/handoff.md) inbox of results still waiting to be integrated, the [Plan](knowledge/plan.md) of accepted work and its order, [Status](knowledge/status.md) and the latest [Journal](knowledge/journal.md) entry. The index names the document responsible for each change, and [Governance](knowledge/governance.md) holds who decides what, the operator principles and the rules of documentation. Historical reviews under `snapshots/` remain dated evidence.
