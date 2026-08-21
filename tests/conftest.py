"""Pytest bootstrap.

Puts the pure-Python modules under src/silver and scripts on the import path so
they can be unit-tested without a Spark session or the dlt runtime. Only modules
that do not import pyspark/dlt at module load time are safe to import here.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for rel in ("src/silver", "scripts"):
    path = str(ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)
