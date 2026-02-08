#!/usr/bin/env python3
"""
FILE: enforcers/integrity_objects.py
VERSION: 0.6
LAST UPDATED: 2026-02-07
PURPOSE:
Validate BiasLens integrity objects (normative contract enforcement).

Locks:
- Star/color/meaning semantics are constitution-level and enforced by STAR_MAP.
- For 1–4 stars: how_to_improve must be non-empty.
- For 5 stars: must include non-empty how_to_improve OR (optionally) maintenance_notes.

NEW (safe, optional):
- integrity objects MAY include K.SCORE_0_100 (int 0..100).
- If present, stars must match the default score bands unless you disable enforcement.

IMPORTANT (2026-02-07 LOCK):
- Public-facing star labels MUST be long-form (e.g., "Major Integrity Problems").
- STAR_MAP is DERIVED from constants.rating_semantics (single source of truth).
  (single source of truth). Do not embed labels here.
"""

from __future__ import annotations

from typing import Any, Dict, List

from schema_names import K
from constants.rating_semantics import STAR_MAP_TUPLES, score_to_stars


# ─────────────────────────────────────────────────────────────
# 🔒 LOCKED: star/color/meaning semantics (project constitution)
# Derived from canonical long-form INTEGRITY_STAR_MAP.
# STAR_MAP remains for legacy compatibility: {stars: (label, color)}
# ─────────────────────────────────────────────────────────────

STAR_MAP = STAR_MAP_TUPLES

CONF_ALLOWED = {"low", "medium", "high"}

# Optional field name (literal key to avoid schema_names drift)
_SCORE_KEY = K.SCORE_0_100

# If True: when score_0_100 is present, enforce that stars match score bands.
_ENFORCE_SCORE_TO_STARS = True


def enforce_integrity_objects(out: Dict[str, Any]) -> List[str]:
    errs: List[str] = []

    # Facts layer integrity object (required when facts_layer exists)
    facts_layer = out.get(K.FACTS_LAYER)
    if isinstance(facts_layer, dict):
        errs += _validate_integrity_object(
            facts_layer,
            K.fact_verification,
            ctx="facts_layer.fact_verification",
            stars5_allow_maintenance=True,
        )

    # Claim registry integrity object (required when claim_registry exists)
    claim_registry = out.get(K.CLAIM_REGISTRY)
    if isinstance(claim_registry, dict):
        errs += _validate_integrity_object(
            claim_registry,
            K.claim_grounding,
            ctx="claim_registry.claim_grounding",
            stars5_allow_maintenance=True,
        )

    # Article layer integrity object (optional)
    article_layer = out.get(K.ARTICLE_LAYER)
    if article_layer is not None:
        if not isinstance(article_layer, dict):
            errs.append("article_layer must be an object if present")
        else:
            # article_integrity is optional (some MVP runs may not emit it yet)
            if K.ARTICLE_INTEGRITY in article_layer:
                errs += _validate_integrity_object(
                    article_layer,
                    K.ARTICLE_INTEGRITY,
                    ctx="article_layer.article_integrity",
                    stars5_allow_maintenance=True,
                )

    return errs


def _validate_integrity_object(
    container: Dict[str, Any],
    key: str,
    ctx: str,
    stars5_allow_maintenance: bool,
) -> List[str]:
    errs: List[str] = []
    obj = container.get(key)

    if not isinstance(obj, dict):
        return [f"{ctx} missing or not an object"]

    required = [
        K.STARS,
        K.LABEL,
        K.COLOR,
        K.CONFIDENCE,
        K.RATIONALE_BULLETS,
        K.GATING_FLAGS,
    ]
    for k in required:
        if k not in obj:
            errs.append(f"{ctx}.{k} missing")

    stars = obj.get(K.STARS)
    if not isinstance(stars, int) or stars not in STAR_MAP:
        errs.append(f"{ctx}.{K.STARS} must be int 1–5")
        return errs

    exp_label, exp_color = STAR_MAP[stars]
    if obj.get(K.LABEL) != exp_label:
        errs.append(f"{ctx}.{K.LABEL} mismatch (expected {exp_label})")
    if obj.get(K.COLOR) != exp_color:
        errs.append(f"{ctx}.{K.COLOR} mismatch (expected {exp_color})")

    conf = obj.get(K.CONFIDENCE)
    if conf not in CONF_ALLOWED:
        errs.append(f"{ctx}.{K.CONFIDENCE} must be one of {sorted(CONF_ALLOWED)}")

    rb = obj.get(K.RATIONALE_BULLETS)
    if not isinstance(rb, list) or len(rb) == 0:
        errs.append(f"{ctx}.{K.RATIONALE_BULLETS} must be a non-empty list")

    how = obj.get(K.HOW_TO_IMPROVE)
    maint = obj.get(K.MAINTENANCE_NOTES)

    if stars <= 4:
        if not isinstance(how, list) or len(how) == 0:
            errs.append(f"{ctx}.{K.HOW_TO_IMPROVE} must be non-empty for stars <= 4")
    else:
        how_ok = isinstance(how, list) and len(how) > 0
        maint_ok = isinstance(maint, list) and len(maint) > 0
        if not (how_ok or (stars5_allow_maintenance and maint_ok)):
            errs.append(
                f"{ctx} for 5 stars must include non-empty how_to_improve OR maintenance_notes"
            )

    # Optional internal score_0_100 (safe + hidden)
    if _SCORE_KEY in obj:
        score = obj.get(_SCORE_KEY)

        if not isinstance(score, int):
            errs.append(f"{ctx}.{_SCORE_KEY} must be int 0..100 if present")
        else:
            if score < 0 or score > 100:
                errs.append(f"{ctx}.{_SCORE_KEY} must be within 0..100 if present")

            if _ENFORCE_SCORE_TO_STARS:
                exp_stars = score_to_stars(score)
                if exp_stars != stars:
                    errs.append(
                        f"{ctx} stars mismatch vs {_SCORE_KEY} (score={score} implies {exp_stars}★)"
                    )

    return errs
