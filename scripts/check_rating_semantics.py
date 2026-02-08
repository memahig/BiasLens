#!/usr/bin/env python3
"""
FILE: scripts/check_rating_semantics.py
VERSION: 1.0
LAST UPDATED: 2026-02-07
PURPOSE:
Fail-fast check that rating semantics have a single authority and enforcer derives from it.
"""

from constants.rating_semantics import INTEGRITY_STAR_MAP
from enforcers.integrity_objects import STAR_MAP


def main() -> None:
    for s in range(1, 6):
        assert STAR_MAP[s][0] == INTEGRITY_STAR_MAP[s]["label"]
        assert STAR_MAP[s][1] == INTEGRITY_STAR_MAP[s]["color"]
    print("OK: enforcer derived from single authority")


if __name__ == "__main__":
    main()
