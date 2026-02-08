#!/usr/bin/env python3
"""
FILE: rating_style.py
VERSION: 1.2
LAST UPDATED: 2026-02-07
PURPOSE:
Legacy shim. Canonical rating semantics now live in constants/rating_semantics.py
"""

from constants.rating_semantics import (
    RatingStyle,
    DEFAULT_STYLE,
    clamp_rating,
    clamp_score,
    score_to_stars,
    stars_to_score_midpoint,
    stars_to_score_range,
    render_rating,
)
