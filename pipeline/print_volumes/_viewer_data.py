"""Viewer data of the print strand: the wiki concordance projection and the index snippet.

The card workbench compares a print object with the wiki. concordance()
projects the p07 claims and the p08 field conflicts onto the objects and
records they are about, together with the wiki pages (docs/data/klawiter.json)
and the publications they name (docs/data/publications/), and writes
data/print/derived/lab/wiki_concordance.json, which p12 copies beside the
viewer. Every link keeps the state of what it projects: a p07 claim stays
"proposed", with its route (alignment, field-match, title-year) and claim id,
and a p08 case stays a "conflict" with its fields. The projection matches
nothing itself and never raises a state; "matched" or "confirmed" can only
come from a review decision. The file holds print values (p08) and stays
local (rights unresolved).

snippet() gives the index a line that tells objects with the same title
apart, quoted from the object's own passage.
"""

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from _common import DERIVED_DIR, PROJECT_ROOT, REPORT_DIR, VOLUMES
from _schema import object_values

CLAIMS = DERIVED_DIR / "claims" / "concordance.jsonl"
CASES = REPORT_DIR / "p08_field_check_cases.jsonl"
KLAWITER = PROJECT_ROOT / "docs" / "data" / "klawiter.json"
PUBLICATIONS = PROJECT_ROOT / "docs" / "data" / "publications"
RECORDS = DERIVED_DIR / "records"
CONCORDANCE = DERIVED_DIR / "lab" / "wiki_concordance.json"
# Files the viewer reads that p12 writes into data/print/derived/viewer/; the
# review server serves these names from there only, never from the versioned
# viewer folder.
VIEWER_DATA_FILES = ("index.json", "vocab.json", CONCORDANCE.name)

# Display caps per object: the best field matches, the first title-year blocks.
SAME_SHOWN = 3
CAND_SHOWN = 3
ROUTES = {
    "textAlignedWith": ("align", "alignment", "shingle-alignment"),
    "samePublicationAs": ("same", "field-match", "title-year-field"),
    "candidateFor": ("cand", "title-year", "title-year"),
}
URI_PAGE = re.compile(r"klawiter:(?:entry/(\d+)|publication/(\d+)-)")

SNIPPET_MAX = 140
# The values that tell editions of one title apart, in the order the entry
# prints them: subtitle, credit (role words and names), imprint, extent.
DISAMBIGUATION = re.compile(
    r"^(?:subtitle"
    r"|persons\[\d+\]\.(?:name|roles\[\d+\])"
    r"|imprints\[\d+\]\.(?:place|publisher|year)"
    r"|extent\.raw)$"
)
# Between two quoted values a short run of spaces and punctuation stays as
# printed ("Ed./Aftw. Knut Beck", "202/(2)p. 1984"); a longer gap is elided.
KEEP_GAP = re.compile(r"^[\s.,;:/]{0,3}$")
ELISION = " · "


def _page(uri: str | None) -> int | None:
    m = URI_PAGE.search(uri or "")
    return int(m.group(1) or m.group(2)) if m else None


def _year(obj: dict) -> str | None:
    """The object's first imprint year, own or inherited, else an edition note year."""
    imprints = obj.get("imprints") or (obj.get("inherited") or {}).get("imprints") or []
    for imprint in imprints:
        if imprint.get("year"):
            return str(imprint["year"]["value"])
    for note in obj.get("edition_notes") or []:
        if note.get("years"):
            return str(note["years"][0]["value"])
    return None


def object_meta(records) -> tuple[dict[str, dict], dict[str, str]]:
    """Per object id what the projection needs; per record id its text hash."""
    meta, hashes = {}, {}
    for rec in records:
        hashes[rec["id"]] = rec["sha256"]
        for obj in rec.get("objects", []):
            types = [t["value"] for t in obj.get("types", []) if "value" in t]
            meta[obj["id"]] = {
                "entry": rec["id"],
                # A collection heading without address stands for its items,
                # which carry their own links.
                "skip": not obj.get("address")
                and (rec.get("kind") == "header" or "collection" in types),
                "year": _year(obj),
            }
    return meta, hashes


