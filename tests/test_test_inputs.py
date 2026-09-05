"""Exercise missing-input behavior through isolated pytest runs."""

import hashlib
import json
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]


@pytest.fixture
def isolated_suite(pytester, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("KLAWITER_REQUIRE_INTERMEDIATES", raising=False)
    source = Path(__file__).with_name("conftest.py").read_text(encoding="utf-8")
    pytester.makeconftest(
        source
        + "\nFRONTEND_JSON = Path(__file__).with_name('frontend.json')\n"
        + "WIKI_GROUND_TRUTH = Path(__file__).with_name('wiki_ground_truth.json')\n"
        + "SEMANTIC_BASELINE_PATH = Path(__file__).with_name('semantic-baseline.json')\n"
        + "STAGE_02_CSV = Path(__file__).with_name('missing_02.csv')\n"
        + "STAGE_04_CSV = Path(__file__).with_name('missing_04.csv')\n"
        + "from types import SimpleNamespace\n"
        + "shutil = SimpleNamespace(which=lambda name: None)\n"
    )
    return pytester


@pytest.mark.parametrize("input_state", ["missing", "malformed"])
def test_required_committed_input_cannot_be_skipped(isolated_suite, input_state):
    if input_state == "malformed":
        (isolated_suite.path / "frontend.json").write_text("{", encoding="utf-8")
    isolated_suite.makepyfile("def test_export(frontend_data): pass")
    result = isolated_suite.runpytest("-q")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*Cannot read required test input*"])


@pytest.mark.parametrize("fixture_name", ["node_executable", "required_intermediates"])
@pytest.mark.parametrize("mode", ["local", "strict", "ci"])
def test_missing_runtime_inputs_fail_in_strict_mode(
    isolated_suite, monkeypatch, fixture_name, mode
):
    if mode == "ci":
        monkeypatch.setenv("CI", "true")
    isolated_suite.makepyfile(f"def test_input({fixture_name}): pass")
    options = ["--require-test-inputs"] if mode == "strict" else []
    result = isolated_suite.runpytest("-q", *options)
    result.assert_outcomes(**({"skipped": 1} if mode == "local" else {"errors": 1}))


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("wrong-hash", "reviewed baseline hash update"),
        ("changed-expectation", "reviewed baseline hash update"),
        ("removed-passing-page", "page inventory changed"),
        ("replaced-page", "page inventory changed"),
        ("duplicate-page", "page inventory changed"),
        ("removed-field", "field inventory changed"),
    ],
)
def test_semantic_oracle_drift_fails_collection(isolated_suite, mutation, error):
    project_root = Path(__file__).parent.parent
    original = (project_root / "tests" / "wiki_ground_truth.json").read_bytes()
    entries = json.loads(original)
    baseline = json.loads(
        (project_root / ".github" / "semantic-baseline.json").read_bytes()
    )
    if mutation == "wrong-hash":
        baseline["groundTruthSha256"] = "incorrect hash"
    elif mutation == "changed-expectation":
        entries[0]["expected"]["title"] = "Invented reference title"
    elif mutation == "removed-passing-page":
        entries = [entry for entry in entries if entry["page_id"] != 33]
    elif mutation == "replaced-page":
        entries[0]["page_id"] = 999999
    elif mutation == "duplicate-page":
        entries[0]["page_id"] = entries[1]["page_id"]
    else:
        del entries[0]["expected"]["translator"]

    content = original if mutation == "wrong-hash" else json.dumps(entries).encode()
    if mutation not in ("wrong-hash", "changed-expectation"):
        # Inventory checks must still fail if someone updates only the hash.
        baseline["groundTruthSha256"] = hashlib.sha256(content).hexdigest()
    (isolated_suite.path / "wiki_ground_truth.json").write_bytes(content)
    (isolated_suite.path / "semantic-baseline.json").write_text(
        json.dumps(baseline), encoding="utf-8"
    )
    isolated_suite.makepyfile("def test_source(wiki_entry): pass")
    result = isolated_suite.runpytest("-q")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines([f"*{error}*"])
