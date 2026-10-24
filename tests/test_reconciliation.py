"""Gate-2 proposal, decision, publication, and EIL feedback contracts."""

from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path

import pytest
from lib.config import (
    AGENT_DECISIONS,
    AGENT_RECONCILIATION,
    LOCATION_DECISIONS,
    LOCATION_RECONCILIATION_LOG,
    LOCATION_REVIEW_EVIDENCE,
    LOCATIONS_JSON,
    OUTPUT_EDITIONS_DIR,
    SOURCE_REVISION_DECISIONS,
    SZD_WORK_INDEX,
    WORK_DECISIONS,
)
from lib.reconciliation import (
    _folded_source_lines,
    build_location_candidates,
    build_reconciliation,
    load_reconciliation_patches,
    merge_decision_patches,
    parse_szd_work_index,
)


@pytest.fixture(scope="session")
def reconciliation(classified_rows) -> dict:
    def read(path: str | Path) -> dict | list:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    return build_reconciliation(
        read(Path(OUTPUT_EDITIONS_DIR) / "work-editions.jsonld"),
        read(LOCATIONS_JSON),
        read(LOCATION_RECONCILIATION_LOG),
        read(LOCATION_REVIEW_EVIDENCE),
        read(LOCATION_DECISIONS),
        read(WORK_DECISIONS),
        parse_szd_work_index(Path(SZD_WORK_INDEX)),
        classified_rows,
        read(AGENT_RECONCILIATION),
        read(AGENT_DECISIONS),
        read(SOURCE_REVISION_DECISIONS),
    )


def _as_person(document: dict) -> dict:
    """The decision file with every decision of every chain recorded by a
    person, the producer whose confirm or correct publishes a link."""
    document = copy.deepcopy(document)
    for decision in document["decisions"]:
        current = decision
        while current:
            current["decidedBy"] = "Editor (SZD)"
            current = current.get("supersedes")
    return document


@pytest.fixture(scope="session")
def person_reconciliation() -> dict:
    """The same decisions as if a person had made them. The occurrence scan
    and the source-revision claims are left out; publication depends on
    neither."""

    def read(path: str | Path) -> dict | list:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    return build_reconciliation(
        read(Path(OUTPUT_EDITIONS_DIR) / "work-editions.jsonld"),
        read(LOCATIONS_JSON),
        read(LOCATION_RECONCILIATION_LOG),
        read(LOCATION_REVIEW_EVIDENCE),
        _as_person(read(LOCATION_DECISIONS)),
        _as_person(read(WORK_DECISIONS)),
        parse_szd_work_index(Path(SZD_WORK_INDEX)),
        [],
        {"agents": []},
        {"decisions": []},
        {"decisions": []},
    )


def test_frozen_szd_index_and_work_links(
    reconciliation: dict, person_reconciliation: dict
) -> None:
    """The three work decisions of the independent verification agent are
    proposals; recorded by a person, the same decisions would publish."""
    assert len(parse_szd_work_index(Path(SZD_WORK_INDEX))) == 590
    assert reconciliation["publishable"]["works"] == {}
    works = person_reconciliation["publishable"]["works"]
    assert {work_id: link["szdId"] for work_id, link in works.items()} == {
        "klawiter:work/54": "SZDWRK.133",
        "klawiter:work/56": "SZDWRK.5",
        "klawiter:work/4916": "SZDWRK.39",
    }


def _location_decisions() -> list[dict]:
    path = Path(__file__).resolve().parent.parent / "data" / "reconciliation"
    return json.loads((path / "location-decisions.json").read_text(encoding="utf-8"))[
        "decisions"
    ]


def _decided(action_set: set[str]) -> set[str]:
    return {d["subject"] for d in _location_decisions() if d["action"] in action_set}


def _held_open() -> set[str]:
    """Places whose decision chain held them open; no person or rule has
    closed any of them, so each is an open claim."""
    subjects = set()
    for decision in _location_decisions():
        current = decision
        while current:
            if current["action"] == "unresolved":
                subjects.add(decision["subject"])
            current = current.get("supersedes")
    return subjects


