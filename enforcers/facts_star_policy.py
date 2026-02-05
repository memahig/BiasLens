#!/usr/bin/env python3
"""
FILE: enforcers/facts_star_policy.py
VERSION: 0.1
LAST UPDATED: 2026-01-31
PURPOSE: Single source of truth for Fact Table Integrity star-cap policy.

Notes:
- This module contains normative star-cap logic for the Facts Layer.
- Both the report builder (producer) and enforcers should import this to prevent drift.
- Structural legality remains the responsibility of integrity_validator.py.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from schema_names import K


UNKNOWN_VERDICTS = {
    K.VERDICT_UNKNOWN,
    K.VERDICT_NOT_FOUND,
    K.VERDICT_INSUFFICIENT_EVIDENCE,
}


def compute_fact_table_max_star(facts: List[Dict[str, Any]]) -> int:
    """
    Computes the maximum allowed stars for facts_layer.fact_verification based on
    epistemic outcomes of checkable facts.

    Policy (current):
      - False-rate caps:
          false/total >= 0.40 => max_star = 1
          false/total >= 0.20 => max_star = 2
      - Unknown-rate caps (applied after false-rate caps):
          unknown/total >= 0.50 => cap at 2
          unknown/total >= 0.25 => cap at 3
          unknown > 0          => cap at 4

    If there are no checkable facts, returns 5 (no cap applied).
    """
    checkable = [
        f for f in facts
        if isinstance(f, dict) and f.get(K.CHECKABILITY) == K.CHECKABILITY_CHECKABLE
    ]
    if not checkable:
        return 5

    total = len(checkable)
    unknown = sum(1 for f in checkable if f.get(K.VERDICT) in UNKNOWN_VERDICTS)
    false = sum(1 for f in checkable if f.get(K.VERDICT) == K.VERDICT_FALSE)

    max_star = 5

    # False-rate caps (strongest)
    if false / total >= 0.40:
        max_star = 1
    elif false / total >= 0.20:
        max_star = 2

    # Unknown-rate caps
    if unknown / total >= 0.50:
        max_star = min(max_star, 2)
    elif unknown / total >= 0.25:
        max_star = min(max_star, 3)
    elif unknown > 0:
        max_star = min(max_star, 4)

    return max_star


def clamp_fact_table_stars(*, stars: int, facts: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Returns (final_stars, max_star) where final_stars is clamped to the policy max_star.
    """
    max_star = compute_fact_table_max_star(facts)
    final_stars = stars if stars <= max_star else max_star
    return final_stars, max_star
