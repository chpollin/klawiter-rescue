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
| `knowledge/` | maintained project knowledge |
| `snapshots/` | dated reviews and evaluation evidence |

Field patches currently update the frontend projection, history and review state. They do not update every canonical graph or report; closing this propagation gap is an acceptance task. Reconciliation patches are applied before the Gate 2 rebuild. See the [patch-store contract](data/corrections/README.md).

BibTeX and RIS exports cite flat records. Browser JSON-LD exports and the full canonical graphs have different scopes, documented in [Interface and curation](knowledge/frontend.md). The complete edition graph is not yet independently browsable in the interface.

## Print volumes (local)

A second strand reads Klawiter's three printed volumes into records with stable identifiers and relates them to the wiki through proposed claims, as the ground for a merged bibliography. The PDFs and everything derived from them stay under `data/print/`, which Git ignores because the rights in the print are unresolved, and nothing of the strand is published until the operator decides so. Rebuilding it needs the three PDFs. [Print volumes](knowledge/print-volumes.md) describes their source and structure, [Print pipeline](knowledge/print-pipeline.md) the stages and how to reproduce them.

```bash
python -m uv run --group print python pipeline/print_volumes/review_server.py
python -m uv run python pipeline/print_volumes/p14_gate.py --export
```

The review server listens on 127.0.0.1 only, by default on port 8767. The card workbench opens at [127.0.0.1:8767/viewer/cards.html](http://127.0.0.1:8767/viewer/cards.html), where a person decides whether a value read from the print is right in its context, and the page check at [127.0.0.1:8767/viewer/page.html](http://127.0.0.1:8767/viewer/page.html) shows a PDF page beside every line and value read from it. The same server serves the interface from `docs/` at its root. Decisions go to `data/print/review/decisions.jsonl`, so a trial run takes another `--port` and its own `--log`. The gate checks the inputs against their hashes, a deterministic rebuild, validation, the frozen samples and that no versioned file repeats print text. [Print viewer](knowledge/print-viewer.md) describes the workbench, and [Testing](knowledge/testing.md) lists the further checks of the strand.

## How this was built

The repository was built with [Promptotyping](https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin), a method in which LLM coding agents implement from maintained project knowledge and a person keeps the decisions on sources, model and acceptance. The history begins in April 2025 with analysis scripts over the wiki's SQL dump and a first `CLAUDE.md`. The current pipeline goes back to the rebuild of 29 March 2026 (930fae2). The knowledge documents, gates and producer register grew during the work, as the journal and the dated reviews show.

The commit trailers name Claude Opus 4.6 from March to April 2026, Claude Fable 5 from June to August, Claude Opus 4.8 in June and July, Claude Fable 5.1 in September and Claude Opus 5.5 from late September as coding agents. One independent audit of August 2026 was run by an OpenAI Codex agent (`data/output/audits/final-independent-verification.json`). The pipeline's own LLM stage, a gap filler for fields no rule reads, runs from a frozen cache by default and recomputes with Gemini only on a deliberate live run.

Project knowledge lives in [`knowledge/`](knowledge/index.md), and [`CLAUDE.md`](CLAUDE.md) translates it into instructions for the agents. Status, plan, handoff inbox and journal record what holds now, what comes next, what still waits for checking and how the state came about. Dated reviews under `snapshots/` are kept as evidence of what was found at the time.

Verification is layered.

- A fixed check order runs the full pipeline, the default and the semantic test suites, Ruff and a whitespace check ([Testing](knowledge/testing.md), Check Commands). A CI job reproduces the deterministic artifacts byte for byte.
- Gate 1 (work/edition graph) and Gate 2 (reconciliation) validate their graphs with SHACL and record the results as EARL reports under `data/output/editions/` and `data/output/reconciliation/`.
- `tests/test_record_invariants.py` checks invariants over every published record.
- Since 71a0fe0 every decision of an LLM agent is a proposal. It stays as evidence with its producer named in the closed register `pipeline/lib/producers.py`, and only a person or an exact deterministic rule confirms an edition, closes a claim or publishes a link.

The journal and the commit history document several episodes in which a check reported success it had not earned. They are the main reason the layers above exist.

| Episode | Where it is documented |
|---|---|
| SHACL had validated an edition graph that expanded to six triples, because its container keys were missing from the JSON-LD context, so earlier conformance claims rested on an almost empty graph | 148a739 (commit message), [Journal](knowledge/journal.md), entry of 26 to 27 August 2026 |
| Editions and places counted as `confirmed` without a person having decided, resting on an agent reconciliation and on decisions taken only by a test fixture | 86670c8, 7994ccb, 71a0fe0 |
| Reviews found defects that every unit test had passed, because the tests used shortened or synthetic strings, asserted current behaviour or ratcheted counts, which led to the invariant layer over all records | [Testing](knowledge/testing.md), Invariants over all records |
| The record card's coverage test reported no gaps because it counted markers a reader cannot see | 4f0f6bc, [Journal](knowledge/journal.md) |
| "Mojibake fixed from 55% to 0%" was narrowed on the same day to the known Mojibake patterns, since other kinds of corruption had not been checked | 930fae2, d5c5775 |

The known limits stand in [Status](knowledge/status.md), whose self-assessment rates the project lower as a completed scholarly research product than as preservation and engineering work. At its snapshot of 24 October 2026 no edition was confirmed and no authority link published, because no person had yet decided. The current figures are in the [Gate 1](data/output/editions/manifest.json) and [Gate 2](data/output/reconciliation/manifest.json) manifests. Search and citation still use one flat record per wiki page. The print strand stays local while the rights in the printed volumes are unresolved.

## Contributing and publication

`CLAUDE.md` is the sole repository-specific agent instruction. Start from the [knowledge index](knowledge/index.md), which routes to [Status](knowledge/status.md), the [Plan](knowledge/plan.md) of accepted work and its order, the [Handoff](knowledge/handoff.md) inbox of results still waiting to be integrated and the latest [Journal](knowledge/journal.md) entry. [Documentation](knowledge/documentation.md) names the document responsible for each change. Historical reviews remain dated evidence.

Randolph J. Klawiter compiled the source bibliography; Christopher Pollin (Digital Humanities Craft) is responsible for the data rescue and publication. `CITATION.cff` contains citation details. Code is MIT-licensed; documentation and the structured data are CC BY 4.0. The license texts are `LICENSE` (MIT) and `LICENSES/CC-BY-4.0.txt`, third-party components are listed in `docs/vendor/NOTICE.md`, and reuse credits the bibliographic source. Release scope, metadata consistency and acceptance are tracked in [Production readiness](knowledge/production-readiness.md).
