"""Work grouping of the lab (relations 1 to 3 of "What a work is in this data").

Input is the list of namespace-0 records of `docs/data/klawiter.json`, the
redirect map, the publication side files and a few derived vocabularies; the
output is the content of `works.json` plus the per-page membership the page
files refer to. Nothing here reads files.

Decisions taken beyond the wording of knowledge/lab-frontend.md, each recorded
in `works.json` under `rules`:

- An anchor is a VIST page with the German pages of Zweig's own works that
  carry the same title key or that the VIST page links. German pages without a
  VIST page that share a title key form one anchor, as the VIST rule groups
  same-title pages; the anchor page is the lowest qualifying page id.
- A page may be an anchor member of more than one work, because the VIST rule
  rests on links and a collected volume can be linked by several VIST pages.
- Relation 1 counts German pages of Zweig's own works that link a VIST page
  inbound as their own kind, because the spec makes only outbound ones anchor
  members.
- Brackets of the excluded kinds are attributed to a work through a link,
  through one of several titles, or, for a year or an English note, through
  the title key of the bracket's first segment ("Der versiegelte Zug. Lenin,
  9. April 1917"); the rest are listed globally only.
- The union total counts pages of parts 1 and 3; anchor pages are reported
  separately.
"""

from __future__ import annotations

import unicodedata
from collections import defaultdict

from lab_rules import (
    classify_bracket,
    first_bracket_after_title,
    lead_key,
    normalise_title,
    parse_translations_section,
    several_title_parts,
    strip_bracket_note,
    strip_page_suffixes,
    title_key,
    variant_key,
)

ADAPTATION_TYPES = frozenset({"film", "dramatic-reading"})
EXCLUDED_CLASSES = ("year-or-number", "place", "english-gloss", "several-titles")
NOT_RECORDED = "language not recorded"


def resolver(entries: list[dict], redirects: dict[str, int]):
    """Resolve a see-also title to a page id, as stage 05 resolves link targets."""
    exact = {}
    loose = {}
    for entry in entries:
        exact.setdefault(entry["title"], entry["sourcePageId"])
        loose.setdefault(_loose(entry["title"]), entry["sourcePageId"])
    loose_redirects = {_loose(k): v for k, v in redirects.items()}

    def resolve(title: str) -> int | None:
        target = " ".join(title.split("|", 1)[0].split())
        if target in exact:
            return exact[target]
        if target in redirects:
            return redirects[target]
        key = _loose(target)
        return loose.get(key, loose_redirects.get(key))

    return resolve


def _loose(title: str) -> str:
    return normalise_title(unicodedata.normalize("NFKC", title))


def link_graph(entries: list[dict], resolve) -> tuple[dict, dict, list]:
    outbound: dict[int, set[int]] = defaultdict(set)
    inbound: dict[int, set[int]] = defaultdict(set)
    unresolved = []
    for entry in entries:
        pid = entry["sourcePageId"]
        for title in entry.get("seeAlso") or []:
            target = resolve(title)
            if target is None:
                unresolved.append({"pageId": pid, "title": title})
            elif target != pid:
                outbound[pid].add(target)
                inbound[target].add(pid)
    return outbound, inbound, unresolved


def page_brackets(
    entries: list[dict], places: frozenset[str], suffix_words: frozenset[str]
) -> dict[int, dict]:
    """Bracket after the page title, its class and title key, per page."""
    result = {}
    for entry in entries:
        text = entry.get("fullBibliographicEntry") or ""
        titles = [entry["title"], strip_page_suffixes(entry["title"], suffix_words)]
        found = first_bracket_after_title(text, titles)
        if found is None:
            continue
        kind = classify_bracket(found["content"], places)
        row = {"content": found["content"], "class": kind}
        if kind == "title":
            row["key"] = title_key(strip_bracket_note(found["content"]))
        elif kind in ("year-or-number", "english-gloss"):
            row["leadKey"] = lead_key(found["content"])
        elif kind == "several-titles":
            row["partKeys"] = [
                title_key(p) for p in several_title_parts(found["content"])
            ]
        result[entry["sourcePageId"]] = row
    return result