def wiki_pages(klawiter: dict) -> dict[int, dict]:
    pages = {}
    for e in klawiter.get("entries", []):
        if e.get("pageNamespace", 0) != 0 or e.get("sourcePageId") is None:
            continue
        text = re.sub(r"\s+", " ", (e.get("fullBibliographicEntry") or "").strip())
        pages[int(e["sourcePageId"])] = {
            "title": (e.get("title") or "")[:160],
            "type": e.get("entryType") or "",
            "category": e.get("mainCategory") or (e.get("categories") or [""])[0],
            "year": e.get("year")
            or (e.get("publicationYears") or [None])[0]
            or (e.get("allYears") or [None])[0],
            "place": e.get("location") or (e.get("publicationPlaces") or [None])[0],
            "publisher": e.get("publisher"),
            "pubCount": e.get("publicationCount") or 0,
            "snippet": text[:320],
        }
    return pages


def publication_infos(files) -> dict[str, dict]:
    """Per publication id its wiki fields; files are (stem, parsed json) pairs."""
    pubs = {}
    for stem, data in files:
        page = data.get("sourcePageId") or (int(stem) if stem.isdigit() else None)
        for pub in data.get("publications", []):
            if not pub.get("id"):
                continue
            extent = pub.get("extent")
            if isinstance(extent, dict):
                extent = extent.get("raw") or str(extent.get("pages") or "") or None
            translators = [
                c.get("name")
                for c in pub.get("credits") or []
                if c.get("role") == "translator" and c.get("name")
            ]
            pubs[pub["id"]] = {
                "id": pub["id"],
                "page": page or _page(pub["id"]),
                "title": (pub.get("title") or "")[:140],
                "place": (pub.get("places") or [None])[0],
                "publisher": pub.get("publisher"),
                "year": pub.get("year"),
                "extent": None if extent is None else str(extent),
                "translator": translators[0] if translators else None,
            }
    return pubs


