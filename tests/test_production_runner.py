"""Production-runner and frozen-model-input contract tests.

These tests protect the boundaries added during the production-readiness lane.
They do not execute the expensive source extraction or make network calls.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

runner = importlib.import_module("run_pipeline")
enrichment = importlib.import_module("03b_llm_enrich")


def test_llm_off_removes_only_optional_stage() -> None:
    selected = runner._selected_steps("01", "06", "off")
    assert [step.stage for step in selected] == [
        "01",
        "01v",
        "02",
        "03",
        "03c",
        "04",
        "gate1",
        "gate1v",
        "gate2",
        "05",
        "06",
    ]


def test_reversed_stage_range_fails() -> None:
    with pytest.raises(ValueError, match="must not follow"):
        runner._selected_steps("05", "03", "frozen")


@pytest.mark.parametrize(
    ("mode", "expected"),
    [("off", "03"), ("frozen", "03b"), ("live", "03b")],
)
def test_normalization_input_is_explicit(mode: str, expected: str) -> None:
    step = next(step for step in runner.STEPS if step.stage == "03c")
    command = runner._command(step, Path("pipeline"), mode)
    assert command[-2:] == ["--input", expected]


def test_frozen_cache_matches_prompt_and_result_hashes() -> None:
    results, provenance = enrichment._load_frozen_cache(enrichment.FROZEN_LLM_CACHE)
    assert results
    assert provenance["promptSha256"] == enrichment.PROMPT_HASH
    assert provenance["model"] == enrichment.MODEL_ID
    assert provenance["originLimit"]


def test_frozen_cache_rejects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    path.write_text(
        json.dumps(
            {
                "provenance": {
                    "promptSha256": enrichment.PROMPT_HASH,
                    "resultsSha256": "0" * 64,
                },
                "results": {"1": {"page_id": 1}},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="result hash"):
        enrichment._load_frozen_cache(str(path))


def test_frozen_command_never_selects_live_mode() -> None:
    step = next(step for step in runner.STEPS if step.stage == "03b")
    command = runner._command(step, Path("pipeline"), "frozen")
    assert command == [
        sys.executable,
        str(Path("pipeline") / "03b_llm_enrich.py"),
        "--mode",
        "frozen",
    ]


def test_provenance_uses_the_selected_llm_mode() -> None:
    step = next(step for step in runner.POSTPROCESSORS if step.stage == "provenance")
    command = runner._command(step, Path("pipeline"), "frozen")
    assert command[-2:] == ["--llm-mode", "frozen"]


def test_gate_sequence_precedes_public_projection() -> None:
    stages = [step.stage for step in runner.STEPS]
    assert stages.index("gate1") < stages.index("gate1v")
    assert stages.index("gate1v") < stages.index("gate2")
    assert stages.index("gate2") < stages.index("05")
    assert runner.POSTPROCESSORS[-1].stage == "gate2v"


def test_stage01_census_is_a_hard_pipeline_step() -> None:
    step = next(step for step in runner.STEPS if step.stage == "01v")
    assert step.script == "census.py"
    command = runner._command(step, Path("pipeline"), "frozen")
    assert command[-2:] == ["--stage", "01"]


def test_classification_input_is_explicit() -> None:
    step = next(step for step in runner.STEPS if step.stage == "04")
    command = runner._command(step, Path("pipeline"), "frozen")
    assert command[-2:] == ["--input", "03c"]


def test_classification_has_no_existence_fallback() -> None:
    classify = importlib.import_module("04_classify")
    from lib.config import STEP_03_OUTPUT, STEP_03B_OUTPUT, STEP_03C_OUTPUT

    assert classify._input_path("03") == STEP_03_OUTPUT
    assert classify._input_path("03b") == STEP_03B_OUTPUT
    assert classify._input_path("03c") == STEP_03C_OUTPUT


def test_missing_normalization_table_fails_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    normalize = importlib.import_module("03c_normalize")
    monkeypatch.setattr(normalize, "DATA_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="normalization table"):
        normalize.load_json("location_normalize.json")


@pytest.mark.parametrize(
    ("script", "frozen_target"),
    [
        ("reconcile_locations.py", "docs/data/locations.json"),
        ("reconcile_agents.py", "data/provenance/agent-reconciliation.json"),
    ],
)
def test_refreezing_tool_refuses_without_explicit_switch(
    script: str, frozen_target: str
) -> None:
    """Refreezing tools overwrite frozen, hash-bound Gate-2 inputs from the
    network; without the explicit switch they must refuse before any
    network call or write."""
    import hashlib
    import subprocess

    target = Path(frozen_target)
    before = hashlib.sha256(target.read_bytes()).hexdigest()
    result = subprocess.run(
        [sys.executable, str(Path("pipeline") / script)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "REFUSED" in result.stderr
    assert hashlib.sha256(target.read_bytes()).hexdigest() == before
