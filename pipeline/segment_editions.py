#!/usr/bin/env python3
"""
Gate-1 Stichproben-Segmentierung: Multi-Edition-Seiten in Werk/Ausgabe-Knoten.

Deterministische Zerlegung der '''[Jahr]: Verlag, Ort'''-Editionsbloecke mit
Zeichenoffsets (Basis der oa:TextPositionSelector-Evidenz) nach dem Modell in
knowledge/ (Werk/Ausgabe-Trennung, ID-Schema klawiter:edition/{pageId}-{jahr}-
{laufbuchstabe}). Drafts sind Rohsegmentierung zur Editorin-Sichtung, keine
fertigen Ausgaben-Knoten; Befunde in data/output/edition-samples/REVIEW.md.

Input:  data/raw/zt_XX (BLOBs, direkt — die Seiten sind quellstabil)
Output: data/output/edition-samples/{slug}.draft.json + {slug}.wiki.txt
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.config import setup_logging, RAW_DIR, OUTPUT_DIR
from lib.encoding import fix_mojibake

log = setup_logging(__name__)

SAMPLES_DIR = os.path.join(OUTPUT_DIR, 'edition-samples')

TARGETS = [
    # (page_id, text_id, blob, work_title, slug)
    (54, 61144, 7, 'Ungeduld des Herzens. Roman', 'ungeduld_p54'),
    (4916, 59061, 6, 'Schachnovelle', 'schachnovelle_p4916'),
    (56, 50710, 5, 'Die Welt von Gestern. Erinnerungen eines Europäers', 'welt-von-gestern_p56'),
]

BS = chr(92)
ESC_QUOTE = BS + "'"
ESC_BS = BS + BS
ESC_NL = BS + 'n'

EDITION_HEADER = re.compile(r"^'''\s*\[")
SECTION_HEADER = re.compile(r"^'''\s*[A-Za-z][^\[\n]*?:?\s*'''\s*$")
YEAR_RE = re.compile(r'(\d{4})')
PAGES_RE = re.compile(r'(\d+)(?:/\(\d+\))?p\.')


def extract_raw(text_id, blob):
    """Read one text directly from its BLOB, same unescape chain as 01_extract."""
    path = os.path.join(RAW_DIR, 'zt_0%d' % blob)
    data = open(path, 'rb').read().decode('latin-1')
    marker = "(%d,_binary '" % text_id
    i = data.find(marker)
    if i < 0:
        raise SystemExit('text_id %d nicht in zt_0%d' % (text_id, blob))
    start = i + len(marker)
    j = data.find("',_binary '", start)
    content = data[start:j]
    content = content.replace("''", "'").replace(ESC_QUOTE, "'")
    content = content.replace(ESC_BS, BS).replace(ESC_NL, '\n')
    return fix_mojibake(content)


def parse_header(header_text):
    """'[1939]: Verlag A / Verlag B, Ort' -> (jahr_raw, publisher, location)."""
    m = re.match(r"\s*\[([^\]]*)\]\s*[:.]?\s*(.*)$", header_text)
    if not m:
        return None, header_text.strip(), None
    year_raw = m.group(1).strip()
    rest = m.group(2).strip().rstrip("'").strip()
    if ',' in rest:
        pub, loc = rest.rsplit(',', 1)
        return year_raw, pub.strip(), loc.strip()
    return year_raw, rest or None, None


def segment(page_id, text, work_title):
    lines = []
    off = 0
    for line in text.split('\n'):
        lines.append((off, line))
        off += len(line) + 1

    headers = []
    for off, line in lines:
        if EDITION_HEADER.match(line):
            headers.append((off, line, 'edition'))
        elif SECTION_HEADER.match(line):
            headers.append((off, line, 'section'))

    editions = []
    sections = []
    seq_per_year = {}
    for idx, (off, line, kind) in enumerate(headers):
        end = headers[idx + 1][0] if idx + 1 < len(headers) else len(text)
        if kind == 'section':
            sections.append({'heading': line.strip("' ").rstrip(':'), 'start': off, 'end': end})
            continue
        body = line.lstrip("'")
        # Doppel-Header '[1960]: A, B / [1964]: C, D' in Teil-Header zerlegen
        parts = re.split(r"\s*/\s*(?=\[(?:ca\.\s*)?\d{4}\])", body)
        for part in parts:
            year_raw, publisher, location = parse_header(part)
            ym = YEAR_RE.search(year_raw or '')
            year = int(ym.group(1)) if ym else None
            key = (year,)
            seq_per_year[key] = seq_per_year.get(key, 0) + 1
            letter = chr(ord('a') + seq_per_year[key] - 1)
            block = text[off:end]
            pm = PAGES_RE.search(block)
            editions.append({
                'id': 'klawiter:edition/%d-%s-%s' % (page_id, year if year else 'x', letter),
                'year': year,
                'yearRaw': year_raw,
                'publisher': publisher,
                'location': location,
                'pageCount': int(pm.group(1)) if pm else None,
                'headerLine': line.strip(),
                'evidence': {'sourceText': 'klawiter:sourceText/%d' % page_id,
                             'start': off, 'end': end},
                'reviewFlags': [f for f, cond in [
                    ('mehrdeutiger-header', len(parts) > 1),
                    ('jahr-unsicher', bool(year_raw and 'ca' in year_raw)),
                    ('ohne-ort', location is None),
                    ('ohne-jahr', year is None),
                ] if cond],
            })

    return {
        'work': {
            'id': 'klawiter:work/%d' % page_id,
            'type': 'schema:CreativeWork',
            'name': work_title,
            'sourcePageId': page_id,
        },
        'editions': editions,
        'unsegmentedSections': sections,
    }


def main():
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    for page_id, text_id, blob, title, slug in TARGETS:
        text = extract_raw(text_id, blob)
        with open(os.path.join(SAMPLES_DIR, slug + '.wiki.txt'), 'w', encoding='utf-8') as f:
            f.write(text)
        result = segment(page_id, text, title)
        out = os.path.join(SAMPLES_DIR, slug + '.draft.json')
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        flagged = sum(1 for e in result['editions'] if e['reviewFlags'])
        log.info('%s: %d Zeichen, %d Editionen (%d mit Review-Flags), %d Sektionen',
                 slug, len(text), len(result['editions']), flagged,
                 len(result['unsegmentedSections']))


if __name__ == '__main__':
    main()
