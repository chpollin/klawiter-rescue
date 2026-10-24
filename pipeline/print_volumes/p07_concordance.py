"""p07: concordance of print and wiki on two routes, with a deterministic test of the field route.

The overlap experiments (knowledge/print-volumes.md, Print and wiki) found
that Addendum II reached the early wiki nearly verbatim, that main-volume
entries were pasted verbatim for minutes before rewriting, and that otherwise
the wiki text is re-keyed. The concordance therefore takes two routes:

- alignment: the share of a print entry's distinctive word 5-grams found in
  any revision of one wiki page (p04 revisions). Shingles that occur in more
  than MAX_SHINGLE_UNITS print entries are not distinctive and are dropped.
  An entry with score >= ALIGNED is aligned with that page.
- field: a print object's title words (up to TITLE_WORDS; a single word
  shorter than MIN_SINGLE_WORD letters reads on into its subtitle, or else
  reaches only a page titled exactly that word) and year occur in one line of
  a page's latest revision; a second field (publisher, place, translator
  surname, own or inherited, or extent) agreeing in the window around that
  line makes it a field match, otherwise it stays a title-year block. The
  second field needs two agreeing tokens or one rare in the wiki lines
  (_rare_limit), so a frequent place or publisher alone does not carry it.
  Lines include contents lines, which the wiki publication layer does not
  hold as publications. A collection header without address is not matched:
  it stands for its volumes, which carry their own matches.

The deterministic test: entries aligned with score >= SILVER at some revision
form silver pairs (print entry, wiki page) whose identity rests on near-verbatim
text, not on a judgement. The field route is scored on them against the
page's latest text, per volume. For Addendum II that measures matching where
the text survived; for the main volume and Addendum I the latest text is
mostly re-keyed, so it measures exactly what the field route must survive.
Recall on silver pairs is the method's loss; the overlap itself is measured
separately. Silver pairs are only as good as the alignment threshold and are
no human gold.

All pairs are claims with state "proposed". The lab view file maps wiki
pages to their print matches for local display; it holds print text and
stays under data/print (rights unresolved).

Output: data/print/derived/claims/concordance.jsonl,
data/print/derived/lab/print-links.json and
data/print/derived/reports/p07_concordance.json.

Usage: python -m uv run python pipeline/print_volumes/p07_concordance.py
"""

import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict

from _common import DERIVED_DIR, PROJECT_ROOT, VOLUMES, write_report
from _fields import summary
from _heldout import is_held_out
from _lines import START_NUMBER

RECORDS = DERIVED_DIR / "records"
REVISIONS = DERIVED_DIR / "wiki" / "revisions.jsonl"
CLAIMS = DERIVED_DIR / "claims"
LAB = DERIVED_DIR / "lab"
PUBLICATIONS = PROJECT_ROOT / "docs" / "data" / "publications"
SHINGLE = 5
MAX_SHINGLE_UNITS = 20
MIN_SHINGLES = 8
ALIGNED = 0.8
SILVER = 0.9
TITLE_WORDS = 4
MIN_SINGLE_WORD = 8
YEAR_WINDOW = 2
# Extent ("396p.", "xvi/368p.") and page ranges ("pp. (1)-3", "p. 79").
EXTENT = re.compile(
    r"\b(\d+(?:/\(?\d+\)?)?)\s?p\.|\bpp?\.\s?(\(?\d+\)?(?:\s?-\s?\(?\d+\)?)?)"
)
MIN_PAGE_DIGITS = 2
MIN_FIELD_TOKEN = 4
# Upper bound on the chance that a lone second-field token stands in the
# window by accident (_rare_limit); fixed before measuring, not tuned.
CHANCE = 0.01
# Publisher words that carry no identity of their own.
GENERIC = frozenset(
    "verlag verlags verlagsanstalt edition editions editeur editions editorial "
    "editora edizioni ediciones editura editrice press publishing publishers "
    "publisher books book company librairie libreria livraria buchhandlung "
    "gesellschaft wydawnictwo kiadas nakladatelstvi izdatelstvo".split()
)
ALIGN = {"class": "editorial", "method": "rule", "rule": "p07.shingle-alignment"}
FIELD = {"class": "editorial", "method": "rule", "rule": "p07.title-year-field"}


def _tokens(text: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in plain if not unicodedata.combining(c)).lower()
    return re.findall(r"[0-9a-z]+", plain)


def _shingles(tokens: list[str]) -> set[str]:
    return {" ".join(tokens[i : i + SHINGLE]) for i in range(len(tokens) - SHINGLE + 1)}


