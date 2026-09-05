"""Gate-1 Work and Edition model, parser, and real-corpus regression tests."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from lib.config import (
    EDITION_MODELING_DECISIONS,
    EDITION_SAMPLE_RECONCILIATION,
)
from lib.editions import (
    _letter_suffix,
    apply_review_reconciliation,
    build_corpus,
    count_edition_headers,
    parse_header_line,
    segment_page,
)

SAMPLES = Path("data/output/edition-samples")


@pytest.fixture(scope="module")
def _edition_corpus(source_rows):
    return build_corpus(source_rows)


@pytest.fixture
def edition_corpus(_edition_corpus):
    """Share the expensive build, but isolate tests that apply review overlays."""
    return deepcopy(_edition_corpus)


@pytest.mark.parametrize(
    ("line", "publisher", "location", "series", "description"),
    [
        (
            "'''[1952]: S. Fischer Verlag. Frankfurt am Main''' [S. Fischer Bibliothek]",
            "S. Fischer Verlag",
            "Frankfurt am Main",
            "[S. Fischer Bibliothek]",
            None,
        ),
        (
            "'''[1978]: S. Fischer Verlag, Frankfurt am Main''' Special edition",
            "S. Fischer Verlag",
            "Frankfurt am Main",
            None,
            "Special edition",
        ),
        (
            "'''[1981]: S. Fischer Verlag, Frankfurt am Main [Gesammelte Werke in Einzelbänden]",
            "S. Fischer Verlag",
            "Frankfurt am Main",
            "[Gesammelte Werke in Einzelbänden]",
            None,
        ),
        (
            "'''[1981]: S. Fischer Verlag, Frankfurt am Main]]]",
            "S. Fischer Verlag",
            "Frankfurt am Main",
            None,
            None,
        ),
    ],
)
def test_reviewed_header_repairs(
    line: str,
    publisher: str,
    location: str,
    series: str | None,
    description: str | None,
) -> None:
    parsed = parse_header_line(line)
    assert len(parsed) == 1
    assert parsed[0].publisher == publisher
    assert parsed[0].location == location
    assert parsed[0].series == series
    assert parsed[0].description == description


def test_compound_header_preserves_two_source_bound_proposals() -> None:
    parsed = parse_header_line(
        "'''[1960]: Deutscher Bücherbund, Düsseldorf / "
        "[1964]: Ex Libris Verlag, Zürich'''"
    )
    assert [(item.year, item.publisher, item.location) for item in parsed] == [
        (1960, "Deutscher Bücherbund", "Düsseldorf"),
        (1964, "Ex Libris Verlag", "Zürich"),
    ]
    assert all("compound-header" in item.flags for item in parsed)


def test_numeric_reference_headers_are_not_editions() -> None:
    text = "'''[1]'''. Citation\n'''[1960]: Publisher, Wien'''\n"
    assert count_edition_headers(text) == 1


@pytest.mark.parametrize(
    ("index", "suffix"),
    [(1, "a"), (26, "z"), (27, "aa"), (28, "ab"), (52, "az")],
)
def test_identifier_suffix_extends_beyond_z(index: int, suffix: str) -> None:
    assert _letter_suffix(index) == suffix


@pytest.mark.parametrize(
    ("slug", "page_id", "expected"),
    [
        ("ungeduld_p54", 54, 31),
        ("schachnovelle_p4916", 4916, 25),
        ("welt-von-gestern_p56", 56, 20),
    ],
)
def test_sample_boundaries_and_selectors(
    slug: str, page_id: int, expected: int
) -> None:
    text = (SAMPLES / f"{slug}.wiki.txt").read_text(encoding="utf-8")
    result = segment_page(page_id, text, slug)
    assert len(result["editions"]) == expected
    assert len(result["annotations"]) == expected
    for edition, annotation in zip(
        result["editions"], result["annotations"], strict=True
    ):
        selector = annotation["oa:hasTarget"]["oa:hasSelector"]
        block = text[selector["oa:start"] : selector["oa:end"]]
        assert block.startswith(edition["klawiter:headerLine"])
        assert annotation["oa:hasBody"]["@id"] == edition["@id"]


def test_real_corpus_selection_and_output_counts(edition_corpus) -> None:
    corpus = edition_corpus
    assert len(corpus["works"]) == 443
    assert len(corpus["editions"]) == 1886
    assert len(corpus["annotations"]) == 1886
    assert all(
        edition["klawiter:reviewStatus"] == "proposed" for edition in corpus["editions"]
    )


def test_reviewed_sample_overlay_preserves_contested_claim(edition_corpus) -> None:
    corpus = edition_corpus
    reconciliation = json.loads(
        Path(EDITION_SAMPLE_RECONCILIATION).read_text(encoding="utf-8")
    )
    modeling = json.loads(Path(EDITION_MODELING_DECISIONS).read_text(encoding="utf-8"))
    reviewed = apply_review_reconciliation(corpus, reconciliation, modeling)
    status_counts = {
        status: sum(
            edition["klawiter:reviewStatus"] == status
            for edition in reviewed["editions"]
        )
        for status in ("proposed", "confirmed", "contested")
    }
    assert status_counts == {"proposed": 1810, "confirmed": 75, "contested": 1}
    assert len(reviewed["carriers"]) == 6
    assert len(reviewed["contestedClaims"]) == 1
    assert len(reviewed["candidateWorks"]) == 1

    editions = {edition["@id"]: edition for edition in reviewed["editions"]}
    contested = editions["klawiter:edition/4916-2016-b"]
    assert "schema:exampleOfWork" not in contested
    assert contested["klawiter:hasContestedClaim"] == {
        "@id": "klawiter:claim/work-binding/4916-2016-b"
    }
    claim = reviewed["contestedClaims"][0]
    assert claim["klawiter:decisionStatus"] == "open"
    assert claim["klawiter:sourceSliceSha256"] == (
        "ff138801185823a39d7be8c03523c74144f649088592128feac2202979c66bc5"
    )
    assert {
        item["klawiter:proposedObject"]["@id"]
        for item in claim["klawiter:interpretation"]
    } == {
        "klawiter:work/4916",
        "klawiter:work-candidate/4916-2016-b-adaptation",
    }
    assert len(claim["klawiter:hasReviewAction"]) == 3
    work = next(
        work for work in reviewed["works"] if work["@id"] == "klawiter:work/4916"
    )
    assert {item["@id"] for item in work["schema:workExample"]}.isdisjoint(
        {contested["@id"]}
    )


@pytest.mark.parametrize(
    ("edition_id", "page_count", "raw"),
    [
        ("klawiter:edition/4916-1995-a", 80, "(80)p."),
        ("klawiter:edition/56-2010-a", 463, "463/1)p."),
    ],
)
def test_reviewed_page_count_repairs(
    edition_corpus, edition_id: str, page_count: int, raw: str
) -> None:
    corpus = edition_corpus
    edition = next(item for item in corpus["editions"] if item["@id"] == edition_id)
    assert edition["schema:numberOfPages"] == page_count
    assert edition["klawiter:pageCountRaw"] == raw
    assert "normalized-page-count-notation" in edition["klawiter:reviewFlags"]


def test_generated_validation_report_passes() -> None:
    report = json.loads(
        Path("data/output/editions/validation-report.json").read_text(encoding="utf-8")
    )
    assert report["allChecksPass"] is True
    assert all(report["checks"].values())


def test_committed_edition_graph_expands_to_rdf() -> None:
    """Guard against silently dropped @context terms.

    Undefined top-level container keys once collapsed the published dataset
    to 6 RDF triples, so the SHACL gate validated an empty graph and reported
    conformance over nothing (defect found 2026-08-26).
    """
    from rdflib import Graph

    graph = Graph()
    graph.parse("data/output/editions/work-editions.jsonld", format="json-ld")
    assert len(graph) > 45_000
