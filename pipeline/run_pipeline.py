#!/usr/bin/env python3
"""Run the Klawiter production pipeline with explicit model-call control.

The default command executes every deterministic stage, applies the tracked
frozen LLM results without a network call, builds and validates Gate 1 and
Gate 2, then builds the verification, curation, and final publication checks.

Usage:
    python pipeline/run_pipeline.py
    python pipeline/run_pipeline.py --llm-mode off
    python pipeline/run_pipeline.py --llm-mode live
    python pipeline/run_pipeline.py --from-stage 03 --to-stage gate2
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter


@dataclass(frozen=True)
class Step:
    """One fail-fast pipeline boundary with a stable public stage identifier."""

    stage: str
    script: str
    description: str


STEPS = (
    Step("01", "01_extract.py", "Extract entries from SQL dump and BLOBs"),
    Step("02", "02_fix_encoding.py", "Repair source encoding"),
    Step("03", "03_parse_entries.py", "Parse wiki markup into fields"),
    Step("03b", "03b_llm_enrich.py", "Apply frozen or live LLM enrichment"),
    Step("03c", "03c_normalize.py", "Normalize auditable field values"),
    Step("04", "04_classify.py", "Classify entry types and periods"),
    Step("gate1", "segment_editions.py", "Build the Work/Edition proposal graph"),
    Step("gate1v", "validate_editions.py", "Validate Gate 1 evidence and schema"),
    Step(
        "gate2", "reconcile_entities.py", "Build reconciliation and public link layers"
    ),
    Step("05", "05_to_jsonld.py", "Build JSON-LD and frontend data"),
    Step("06", "06_validate.py", "Validate the structured dataset"),
)

POSTPROCESSORS = (
    Step("verify", "verify.py", "Verify field values against source text"),
    Step("census", "census.py", "Reconcile source, JSON-LD, and frontend records"),
    Step(
        "provenance",
        "inject_provenance.py",
        "Project field provenance into frontend data",
    ),
    Step("triage", "build_triage.py", "Build Expert-in-the-Loop review hints"),
    Step("patches", "apply_patches.py", "Apply reviewed correction patches"),
    Step(
        "gate2v", "validate_reconciliation.py", "Validate Gate 2 and public projections"
    ),
)


def _configure_utf8() -> None:
    """Make status output safe on the Windows console before printing Unicode."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def _parse_args() -> argparse.Namespace:
    stage_ids = tuple(step.stage for step in STEPS)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-stage", choices=stage_ids, default="01")
    parser.add_argument("--to-stage", choices=stage_ids, default="06")
    parser.add_argument(
        "--llm-mode",
        choices=("frozen", "off", "live"),
        default="frozen",
        help="Frozen is reproducible and network-free; live may incur API calls.",
    )
    parser.add_argument(
        "--postprocess",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Build verification, curation, and final Gate 2 checks after stage 06.",
    )
    return parser.parse_args()


def _selected_steps(start: str, end: str, llm_mode: str) -> list[Step]:
    stage_ids = [step.stage for step in STEPS]
    start_index = stage_ids.index(start)
    end_index = stage_ids.index(end)
    if start_index > end_index:
        raise ValueError("--from-stage must not follow --to-stage")
    selected = list(STEPS[start_index : end_index + 1])
    if llm_mode == "off":
        selected = [step for step in selected if step.stage != "03b"]
    return selected


def _command(step: Step, pipeline_dir: Path, llm_mode: str) -> list[str]:
    command = [sys.executable, str(pipeline_dir / step.script)]
    if step.stage == "03b":
        command.extend(("--mode", llm_mode))
    elif step.stage == "03c":
        command.extend(("--input", "03" if llm_mode == "off" else "03b"))
    elif step.stage == "provenance":
        command.extend(("--llm-mode", llm_mode))
    return command


def _run_step(
    step: Step, pipeline_dir: Path, project_root: Path, llm_mode: str
) -> None:
    print(f"\n{'─' * 68}")
    print(f"{step.stage}: {step.description}")
    print(f"Script: {step.script}")
    print(f"{'─' * 68}")
    started = perf_counter()
    result = subprocess.run(
        _command(step, pipeline_dir, llm_mode),
        cwd=project_root,
        check=False,
    )
    elapsed = perf_counter() - started
    if result.returncode != 0:
        raise RuntimeError(
            f"Stage {step.stage} failed with exit code {result.returncode} "
            f"after {elapsed:.1f}s"
        )
    print(f"OK: {step.stage} completed in {elapsed:.1f}s")


def main() -> None:
    _configure_utf8()
    args = _parse_args()
    if args.postprocess and args.to_stage != "06":
        raise ValueError("Post-processing requires --to-stage 06")

    pipeline_dir = Path(__file__).resolve().parent
    project_root = pipeline_dir.parent
    selected = _selected_steps(args.from_stage, args.to_stage, args.llm_mode)
    if not selected:
        raise ValueError("The selected range contains no executable stage")

    print("=" * 68)
    print("Klawiter production pipeline")
    print(f"Stages: {selected[0].stage} through {selected[-1].stage}")
    print(f"LLM mode: {args.llm_mode}")
    print(f"Post-processing: {'yes' if args.postprocess else 'no'}")
    print("=" * 68)

    started = perf_counter()
    for step in selected:
        _run_step(step, pipeline_dir, project_root, args.llm_mode)
    if args.postprocess:
        for step in POSTPROCESSORS:
            _run_step(step, pipeline_dir, project_root, args.llm_mode)

    print("\n" + "=" * 68)
    print(f"Pipeline completed in {perf_counter() - started:.1f}s")
    print("=" * 68)


if __name__ == "__main__":
    main()
