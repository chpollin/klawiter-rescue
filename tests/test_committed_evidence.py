"""Reviewed gate references must survive regeneration and reject evidence drift."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import verify_committed_evidence as evidence


@pytest.fixture
def snapshot(tmp_path):
    references = {}

    def artifact(relative, content=b"reviewed bytes"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return hashlib.sha256(content).hexdigest()

    for relative in evidence.MANIFESTS:
        gate = Path(relative).parent.name
        document = {key: {} for key in evidence.REQUIRED[gate]}
        document.update(
            algorithmVersion="1.0",
            codeSha256="reviewed-code",
            counts={"reviewCases": 2},
            generatedAt="2026-09-05T10:00:00Z",
            validation={"deterministicRebuild": True},
        )
        names = evidence.TIMESTAMPED_ARTIFACTS | {"review-queue.json"}
        names |= {"work-editions.jsonld" if gate == "editions" else "candidates.json"}
        document["artifacts"] = {
            name: artifact(str(Path(relative).parent / name)) for name in names
        }
        source = {"path": f"inputs/{gate}.json"}
        source["sha256"] = artifact(source["path"])
        if gate == "editions":
            document["source"] = source
        else:
            document["inputs"] = {"classified-source": source}
        references[relative] = document
        (tmp_path / relative).write_text(json.dumps(document), encoding="utf-8")
    return tmp_path, references


def rewrite(root, relative, mutate):
    path = root / relative
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_reviewed_snapshot_passes(snapshot):
    evidence.verify(*snapshot)


def test_equal_numeric_values_with_different_json_types_are_drift():
    assert evidence.changed_paths({"count": 1}, {"count": True}) == ["count"]
    assert evidence.changed_paths({"items": [1]}, {"items": [1.0]}) == ["items[0]"]


@pytest.mark.parametrize("name", ["candidates.json", "review-queue.json"])
def test_ignored_artifact_changes_fail_with_or_without_updated_hash(snapshot, name):
    root, references = snapshot
    relative = evidence.MANIFESTS[1]
    artifact = root / Path(relative).parent / name
    artifact.write_bytes(b"different candidates or queue")
    with pytest.raises(ValueError, match="hash mismatch"):
        evidence.verify(root, references)
    rewrite(
        root,
        relative,
        lambda doc: doc["artifacts"].update(
            {name: hashlib.sha256(artifact.read_bytes()).hexdigest()}
        ),
    )
    with pytest.raises(ValueError, match="reviewed manifest drift"):
        evidence.verify(root, references)


@pytest.mark.parametrize(
    "relative",
    [
        "inputs/editions.json",
        "inputs/reconciliation.json",
        "data/output/reconciliation/candidates.json",
        "data/output/reconciliation/review-queue.json",
        "data/output/editions/manifest.json",
    ],
)
def test_missing_required_file_fails(snapshot, relative):
    root, references = snapshot
    (root / relative).unlink()
    with pytest.raises(FileNotFoundError):
        evidence.verify(root, references)


@pytest.mark.parametrize(
    "change",
    [
        lambda doc: doc.update(codeSha256="changed-code"),
        lambda doc: doc["counts"].update(reviewCases=3),
        lambda doc: doc["inputs"]["classified-source"].update(sha256="changed-input"),
        lambda doc: doc["inputs"]["classified-source"].pop("sha256"),
        lambda doc: doc["counts"].pop("reviewCases"),
        lambda doc: doc["artifacts"].pop("candidates.json"),
        lambda doc: doc["artifacts"].pop("earl.jsonld"),
        lambda doc: doc.pop("generatedAt"),
        lambda doc: doc.pop("inputs"),
        lambda doc: doc.update(unreviewedNewKey=True),
    ],
)
def test_stable_drift_and_missing_keys_fail(snapshot, change):
    root, references = snapshot
    rewrite(root, evidence.MANIFESTS[1], change)
    with pytest.raises(ValueError):
        evidence.verify(root, references)


def test_only_explicit_timestamp_fields_may_change(snapshot):
    root, references = snapshot
    frozen = copy.deepcopy(references)
    for relative in evidence.MANIFESTS:

        def change(document):
            document["generatedAt"] = "2026-09-06T10:00:00Z"
            for name in evidence.TIMESTAMPED_ARTIFACTS:
                path = root / Path(relative).parent / name
                path.write_bytes(b"new run timestamp")
                document["artifacts"][name] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()

        rewrite(root, relative, change)
    evidence.verify(root, references)
    assert references == frozen


def test_changed_input_bytes_fail_without_manifest_change(snapshot):
    root, references = snapshot
    (root / "inputs/reconciliation.json").write_bytes(b"unreviewed input")
    with pytest.raises(ValueError, match="inputs/reconciliation.json"):
        evidence.verify(root, references)


def test_cli_uses_head_reference_and_fails_if_git_reference_missing(
    snapshot, monkeypatch
):
    root, references = snapshot
    monkeypatch.setattr(evidence, "__file__", str(root / "pipeline/verify.py"))
    monkeypatch.setattr(sys, "argv", ["verify"])
    seen = []

    def committed(command, cwd):
        assert cwd == root
        assert command[:2] == ["git", "show"]
        assert command[2].startswith("HEAD:")
        seen.append(command[2])
        return json.dumps(references[command[2][5:]]).encode()

    monkeypatch.setattr(subprocess, "check_output", committed)
    assert evidence.main() == 0
    assert len(seen) == 2
    rewrite(
        root, evidence.MANIFESTS[1], lambda doc: doc["counts"].update(reviewCases=5)
    )
    assert evidence.main() == 1

    def missing(command, cwd):
        raise subprocess.CalledProcessError(128, command)

    monkeypatch.setattr(subprocess, "check_output", missing)
    assert evidence.main() == 1
