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

from lib.patterns import (
    ABSENCE_MARKS,
    CORPORATE_SUFFIXES,
    EDITION_YEAR_PREFIX,
    PLACE_NAMES_STANDING_ALONE,
    PLACE_QUALIFIERS,
)

ALGORITHM_VERSION = "1.3"
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
    imprint: str | None
    imprints: tuple[Imprint, ...]
    series: str | None
    description: str | None
    flags: tuple[str, ...]

    @property
    def publishers(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(item.publisher for item in self.imprints if item.publisher)
        )

    @property
    def locations(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.place for item in self.imprints if item.place))

    @property
    def publisher(self) -> str | None:
        return self.publishers[0] if self.publishers else None

    @property
    def location(self) -> str | None:
        return self.locations[0] if self.locations else None


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
    # A bracket after a comma is an imprint segment, the supplied place of
    # "Milliyet Yayınları, [Istanbul]" or the "[s.l.]" of "[s.n.], [s.l.]".
    if not match or value[: match.start()].rstrip().endswith(","):
        return value.strip(), None
    return value[: match.start()].strip(), match.group(1)


# The imprint continues after the closing bold: either the bold holds only the
# year ("'''[2010]:''' The Continuum International Publishing Group, New
# York", page 1949), or the bold imprint breaks off before a gloss and the place
# ("'''[2009]: al-Markaz al-Qawmī li-l-Tarjamah''' [National Center for
# Translation], al-Qāhirah [Cairo]", page 4216).
# A sentence after the bold is a description, not an imprint ("'''[2009]'''.
# Story read by … Berlin: Argon Verlag, 2009", page 279), so the suffix may
# open only with the colon, holds no sentence break and ends in no number.
_IMPRINT_SUFFIX_RE = re.compile(r"^:?\s*(?=[^\W\d_])(?!.*'')(?!.*\.\s)[^\n]*,[^\n\d]*$")
_GLOSS_CONTINUATION_RE = re.compile(r"^(?:\s*\[[^\[\]\n]*\])*\s*,\s*\S")
_EXTENT_IN_SUFFIX_RE = re.compile(r"\d\)?p\.")


def _continues_imprint(field_text: str, suffix: str) -> str | None:
    """The imprint text when the suffix after the bold continues it."""
    if _EXTENT_IN_SUFFIX_RE.search(suffix):
        return None
    if not field_text.strip():
        if _IMPRINT_SUFFIX_RE.match(suffix):
            return suffix.lstrip(":").strip()
        return None
    if field_text.rstrip().endswith(",") or _GLOSS_CONTINUATION_RE.match(suffix):
        joiner = "" if suffix.lstrip().startswith(",") else " "
        return f"{field_text.strip()}{joiner}{suffix.strip()}"
    return None


@dataclass(frozen=True)
class Imprint:
    """One publisher and place pair of a header, both in source wording."""

    publisher: str | None
    place: str | None
    resolved: bool


def protected_mask(text: str) -> list[bool]:
    """Mark the characters inside balanced brackets or paired quotation marks.

    A comma or separator there belongs to a name ("Izdatel'stvo \\"Mir knigi,
    Literatura\\"", "[Pune, formerly Poona]") and never splits the imprint. An
    opener without its closer protects nothing, so one stray bracket cannot
    swallow the rest of the header.
    """
    mask = [False] * len(text)
    stack: list[int] = []
    for index, char in enumerate(text):
        if char in "[(":
            stack.append(index)
        elif char in "])" and stack:
            start = stack.pop()
            for position in range(start, index + 1):
                mask[position] = True
    for opener, closer in (('"', '"'), ("“", "”"), ("„", "“")):
        start = text.find(opener)
        while start >= 0:
            end = text.find(closer, start + 1)
            if end < 0:
                break
            for position in range(start, end + 1):
                mask[position] = True
            start = text.find(opener, end + 1)
    return mask


def _cuts(text: str, pattern: re.Pattern[str], mask: list[bool]) -> list[re.Match]:
    return [match for match in pattern.finditer(text) if not mask[match.start()]]


