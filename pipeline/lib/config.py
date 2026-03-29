"""
Centralized configuration for the Klawiter pipeline.
All paths, limits, and shared setup in one place.
"""

import csv
import os
import sys
import logging

# CSV field size limit (10MB) — set once, globally
csv.field_size_limit(10 * 1024 * 1024)

# Windows console encoding fix
if sys.platform == 'win32':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')

# Base directories
PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(PIPELINE_DIR)

# Source files (raw MediaWiki dumps)
RAW_DIR = os.path.join(PROJECT_ROOT, 'data', 'raw')
SQL_DUMP_PATH = os.path.join(RAW_DIR, 'zweig_part_01.sql')
BLOB_FILES = [os.path.join(RAW_DIR, f'zt_0{i}') for i in range(8)]

# Intermediate data
INTERMEDIATE_DIR = os.path.join(PROJECT_ROOT, 'data', 'intermediate')
STEP_01_OUTPUT = os.path.join(INTERMEDIATE_DIR, '01_extracted.csv')
STEP_02_OUTPUT = os.path.join(INTERMEDIATE_DIR, '02_encoding_fixed.csv')
STEP_03_OUTPUT = os.path.join(INTERMEDIATE_DIR, '03_parsed.csv')
STEP_04_OUTPUT = os.path.join(INTERMEDIATE_DIR, '04_classified.csv')

# Final output
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'data', 'output')
OUTPUT_JSONLD = os.path.join(OUTPUT_DIR, 'klawiter.jsonld')
OUTPUT_ENTRIES_DIR = os.path.join(OUTPUT_DIR, 'entries')
OUTPUT_QUALITY_REPORT = os.path.join(OUTPUT_DIR, 'quality-report.json')
OUTPUT_FRONTEND_JSON = os.path.join(PROJECT_ROOT, 'docs', 'data', 'klawiter.json')

# Year validation range
import datetime
MAX_VALID_YEAR = datetime.datetime.now().year + 5


def setup_logging(name=None):
    """Standard logging setup for all pipeline scripts."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s'
    )
    return logging.getLogger(name or __name__)


def load_csv(path):
    """Load a CSV file into a list of dicts. Validates file exists."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file not found: {path}")
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def write_csv(path, rows, fieldnames):
    """Write rows to CSV atomically (write to .tmp, then rename)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    # Atomic rename (on Windows, need to remove target first if exists)
    if os.path.exists(path):
        os.remove(path)
    os.rename(tmp_path, path)