def _claim_id(*parts: str) -> str:
    return "claim:" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _load_entries() -> list[dict]:
    entries = []
    for volume in VOLUMES:
        path = RECORDS / f"entries-{volume}.jsonl"
        if not path.exists():
            sys.exit(f"FEHLER: {path} missing; run p03_records.py first")
        with path.open(encoding="utf-8") as source:
            entries.extend(
                record
                for record in map(json.loads, source)
                if record["kind"] == "entry"
            )
    return entries


def _print_index(entries: list[dict]) -> tuple[dict[str, list[int]], dict[int, int]]:
    """Distinctive shingle -> entry indexes, and each entry's distinctive count."""
    index: dict[str, list[int]] = defaultdict(list)
    for n, entry in enumerate(entries):
        body = START_NUMBER.sub("", entry["text"], count=1)
        for shingle in _shingles(_tokens(body)):
            index[shingle].append(n)
    index = {s: ns for s, ns in index.items() if len(ns) <= MAX_SHINGLE_UNITS}
    sizes: Counter = Counter()
    for ns in index.values():
        sizes.update(ns)
    return index, {n: c for n, c in sizes.items() if c >= MIN_SHINGLES}


def _align(
    index: dict[str, list[int]], sizes: dict[int, int]
) -> tuple[dict[int, dict], dict[int, list[list[str]]], dict[int, str]]:
    """Best page per entry by shingle share over all revisions; latest page lines."""
    matched: dict[tuple[int, int], set[str]] = defaultdict(set)
    first_seen: dict[tuple[int, int], str] = {}
    latest_lines: dict[int, list[list[str]]] = {}
    latest_raw: dict[int, list[str]] = {}
    latest_offsets: dict[int, list[int]] = {}
    latest_text: dict[int, str] = {}
    titles: dict[int, str] = {}
    with REVISIONS.open(encoding="utf-8") as source:
        for row in map(json.loads, source):
            page = row["page"]
            titles[page] = row["title"]
            tokens = _tokens(row["text"])
            for shingle in _shingles(tokens) & index.keys():
                for n in index[shingle]:
                    if n not in sizes:
                        continue
                    key = (n, page)
                    if shingle not in matched[key]:
                        matched[key].add(shingle)
                        first_seen.setdefault(key, row["timestamp"])
            if row["latest"]:
                raw, offsets, pos = [], [], 0
                for ln in row["text"].splitlines(keepends=True):
                    if ln.strip():
                        raw.append(ln.rstrip("\r\n"))
                        offsets.append(pos)
                    pos += len(ln)
                latest_raw[page] = raw
                latest_offsets[page] = offsets
                latest_text[page] = row["text"]
                latest_lines[page] = [_tokens(ln) for ln in raw]
    best: dict[int, dict] = {}
    for (n, page), shingles in matched.items():
        score = len(shingles) / sizes[n]
        if n not in best or score > best[n]["score"]:
            best[n] = {
                "page": page,
                "score": round(score, 3),
                "first_seen": first_seen[(n, page)],
            }
    return (
        best,
        latest_lines,
        {
            "titles": titles,
            "raw": latest_raw,
            "offsets": latest_offsets,
            "text": latest_text,
        },
    )


def _publication_slices(pages: set[int], texts: dict[int, str]) -> tuple[dict, Counter]:
    """Publication slices per page from the published frontend layer, kept only
    where the slice of the latest revision hashes to the published slice. A
    mismatch means the two readings of the page differ, so no line is mapped."""
    slices: dict[int, list[tuple[int, int, str]]] = {}
    checked: Counter = Counter()
    for page in sorted(pages):
        path = PUBLICATIONS / f"{page}.json"
        if not path.exists():
            continue
        text = texts[page]
        kept = []
        for pub in json.loads(path.read_text(encoding="utf-8"))["publications"]:
            cut = pub["sourceSlice"]
            digest = hashlib.sha256(
                text[cut["start"] : cut["end"]].encode("utf-8")
            ).hexdigest()
            ok = digest == cut["sha256"]
            checked["verified" if ok else "mismatch"] += 1
            if ok:
                kept.append((cut["start"], cut["end"], pub["id"]))
        slices[page] = kept
    return slices, checked


def _publication_at(slices: dict, offsets: dict, page: int, line: int) -> str | None:
    offset = offsets[page][line]
    for start, end, pub_id in slices.get(page, ()):
        if start <= offset < end:
            return pub_id
    return None


def _short_title(title: str) -> str | None:
    """The single word of a title too short to block lines on its own."""
    words = _tokens(title)[:TITLE_WORDS]
    if len(words) == 1 and len(words[0]) < MIN_SINGLE_WORD:
        return words[0]
    return None