def test_llm_agent_decisions_publish_no_place_link(
    reconciliation: dict, person_reconciliation: dict
) -> None:
    """Every place decision is an LLM agent's, so none publishes; the same
    confirm and correct decisions by a person would. A subject with a
    candidate but no decision, such as La Tour d'Aigues, publishes neither."""
    assert reconciliation["publishable"]["locations"] == {}
    states = reconciliation["decisions"]["decisionStates"]
    assert {item["producer"] for item in states.values()} == {"llm-agent"}
    assert {item["decisionState"] for item in states.values()} == {
        "proposed",
        "contested",
    }
    published = person_reconciliation["publishable"]["locations"]
    assert set(published) == _decided({"confirm", "correct"})
    undecided = next(
        item
        for item in reconciliation["candidates"]["locations"]
        if item["sourceLocation"] == "La Tour d'Aigues"
    )
    assert undecided["candidates"] and not undecided.get("decision")
    assert "La Tour d'Aigues" not in published


def test_wrong_legacy_qids_are_replaced_fail_closed(
    person_reconciliation: dict,
) -> None:
    published = person_reconciliation["publishable"]["locations"]
    assert published["Rio de Janiero"]["qid"] == "Q8678"
    assert published["Yanji"]["qid"] == "Q713362"
    assert published["Bambaī"]["qid"] == "Q1156"
    serialized = json.dumps(published)
    assert "Q2720540" not in serialized
    assert "Q26085641" not in serialized


def test_agent_candidates_are_fail_closed(reconciliation: dict) -> None:
    """101 frozen agent subjects join the review pool; without a single
    decision nothing publishes and every subject queues."""
    agents = reconciliation["candidates"]["agents"]
    assert len(agents) == 101
    assert all(subject["decision"] is None for subject in agents)
    assert reconciliation["publishable"]["agents"] == {}
    queued = {
        (case["entityType"], case["subject"])
        for case in reconciliation["queue"]["cases"]
    }
    assert all(
        (subject["entityType"], subject["sourceName"]) in queued for subject in agents
    )


def test_unresolved_and_unreviewed_cases_remain_in_complete_queue(
    reconciliation: dict,
) -> None:
    queue = reconciliation["queue"]
    # Only a decision by a person or an exact rule takes a subject out of the
    # queue, and none exists, so every place, work and agent subject queues;
    # an LLM agent's decision waits beside its candidates.
    candidates = reconciliation["candidates"]
    assert queue["caseCount"] == sum(
        len(candidates[kind]) for kind in ("locations", "works", "agents")
    )
    queued = {(item["entityType"], item["subject"]): item for item in queue["cases"]}
    assert queued[("location", "Saint-Aignan")]["status"] == "unresolved"
    assert queued[("location", "Tyresö")]["status"] == "unresolved"
    work = queued[("work", "klawiter:work/54")]
    assert work["status"] == "proposed"
    assert work["proposedDecision"]["decidedBy"] == "independent-verification-agent"


def test_unresolved_decisions_are_explicit_contested_claims(
    reconciliation: dict,
) -> None:
    claims = [
        claim
        for claim in reconciliation["contestedClaims"]
        if claim["klawiter:decisionStatus"] == "open"
        and claim["klawiter:identityScope"] == "location"
    ]
    names = {claim["klawiter:claimSubject"]["schema:name"] for claim in claims}
    # An LLM agent's later decision closes no claim (Tyresö, Kuwait and the
    # compound places, decided by the main instance on 2026-09-23).
    assert names == _held_open()
    assert {"Saint-Aignan", "Tyresö", "Kuwait"} <= names
    assert all(claim["klawiter:claimStatus"] == "contested" for claim in claims)
    assert all(len(claim["klawiter:interpretation"]) >= 2 for claim in claims)
    assert all(claim["klawiter:sourceEvidence"] for claim in claims)
    saint_aignan = next(
        claim
        for claim in claims
        if claim["klawiter:claimSubject"]["@id"] == "klawiter:location/Saint-Aignan"
    )
    assert saint_aignan["klawiter:claimSubject"]["schema:name"] == "Saint-Aignan"
    assert any(
        evidence["sourceValue"] == "Saint-Aignan"
        and len(evidence["sourceTextSha256"]) == 64
        for evidence in saint_aignan["klawiter:sourceEvidence"]
    )


def test_stage_05_reads_only_publishable_links() -> None:
    stage_05 = importlib.import_module("05_to_jsonld")
    # The publishable layer holds decisions by a person or an exact rule only.
    assert stage_05.load_location_wikidata() == {}


