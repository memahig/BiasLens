
#!/usr/bin/env python3
"""
FILE: rating_style.py
VERSION: 1.0
LAST UPDATED: 2026-02-03
PURPOSE:
Central rating semantics and rendering for BiasLens.

Responsibilities:
- Define locked star/color/meaning semantics.
- Provide deterministic score ↔ stars mapping.
- Render user-facing rating tokens consistently.

LOCKS:
- Star meanings are constitution-level and must remain aligned with
  enforcers/integrity_objects.STAR_MAP.
- Score→stars bands are locked unless a deliberate migration occurs.
- This file is the single source of truth for rating presentation.
"""


from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


# ─────────────────────────────────────────────────────────────
# rating_style.py
# PURPOSE:
# - Render user-facing rating tokens consistently:
#     dot + stars  (and optionally meaning)
# - Provide internal 0–100 scoring ↔ stars mapping.
#
# LOCKED SEMANTICS (user-facing):
#   1★ = 🔴 Severe integrity failures
#   2★ = 🟠 Major problems
#   3★ = 🟡 Mixed / variable
#   4★ = 🟢 Strong
#   5★ = 🔵 Exceptional
#
# SCORE→STARS BANDS (internal, locked for now):
#   0–19   -> 1★
#   20–39  -> 2★
#   40–59  -> 3★
#   60–79  -> 4★
#   80–100 -> 5★
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RatingStyle:
    star: str = "⭐"

    # Color circle by star count (locked)
    circle_map: Dict[int, str] = None  # type: ignore[assignment]

    # Meaning by star count (locked)
    meaning_map: Dict[int, str] = None  # type: ignore[assignment]

    # Render controls
    dot_first: bool = True          # user preference: dot before stars
    show_meaning: bool = False      # keep "hidden" by default; flip True if desired
    meaning_sep: str = " — "        # separator between rating token and meaning

    def __post_init__(self) -> None:
        if self.circle_map is None:
            object.__setattr__(
                self,
                "circle_map",
                {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"},
            )

        if self.meaning_map is None:
            object.__setattr__(
                self,
                "meaning_map",
                {
                    1: "Severe integrity failures",
                    2: "Major problems",
                    3: "Mixed / variable",
                    4: "Strong",
                    5: "Exceptional",
                },
            )


DEFAULT_STYLE = RatingStyle()


# ─────────────────────────────────────────────────────────────
# Core helpers
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
    Internal mapping (engine-facing). Bands are currently locked.

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
    """
    Stable midpoint score for a given star band.
    Ensures score_to_stars(midpoint) == stars.
    """
    st = clamp_rating(stars)
    return {1: 10, 2: 30, 3: 50, 4: 70, 5: 90}[st]


def stars_to_score_range(stars: int) -> tuple[int, int]:
    st = clamp_rating(stars)
    return {1: (0, 19), 2: (20, 39), 3: (40, 59), 4: (60, 79), 5: (80, 100)}[st]


def render_rating(
    rating: int,
    *,
    style: RatingStyle = DEFAULT_STYLE,
    meaning: Optional[str] = None,
    show_meaning: Optional[bool] = None,
) -> str:
    """
    Renders:
      - default:     🔴 ⭐
      - meaning on:  🔴 ⭐ — Severe integrity failures

    `meaning` overrides meaning_map if provided.
    """
    r = clamp_rating(rating)
    stars = style.star * r
    dot = style.circle_map.get(r, "")

    if style.dot_first:
        token = f"{dot} {stars}".strip()
    else:
        token = f"{stars} {dot}".strip()

    use_meaning = style.show_meaning if show_meaning is None else bool(show_meaning)
    if not use_meaning:
        return token

    m = (meaning or style.meaning_map.get(r, "")).strip()
    return f"{token}{style.meaning_sep}{m}".strip()