def _segments(text: str) -> list[tuple[int, int]]:
    """Spans of the comma segments of one imprint, outside protected regions."""
    mask = protected_mask(text)
    spans = []
    start = 0
    for index, char in enumerate(text):
        if char == "," and not mask[index]:
            spans.append((start, index))
            start = index + 1
    spans.append((start, len(text)))
    return [
        (start + len(text[start:end]) - len(text[start:end].lstrip()), end)
        for start, end in spans
        if text[start:end].strip()
    ]


def _segment_text(text: str, span: tuple[int, int]) -> str:
    return text[span[0] : span[1]].strip()


def _is_qualifier(segment: str) -> bool:
    if segment in PLACE_QUALIFIERS:
        return True
    # A bracket standing alone after a comma supplies the place or glosses it
    # ("Milliyet Yayınları, [Istanbul]", "ʿAṭāʾī, Tihrān, [Tehran]").
    return segment.startswith("[") and segment.endswith("]")


def _pair(text: str, *, continuation: bool = False) -> Imprint:
    """Read one publisher and its place from a single imprint statement.

    The place is the last comma segment, together with the trailing segments
    that qualify it (a state, a country, a supplied bracket). The publisher is
    everything before. The pair is resolved where the publisher is one segment
    once its legal-form suffixes are joined to it; otherwise the boundary
    between a publisher name with commas and a place hierarchy stays open.
    """
    spans = _segments(text)
    segments = [_segment_text(text, span) for span in spans]
    if not segments:
        return Imprint(None, None, True)
    if len(segments) == 1:
        single = segments[0]
        if single in PLACE_NAMES_STANDING_ALONE:
            return Imprint(None, single, True)
        period = PUBLISHER_PERIOD_RE.search(single)
        if period:
            return Imprint(
                single[: period.end() - 2].strip() or None,
                single[period.end() :].strip() or None,
                True,
            )
        return Imprint(_present(single), None, True)
    qualifiers = 0
    while qualifiers < len(segments) - 1 and _is_qualifier(
        segments[len(segments) - 1 - qualifiers]
    ):
        qualifiers += 1
    place_index = len(segments) - 1 - qualifiers
    if qualifiers and place_index == 0:
        # "Publisher, Country" and "Place, Country" read alike; a continuation
        # after "and" has no publisher of its own, a first statement has one.
        if continuation:
            return Imprint(None, text[spans[0][0] :].strip(), False)
        place_index = 1
    place = _present(text[spans[place_index][0] :].strip().rstrip(",").strip())
    publisher_segments = segments[:place_index]
    names = [item for item in publisher_segments if item not in CORPORATE_SUFFIXES]
    publisher = _present(text[: spans[place_index][0]].strip().rstrip(",").strip())
    return Imprint(publisher, place, len(names) <= 1)


def _present(value: str | None) -> str | None:
    """A publisher or place value, or None where the source marks its absence."""
    if not value or value.strip() in ABSENCE_MARKS:
        return None
    return value


# Co-imprints: "Nauka i izkustvo, Sofija / DPK St. Dobrev-Strandzhata, Varna".
# A slash counts only with space before it, so "Berlin/Darmstadt/Wien" and the
# parallel name "Trst/Trieste" stay one place.
_CO_IMPRINT_RE = re.compile(r"\s+/{1,2}\s*|;\s+")
_AND_RE = re.compile(r"(?<!,) and ")
# "Longmans, Green and Company": the word after "and" continues a firm name.
_FIRM_CONTINUATIONS = frozenset({"Company", "Co.", "Sons", "Son", "Brothers"})


