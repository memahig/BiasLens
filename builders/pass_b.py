

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
- Runs Claim Evaluation Engine and attaches output under claim_registry.claim_evaluations.
- NEW: Builds claim_registry.claim_grounding from claim_evaluations.score_0_100 (stars derived).
"""

from __future__ import annotations
import re

from typing import Any, Dict, List
from datetime import datetime

from schema_names import K
from rating_style import score_to_stars, stars_to_score_midpoint
from modules.claims.claim_evaluator import run_claim_evaluator
from modules.timeline.timeline_engine import compute_timeline


# -----------------------------
# Timeline Consistency Sensor (MVP)
# -----------------------------

STATE_MISSING = ("missing", "abduct", "kidnap")
STATE_ALIVE = ("seen", "spotted", "shopping", "called", "spoke", "met")

def _classify_event_state(text: str):
    t = text.lower()

    if any(w in t for w in STATE_MISSING):
        return "missing"

    if any(w in t for w in STATE_ALIVE):
        return "alive"

    return None


def _detect_timeline_conflicts(claims):

    states = []

    for c in claims:
        txt = c.get(K.CLAIM_TEXT, c.get("claim_text", ""))
        state = _classify_event_state(txt)

        if state:
            states.append(state)

    if "missing" in states and "alive" in states:
        return {
            K.MODULE_STATUS: "run",
            "flag": "timeline_conflict_candidate",
            "confidence": "low",
            "note": "Article contains signals suggesting both disappearance and post-disappearance activity. Requires verification."
        }

    return {
        K.MODULE_STATUS: "run",
        "flag": None
    }



# Single optional field name (allowed by integrity_objects)
_SCORE_KEY = "score_0_100"


def _ensure_score_midpoint(integ: Dict[str, Any]) -> None:
    """
    If score_0_100 is missing, set it to a stable midpoint for the current stars.
    Does NOT change stars/label/color.
    """
    if not isinstance(integ, dict):
        return
    if _SCORE_KEY in integ:
        return
    stars = integ.get(K.STARS)
    if not isinstance(stars, int):
        return
    integ[_SCORE_KEY] = stars_to_score_midpoint(stars)


def _build_claim_grounding(*, claim_eval: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a schema-legal integrity object for claim-level integrity.

    Notes:
    - Deterministic
    - Uses score_0_100 -> stars mapping
    - Does NOT claim truth; this is structural-risk scoring only (text signals).
    """
    score = claim_eval.get(_SCORE_KEY, 50)
    try:
        score_int = int(score)
    except Exception:
        score_int = 50
    score_int = max(0, min(100, score_int))

    stars = score_to_stars(score_int)

    # Import here to avoid circular import hazards at module load time
    from enforcers.integrity_objects import STAR_MAP  # locked semantics

    label, color = STAR_MAP[stars]

    items = claim_eval.get(K.ITEMS, [])
    n_items = len(items) if isinstance(items, list) else 0

    rationale: List[str] = [
        "Claim Integrity is computed from deterministic structural signals in Pass B (text-only), not truth verification.",
        f"Claim Evaluation Engine emitted {n_items} issue item(s); score_0_100 summarizes severity-weighted structure risk.",
    ]

    how: List[str] = [
        "Add disambiguating nouns/names when using pronouns (they/it/this).",
        "Avoid absolute terms (always/never) unless you provide strong evidence and scope limits.",
        "When asserting causality, include mechanism + evidence and consider alternative explanations.",
        "Treat motive/intent language as a hypothesis; add direct supporting evidence or rephrase as uncertainty.",
    ]

    return {
        K.STARS: stars,
        K.LABEL: label,
        K.COLOR: color,
        K.CONFIDENCE: "low",  # MVP: text-signal engine; later can rise with retrieval/verification
        K.RATIONALE_BULLETS: rationale,
        K.HOW_TO_IMPROVE: how if stars <= 4 else ["Maintain: keep claims specific, qualified, and evidence-tethered."],
        K.GATING_FLAGS: [],
        _SCORE_KEY: score_int,
    }


def run_pass_b(pass_a_out: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(pass_a_out, dict):
        raise RuntimeError("Pass B contract violation: input must be a dict.")

    out = pass_a_out

    # 1) Attach midpoint scores to existing integrity objects (stable behavior)
    facts_layer = out.get(K.FACTS_LAYER)
    if isinstance(facts_layer, dict):
        integ = facts_layer.get(K.fact_verification)
        if isinstance(integ, dict):
            _ensure_score_midpoint(integ)

    article_layer = out.get(K.ARTICLE_LAYER)
    if isinstance(article_layer, dict):
        integ = article_layer.get(K.ARTICLE_INTEGRITY)
        if isinstance(integ, dict):
            _ensure_score_midpoint(integ)

    # 2) Run Claim Evaluation Engine and attach under claim_registry.claim_evaluations
    claim_module = run_claim_evaluator(out)

    cr = out.get(K.CLAIM_REGISTRY)
    if isinstance(cr, dict):
        cr[K.CLAIM_EVALUATIONS] = claim_module

        # 3) NEW: Claim Integrity object derived from claim_evaluations.score_0_100
        cr[K.claim_grounding] = _build_claim_grounding(claim_eval=claim_module)

    # ---- Timeline consistency (Article Layer) ----
    article_layer = out.get(K.ARTICLE_LAYER)

    if isinstance(article_layer, dict) and isinstance(cr, dict):
        claims = cr.get(K.CLAIMS, [])
        events, summary = compute_timeline(claims)
        article_layer[K.TIMELINE_EVENTS] = events
        article_layer[K.TIMELINE_SUMMARY] = summary
        article_layer[K.TIMELINE_CONSISTENCY] = {
            K.MODULE_STATUS: K.MODULE_RUN,
            K.NOTES: [
                "Timeline events extracted using weekday and clock anchors.",
                "Weekday anchors were normalized into an article-relative day_index (dominant-cluster rebasing).",
                "Time-only events were attached to the dominant anchored day (MVP heuristic).",
                "Earlier stray weekday mentions were pushed to the end to preserve the dominant chronology.",
                "This is heuristic chronology, not absolute datetime reconstruction.",
            ],
        }



    return out
