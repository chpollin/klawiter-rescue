"""Deterministic Work and Edition segmentation for Gate 1.

The module turns source-bound MediaWiki publication headers into proposed
Schema.org Work and Book nodes. It preserves every source slice, emits stable
source-derived identifiers, and routes ambiguous notation into review flags.
It never promotes a proposal to an expert-confirmed assertion.

The model and identifier contract come from knowledge/production-readiness.md.
The three sample pages and their independent reviews under
data/output/edition-samples/ are the regression evidence for the parser.
"""

from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

from lib.patterns import EDITION_YEAR_PREFIX

ALGORITHM_VERSION = "1.2"
# Header grammar built from the shared year fragment in lib/patterns.py, so
# '[ca. YEAR]' parses identically in the flat extraction and here. patterns.py
# is part of segment_editions.py's provenance code hash for this reason.
EDITION_HEADER_RE = re.compile(
    rf"^'''\s*\[{EDITION_YEAR_PREFIX}\]", re.MULTILINE | re.IGNORECASE
)
YEAR_RE = re.compile(r"(\d{4})")
COMPOUND_HEADER_RE = re.compile(rf"\s+/\s+(?=\[{EDITION_YEAR_PREFIX}\])")
HEADER_RE = re.compile(r"\s*\[([^\]]*)\]\s*[:.]?\s*(.*)$")
SERIES_RE = re.compile(r"\s*(\[[^\]]+\])\s*$")
# Edition-block page counts: N of 'N/(M)p.' is the numbered-page component,
# deliberately NOT the summed total that verify.py derives with
# lib/patterns.PARENS_PAGE_RE. Same notation, different question — kept as
# separate grammars with this pointer instead of a false unification.
STANDARD_PAGE_COUNT_RE = re.compile(r"(?<!\()\b(\d+)(?:/\(\d+\))?p\.")
PAREN_PAGE_COUNT_RE = re.compile(r"\((\d+)\)p\.")
MALFORMED_PAGE_COUNT_RE = re.compile(r"\b(\d+)/(\d+)\)p\.")
PUBLISHER_PERIOD_RE = re.compile(
    r"\b(?:Verlag|Press|Publishing|Publishers|Éditions|Edition|Editore|Editorial)\.\s+",
    re.IGNORECASE,
)
STRUCTURAL_SECTION_RE = re.compile(
    r"^'''\s*(Contents|Anhang|Appendix|Photographs|Some excerpts|Excerpts|"
    r"Related topics|Translations|Original Manuscripts|Volumes|Individual Stories|"
    r"First printing|New edition|Page Proofs|German|Note|See)\s*:?[\s']*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class HeaderFields:
    """Source-derived fields for one edition represented in a header line."""

    year_raw: str
    year: int | None
    publisher: str | None
    location: str | None
    series: str | None
    description: str | None
    flags: tuple[str, ...]


@dataclass(frozen=True)
class Boundary:
    """A source line that starts an edition candidate or structural section."""

    start: int
    line: str
    kind: str


def _letter_suffix(index: int) -> str:
    """Return a, b, ..., z, aa, ab for a one-based occurrence index."""
    if index < 1:
        raise ValueError("Edition occurrence index must be positive")
    letters: list[str] = []
    number = index
    while number:
        number, remainder = divmod(number - 1, 26)
        letters.append(chr(ord("a") + remainder))
    return "".join(reversed(letters))


def _split_series(value: str) -> tuple[str, str | None]:
    match = SERIES_RE.search(value)
    if not match:
        return value.strip(), None
    return value[: match.start()].strip(), match.group(1)


def _split_publisher_location(value: str) -> tuple[str | None, str | None, bool]:
    cleaned = re.sub(r"\]{2,}$", "", value).strip().rstrip("'").strip()
    normalized = cleaned != value.strip().rstrip("'").strip()
    if not cleaned:
        return None, None, normalized
    if "," in cleaned:
        publisher, location = cleaned.rsplit(",", 1)
        return publisher.strip() or None, location.strip() or None, normalized
    period = PUBLISHER_PERIOD_RE.search(cleaned)
    if period:
        publisher = cleaned[: period.end() - 2].strip()
        location = cleaned[period.end() :].strip()
        return publisher or None, location or None, True
    return cleaned, None, normalized


def parse_header_line(line: str) -> list[HeaderFields]:
    """Parse one exact source header while retaining every ambiguous feature."""
    stripped = line.strip()
    body = stripped[3:].lstrip() if stripped.startswith("'''") else stripped
    if "'''" in body:
        header_text, suffix = body.split("'''", 1)
        suffix = suffix.strip() or None
        missing_close = False
    else:
        header_text = body
        suffix = None
        missing_close = True
    suffix_series = None
    if suffix and SERIES_RE.fullmatch(suffix):
        suffix_series = suffix
        suffix = None

    parts = COMPOUND_HEADER_RE.split(header_text)
    parsed: list[HeaderFields] = []
    for part in parts:
        match = HEADER_RE.match(part)
        if not match:
            parsed.append(
                HeaderFields(
                    year_raw="",
                    year=None,
                    publisher=part.strip() or None,
                    location=None,
                    series=None,
                    description=suffix,
                    flags=("unparsed-header",),
                )
            )
            continue

        year_raw = match.group(1).strip()
        year_match = YEAR_RE.search(year_raw)
        year = int(year_match.group(1)) if year_match else None
        field_text, series = _split_series(match.group(2).strip())
        series = series or suffix_series
        publisher, location, normalized = _split_publisher_location(field_text)
        flags: list[str] = []
        if len(parts) > 1:
            flags.append("compound-header")
        if "ca" in year_raw.casefold():
            flags.append("approximate-year")
        if year is None:
            flags.append("missing-year")
        if location is None:
            flags.append("missing-location")
        if missing_close:
            flags.append("malformed-bold-header")
        if suffix:
            flags.append("header-suffix")
        if series:
            flags.append("header-series")
        if normalized:
            flags.append("normalized-header-residue")
        parsed.append(
            HeaderFields(
                year_raw=year_raw,
                year=year,
                publisher=publisher,
                location=location,
                series=series,
                description=suffix,
                flags=tuple(flags),
            )
        )
    return parsed


def _boundaries(text: str) -> list[Boundary]:
    boundaries: list[Boundary] = []
    offset = 0
    for line_with_end in text.splitlines(keepends=True):
        line = line_with_end.rstrip("\r\n")
        if EDITION_HEADER_RE.match(line):
            boundaries.append(Boundary(offset, line, "edition"))
        elif STRUCTURAL_SECTION_RE.match(line):
            boundaries.append(Boundary(offset, line, "section"))
        offset += len(line_with_end)
    if offset < len(text):
        line = text[offset:]
        if EDITION_HEADER_RE.match(line):
            boundaries.append(Boundary(offset, line, "edition"))
        elif STRUCTURAL_SECTION_RE.match(line):
            boundaries.append(Boundary(offset, line, "section"))
    return boundaries


def _page_count(
    block: str,
) -> tuple[int | None, int | None, str | None, tuple[str, ...]]:
    standard = STANDARD_PAGE_COUNT_RE.search(block)
    if standard:
        return int(standard.group(1)), None, standard.group(0), ()
    parenthesized = PAREN_PAGE_COUNT_RE.search(block)
    if parenthesized:
        return (
            int(parenthesized.group(1)),
            None,
            parenthesized.group(0),
            ("normalized-page-count-notation",),
        )
    malformed = MALFORMED_PAGE_COUNT_RE.search(block)
    if malformed:
        return (
            int(malformed.group(1)),
            None,
            malformed.group(0),
            ("normalized-page-count-notation",),
        )
    return None, None, None, ()


def segment_page(page_id: int, text: str, work_title: str) -> dict:
    """Segment one page into proposed edition nodes and exact annotations."""
    boundaries = _boundaries(text)
    editions: list[dict] = []
    annotations: list[dict] = []
    sections: list[dict] = []
    occurrences: dict[int | None, int] = {}

    for index, boundary in enumerate(boundaries):
        end = boundaries[index + 1].start if index + 1 < len(boundaries) else len(text)
        if boundary.kind == "section":
            sections.append(
                {
                    "heading": boundary.line.strip("' ").rstrip(":"),
                    "start": boundary.start,
                    "end": end,
                }
            )
            continue

        block = text[boundary.start : end]
        page_count, page_count_candidate, page_count_raw, page_flags = _page_count(
            block
        )
        for fields in parse_header_line(boundary.line):
            occurrences[fields.year] = occurrences.get(fields.year, 0) + 1
            suffix = _letter_suffix(occurrences[fields.year])
            year_anchor = str(fields.year) if fields.year is not None else "x"
            edition_id = f"klawiter:edition/{page_id}-{year_anchor}-{suffix}"
            flags = list(dict.fromkeys((*fields.flags, *page_flags)))
            source_hash = hashlib.sha256(block.encode("utf-8")).hexdigest()
            edition: dict = {
                "@id": edition_id,
                "@type": "schema:Book",
                "schema:exampleOfWork": {"@id": f"klawiter:work/{page_id}"},
                "klawiter:sourcePageId": page_id,
                "klawiter:headerLine": boundary.line,
                "klawiter:yearRaw": fields.year_raw,
                "klawiter:reviewStatus": "proposed",
                "klawiter:reviewFlags": flags,
                "klawiter:sourceSliceSha256": source_hash,
            }
            if fields.year is not None:
                edition["schema:datePublished"] = str(fields.year)
            if fields.publisher:
                edition["schema:publisher"] = fields.publisher
            if fields.location:
                edition["schema:locationCreated"] = fields.location
            if page_count is not None:
                edition["schema:numberOfPages"] = page_count
            if page_count_candidate is not None:
                edition["klawiter:pageCountCandidate"] = page_count_candidate
            if page_count_raw is not None:
                edition["klawiter:pageCountRaw"] = page_count_raw
            if fields.series:
                edition["klawiter:headerSeries"] = fields.series
            if fields.description:
                edition["schema:description"] = fields.description
            editions.append(edition)

            annotation_id = edition_id.replace(
                "klawiter:edition/", "klawiter:annotation/"
            )
            annotations.append(
                {
                    "@id": annotation_id,
                    "@type": "oa:Annotation",
                    "oa:hasBody": {"@id": edition_id},
                    "oa:hasTarget": {
                        "@type": "oa:SpecificResource",
                        "oa:hasSource": {"@id": f"klawiter:sourceText/{page_id}"},
                        "oa:hasSelector": {
                            "@type": "oa:TextPositionSelector",
                            "oa:start": boundary.start,
                            "oa:end": end,
                        },
                    },
                }
            )

    work = {
        "@id": f"klawiter:work/{page_id}",
        "@type": "schema:CreativeWork",
        "schema:name": work_title,
        "klawiter:sourcePageId": page_id,
        "schema:workExample": [{"@id": edition["@id"]} for edition in editions],
    }
    return {
        "work": work,
        "editions": editions,
        "annotations": annotations,
        "unsegmentedSections": sections,
    }


def apply_review_reconciliation(
    dataset: dict, reconciliation: dict, modeling_decisions: dict
) -> dict:
    """Apply independently verified sample decisions without hiding uncertainty."""
    reviewed = copy.deepcopy(dataset)
    editions = {edition["@id"]: edition for edition in reviewed["editions"]}
    works = {work["@id"]: work for work in reviewed["works"]}
    annotations = {
        annotation["oa:hasBody"]["@id"]: annotation
        for annotation in reviewed["annotations"]
    }

    claim_specs = {
        item["edition_id"]: item
        for item in modeling_decisions.get("contested_claims", [])
    }
    contested_claims: list[dict] = []
    candidate_works: list[dict] = []

    for decision in reconciliation["case_decisions"]:
        edition_id = decision["edition_id"]
        if edition_id not in editions:
            raise ValueError(f"Reviewed edition is absent from Gate 1: {edition_id}")
        edition = editions[edition_id]
        source = decision["source"]
        annotation = annotations[edition_id]
        selector = annotation["oa:hasTarget"]["oa:hasSelector"]
        if [selector["oa:start"], selector["oa:end"]] != source["selector"]:
            raise ValueError(f"Reviewed selector changed for {edition_id}")
        if edition["klawiter:sourceSliceSha256"] != source["slice_sha256"]:
            raise ValueError(f"Reviewed source slice changed for {edition_id}")
        if edition["klawiter:headerLine"].rstrip() != source["header"].rstrip():
            raise ValueError(f"Reviewed header changed for {edition_id}")

        disposition = decision["disposition"]
        edition["klawiter:reviewStatus"] = (
            "contested" if disposition == "unresolved" else "confirmed"
        )
        edition["klawiter:reviewDecision"] = disposition
        edition["klawiter:reviewBasis"] = decision["basis"]
        if disposition == "unresolved":
            specification = claim_specs.get(edition_id)
            if specification is None:
                raise ValueError(
                    f"Unresolved edition lacks a contested-claim specification: {edition_id}"
                )
            edition["klawiter:reviewFlags"] = list(
                dict.fromkeys(
                    (*edition["klawiter:reviewFlags"], "contested-work-identity")
                )
            )
            work_binding = edition.pop("schema:exampleOfWork")
            claim_id = specification["claim_id"]
            edition["klawiter:contestedClaim"] = {"@id": claim_id}
            edition["klawiter:bindingStatus"] = "contested"
            work = works[work_binding["@id"]]
            work["schema:workExample"] = [
                example
                for example in work["schema:workExample"]
                if example["@id"] != edition_id
            ]

            interpretations = []
            for item in specification["interpretations"]:
                proposed_object = item["proposed_object"]
                interpretations.append(
                    {
                        "@id": item["interpretation_id"],
                        "@type": "klawiter:ClaimInterpretation",
                        "schema:name": item["label"],
                        "schema:description": item["basis"],
                        "klawiter:proposedObject": {"@id": proposed_object},
                        "klawiter:interpretationStatus": "contested",
                    }
                )
                candidate = item.get("candidate_work")
                if candidate:
                    candidate_works.append(
                        {
                            "@id": candidate["work_id"],
                            "@type": "klawiter:WorkIdentityCandidate",
                            "schema:name": candidate["label"],
                            "klawiter:identityStatus": "contested",
                            "prov:wasDerivedFrom": {"@id": annotation["@id"]},
                        }
                    )

            review_actions = []
            for reviewer, outcome in sorted(decision["reviewers"].items()):
                review_actions.append(
                    {
                        "@id": f"klawiter:review/{edition_id.rsplit('/', 1)[1]}/reviewer-{reviewer}",
                        "@type": "klawiter:ReviewAction",
                        "prov:wasAssociatedWith": {
                            "@id": f"klawiter:agent/sample-reviewer-{reviewer}"
                        },
                        "prov:used": {"@id": annotation["@id"]},
                        "klawiter:reviewOutcome": outcome,
                    }
                )
            review_actions.append(
                {
                    "@id": f"klawiter:review/{edition_id.rsplit('/', 1)[1]}/reconciliation",
                    "@type": "klawiter:ReviewAction",
                    "prov:wasAssociatedWith": {
                        "@id": "klawiter:agent/reconciliation-verifier"
                    },
                    "prov:used": [
                        {"@id": annotation["@id"]},
                        {"@id": "klawiter:evidence/sample-reconciliation"},
                    ],
                    "klawiter:reviewOutcome": "unresolved",
                    "klawiter:reviewBasis": decision["basis"],
                }
            )
            contested_claims.append(
                {
                    "@id": claim_id,
                    "@type": "klawiter:ContestedClaim",
                    "klawiter:claimSubject": {"@id": edition_id},
                    "klawiter:claimPredicate": {"@id": specification["predicate"]},
                    "klawiter:claimStatus": "contested",
                    "klawiter:decisionStatus": specification["decision_status"],
                    "klawiter:sourcePageId": edition["klawiter:sourcePageId"],
                    "klawiter:sourceSliceSha256": edition["klawiter:sourceSliceSha256"],
                    "oa:hasTarget": copy.deepcopy(annotation["oa:hasTarget"]),
                    "prov:wasDerivedFrom": [
                        {"@id": annotation["@id"]},
                        {"@id": "klawiter:evidence/sample-reconciliation"},
                    ],
                    "klawiter:interpretation": interpretations,
                    "klawiter:reviewAction": review_actions,
                }
            )

    carriers: list[dict] = []
    for relation in modeling_decisions["carrier_relations"]:
        edition_id = relation["edition_id"]
        edition = editions.get(edition_id)
        if edition is None:
            raise ValueError(
                f"Carrier decision references absent edition: {edition_id}"
            )
        carrier_id = relation["carrier_id"]
        edition["schema:isPartOf"] = {"@id": carrier_id}
        carriers.append(
            {
                "@id": carrier_id,
                "@type": "schema:PublicationVolume",
                "schema:name": relation["source_label"],
                "klawiter:identityScope": "source-occurrence",
                "klawiter:reviewStatus": "confirmed",
                "klawiter:sourceEdition": {"@id": edition_id},
            }
        )

    reviewed["carriers"] = carriers
    reviewed["contestedClaims"] = contested_claims
    reviewed["candidateWorks"] = candidate_works
    reviewed["klawiter:reviewEvidenceSha256"] = modeling_decisions[
        "sample_reconciliation_sha256"
    ]
    reviewed["klawiter:reviewContract"] = (
        "Agentic sample decisions are confirmed only within their exact selectors; "
        "all other editions remain proposals and contested bindings remain explicit "
        "claims with open decisions."
    )
    return reviewed


def count_edition_headers(text: str) -> int:
    """Count source lines that satisfy the ratified edition-header rule."""
    return len(EDITION_HEADER_RE.findall(text))


def build_corpus(rows: Iterable[dict[str, str]]) -> dict:
    """Build the deterministic Gate-1 graph for every intended source page."""
    works: list[dict] = []
    editions: list[dict] = []
    annotations: list[dict] = []
    page_summaries: list[dict] = []
    source_hasher = hashlib.sha256()

    ordered_rows = sorted(rows, key=lambda row: int(row["page_id"]))
    for row in ordered_rows:
        if row.get("page_namespace", "0") != "0":
            continue
        text = row.get("content", "")
        header_count = count_edition_headers(text)
        if header_count < 2:
            continue
        page_id = int(row["page_id"])
        result = segment_page(page_id, text, row.get("page_title", ""))
        works.append(result["work"])
        editions.extend(result["editions"])
        annotations.extend(result["annotations"])
        source_hasher.update(f"{page_id}\0".encode("utf-8"))
        source_hasher.update(text.encode("utf-8"))
        source_hasher.update(b"\0")
        page_summaries.append(
            {
                "sourcePageId": page_id,
                "sourceTextId": int(row["text_id"]) if row.get("text_id") else None,
                "headerCount": header_count,
                "editionCount": len(result["editions"]),
                "reviewFlagCount": sum(
                    bool(edition["klawiter:reviewFlags"])
                    for edition in result["editions"]
                ),
            }
        )

    return {
        "@context": {
            "schema": "https://schema.org/",
            "klawiter": "https://chpollin.github.io/klawiter-rescue/vocab/",
            "oa": "http://www.w3.org/ns/oa#",
            "prov": "http://www.w3.org/ns/prov#",
            "dcterms": "http://purl.org/dc/terms/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "schema:datePublished": {"@type": "xsd:gYear"},
            # Every top-level array key must be a defined term: JSON-LD drops
            # undefined keys silently, which collapsed this dataset to 6 RDF
            # triples and made the SHACL gate validate an empty graph.
            "works": {"@id": "klawiter:works", "@container": "@set"},
            "editions": {"@id": "klawiter:editions", "@container": "@set"},
            "annotations": {"@id": "klawiter:annotations", "@container": "@set"},
            "carriers": {"@id": "klawiter:carriers", "@container": "@set"},
            "contestedClaims": {
                "@id": "klawiter:contestedClaims",
                "@container": "@set",
            },
            "candidateWorks": {
                "@id": "klawiter:candidateWorks",
                "@container": "@set",
            },
            "pageSummaries": {
                "@id": "klawiter:pageSummaries",
                "@container": "@set",
            },
        },
        "@id": "klawiter:dataset/work-editions",
        "@type": "schema:Dataset",
        "dcterms:license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
        # This graph is the canonical dataset for pages with multiple
        # editions (operator decision 2026-08-26); the flat dataset is its
        # derived convenience projection.
        "klawiter:derivedProjection": {"@id": "klawiter:klawiter-bibliography"},
        "klawiter:authorityNote": (
            "This Work/Edition graph is the canonical dataset for pages "
            "with multiple editions; the flat dataset klawiter.jsonld is a "
            "derived convenience projection."
        ),
        "klawiter:algorithmVersion": ALGORITHM_VERSION,
        "klawiter:selectionRule": "namespace 0 page with at least two source lines matching a four-digit or ca.-year bold header",
        "klawiter:sourceCorpusSha256": source_hasher.hexdigest(),
        "works": works,
        "editions": editions,
        "annotations": annotations,
        "pageSummaries": page_summaries,
    }


def apply_confirmed_work_links(dataset, work_decisions, szd_authorities):
    """Attach confirmed SZD/GND identities as schema:sameAs on work nodes.

    The edition graph is the canonical dataset (operator decision
    2026-08-26); the human-confirmed work identities must live here, not
    only in a reconciliation side file. Only confirmed or corrected
    decisions produce links; everything else stays a candidate.
    """
    by_szd = {authority["szdId"]: authority for authority in szd_authorities}
    links = {}
    for decision in work_decisions.get("decisions", []):
        if decision.get("action") not in {"confirm", "correct"}:
            continue
        authority = by_szd.get(decision.get("szdId"))
        if not authority:
            continue
        uris = [authority["szdUri"]]
        if authority.get("gndUri"):
            uris.append(authority["gndUri"])
        links[decision["subjectId"]] = uris
    for work in dataset["works"]:
        uris = links.get(work["@id"])
        if uris:
            work["schema:sameAs"] = [{"@id": uri} for uri in uris]
    return len(links)
