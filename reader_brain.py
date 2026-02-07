#!/usr/bin/env python3
"""
FILE: reader_brain.py
VERSION: 1.1
LAST UPDATED: 2026-02-07
PURPOSE:
Reader cognition engine that converts validated BiasLens findings
into human-impactful Reader In-Depth output.

Reads report pack.
Writes nothing upstream.
Pure rendering intelligence.

LOCKS:
- Reader layer is a TRANSLATION layer, not an analysis layer.
- Must NOT invent new findings or do new verification.
- Must render user-facing rating tokens as: dot + stars (via rating_style.render_rating).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rating_style import render_rating
from schema_names import K

from reader_phrasebook import (
    MechanismPhrase,
    get_mechanism,
    severity_label,
)

# ---------------------------------------------------------
# Internal Signal Object
# ---------------------------------------------------------

@dataclass
class Signal:
    key: str
    severity: str
    evidence: List[str]


# ---------------------------------------------------------
# Utilities
# ---------------------------------------------------------

SEVERITY_ORDER = {
    "high": 4,
    "elevated": 3,
    "moderate": 2,
    "low": 1,
}


def _d(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _l(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _s(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _clamp_stars(x: Any, default: int = 3) -> int:
    try:
        v = int(x)
    except Exception:
        v = default
    return max(1, min(5, v))


def _overall_integrity(pack: Dict[str, Any]) -> Dict[str, Any]:
    """
    Best-available integrity object for Reader surface.
    Preference:
      1) article_layer.article_integrity
      2) claim_registry.claim_grounding (fallback)
      3) facts_layer.fact_verification (fallback)
    """
    article = _d(pack.get(K.ARTICLE_LAYER))
    ai = _d(article.get(K.ARTICLE_INTEGRITY))
    if ai.get(K.STARS) is not None:
        return ai

    cr = _d(pack.get(K.CLAIM_REGISTRY))
    cg = _d(cr.get(K.claim_grounding))
    if cg.get(K.STARS) is not None:
        return cg

    facts = _d(pack.get(K.FACTS_LAYER))
    fv = _d(facts.get(K.fact_verification))
    if fv.get(K.STARS) is not None:
        return fv

    return {}


def _rating_token_and_label(pack: Dict[str, Any]) -> tuple[str, str, int]:
    oi = _overall_integrity(pack)
    stars = _clamp_stars(oi.get(K.STARS, 3))
    label = _s(oi.get(K.LABEL)) or "Unrated"
    token = render_rating(stars)
    return token, label, stars


def _article_type(pack: Dict[str, Any], signals: List[Signal]) -> str:
    """
    Conservative, deterministic classifier.
    This is NOT a moral judgment and must avoid political labels.
    Goal: set reader expectations (news vs analysis vs opinion).

    Rules (minimal, stable):
    - If it reads mostly like interpretation and integrity is <=3: "Opinion / Analysis"
    - If integrity >=4 and few signals: "Reporting / Analysis"
    - Default: "Analysis / Interpretive Journalism"
    """
    _, _, stars = _rating_token_and_label(pack)
    top_sev = signals[0].severity if signals else "low"

    if stars <= 3 and top_sev in {"moderate", "elevated", "high"}:
        return "Opinion / Analysis"

    if stars >= 4 and not signals:
        return "Reporting / Analysis"

    return "Analysis / Interpretive Journalism"


# ---------------------------------------------------------
# Signal Extraction
# ---------------------------------------------------------

def extract_signals(pack: Dict[str, Any]) -> List[Signal]:
    """
    Reads module outputs and converts them into reader signals.

    NOTE:
    - This is downstream, controlled judgment.
    - Must remain conservative: only emit signals when upstream modules ran
      or when integrity objects clearly indicate risk (e.g., low stars).
    """
    signals: List[Signal] = []

    article = _d(pack.get(K.ARTICLE_LAYER))
    claim_registry = _d(pack.get(K.CLAIM_REGISTRY))
    facts_layer = _d(pack.get(K.FACTS_LAYER))

    # ----------------------------------------
    # Headline / Presentation Integrity
    # ----------------------------------------
    pres = _d(article.get(K.PRESENTATION_INTEGRITY))
    if _s(pres.get(K.MODULE_STATUS) or pres.get(K.STATUS)).lower() == K.MODULE_RUN:
        sev = _normalize_severity(pres)
        if sev != "low":
            signals.append(
                Signal(
                    key="headline_body_delta",
                    severity=sev,
                    evidence=_safe_quotes(pres),
                )
            )

    # ----------------------------------------
    # Reality-Anchored Language (if present)
    # ----------------------------------------
    lang = _d(article.get("reality_anchored_language"))
    if _s(lang.get(K.MODULE_STATUS) or lang.get(K.STATUS)).lower() == K.MODULE_RUN:
        sev = _normalize_severity(lang)
        if sev in {"moderate", "elevated", "high"}:
            signals.append(
                Signal(
                    key="reality_anchored_language",
                    severity=sev,
                    evidence=_safe_quotes(lang),
                )
            )

    # ----------------------------------------
    # Claim Integrity (fallback reader signal)
    # ----------------------------------------
    ci = _d(claim_registry.get(K.claim_grounding))
    if ci:
        stars = _clamp_stars(ci.get(K.STARS, 3))
        if stars <= 2:
            signals.append(Signal(key="load_bearing_weak_claim", severity="high", evidence=[]))
        elif stars == 3:
            signals.append(Signal(key="verification_gap", severity="moderate", evidence=[]))

    # ----------------------------------------
    # Facts Layer (verification gap)
    # ----------------------------------------
    fact_table = _d(facts_layer.get(K.fact_verification))
    if fact_table:
        stars = _clamp_stars(fact_table.get(K.STARS, 3))
        if stars <= 2:
            signals.append(Signal(key="verification_gap", severity="elevated", evidence=[]))

    # ----------------------------------------
    # Systematic Omission (if present)
    # ----------------------------------------
    omission = _d(article.get("systematic_omission"))
    if _s(omission.get(K.MODULE_STATUS) or omission.get(K.STATUS)).lower() == K.MODULE_RUN:
        sev = _normalize_severity(omission)
        if sev in {"moderate", "elevated", "high"}:
            signals.append(Signal(key="omission_expected_context", severity=sev, evidence=[]))

    return _dedupe(signals)


# ---------------------------------------------------------
# Ranking
# ---------------------------------------------------------

def rank_signals(signals: List[Signal]) -> List[Signal]:
    return sorted(signals, key=lambda s: SEVERITY_ORDER.get(s.severity, 0), reverse=True)[:5]


# ---------------------------------------------------------
# Rendering (Public Entry)
# ---------------------------------------------------------

def build_reader_in_depth(pack: Dict[str, Any]) -> str:
    signals = rank_signals(extract_signals(pack))

    parts: List[str] = []
    parts.append(_reader_header(pack, signals))
    parts.append(_one_paragraph_summary(pack, signals))

    parts.append("\n## What kind of piece is this?\n")
    parts.append(_piece_classifier(pack, signals))

    parts.append("\n## How this can work on readers\n")
    if not signals:
        parts.append(
            "BiasLens did not detect major reader-risk mechanisms in this run. "
            "This does not guarantee the piece is flawless — only that no strong structural concerns surfaced."
        )
    else:
        for s in signals:
            mech = get_mechanism(s.key)
            if not mech:
                continue
            parts.append(_render_mechanism(mech, s))

    parts.append("\n## Unknowns and limits\n")
    parts.append(_unknowns(pack))

    parts.append("\n## How to raise the score\n")
    parts.append(_raise_score(pack))

    return "\n".join(parts)


# ---------------------------------------------------------
# Header / Summary / Classifier
# ---------------------------------------------------------

def _reader_header(pack: Dict[str, Any], signals: List[Signal]) -> str:
    token, label, _ = _rating_token_and_label(pack)
    a_type = _article_type(pack, signals)
    return (
        f"**Article Type: {a_type}**\n"
        f"**Overall Information Integrity: {token} ({label})**\n"
    )


def _one_paragraph_summary(pack: Dict[str, Any], signals: List[Signal]) -> str:
    token, label, _ = _rating_token_and_label(pack)

    if not signals:
        return (
            f"BiasLens found no major structural reader risks in this run. "
            f"Overall Information Integrity is **{token} ({label})**."
        )

    top = signals[0].severity
    return (
        f"BiasLens identified structural patterns that could shape reader interpretation. "
        f"The strongest concern level detected is **{severity_label(top)}**. "
        f"Overall Information Integrity is **{token} ({label})**."
    )


def _piece_classifier(pack: Dict[str, Any], signals: List[Signal]) -> str:
    _, _, stars = _rating_token_and_label(pack)
    top = signals[0].severity if signals else "low"

    if stars >= 4 and top == "low":
        return (
            "This reads as careful reporting or measured interpretation. "
            "The structure leaves room for uncertainty and does not heavily pressure the reader."
        )

    if stars >= 4:
        return (
            "This reads as generally careful analysis, with a few structural pressure points worth tracking."
        )

    if stars == 3:
        return (
            "This reads as mixed reporting and interpretation — informative, but requiring reader discretion."
        )

    return (
        "This piece leans heavily on interpretation or weakly supported claims. "
        "Readers should separate what is verified from what is asserted."
    )


# ---------------------------------------------------------
# Mechanism Renderer
# ---------------------------------------------------------

def _render_mechanism(mech: MechanismPhrase, signal: Signal) -> str:
    sev = severity_label(signal.severity)

    block = f"""
