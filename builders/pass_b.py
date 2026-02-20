#!/usr/bin/env python3
"""
FILE: builders/pass_b.py
VERSION: 0.3
LAST UPDATED: 2026-02-19
PURPOSE: Pass B orchestrator (post-Pass-A) — extends a Pass A report pack.

ARCHITECTURE LOCK:
- Pass B MUST take a Pass A output dict and return a dict.
- Pass B MUST NOT re-scrape or re-run Pass A extraction.
- Pass B extends the existing schema output; it does not replace it.

Current behavior:
- WIRES timeline into article_layer:
    timeline_events
    timeline_summary
- Runs Claim Evaluation Engine and attaches output under claim_registry.claim_evaluations.
- Builds claim_registry.claim_grounding from claim_evaluations.score_0_100 (stars derived).
- Evaluates Headline–Body Delta (Presentation Integrity) under headline_body_delta.
- Adds optional internal numeric scoring (score_0_100) to integrity objects
  WITHOUT changing stars (uses star-band midpoint to preserve consistency).
- Runs Systematic Omission:
    Stage 1 (internal): omissions_finder writes candidates + breadcrumbs under run_metadata.*
    Stage 2 (public): omissions_engine writes deterministic findings under article_layer.systematic_omission
- Emits sockets only (timeline_consistency, framing_evidence_alignment). No extra intelligence.
"""

from __future__ import annotations

from typing import Any, Dict, List

from schema_names import K
from constants.rating_semantics import score_to_stars, stars_to_score_midpoint
from modules.claims.claim_evaluator import run_claim_evaluator
from modules.timeline.timeline_engine import compute_timeline
from modules.omissions.omissions_engine import run_omissions_engine
from modules.omissions.omissions_finder import run_omissions_finder
from modules.presentation.headline_body_delta import evaluate_headline_body_delta


# ---- robust key resolution (supports legacy lowercase + future uppercase) ----
_FACT_VERIFICATION_KEY = getattr(K, "FACT_VERIFICATION", getattr(K, "fact_verification", "fact_verification"))
_CLAIM_GROUNDING_KEY = getattr(K, "CLAIM_GROUNDING", getattr(K, "claim_grounding", "claim_grounding"))
_SCORE_KEY = getattr(K, "SCORE_0_100", "score_0_100")


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
        K.CONFIDENCE: "low",
        K.RATIONALE_BULLETS: rationale,
        K.HOW_TO_IMPROVE: how if stars <= 4 else ["Maintain: keep claims specific, qualified, and evidence-tethered."],
        K.GATING_FLAGS: [],
        _SCORE_KEY: score_int,
    }


def run_pass_b(pass_a_out: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(pass_a_out, dict):
        raise RuntimeError("Pass B contract violation: input must be a dict.")

    # NOTE: This mutates nested dicts in-place (same as before). If you ever want
    # a non-mutating Pass B, you’ll need a deep copy (expensive) or a structured copier.
    out = pass_a_out

    # Resolve core containers (do not create if missing; Pass A owns construction)
    cr = out.get(K.CLAIM_REGISTRY)
    article_layer = out.get(K.ARTICLE_LAYER)

    # 1) Timeline wiring → article_layer.*
    if isinstance(article_layer, dict) and isinstance(cr, dict):
        claims = cr.get(K.CLAIMS, [])
        if isinstance(claims, list):
            events, summary = compute_timeline(claims)
        else:
            events, summary = [], {
                "total_events": 0,
                "anchored_days": 0,
                "time_events": 0,
                "first_day": None,
                "last_day": None,
            }

        article_layer[K.TIMELINE_EVENTS] = events
        article_layer[K.TIMELINE_SUMMARY] = summary

    # 2) Claim Evaluation Engine → claim_registry.claim_evaluations + claim_grounding
    claim_module = run_claim_evaluator(out)
    if isinstance(cr, dict):
        cr[K.CLAIM_EVALUATIONS] = claim_module
        cr[_CLAIM_GROUNDING_KEY] = _build_claim_grounding(claim_eval=claim_module)

    # 3) Headline–Body Delta (Presentation Integrity) — evaluator (MVP)
    # Container is produced in Pass A; Pass B flips it to RUN and emits deterministic notes.
    out[K.HEADLINE_BODY_DELTA] = evaluate_headline_body_delta(out)

    # 4) Attach midpoint scores to existing integrity objects (stable behavior)
    facts_layer = out.get(K.FACTS_LAYER)
    if isinstance(facts_layer, dict):
        integ = facts_layer.get(_FACT_VERIFICATION_KEY)
        if isinstance(integ, dict):
            _ensure_score_midpoint(integ)

    if isinstance(article_layer, dict):
        integ = article_layer.get(K.ARTICLE_INTEGRITY)
        if isinstance(integ, dict):
            _ensure_score_midpoint(integ)

    # 5) Systematic Omission (MVP)
    # Stage 1: perception layer (internal candidates only)
    out = run_omissions_finder(out)

    # Stage 2: deterministic structural findings (public-facing)
    if isinstance(article_layer, dict):
        article_layer[K.SYSTEMATIC_OMISSION] = run_omissions_engine(out)

        # Socket only. No Phase 4 intelligence here.
        article_layer[K.TIMELINE_CONSISTENCY] = {
            K.MODULE_STATUS: K.MODULE_RUN,
            "notes": [
                "Timeline events extracted using weekday and clock anchors.",
                "Weekday anchors normalized into article-relative day_index (dominant-cluster rebasing).",
                "Time-only events attached to the dominant anchored day (MVP heuristic).",
                "This is heuristic chronology, not absolute datetime reconstruction.",
            ],
        }

        # 6) Framing–Evidence Alignment (socket only — no intelligence yet)
        article_layer[K.FRAMING_EVIDENCE_ALIGNMENT] = {
            K.MODULE_STATUS: K.MODULE_NOT_RUN,
            "notes": [
                "Socket present. This module will evaluate whether narrative framing exceeds the strength of presented evidence.",
                "No heuristics executed in this phase.",
            ],
        }

    return out