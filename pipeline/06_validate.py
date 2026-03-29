#!/usr/bin/env python3
"""
Step 6: Validate the JSON-LD output and generate a quality report.

Input:  data/output/klawiter.jsonld
Output: data/output/quality-report.json
"""

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import setup_logging, OUTPUT_JSONLD, OUTPUT_QUALITY_REPORT
from lib.encoding import has_mojibake

log = setup_logging(__name__)


def validate_entry(entry):
    """Validate a single entry and return list of issues."""
    issues = []

    if not entry.get('klawiter:title') and not entry.get('klawiter:isRedirect'):
        issues.append({'field': 'title', 'issue': 'missing', 'severity': 'warning'})

    if not entry.get('klawiter:entryType'):
        issues.append({'field': 'entryType', 'issue': 'missing', 'severity': 'error'})

    if entry.get('klawiter:isRedirect'):
        return issues

    # Year validation
    year = entry.get('klawiter:year')
    if year:
        if not isinstance(year, int) or year < 1800 or year > 2035:
            issues.append({'field': 'year', 'issue': f'invalid value: {year}', 'severity': 'warning'})

    if not entry.get('klawiter:fullBibliographicEntry'):
        issues.append({'field': 'fullBibliographicEntry', 'issue': 'missing', 'severity': 'info'})

    for field in ('klawiter:title', 'klawiter:fullBibliographicEntry'):
        val = entry.get(field, '')
        if isinstance(val, str) and has_mojibake(val):
            issues.append({'field': field, 'issue': 'residual Mojibake detected', 'severity': 'warning'})

    return issues


def main():
    log.info(f"Reading {OUTPUT_JSONLD}")

    with open(OUTPUT_JSONLD, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    entries = dataset.get('klawiter:entries', [])
    log.info(f"Loaded {len(entries)} entries, validating...")

    all_issues = []
    entries_with_issues = 0
    severity_counts = Counter()

    for entry in entries:
        issues = validate_entry(entry)
        if issues:
            entries_with_issues += 1
            for issue in issues:
                issue['entry_id'] = entry.get('@id', 'unknown')
                severity_counts[issue['severity']] += 1
                all_issues.append(issue)

    # Field coverage (non-redirects in main namespace only)
    non_redirects = [e for e in entries
                     if not e.get('klawiter:isRedirect')
                     and e.get('klawiter:pageNamespace', 0) == 0]
    non_redirect_count = len(non_redirects)

    # Also count all non-redirects (including category pages etc.)
    all_non_redirects = [e for e in entries if not e.get('klawiter:isRedirect')]

    coverage_fields = [
        'klawiter:title', 'klawiter:year', 'klawiter:publisher',
        'klawiter:location', 'klawiter:language', 'klawiter:languageCode',
        'klawiter:pageCount', 'klawiter:translator', 'klawiter:categories',
        'klawiter:mainCategory', 'klawiter:fullBibliographicEntry',
        'klawiter:seeAlso', 'klawiter:reprints', 'klawiter:translations',
        'klawiter:contentItems',
    ]

    field_coverage = {}
    for field in coverage_fields:
        present = sum(1 for e in non_redirects if e.get(field))
        field_coverage[field] = {
            'count': present,
            'percentage': round(100 * present / non_redirect_count, 1) if non_redirect_count else 0,
        }

    # Distributions
    type_dist = Counter(e.get('klawiter:entryType', 'unknown') for e in entries)
    lang_dist = Counter(e.get('klawiter:language', '') for e in all_non_redirects if e.get('klawiter:language'))
    period_dist = Counter(e.get('klawiter:timePeriod', '') for e in all_non_redirects if e.get('klawiter:timePeriod'))
    ns_dist = Counter(e.get('klawiter:pageNamespace', 0) for e in entries)

    years = [e.get('klawiter:year') for e in all_non_redirects if e.get('klawiter:year')]
    year_range = {'min': min(years), 'max': max(years), 'count': len(years)} if years else {}

    report = {
        'summary': {
            'total_entries': len(entries),
            'redirects': sum(1 for e in entries if e.get('klawiter:isRedirect')),
            'non_redirects_main': non_redirect_count,
            'non_redirects_all': len(all_non_redirects),
            'entries_with_issues': entries_with_issues,
            'total_issues': len(all_issues),
            'severity_counts': dict(severity_counts),
        },
        'namespace_distribution': dict(sorted(ns_dist.items())),
        'field_coverage': field_coverage,
        'entry_type_distribution': dict(type_dist.most_common()),
        'language_distribution': dict(lang_dist.most_common(30)),
        'time_period_distribution': dict(period_dist.most_common()),
        'year_range': year_range,
        'sample_issues': all_issues[:50],
    }

    os.makedirs(os.path.dirname(OUTPUT_QUALITY_REPORT), exist_ok=True)
    with open(OUTPUT_QUALITY_REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log.info(f"Quality report written to {OUTPUT_QUALITY_REPORT}")
    log.info(f"Summary:")
    log.info(f"  Total entries: {len(entries)}")
    log.info(f"  Redirects: {report['summary']['redirects']}")
    log.info(f"  Non-redirects (main ns): {non_redirect_count}")
    log.info(f"  Non-redirects (all ns): {len(all_non_redirects)}")
    log.info(f"  Namespace distribution: {dict(ns_dist)}")
    log.info(f"  Entries with issues: {entries_with_issues}")
    log.info(f"  Issues by severity: {dict(severity_counts)}")
    log.info(f"Field coverage (non-redirects, main namespace):")
    for field, info in field_coverage.items():
        short = field.split(':')[1]
        log.info(f"  {short}: {info['percentage']}% ({info['count']}/{non_redirect_count})")


if __name__ == '__main__':
    main()