def build_anchors(
    pages: dict[int, dict],
    zweig_types: frozenset[str],
    outbound: dict,
    inbound: dict,
    brackets: dict,
    suffix_words: frozenset[str],
) -> list[dict]:
    german = {
        pid
        for pid, e in pages.items()
        if e["entryType"] in zweig_types and e.get("language") == "German"
    }
    key_of = {pid: title_key(pages[pid]["title"], suffix_words) for pid in german}
    by_key: dict[str, list[int]] = defaultdict(list)
    for pid in sorted(german):
        by_key[key_of[pid]].append(pid)

    anchors: dict[str, dict] = {}
    vist = sorted(pid for pid, e in pages.items() if "(VIST)" in e["title"])
    for pid in vist:
        key = title_key(pages[pid]["title"], suffix_words)
        anchor = anchors.setdefault(
            key, {"anchorPageId": pid, "key": key, "vist": True, "members": {}}
        )
        anchor["members"].setdefault(pid, "VIST page")
        for other in by_key.get(key, []):
            anchor["members"].setdefault(other, "same title")
        for other in sorted(outbound.get(pid, ())):
            if other in german:
                anchor["members"].setdefault(other, "linked by the VIST page")

    # A page linked by a VIST page joins that work's German editions and may
    # still anchor its own work, as "Amok. Novellen einer Leidenschaft" does.
    in_vist = {
        m
        for a in anchors.values()
        for m, reason in a["members"].items()
        if reason != "linked by the VIST page"
    }
    cited_keys = {b["key"] for b in brackets.values() if b["class"] == "title"}
    for key, pids in sorted(by_key.items()):
        if key in anchors:
            continue
        rest = [p for p in pids if p not in in_vist]
        qualifying = [
            p for p in rest if (inbound.get(p, set()) - {p}) or key in cited_keys
        ]
        if not qualifying:
            continue
        members = {}
        for p in rest:
            reasons = []
            if inbound.get(p, set()) - {p}:
                reasons.append("linked by other pages")
            if key in cited_keys:
                reasons.append("title cited in brackets")
            members[p] = ", ".join(reasons) or "same title"
        anchors[key] = {
            "anchorPageId": min(qualifying),
            "key": key,
            "vist": False,
            "members": members,
        }
    return sorted(anchors.values(), key=lambda a: a["anchorPageId"])


def _row(pid: int, pages: dict, pubs: dict) -> dict:
    entry = pages[pid]
    row = {
        "pageId": pid,
        "title": entry["title"],
        "entryType": entry["entryType"],
        "language": entry.get("language"),
    }
    publications = pubs.get(pid)
    if publications:
        row["publications"] = [
            {
                "id": p["id"],
                "year": p.get("year"),
                "imprint": p.get("imprint"),
                "language": p.get("language"),
            }
            for p in publications
        ]
    else:
        row["publications"] = None
        row["year"] = entry.get("year")
        row["allYears"] = entry.get("allYears") or (
            [entry["year"]] if entry.get("year") else []
        )
    return row


def _gap_groups(rows: list[dict]) -> dict:
    """Publications without language and without year, each row listed.

    A page without a publication breakdown counts as one row with its
    page-level values and `publicationId: null`.
    """
    no_language, no_year = [], []
    for row in rows:
        units = row["publications"] or [
            {"id": None, "year": row.get("year"), "language": row["language"]}
        ]
        for unit in units:
            ref = {"pageId": row["pageId"], "publicationId": unit["id"]}
            if not unit.get("language"):
                no_language.append(ref)
            if not unit.get("year"):
                no_year.append(ref)
    return {
        "unit": "publications; a page without breakdown counts as one row",
        "languageNotRecorded": {"count": len(no_language), "rows": no_language},
        "yearNotRecorded": {"count": len(no_year), "rows": no_year},
    }


