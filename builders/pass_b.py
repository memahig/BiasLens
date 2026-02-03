#!/usr/bin/env python3
"""
FILE: builders/pass_b.py
PURPOSE: Pass B orchestrator (post-Pass-A) — upgrades/extends a Pass A report pack.

ARCHITECTURE LOCK:
- Pass B MUST take a Pass A output dict and return a dict.
- Pass B MUST NOT re-scrape or re-run Pass A extraction.
- Pass B extends the existing schema output; it does not replace it.

Current behavior:
- Adds optional internal numeric scoring (score_0_100) to integrity objects
  WITHOUT changing stars (uses star-band midpoint to preserve consistency).
"""

from __future__ import annotations

from typing import Any, Dict

from schema_names import K
from rating_style import stars_to_score_midpoint

_SCORE_KEY = "score_0_100"


def _ensure_score_midpoint(integ: Dict[str, Any]) -> None:
    """
    If score_0_100 is missing, set it to a stable midpoint for the current stars.
    Does NOT change stars/label/color (Pass A remains source of public rating).
    """
    if not isinstance(integ, dict):
        return
    if _SCORE_KEY in integ:
        return
    stars = integ.get(K.STARS)
    if not isinstance(stars, int):
        return
    integ[_SCORE_KEY] = stars_to_score_midpoint(stars)


def run_pass_b(pass_a_out: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(pass_a_out, dict):
        raise RuntimeError("Pass B contract violation: input must be a dict.")

    out = pass_a_out

    facts_layer = out.get(K.FACTS_LAYER)
    if isinstance(facts_layer, dict):
        integ = facts_layer.get(K.FACT_TABLE_INTEGRITY)
        if isinstance(integ, dict):
            _ensure_score_midpoint(integ)

    article_layer = out.get(K.ARTICLE_LAYER)
    if isinstance(article_layer, dict):
        integ = article_layer.get(K.ARTICLE_INTEGRITY)
        if isinstance(integ, dict):
            _ensure_score_midpoint(integ)

    return out
