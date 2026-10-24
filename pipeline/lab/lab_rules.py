"""Pure rules of the lab data preparation (milestone L3 of knowledge/lab-frontend.md).

The functions here take plain values and return plain values, so the tests can
exercise them on small snippets of the real data without reading any file.
`prepare_lab_data.py` composes them over a committed snapshot.

Rules and their origin in the specification:

- occurrence matching (S2.1): word-boundary match, each comma-separated part
  matched on its own, the occurrence inside the own passage first;
- the page-level boundary check (S2.2), including the shared-year and
  missing-year cases;
- the provisional producer labels with the research coordinator's ruling of
  2026-10-23 (every agent label names LLM agents and "no person"), reader
  labels for deciders and evidence files, and decision dates read from the
  basis sentence where no date field exists;
- the section heading that holds a value outside every publication passage;
- title keys and the classification of bracketed original titles (relation 3
  of "What a work is in this data");
- the parse of the compiler's "Translations" section (relation 2).

Regime: flat script pipeline (pipeline/ is never installed). The module has no
first-party imports so that pytest can import it from this directory.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

RULES_VERSION = "lab-rules-2"

# Occurrence matching (S2.1)


def split_parts(value: object) -> list[str]:
    """Parts of a value that are matched separately, duplicates removed.

    A comma-separated value such as the LLM translator string of page 448
    ("Božena Koseková, Božena Koseková, Božena Koselová") is matched part by
    part, because its parts may come from different passages.
    """
    if value is None or value == "":
        return []
    if isinstance(value, (int, float)):
        return [str(value)]
    parts = [part.strip() for part in str(value).split(",")]
    return list(dict.fromkeys(part for part in parts if part))


def find_occurrences(text: str, needle: str) -> list[tuple[int, int]]:
    """Exact, case-sensitive occurrences of `needle` that respect word boundaries.

    A boundary means no Unicode word character directly before or after the
    match, so "Praha" matches in "Praha/Prague" but not in "Prahaus". A
    number is bounded by digits only, because extents are written "348p.":
    "348" matches there but not in "1348".
    """
    if not needle:
        return []
    edge = r"\d" if needle.isdigit() else r"\w"
    pattern = re.compile(rf"(?<!{edge})" + re.escape(needle) + rf"(?!{edge})")
    return [(m.start(), m.end()) for m in pattern.finditer(text)]


@dataclass(frozen=True)
class Passage:
    """The text range of one publication inside `fullBibliographicEntry`."""

    pub_id: str
    year: int | None
    start: int | None
    end: int | None

    def holds(self, span: tuple[int, int]) -> bool:
        if self.start is None or self.end is None:
            return False
        return self.start <= span[0] and span[1] <= self.end


def passage_of(span: tuple[int, int], passages: list[Passage]) -> Passage | None:
    for passage in passages:
        if passage.holds(span):
            return passage
    return None


def value_occurrences(
    text: str, value: object, passages: list[Passage], own_ids: set[str]
) -> dict:
    """Occurrences of every part of a value, own-passage occurrences first.

    `own_ids` names the publications whose passage counts as the value's own:
    the publication itself for a publication field, the year-supplying
    publications for a page-level value.
    """
    parts = []
    for part in split_parts(value):
        spans = find_occurrences(text, part)
        rows = []
        for span in spans:
            holder = passage_of(span, passages)
            row = {
                "start": span[0],
                "end": span[1],
                "publicationId": holder.pub_id if holder else None,
                "own": bool(holder and holder.pub_id in own_ids),
            }
            if holder is None and passages:
                row |= section_of(text, span[0])
            rows.append(row)
        rows.sort(key=lambda row: (not row["own"], row["start"]))
        parts.append({"part": part, "occurrences": rows, "noExactOccurrence": not rows})
    return {
        "parts": parts,
        "noExactOccurrence": bool(parts) and all(p["noExactOccurrence"] for p in parts),
    }


# Page-level boundary check (S2.2)

BOUNDARY_FIELDS = ("publisher", "location", "translator", "pageCount")


def boundary_check(
    text: str,
    record_year: int | None,
    passages: list[Passage],
    values: dict[str, object],
) -> dict:
    """Check whether page-level values occur only in another publication's passage.

    The check runs only on pages with a publication breakdown. Where several
    publications share the record's year, an occurrence in any of them passes.
    Where no publication has the record's year, the check does not run and
    says so. A part warns ("fires") only when every one of its occurrences lies
    inside the passage of a publication other than the year-supplying ones;
    the result names those publications.
    """
    if not passages:
        return {"run": False, "reason": "no-publication-breakdown", "fields": {}}
    if record_year is None:
        return {"run": False, "reason": "record-has-no-year", "fields": {}}
    year_passages = [p for p in passages if p.year == record_year]
    if not year_passages:
        return {
            "run": False,
            "reason": "record-year-matches-no-publication",
            "fields": {},
        }
    if all(p.start is None for p in year_passages):
        return {
            "run": False,
            "reason": "year-publication-passage-not-located",
            "fields": {},
        }
    year_ids = {p.pub_id for p in year_passages}
    fields = {}
    for field in BOUNDARY_FIELDS:
        value = values.get(field)
        if value is None or value == "":
            continue
        part_results = [
            _boundary_part(text, part, passages, year_ids)
            for part in split_parts(value)
        ]
        fields[field] = {
            "fires": any(r["result"] == "fires" for r in part_results),
            "parts": part_results,
        }
    return {
        "run": True,
        "yearPublications": sorted(year_ids),
        "sharedYear": len(year_ids) > 1,
        "fields": fields,
    }


def _boundary_part(
    text: str, part: str, passages: list[Passage], year_ids: set[str]
) -> dict:
    spans = find_occurrences(text, part)
    if not spans:
        return {"part": part, "result": "no-exact-occurrence", "heldBy": []}
    holders = [passage_of(span, passages) for span in spans]
    if any(h is not None and h.pub_id in year_ids for h in holders):
        return {"part": part, "result": "pass", "heldBy": []}
    if all(h is not None for h in holders):
        held = {h.pub_id: h.year for h in holders}
        return {
            "part": part,
            "result": "fires",
            "heldBy": [
                {"publicationId": k, "year": v} for k, v in sorted(held.items())
            ],
        }
    return {"part": part, "result": "outside-publication-passages", "heldBy": []}


# Provisional producer labels

LABEL_MAPPING_NOTE = (
    "Provisional mapping from decider strings to producer labels "
    "(knowledge/lab-frontend.md, Provisional producer labels) until the shared "
    "claim schema provides a typed producer class."
)
NO_PERSON = "no person"
NO_SOURCE_OCCURRENCE = "no source occurrence"
# Every decider stored today is an LLM agent or a test fixture; none is a person.
# The research coordinator's ruling of 2026-10-23 requires every agent label to
# say "LLM" and "no person" until the operator decides on the delegation.
DECIDER_LABELS = {
    "independent-verification-agent": "independent LLM agent review, no person",
    "main-instance": "the main LLM agent under operator delegation, no person",
    "repository-ground-truth-fixture": (
        "a test fixture of twenty places, no source occurrence, no person"
    ),
    "klawiter:agent/sample-reviewer-a": "LLM agent reviewer A, no person",
    "klawiter:agent/sample-reviewer-b": "LLM agent reviewer B, no person",
    "klawiter:agent/reconciliation-verifier": (
        "LLM agent for verification and reconciliation, no person"
    ),
    "klawiter:agent/main-instance": (
        "the main LLM agent under operator delegation, no person"
    ),
}
# Short producer label beside the state word, in the wording the operator set
# for every agent decision on 2026-10-24. It carries "no person", which the
# production frontend's DECIDER_PRODUCERS does not yet do. The record of the
# edition sample of 2026-08-21 itself names no delegation (lab-frontend.md).
AGENT_DELEGATED = "LLM agent, delegated, no person"
DECIDER_SHORT = {
    "independent-verification-agent": AGENT_DELEGATED,
    "main-instance": AGENT_DELEGATED,
    "klawiter:agent/main-instance": AGENT_DELEGATED,
    "repository-ground-truth-fixture": "test fixture, no person",
    "klawiter:agent/sample-reviewer-a": AGENT_DELEGATED,
    "klawiter:agent/sample-reviewer-b": AGENT_DELEGATED,
    "klawiter:agent/reconciliation-verifier": AGENT_DELEGATED,
}
PERSON_DECIDERS: frozenset[str] = frozenset()


def decider_label(decider: str | None) -> str:
    """Reader label of a decider string; unknown deciders stay visible as such."""
    if not decider:
        return "decider not recorded"
    return DECIDER_LABELS.get(decider, f"unlabelled decider {decider}")


def decider_short(decider: str | None) -> str:
    """Short producer label beside a state word."""
    if not decider:
        return "producer not recorded"
    if decider in PERSON_DECIDERS:
        return "person"
    return DECIDER_SHORT.get(decider, decider)


def has_source_occurrence(evidence: list[str]) -> bool:
    return any(str(e).startswith("klawiter:sourceOccurrence/") for e in evidence)


def producer_label(decision: dict) -> dict:
    """State, producer, warning and link flag of one stored place decision.

    Follows the table "Provisional producer labels" of the specification. A
    confirmation without a source occurrence keeps the state word but carries
    the warning "no source occurrence", which the interface shows beside it.
    """
    action = decision.get("action")
    decider = decision.get("decidedBy")
    with_occurrence = has_source_occurrence(decision.get("evidence") or [])
    label = {
        "warning": None,
        "person": decider in PERSON_DECIDERS,
        "producerShort": decider_short(decider),
    }
    if action in ("confirm", "correct") and decider == "independent-verification-agent":
        if with_occurrence:
            producer = (
                "independent LLM agents against source and Wikidata, adjudicated "
                "by the main LLM agent under operator delegation, no person"
            )
        else:
            producer = "LLM agent review, no source occurrence, no person"
            label["warning"] = NO_SOURCE_OCCURRENCE
        return label | {"state": "confirmed", "producer": producer, "link": True}
    if action in ("confirm", "correct") and decider == "main-instance":
        return label | {
            "state": "confirmed",
            "producer": "main LLM agent under operator delegation, no person",
            "link": True,
        }
    if action == "reject":
        return label | {
            "state": None,
            "producer": f"candidate rejected by {decider_label(decider)}",
            "link": False,
        }
    if action == "unresolved":
        return label | {
            "state": "contested",
            "producer": f"open, readings listed; left open by {decider_label(decider)}",
            "link": False,
        }
    return label | {
        "state": None,
        "producer": f"unmapped decision {action} by {decider_label(decider)}",
        "link": False,
    }


SAMPLE_REVIEW_PRODUCER = (
    "two independent LLM agent reviews, reconciled by an LLM agent for "
    "verification, no person"
)
SAMPLE_DISPOSITIONS = {
    "confirm": "segment and fields confirmed",
    "correct": "confirmed with a documented field correction",
    "reject-proposal": "confirmed after a reviewer's alternative reading was rejected",
    "unresolved": "left open",
}


def edition_assignment(
    review_status: str | None,
    edition_id: str | None,
    sample_case: dict | None,
    sample_date: str | None,
    claim: dict | None,
) -> dict:
    """State and producer of a publication's edition assignment (S2.3).

    The published side files hold the state only. The producer comes from the
    tracked edition-sample reconciliation, or from a decided edition claim in
    the published reconciliation data; otherwise it reads "producer not
    recorded".
    """
    state = review_status or "proposed"
    base = {"state": state, "inEditionModel": edition_id is not None}
    if state == "proposed":
        return base | {
            "producer": "a deterministic rule, not reviewed",
            "producerShort": "rule",
        }
    decisions = [
        r
        for r in (claim or {}).get("reviewHistory") or []
        if r.get("outcome") in ("confirm", "correct")
    ]
    if decisions:
        last = decisions[-1]
        when = decision_date(last.get("date"), last.get("basis"))
        return base | {
            "producer": decider_label(last.get("reviewer")),
            "producerShort": decider_short(last.get("reviewer")),
            "date": when["date"],
            "detail": "decided as an edition claim with review history",
        }
    if sample_case:
        return base | {
            "producer": SAMPLE_REVIEW_PRODUCER,
            "producerShort": AGENT_DELEGATED,
            "date": sample_date,
            "detail": SAMPLE_DISPOSITIONS.get(
                sample_case.get("disposition"), sample_case.get("disposition")
            ),
        }
    return base | {
        "producer": "producer not recorded",
        "producerShort": "producer not recorded",
    }


_BASIS_DATE = re.compile(r"\bon (\d{4}-\d{2}-\d{2})\b")


def decision_date(decided_at: str | None, basis: str | None) -> dict:
    """The decision date, from its field or else from the basis sentence."""
    if decided_at:
        return {"date": str(decided_at)[:10], "dateSource": "recorded"}
    m = _BASIS_DATE.search(basis or "")
    if m:
        return {"date": m.group(1), "dateSource": "basis text"}
    return {"date": None, "dateSource": None}


_OCCURRENCE_REF = re.compile(r"^klawiter:sourceOccurrence/location/(\d+)/(\d+)/(\d+)$")
_AGENT_REVIEW_FILE = re.compile(r"location-agent-review-(\d{4}-\d{2}-\d{2})\.json$")


def evidence_label(ref: str) -> dict:
    """An evidence reference in reader terms, the raw reference kept beside it.

    File paths and anchors are internal names, so they are translated into
    what the file is; source occurrences keep page and text for a link.
    """
    ref = str(ref)
    m = _OCCURRENCE_REF.match(ref)
    if m:
        return {
            "kind": "source-occurrence",
            "pageId": int(m.group(1)),
            "textId": int(m.group(2)),
            "n": int(m.group(3)),
            "ref": ref,
        }
    path = ref.split("#", 1)[0]
    if path.endswith("location-low-score-review.json"):
        label = "LLM agent review of low-scoring Wikidata candidates"
    elif m := _AGENT_REVIEW_FILE.search(path):
        label = f"LLM agent review of {m.group(1)}"
    elif path.endswith("wikidata_ground_truth.json"):
        label = "test fixture of twenty places"
    else:
        label = f"file {path.rsplit('/', 1)[-1]}"
    return {"kind": "file", "label": label, "ref": ref}


_WIKI_LINK = re.compile(r"\[\[([^\[\]|]*\|)?([^\[\]]*)\]\]")


def plain_wiki_text(text: str | None) -> str | None:
    """Wiki markup removed from a quoted source line: bold, italics, links."""
    if text is None:
        return None
    text = _WIKI_LINK.sub(lambda m: m.group(2), text)
    return re.sub(r"'{2,}", "", text)


_LABEL_LINE_AT = re.compile(r"^[ \t]*([^\n:\[\]\d]{2,40}?)[ \t]*:[ \t]*$", re.MULTILINE)
# Matched at a line start through `match(text, pos)`, so it carries no `^`.
_INLINE_LABEL = re.compile(r"[ \t]*([^\n:\[\]\d]{2,40}?)[ \t]*:\s")


def section_of(text: str, offset: int) -> dict:
    """The compiler's section heading before an offset, and an inline line label.

    Headings are bare label lines such as "Translations:" or "Contents:"; a
    line such as "Albanian: Padurimi ..." also names its language. The result
    says where a value outside every publication passage stands.
    """
    heading = None
    for m in _LABEL_LINE_AT.finditer(text, 0, offset):
        heading = m.group(1).strip()
    line_start = text.rfind("\n", 0, offset) + 1
    inline = _INLINE_LABEL.match(text, line_start)
    return {
        "section": heading,
        "lineLabel": inline.group(1).strip()
        if inline and inline.end() <= offset
        else None,
    }


# Title keys and bracket classes (relation 3)

_APOSTROPHES = str.maketrans({c: "'" for c in "‘’ʼʻ`´′"})
_QUOTES = '"“”„«»‹›'
GENRE_PHRASE = re.compile(
    r"^(?:ein|eine)?\s*(?:roman|romane|novelle|novellen|erzählung|erzählungen|"
    r"legende|legenden|erlebnis|dichtung|drama|schauspiel|tragödie|komödie|"
    r"gedicht|gedichte|essay|essays|biographie|romanentwurf|rede)$"
)
LEADING_ARTICLE = re.compile(r"^(?:der|die|das|ein|eine)\s+")


def normalise_title(text: str) -> str:
    """Unicode compatibility form, straight apostrophes, no quotes, case-folded."""
    text = unicodedata.normalize("NFKC", text).translate(_APOSTROPHES)
    text = "".join(c for c in text if c not in _QUOTES)
    text = " ".join(text.casefold().split())
    return text.strip(" .,;:")


def strip_page_suffixes(title: str, suffix_words: frozenset[str]) -> str:
    """Remove disambiguation suffixes of a page title.

    Trailing parentheticals such as "(VIST)", "(IS)" or "(Croatian)" go, and a
    trailing " / <word>" goes when the word is a known suffix such as
    "Volume" or a language name, since " / " otherwise joins several titles.
    """
    previous = None
    while previous != title:
        previous = title
        title = re.sub(r"\s*\([^()]*\)\s*$", "", title).strip()
        m = re.search(r"\s+/\s+([^/]+)$", title)
        if m and m.group(1).strip().casefold() in suffix_words:
            title = title[: m.start()].strip()
    return title


def title_key(text: str, suffix_words: frozenset[str] = frozenset()) -> str:
    """Comparison key: normalised, suffixes and trailing genre segments removed."""
    key = normalise_title(strip_page_suffixes(text, suffix_words))
    segments = [s for s in re.split(r"\.\s+", key) if s]
    while len(segments) > 1 and GENRE_PHRASE.match(segments[-1].strip(" .,;:")):
        segments.pop()
    return ". ".join(segments).strip(" .,;:")


def variant_key(key: str) -> str:
    """Looser key used only to list possible variants, never to merge.

    It drops a leading article, diacritics and punctuation, so that "Der
    Brief einer Unbekannten" and "Joseph Fouche: Bildnis ..." surface beside
    "Brief einer Unbekannten" and "Joseph Fouché. Bildnis ...".
    """
    decomposed = unicodedata.normalize("NFKD", key)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    plain = " ".join(re.sub(r"[^\w\s]", " ", plain).split())
    return LEADING_ARTICLE.sub("", plain)


SEVERAL_TITLES = re.compile(r"\s\*\s|\s/\s|\s//\s|;\s|\s=\s")
YEAR = re.compile(r"(?<!\d)(?:1[5-9]\d\d|20\d\d)(?!\d)")
ENGLISH_WORDS = frozenset(
    "the of and a an from with for to in on by his her my our their is are "
    "translated translation film based adaptation stories story novel novella "
    "novellas poems letters essays selected collected life biography".split()
)
GERMAN_WORDS = frozenset(
    "der die das und ein eine einer eines des dem den von mit im zum zur aus "
    "über auf um".split()
)


def classify_bracket(content: str, places: frozenset[str]) -> str:
    """Class of a bracket's content: a candidate title or one excluded kind.

    Excluded kinds, checked in this order: "year-or-number" (a year, or no
    letters at all), "several-titles" (joined by " * ", " / ", " // ", "; " or
    " = "), "place" (a known place name), "english-gloss" (English function
    words and no German ones). A trailing translator note is removed first.
    Everything else is "title".
    """
    stripped = strip_bracket_note(content)
    if not stripped or YEAR.search(stripped) or not re.search(r"[^\W\d_]", stripped):
        return "year-or-number"
    if SEVERAL_TITLES.search(stripped):
        return "several-titles"
    if normalise_title(stripped) in places:
        return "place"
    words = set(re.findall(r"[^\W\d_]+", stripped.casefold()))
    if words & ENGLISH_WORDS and not words & GERMAN_WORDS:
        return "english-gloss"
    return "title"


_TRAILING_NOTE = re.compile(r"\.\s+(?:Translated|Translation)(?!\w).*$", re.DOTALL)


def strip_bracket_note(content: str) -> str:
    """Drop a trailing translator note such as ". Translated by E. Ter-Minasian".

    The compiler sometimes puts the note into the bracket after the original
    title (page 2694); without the note the bracket holds a plain title.
    """
    return _TRAILING_NOTE.sub("", content.strip()).strip()


def lead_key(content: str) -> str:
    """Title key of the first sentence of a bracket, to attribute an excluded one."""
    first = re.split(r"\.\s+|,\s+|:\s+", strip_bracket_note(content), maxsplit=1)[0]
    return title_key(first)


def several_title_parts(content: str) -> list[str]:
    return [p.strip() for p in SEVERAL_TITLES.split(content) if p.strip()]


_GAP_MAX = 40
_CONTAINER_GAP = re.compile(r"[\"”']\s+in\s")


def first_bracket_after_title(text: str, titles: list[str]) -> dict | None:
    """The first bracket after the page title on the same line.

    The title is searched case-insensitively, first as given, then in the
    further forms passed by the caller (suffixes removed). Between the title
    and the bracket only a short subtitle without digits may stand, such as
    ". Roman" or ": novellalar", so that a series or container bracket later
    in the line is not read as the original title. A gap that closes a quoted
    title and continues with " in " leads to a container, not an original.
    A bracket glued to a word ("N[arahara]") is a completion, not a bracket.
    """
    lowered = text.casefold()
    for title in dict.fromkeys(t for t in titles if t):
        index = lowered.find(title.casefold())
        if index < 0:
            continue
        line_end = text.find("\n", index)
        rest = text[index + len(title) : line_end if line_end >= 0 else len(text)]
        m = re.match(r"([^\[\]]*?)(?<!\w)\[([^\[\]]*)\]", rest)
        if not m:
            return None
        gap = m.group(1)
        if len(gap) > _GAP_MAX or re.search(r"\d", gap) or _CONTAINER_GAP.search(gap):
            return None
        return {"titleFound": title, "gap": gap, "content": m.group(2).strip()}
    return None


# Search folding (S1.1)

_FOLD_LETTERS = str.maketrans(
    {"ß": "ss", "ı": "i", "ł": "l", "ø": "o", "đ": "d", "æ": "ae", "œ": "oe", "þ": "th"}
)
_UMLAUT_DIGRAPHS = (("ae", "a"), ("oe", "o"), ("ue", "u"))


def fold_search(text: str) -> str:
    """Search key: diacritics stripped, German umlauts folded, punctuation spaced.

    "Netrpělivost" and "Netrpelivost", "Müller" and "Mueller", "ʿĀṣifah" and
    "Asifah" fold alike. The digraph step applies to every word on both sides
    of the comparison, so it never hides a substring match. docs/lab/js/lab.js
    mirrors this function for the query; keep both in step.
    """
    text = unicodedata.normalize("NFKC", text or "").lower().translate(_FOLD_LETTERS)
    text = "".join(
        c
        for c in unicodedata.normalize("NFD", text)
        if not unicodedata.category(c).startswith("M")
        and unicodedata.category(c) not in ("Lm", "Sk")
        and c not in "'’‘`´"
    )
    for digraph, vowel in _UMLAUT_DIGRAPHS:
        text = text.replace(digraph, vowel)
    return " ".join("".join(c if c.isalnum() else " " for c in text).split())


# Relation 2: the compiler's "Translations" section

_SECTION_HEAD = re.compile(r"^\s*Translations\s*:\s*$", re.MULTILINE)
_LABEL_LINE = re.compile(r"^\s*([^:\n]{1,60}?)\s*:\s*(.*)$")


def parse_translations_section(text: str, language_words: frozenset[str]) -> dict:
    """Language lines of the "Translations:" section, as the compiler wrote them.

    A line "Language: text" opens a language; a bare "Language:" opens one
    whose text follows on the next lines; other lines continue the current
    language, and those shaped like "Label: text" are also reported as
    unrecognised so that a missing language name shows up. A bare label whose first word is no language name, such as
    "Secondary Literature:", ends the section. German lines are returned
    apart, because they list German reprints and belong to the German
    editions.
    """
    head = _SECTION_HEAD.search(text)
    if not head:
        return {"found": False, "languages": [], "german": [], "unrecognised": []}
    entries: list[dict] = []
    unrecognised: list[str] = []
    for line in text[head.end() :].split("\n"):
        if not line.strip():
            continue
        m = _LABEL_LINE.match(line)
        words = re.split(r"[\s/(]+", m.group(1).strip()) if m else []
        first = words[0].casefold() if words else ""
        if m and first in language_words:
            entries.append({"language": m.group(1).strip(), "text": m.group(2).strip()})
            continue
        if m and not m.group(2).strip():
            break
        if m:
            unrecognised.append(line.strip())
        if entries:
            joined = f"{entries[-1]['text']}\n{line.strip()}".strip()
            entries[-1]["text"] = joined
        else:
            break
    german = [e for e in entries if e["language"].casefold().startswith("german")]
    others = [e for e in entries if e not in german]
    return {
        "found": True,
        "languages": others,
        "german": german,
        "unrecognised": unrecognised,
    }


# Constants shared with the production frontend


def parse_zweig_author_types(constants_js: str) -> list[str]:
    """Rebuild ZWEIG_AUTHOR_TYPES from docs/js/constants.js.

    The constant is derived in JavaScript: the types of the "Works" group of
    CATEGORY_GROUPS plus 'collected-works', minus TITLE_AUTHOR_TYPES. The
    parse follows that derivation and fails loudly if the shape changes.
    """
    if "const ZWEIG_AUTHOR_TYPES" not in constants_js:
        raise ValueError("ZWEIG_AUTHOR_TYPES not found in constants.js")
    works = re.search(
        r"heading:\s*'Works',\s*types:\s*\[([^\]]*)\]", constants_js, re.DOTALL
    )
    title_author = re.search(
        r"const TITLE_AUTHOR_TYPES\s*=\s*\[([^\]]*)\]", constants_js
    )
    derivation = re.search(
        r"const ZWEIG_AUTHOR_TYPES\s*=\s*\[\s*\.\.\.CATEGORY_GROUPS\.find\("
        r"group => group\.heading === 'Works'\)\.types,\s*'collected-works',?\s*\]"
        r"\.filter\(type => !TITLE_AUTHOR_TYPES\.includes\(type\)\)",
        constants_js,
    )
    if not (works and title_author and derivation):
        raise ValueError("ZWEIG_AUTHOR_TYPES derivation changed shape in constants.js")
    excluded = set(re.findall(r"'([^']+)'", title_author.group(1)))
    types = re.findall(r"'([^']+)'", works.group(1)) + ["collected-works"]
    return [t for t in dict.fromkeys(types) if t not in excluded]
