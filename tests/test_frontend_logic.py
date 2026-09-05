"""Run every frontend behavior test and syntax-check every shipped JS module."""

import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BEHAVIOR_TESTS = sorted((PROJECT_ROOT / "tests").glob("*.test.js"))
JS_MODULES = sorted((PROJECT_ROOT / "docs" / "js").glob("*.js"))


def test_frontend_test_inventory_is_nonempty():
    assert BEHAVIOR_TESTS, "No frontend behavior tests discovered"
    assert JS_MODULES, "No shipped frontend modules discovered"


@pytest.mark.parametrize("path", BEHAVIOR_TESTS, ids=lambda p: p.name)
def test_frontend_behavior(node_executable, path):
    result = subprocess.run(
        [node_executable, "--test", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("path", JS_MODULES, ids=lambda p: p.name)
def test_frontend_syntax(node_executable, path):
    result = subprocess.run(
        [node_executable, "--check", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
