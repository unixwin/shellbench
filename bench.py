#!/usr/bin/env python3
"""benchsuite entry point. Usage: python3 bench.py {list,run,compare,gap} ..."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from benchsuite.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
