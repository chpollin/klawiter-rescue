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


@pytest.mark.parametrize(
    ("line", "publishers", "locations"),
    [
        # Page 54: a co-imprint of three publishers, each with its seat.
        (
            "'''[1939]: Gottfried Bermann-Fischer Verlag, Stockholm / Uitgeverij "
            "Allert de Lange, Amsterdam / Longmans, Green and Company, "
            "New York/Toronto'''",
            (
                "Gottfried Bermann-Fischer Verlag",
                "Uitgeverij Allert de Lange",
                "Longmans, Green and Company",
            ),
            ("Stockholm", "Amsterdam", "New York/Toronto"),
        ),
        # Page 54: the country qualifies the town, it is not the place.
        (
            "'''[1981]: Buch- und Schallplattenfreunde, Zug, Switzerland'''",
            ("Buch- und Schallplattenfreunde",),
            ("Zug, Switzerland",),
        ),
        # Page 1452: a parallel place name stays one place.
        (
            "'''[1988]: Založništvo tržaškega tiska, Trst/Trieste and Adit, "
            "Ljubljana'''",
            ("Založništvo tržaškega tiska", "Adit"),
            ("Trst/Trieste", "Ljubljana"),
        ),
        # Page 4377: parallel seats after a slash stay one place statement.
        (
            "'''[1921]: Holger Schildts Förlag, Stockholm / Helsingfors'''",
            ("Holger Schildts Förlag",),
            ("Stockholm / Helsingfors",),
        ),
        # Page 4473: a country alone names the country of production.
        ("'''[1984]: Czechoslovakia'''", (), ("Czechoslovakia",)),
    ],
)
def test_header_imprint_pairs(
    line: str, publishers: tuple[str, ...], locations: tuple[str, ...]
) -> None:
    parsed = parse_header_line(line)
    assert len(parsed) == 1
    assert parsed[0].publishers == publishers
    assert parsed[0].locations == locations


def test_an_imprint_after_the_bold_is_read_but_a_sentence_is_not() -> None:
    """Page 1949 sets the imprint after the bold year; page 279 sets a
    description there, which names no publisher of the header's own."""
    imprint = parse_header_line(
        "'''[2010]:''' The Continuum International Publishing Group, New York"
    )[0]
    assert imprint.publishers == ("The Continuum International Publishing Group",)
    assert imprint.locations == ("New York",)
    assert imprint.description is None
    sentence = parse_header_line(
        "'''[2009]'''. Story read by Christoph Maria Herbst. 2 CDs. 146 minutes. "
        "Berlin: Argon Verlag, 2009"
    )[0]
    assert sentence.publishers == ()
    assert sentence.locations == ()
    assert sentence.description.startswith(". Story read by")


def test_a_co_imprint_edition_lists_every_publisher_and_place() -> None:
    edition = segment_page(
        54,
        "'''[1939]: Gottfried Bermann-Fischer Verlag, Stockholm / Uitgeverij "
        "Allert de Lange, Amsterdam'''\n''Ungeduld des Herzens''. 562p.\n",
        "Ungeduld des Herzens",
    )["editions"][0]
    assert edition["schema:publisher"] == [
        "Gottfried Bermann-Fischer Verlag",
        "Uitgeverij Allert de Lange",
    ]
    assert edition["schema:locationCreated"] == ["Stockholm", "Amsterdam"]


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
    # Pages 35, 279, 793 and 2817 joined with their restored human revisions
    # (data/reconciliation/source-revision-decisions.json).
    assert len(corpus["works"]) == 447
    assert len(corpus["editions"]) == 2077
    assert len(corpus["annotations"]) == 2077
    assert all(
        edition["klawiter:reviewStatus"] == "proposed" for edition in corpus["editions"]
    )


ADAPTATION_EDITION = "klawiter:edition/4916-2016-b"
ADAPTATION_WORK = "klawiter:work-candidate/4916-2016-b-adaptation"


def _reviewed(corpus: dict, modeling: dict | None = None) -> dict:
    reconciliation = json.loads(
        Path(EDITION_SAMPLE_RECONCILIATION).read_text(encoding="utf-8")
    )
    if modeling is None:
        modeling = json.loads(
            Path(EDITION_MODELING_DECISIONS).read_text(encoding="utf-8")
        )
    return apply_review_reconciliation(corpus, reconciliation, modeling)


