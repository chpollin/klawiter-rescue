#!/usr/bin/env python3
"""
Census: end-to-end record reconciliation from the SQL source to the frontend.

Where verify.py checks field *values* and 06_validate.py reports dataset
quality, this script answers a different question: does every record make it
from the raw SQL dump into the JSON-LD and the frontend, with nothing silently
lost and nothing invented? It is the completeness counterpart to verify.py's
correctness check.

It reconciles three layers:
  source    data/intermediate/01_extracted.csv  (one row per MediaWiki page)
  jsonld    data/output/klawiter.jsonld          (full Linked Data dataset)
  frontend  docs/data/klawiter.json              (what the site loads)

and asserts the identities that must hold if the pipeline is lossless:
  - every source page_id appears exactly once in the JSON-LD (no loss, no dup)
  - the JSON-LD invents no page_id absent from the source
  - the frontend is the JSON-LD minus redirects
  - source ns0 = displayed entries + ns0 redirects

Records with empty source content (no BLOB text row) are reported separately
and split into bibliographic (namespace 0) and non-bibliographic. A page that
is empty in the source is not a pipeline failure; it is a faithful copy of an
empty source page.

Output: data/output/census-report.json + a console summary with PASS/FAIL.
Read-only over the data; writes only the report.
"""

import csv
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import (
    setup_logging, STEP_01_OUTPUT, OUTPUT_JSONLD, OUTPUT_FRONTEND_JSON,
    OUTPUT_DIR,
)

log = setup_logging(__name__)

REPORT_PATH = os.path.join(OUTPUT_DIR, 'census-report.json')

# Namespaces that carry bibliographic entries. Everything else (category,
# template, file, mediawiki system pages) is structural, not a bibliography
# record, and its absence from the displayed UI is by design.
BIBLIOGRAPHIC_NS = 0


