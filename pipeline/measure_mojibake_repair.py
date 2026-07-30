#!/usr/bin/env python3
"""
Measure the broadened mojibake repair in lib/encoding.py.

The earlier repair only triggered on the Ã/Â (C2/C3) lead bytes, so the Latin
Extended-A and Extended-Additional diacritics of transliterated titles (the ā,
ī, ş, ḥ, ṭ of Arabic, Greek, Vietnamese and Slavic romanizations, error class 3
in knowledge/testing.md) and the double-encoded smart quotes were left
uncorrected. fix_mojibake now repairs each mojibake run independently by
re-encoding it as Latin-1 and decoding as UTF-8, validating the result.

This script characterizes that repair over the raw extraction input
(01_extracted.csv, namespace 0), the same text the encoding stage consumes:

  - how many mojibake runs are detected, repaired, and self-rejected
    (a run whose re-encoded bytes are not valid UTF-8 is left untouched),
  - the residual count after repair (must be 0 for a complete repair),
  - whether the repair is idempotent,
  - every repaired run whose output falls outside the common Latin, Greek,
    Cyrillic, Hebrew and Arabic blocks, listed in full for human review so a
    genuine corruption could not hide behind an aggregate count.

It is read-only over the data and writes data/output/mojibake-repair-report.json.
Deterministic: same inputs produce a byte-identical report.
"""

import csv
import os
import sys
import unicodedata
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import STEP_01_OUTPUT, OUTPUT_DIR
from lib.encoding import fix_mojibake, has_mojibake, _MOJIBAKE_RE, _redecode_run

REPORT_PATH = os.path.join(OUTPUT_DIR, 'mojibake-repair-report.json')

# Unicode blocks a transliterated Stefan-Zweig bibliography can legitimately
# gain from a repair. Anything outside is surfaced individually for review; it
# is not assumed wrong (the corpus carries rare polytonic Greek and a bullet),
# but it must be eyeballed rather than counted away.
def _is_common(s):
    for c in s:
        o = ord(c)
        if o < 0x80:
            continue
        if 0x80 <= o <= 0x024F:      # Latin-1 Supplement + Latin Extended-A/B
            continue
        if 0x0250 <= o <= 0x02FF:    # IPA + spacing modifier letters
            continue
        if 0x0300 <= o <= 0x036F:    # combining diacritics
            continue
        if 0x0370 <= o <= 0x04FF:    # Greek + Cyrillic
            continue
        if 0x0590 <= o <= 0x06FF:    # Hebrew + Arabic
            continue
        if 0x1E00 <= o <= 0x1EFF:    # Latin Extended Additional (transliteration)
            continue
        if 0x2000 <= o <= 0x209F:    # general punctuation, super/subscripts
            continue
        return False
    return True


def _codepoints(s):
    return ' '.join('U+%04X %s' % (ord(c), unicodedata.name(c, '?')) for c in s)


def load_ns0_content():
    csv.field_size_limit(10 ** 8)
    with open(STEP_01_OUTPUT, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('page_namespace') != '0':
                continue
            yield int(row['page_id']), row.get('content') or ''


def measure():
    runs_detected = runs_repaired = runs_self_rejected = 0
    distinct = set()
    unusual = Counter()
    residual_entries = 0
    not_idempotent = 0
    sample_titles = []

    for pid, content in load_ns0_content():
        for m in _MOJIBAKE_RE.finditer(content):
            runs_detected += 1
            run = m.group(0)
            fixed = _redecode_run(m)
            if fixed == run:
                runs_self_rejected += 1
            else:
                runs_repaired += 1
                distinct.add((run, fixed))
                if not _is_common(fixed):
                    unusual[(run, fixed)] += 1

        repaired = fix_mojibake(content)
        if has_mojibake(repaired):
            residual_entries += 1
        if fix_mojibake(repaired) != repaired:
            not_idempotent += 1

        if len(sample_titles) < 12 and _MOJIBAKE_RE.search(content):
            first = content.split('\n', 1)[0].strip()
            fixed_first = fix_mojibake(first)
            if first != fixed_first and len(first) <= 120:
                sample_titles.append({'pageId': pid, 'before': first, 'after': fixed_first})

    report = {
        'description': (
            'Broadened mojibake repair characterized over 01_extracted.csv '
            '(namespace 0). Runs are repaired by per-run Latin-1 re-encode then '
            'UTF-8 decode, with self-validation. Deterministic.'
        ),
        'source': os.path.relpath(STEP_01_OUTPUT).replace(os.sep, '/'),
        'runs': {
            'detected': runs_detected,
            'repaired': runs_repaired,
            'self_rejected': runs_self_rejected,
            'distinct_mappings': len(distinct),
        },
        'residual_entries_after_repair': residual_entries,
        'not_idempotent_entries': not_idempotent,
        'unusual_outputs': sorted(
            ({'run_codepoints': _codepoints(run),
              'output': fixed,
              'output_codepoints': _codepoints(fixed),
              'count': n}
             for (run, fixed), n in unusual.items()),
            key=lambda r: (-r['count'], r['output']),
        ),
        'sample_titles': sorted(sample_titles, key=lambda r: r['pageId']),
    }
    return report


def main():
    import json
    report = measure()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')
    r = report['runs']
    print(f"runs detected {r['detected']}  repaired {r['repaired']}  "
          f"self-rejected {r['self_rejected']}  distinct {r['distinct_mappings']}")
    print(f"residual entries after repair: {report['residual_entries_after_repair']}")
    print(f"not idempotent entries: {report['not_idempotent_entries']}")
    print(f"unusual outputs (for review): {len(report['unusual_outputs'])}")
    for u in report['unusual_outputs']:
        print(f"  {u['count']:4d}  {u['output']!r}  {u['output_codepoints']}")
    print(f"report written: {os.path.relpath(REPORT_PATH).replace(os.sep, '/')}")


if __name__ == '__main__':
    main()
