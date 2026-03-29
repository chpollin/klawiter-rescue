#!/usr/bin/env python3
"""
Run the complete Klawiter extraction pipeline.
Each step reads from the previous step's output.

Usage:
    python run_pipeline.py          # Run all steps
    python run_pipeline.py 3        # Run from step 3 onwards
    python run_pipeline.py 2 4      # Run steps 2 through 4
"""

import subprocess
import sys
import os
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

STEPS = [
    ('01_extract.py', 'Extract entries from SQL dump + BLOBs'),
    ('02_fix_encoding.py', 'Fix Mojibake encoding'),
    ('03_parse_entries.py', 'Parse wiki markup → structured fields'),
    ('03b_llm_enrich.py', 'LLM-based metadata enrichment (Gemini)'),
    ('04_classify.py', 'Classify entry types + time periods'),
    ('05_to_jsonld.py', 'Convert to JSON-LD'),
    ('06_validate.py', 'Validate + quality report'),
]


def main():
    pipeline_dir = os.path.dirname(os.path.abspath(__file__))

    # Parse step range
    start = 1
    end = len(STEPS)
    if len(sys.argv) >= 2:
        start = int(sys.argv[1])
    if len(sys.argv) >= 3:
        end = int(sys.argv[2])

    print(f"{'='*60}")
    print(f"Klawiter Pipeline — Steps {start}–{end}")
    print(f"{'='*60}")

    total_start = time.time()

    for i in range(start - 1, end):
        script, description = STEPS[i]
        step_num = i + 1
        print(f"\n{'—'*60}")
        print(f"Step {step_num}/{len(STEPS)}: {description}")
        print(f"Running: {script}")
        print(f"{'—'*60}")

        step_start = time.time()
        result = subprocess.run(
            [sys.executable, os.path.join(pipeline_dir, script)],
            cwd=os.path.dirname(pipeline_dir),
        )

        elapsed = time.time() - step_start
        if result.returncode != 0:
            print(f"\nStep {step_num} FAILED (exit code {result.returncode}) after {elapsed:.1f}s")
            sys.exit(1)

        print(f"Step {step_num} completed in {elapsed:.1f}s")

    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"Pipeline complete in {total_elapsed:.1f}s")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
