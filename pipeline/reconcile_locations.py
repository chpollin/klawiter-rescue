#!/usr/bin/env python3
"""
Reconcile locations from locations.json against Wikidata.

Two-phase approach:
1. Wikidata Reconciliation API (fuzzy matching, multi-language)
2. SPARQL endpoint (structured metadata for matched Q-IDs)

Output: Updated locations.json with wikidataId, wikidataLabel, wikidataScore, countryQid.
Also writes locations_reconciliation_log.json for manual review.

Usage: python pipeline/reconcile_locations.py
"""

import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).parent.parent
LOCATIONS_PATH = PROJECT_ROOT / "docs" / "data" / "locations.json"
LOG_PATH = PROJECT_ROOT / "docs" / "data" / "locations_reconciliation_log.json"
USER_AGENT = (
    "KlawitterBibliography/1.0 (https://github.com/chpollin/klawiter-rescue; research)"
)
RECON_BASE = "https://wikidata.reconci.link"
SPARQL_URL = "https://query.wikidata.org/sparql"
BATCH_SIZE = 20
DELAY_S = 2.0
MIN_SCORE = 70  # Minimum score for auto-accept


def clean_name(name: str) -> list[str]:
    """Generate search variants for a location name."""
    variants = []
    clean = name.rstrip("?").strip()

    # Bracketed alternatives: "Tiranë (Tirana)" → ["Tiranë", "Tirana"]
    m = re.match(r"^(.+?)\s*[\[(](.+?)[\])]$", clean)
    if m:
        variants.append(m.group(1).strip())
        variants.append(m.group(2).strip())

    # Slash variants: "Moskva / Vladivostok" → ["Moskva", "Vladivostok"]
    if "/" in clean:
        for part in clean.split("/"):
            trimmed = part.strip().split(",")[0].strip()
            if len(trimmed) > 1:
                variants.append(trimmed)

    # State suffix: "San Francisco, CA" → "San Francisco"
    m2 = re.match(r"^(.+?),\s*[A-Z]{2,3}$", clean)
    if m2:
        variants.append(m2.group(1).strip())

    if clean not in variants:
        variants.append(clean)

    return list(dict.fromkeys(variants))  # dedupe, preserve order


