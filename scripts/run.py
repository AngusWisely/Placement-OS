#!/usr/bin/env python3
"""Run Placement OS from a source checkout."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from placement_os.server import run

if __name__ == "__main__":
    run()
