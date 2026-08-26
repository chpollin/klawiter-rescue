"""
Bridge that runs the Node-based check of the edit-layer frontend logic
(tests/evidence_triage.test.js) inside the pytest suite. The JS file pins the
evidence-span matching and triage-hint ordering added by increments 2 and 3;
see its header. Skipped where node is unavailable.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent


def test_evidence_and_triage_logic():
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    result = subprocess.run(
        [node, str(PROJECT_ROOT / "tests" / "evidence_triage.test.js")],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_contested_claim_export_and_display():
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    result = subprocess.run(
        [node, str(PROJECT_ROOT / "tests" / "contested_claims.test.js")],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
