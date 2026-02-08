#!/usr/bin/env python3
"""
FILE: constants/rating_semantics.py
VERSION: 1.0
LAST UPDATED: 2026-02-07
PURPOSE:
Single source of truth for BiasLens rating semantics.

This file is the ONLY authority for:
- Star -> (label, color) semantics (public-facing long-form labels)
- Dot emojis by star rating
- Score(0–100) -> stars mapping bands
- Rendering helpers (dot + stars + optional meaning)

Anti-drift rule:
- No other module may embed star meaning strings.
- Enforcers and renderers must import from here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


# ─────────────────────────────────────────────────────────────
# 🔒 CANONICAL PUBLIC LABELS + COLORS (SINGLE AUTHORITY)
# ─────────────────────────────────────────────────────────────

INTEGRITY_STAR_MAP: Dict[int, Dict[str, str]] = {
    1: {"color": "red",    "label": "Severe Integrity Failures"},
    2: {"color": "orange", "label": "Major Integrity Problems"},
    3: {"color": "yellow", "label": "Mixed / Variable Integrity"},
    4: {"color": "green",  "label": "Strong Information Integrity"},
    5: {"color": "blue",   "label": "Exceptional Information Integrity"},
}

# Dot emojis (presentation)
DOT_MAP: Dict[int, str] = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}

# Legacy-compatible map: {stars: (label, color)}
STAR_MAP_TUPLES: Dict[int, Tuple[str, str]] = {
    int(stars): (meta["label"], meta["color"])
    for stars, meta in INTEGRITY_STAR_MAP.items()
}


# ─────────────────────────────────────────────────────────────
# Score ↔ Stars (LOCKED BANDS)
# ─────────────────────────────────────────────────────────────

def clamp_rating(r: int) -> int:
    try:
        rr = int(r)
    except Exception:
        rr = 3
    return max(1, min(5, rr))


def clamp_score(score_0_100: int) -> int:
    try:
        s = int(score_0_100)
    except Exception:
        s = 50
    return max(0, min(100, s))


def score_to_stars(score_0_100: int) -> int:
    """
    Locked mapping:
      0–19   -> 1★
      20–39  -> 2★
      40–59  -> 3★
      60–79  -> 4★
      80–100 -> 5★
    """
    s = clamp_score(score_0_100)
    if s < 20:
        return 1
    if s < 40:
        return 2
    if s < 60:
        return 3
    if s < 80:
        return 4
    return 5


def stars_to_score_midpoint(stars: int) -> int:
    st = clamp_rating(stars)
    return {1: 10, 2: 30, 3: 50, 4: 70, 5: 90}[st]


def stars_to_score_range(stars: int) -> tuple[int, int]:
    st = clamp_rating(stars)
    return {1: (0, 19), 2: (20, 39), 3: (40, 59), 4: (60, 79), 5: (80, 100)}[st]


# ─────────────────────────────────────────────────────────────
# Rendering helpers
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RatingStyle:
    star: str = "⭐"
    dot_first: bool = True
    show_meaning: bool = False
    meaning_sep: str = " — "


DEFAULT_STYLE = RatingStyle()


def render_rating(
    rating: int,
    *,
    style: RatingStyle = DEFAULT_STYLE,
    meaning: Optional[str] = None,
    show_meaning: Optional[bool] = None,
) -> str:
    """
    Renders:
      - default:     🟠 ⭐⭐
      - meaning on:  🟠 ⭐⭐ — Major Integrity Problems
    """
    r = clamp_rating(rating)
    stars = style.star * r
    dot = DOT_MAP.get(r, "")

    token = f"{dot} {stars}".strip() if style.dot_first else f"{stars} {dot}".strip()

    use_meaning = style.show_meaning if show_meaning is None else bool(show_meaning)
    if not use_meaning:
        return token

    canonical = INTEGRITY_STAR_MAP.get(r, {}).get("label", "")
    m = (meaning or canonical).strip()
    return f"{token}{style.meaning_sep}{m}".strip()