def test_public_reconciliation_projection_is_time_independent(
    reconciliation: dict,
) -> None:
    reconcile_entities = importlib.import_module("reconcile_entities")
    edition_dataset = json.loads(
        (Path(OUTPUT_EDITIONS_DIR) / "work-editions.jsonld").read_text(encoding="utf-8")
    )
    first = reconcile_entities._frontend(reconciliation, edition_dataset)
    second = reconcile_entities._frontend(reconciliation, edition_dataset)
    assert first == second
    assert "generatedAt" not in first


def test_reconciliation_patch_supersedes_prior_decision(tmp_path: Path) -> None:
    patch_path = tmp_path / "curation.json"
    patch_path.write_text(
        json.dumps(
            {
                "reconciliationPatchVersion": 1,
                "reconciliationPatches": [
                    {
                        "entityType": "location",
                        "subject": "Saint-Aignan",
                        "action": "confirm",
                        "qid": "Q1055925",
                        "decisionId": "location/Saint-Aignan/Q1055925/editor",
                        "decidedBy": "Editor (SZD)",
                        "decidedAt": "2026-08-21T20:00:00Z",
                        "evidence": ["source-imprint"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    loaded = load_reconciliation_patches(tmp_path)
    base = json.loads(Path(LOCATION_DECISIONS).read_text(encoding="utf-8"))
    merged = merge_decision_patches(base, loaded["location"], "location")
    decision = next(
        item for item in merged["decisions"] if item["subject"] == "Saint-Aignan"
    )
    assert decision["action"] == "confirm"
    assert decision["supersedesDecisionId"] == "location/Saint-Aignan/unresolved"


def test_editor_reject_closes_open_claim_with_no_assignment(classified_rows) -> None:
    """A reject from the editor (edit.js decideLocation) carries no resolution;
    on an open claim it accepts the no-assignment reading and links nothing."""

    def read(path: str | Path) -> dict | list:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    patch = {
        "entityType": "location",
        "subject": "Saint-Aignan",
        "action": "reject",
        "qid": None,
        "label": None,
        "decisionId": "location/Saint-Aignan/editor-2026-10-23T10:00:00Z",
        "decidedBy": "Editor (SZD)",
        "decidedAt": "2026-10-23T10:00:00Z",
        "evidence": ["frontend-entry/1", "no-candidate"],
        "source": "human",
    }
    decisions = merge_decision_patches(read(LOCATION_DECISIONS), [patch], "location")
    result = build_reconciliation(
        read(Path(OUTPUT_EDITIONS_DIR) / "work-editions.jsonld"),
        read(LOCATIONS_JSON),
        read(LOCATION_RECONCILIATION_LOG),
        read(LOCATION_REVIEW_EVIDENCE),
        decisions,
        read(WORK_DECISIONS),
        parse_szd_work_index(Path(SZD_WORK_INDEX)),
        classified_rows,
        read(AGENT_RECONCILIATION),
        read(AGENT_DECISIONS),
        read(SOURCE_REVISION_DECISIONS),
    )
    claim = next(
        claim
        for claim in result["contestedClaims"]
        if claim["klawiter:claimSubject"]["@id"] == "klawiter:location/Saint-Aignan"
    )
    assert claim["klawiter:decisionStatus"] == "decided"
    accepted = [
        item["@id"]
        for item in claim["klawiter:interpretation"]
        if item["klawiter:interpretationStatus"] == "accepted"
    ]
    assert accepted == [f"{claim['@id']}/interpretation/no-assignment"]
    assert "Saint-Aignan" not in result["publishable"]["locations"]


def test_generated_gate2_validation_passes() -> None:
    report = json.loads(
        Path("data/output/reconciliation/validation-report.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["allChecksPass"] is True
    assert all(report["checks"].values())


def test_gate2_provenance_paths_are_repository_relative() -> None:
    manifest = json.loads(
        Path("data/output/reconciliation/manifest.json").read_text(encoding="utf-8")
    )
    assert all(
        not Path(item["path"]).is_absolute() and "\\" not in item["path"]
        for item in manifest["inputs"].values()
    )
    provenance = json.loads(
        Path("data/output/reconciliation/provenance.jsonld").read_text(encoding="utf-8")
    )
    locations = [
        item["prov:atLocation"]
        for item in provenance["@graph"]
        if "prov:atLocation" in item
    ]
    assert locations
    assert all(not Path(path).is_absolute() and "\\" not in path for path in locations)


AGENT_OCCURRENCE_FIELDS = {"person": "translator", "publisher": "publisher"}


def test_agent_subjects_carry_source_occurrence_evidence(reconciliation: dict) -> None:
    """Every agent subject with a candidate needs source evidence or an
    explicit null finding; without it no unresolved decision is arguable."""
    subjects = reconciliation["candidates"]["agents"]
    with_candidates = [subject for subject in subjects if subject["candidates"]]
    assert with_candidates
    for subject in subjects:
        occurrences = subject["sourceOccurrences"]
        if subject["candidates"]:
            assert occurrences or subject.get("sourceOccurrenceNote"), (
                f"{subject['subjectId']} has candidates without occurrence evidence"
            )
        field = AGENT_OCCURRENCE_FIELDS[subject["entityType"]]
        for occurrence in occurrences:
            assert occurrence["sourceField"] == field
            assert occurrence["sourceValue"] == subject["sourceName"]
            assert occurrence["sourcePath"] == "data/intermediate/04_classified.csv"
            assert isinstance(occurrence["sourcePageId"], int)
            assert occurrence["sourceMatchMode"] in {"field-value", "field-value-line"}
            if occurrence["sourceMatchMode"] == "field-value-line":
                assert len(occurrence["sourceTextSha256"]) == 64
                assert occurrence["sourceText"]
                assert occurrence["sourceLine"] >= 1


def test_agent_occurrence_pages_match_the_classified_source(
    reconciliation: dict, classified_rows
) -> None:
    rows = classified_rows
    for subject in reconciliation["candidates"]["agents"]:
        field = AGENT_OCCURRENCE_FIELDS[subject["entityType"]]
        expected = {
            int(row["page_id"]) for row in rows if row[field] == subject["sourceName"]
        }
        found = {
            occurrence["sourcePageId"] for occurrence in subject["sourceOccurrences"]
        }
        assert found == expected


def test_agent_occurrences_are_deterministically_ordered(reconciliation: dict) -> None:
    for subject in reconciliation["candidates"]["agents"]:
        keys = [
            (
                occurrence["sourcePageId"],
                occurrence["sourceTextId"] or 0,
                occurrence["sourceLine"] or 0,
            )
            for occurrence in subject["sourceOccurrences"]
        ]
        assert keys == sorted(keys)
        ids = [occurrence["@id"] for occurrence in subject["sourceOccurrences"]]
        assert len(ids) == len(set(ids))


@pytest.mark.parametrize("entity_type", ["person", "publisher"])
def test_unresolved_agent_decision_becomes_a_contested_claim(
    reconciliation: dict, classified_rows, entity_type
) -> None:
    """The occurrence scan is what makes an unresolved agent decision
    representable: it supplies the source evidence the claim requires."""
    subject = next(
        item
        for item in reconciliation["candidates"]["agents"]
        if item["entityType"] == entity_type
        and item["candidates"]
        and item["sourceOccurrences"]
    )
    decision = {
        "entityType": subject["entityType"],
        "subject": subject["sourceName"],
        "action": "unresolved",
        "decisionId": f"agent/{subject['sourceName']}/unresolved",
        "decidedBy": "independent-verification-agent",
        "decidedAt": "2026-08-27T10:00:00Z",
        "evidence": ["source-imprint"],
    }
    frozen_agents = json.loads(Path(AGENT_RECONCILIATION).read_text(encoding="utf-8"))
    agent = next(
        item
        for item in frozen_agents["agents"]
        if item["kind"] == subject["entityType"]
        and item["name"] == subject["sourceName"]
    )
    field = AGENT_OCCURRENCE_FIELDS[subject["entityType"]]
    source_rows = [
        row for row in classified_rows if row[field] == subject["sourceName"]
    ]
    # Keep every occurrence of this real subject. The session fixture covers
    # the complete corpus; this decision needs no unrelated work/location scan.
    rebuilt = build_reconciliation(
        {"works": []},
        {},
        [],
        {},
        {"decisions": []},
        {"decisions": []},
        [],
        source_rows,
        {"agents": [agent]},
        {"decisions": [decision]},
    )
    claim = next(
        item
        for item in rebuilt["contestedClaims"]
        if item["klawiter:claimSubject"]["@id"] == subject["subjectId"]
    )
    assert claim["klawiter:identityScope"] == subject["entityType"]
    assert claim["klawiter:claimStatus"] == "contested"
    assert claim["klawiter:decisionStatus"] == "open"
    assert len(claim["klawiter:interpretation"]) >= 2
    assert claim["klawiter:sourceEvidence"] == subject["sourceOccurrences"]
    assert rebuilt["publishable"]["agents"] == {}


def test_public_agent_projection_carries_occurrence_evidence(
    reconciliation: dict,
) -> None:
    reconcile_entities = importlib.import_module("reconcile_entities")
    edition_dataset = json.loads(
        (Path(OUTPUT_EDITIONS_DIR) / "work-editions.jsonld").read_text(encoding="utf-8")
    )
    frontend = reconcile_entities._frontend(reconciliation, edition_dataset)
    assert frontend["schemaVersion"] == "1.4"
    subject = reconciliation["candidates"]["agents"][0]
    key = f"{subject['entityType']}/{subject['sourceName']}"
    projected = frontend["agents"][key]
    # The internal pipeline path stays out of the published projection, the
    # same rule the contested-claim projection follows.
    assert projected["sourceOccurrences"] == [
        {name: value for name, value in occurrence.items() if name != "sourcePath"}
        for occurrence in subject["sourceOccurrences"]
    ]
    # The interface list holds open claims; no person or rule has decided one.
    assert {claim["decisionStatus"] for claim in frontend["contestedClaims"]} == {
        "open"
    }
    assert frontend["decidedClaims"] == []
    assert {
        "Sofija, Varna",
        "Varna, Sofija",
        "Bloemfontein, Kaapstad",
        "Tyresö",
        "Kuwait",
    } <= {claim["subject"]["name"] for claim in frontend["contestedClaims"]}
    for claim in frontend["contestedClaims"]:
        assert {step["producer"] for step in claim["reviewHistory"]} == {"llm-agent"}
    varna = frontend["locations"]["Varna"]
    assert varna["decision"]["action"] == "confirm"
    assert varna["decisionProducer"] == "llm-agent"
    assert varna["decisionState"] == "proposed"
    assert varna["publishable"] is None


# Compound place strings decided on 2026-09-23: each names two cities, whose
# components are decided as subjects of their own.
COMPOUND_CLAIMS = {
    "Sofija, Varna": ("1ff25adffafe2fd7", {"Q472", "Q6506"}, {1725, 1799}),
    "Varna, Sofija": ("f401570c46e6b7e9", {"Q472", "Q6506"}, {1725, 1799}),
    "Bloemfontein, Kaapstad": ("e5742c35b57192e9", {"Q37701", "Q5465"}, {4209, 5330}),
}


def test_compound_places_stay_open_with_the_proposed_reading(
    reconciliation: dict,
) -> None:
    """The main instance decided the compound places as two places each; the
    decision is a proposal, so the claim stays open with that reading among
    the competing ones, and neither the compound nor a component publishes."""
    claims = {
        claim["klawiter:claimSubject"]["schema:name"]: claim
        for claim in reconciliation["contestedClaims"]
    }
    for name, (suffix, qids, _) in COMPOUND_CLAIMS.items():
        claim = claims[name]
        assert claim["@id"] == f"klawiter:claim/reconciliation/location/{suffix}"
        assert claim["klawiter:claimStatus"] == "contested"
        assert claim["klawiter:decisionStatus"] == "open"
        readings = {
            item["@id"].rsplit("/", 1)[1]: (
                item["klawiter:interpretationStatus"],
                item["klawiter:candidateSource"],
            )
            for item in claim["klawiter:interpretation"]
        }
        assert {key: status for key, (status, _) in readings.items()} == dict.fromkeys(
            [*qids, "no-assignment", "two-places"], "contested"
        )
        assert readings["two-places"][1] == "llm-agent-proposal"
        history = claim["klawiter:hasReviewAction"]
        assert [item["klawiter:reviewOutcome"] for item in history] == [
            "unresolved",
            "reject",
        ]
        assert history[-1]["klawiter:reviewBasis"] == (
            "decided by the main instance after delegation by the operator on "
            "2026-09-23, revisable"
        )
        assert claim["klawiter:reviewNote"]
    assert reconciliation["publishable"]["locations"] == {}


def test_a_person_decides_the_compound_places(person_reconciliation: dict) -> None:
    """Recorded by a person, the same decisions close the compound claims with
    the two-places reading and publish the components."""
    claims = {
        claim["klawiter:claimSubject"]["schema:name"]: claim
        for claim in person_reconciliation["contestedClaims"]
    }
    published = person_reconciliation["publishable"]["locations"]
    for name, (_, qids, _) in COMPOUND_CLAIMS.items():
        claim = claims[name]
        assert claim["klawiter:claimStatus"] == "resolved"
        assert claim["klawiter:decisionStatus"] == "decided"
        readings = {
            item["@id"].rsplit("/", 1)[1]: item["klawiter:interpretationStatus"]
            for item in claim["klawiter:interpretation"]
        }
        assert readings == {
            **dict.fromkeys(qids, "rejected"),
            "no-assignment": "rejected",
            "two-places": "accepted",
        }
        assert name not in published
    # Sofija alone rested on the test fixture, which confirms nothing since
    # 2026-10-23; the compound decision rejects only the single-identity reading.
    assert "Sofija" not in published
    assert published["Varna"]["qid"] == "Q6506"
    assert published["Bloemfontein"]["qid"] == "Q37701"
    assert published["Kaapstad (Capetown)"]["qid"] == "Q5465"
    open_ids = {
        claim["@id"]
        for claim in person_reconciliation["contestedClaims"]
        if claim["klawiter:identityScope"] == "location"
        and claim["klawiter:decisionStatus"] == "open"
    }
    assert "klawiter:claim/reconciliation/location/d72833396adc8499" in open_ids
    assert "klawiter:claim/reconciliation/location/13c36aabb066d6a3" not in open_ids
    assert len(open_ids) == len(_decided({"unresolved"}))


def test_claim_evidence_is_the_pages_that_carry_the_subject(
    reconciliation: dict,
) -> None:
    claims = {
        claim["klawiter:claimSubject"]["schema:name"]: claim
        for claim in reconciliation["contestedClaims"]
    }
    for name, (_, _, pages) in COMPOUND_CLAIMS.items():
        evidence = claims[name]["klawiter:sourceEvidence"]
        assert {item["sourcePageId"] for item in evidence} == pages
        components = [part.strip().casefold() for part in name.split(",")]
        for item in evidence:
            text = item["sourceText"].casefold()
            assert text.startswith("'''[19"), item["sourceText"]
            assert all(component in text for component in components)


def test_component_match_needs_one_imprint_with_whole_words() -> None:
    rows = [
        {
            "page_id": "1",
            "text_id": "11",
            "raw_content": "'''[1966]: Nauka, Sofija / DPK, Varna'''",
        },
        {
            "page_id": "2",
            "text_id": "12",
            "raw_content": "in [1]. [[X]] [Varna, 1992]. [2]. [[Y]] [Sofija, 1946]",
        },
        {
            "page_id": "3",
            "text_id": "13",
            "raw_content": "'''[1977]: University of California Press, Los Angeles'''",
        },
    ]
    folded = _folded_source_lines(rows)
    locations = {
        "Sofija, Varna": {"lat": 0, "lng": 0},
        "Los Angeles, CA": {"lat": 0, "lng": 0},
    }
    subjects = {
        subject["sourceLocation"]: subject
        for subject in build_location_candidates(locations, [], None, folded)
    }
    assert [
        item["sourcePageId"] for item in subjects["Sofija, Varna"]["sourceOccurrences"]
    ] == [1]
    assert subjects["Los Angeles, CA"]["sourceOccurrences"] == []


def test_open_and_decided_claim_counts_agree_across_gates() -> None:
    from lib.config import OUTPUT_RECONCILIATION_DIR

    gate1 = json.loads(
        (Path(OUTPUT_EDITIONS_DIR) / "manifest.json").read_text(encoding="utf-8")
    )["counts"]
    gate2 = json.loads(
        (Path(OUTPUT_RECONCILIATION_DIR) / "manifest.json").read_text(encoding="utf-8")
    )["counts"]
    assert "contestedClaims" not in gate1
    for key in ("contestedEditionClaims", "decidedEditionClaims"):
        assert gate1[key] == gate2[key]
    # The adaptation resolution of 2026-09-22 and the place decisions closing
    # claims were made by LLM agents, so every claim is open.
    assert gate1["contestedEditionClaims"] == 1
    assert gate1["decidedEditionClaims"] == 0
    assert gate2["contestedAuthorityClaims"] == len(_held_open())
    assert gate2["decidedAuthorityClaims"] == 0
    assert gate2["contestedSourceRevisionClaims"] == 10
    assert gate2["confirmedDecisions"] == 0
    assert gate2["publishableLocationLinks"] == 0
    assert gate2["publishableWorkLinks"] == 0
