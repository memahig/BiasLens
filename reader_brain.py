
#!/usr/bin/env python3
"""
FILE: reader_brain.py
VERSION: 1.0
LAST UPDATED: 2026-02-04
PURPOSE:
Reader cognition engine that converts validated BiasLens findings
into human-impactful Reader In-Depth output.

Reads report pack.
Writes nothing upstream.
Pure rendering intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

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
# Signal Extraction
# ---------------------------------------------------------

def extract_signals(pack: Dict[str, Any]) -> List[Signal]:
    """
    Reads module outputs and converts them into reader signals.

    This is intentionally heuristic.
    Reader Brain is allowed controlled judgment.
    """

    signals: List[Signal] = []

    article = pack.get("article_layer", {})
    claim_registry = pack.get("claim_registry", {})
    facts_layer = pack.get("facts_layer", {})

    # ----------------------------------------
    # Headline / Presentation
    # ----------------------------------------

    pres = article.get("presentation_integrity", {})
    if pres.get("status") == "run":
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
    # Reality Anchored Language
    # ----------------------------------------

    lang = article.get("reality_anchored_language", {})
    if lang.get("status") == "run":
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
    # Claim Integrity
    # ----------------------------------------

    ci = claim_registry.get("claim_grounding", {})
    if ci:
        stars = ci.get("stars", 3)

        if stars <= 2:
            signals.append(
                Signal(
                    key="load_bearing_weak_claim",
                    severity="high",
                    evidence=[],
                )
            )

        elif stars == 3:
            signals.append(
                Signal(
                    key="verification_gap",
                    severity="moderate",
                    evidence=[],
                )
            )

    # ----------------------------------------
    # Facts Layer
    # ----------------------------------------

    fact_table = facts_layer.get("fact_verification", {})
    if fact_table:
        stars = fact_table.get("stars", 3)

        if stars <= 2:
            signals.append(
                Signal(
                    key="verification_gap",
                    severity="elevated",
                    evidence=[],
                )
            )

    # ----------------------------------------
    # Omission
    # ----------------------------------------

    omission = article.get("systematic_omission", {})
    if omission.get("status") == "run":
        sev = _normalize_severity(omission)
        if sev in {"moderate", "elevated", "high"}:
            signals.append(
                Signal(
                    key="omission_expected_context",
                    severity=sev,
                    evidence=[],
                )
            )

    return _dedupe(signals)


# ---------------------------------------------------------
# Ranking
# ---------------------------------------------------------

SEVERITY_ORDER = {
    "high": 4,
    "elevated": 3,
    "moderate": 2,
    "low": 1,
}


def rank_signals(signals: List[Signal]) -> List[Signal]:

    return sorted(
        signals,
        key=lambda s: SEVERITY_ORDER.get(s.severity, 0),
        reverse=True,
    )[:5]  # cap for readability


# ---------------------------------------------------------
# Rendering
# ---------------------------------------------------------

def build_reader_in_depth(pack: Dict[str, Any]) -> str:

    signals = rank_signals(extract_signals(pack))

    parts: List[str] = []

    parts.append(_one_paragraph_summary(pack, signals))
    parts.append("\n## What kind of piece is this?\n")
    parts.append(_piece_classifier(pack))

    parts.append("\n## How this can work on readers\n")

    if not signals:
        parts.append(
            "BiasLens did not detect major reader-risk mechanisms in this run. "
            "This does not guarantee the article is flawless — only that no strong structural concerns surfaced."
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
# Helpers
# ---------------------------------------------------------

def _one_paragraph_summary(pack, signals):

    rating = pack.get("quality_rating", {})
    label = rating.get("label", "Unrated")

    if not signals:
        return (
            f"BiasLens found no major structural reader risks in this run. "
            f"Overall Information Integrity appears **{label}**, though all journalism benefits from healthy skepticism."
        )

    top = signals[0].severity

    return (
        f"BiasLens identifies structural patterns that could shape reader interpretation. "
        f"The strongest concern level detected is **{severity_label(top)}**. "
        f"Overall Information Integrity is rated **{label}**."
    )


def _piece_classifier(pack):

    stars = pack.get("quality_rating", {}).get("stars", 3)

    if stars >= 4:
        return (
            "This reads as primarily evidence-forward reporting. "
            "Claims appear reasonably grounded, though readers should still track scope and sourcing."
        )

    if stars == 3:
        return (
            "This reads as mixed reporting and interpretation — informative, but requiring reader discretion."
        )

    return (
        "This piece leans heavily on interpretation or weakly supported claims. "
        "Readers should separate what is verified from what is asserted."
    )


def _unknowns(pack):

    limits = pack.get("declared_limits")

    if limits:
        return "BiasLens explicitly declares areas of uncertainty in this analysis."

    return (
        "No explicit limits were declared in this run. "
        "Responsible reading still assumes that unseen evidence could refine conclusions."
    )


def _raise_score(pack):

    improve = pack.get("quality_rating", {}).get("how_to_improve")

    if improve:
        return improve

    return (
        "Raise Information Integrity by strengthening verification, narrowing claims, "
        "adding expected context, and aligning language with demonstrated evidence."
    )


def _normalize_severity(obj):

    stars = obj.get("stars")

    if stars is None:
        return "moderate"

    if stars <= 2:
        return "high"
    if stars == 3:
        return "moderate"
    if stars == 4:
        return "low"

    return "low"


def _safe_quotes(obj):

    quotes = obj.get("evidence_quotes")

    if isinstance(quotes, list):
        return quotes[:2]

    return []


def _dedupe(signals: List[Signal]) -> List[Signal]:

    seen = {}
    for s in signals:
        if s.key not in seen or SEVERITY_ORDER[s.severity] > SEVERITY_ORDER[seen[s.key].severity]:
            seen[s.key] = s

    return list(seen.values())
