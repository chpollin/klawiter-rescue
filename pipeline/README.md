# Pipeline entry points

Run commands from the repository root after the dependency setup in the [project README](../README.md). The [pipeline architecture](../knowledge/pipeline.md) explains the transformations; [data contracts](../knowledge/data.md) define the published layers, and [testing](../knowledge/testing.md) defines the checks and their limits.

```bash
python -m uv run python pipeline/run_pipeline.py
```

The default `frozen` mode reads the versioned LLM enrichment cache and makes no model request. `--llm-mode off` skips enrichment and sends rule output to normalization. `--llm-mode live` deliberately permits model calls, requires `GEMINI_API_KEY`, and produces results that need source review before adoption as frozen input.

For a bounded rebuild, name stage IDs explicitly and disable post-processing when the last stage is before `06`:

```bash
python -m uv run python pipeline/run_pipeline.py --from-stage 03 --to-stage gate2 --no-postprocess
python -m uv run python pipeline/run_pipeline.py --llm-mode off
```

The runner executes `01`, `01v`, `02`, `03`, `03b`, `03c`, `04`, `gate1`, `gate1v`, `gate2`, `05`, and `06`. Stage `01v` invokes the dump-to-extract census. The default post-processing order is `verify`, `census`, `provenance`, `triage`, `patches`, `vocab`, and `gate2v`; `vocab` runs `build_vocab_pages.py`. The runner stops on a nonzero child-process exit. Reported bibliographic issues may remain even when a run completes.

`--from-stage` and `--to-stage` accept the main stage IDs declared in [run_pipeline.py](run_pipeline.py), including `01v`. Post-processors are not range endpoints. A partial run requires the earlier artifacts it consumes; it does not prove a complete rebuild. Numeric positional stage arguments are unsupported.

## Local ownership

| Component | Responsibility |
|---|---|
| [lib/config.py](lib/config.py) | Shared paths, I/O and logging |
| [lib/encoding.py](lib/encoding.py), [lib/wiki_parser.py](lib/wiki_parser.py), [lib/patterns.py](lib/patterns.py) | Source repair, wiki structure and field extraction |
| [lib/editions.py](lib/editions.py) | Work/edition segmentation and scoped source evidence |
| [lib/reconciliation.py](lib/reconciliation.py) | Candidates, reviewed decisions, open claims and publishable links |
| [05_to_jsonld.py](05_to_jsonld.py) | Canonical flat JSON-LD and frontend projection |
| [apply_patches.py](apply_patches.py) | Released field corrections as the final frontend overlay |
| [build_vocab_pages.py](build_vocab_pages.py) | Vocabulary index and term pages |

Keep source material under `data/raw/` unchanged. Rebuild intermediates and published artifacts through their responsible scripts. Frozen inputs and decisions remain separate from generated output; see the [correction-store contract](../data/corrections/README.md) for field replay and reconciliation patches.

Gate 1 and Gate 2 rebuild their core documents inside the validators. CI then runs `pipeline/verify_committed_evidence.py`, reading the reviewed manifests directly from Git HEAD so regeneration cannot replace the reference. Every stable key/value must match, including source/input/code hashes, counts, validation and operator points. Only the run timestamp and hashes of the explicitly timestamped EARL/PROV/validation artifacts may differ; their files must still exist and match the current manifest hashes. All referenced input and artifact bytes are checked, including the ignored reconciliation candidates and review queue. The existing explicit Git-diff artifact list remains an additional comparison.

After a source-reviewed change, freeze the current Gate 1/2 manifests with their matching code, inputs and artifacts in the same commit. Do not regenerate a separate allowance list to absorb drift. A local precommit review may use an explicit reference directory copied from the reviewed run; CI uses HEAD. See [testing](../knowledge/testing.md).