### {mech.title} — {sev}

**What it is:**  
{mech.what_it_is}

**Why it matters:**  
{mech.reader_effect}
"""

    if signal.evidence:
        quotes = "\n".join(f"> {q}" for q in signal.evidence[:2])
        block += f"\n**Seen in the article:**\n{quotes}\n"

    block += f"""
**To reduce this concern:**  
{mech.how_to_reduce}
"""
    return block


# ---------------------------------------------------------
# Limits / Improvements
# ---------------------------------------------------------

def _unknowns(pack: Dict[str, Any]) -> str:
    limits = _l(pack.get(K.DECLARED_LIMITS))
    if limits:
        return "BiasLens explicitly declares areas of uncertainty in this analysis."
    return (
        "No explicit limits were declared in this run. "
        "Responsible reading still assumes that unseen evidence could refine conclusions."
    )


def _raise_score(pack: Dict[str, Any]) -> str:
    oi = _overall_integrity(pack)
    improve = oi.get(K.HOW_TO_IMPROVE)

    if isinstance(improve, list) and improve:
        lines = []
        for x in improve:
            t = _s(x)
            if t:
                lines.append(f"- {t}")
        if lines:
            return "\n".join(lines)

    if isinstance(improve, str) and improve.strip():
        return improve.strip()

    return (
        "Raise Information Integrity by strengthening verification, narrowing claims, "
        "adding expected context, and aligning language with demonstrated evidence."
    )


# ---------------------------------------------------------
# Severity / Quotes / Dedupe
# ---------------------------------------------------------

def _normalize_severity(obj: Dict[str, Any]) -> str:
    stars = obj.get(K.STARS)
    if stars is None:
        return "moderate"

    st = _clamp_stars(stars, default=3)
    if st <= 2:
        return "high"
    if st == 3:
        return "moderate"
    # 4–5 star modules represent low concern
    return "low"


def _safe_quotes(obj: Dict[str, Any]) -> List[str]:
    quotes = obj.get("evidence_quotes")
    if isinstance(quotes, list):
        return [q for q in quotes[:2] if _s(q)]
    return []


def _dedupe(signals: List[Signal]) -> List[Signal]:
    seen: Dict[str, Signal] = {}
    for s in signals:
        if s.key not in seen:
            seen[s.key] = s
            continue
        if SEVERITY_ORDER.get(s.severity, 0) > SEVERITY_ORDER.get(seen[s.key].severity, 0):
            seen[s.key] = s
    return list(seen.values())
