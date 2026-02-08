

#!/usr/bin/env python3
"""
FILE: scoring_policy.py
VERSION: 0.2
LAST UPDATED: 2026-02-03
PURPOSE:
Deterministic scoring policy for Claim Evaluation Engine.

Design intent:
- Keep stars as the public-friendly "UI token" (1–5).
- Maintain a more granular internal score_0_100 for tuning and debugging.
- Deterministic, stable, no randomness.

Policy (v0.2):
- Start at 100.
- Apply severity-weighted deductions per flagged item.
- Normalize by claim count *gently* (so longer texts aren't punished too hard).
- Clamp to 0..100.

Notes:
- This is NOT a truth score. It is a structural-risk score derived from text signals.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from constants.rating_semantics import score_to_stars


from schema_names import K

# Severity → deduction points per item
SEVERITY_WEIGHTS: Dict[str, int] = {
    K.SEV_LOW: 4,
    K.SEV_MODERATE: 10,
    K.SEV_ELEVATED: 18,
    K.SEV_HIGH: 28,
}

# Optional: issue-specific additional weights (can be tuned later)
# e.g., if "intent_inference_language" should cost more than a generic elevated.
ISSUE_WEIGHTS: Dict[str, int] = {
    # "intent_inference_language": 4,  # example: add +4 points to that issue
}


def _s(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def score_claim_evaluations(
    *,
    items: List[Dict[str, Any]],
    claims: List[Dict[str, Any]],
) -> Tuple[int, List[str]]:
    """
    Deterministic structural scoring for the claim evaluation module.

    Inputs:
      items: claim evaluation flags (each includes 'severity', 'issue_type', etc.)
      claims: extracted claims list

    Returns:
      (score_0_100, notes)
    """
    notes: List[str] = []

    # --- 1) base score
    base = 100

    # --- 2) total deduction from items
    deduction = 0
    sev_counts: Dict[str, int] = {}
    issue_counts: Dict[str, int] = {}

    for it in items:
        sev = _s(it.get(K.SEVERITY)).lower() or K.SEV_LOW
        issue = _s(it.get(K.ISSUE_TYPE)).lower()

        sev_counts[sev] = sev_counts.get(sev, 0) + 1
        if issue:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        w = SEVERITY_WEIGHTS.get(sev, SEVERITY_WEIGHTS[K.SEV_LOW])
        w += ISSUE_WEIGHTS.get(issue, 0)
        deduction += w

    # --- 3) gentle normalization by number of claims
    # Rationale: more claims = more opportunities for flags; normalize slowly.
    #   1 claim -> factor 1.00
    #   2 claims -> 1.10
    #   5 claims -> 1.40
    #  10 claims -> 1.70
    n_claims = max(1, len(claims))
    norm_factor = 1.0 + min(0.7, 0.1 * (n_claims - 1))
    scaled_deduction = int(round(deduction / norm_factor))

    # --- 4) final score
    score = base - scaled_deduction
    score = max(0, min(100, int(score)))

    # --- notes for scholar/debug
    notes.append("Score is deterministic: 100 minus severity-weighted deductions (gently normalized by claim count).")
    notes.append(f"claims={len(claims)} items={len(items)} raw_deduction={deduction} norm_factor={norm_factor:.2f} scaled_deduction={scaled_deduction}")
    if sev_counts:
        sev_summary = ", ".join(f"{k}={sev_counts[k]}" for k in sorted(sev_counts.keys()))
        notes.append(f"severity_counts: {sev_summary}")
    if issue_counts:
        top = sorted(issue_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
        issue_summary = ", ".join(f"{k}={v}" for k, v in top)
        notes.append(f"top_issue_types: {issue_summary}")

    # Sanity note: star band implied by score
    notes.append(f"score_band_stars={score_to_stars(score)}")

    return score, notes
