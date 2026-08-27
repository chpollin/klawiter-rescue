"""Deterministic Gate-2 candidate, decision, and publication separation."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path
from typing import NamedTuple
from urllib.parse import quote

# Canonical Wikidata RDF entity IRI: the http form is what Wikidata's own
# RDF uses; the https form never joins against external triples.
WIKIDATA_URI = "http://www.wikidata.org/entity/"
SZD_WORK_URI = "https://gams.uni-graz.at/o:szd.werkindex#"
TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
ALGORITHM_VERSION = "1.1"


def load_reconciliation_patches(directory: Path) -> dict:
    """Load approved EIL decision patches placed in the correction store."""
    result = {"location": [], "work": [], "person": [], "publisher": [], "files": []}
    if not directory.exists():
        return result
    for path in sorted(directory.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        patches = document.get("reconciliationPatches", [])
        if not patches:
            continue
        if document.get("reconciliationPatchVersion") != 1:
            raise ValueError(f"Unsupported reconciliation patch version: {path}")
        result["files"].append(path)
        for patch in patches:
            entity_type = patch.get("entityType")
            if entity_type not in {"location", "work", "person", "publisher"}:
                raise ValueError(f"Invalid reconciliation entity type in {path}")
            required = {
                "decisionId",
                "action",
                "decidedBy",
                "decidedAt",
                "evidence",
            }
            subject_key = "subjectId" if entity_type == "work" else "subject"
            if not required.issubset(patch) or subject_key not in patch:
                raise ValueError(f"Incomplete reconciliation decision in {path}")
            result[entity_type].append(copy.deepcopy(patch))
    return result


def merge_agent_decision_patches(decision_document: dict, patches: list[dict]) -> dict:
    """Overlay approved EIL agent decisions (person and publisher kinds in
    one document) while retaining supersession evidence."""
    merged = copy.deepcopy(decision_document)
    by_key = {
        (decision["entityType"], decision["subject"]): decision
        for decision in merged["decisions"]
    }
    for patch in patches:
        key = (patch["entityType"], patch["subject"])
        prior = by_key.get(key)
        replacement = copy.deepcopy(patch)
        if prior:
            replacement["supersedesDecisionId"] = prior["decisionId"]
            replacement["supersedes"] = copy.deepcopy(prior)
        by_key[key] = replacement
    merged["decisions"] = sorted(
        by_key.values(),
        key=lambda item: (item["entityType"], str(item["subject"]).casefold()),
    )
    return merged


def merge_decision_patches(
    decision_document: dict, patches: list[dict], entity_type: str
) -> dict:
    """Overlay approved EIL decisions while retaining supersession evidence."""
    subject_key = "subject" if entity_type == "location" else "subjectId"
    merged = copy.deepcopy(decision_document)
    by_subject = {decision[subject_key]: decision for decision in merged["decisions"]}
    for patch in patches:
        subject = patch[subject_key]
        prior = by_subject.get(subject)
        replacement = copy.deepcopy(patch)
        if prior:
            replacement["supersedesDecisionId"] = prior["decisionId"]
            replacement["supersedes"] = copy.deepcopy(prior)
        by_subject[subject] = replacement
    merged["decisions"] = sorted(
        by_subject.values(), key=lambda item: str(item[subject_key]).casefold()
    )
    return merged


def _normalize_title(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    text = re.sub(r"\s*/\s*(?:volume|vist|translations?)\s*$", "", text)
    text = re.sub(r"\([^)]*\)\s*$", "", text)
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def parse_szd_work_index(path: Path) -> list[dict]:
    """Read the frozen TEI work index into a compact authority list."""
    root = ET.parse(path).getroot()
    works = []
    for bibl in root.findall(".//tei:listBibl/tei:bibl", TEI_NS):
        title_node = bibl.find("tei:title", TEI_NS)
        szd_id = bibl.get(XML_ID)
        if title_node is None or not szd_id:
            continue
        title = "".join(title_node.itertext()).strip()
        works.append(
            {
                "szdId": szd_id,
                "title": title,
                "normalizedTitle": _normalize_title(title),
                "szdUri": SZD_WORK_URI + szd_id,
                "gndUri": title_node.get("ref"),
            }
        )
    return works


def build_work_candidates(dataset: dict, authorities: list[dict]) -> list[dict]:
    """Rank frozen SZD authority candidates for every segmented work."""
    results = []
    for work in dataset["works"]:
        source_title = work["schema:name"]
        normalized = _normalize_title(source_title)
        ranked = []
        for authority in authorities:
            if not normalized or not authority["normalizedTitle"]:
                continue
            score = round(
                100
                * SequenceMatcher(
                    None, normalized, authority["normalizedTitle"]
                ).ratio(),
                1,
            )
            if score < 45:
                continue
            candidate = {
                "candidateId": (
                    f"work/{work['klawiter:sourcePageId']}/{authority['szdId']}"
                ),
                "szdId": authority["szdId"],
                "label": authority["title"],
                "score": score,
                "matchMethod": "exact-title" if score == 100 else "title-similarity",
                "szdUri": authority["szdUri"],
            }
            if authority["gndUri"]:
                candidate["gndUri"] = authority["gndUri"]
            ranked.append(candidate)
        ranked.sort(key=lambda item: (-item["score"], item["szdId"]))
        results.append(
            {
                "subjectId": work["@id"],
                "sourcePageId": work["klawiter:sourcePageId"],
                "sourceTitle": source_title,
                "normalizedTitle": normalized,
                "candidates": ranked[:3],
            }
        )
    return results


def build_location_candidates(
    locations: dict,
    reconciliation_log: list[dict],
    review_evidence: dict | None = None,
    folded_rows: list[_SourceRow] | None = None,
) -> list[dict]:
    """Preserve every legacy reconciliation output as an unconfirmed candidate."""
    log_by_location = {item["location"]: item for item in reconciliation_log}
    folded_rows = folded_rows or []
    results = []
    for name in sorted(locations, key=str.casefold):
        info = locations[name]
        log_item = log_by_location.get(name, {"status": "unrecorded"})
        candidates = []
        qid = info.get("wikidataId")
        if qid:
            candidates.append(
                {
                    "candidateId": f"location/{name}/{qid}",
                    "qid": qid,
                    "label": info.get("wikidataLabel") or name,
                    "score": info.get("wikidataScore"),
                    "matchExact": log_item.get("matchExact"),
                    "candidateSource": "legacy-reconciliation-output",
                    "uri": WIKIDATA_URI + qid,
                }
            )
        elif log_item.get("wikidataId"):
            candidate_qid = log_item["wikidataId"]
            candidates.append(
                {
                    "candidateId": f"location/{name}/{candidate_qid}",
                    "qid": candidate_qid,
                    "label": log_item.get("wikidataLabel") or name,
                    "score": log_item.get("wikidataScore"),
                    "matchExact": False,
                    "candidateSource": "legacy-low-score-output",
                    "uri": WIKIDATA_URI + candidate_qid,
                }
            )
        results.append(
            {
                "subjectId": f"klawiter:location/{quote(name, safe='')}",
                "sourceLocation": name,
                "coordinates": {"lat": info["lat"], "lng": info["lng"]},
                "country": info.get("country"),
                "legacyStatus": log_item.get("status"),
                "candidates": candidates,
                "sourceOccurrences": _location_source_occurrences(name, folded_rows),
            }
        )
    if review_evidence:
        by_location = {item["sourceLocation"]: item for item in results}

        def add_candidate(location: str, item: dict, source: str) -> None:
            subject = by_location.get(location)
            if subject is None:
                raise ValueError(f"Reviewed location is absent: {location}")
            qid = item["wikidata_id"]
            if any(candidate["qid"] == qid for candidate in subject["candidates"]):
                return
            subject["candidates"].append(
                {
                    "candidateId": f"location/{location}/{qid}",
                    "qid": qid,
                    "label": item.get("wikidata_label") or location,
                    "score": None,
                    "matchExact": False,
                    "candidateSource": source,
                    "uri": WIKIDATA_URI + qid,
                }
            )

        for case in review_evidence["case_decisions"]:
            corrected = case.get("correct_candidate")
            if corrected:
                add_candidate(
                    case["source_location"],
                    corrected,
                    "independent-review-correction",
                )
        for assessment in review_evidence["open_log_entry_assessment"]["entries"]:
            proposals = []
            if assessment.get("candidate"):
                proposals.append(assessment["candidate"])
            if assessment.get("candidates"):
                proposals.extend(assessment["candidates"])
            if assessment.get("candidate_hypothesis"):
                proposals.append(assessment["candidate_hypothesis"])
            if assessment.get("candidate_hypotheses"):
                proposals.extend(assessment["candidate_hypotheses"])
            for proposal in proposals:
                add_candidate(
                    assessment["location"],
                    proposal,
                    "independent-review-proposal",
                )
    return results


OCCURRENCE_SOURCE_PATH = "data/intermediate/04_classified.csv"

# The flat field a frozen agent name was counted over at freezing time; the
# occurrence scan resolves a subject through the same field.
AGENT_SOURCE_FIELDS = {"person": "translator", "publisher": "publisher"}


class _SourceRow(NamedTuple):
    """One classified source row, folded for repeated occurrence scanning."""

    page_id: int
    text_id: int | None
    lines: list[tuple[int, str, str]]
    fields: dict[str, str]


def _folded_source_lines(source_rows: list[dict[str, str]]) -> list[_SourceRow]:
    """Fold every source line exactly once. The occurrence scan runs per
    subject over the full source; folding inside that scan would re-fold the
    corpus hundreds of times per build."""
    folded = []
    for row in source_rows:
        text = (
            row.get("raw_content")
            or row.get("content")
            or row.get("full_bibliographic_entry")
            or ""
        )
        lines = [
            (number, line, line.casefold())
            for number, line in enumerate(text.splitlines(), start=1)
        ]
        folded.append(
            _SourceRow(
                page_id=int(row["page_id"]),
                text_id=int(row["text_id"]) if row.get("text_id") else None,
                lines=lines,
                fields={
                    field: row.get(field, "") for field in AGENT_SOURCE_FIELDS.values()
                },
            )
        )
    return folded


def _line_occurrence(
    scope: str,
    row: _SourceRow,
    line_number: int,
    line: str,
    value: str,
    match_mode: str,
    field: str | None = None,
) -> dict:
    """An occurrence anchored to one exact source line."""
    occurrence = {
        "@id": (
            f"klawiter:sourceOccurrence/{scope}/{row.page_id}/"
            f"{row.text_id or 0}/{line_number}"
        ),
        "sourcePageId": row.page_id,
        "sourceTextId": row.text_id,
        "sourcePath": OCCURRENCE_SOURCE_PATH,
        "sourceLine": line_number,
        "sourceValue": value,
        "sourceMatchMode": match_mode,
        "sourceText": line,
        "sourceTextSha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
    }
    if field:
        occurrence["sourceField"] = field
    return occurrence


def _field_occurrence(scope: str, row: _SourceRow, value: str, field: str) -> dict:
    """An occurrence proved by the extracted field alone. The value reached
    the field through enrichment or normalization, so no line of the source
    text carries it literally; the record says exactly that instead of
    asserting a text position it cannot support."""
    return {
        "@id": (
            f"klawiter:sourceOccurrence/{scope}/{row.page_id}/{row.text_id or 0}/field"
        ),
        "sourcePageId": row.page_id,
        "sourceTextId": row.text_id,
        "sourcePath": OCCURRENCE_SOURCE_PATH,
        "sourceLine": None,
        "sourceValue": value,
        "sourceMatchMode": "field-value",
        "sourceField": field,
    }


def _sorted_occurrences(occurrences: list[dict]) -> list[dict]:
    occurrences.sort(
        key=lambda item: (
            item["sourcePageId"],
            item["sourceTextId"] or 0,
            item["sourceLine"] or 0,
        )
    )
    return occurrences


def _location_source_occurrences(
    location: str, folded_rows: list[_SourceRow]
) -> list[dict]:
    """Return stable, exact source-line references for a location string."""
    occurrences: list[dict] = []
    seen: set[tuple[int, int | None, int]] = set()
    needle = location.casefold()
    components = [item.strip().casefold() for item in location.split(",")]
    for row in folded_rows:
        for line_number, line, folded_line in row.lines:
            exact_match = needle in folded_line
            component_match = len(components) > 1 and all(
                component in folded_line for component in components
            )
            if not exact_match and not component_match:
                continue
            key = (row.page_id, row.text_id, line_number)
            if key in seen:
                continue
            seen.add(key)
            occurrences.append(
                _line_occurrence(
                    "location",
                    row,
                    line_number,
                    line,
                    location,
                    "exact-string" if exact_match else "component-set",
                )
            )
    return _sorted_occurrences(occurrences)


def _agent_source_occurrences(
    kind: str, name: str, folded_rows: list[_SourceRow]
) -> list[dict]:
    """Return source references for a translator or publisher name.

    A location is a substring of the bibliographic text, so its scan runs
    over every line. An agent name is a parsed field value, so the field
    identifies the entries that carry it; the scan then anchors the name in
    the lines of exactly those entries and falls back to the field itself
    where no line spells it out.
    """
    field = AGENT_SOURCE_FIELDS[kind]
    needle = name.casefold()
    occurrences: list[dict] = []
    for row in folded_rows:
        if row.fields.get(field) != name:
            continue
        matched = [
            (line_number, line)
            for line_number, line, folded_line in row.lines
            if needle in folded_line
        ]
        if matched:
            occurrences.extend(
                _line_occurrence(
                    kind, row, line_number, line, name, "field-value-line", field
                )
                for line_number, line in matched
            )
        else:
            occurrences.append(_field_occurrence(kind, row, name, field))
    return _sorted_occurrences(occurrences)


def build_agent_candidates(
    agent_reconciliation: dict, folded_rows: list[_SourceRow] | None = None
) -> list[dict]:
    """Rank frozen Wikidata candidates for translator and publisher names.

    Proposals only: like locations and works, an agent name publishes an
    authority link exclusively through a confirmed decision. Each subject
    carries the source occurrences that make an unresolved decision arguable.
    """
    folded_rows = folded_rows or []
    subjects = []
    for item in agent_reconciliation.get("agents", []):
        kind, name = item["kind"], item["name"]
        candidates = [
            {
                "candidateId": f"agent/{kind}/{quote(name, safe='')}/{hit['qid']}",
                "qid": hit["qid"],
                "label": hit["label"],
                "score": hit["score"],
                "matchExact": hit["matchExact"],
                "uri": WIKIDATA_URI + hit["qid"],
                "candidateSource": "wikidata-reconciliation-frozen",
            }
            for hit in item.get("candidates", [])
        ]
        subject = {
            "entityType": kind,
            "subjectId": f"klawiter:{kind}/{quote(name, safe='')}",
            "sourceName": name,
            "occurrences": item["occurrences"],
            "sourceOccurrences": _agent_source_occurrences(kind, name, folded_rows),
            "candidates": candidates,
            "decision": None,
        }
        if not subject["sourceOccurrences"]:
            subject["sourceOccurrenceNote"] = (
                f"Null finding: no {AGENT_SOURCE_FIELDS[kind]} value in "
                f"{OCCURRENCE_SOURCE_PATH} equals this frozen agent name."
            )
        subjects.append(subject)
    subjects.sort(key=lambda subject: (subject["entityType"], subject["sourceName"]))
    return subjects


def apply_agent_decisions(subjects: list[dict], decisions: list[dict]) -> list[dict]:
    """Attach reviewed agent decisions with the same guarantees locations
    and works enjoy: unique subjects, evidence required, confirmed targets
    must be candidates, corrections enter as marked candidates."""
    by_key = {
        (subject["entityType"], subject["sourceName"]): subject for subject in subjects
    }
    seen: set[tuple[str, str]] = set()
    for decision in decisions:
        key = (decision["entityType"], decision["subject"])
        if key in seen:
            raise ValueError(f"Duplicate agent decision for {key}")
        seen.add(key)
        subject = by_key.get(key)
        if subject is None:
            raise ValueError(f"Decision references absent agent: {key}")
        action = decision["action"]
        if action not in {"confirm", "correct", "reject", "unresolved"}:
            raise ValueError(f"Unsupported decision action: {action}")
        if not decision.get("evidence"):
            raise ValueError(f"Decision lacks evidence: {decision['decisionId']}")
        if action == "unresolved" and not subject["sourceOccurrences"]:
            raise ValueError(
                "An unresolved agent decision needs source-occurrence "
                f"evidence, and the scan found none for {key}"
            )
        target = decision.get("qid")
        candidate_targets = {candidate["qid"] for candidate in subject["candidates"]}
        if action == "confirm" and target not in candidate_targets:
            raise ValueError(f"Confirmed target is not a candidate for {key}: {target}")
        if action == "correct" and target and target not in candidate_targets:
            subject["candidates"].append(
                {
                    "candidateId": (
                        f"agent/{decision['entityType']}/"
                        f"{quote(decision['subject'], safe='')}/{target}"
                    ),
                    "qid": target,
                    "label": decision.get("label") or decision["subject"],
                    "score": None,
                    "matchExact": False,
                    "uri": WIKIDATA_URI + target,
                    "candidateSource": "independent-review-correction",
                }
            )
        subject["decision"] = decision
    return subjects


def _decision_subject(decision: dict, entity_type: str) -> str:
    return decision["subject"] if entity_type == "location" else decision["subjectId"]


def apply_decisions(
    subjects: list[dict], decisions: list[dict], entity_type: str
) -> list[dict]:
    """Attach reviewed decisions while checking that publishable targets exist."""
    subject_key = "sourceLocation" if entity_type == "location" else "subjectId"
    by_subject = {subject[subject_key]: subject for subject in subjects}
    seen: set[str] = set()
    for decision in decisions:
        subject_name = _decision_subject(decision, entity_type)
        if subject_name in seen:
            raise ValueError(f"Duplicate {entity_type} decision for {subject_name}")
        seen.add(subject_name)
        subject = by_subject.get(subject_name)
        if subject is None:
            raise ValueError(
                f"Decision references absent {entity_type}: {subject_name}"
            )
        action = decision["action"]
        if action not in {"confirm", "correct", "reject", "unresolved"}:
            raise ValueError(f"Unsupported decision action: {action}")
        if not decision.get("evidence"):
            raise ValueError(f"Decision lacks evidence: {decision['decisionId']}")

        target_key = "qid" if entity_type == "location" else "szdId"
        target = decision.get(target_key)
        candidate_targets = {
            candidate[target_key] for candidate in subject["candidates"]
        }
        if action == "confirm" and target not in candidate_targets:
            raise ValueError(
                f"Confirmed target is not a candidate for {subject_name}: {target}"
            )
        if action == "correct" and target and target not in candidate_targets:
            candidate = {
                "candidateId": f"{entity_type}/{subject_name}/{target}",
                target_key: target,
                "label": decision.get("label") or subject_name,
                "score": None,
                "candidateSource": "independent-review-correction",
            }
            if entity_type == "location":
                candidate["uri"] = WIKIDATA_URI + target
            else:
                candidate["szdUri"] = SZD_WORK_URI + target
                if decision.get("gndUri"):
                    candidate["gndUri"] = decision["gndUri"]
            subject["candidates"].append(candidate)
        subject["decision"] = decision
    return subjects


def _priority(subject: dict, entity_type: str) -> str:
    decision = subject.get("decision")
    if decision and decision["action"] == "unresolved":
        return "P0"
    candidates = subject["candidates"]
    if not candidates:
        return "P0"
    if entity_type in ("location", "person", "publisher"):
        score = candidates[0].get("score")
        if score is None or score < 90:
            return "P1"
        return "P2"
    if candidates[0].get("matchMethod") == "exact-title":
        return "P1"
    return "P2"


def _queue_subject_groups(
    locations: list[dict], works: list[dict], agents: list[dict]
) -> list[tuple[str, dict]]:
    groups = [("location", subject) for subject in locations]
    groups += [("work", subject) for subject in works]
    groups += [(subject["entityType"], subject) for subject in agents]
    return groups


def _queue_display(subject: dict, entity_type: str) -> str:
    if entity_type == "location":
        return subject["sourceLocation"]
    if entity_type in ("person", "publisher"):
        return subject["sourceName"]
    return subject["subjectId"]


def _review_queue(locations: list[dict], works: list[dict], agents: list[dict]) -> dict:
    cases = []
    for entity_type, subject in _queue_subject_groups(locations, works, agents):
        decision = subject.get("decision")
        if decision and decision["action"] not in {"unresolved"}:
            continue
        cases.append(
            {
                "entityType": entity_type,
                "subject": _queue_display(subject, entity_type),
                "priority": _priority(subject, entity_type),
                "status": decision["action"] if decision else "proposed",
                "candidates": subject["candidates"],
                "evidence": {
                    key: value
                    for key, value in subject.items()
                    if key not in {"candidates", "decision"}
                },
            }
        )
    order = {"P0": 0, "P1": 1, "P2": 2}
    cases.sort(
        key=lambda case: (
            order[case["priority"]],
            case["entityType"],
            str(case["subject"]).casefold(),
        )
    )
    return {
        "contract": (
            "A candidate is never publishable before an evidence-bearing confirm "
            "or correct decision. Unresolved cases remain explicit."
        ),
        "caseCount": len(cases),
        "cases": cases,
    }


def _publishable_agent_links(agents: list[dict]) -> dict:
    links: dict = {}
    for subject in agents:
        decision = subject.get("decision")
        if not decision or decision["action"] not in {"confirm", "correct"}:
            continue
        qid = decision["qid"]
        candidate = next(item for item in subject["candidates"] if item["qid"] == qid)
        links[f"{subject['entityType']}/{subject['sourceName']}"] = {
            "kind": subject["entityType"],
            "name": subject["sourceName"],
            "qid": qid,
            "label": candidate["label"],
            "uri": WIKIDATA_URI + qid,
            "decisionId": decision["decisionId"],
        }
    return links


def _publishable_links(locations: list[dict], works: list[dict]) -> dict:
    location_links = {}
    for subject in locations:
        decision = subject.get("decision")
        if not decision or decision["action"] not in {"confirm", "correct"}:
            continue
        qid = decision["qid"]
        candidate = next(item for item in subject["candidates"] if item["qid"] == qid)
        location_links[subject["sourceLocation"]] = {
            "qid": qid,
            "label": candidate["label"],
            "uri": WIKIDATA_URI + qid,
            "decisionId": decision["decisionId"],
        }

    work_links = {}
    for subject in works:
        decision = subject.get("decision")
        if not decision or decision["action"] not in {"confirm", "correct"}:
            continue
        szd_id = decision["szdId"]
        candidate = next(
            item for item in subject["candidates"] if item["szdId"] == szd_id
        )
        link = {
            "szdId": szd_id,
            "label": candidate["label"],
            "szdUri": candidate["szdUri"],
            "decisionId": decision["decisionId"],
        }
        if candidate.get("gndUri"):
            link["gndUri"] = candidate["gndUri"]
        work_links[subject["subjectId"]] = link
    return {
        "publicationContract": (
            "Only targets with an evidence-bearing confirm or correct decision "
            "are projected into public data."
        ),
        "locations": location_links,
        "works": work_links,
        "agents": {},
    }


def _decision_history(decision: dict) -> list[dict]:
    """Decision trail as klawiter:ReviewAction nodes, the same class the
    edition graph uses for its review evidence."""
    history = []
    current: dict | None = decision
    while current:
        action = {
            "@id": "klawiter:review/reconciliation/"
            + hashlib.sha256(current["decisionId"].encode("utf-8")).hexdigest()[:16],
            "@type": "klawiter:ReviewAction",
            "klawiter:decisionId": current["decisionId"],
            "klawiter:reviewOutcome": current["action"],
            "prov:wasAssociatedWith": {"schema:name": current["decidedBy"]},
            "klawiter:evidence": current["evidence"],
        }
        if current.get("decidedAt"):
            action["klawiter:decidedAt"] = current["decidedAt"]
        history.append(action)
        current = current.get("supersedes")
    history.reverse()
    return history


def _claim_subject_key(subject: dict, entity_type: str) -> str:
    if entity_type == "location":
        return subject["sourceLocation"]
    if entity_type in AGENT_SOURCE_FIELDS:
        return subject["sourceName"]
    return subject["subjectId"]


def _contested_claims(
    locations: list[dict], works: list[dict], agents: list[dict] | None = None
) -> list[dict]:
    """Materialize unresolved decisions as claims without publishing them as links."""
    claims = []
    groups: list[tuple[str, list[dict]]] = [("location", locations), ("work", works)]
    for subject in agents or []:
        groups.append((subject["entityType"], [subject]))
    for entity_type, subjects in groups:
        for subject in subjects:
            decision = subject.get("decision")
            if not decision or decision["action"] != "unresolved":
                continue
            subject_id = subject["subjectId"]
            subject_key = _claim_subject_key(subject, entity_type)
            claim_suffix = hashlib.sha256(
                f"{entity_type}\0{subject_key}".encode("utf-8")
            ).hexdigest()[:16]
            claim_id = f"klawiter:claim/reconciliation/{entity_type}/{claim_suffix}"
            wikidata_scope = entity_type == "location" or (
                entity_type in AGENT_SOURCE_FIELDS
            )
            target_key = "qid" if wikidata_scope else "szdId"
            interpretations = []
            for candidate in subject["candidates"]:
                target = candidate[target_key]
                target_uri = candidate["uri"] if wikidata_scope else candidate["szdUri"]
                interpretations.append(
                    {
                        "@id": f"{claim_id}/interpretation/{target}",
                        "@type": "klawiter:ClaimInterpretation",
                        "schema:name": candidate["label"],
                        "klawiter:proposedObject": {"@id": target_uri},
                        "klawiter:interpretationStatus": "contested",
                        "klawiter:candidateId": candidate["candidateId"],
                        "klawiter:candidateSource": candidate.get("candidateSource")
                        or candidate.get("matchMethod"),
                    }
                )
            interpretations.append(
                {
                    "@id": f"{claim_id}/interpretation/no-assignment",
                    "@type": "klawiter:ClaimInterpretation",
                    "schema:name": (
                        "No canonical authority assignment in the current evidence"
                    ),
                    "klawiter:interpretationStatus": "contested",
                    "klawiter:candidateSource": "fail-closed-alternative",
                }
            )
            source_evidence = (
                subject["sourceOccurrences"]
                if "sourceOccurrences" in subject
                else [
                    {
                        "@id": f"klawiter:sourceText/{subject['sourcePageId']}",
                        "sourcePageId": subject["sourcePageId"],
                        "sourceTitle": subject["sourceTitle"],
                    }
                ]
            )
            claims.append(
                {
                    "@id": claim_id,
                    "@type": "klawiter:ContestedClaim",
                    "klawiter:identityScope": entity_type,
                    "klawiter:claimSubject": {
                        "@id": subject_id,
                        "schema:name": subject_key,
                    },
                    "klawiter:claimPredicate": {"@id": "schema:sameAs"},
                    "klawiter:claimStatus": "contested",
                    "klawiter:decisionStatus": "open",
                    "klawiter:sourceEvidence": source_evidence,
                    "klawiter:interpretation": interpretations,
                    "klawiter:hasReviewAction": _decision_history(decision),
                }
            )
    claims.sort(key=lambda item: item["@id"])
    return claims


def build_reconciliation(
    edition_dataset: dict,
    locations: dict,
    location_log: list[dict],
    location_review: dict,
    location_decisions: dict,
    work_decisions: dict,
    szd_authorities: list[dict],
    source_rows: list[dict[str, str]] | None = None,
    agent_reconciliation: dict | None = None,
    agent_decisions: dict | None = None,
) -> dict:
    """Build all deterministic Gate-2 layers from frozen inputs."""
    folded_rows = _folded_source_lines(source_rows or [])
    location_subjects = apply_decisions(
        build_location_candidates(
            locations, location_log, location_review, folded_rows
        ),
        location_decisions["decisions"],
        "location",
    )
    work_subjects = apply_decisions(
        build_work_candidates(edition_dataset, szd_authorities),
        work_decisions["decisions"],
        "work",
    )
    agent_subjects = apply_agent_decisions(
        build_agent_candidates(agent_reconciliation or {}, folded_rows),
        (agent_decisions or {}).get("decisions", []),
    )
    decisions = {
        "contract": "Decisions remain separate from generated candidates and public links.",
        "locationDecisions": location_decisions["decisions"],
        "workDecisions": work_decisions["decisions"],
        "agentDecisions": (agent_decisions or {}).get("decisions", []),
    }
    candidates = {
        "algorithmVersion": ALGORITHM_VERSION,
        "locations": location_subjects,
        "works": work_subjects,
        "agents": agent_subjects,
    }
    publishable = _publishable_links(location_subjects, work_subjects)
    publishable["agents"] = _publishable_agent_links(agent_subjects)
    queue = _review_queue(location_subjects, work_subjects, agent_subjects)
    contested_claims = _contested_claims(
        location_subjects, work_subjects, agent_subjects
    )
    return {
        "candidates": candidates,
        "decisions": decisions,
        "publishable": publishable,
        "queue": queue,
        "contestedClaims": contested_claims,
    }
