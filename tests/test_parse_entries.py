"""Regression checks for page-level parsing decisions."""

import importlib

import pytest
from lib.config import STEP_02_OUTPUT, load_csv


@pytest.fixture(scope="module")
def parser():
    return importlib.import_module("03_parse_entries")


def _row(**overrides):
    row = {
        "page_id": "2979",
        "page_namespace": "0",
        "page_title": "",
        "text_id": "",
        "blob_id": "",
        "content": "",
    }
    row.update(overrides)
    return row


def test_blanked_page_keeps_its_title(parser) -> None:
    parsed = parser.process_entry(_row(page_title="A unidade espiritual do mundo"))
    assert parsed["title"] == "A unidade espiritual do mundo"
    assert parsed["raw_content"] == ""


def test_blanked_page_without_title_stays_empty(parser) -> None:
    assert parser.process_entry(_row())["title"] == ""


def test_blanked_page_title_wiki_markup_is_stripped(parser) -> None:
    assert parser.process_entry(_row(page_title="''A unidade''"))["title"] == (
        "A unidade"
    )


@pytest.mark.usefixtures("required_intermediates")
def test_approximate_year_header_is_not_used_as_title() -> None:
    parser = importlib.import_module("03_parse_entries")
    row = next(item for item in load_csv(STEP_02_OUTPUT) if item["page_id"] == "54")
    parsed = parser.process_entry(row)
    assert parsed["title"] == "Ungeduld des Herzens (VIST)"