def reconcile_batch(names: list[str], lang: str = "en") -> dict:
    """Query Wikidata Reconciliation API for a batch of names."""
    queries = {}
    for i, name in enumerate(names):
        queries[f"q{i}"] = {
            "query": name,
            "type": "Q486972",  # human settlement
            "limit": 3,
        }
    resp = requests.post(
        f"{RECON_BASE}/{lang}/api",
        data={"queries": json.dumps(queries)},
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    resp.raise_for_status()
    raw = resp.json()

    results = {}
    for i, name in enumerate(names):
        key = f"q{i}"
        hits = raw.get(key, {}).get("result", [])
        if hits:
            results[name] = hits
    return results


def sparql_metadata(qids: list[str]) -> dict:
    """Fetch coordinates and country for a batch of Q-IDs via SPARQL."""
    if not qids:
        return {}
    values = " ".join(f"wd:{q}" for q in qids)
    query = f"""
SELECT ?item ?coord ?countryItem WHERE {{
  VALUES ?item {{ {values} }}
  OPTIONAL {{ ?item wdt:P625 ?coord . }}
  OPTIONAL {{ ?item wdt:P17 ?countryItem . }}
}}
"""
    resp = requests.get(
        SPARQL_URL,
        params={"format": "json", "query": query},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()
    bindings = resp.json().get("results", {}).get("bindings", [])

    result = {}
    for b in bindings:
        uri = b.get("item", {}).get("value", "")
        qid = uri.split("/")[-1] if uri else None
        if not qid:
            continue

        coord = None
        wkt = b.get("coord", {}).get("value", "")
        m = re.match(r"Point\(([-\d.]+)\s+([-\d.]+)\)", wkt)
        if m:
            coord = {"lng": float(m.group(1)), "lat": float(m.group(2))}

        country_uri = b.get("countryItem", {}).get("value", "")
        country_qid = country_uri.split("/")[-1] if country_uri else None

        result[qid] = {"coord": coord, "countryQid": country_qid}

    return result


def pick_best_match(hits_by_lang: dict) -> dict | None:
    """Pick the best match from multi-language results: exact match first, then highest score."""
    all_hits = []
    for lang, hits in hits_by_lang.items():
        for h in hits:
            all_hits.append({**h, "_lang": lang})

    if not all_hits:
        return None

    # Prefer match=True, then highest score
    all_hits.sort(
        key=lambda h: (h.get("match", False), h.get("score", 0)), reverse=True
    )
    return all_hits[0]


def main():
    locations = json.loads(LOCATIONS_PATH.read_text("utf-8"))
    print(f"Loaded {len(locations)} locations.")

    # Phase 1: Reconciliation API (multi-language)
    name_to_key = defaultdict(list)  # search_name → [original_keys]
    for key in locations:
        for variant in clean_name(key):
            name_to_key[variant].append(key)

    unique_names = list(name_to_key.keys())
    print(f"{len(unique_names)} unique search names.")

    # Reconcile in two languages: English + German
    all_results = defaultdict(dict)  # search_name → {lang: hits}

    for lang in ["en", "de"]:
        print(f"\nReconciling against {lang} endpoint...")
        batches = [
            unique_names[i : i + BATCH_SIZE]
            for i in range(0, len(unique_names), BATCH_SIZE)
        ]

        for bi, batch in enumerate(batches):
            print(
                f"  Batch {bi + 1}/{len(batches)} ({len(batch)} names)...",
                end=" ",
                flush=True,
            )
            try:
                results = reconcile_batch(batch, lang)
                matched = sum(1 for v in results.values() if v)
                print(f"{matched} matches")
                for name, hits in results.items():
                    all_results[name][lang] = hits
            except Exception as e:
                print(f"ERROR: {e}")
                if "429" in str(e):
                    print("  Rate limited, waiting 10s...")
                    time.sleep(10)
            time.sleep(DELAY_S)

    # Pick best match per original location key
    matches = {}  # original_key → {id, name, score, match}
    log = []

    for search_name, original_keys in name_to_key.items():
        hits_by_lang = all_results.get(search_name, {})
        if not hits_by_lang:
            continue

        for orig_key in original_keys:
            if orig_key in matches:
                continue  # already matched via another variant
            best = pick_best_match(hits_by_lang)
            if best and best.get("score", 0) >= MIN_SCORE:
                matches[orig_key] = {
                    "wikidataId": best["id"],
                    "wikidataLabel": best["name"],
                    "wikidataScore": round(best.get("score", 0)),
                    "matchExact": best.get("match", False),
                }
                log.append(
                    {
                        "location": orig_key,
                        "searchName": search_name,
                        "status": "matched",
                        **matches[orig_key],
                    }
                )
            elif best:
                log.append(
                    {
                        "location": orig_key,
                        "searchName": search_name,
                        "status": "low_score",
                        "wikidataId": best["id"],
                        "wikidataLabel": best["name"],
                        "wikidataScore": round(best.get("score", 0)),
                    }
                )

    # Log unmatched
    for key in locations:
        if key not in matches and not any(item["location"] == key for item in log):
            log.append({"location": key, "status": "unmatched"})

    matched_count = len(matches)
    total = len(locations)
    print(
        f"\nPhase 1 results: {matched_count}/{total} matched ({matched_count / total * 100:.1f}%)"
    )

    # Phase 2: SPARQL metadata for matched Q-IDs
    print("\nFetching SPARQL metadata...")
    all_qids = list(set(m["wikidataId"] for m in matches.values()))
    metadata = {}
    for i in range(0, len(all_qids), 50):
        batch = all_qids[i : i + 50]
        print(f"  SPARQL batch {i // 50 + 1} ({len(batch)} Q-IDs)...")
        try:
            batch_meta = sparql_metadata(batch)
            metadata.update(batch_meta)
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(1)

    print(f"  Metadata for {len(metadata)}/{len(all_qids)} Q-IDs.")

    # Phase 3: Update locations.json
    coord_updates = 0
    for key, match in matches.items():
        loc = locations[key]
        loc["wikidataId"] = match["wikidataId"]
        loc["wikidataLabel"] = match["wikidataLabel"]
        loc["wikidataScore"] = match["wikidataScore"]

        meta = metadata.get(match["wikidataId"], {})
        if meta.get("countryQid"):
            loc["countryQid"] = meta["countryQid"]
        if meta.get("coord"):
            wd_coord = meta["coord"]
            dist = abs(loc["lat"] - wd_coord["lat"]) + abs(loc["lng"] - wd_coord["lng"])
            if dist > 0.5:
                print(f"  Coord update: {key} ({dist:.2f} deg delta)")
                loc["lat"] = wd_coord["lat"]
                loc["lng"] = wd_coord["lng"]
                coord_updates += 1

    # Write results
    LOCATIONS_PATH.write_text(
        json.dumps(locations, indent=2, ensure_ascii=False), "utf-8"
    )
    LOG_PATH.write_text(json.dumps(log, indent=2, ensure_ascii=False), "utf-8")

    print("\nDone.")
    print(f"  Matched: {matched_count}/{total} ({matched_count / total * 100:.1f}%)")
    print(f"  Coordinate updates: {coord_updates}")
    print(f"  Log: {LOG_PATH}")
    print(f"  Updated: {LOCATIONS_PATH}")

    # Summary of unmatched
    unmatched = [item for item in log if item["status"] == "unmatched"]
    low_score = [item for item in log if item["status"] == "low_score"]
    if low_score:
        print(f"\n  Low score ({len(low_score)}, need review):")
        for item in low_score[:10]:
            print(
                f"    {item['location']} → {item['wikidataId']} ({item['wikidataLabel']}) score={item['wikidataScore']}"
            )
    if unmatched:
        print(f"\n  Unmatched ({len(unmatched)}):")
        for item in unmatched[:10]:
            print(f"    {item['location']}")


if __name__ == "__main__":
    main()
