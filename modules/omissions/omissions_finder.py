#!/usr/bin/env python3
"""
FILE: modules/omissions/omissions_finder.py
VERSION: 0.1
LAST UPDATED: 2026-02-10
PURPOSE:
Stage-1 omission perception. Produces INTERNAL-ONLY omission candidates stored under run_metadata.

Design locks:
- Candidates are hypotheses only ("possible_missing"), never reportable findings.
- Three omission strata are kept in separate candidate streams: STRUCTURAL, INFERENTIAL, INTERPRETIVE.
- This module does not compute reportability, severity, stars, or any public-facing integrity objects.
"""

from __future__ import annotations

from typing import Any, Dict, List

from schema_names import K

# Existing deterministic STRUCTURAL engine (v0.5) used as a subroutine.
from modules.omissions.omissions_engine import run_omissions_engine as _run_structural_engine
from evidence_bank_builder import add_evidence_span


def _ensure_run_metadata(out: Dict[str, Any]) -> Dict[str, Any]:
    rm = out.get(K.RUN_METADATA)
    if not isinstance(rm, dict):
        rm = {}
        out[K.RUN_METADATA] = rm
    return rm


def _mk_candidate(
    *,
    candidate_id: str,
    detector_id: str,
    detector_layer: str,          # "structural" | "inferential" | "interpretive"
    hypothesis_type: str,
    trigger_summary: str,
    expected_missing: str,
    impact_hypothesis: str,
    evidence_eids: List[str],
    evidence_roles: Dict[str, str],
    missing_parameter_types: List[str],
    scope_hint: str,
    stakes_hint: str,
) -> Dict[str, Any]:
    return {
        K.OMISSION_CANDIDATE_ID: candidate_id,
        K.DETECTOR_ID: detector_id,
        K.DETECTOR_LAYER: detector_layer,
        K.HYPOTHESIS_TYPE: hypothesis_type,
        K.TRIGGER_SUMMARY: trigger_summary,
        K.EXPECTED_MISSING: expected_missing,
        K.IMPACT_HYPOTHESIS: impact_hypothesis,
        K.EVIDENCE_EIDS: evidence_eids,
        K.EVIDENCE_ROLES: evidence_roles,
        K.MISSING_PARAMETER_TYPES: missing_parameter_types,
        K.SCOPE_HINT: scope_hint,
        K.STAKES_HINT: stakes_hint,
    }

def _map_structural_finding_to_operator_type(omission_type: str) -> str:
    t = (omission_type or "").lower()
    if "comparison" in t:
        return "comparison"
    if "time_window" in t or "trend" in t:
        return "trend_change"
    if "baseline" in t or "magnitude" in t:
        return "trend_change"
    if "causal" in t:
        return "causation"
    if "scope" in t or "general" in t:
        return "generalization_scope"
    return "unknown"

def _best_effort_find_span(full_text: str, snippet: str) -> Any:
    if not isinstance(full_text, str) or not full_text.strip():
        return None
    if not isinstance(snippet, str) or not snippet.strip():
        return None
    i = full_text.find(snippet)
    if i == -1:
        return None
    return i, i + len(snippet)


def _missing_params_for_detector(detector_id: str) -> List[str]:
    # Canonical 10-type vocabulary (stored as K.MPT_* strings)
    m = (detector_id or "").strip().upper()
    if m == "OMIT_001":
        return [K.MPT_BASELINE, K.MPT_DENOMINATOR, K.MPT_COMPARATOR_CLASS, K.MPT_ABSOLUTE_VALUE]
    if m == "OMIT_002":
        return [K.MPT_TIME_WINDOW]
    if m == "OMIT_003":
        return [K.MPT_POPULATION_SCOPE]
    if m == "OMIT_004":
        return [K.MPT_COMPARATOR_CLASS, K.MPT_BASELINE]
    if m == "OMIT_005":
        return [K.MPT_MECHANISM, K.MPT_EVIDENCE_TYPE]
    return []


def find_structural_candidates(out: Dict[str, Any]) -> List[Dict[str, Any]]:
    rm = _ensure_run_metadata(out)
    full_text = rm.get("input_text", "")
    source_title = ""
    source_url = None

    # Ensure evidence_bank exists (pass A should normally populate it)
    if not isinstance(out.get(K.EVIDENCE_BANK), list):
        out[K.EVIDENCE_BANK] = []

    evidence_bank: List[Dict[str, Any]] = out[K.EVIDENCE_BANK]  # type: ignore[assignment]

    res = _run_structural_engine(out)
    raw_findings = res.get("findings", [])
    candidates: List[Dict[str, Any]] = []

    for idx, f in enumerate(raw_findings, start=1):
        if not isinstance(f, dict):
            continue

        detector_id = str(f.get("omission_id") or "OMIT_000").strip()
        hypothesis_type = str(f.get("omission_type") or "unknown").strip()
        trigger_text = str(f.get("trigger_text") or "").strip()
        expected = str(f.get("expected_context") or "").strip()
        absence = str(f.get("absence_signal") or "").strip()
        impact = str(f.get("impact") or "").strip()

        if not trigger_text:
            continue

        # For now we can only anchor the trigger sentence (engine doesn't provide smaller spans yet)
        span = _best_effort_find_span(full_text, trigger_text)
        if span is None:
            # fail-closed: no anchor -> no candidate
            continue
        start_char, end_char = span

        trigger_eid = add_evidence_span(
            evidence_bank=evidence_bank,
            full_text=full_text,
            start_char=start_char,
            end_char=end_char,
            why_relevant=f"{detector_id} trigger",
            source_title=source_title,
            source_url=source_url,
        )
        if not trigger_eid:
            continue

        candidates.append(
            _mk_candidate(
                candidate_id=f"OMC_STRUCT_{detector_id}_{idx:03d}",
                detector_id=detector_id,
                detector_layer="structural",
                hypothesis_type=hypothesis_type,
                trigger_summary=trigger_text,
                expected_missing=expected,
                impact_hypothesis=impact,
                evidence_eids=[trigger_eid],
                evidence_roles={trigger_eid: K.EVID_ROLE_TRIGGER},
                missing_parameter_types=_missing_params_for_detector(detector_id),
                scope_hint=K.SCOPE_LOCAL,
                stakes_hint=K.STAKES_MODERATE,
            )
        )

    return candidates


def find_inferential_candidates(out: Dict[str, Any]) -> List[Dict[str, Any]]:
    # v0.1: stub (LLM expectation harvester will populate later)
    return []


def find_interpretive_candidates(out: Dict[str, Any]) -> List[Dict[str, Any]]:
    # v0.1: stub (LLM expectation harvester will populate later)
    return []


def run_omissions_finder(out: Dict[str, Any]) -> Dict[str, Any]:
    rm = _ensure_run_metadata(out)

    structural = find_structural_candidates(out)
    inferential = find_inferential_candidates(out)
    interpretive = find_interpretive_candidates(out)

    rm[K.OMISSION_CANDIDATES_STRUCTURAL] = structural
    rm[K.OMISSION_CANDIDATES_INFERENTIAL] = inferential
    rm[K.OMISSION_CANDIDATES_INTERPRETIVE] = interpretive
    rm[K.OMISSION_FINDER_NOTES] = {
        "stage": "finder_only",
        "counts": {
            "structural": len(structural),
            "inferential": len(inferential),
            "interpretive": len(interpretive),
        },
        "visibility": "internal_only",
    }

    return out
