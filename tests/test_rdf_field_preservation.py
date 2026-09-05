"""Field-level RDF coverage for edition summaries and authority evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from lib.editions import build_corpus
from lib.reconciliation import build_reconciliation
from rdflib import RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef
from reconcile_entities import CONTESTED_CONTEXT

KLAWITER = Namespace("https://chpollin.github.io/klawiter-rescue/vocab/")
SOURCE_PATH = "data/intermediate/04_classified.csv"
HEADER = "'''[1950]: Original Press, Wien'''"
TRANSLATION = "Translated by Iso Velikanović."


def _rdf(document: dict) -> Graph:
    return Graph().parse(data=json.dumps(document), format="json-ld")


def _iri(identifier: str) -> URIRef:
    return URIRef(identifier.replace("klawiter:", str(KLAWITER), 1))


def test_every_page_summary_field_survives_rdf_conversion() -> None:
    corpus = build_corpus(
        [
            {
                "page_id": "101",
                "text_id": "1234",
                "page_title": "First work",
                "content": (
                    "'''[1950]: First Press, Wien'''\n100p.\n\n"
                    "'''[1951]: Second Press, Paris'''\n101p.\n"
                ),
            },
            {
                "page_id": "102",
                "text_id": "",
                "page_title": "Second work",
                "content": (
                    "'''[1950]: First Press, Wien / "
                    "[1951]: Second Press, Berlin'''\n100p.\n\n"
                    "'''[1952]: Third Press, Zürich'''\n102p.\n"
                ),
            },
        ]
    )
    expected = [
        {
            "sourcePageId": 101,
            "sourceTextId": 1234,
            "headerCount": 2,
            "editionCount": 2,
            "reviewFlagCount": 0,
        },
        {
            "sourcePageId": 102,
            "sourceTextId": None,
            "headerCount": 2,
            "editionCount": 3,
            "reviewFlagCount": 2,
        },
    ]
    assert corpus["pageSummaries"] == expected
    graph = _rdf(corpus)
    summary_nodes = set(
        graph.objects(KLAWITER["dataset/work-editions"], KLAWITER.pageSummaries)
    )
    assert len(summary_nodes) == len(expected)
    for summary in expected:
        matches = summary_nodes.intersection(
            graph.subjects(KLAWITER.sourcePageId, Literal(summary["sourcePageId"]))
        )
        assert len(matches) == 1
        node = matches.pop()
        for key, value in summary.items():
            objects = set(graph.objects(node, KLAWITER[key]))
            assert objects == (set() if value is None else {Literal(value)})
    assert corpus["pageSummaries"] == expected


@pytest.fixture(scope="module")
def authority_claims() -> list[dict]:
    def unresolved(**subject: str) -> dict:
        return {
            "decisionId": "test/" + next(iter(subject.values())),
            "action": "unresolved",
            "decidedBy": "Test reviewer",
            "decidedAt": "2026-09-05T00:00:00Z",
            "evidence": ["Synthetic source fixture"],
            **subject,
        }

    result = build_reconciliation(
        edition_dataset={
            "works": [
                {
                    "@id": "klawiter:work/101",
                    "klawiter:sourcePageId": 101,
                    "schema:name": "Known Work",
                }
            ]
        },
        locations={"Wien": {"lat": 0, "lng": 0}},
        location_log=[],
        location_review={},
        location_decisions={"decisions": [unresolved(subject="Wien")]},
        work_decisions={"decisions": [unresolved(subjectId="klawiter:work/101")]},
        szd_authorities=[],
        source_rows=[
            {
                "page_id": "101",
                "text_id": "1234",
                "raw_content": HEADER + "\n" + TRANSLATION,
                "translator": "Iso Velikanović",
                "publisher": "Normalized Press",
            }
        ],
        agent_reconciliation={
            "agents": [
                {"kind": "person", "name": "Iso Velikanović", "occurrences": 1},
                {"kind": "publisher", "name": "Normalized Press", "occurrences": 1},
            ]
        },
        agent_decisions={
            "decisions": [
                unresolved(entityType="person", subject="Iso Velikanović"),
                unresolved(entityType="publisher", subject="Normalized Press"),
            ]
        },
    )
    return result["contestedClaims"]


@pytest.mark.parametrize("kind", ["location", "person", "publisher", "work"])
def test_contested_source_evidence_survives_rdf_conversion(
    authority_claims: list[dict], kind: str
) -> None:
    claim = next(
        item for item in authority_claims if item["klawiter:identityScope"] == kind
    )
    assert len(claim["klawiter:sourceEvidence"]) == 1
    source = claim["klawiter:sourceEvidence"][0]
    expected = {"sourcePageId": 101}
    if kind == "work":
        expected["sourceTitle"] = "Known Work"
    else:
        expected.update(sourceTextId=1234, sourcePath=SOURCE_PATH)
        if kind == "publisher":
            expected.update(
                sourceLine=None,
                sourceValue="Normalized Press",
                sourceMatchMode="field-value",
                sourceField="publisher",
            )
        else:
            line = HEADER if kind == "location" else TRANSLATION
            expected.update(
                sourceLine=1 if kind == "location" else 2,
                sourceValue="Wien" if kind == "location" else "Iso Velikanović",
                sourceMatchMode="exact-string"
                if kind == "location"
                else "field-value-line",
                sourceText=line,
                sourceTextSha256=hashlib.sha256(line.encode("utf-8")).hexdigest(),
            )
            if kind == "person":
                expected["sourceField"] = "translator"
    assert {key: value for key, value in source.items() if key != "@id"} == expected

    graph = _rdf({**CONTESTED_CONTEXT, "@graph": authority_claims})
    evidence_node = _iri(source["@id"])
    assert (_iri(claim["@id"]), KLAWITER.sourceEvidence, evidence_node) in graph
    expected_triples = {
        (KLAWITER[key], Literal(value))
        for key, value in expected.items()
        if value is not None
    }
    assert set(graph.predicate_objects(evidence_node)) == expected_triples
    assert {key: value for key, value in source.items() if key != "@id"} == expected


@pytest.mark.parametrize(
    ("term", "datatype"),
    [
        ("bindingStatus", XSD.string),
        ("headerSeries", XSD.string),
        ("reviewContract", XSD.string),
        ("reviewDecision", XSD.string),
        ("reviewEvidenceSha256", XSD.string),
        ("headerCount", XSD.integer),
        ("editionCount", XSD.integer),
        ("reviewFlagCount", XSD.integer),
        ("sourceText", XSD.string),
        ("sourceMatchMode", XSD.string),
    ],
)
def test_restored_rdf_properties_are_registered(term: str, datatype: URIRef) -> None:
    register = Path(__file__).resolve().parents[1] / "docs/vocab/klawiter.ttl"
    graph = Graph().parse(register, format="turtle")
    predicate = KLAWITER[term]
    assert (predicate, RDF.type, RDF.Property) in graph
    assert (predicate, RDFS.range, datatype) in graph
    assert (predicate, RDFS.isDefinedBy, KLAWITER[""]) in graph
    assert graph.value(predicate, RDFS.label, any=False)
    assert graph.value(predicate, RDFS.comment, any=False)
