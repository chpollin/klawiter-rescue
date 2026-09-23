"""The archival dump the pipeline reads must be the inventoried one."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INVENTORY = ROOT / "data" / "provenance" / "source-dump.json"


def test_raw_dump_matches_its_inventory():
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    listed = {entry["path"]: entry for entry in inventory["files"]}
    present = {
        p.relative_to(ROOT).as_posix() for p in (ROOT / "data" / "raw").iterdir()
    }
    assert present == set(listed), "raw dump and inventory list different files"
    for path, entry in listed.items():
        content = (ROOT / path).read_bytes()
        assert len(content) == entry["bytes"], path
        assert hashlib.sha256(content).hexdigest() == entry["sha256"], path
