"""The print-volume scripts import their helpers as top-level modules."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
