#!/usr/bin/env python3
"""Entry point for the market-style aware stock analyser.

Kept deliberately thin: all logic lives in the ``stocklab`` package so the
project stays testable and importable from notebooks.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from stocklab.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
