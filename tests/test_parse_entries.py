"""
Unit tests for pipeline/03_parse_entries.py process_entry.

The module has a digit in its filename and is loaded via importlib, the same
mechanism the pipeline runner uses for numbered steps. These tests pin the
blanked-stub title behavior (entry 2979): a page whose BLOB content was emptied
at the source must still be shown with its surviving page title, not as
"Untitled" (editor decision).
"""

import importlib.util
import os

import pytest

PIPELINE_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "pipeline")


def _load_03():
    path = os.path.abspath(os.path.join(PIPELINE_DIR, "03_parse_entries.py"))
    spec = importlib.util.spec_from_file_location("parse_03", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def m():
    return _load_03()


def _row(**over):
    row = {
        "page_id": "2979",
        "page_namespace": "0",
        "page_title": "",
        "text_id": "",
        "blob_id": "",
        "content": "",
    }
    row.update(over)
    return row


class TestBlankedStubTitle:
    def test_blanked_page_keeps_its_title(self, m):
        # entry 2979: empty content, title survives in the page table.
        r = m.process_entry(_row(page_title="A unidade espiritual do mundo"))
        assert r["title"] == "A unidade espiritual do mundo"
        assert r["raw_content"] == ""

    def test_blanked_page_without_title_stays_empty(self, m):
        r = m.process_entry(_row(page_title=""))
        assert r["title"] == ""

    def test_blanked_page_title_wiki_markup_stripped(self, m):
        r = m.process_entry(_row(page_title="''A unidade''"))
        assert r["title"] == "A unidade"
