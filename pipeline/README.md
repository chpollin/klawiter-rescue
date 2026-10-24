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
| [print_volumes/](print_volumes/) | Line extraction and probes of the print-volume PDFs, outside the production run; see [Print pipeline](../knowledge/print-pipeline.md) |

Keep source material under `data/raw/` unchanged. Rebuild intermediates and published artifacts through their responsible scripts. Frozen inputs and decisions remain separate from generated output; see the [correction-store contract](../data/corrections/README.md) for field replay and reconciliation patches.

After a full run, `python -m uv run python pipeline/verify_committed_evidence.py` compares the rebuilt Gate 1/2 manifests with the reviewed ones in Git HEAD. After a source-reviewed change, freeze the current manifests with their matching code, inputs and artifacts in the same commit; do not regenerate a separate allowance list to absorb drift. The comparison contract and the local `--reference-dir` review are defined in [testing](../knowledge/testing.md#ci-reproduction-boundary).