def split_imprint(value: str) -> tuple[Imprint, ...]:
    """Split an imprint statement into publisher and place pairs.

    Co-imprints are separated at " / ", " // ", "; " and at an "and" that joins
    two complete statements. A part without a comma names no place and belongs
    to the publisher of the part after it ("Acantilado / Quaderns Crema, S. A.
    U., Barcelona"). Every value keeps its source wording.
    """
    text = value.strip()
    if not text:
        return ()
    mask = protected_mask(text)
    bounds = [0]
    for match in _cuts(text, _CO_IMPRINT_RE, mask):
        bounds.append(match.start())
        bounds.append(match.end())
    bounds.append(len(text))
    raw_parts = [
        (bounds[index], bounds[index + 1]) for index in range(0, len(bounds), 2)
    ]
    # Merge a part without its own place into the part after it, keeping the
    # separator as the source writes it.
    parts: list[tuple[int, int]] = []
    pending: int | None = None
    for start, end in raw_parts:
        chunk = text[start:end]
        begin = pending if pending is not None else start
        if not any(char == "," and not mask[start + i] for i, char in enumerate(chunk)):
            pending = begin
            continue
        parts.append((begin, end))
        pending = None
    if pending is not None:
        # A last part without a comma continues the place before it: the
        # parallel seats of "Holger Schildts Förlag, Stockholm / Helsingfors"
        # (page 4377) form one place statement.
        if parts:
            parts[-1] = (parts[-1][0], len(text))
        else:
            parts.append((pending, len(text)))

    imprints: list[Imprint] = []
    for start, end in parts:
        statement = text[start:end]
        local_mask = mask[start:end]
        pieces = [0]
        for match in _AND_RE.finditer(statement):
            if local_mask[match.start()]:
                continue
            left = statement[pieces[-1] : match.start()]
            right = statement[match.end() :]
            right_first = right.split(",", 1)[0].split()
            if (
                "," in left
                and "," in right
                and right_first
                and right_first[0] not in _FIRM_CONTINUATIONS
            ):
                pieces.extend((match.start(), match.end()))
        pieces.append(len(statement))
        for index in range(0, len(pieces), 2):
            imprints.append(
                _pair(
                    statement[pieces[index] : pieces[index + 1]],
                    continuation=index > 0,
                )
            )
    return tuple(imprints)


