
#!/usr/bin/env python3
"""
FILE: enforcers/integrity_objects.py
VERSION: 0.3
LAST UPDATED: 2026-02-02
PURPOSE:
Validate BiasLens integrity objects (normative contract enforcement).

Locks:
- Star/color/meaning semantics are constitution-level and enforced by STAR_MAP.
- For 1–4 stars: how_to_improve must be non-empty.
- For 5 stars: must include non-empty how_to_improve OR (optionally) maintenance_notes.

NEW (safe, optional):
- integrity objects MAY include "score_0_100" (int 0..100).
- If present, stars must match the default score bands unless you disable enforcement.

Notes:
- Unknown extra fields are allowed (ignored) to support telemetry/debug.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from schema_names import K


# 🔒 LOCKED: star/color/meaning semantics (project constitution)
# 1⭐ = 🔴 Severe integrity failures
# 2⭐⭐ = 🟠 Major problems
# 3⭐⭐⭐ = 🟡 Mixed / variable
# 4⭐⭐⭐⭐ = 🟢 Strong
# 5⭐⭐⭐⭐⭐ = 🔵 Exceptional
STAR_MAP = {
    1: ("Severe integrity failures", "red"),
    2: ("Major problems", "orange"),
    3: ("Mixed / variable", "yellow"),
    4: ("Strong", "green"),
    5: ("Exceptional", "blue"),
}

CONF_ALLOWED = {"low", "medium", "high"}

# Optional field name (literal key to avoid schema_names drift)
_SCORE_KEY = "score_0_100"

# If True: when score_0_100 is present, enforce that stars match score bands.
_ENFORCE_SCORE_TO_STARS = True


def _score_to_stars(score_0_100: int) -> int:
    """
    Default internal mapping (engine-facing), consistent with rating_style.py.

      0–19   -> 1★
      20–39  -> 2★
      40–59  -> 3★
      60–79  -> 4★
      80–100 -> 5★

    If you later tune these bands, tune them in BOTH places or centralize.
    """
    s = int(score_0_100)
    if s < 20:
        return 1
    if s < 40:
        return 2
    if s < 60:
        return 3
    if s < 80:
        return 4
    return 5


def enforce_integrity_objects(out: Dict[str, Any]) -> List[str]:
    errs: List[str] = []

    # Facts layer integrity object (required)
    facts_layer = out.get(K.FACTS_LAYER)
    if isinstance(facts_layer, dict):
        errs += _validate_integrity_object(
            facts_layer,
            K.FACT_TABLE_INTEGRITY,
            ctx="facts_layer.fact_table_integrity",
            stars5_allow_maintenance=True,
        )

    # Article layer integrity object (optional)
    article_layer = out.get(K.ARTICLE_LAYER)
    if article_layer is not None:
        if not isinstance(article_layer, dict):
            errs.append("article_layer must be an object if present")
        else:
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
            errs.append(f"{ctx} for 5 stars must include non-empty how_to_improve OR maintenance_notes")

    # ─────────────────────────────────────────────────────────
    # Optional internal score_0_100 (safe + hidden)
    # ─────────────────────────────────────────────────────────
    if _SCORE_KEY in obj:
        score = obj.get(_SCORE_KEY)

        if not isinstance(score, int):
            errs.append(f"{ctx}.{_SCORE_KEY} must be int 0..100 if present")
        else:
            if score < 0 or score > 100:
                errs.append(f"{ctx}.{_SCORE_KEY} must be within 0..100 if present")

            if _ENFORCE_SCORE_TO_STARS:
                exp_stars = _score_to_stars(score)
                if exp_stars != stars:
                    errs.append(
                        f"{ctx} stars mismatch vs {_SCORE_KEY} (score={score} implies {exp_stars}★)"
                    )

    return errs