def _count(rows: list[dict]) -> dict:
    return {
        "pages": len(rows),
        "publications": sum(len(r["publications"] or []) for r in rows),
        "pagesWithoutBreakdown": sum(1 for r in rows if not r["publications"]),
    }


def _sort_rows(rows: list[dict]) -> list[dict]:
    def first_year(row: dict) -> int:
        years = [p["year"] for p in row["publications"] or [] if p.get("year")]
        years += row.get("allYears") or []
        return min(years) if years else 9999

    return sorted(rows, key=lambda r: (first_year(r), r["pageId"]))


def _relation1(anchor_ids, pages, pubs, outbound, inbound, zweig_types) -> dict:
    linked: dict[int, set[str]] = defaultdict(set)
    for a in anchor_ids:
        for p in outbound.get(a, ()):
            linked[p].add("named in the anchor's see-also")
        for p in inbound.get(a, ()):
            linked[p].add("names the anchor in its see-also")
    for a in anchor_ids:
        linked.pop(a, None)
    linked = {p: d for p, d in linked.items() if p in pages}

    translations: dict[str, list] = defaultdict(list)
    german, adaptations, other = [], [], []
    for pid in sorted(linked):
        entry = pages[pid]
        row = _row(pid, pages, pubs) | {"direction": sorted(linked[pid])}
        if entry["entryType"] in zweig_types:
            if entry.get("language") == "German":
                german.append(row)
            else:
                translations[entry.get("language") or NOT_RECORDED].append(row)
        elif entry["entryType"] in ADAPTATION_TYPES:
            adaptations.append(row)
        else:
            other.append(row)
    all_rows = (
        german + adaptations + other + [r for v in translations.values() for r in v]
    )
    return {
        "label": "linked by the compiler",
        "count": _count(all_rows),
        "translationsByLanguage": {
            lang: {"count": _count(rows), "rows": _sort_rows(rows)}
            for lang, rows in sorted(translations.items())
        },
        "germanPagesLinkingTheAnchor": {
            "count": _count(german),
            "rows": _sort_rows(german),
        },
        "adaptationsAndReadings": {
            "count": _count(adaptations),
            "rows": _sort_rows(adaptations),
        },
        "secondaryLiteratureAndOther": {
            "count": _count(other),
            "rows": _sort_rows(other),
        },
        "gapGroups": _gap_groups(all_rows),
        "pageIds": sorted(linked),
    }


def _relation2(anchor_ids, pages, language_words) -> dict:
    sources = []
    unrecognised = []
    for pid in sorted(anchor_ids):
        parsed = parse_translations_section(
            pages[pid].get("fullBibliographicEntry") or "", language_words
        )
        if not parsed["found"]:
            continue
        sources.append(
            {
                "pageId": pid,
                "languages": parsed["languages"],
                "germanReprints": parsed["german"],
            }
        )
        unrecognised += [
            {"pageId": pid, "line": line} for line in parsed.get("unrecognised", [])
        ]
    return {
        "label": "listed by the compiler as text",
        "languageCount": len({e["language"] for s in sources for e in s["languages"]}),
        "sources": sources,
        "unrecognisedLabelLines": unrecognised,
    }