def _title_key(title: str, subtitle: str = "") -> list[str]:
    """Title words for the line route; a short single word reads on into the
    subtitle ("Angst. Novelle"), and without one it has no line key."""
    if _short_title(title):
        extra = _tokens(subtitle)
        return (_tokens(title) + extra)[:TITLE_WORDS] if extra else []
    return _tokens(title)[:TITLE_WORDS]


def _subtitle(obj: dict) -> str:
    """The subtitle of whichever title summary() reads; an inherited work
    heading carries none."""
    if obj.get("title"):
        return (obj.get("subtitle") or {}).get("value", "")
    if (obj.get("inherited") or {}).get("title"):
        return ""
    host = (obj.get("hosts") or [{}])[0]
    return (host.get("subtitle") or {}).get("value", "") if host.get("title") else ""


def _stands_for_items(obj: dict) -> bool:
    """A collection header without address names the series of the volumes
    after it, which carry their own matches; a wiki line naming the series
    states no identity with the header."""
    types = {t.get("value") for t in obj.get("types", [])}
    return not obj.get("address") and "collection" in types


def _field_tokens(fields: dict, text: str) -> set[str]:
    """Second-field tokens: imprint and translator words, and the numbers of
    extent and page ranges ("396p.", "pp. 300-324"), which periodical and
    contribution entries carry instead of an imprint."""
    texts = [fields.get("publisher", ""), fields.get("place", "")]
    surname = _tokens(fields.get("translator") or "")[-1:]
    texts.extend(surname)
    texts.append(fields.get("inherited_imprint", ""))
    found = set()
    for value in texts:
        for token in _tokens(value or ""):
            if len(token) >= MIN_FIELD_TOKEN and token not in GENERIC:
                if not token.isdigit():
                    found.add(token)
    for groups in EXTENT.findall(text):
        numbers = re.findall(r"\d+", " ".join(groups))
        found.update(n for n in numbers if len(n) >= MIN_PAGE_DIGITS)
    return found


def _line_index(latest_lines: dict[int, list[list[str]]]) -> dict[str, set]:
    index: dict[str, set] = defaultdict(set)
    for page, lines in latest_lines.items():
        for i, tokens in enumerate(lines):
            for token in set(tokens):
                index[token].add((page, i))
    return index


def _field_matches(
    obj: dict,
    latest_lines: dict[int, list[list[str]]],
    index: dict[str, set],
    title_pages: dict[str, set],
    page_titles: dict[int, str],
    rare_limit: int,
) -> list[dict]:
    """Lines holding the title words with the year within YEAR_WINDOW lines; on a
    page whose own title is or holds the title words, any line holding the year.

    A short single-word title ("Angst") is too common for lines on its own; it
    blocks lines together with its subtitle, and pages whose title is exactly
    that word.
    """
    fields = summary(obj)
    # An edition line has no title of its own; it reads the work heading's.
    title = fields["title"]
    words = _title_key(title, _subtitle(obj))
    short = _short_title(title)
    year = fields.get("year")
    if not year:
        return []
    year_token = str(year)
    year_lines = index.get(year_token, set())
    in_lines: set = set()
    if words:
        phrase = " " + " ".join(words) + " "
        candidates = set.intersection(*(index.get(w, set()) for w in words))
        for page, i in candidates:
            lines = latest_lines[page]
            if phrase not in " " + " ".join(lines[i]) + " ":
                continue
            window = range(
                max(0, i - YEAR_WINDOW), min(len(lines), i + YEAR_WINDOW + 1)
            )
            near = [j for j in window if year_token in lines[j]]
            if near:
                in_lines.add((page, min(near, key=lambda j: abs(j - i))))
    if short:
        pages = {p for p in title_pages.get(short, set()) if page_titles[p] == short}
        page_phrase = " " + short + " "
    elif words:
        pages = set.intersection(*(title_pages.get(w, set()) for w in words))
        page_phrase = phrase
    else:
        return []
    in_title = {
        (page, i)
        for page, i in year_lines
        if page in pages and page_phrase in " " + page_titles[page] + " "
    }
    extra = _field_tokens(fields, obj["text"])
    found = []
    for page, i in sorted(in_lines | in_title):
        lines = latest_lines[page]
        window = lines[max(0, i - YEAR_WINDOW) : i + YEAR_WINDOW + 1]
        agreeing = sorted(extra & {t for line in window for t in line})
        found.append(
            {
                "page": page,
                "line": i,
                "second_field": agreeing,
                "kind": "field"
                if _second_field_agrees(agreeing, index, rare_limit)
                else "title-year",
            }
        )
    return found