def test_reviewed_sample_overlay_records_the_adaptation_decision(
    edition_corpus,
) -> None:
    """The graphic novel's work binding, open until 2026-09-22, is decided as a
    work of its own: an adaptation of the Schachnovelle whose German edition
    translates the French graphic novel. The claim stays as the record."""
    reviewed = _reviewed(edition_corpus)
    status_counts = {
        status: sum(
            edition["klawiter:reviewStatus"] == status
            for edition in reviewed["editions"]
        )
        for status in ("proposed", "confirmed", "contested")
    }
    assert status_counts == {"proposed": 2001, "confirmed": 76, "contested": 0}
    assert len(reviewed["carriers"]) == 6
    assert len(reviewed["contestedClaims"]) == 1
    assert reviewed["candidateWorks"] == []

    editions = {edition["@id"]: edition for edition in reviewed["editions"]}
    edition = editions[ADAPTATION_EDITION]
    assert edition["schema:exampleOfWork"] == {"@id": ADAPTATION_WORK}
    assert edition["schema:translationOfWork"] == [
        {"@id": "klawiter:edition/675-2015-a"},
        {"@id": "klawiter:edition/5110-2015-a"},
    ]
    assert all(
        target["@id"] in editions for target in edition["schema:translationOfWork"]
    )
    assert edition["klawiter:bindingStatus"] == "decided"
    assert "contested-work-identity" not in edition["klawiter:reviewFlags"]
    assert "extent-differs-across-source-pages" in edition["klawiter:reviewFlags"]
    assert edition["klawiter:hasContestedClaim"] == {
        "@id": "klawiter:claim/work-binding/4916-2016-b"
    }

    claim = reviewed["contestedClaims"][0]
    assert claim["klawiter:claimStatus"] == "resolved"
    assert claim["klawiter:decisionStatus"] == "decided"
    assert claim["klawiter:sourceSliceSha256"] == (
        "ff138801185823a39d7be8c03523c74144f649088592128feac2202979c66bc5"
    )
    assert {
        item["klawiter:proposedObject"]["@id"]: item["klawiter:interpretationStatus"]
        for item in claim["klawiter:interpretation"]
    } == {"klawiter:work/4916": "rejected", ADAPTATION_WORK: "accepted"}
    decision = claim["klawiter:hasReviewAction"][-1]
    assert len(claim["klawiter:hasReviewAction"]) == 4
    assert decision["dcterms:date"] == "2026-09-22"
    assert "revisable" in decision["klawiter:reviewBasis"]
    assert "120p." in claim["klawiter:reviewNote"][0]

    works = {work["@id"]: work for work in reviewed["works"]}
    adaptation = works[ADAPTATION_WORK]
    assert adaptation["schema:isBasedOn"] == {"@id": "klawiter:work/4916"}
    assert adaptation["schema:workExample"] == [{"@id": ADAPTATION_EDITION}]
    assert "klawiter:sourcePageId" not in adaptation
    schachnovelle = {
        item["@id"] for item in works["klawiter:work/4916"]["schema:workExample"]
    }
    assert ADAPTATION_EDITION not in schachnovelle


def test_without_its_resolution_the_claim_stays_open(edition_corpus) -> None:
    """Removing the decision restores the open claim unchanged, so the
    decision is revisable by editing the decision file alone."""
    modeling = json.loads(Path(EDITION_MODELING_DECISIONS).read_text(encoding="utf-8"))
    for claim in modeling["contested_claims"]:
        claim.pop("resolution")
        claim["decision_status"] = "open"
    reviewed = _reviewed(edition_corpus, modeling)
    edition = next(
        item for item in reviewed["editions"] if item["@id"] == ADAPTATION_EDITION
    )
    assert edition["klawiter:reviewStatus"] == "contested"
    assert "schema:exampleOfWork" not in edition
    assert [item["@id"] for item in reviewed["candidateWorks"]] == [ADAPTATION_WORK]
    assert reviewed["contestedClaims"][0]["klawiter:decisionStatus"] == "open"
    assert ADAPTATION_WORK not in {work["@id"] for work in reviewed["works"]}


def test_the_validator_rejects_a_decision_the_graph_does_not_carry_out(
    edition_corpus,
) -> None:
    from validate_editions import _check_contested_claims

    reviewed = _reviewed(edition_corpus)
    assert _check_contested_claims(reviewed) == []

    unbound = deepcopy(reviewed)
    for work in unbound["works"]:
        if work["@id"] == "klawiter:work/4916":
            work["schema:workExample"].append({"@id": ADAPTATION_EDITION})
    errors = _check_contested_claims(unbound)
    assert any("rejected work still lists" in error for error in errors), errors

    undecided = deepcopy(reviewed)
    undecided["contestedClaims"][0]["klawiter:interpretation"][0][
        "klawiter:interpretationStatus"
    ] = "accepted"
    errors = _check_contested_claims(undecided)
    assert any("exactly one reading" in error for error in errors), errors


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
