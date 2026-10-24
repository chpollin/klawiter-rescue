# Stefan Zweig Bibliography (Klawiter)

A source-bound reconstruction of Randolph J. Klawiter's Stefan Zweig bibliography from a decommissioned MediaWiki. This repository contains the extraction pipeline, structured data, static research interface and review evidence.

[Public interface](https://chpollin.github.io/klawiter-rescue/) · [Current status and next steps](knowledge/status.md) · [Project knowledge](knowledge/index.md)

The current-page inventory is preserved. Complete bibliographic modelling and product acceptance remain open: a wiki page can describe several publications, while search and citation still use a flat page record. The work/edition graph is a complementary, source-anchored representation of the selected multi-edition corpus. Counts and current acceptance evidence belong in [Status](knowledge/status.md), with links to the generated reports.

## Run locally

Python 3.11+, Node.js for frontend tests, and the delivered source files under `data/raw/` are required. Run commands from the repository root.

```bash
python -m pip install uv==0.12.5
python -m uv sync --locked
python -m uv run python pipeline/run_pipeline.py
python -m http.server 8000 --directory docs
```

Open [localhost:8000](http://localhost:8000/). Curation is available on localhost; changes are stored in the browser and exported as patches.

`uv.lock` pins the runtime and development dependencies. The default pipeline uses the versioned LLM cache and makes no model or network call. It fails at the first unsuccessful stage. [Pipeline](knowledge/pipeline.md) documents each stage, its inputs and rebuild boundary.

```bash
python -m uv run python pipeline/run_pipeline.py --from-stage 03 --to-stage gate2 --no-postprocess
python -m uv run python pipeline/run_pipeline.py --llm-mode off
```

`--llm-mode live` deliberately recomputes model results, requires `GEMINI_API_KEY` and may incur API charges. Review its output before replacing frozen inputs.

## Verify changes

```bash
python -m uv run python pipeline/run_pipeline.py
python -m uv run pytest -q --require-test-inputs
python -m uv run pytest -q -m semantic --require-test-inputs
python -m uv run ruff check pipeline tests
python -m uv run ruff format --check pipeline tests
git diff --check
```

The default suite blocks new or changed failures against exact reviewed page/field/value inventories. The semantic suite deliberately retains known source/expectation disagreements as red assertions; it is not an acceptance score. Missing committed test inputs fail, and `--require-test-inputs` also fails on a missing Node.js or missing stage CSVs, which the production run writes. [Testing](knowledge/testing.md), Check Commands, holds the complete list with the checks of the print strand and explains fixtures, independent evidence, CI and the limits of these checks.

## Data and curation

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
| `knowledge/` | maintained knowledge and dated review evidence |

Field patches currently update the frontend projection, history and review state. They do not update every canonical graph or report; closing this propagation gap is an acceptance task. Reconciliation patches are applied before the Gate 2 rebuild. See the [patch-store contract](data/corrections/README.md).

BibTeX and RIS exports cite flat records. Browser JSON-LD exports and the full canonical graphs have different scopes, documented in [Interface and curation](knowledge/frontend.md). The complete edition graph is not yet independently browsable in the interface.

## Print volumes (local)

A second strand reads Klawiter's three printed volumes into records with stable identifiers and relates them to the wiki through proposed claims, as the ground for a merged bibliography. The PDFs and everything derived from them stay under `data/print/`, which Git ignores because the rights in the print are unresolved, and nothing of the strand is published until the operator decides so. Rebuilding it needs the three PDFs. [Print volumes](knowledge/print-volumes.md) describes their source, the stages and how to reproduce them.

```bash
python -m uv run --group print python pipeline/print_volumes/review_server.py
python -m uv run python pipeline/print_volumes/p14_gate.py --export
```

The review server listens on 127.0.0.1 only, by default on port 8767. The card workbench opens at [127.0.0.1:8767/viewer/cards.html](http://127.0.0.1:8767/viewer/cards.html), where a person decides whether a value read from the print is right in its context, and the page check at [127.0.0.1:8767/viewer/page.html](http://127.0.0.1:8767/viewer/page.html) shows a PDF page beside every line and value read from it. The same server serves the interface from `docs/` at its root. Decisions go to `data/print/review/decisions.jsonl`, so a trial run takes another `--port` and its own `--log`. The gate checks the inputs against their hashes, a deterministic rebuild, validation, the frozen samples and that no versioned file repeats print text. [Print viewer](knowledge/print-viewer.md) describes the workbench, and [Testing](knowledge/testing.md) lists the further checks of the strand.

## Contributing and publication

`CLAUDE.md` is the sole repository-specific agent instruction. Start from the [knowledge index](knowledge/index.md), which routes to [Status](knowledge/status.md), the [Plan](knowledge/plan.md) of accepted work and its order, the [Handoff](knowledge/handoff.md) inbox of results still waiting to be integrated and the latest [Journal](knowledge/journal.md) entry. [Documentation](knowledge/documentation.md) names the document responsible for each change. Historical reviews remain dated evidence.

Randolph J. Klawiter compiled the source bibliography; Christopher Pollin (Digital Humanities Craft) is responsible for the data rescue and publication. `CITATION.cff` contains citation details. Code is MIT-licensed; documentation and the structured data are CC BY 4.0. The license texts are `LICENSE` (MIT) and `LICENSES/CC-BY-4.0.txt`, third-party components are listed in `docs/vendor/NOTICE.md`, and reuse credits the bibliographic source. Release scope, metadata consistency and acceptance are tracked in [Production readiness](knowledge/production-readiness.md).