def project(
    claims,
    cases,
    meta: dict[str, dict],
    hashes: dict[str, str],
    pages: dict[int, dict],
    pubs: dict[str, dict],
) -> dict:
    """The concordance file's links, pages, publications, wiki-only pages and counts."""
    links: dict[str, dict] = {}
    pages_used: set[int] = set()
    pubs_used: set[str] = set()
    counts: Counter = Counter()
    for c in claims:
        subject, target = c["subject"], c["object"]
        if (meta.get(subject) or {}).get("skip"):
            counts["claims_skipped_collection"] += 1
            continue
        key, route, method = ROUTES[c["predicate"]]
        state = c["state"]
        counts[f"{route}:{state}"] += 1
        evidence = c.get("evidence") or {}
        page = evidence.get("wiki_page") or _page(target)
        if page:
            pages_used.add(int(page))
        if target.startswith("klawiter:publication/"):
            pubs_used.add(target)
        item = {"claim": c["id"], "state": state, "route": route, "page": page}
        if key == "align":
            item.update(
                score=evidence.get("score", 1.0), firstSeen=evidence.get("first_seen")
            )
        else:
            item["target"] = target
            if key == "same":
                item["secondField"] = evidence.get("second_field", [])
        item["method"] = method
        # A claim read from a record text that has changed since stays listed,
        # marked, until p07 runs again.
        record = (evidence.get("print") or {}).get("record")
        sha = (evidence.get("print") or {}).get("sha256")
        if record and sha and hashes.get(record) not in (None, sha):
            item["stale"] = True
            counts["claims_stale"] += 1
        links.setdefault(subject, {}).setdefault(key, []).append(item)

    for subject, info in links.items():
        totals = {}
        if "same" in info:
            year = (meta.get(subject) or {}).get("year")
            # Same year first, then more agreeing second fields; stable on the
            # claim order of p07 beyond that.
            info["same"].sort(
                key=lambda x: (
                    0
                    if x["target"] in pubs
                    and str(pubs[x["target"]].get("year")) == year
                    else 1,
                    -len(x.get("secondField") or []),
                )
            )
            if len(info["same"]) > SAME_SHOWN:
                totals["same"] = len(info["same"])
                info["same"] = info["same"][:SAME_SHOWN]
        if len(info.get("cand", [])) > CAND_SHOWN:
            totals["cand"] = len(info["cand"])
            info["cand"] = info["cand"][:CAND_SHOWN]
        if totals:
            info["totals"] = totals

    for row in cases:
        if not (row.get("differ") and row.get("print") and row.get("wiki")):
            continue
        target = row["wiki"]
        page = _page(target)
        if page:
            pages_used.add(page)
        if target.startswith("klawiter:publication/"):
            pubs_used.add(target)
        counts["field-check:conflict"] += 1
        links.setdefault(row["print"], {})["diff"] = {
            "state": "conflict",
            "route": "field-check",
            "layer": row.get("layer"),
            "wiki": target,
            "page": page,
            "differ": row["differ"],
            "agree": row.get("agree") or [],
            "printFields": row.get("printFields") or {},
            "wikiFields": row.get("wikiFields") or {},
        }

    counts["subjects"] = len(links)
    return {
        "links": links,
        "pages": {str(p): pages[p] for p in sorted(pages)},
        "pubs": {k: pubs[k] for k in sorted(pubs_used) if k in pubs},
        "wikiOnlyPages": sorted(set(pages) - pages_used),
        "counts": dict(sorted(counts.items())),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _jsonl(path: Path):
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def concordance() -> dict:
    """Write the concordance file from the current inputs; return its counts."""
    for path in (CLAIMS, KLAWITER, PUBLICATIONS):
        if not path.exists():
            sys.exit(
                f"FEHLER: {path} missing; run p07 and the production pipeline first"
            )
    record_files = [RECORDS / f"entries-{v}.jsonl" for v in VOLUMES]
    meta, hashes = object_meta(rec for p in record_files for rec in _jsonl(p))
    pub_files = sorted(PUBLICATIONS.glob("*.json"))
    pubs = publication_infos(
        (p.stem, json.loads(p.read_text(encoding="utf-8"))) for p in pub_files
    )
    combined = hashlib.sha256(
        "".join(f"{p.name}\t{_sha256(p)}\n" for p in pub_files).encode("utf-8")
    ).hexdigest()
    source = [
        {"path": _rel(p), "sha256": _sha256(p)}
        for p in (CLAIMS, *([CASES] if CASES.exists() else []), KLAWITER, *record_files)
    ]
    source.append(
        {
            "path": _rel(PUBLICATIONS) + "/*.json",
            "files": len(pub_files),
            "sha256": combined,
            "hashOf": "one line per file, sorted by name: name TAB sha256 LF",
        }
    )
    data = project(
        _jsonl(CLAIMS),
        _jsonl(CASES) if CASES.exists() else (),
        meta,
        hashes,
        wiki_pages(json.loads(KLAWITER.read_text(encoding="utf-8"))),
        pubs,
    )
    out = {
        "about": "Wiki concordance of the print objects for the local card workbench; "
        "holds print values, local only (rights unresolved). links: per print object "
        "or record id the p07 claims (align: alignment, same: field-match, cand: "
        "title-year) with claim id and state, which p07 sets to proposed and this "
        "projection never raises, and the p08 field conflict (diff, state conflict). "
        f"same shows the best {SAME_SHOWN} by same year and agreeing second fields, "
        f"cand the first {CAND_SHOWN}; totals gives the full count where cut. stale "
        "marks a claim whose record text changed since p07. pages: the wiki's main "
        "namespace pages; pubs: the publications a link names; wikiOnlyPages: pages "
        "no link names. Nothing here is matched or confirmed.",
        "source": source,
        **data,
    }
    CONCORDANCE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONCORDANCE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    tmp.replace(CONCORDANCE)
    return data["counts"]


def _cut(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= SNIPPET_MAX:
        return text
    head = text[: SNIPPET_MAX - 1]
    if " " in head:
        head = head[: head.rindex(" ")]
    # A cut right after an elision drops the elision mark too.
    return head.rstrip(" .,;:·") + "…"


def _own_span(value: dict | None, start: int, length: int) -> tuple[int, int] | None:
    """The value's span relative to the object's text, if the passage is the object's own."""
    if not value or value.get("from") or "span" not in value:
        return None
    a, b = value["span"][0] - start, value["span"][1] - start
    return (a, b) if 0 <= a < b <= length else None


def snippet(obj: dict, titled: bool) -> str:
    """A line from the object's own passage that tells it apart from its namesakes.

    Titled objects: the subtitle, credit, imprint and extent passages in
    printed order, short gaps kept and longer ones elided; without such values
    the text after the title. Untitled objects: the start of their text, as
    the viewer shows it in place of a title.
    """
    text, start = obj["text"], obj["span"][0]
    if not titled:
        return _cut(text)
    spans = sorted(
        span
        for path, v in object_values(obj)
        if DISAMBIGUATION.match(path) and (span := _own_span(v, start, len(text)))
    )
    if not spans:
        label = _own_span(obj.get("term") or obj.get("title"), start, len(text))
        return _cut(text[label[1] if label else 0 :].lstrip(" .,;:"))
    merged = [list(spans[0])]
    for a, b in spans[1:]:
        if a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out = text[merged[0][0] : merged[0][1]]
    for (_, prev_end), (a, b) in zip(merged, merged[1:]):
        gap = text[prev_end:a]
        out += (gap if KEEP_GAP.match(gap) else ELISION) + text[a:b]
    return _cut(out)