def _rare_limit(latest_lines: dict[int, list[list[str]]]) -> int:
    """Most wiki lines a token may stand in and still count alone as a second
    field: its chance presence in a window of 2 * YEAR_WINDOW + 1 lines stays
    below CHANCE, if lines held it at random."""
    lines = sum(len(page) for page in latest_lines.values())
    return int(lines * CHANCE / (2 * YEAR_WINDOW + 1))


def _second_field_agrees(
    agreeing: list[str], index: dict[str, set], rare_limit: int
) -> bool:
    """Two agreeing tokens, or one that is rare in the wiki lines. A frequent
    place or publisher ("Leipzig", "Moskva") alone stays a title-year block."""
    if len(agreeing) >= 2:
        return True
    return len(agreeing) == 1 and len(index.get(agreeing[0], ())) <= rare_limit


def main() -> int:
    for path in (REVISIONS,):
        if not path.exists():
            sys.exit(f"FEHLER: {path} missing; run p04_wiki_revisions.py first")
    entries = _load_entries()
    index, sizes = _print_index(entries)
    print(f"OK {len(entries)} print entries, {len(sizes)} with enough distinctive text")
    best, latest_lines, wiki = _align(index, sizes)
    line_index = _line_index(latest_lines)
    rare_limit = _rare_limit(latest_lines)
    slices, slice_check = _publication_slices(set(latest_lines), wiki["text"])
    page_titles = {
        page: " ".join(_tokens(title)) for page, title in wiki["titles"].items()
    }
    title_pages: dict[str, set] = defaultdict(set)
    for page, title in page_titles.items():
        for token in title.split():
            title_pages[token].add(page)

    claims: list[dict] = []
    links: dict[int, list[dict]] = defaultdict(list)
    stats: dict[str, Counter] = {v: Counter() for v in VOLUMES}
    silver: dict[str, Counter] = {v: Counter() for v in VOLUMES}
    alignment_scores: dict[str, list[float]] = {v: [] for v in VOLUMES}
    for n, entry in enumerate(entries):
        volume = entry["volume"]
        stats[volume]["entries"] += 1
        aligned = best.get(n)
        if n in sizes:
            stats[volume]["alignable"] += 1
            alignment_scores[volume].append(aligned["score"] if aligned else 0.0)
        field_pages: dict[int, str] = {}
        # Per page: publication -> most second-field tokens agreeing in a match.
        field_publications: dict[int, dict[str, int]] = defaultdict(dict)
        for obj in entry["objects"]:
            stats[volume]["objects"] += 1
            if _stands_for_items(obj):
                stats[volume]["collection_headers_not_matched"] += 1
                continue
            matches = _field_matches(
                obj, latest_lines, line_index, title_pages, page_titles, rare_limit
            )
            if matches:
                stats[volume]["objects_with_title_year_block"] += 1
            if any(m["kind"] == "field" for m in matches):
                stats[volume]["objects_with_field_match"] += 1
            for m in matches:
                if field_pages.get(m["page"]) != "field":
                    field_pages[m["page"]] = m["kind"]
                publication = _publication_at(
                    slices, wiki["offsets"], m["page"], m["line"]
                )
                if m["kind"] == "field":
                    stats[volume]["field_matches"] += 1
                    stats[volume]["field_matches_on_publication"] += bool(publication)
                    if publication:
                        held = field_publications[m["page"]]
                        held[publication] = max(
                            held.get(publication, 0), len(m["second_field"])
                        )
                claims.append(
                    {
                        "id": _claim_id(obj["id"], str(m["page"]), str(m["line"])),
                        "subject": obj["id"],
                        "predicate": "samePublicationAs"
                        if m["kind"] == "field"
                        else "candidateFor",
                        # A line inside a verified publication slice names that
                        # publication; otherwise only the page is known.
                        "object": publication or f"klawiter:entry/{m['page']}",
                        "evidence": {
                            "print": {"record": entry["id"], "sha256": entry["sha256"]},
                            "wiki_page": m["page"],
                            "wiki_line": wiki["raw"][m["page"]][m["line"]],
                            "second_field": m["second_field"],
                        },
                        "producer": FIELD,
                        "state": "proposed",
                    }
                )
        if aligned and aligned["score"] >= ALIGNED:
            stats[volume]["aligned"] += 1
            claims.append(
                {
                    "id": _claim_id(entry["id"], str(aligned["page"]), "align"),
                    "subject": entry["id"],
                    "predicate": "textAlignedWith",
                    "object": f"klawiter:entry/{aligned['page']}",
                    "evidence": {
                        "print": {"record": entry["id"], "sha256": entry["sha256"]},
                        "score": aligned["score"],
                        "first_seen": aligned["first_seen"],
                    },
                    "producer": ALIGN,
                    "state": "proposed",
                }
            )
        # Held-out records stay out of the silver statistics, which serve
        # rule development as a diagnosis (_heldout.py).
        if aligned and aligned["score"] >= SILVER and not is_held_out(entry):
            silver[volume]["pairs"] += 1
            kind = field_pages.get(aligned["page"])
            silver[volume]["found_by_title_year"] += kind is not None
            silver[volume]["found_by_field"] += kind == "field"
        routes = {}
        if aligned and aligned["score"] >= ALIGNED:
            routes[aligned["page"]] = {
                "route": "alignment",
                "score": aligned["score"],
                "firstSeen": aligned["first_seen"],
            }
        for page, kind in field_pages.items():
            routes.setdefault(page, {"route": kind})
        for page, publications in field_publications.items():
            # Ranked by agreeing second-field tokens; the best are candidates
            # first, the rest stay listed. A rank is no confirmation.
            ranked = sorted(publications, key=lambda p: (-publications[p], p))
            top = publications[ranked[0]]
            routes[page]["publicationIds"] = ranked
            routes[page]["bestPublicationIds"] = [
                p for p in ranked if publications[p] == top
            ]
        for page, route in routes.items():
            links[page].append(
                {
                    "printId": entry["id"],
                    "volume": volume,
                    "address": entry["address"],
                    "pdfPage": entry["page"],
                    "text": entry["text"],
                    **route,
                }
            )
        if routes:
            stats[volume]["entries_with_any_wiki_page"] += 1

    CLAIMS.mkdir(parents=True, exist_ok=True)
    out = CLAIMS / "concordance.jsonl"
    with out.with_suffix(".tmp").open("w", encoding="utf-8") as sink:
        for claim in claims:
            sink.write(json.dumps(claim, ensure_ascii=False) + "\n")
    out.with_suffix(".tmp").replace(out)
    LAB.mkdir(parents=True, exist_ok=True)
    lab = {
        "about": "Print matches per wiki page; local only, print rights unresolved. "
        "Routes: alignment (near-verbatim text in some revision), field (title, "
        "year and a second field in one line of the latest text), title-year "
        "(block only). All proposed, none confirmed.",
        "pages": {
            str(page): {"title": wiki["titles"].get(page, ""), "print": rows}
            for page, rows in sorted(links.items())
        },
    }
    (LAB / "print-links.json").write_text(
        json.dumps(lab, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    def deciles(values: list[float]) -> list[float]:
        ordered = sorted(values)
        return (
            [ordered[int(len(ordered) * q / 10)] for q in range(1, 10)]
            if ordered
            else []
        )

    report = {
        "parameters": {
            "shingle": SHINGLE,
            "max_shingle_units": MAX_SHINGLE_UNITS,
            "aligned": ALIGNED,
            "silver": SILVER,
            "chance": CHANCE,
            "rare_limit_lines": rare_limit,
        },
        "volumes": {
            v: {
                **dict(stats[v]),
                "alignment_score_deciles": deciles(alignment_scores[v]),
                "silver_test": {
                    **dict(silver[v]),
                    "recall_title_year": round(
                        silver[v]["found_by_title_year"] / max(1, silver[v]["pairs"]), 3
                    ),
                    "recall_field": round(
                        silver[v]["found_by_field"] / max(1, silver[v]["pairs"]), 3
                    ),
                },
            }
            for v in VOLUMES
        },
        "wiki_pages_with_print": len(links),
        "publication_slices": dict(slice_check),
        "claims": dict(Counter(c["predicate"] for c in claims)),
    }
    path = write_report("p07_concordance", report)
    for v in VOLUMES:
        s, t = stats[v], report["volumes"][v]["silver_test"]
        print(
            f"OK {v}: entries {s['entries']}, aligned {s['aligned']}, "
            f"objects {s['objects']} (block {s['objects_with_title_year_block']}, "
            f"field {s['objects_with_field_match']}), entries with a wiki page "
            f"{s['entries_with_any_wiki_page']}; silver {t['pairs']} pairs, recall "
            f"title-year {t['recall_title_year']}, field {t['recall_field']}"
        )
    print(f"OK wiki pages with print matches: {len(links)}; claims {report['claims']}")
    print(f"OK report {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
