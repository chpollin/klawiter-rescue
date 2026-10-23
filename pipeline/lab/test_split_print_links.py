from __future__ import annotations

import subprocess
from pathlib import Path

from split_print_links import REPO, split


def test_split_keeps_matches_and_counts_routes():
    data = {
        "about": "local only",
        "pages": {
            "3": {
                "title": "Amok",
                "print": [
                    {"printId": "I/A/1", "route": "field"},
                    {"printId": "I/F/1", "route": "alignment"},
                ],
            },
            "10": {"title": "X", "print": [{"printId": "I/A/2", "route": "field"}]},
        },
    }
    index, files = split(data)
    assert files["3"]["print"][1]["printId"] == "I/F/1"
    assert index["state"] == "proposed"
    assert index["matchesByRoute"] == {"alignment": 1, "field": 2}
    assert list(index["perPage"]) == ["3", "10"]


def test_local_lab_folder_is_ignored_and_untracked():
    local = Path("docs/lab/local")
    tracked = subprocess.run(
        ["git", "ls-files", "--", str(local)], cwd=REPO, capture_output=True, text=True
    )
    assert tracked.stdout.strip() == ""
    assert (
        subprocess.run(
            ["git", "check-ignore", "-q", str(local / "print" / "1.json")], cwd=REPO
        ).returncode
        == 0
    )
