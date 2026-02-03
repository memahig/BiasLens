
#!/usr/bin/env python3
"""
FILE: scoring_policy.py
VERSION: 0.2
LAST UPDATED: 2026-02-03
PURPOSE:
Single source of truth for BiasLens internal numeric scoring aggregation (0–100).

This file does NOT compute scores.
It only:
- defines the scoring *constitution* (module weights)
- aggregates module scores deterministically
- declares what is required vs optional (for future gates)

Design:
- Module scores are emitted by Pass B modules as int 0..100.
- This policy aggregates whatever ran.
- Missing modules are handled explicitly (no silent assumptions).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from rating_style import clamp_score


@dataclass(frozen=True)
class ModuleSpec:
    weight: float
    required: bool = False


@dataclass(frozen=True)
class ModuleScore:
    score_0_100: int
    status: str  # "run" | "not_run"


# ─────────────────────────────────────────────────────────────
# Scoring constitution (edit deliberately)
# ─────────────────────────────────────────────────────────────
MODULES: Dict[str, ModuleSpec] = {
    # Facts / Reality Alignment
    "facts_layer": ModuleSpec(weight=0.30, required=False),

    # Claim evaluation (support, tethering, attribution discipline, etc.)
    "claims_layer": ModuleSpec(weight=0.35, required=False),

    # Argument reconstruction + integrity
    "argument_layer": ModuleSpec(weight=0.20, required=False),

    # Headline/body delta + presentation integrity
    "presentation_layer": ModuleSpec(weight=0.15, required=False),
}


def _validate_modules(mods: Dict[str, ModuleSpec] = MODULES) -> None:
    total = sum(float(m.weight) for m in mods.values())
    if abs(total - 1.0) > 1e-6:
        raise RuntimeError(f"Scoring policy invalid: weights sum to {total}, expected 1.0")


def aggregate_score(
    scores: Dict[str, ModuleScore],
    *,
    missing_policy: str = "renormalize",  # "renormalize" | "penalize"
) -> Tuple[int, Dict[str, str], Dict[str, str]]:
    """
    Returns:
      (final_score_0_100,
       status_notes_by_module,
       required_notes_by_module)

    missing_policy:
      - renormalize: average over modules that ran
      - penalize: not_run contributes 0 at full weight (harsh)

    required_notes_by_module:
      - "required_missing" if required=True and status != "run"
      - else ""
    """
    _validate_modules(MODULES)

    if missing_policy not in {"renormalize", "penalize"}:
        missing_policy = "renormalize"

    status_notes: Dict[str, str] = {}
    required_notes: Dict[str, str] = {}

    num = 0.0
    den = 0.0

    for name, spec in MODULES.items():
        ms = scores.get(name)

        if ms is None:
            status = "missing"
            score = None
        else:
            status = ms.status if ms.status in {"run", "not_run"} else "not_run"
            score = clamp_score(ms.score_0_100)

        status_notes[name] = status

        if spec.required and status != "run":
            required_notes[name] = "required_missing"
        else:
            required_notes[name] = ""

        if status == "run" and score is not None:
            num += spec.weight * score
            den += spec.weight
        else:
            if missing_policy == "penalize":
                den += spec.weight  # contributes 0

    if den <= 0.0:
        # Nothing ran; neutral midpoint but explicitly marked by notes upstream.
        return (50, status_notes, required_notes)

    final = int(round(num / den))
    return (clamp_score(final), status_notes, required_notes)
