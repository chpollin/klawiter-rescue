#!/usr/bin/env python3
"""
Verification script: round-trip check of pipeline extraction quality.

Loads the final JSON-LD output and the encoding-fixed intermediate CSV,
then for each entry compares extracted fields against the raw wiki content
to find false positives (wrong extractions) and false negatives (missed info).

Output: data/output/verification-report.json
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (
    OUTPUT_DIR,
    OUTPUT_JSONLD,
    STEP_02_OUTPUT,
    load_csv,
    setup_logging,
    write_json,
)
from lib.encoding import normalize_text as normalize
from lib.encoding import strip_encoding_artifacts as strip_encoding
from lib.patterns import (
    PAGE_RANGE_RE,
    PARENS_PAGE_RE,
    extract_all_years,
    extract_location,
    extract_publisher,
    extract_translator,
)
from lib.vocabulary import plain_value
from lib.wiki_parser import remove_wiki_markup

log = setup_logging(__name__)

REPORT_PATH = os.path.join(OUTPUT_DIR, "verification-report.json")


def load_raw_content_map():
    """Load step 02 CSV and build text_id -> {content, page_title} mapping."""
    rows = load_csv(STEP_02_OUTPUT)
    content_map = {}
    for row in rows:
        text_id = row.get("text_id", "")
        if text_id:
            content_map[int(text_id)] = {
                "content": row.get("content", ""),
                "page_title": row.get("page_title", ""),
            }
    return content_map


def value_in_content(value, content):
    """Check if a value appears in the raw content.
    Tries exact match first, then encoding-aware match.
    """
    if not value or not content:
        return False
    # Exact (case-insensitive, whitespace-normalized)
    if normalize(value) in normalize(content):
        return True
    # Encoding-aware: strip mojibake from both sides
    if normalize(strip_encoding(value)) in normalize(strip_encoding(content)):
        return True
    return False


def page_count_in_content(page_count, content):
    """Check if a page count value appears in raw content.
    Handles: literal number, N/(M)p. summation, pp. X-Y ranges.
    """
    if page_count is None or not content:
        return False
    pc = int(page_count)
    # Direct match
    if str(pc) in content:
        return True
    # N/(M)p. summation: e.g. 285/(3)p. → 288
    for m in PARENS_PAGE_RE.finditer(content):
        numbered, unnumbered = int(m.group(1)), int(m.group(2))
        if numbered + unnumbered == pc:
            return True
    # pp. X-Y range: correct count is Y - X + 1
    for m in PAGE_RANGE_RE.finditer(content):
        start, end = int(m.group(1)), int(m.group(2))
        if end - start + 1 == pc:
            return True
    return False


def has_publisher_indicator(text):
    """Broader check: does the text contain indicators of a publisher
    that the current patterns might miss?
    Looks for: city + colon patterns, known publisher suffixes in context, etc.
    """
    if not text:
        return None
    # Pattern: "City: Something" or "City, Something, year"
    m = re.search(
        r"(?:Wien|Berlin|Leipzig|London|New York|Paris|Zürich|Frankfurt|München|Hamburg|Stockholm)\s*[,:]\s*([A-Z][\w\s&.\'-]{2,60})",
        text,
    )
    if m:
        candidate = m.group(1).strip().rstrip(".,;:")
        if len(candidate) >= 3 and not candidate.isdigit():
            return candidate
    return None


def has_translator_indicator(text):
    """Broader check: does the text contain indicators of a translation
    that the current patterns might miss?
    Looks for: Übers., trad., translator abbreviations, etc.
    """
    if not text:
        return None
    indicators = [
        # German abbreviations
        re.compile(
            r"[Üü]bers\.?\s+(?:v\.?\s+)?([A-Z][a-zA-ZÀ-ÿ\s.\'-]{2,60})", re.UNICODE
        ),
        # French short
        re.compile(
            r"trad\.?\s+(?:de\s+|par\s+)?([A-Z][a-zA-ZÀ-ÿ\s.\'-]{2,60})", re.UNICODE
        ),
        # English short
        re.compile(r"tr\.?\s+(?:by\s+)?([A-Z][a-zA-ZÀ-ÿ\s.\'-]{2,60})", re.UNICODE),
        # Parenthetical translator
        re.compile(
            r"\((?:translated|übersetzt|traduit|trad\.?)\s+(?:by|von|par)\s+([A-Z][a-zA-ZÀ-ÿ\s.\'-]{2,60})\)",
            re.IGNORECASE | re.UNICODE,
        ),
    ]
    for pat in indicators:
        m = pat.search(text)
        if m:
            name = m.group(1).strip().rstrip(".,;:")
            if len(name) >= 3:
                return name
    return None


def verify_entry(entry, raw_content, page_title=""):
    """Verify a single entry's extracted fields against raw content.
    Returns dict with per-field verification results.
    """
    result = {
        "page_id": entry.get("sourcePageId"),
        "title": plain_value(entry.get("name", "")),
        "fields": {},
    }

    if not raw_content:
        result["error"] = "no_raw_content"
        return result

    # Clean version of raw content (wiki markup removed) for title comparison
    raw_clean = remove_wiki_markup(raw_content)

    # --- Title verification ---
    # The pipeline uses page_title as fallback when wiki extraction returns a
    # [year]: pattern (metadata, not a real title). page_title is wiki page name
    # metadata and will never appear in raw_content — that's expected, not a
    # false positive. We detect this case and classify it separately.
    title = plain_value(entry.get("name", ""))
    if title:
        found = value_in_content(title, raw_content) or value_in_content(
            title, raw_clean
        )
        if found:
            status = "correct"
            title_source = "wiki_extract"
        elif page_title and (
            normalize(title) == normalize(page_title)
            or normalize(title) == normalize(remove_wiki_markup(page_title))
        ):
            # Title came from page_title fallback — not in raw content by design
            status = "correct_fallback"
            title_source = "page_title_fallback"
        else:
            status = "false_positive"
            title_source = "unknown"
        result["fields"]["title"] = {
            "extracted": title,
            "in_raw": found,
            "status": status,
            "title_source": title_source,
        }

    # --- Year verification ---
    date_published = entry.get("datePublished")
    year = int(date_published) if date_published else None
    if year is not None:
        year_str = str(year)
        found = year_str in raw_content
        result["fields"]["year"] = {
            "extracted": year,
            "in_raw": found,
            "status": "correct" if found else "false_positive",
        }

    # Check for years in raw content not captured
    raw_years = extract_all_years(raw_content)
    extracted_years = entry.get("allYears", [])
    if not extracted_years and year is not None:
        extracted_years = [year]
    missed_years = [y for y in raw_years if y not in extracted_years]
    if missed_years:
        result["fields"]["year_false_negatives"] = missed_years

    # --- Publisher verification ---
    publisher = plain_value(entry.get("publisher", ""))
    if publisher:
        found = value_in_content(publisher, raw_content)
        result["fields"]["publisher"] = {
            "extracted": publisher,
            "in_raw": found,
            "status": "correct" if found else "false_positive",
        }

    # Check for publisher patterns in raw content not captured
    if not publisher:
        raw_publisher = extract_publisher(raw_content) or has_publisher_indicator(
            raw_clean
        )
        if raw_publisher:
            result["fields"]["publisher_false_negative"] = {
                "detected_in_raw": raw_publisher,
                "note": "publisher found in raw but not in output",
            }

    # --- Location verification ---
    location = plain_value(entry.get("locationCreated", ""))
    if location:
        found = value_in_content(location, raw_content)
        result["fields"]["location"] = {
            "extracted": location,
            "in_raw": found,
            "status": "correct" if found else "false_positive",
        }

    # Check for locations not captured
    if not location:
        raw_location = extract_location(raw_content)
        if raw_location:
            result["fields"]["location_false_negative"] = {
                "detected_in_raw": raw_location,
                "note": "location found in raw but not in output",
            }

    # --- Translator verification ---
    translator = plain_value(entry.get("translator", ""))
    if translator:
        found = value_in_content(translator, raw_content)
        result["fields"]["translator"] = {
            "extracted": translator,
            "in_raw": found,
            "status": "correct" if found else "false_positive",
        }

    # Check for translator patterns not captured
    if not translator:
        raw_translator = extract_translator(raw_content) or has_translator_indicator(
            raw_clean
        )
        if raw_translator:
            result["fields"]["translator_false_negative"] = {
                "detected_in_raw": raw_translator,
                "note": "translator found in raw but not in output",
            }

    # --- Page count verification ---
    page_count = entry.get("numberOfPages")
    if page_count is not None:
        found = page_count_in_content(page_count, raw_content)
        result["fields"]["page_count"] = {
            "extracted": page_count,
            "in_raw": found,
            "status": "correct" if found else "false_positive",
        }

    return result


def compute_summary(results):
    """Compute aggregate statistics from verification results."""
    fields = ["title", "year", "publisher", "location", "translator", "page_count"]
    summary = {}

    for field in fields:
        total_extracted = 0
        correct = 0
        correct_fallback = 0
        false_positive = 0
        false_negative = 0

        for r in results:
            f = r.get("fields", {})
            if field in f:
                total_extracted += 1
                status = f[field]["status"]
                if status == "correct":
                    correct += 1
                elif status == "correct_fallback":
                    correct_fallback += 1
                elif status == "false_positive":
                    false_positive += 1

            fn_key = f"{field}_false_negative"
            if fn_key in f:
                false_negative += 1

        total_entries = len(results)
        coverage = total_extracted / total_entries if total_entries else 0
        # Precision: both correct and correct_fallback count as correct
        total_correct = correct + correct_fallback
        precision = total_correct / total_extracted if total_extracted else 0

        summary[field] = {
            "total_entries": total_entries,
            "extracted": total_extracted,
            "correct": correct,
            "correct_fallback": correct_fallback,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "coverage": round(coverage * 100, 1),
            "precision": round(precision * 100, 1),
        }

    return summary


def main():
    # Load JSON-LD
    log.info(f"Loading JSON-LD: {OUTPUT_JSONLD}")
    with open(OUTPUT_JSONLD, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    entries = dataset.get("entries", [])
    log.info(f"  Loaded {len(entries)} entries")

    # Load raw content
    log.info(f"Loading raw content: {STEP_02_OUTPUT}")
    content_map = load_raw_content_map()
    log.info(f"  Loaded {len(content_map)} raw content entries")

    # Filter to namespace 0 non-redirect entries for verification
    bib_entries = [
        e for e in entries if e.get("pageNamespace", 0) == 0 and not e.get("isRedirect")
    ]
    log.info(f"  Bibliography entries (ns0, non-redirect): {len(bib_entries)}")

    # Verify each entry
    results = []
    no_raw = 0
    for entry in bib_entries:
        text_id = entry.get("sourceTextId")
        raw_data = content_map.get(text_id, {}) if text_id else {}
        raw_content = (
            raw_data.get("content", "") if isinstance(raw_data, dict) else raw_data
        )
        page_title = (
            raw_data.get("page_title", "") if isinstance(raw_data, dict) else ""
        )
        if not raw_content:
            no_raw += 1

        result = verify_entry(entry, raw_content, page_title=page_title)
        results.append(result)

    log.info(f"  Entries without raw content: {no_raw}")

    # Compute summary
    summary = compute_summary(results)

    # Log summary
    log.info("=" * 60)
    log.info("VERIFICATION SUMMARY")
    log.info("=" * 60)
    for field, stats in summary.items():
        log.info(
            f"  {field:15s}: coverage={stats['coverage']:5.1f}%  "
            f"precision={stats['precision']:5.1f}%  "
            f"FP={stats['false_positive']:4d}  FN={stats['false_negative']:4d}  "
            f"extracted={stats['extracted']}/{stats['total_entries']}"
        )

    # Collect examples of false positives and false negatives
    false_positive_examples = {}
    false_negative_examples = {}
    for field in ["title", "year", "publisher", "location", "translator", "page_count"]:
        fp_list = []
        fn_list = []
        for r in results:
            f = r.get("fields", {})
            if (
                field in f
                and f[field]["status"] == "false_positive"
                and len(fp_list) < 10
            ):
                fp_list.append(
                    {
                        "page_id": r["page_id"],
                        "title": r["title"],
                        "extracted_value": f[field]["extracted"],
                    }
                )
            fn_key = f"{field}_false_negative"
            if fn_key in f and len(fn_list) < 10:
                fn_list.append(
                    {
                        "page_id": r["page_id"],
                        "title": r["title"],
                        "detected_in_raw": f[fn_key].get("detected_in_raw", f[fn_key]),
                    }
                )
        if fp_list:
            false_positive_examples[field] = fp_list
        if fn_list:
            false_negative_examples[field] = fn_list

    # Build report
    report = {
        "summary": summary,
        "false_positive_examples": false_positive_examples,
        "false_negative_examples": false_negative_examples,
        "total_bib_entries": len(bib_entries),
        "entries_without_raw_content": no_raw,
        "detailed_results": results,
    }

    # Write report
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    write_json(REPORT_PATH, report, indent=2)
    log.info(f"\nReport written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
