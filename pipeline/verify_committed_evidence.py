"""Compare rebuilt gates with reviewed manifests without refreshing the reference."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

MANIFESTS = (
    "data/output/editions/manifest.json",
    "data/output/reconciliation/manifest.json",
)
TIMESTAMPED_ARTIFACTS = {
    "earl.jsonld",
    "provenance.jsonld",
    "validation-report.json",
}
REQUIRED = {
    "editions": {
        "algorithmVersion",
        "artifacts",
        "authorityEvidence",
        "codeSha256",
        "counts",
        "generatedAt",
        "reviewEvidence",
        "selectionRule",
        "source",
        "validation",
    },
    "reconciliation": {
        "algorithmVersion",
        "artifacts",
        "codeSha256",
        "counts",
        "frontendArtifact",
        "generatedAt",
        "inputs",
        "operatorPoints",
        "validation",
    },
}


def stable_manifest(document: dict, gate: str) -> dict:
    """Drop only the explicit run-dependent values, never their required keys."""
    missing = REQUIRED[gate] - document.keys()
    if missing:
        raise ValueError(f"{gate}: missing manifest keys: {sorted(missing)}")
    if not isinstance(document["generatedAt"], str) or not document["generatedAt"]:
        raise ValueError(f"{gate}: missing run timestamp")
    stable = copy.deepcopy(document)
    del stable["generatedAt"]
    for name in TIMESTAMPED_ARTIFACTS:
        if name not in stable["artifacts"]:
            raise ValueError(f"{gate}: missing artifact hash: {name}")
        del stable["artifacts"][name]
    return stable


def changed_paths(expected, actual, prefix="") -> list[str]:
    if type(expected) is not type(actual):
        return [prefix]
    if isinstance(expected, dict) and isinstance(actual, dict):
        changes = []
        for key in sorted(expected.keys() | actual.keys()):
            path = f"{prefix}.{key}" if prefix else key
            if key not in expected or key not in actual:
                changes.append(path)
            else:
                changes.extend(changed_paths(expected[key], actual[key], path))
        return changes
    if isinstance(expected, list) and len(expected) == len(actual):
        return [
            path
            for index, (before, after) in enumerate(zip(expected, actual, strict=True))
            for path in changed_paths(before, after, f"{prefix}[{index}]")
        ]
    return [] if expected == actual else [prefix]


def verify_file(root: Path, relative: str, expected: str) -> None:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Manifest path escapes repository: {relative}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise ValueError(f"Artifact/input hash mismatch: {relative}")


def verify_references(root: Path, value) -> None:
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            verify_file(root, value["path"], value["sha256"])
        for child in value.values():
            verify_references(root, child)
    elif isinstance(value, list):
        for child in value:
            verify_references(root, child)


def verify(root: Path, references: dict[str, dict]) -> None:
    for relative in MANIFESTS:
        gate = Path(relative).parent.name
        actual = json.loads((root / relative).read_text(encoding="utf-8"))
        expected = references[relative]
        changes = changed_paths(
            stable_manifest(expected, gate), stable_manifest(actual, gate)
        )
        if changes:
            raise ValueError(f"{gate}: reviewed manifest drift: {', '.join(changes)}")
        for name, digest in actual["artifacts"].items():
            verify_file(root, str(Path(relative).parent / name), digest)
        verify_references(root, actual)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference-dir",
        type=Path,
        help="Explicit local review snapshot root; CI always uses committed HEAD blobs.",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    try:
        references = {}
        for relative in MANIFESTS:
            if args.reference_dir:
                raw = (args.reference_dir / relative).read_bytes()
            else:
                raw = subprocess.check_output(
                    ["git", "show", f"HEAD:{relative}"], cwd=root
                )
            references[relative] = json.loads(raw)
        verify(root, references)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Committed evidence verification failed: {exc}")
        return 1
    print("Both gate manifests and their referenced bytes match reviewed evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