def _split_publisher_location(
    value: str,
) -> tuple[tuple[Imprint, ...], bool]:
    """The imprint pairs of a header field, and whether residue was repaired."""
    cleaned = re.sub(r"\]{2,}$", "", value).strip().rstrip("'").strip()
    normalized = cleaned != value.strip().rstrip("'").strip()
    return split_imprint(cleaned), normalized


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
    for index, part in enumerate(parts):
        match = HEADER_RE.match(part)
        if not match:
            parsed.append(
                HeaderFields(
                    year_raw="",
                    year=None,
                    imprint=part.strip() or None,
                    imprints=(Imprint(part.strip() or None, None, True),),
                    series=None,
                    description=suffix,
                    flags=("unparsed-header",),
                )
            )
            continue

        year_raw = match.group(1).strip()
        year_match = YEAR_RE.search(year_raw)
        year = int(year_match.group(1)) if year_match else None
        description = suffix
        continued = None
        if suffix and index == len(parts) - 1:
            continued = _continues_imprint(match.group(2), suffix)
        if continued is not None:
            # The trailing bracket of a continued imprint glosses its place
            # ("al-Qāhirah [Cairo]"); a series never follows the bold here.
            field_text, series, description = continued, None, None
        else:
            field_text, series = _split_series(match.group(2).strip())
        series = series or suffix_series
        imprints, normalized = _split_publisher_location(field_text)
        if "," not in field_text and PUBLISHER_PERIOD_RE.search(field_text):
            normalized = True
        imprint = re.sub(r"\]{2,}$", "", field_text).strip().rstrip("'").strip()
        flags: list[str] = []
        if len(parts) > 1:
            flags.append("compound-header")
        if "ca" in year_raw.casefold():
            flags.append("approximate-year")
        if year is None:
            flags.append("missing-year")
        if not any(item.place for item in imprints):
            flags.append("missing-location")
        if missing_close:
            flags.append("malformed-bold-header")
        if description:
            flags.append("header-suffix")
        if series:
            flags.append("header-series")
        if normalized:
            flags.append("normalized-header-residue")
        parsed.append(
            HeaderFields(
                year_raw=year_raw,
                year=year,
                imprint=imprint or None,
                imprints=imprints,
                series=series,
                description=description,
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


def _one_or_all(values: tuple[str, ...]) -> str | list[str]:
    return values[0] if len(values) == 1 else list(values)


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
            # A co-imprint names several publishers and places; the pairing
            # itself lives in the publication layer.
            if fields.publishers:
                edition["schema:publisher"] = _one_or_all(fields.publishers)
            if fields.locations:
                edition["schema:locationCreated"] = _one_or_all(fields.locations)
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


def _resolve_claim(
    claim: dict,
    edition: dict,
    works: dict,
    annotation: dict,
    resolution: dict,
) -> dict:
    """Close a contested work binding with the recorded decision.

    The claim stays in the graph with its interpretations and review history,
    now marked resolved, so the decision can be traced and revised. The
    accepted interpretation must propose a work candidate; that candidate
    becomes a work under its stable identifier, bound to the edition, and the
    rejected readings keep their objects without a binding. Returns the new
    work node.
    """
    selected = resolution["selected_interpretation"]
    accepted = [
        item for item in claim["klawiter:interpretation"] if item["@id"] == selected
    ]
    if len(accepted) != 1:
        raise ValueError(f"Resolution selects no interpretation of {claim['@id']}")
    work_id = accepted[0]["klawiter:proposedObject"]["@id"]
    if not work_id.startswith("klawiter:work-candidate/"):
        raise ValueError(f"Resolution of {claim['@id']} selects no work candidate")
    for item in claim["klawiter:interpretation"]:
        item["klawiter:interpretationStatus"] = (
            "accepted" if item["@id"] == selected else "rejected"
        )
    claim["klawiter:claimStatus"] = "resolved"
    claim["klawiter:decisionStatus"] = resolution["decision_status"]
    basis = f"{resolution['provenance']} {resolution['basis']}"
    claim["klawiter:hasReviewAction"].append(
        {
            "@id": resolution["review_id"],
            "@type": "klawiter:ReviewAction",
            "prov:wasAssociatedWith": {"@id": resolution["decided_by"]},
            "prov:used": [
                {"@id": annotation["@id"]},
                *({"@id": source} for source in resolution["evidence"]),
            ],
            "klawiter:reviewOutcome": "confirm",
            "klawiter:reviewBasis": basis,
            "dcterms:date": resolution["decided_on"],
        }
    )
    notes = resolution.get("review_notes", [])
    if notes:
        claim["klawiter:reviewNote"] = [note["detail"] for note in notes]

    specification = resolution["work"]
    work = {
        "@id": work_id,
        "@type": "schema:CreativeWork",
        "schema:name": specification["label"],
        "schema:creator": specification["creator"],
        "schema:genre": specification["genre"],
        "schema:isBasedOn": {"@id": specification["based_on"]},
        "schema:description": specification["relation"],
        "schema:workExample": [{"@id": edition["@id"]}],
        "prov:wasDerivedFrom": {"@id": claim["@id"]},
    }
    if specification["based_on"] not in works:
        raise ValueError(
            f"Adapted work is absent from Gate 1: {specification['based_on']}"
        )
    edition["schema:exampleOfWork"] = {"@id": work_id}
    edition["schema:translationOfWork"] = [
        {"@id": source} for source in resolution["translation_of"]
    ]
    edition["klawiter:reviewStatus"] = "confirmed"
    edition["klawiter:reviewDecision"] = "confirm"
    edition["klawiter:reviewBasis"] = basis
    edition["klawiter:bindingStatus"] = "decided"
    edition["klawiter:reviewFlags"] = list(
        dict.fromkeys(
            [
                *(
                    flag
                    for flag in edition["klawiter:reviewFlags"]
                    if flag != "contested-work-identity"
                ),
                *(note["code"] for note in notes),
            ]
        )
    )
    return work


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
            edition["klawiter:hasContestedClaim"] = {"@id": claim_id}
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
            claim = {
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
                "klawiter:hasReviewAction": review_actions,
            }
            resolution = specification.get("resolution")
            if resolution:
                work = _resolve_claim(claim, edition, works, annotation, resolution)
                reviewed["works"].append(work)
                works[work["@id"]] = work
                candidate_works[:] = [
                    item for item in candidate_works if item["@id"] != work["@id"]
                ]
            contested_claims.append(claim)

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
            # Summary children must survive expansion as well as the container.
            "sourcePageId": {"@id": "klawiter:sourcePageId", "@type": "xsd:integer"},
            "sourceTextId": {"@id": "klawiter:sourceTextId", "@type": "xsd:integer"},
            "headerCount": {"@id": "klawiter:headerCount", "@type": "xsd:integer"},
            "editionCount": {"@id": "klawiter:editionCount", "@type": "xsd:integer"},
            "reviewFlagCount": {
                "@id": "klawiter:reviewFlagCount",
                "@type": "xsd:integer",
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
