
# enforcers/integrity_objects.py
from __future__ import annotations

from typing import Any, Dict, List

from schema_names import K


STAR_MAP = {
    1: ("Very Poor Information Integrity", "red"),
    2: ("Poor Information Integrity", "orange"),
    3: ("Mixed / Variable Information Integrity", "yellow"),
    4: ("Good Information Integrity", "green"),
    5: ("Exemplary Information Integrity", "blue"),
}

CONF_ALLOWED = {"low", "medium", "high"}


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
            errs.append(
                f"{ctx} for 5 stars must include non-empty how_to_improve OR maintenance_notes"
            )

    return errs