def _relation3(work_key, anchor_ids, rel1_ids, pages, pubs, brackets) -> dict:
    hits, variants = [], []
    excluded: dict[str, list] = {k: [] for k in EXCLUDED_CLASSES}
    for pid in sorted(brackets):
        if pid in anchor_ids or pid not in pages:
            continue
        b = brackets[pid]
        if b["class"] == "title":
            if b["key"] == work_key:
                hits.append(_row(pid, pages, pubs) | {"bracket": b["content"]})
            elif variant_key(b["key"]) == variant_key(work_key):
                variants.append(_row(pid, pages, pubs) | {"bracket": b["content"]})
        elif b["class"] == "several-titles" and work_key in b["partKeys"]:
            excluded["several-titles"].append({"pageId": pid, "bracket": b["content"]})
        elif b["class"] in excluded and (
            pid in rel1_ids or b.get("leadKey") == work_key
        ):
            excluded[b["class"]].append({"pageId": pid, "bracket": b["content"]})
    for row in hits + variants:
        row["alsoLinkedByCompiler"] = row["pageId"] in rel1_ids
    by_type: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for row in hits:
        by_type[row["entryType"]][row["language"] or NOT_RECORDED].append(row)
    return {
        "label": "cites the original title in brackets, found by a lab rule, not reviewed",
        "count": _count(hits),
        "alsoLinkedCount": sum(1 for r in hits if r["alsoLinkedByCompiler"]),
        "byEntryType": {
            etype: {
                lang: {"count": _count(rows), "rows": _sort_rows(rows)}
                for lang, rows in sorted(langs.items())
            }
            for etype, langs in sorted(by_type.items())
        },
        "gapGroups": _gap_groups(hits),
        "excludedBrackets": {
            k: {"count": len(v), "rows": v} for k, v in excluded.items()
        },
        "possiblySameTitle": {
            "note": "variant form of the title, possibly the same title, never merged",
            "count": _count(variants),
            "rows": _sort_rows(variants),
        },
        "pageIds": [r["pageId"] for r in hits],
    }


def build_works(
    pages: dict[int, dict],
    pubs: dict[int, list],
    redirects: dict[str, int],
    zweig_types: frozenset[str],
    places: frozenset[str],
    suffix_words: frozenset[str],
    language_words: frozenset[str],
) -> dict:
    entries = list(pages.values())
    resolve = resolver(entries, redirects)
    outbound, inbound, unresolved = link_graph(entries, resolve)
    brackets = page_brackets(entries, places, suffix_words)
    anchors = build_anchors(
        pages, zweig_types, outbound, inbound, brackets, suffix_words
    )

    works = []
    for anchor in anchors:
        anchor_ids = set(anchor["members"])
        rel1 = _relation1(anchor_ids, pages, pubs, outbound, inbound, zweig_types)
        rel1_ids = set(rel1["pageIds"])
        rel3 = _relation3(anchor["key"], anchor_ids, rel1_ids, pages, pubs, brackets)
        union = rel1_ids | set(rel3["pageIds"])
        anchor_pubs = sum(len(pubs.get(p) or []) for p in anchor_ids)
        anchor_title = strip_page_suffixes(
            pages[anchor["anchorPageId"]]["title"], suffix_words
        )
        works.append(
            {
                "workId": f"lab-work/{anchor['anchorPageId']}",
                "idNote": "lab-derived identifier from the anchor page id",
                "title": anchor_title,
                "titleKey": anchor["key"],
                "anchor": {
                    "pageId": anchor["anchorPageId"],
                    "vist": anchor["vist"],
                    "germanWorkPage": any(
                        pages[p].get("language") == "German" for p in anchor_ids
                    ),
                    "members": [
                        {"pageId": p, "title": pages[p]["title"], "reason": r}
                        for p, r in sorted(anchor["members"].items())
                    ],
                    "publicationsOnAnchorPages": anchor_pubs,
                    "anchorPagesWithoutBreakdown": sorted(
                        p for p in anchor_ids if not pubs.get(p)
                    ),
                },
                "linkedByCompiler": rel1,
                "listedAsText": _relation2(anchor_ids, pages, language_words),
                "citingTitleInBrackets": rel3,
                "union": {
                    "unit": "pages in parts 1 and 3, counted once; anchor pages apart",
                    "count": len(union),
                    "inBothParts": sorted(rel1_ids & set(rel3["pageIds"])),
                },
                "scopeNote": (
                    "Appearances inside anthologies and collected volumes are not "
                    "covered by this view."
                ),
            }
        )

    excluded_global: dict[str, list[int]] = defaultdict(list)
    for pid, b in sorted(brackets.items()):
        excluded_global[b["class"]].append(pid)
    return {
        "works": works,
        "brackets": brackets,
        "bracketClasses": {
            k: {"count": len(v), "pageIds": v}
            for k, v in sorted(excluded_global.items())
        },
        "unresolvedSeeAlso": unresolved,
        "outbound": outbound,
    }