def load_source_pages():
    """Load 01_extracted.csv: one row per source page across all namespaces."""
    csv.field_size_limit(10 ** 8)
    pages = {}
    with open(STEP_01_OUTPUT, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            pid = int(row['page_id'])
            pages[pid] = {
                'namespace': int(row['page_namespace']),
                'title': row.get('page_title', ''),
                'text_id': row.get('text_id', ''),
                'empty': not row.get('content', '').strip(),
            }
    return pages


def load_entries(path):
    """Load a dataset file; entries live under 'entries' or are the top list."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return data['entries'] if isinstance(data, dict) and 'entries' in data else data


def is_redirect(entry):
    return bool(entry.get('isRedirect')) or entry.get('entryType') == 'redirect'


def main():
    log.info("Loading layers ...")
    pages = load_source_pages()
    jsonld = load_entries(OUTPUT_JSONLD)
    frontend = load_entries(OUTPUT_FRONTEND_JSON)
    log.info(f"  source pages: {len(pages)}  jsonld: {len(jsonld)}  frontend: {len(frontend)}")

    # --- Source layer -----------------------------------------------------
    source_ns = Counter(p['namespace'] for p in pages.values())
    empty_pages = {pid: p for pid, p in pages.items() if p['empty']}
    empty_biblio = {pid: p for pid, p in empty_pages.items()
                    if p['namespace'] == BIBLIOGRAPHIC_NS}
    empty_other = {pid: p for pid, p in empty_pages.items()
                   if p['namespace'] != BIBLIOGRAPHIC_NS}

    # --- JSON-LD layer ----------------------------------------------------
    jsonld_pids = [e.get('sourcePageId') for e in jsonld]
    jsonld_pid_counts = Counter(jsonld_pids)
    jsonld_dups = {pid: n for pid, n in jsonld_pid_counts.items() if n > 1}
    jsonld_pid_set = set(jsonld_pids)
    source_pid_set = set(pages.keys())
    missing_in_jsonld = source_pid_set - jsonld_pid_set      # source page lost
    invented_in_jsonld = jsonld_pid_set - source_pid_set     # record with no source
    jsonld_redirects = sum(1 for e in jsonld if is_redirect(e))

    # --- Frontend layer ---------------------------------------------------
    frontend_redirects = sum(1 for e in frontend if is_redirect(e))
    frontend_ns = Counter(e.get('pageNamespace') for e in frontend)
    displayed = [e for e in frontend
                 if e.get('pageNamespace') == BIBLIOGRAPHIC_NS and not is_redirect(e)]
    # An entry is "named" if it carries a display title. The frontend stores it
    # under "title"; the JSON-LD under "name". Decision (2026-06-21): a source-
    # blanked bibliographic page (e.g. 2979, BLOB text missing) is displayed with
    # its page-title fallback rather than hidden, so it is named like any other
    # entry. The invariant is therefore that no displayed entry is unnamed.
    def display_name(e):
        return (e.get('title') or e.get('name') or '').strip()
    unnamed_displayed = [e for e in displayed if not display_name(e)]

    # --- Reconciliation identities ---------------------------------------
    ns0_redirects = sum(1 for e in jsonld
                        if e.get('pageNamespace') == BIBLIOGRAPHIC_NS and is_redirect(e))
    checks = []

    def check(name, ok, detail):
        checks.append({'check': name, 'pass': bool(ok), 'detail': detail})

    check('jsonld_is_1to1_with_source',
          not missing_in_jsonld and not invented_in_jsonld and not jsonld_dups,
          f"missing={len(missing_in_jsonld)} invented={len(invented_in_jsonld)} dups={len(jsonld_dups)}")
    check('frontend_excludes_all_redirects',
          frontend_redirects == 0,
          f"redirects in frontend = {frontend_redirects}")
    check('frontend_equals_jsonld_minus_redirects',
          len(frontend) == len(jsonld) - jsonld_redirects,
          f"{len(frontend)} == {len(jsonld)} - {jsonld_redirects}")
    check('source_ns0_equals_displayed_plus_ns0_redirects',
          source_ns[BIBLIOGRAPHIC_NS] == len(displayed) + ns0_redirects,
          f"{source_ns[BIBLIOGRAPHIC_NS]} == {len(displayed)} + {ns0_redirects}")
    unnamed_pids = {e.get('sourcePageId') for e in unnamed_displayed}
    check('every_displayed_entry_is_named',
          unnamed_pids == set(),
          f"empty_biblio={len(empty_biblio)} (blanked, shown with page-title fallback) "
          f"unnamed_displayed={len(unnamed_pids)} ids={sorted(unnamed_pids)[:20]}")

    report = {
        'source': {
            'total_pages': len(pages),
            'by_namespace': dict(sorted(source_ns.items())),
            'empty_content_pages': {
                'total': len(empty_pages),
                'bibliographic_ns0': [
                    {'page_id': pid, 'title': p['title'], 'text_id': p['text_id']}
                    for pid, p in sorted(empty_biblio.items())
                ],
                'non_bibliographic': [
                    {'page_id': pid, 'namespace': p['namespace'], 'title': p['title']}
                    for pid, p in sorted(empty_other.items())
                ],
            },
        },
        'jsonld': {
            'total_entries': len(jsonld),
            'unique_source_pages': len(jsonld_pid_set),
            'redirects': jsonld_redirects,
            'non_redirects': len(jsonld) - jsonld_redirects,
            'missing_source_pages': sorted(missing_in_jsonld),
            'invented_records': sorted(p for p in invented_in_jsonld if p is not None),
            'duplicate_source_pages': jsonld_dups,
        },
        'frontend': {
            'total_entries': len(frontend),
            'redirects': frontend_redirects,
            'by_namespace': dict(sorted((k, v) for k, v in frontend_ns.items() if k is not None)),
            'displayed_ns0_entries': len(displayed),
            'unnamed_displayed': [
                {'page_id': e.get('sourcePageId'),
                 'title_from_source': pages.get(e.get('sourcePageId'), {}).get('title', ''),
                 'entry_type': e.get('entryType')}
                for e in unnamed_displayed
            ],
        },
        'reconciliation_checks': checks,
        'all_checks_pass': all(c['pass'] for c in checks),
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # --- Console summary --------------------------------------------------
    log.info("=" * 64)
    log.info("RECORD CENSUS  (SQL source -> JSON-LD -> frontend)")
    log.info("=" * 64)
    log.info(f"  source pages       : {len(pages)}  {dict(sorted(source_ns.items()))}")
    log.info(f"  jsonld entries     : {len(jsonld)}  (1:1 with source: "
             f"{'YES' if not missing_in_jsonld and not invented_in_jsonld and not jsonld_dups else 'NO'})")
    log.info(f"  jsonld redirects   : {jsonld_redirects}")
    log.info(f"  frontend entries   : {len(frontend)}  (redirects: {frontend_redirects})")
    log.info(f"  displayed (ns0)    : {len(displayed)}")
    log.info(f"  empty-content pages: {len(empty_pages)}  "
             f"(bibliographic ns0: {len(empty_biblio)}, other: {len(empty_other)})")
    log.info(f"  unnamed displayed  : {len(unnamed_displayed)}")
    for pid, p in sorted(empty_biblio.items()):
        log.info(f"     -> ns0 blanked page {pid}: \"{p['title']}\" (text_id {p['text_id']})")
    log.info("-" * 64)
    for c in checks:
        log.info(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['check']}  ({c['detail']})")
    log.info("-" * 64)
    log.info(f"  ALL CHECKS PASS: {report['all_checks_pass']}")
    log.info(f"\nReport written to {REPORT_PATH}")

    return 0 if report['all_checks_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
