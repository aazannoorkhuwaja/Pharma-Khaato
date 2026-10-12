#!/usr/bin/env python3
"""Legacy sample-data entry point.

Sample seeding used to operate on whatever database Pharma-Khaato resolved,
which made an innocent developer/demo command capable of polluting real data.
The supported demo is now always isolated under ``.demo-data``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def seed_database():
    """Reset and seed the isolated demo database; never the production DB."""
    from scripts.demo_mode import reset_demo_storage, seed_demo_database

    reset_demo_storage()
    return seed_demo_database()


def main() -> int:
    from scripts.demo_mode import print_demo_card

    summary = seed_database()
    print_demo_card(summary)
    print("Sample data was written only to .demo-data; normal application data was not touched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
