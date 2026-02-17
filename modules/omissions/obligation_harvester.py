#!/usr/bin/env python3
"""
FILE: modules/omissions/obligation_harvester.py
VERSION: 0.1
LAST UPDATED: 2026-02-15
PURPOSE:
Probabilistic omission perception (Pass A2) that harvests *semantic commitments → epistemic obligations*
and emits INTERNAL-ONLY omission candidate tickets (hypotheses), anchored to verbatim evidence spans.

CONSTITUTION / LOCKS:
- Candidates ONLY: this module never emits reportable findings, severity, stars, or intent inference.
- Omission is framed ONLY as "absence of expected context" (never motive/intent).
- Evidence governs: every candidate MUST be anchored to a verbatim trigger span in full_text and receive an EID.
  If anchoring fails -> candidate is dropped (fail-closed).
- This module does not assert external facts; it only extracts obligations implied by language in the text.
- Output is designed to be adaptable via K.EXTRACTED_SLOTS / K.CANDIDATE_NOTES without schema drift.

INTEGRATION TARGET:
- Called by modules/omissions/omissions_finder.py in find_inferential_candidates(out)
- Stores results under run_metadata.omission_candidates_inferential (internal only)

NOTE:
- This module is LLM-agnostic. You must supply an llm_json_call(prompt, user_text)->dict callable.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple
import json
import re

from schema_names import K
from evidence_bank_builder import add_evidence_span


# -----------------------------
# Internal config
# -----------------------------

# Stable detector id for this harvester channel (do not churn; supports regression).
_DETECTOR_ID = "OMIT_LLM_001"

# Candidate id prefix for inferential tickets
_CAND_PREFIX = "OMC_INFER"

# Hard cap to prevent runaway (MVP safety)
_MAX_CANDIDATES = 20

# Sentence boundary heuristic used only for prompt guidance (anchoring is verbatim substring).
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


# -----------------------------
# Helpers
# -----------------------------

def _ensure_run_metadata(out: Dict[str, Any]) -> Dict[str, Any]:
    rm = out.get(K.RUN_METADATA)
    if not isinstance(rm, dict):
        rm = {}
        out[K.RUN_METADATA] = rm
    return rm


def _get_full_text(out: Dict[str, Any]) -> str:
    rm = _ensure_run_metadata(out)
    t = rm.get("input_text")
    if isinstance(t, str) and t.strip():
        return t
    return ""


def _best_effort_source(out: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """
    Prefer source info from evidence_bank[0].source if present.
    report_stub currently embeds source per evidence item.
    """
    eb = out.get(K.EVIDENCE_BANK)
    if isinstance(eb, list) and eb:
        first = eb[0]
        if isinstance(first, dict):
            src = first.get(K.SOURCE)
            if isinstance(src, dict):
                title = src.get(K.TITLE)
                url = src.get(K.URL)
                return (title if isinstance(title, str) else "", url if isinstance(url, str) else None)
    return ("", None)


def _find_span(full_text: str, trigger_text: str) -> Optional[Tuple[int, int]]:
    if not isinstance(full_text, str) or not full_text.strip():
        return None
    if not isinstance(trigger_text, str) or not trigger_text.strip():
        return None
    i = full_text.find(trigger_text)
    if i == -1:
        return None
    return (i, i + len(trigger_text))


def _is_allowed_mpt(x: Any) -> bool:
    if not isinstance(x, str):
        return False
    allowed = {
        K.MPT_BASELINE,
        K.MPT_DENOMINATOR,
        K.MPT_COMPARATOR_CLASS,
        K.MPT_TIME_WINDOW,
        K.MPT_ABSOLUTE_VALUE,
        K.MPT_POPULATION_SCOPE,
        K.MPT_DEFINITION,
        K.MPT_MECHANISM,
        K.MPT_EVIDENCE_TYPE,
        K.MPT_SOURCE_PROVENANCE,
    }
    return x in allowed


def _safe_scope_hint(x: Any) -> str:
    if x == K.SCOPE_LOCAL:
        return K.SCOPE_LOCAL
    if x == K.SCOPE_PARAGRAPH:
        return K.SCOPE_PARAGRAPH
    if x == K.SCOPE_ARTICLE:
        return K.SCOPE_ARTICLE
    return K.SCOPE_LOCAL


def _safe_stakes_hint(x: Any) -> str:
    if x == K.STAKES_LOW:
        return K.STAKES_LOW
    if x == K.STAKES_MODERATE:
        return K.STAKES_MODERATE
    if x == K.STAKES_ELEVATED:
        return K.STAKES_ELEVATED
    if x == K.STAKES_HIGH:
        return K.STAKES_HIGH
    return K.STAKES_MODERATE


def _mk_ticket(
    *,
    candidate_id: str,
    hypothesis_type: str,
    trigger_summary: str,
    expected_missing: str,
    impact_hypothesis: str,
    evidence_eids: List[str],
    evidence_roles: Dict[str, str],
    missing_parameter_types: List[str],
    scope_hint: str,
    stakes_hint: str,
    detector_confidence: Optional[str] = None,
    extracted_slots: Optional[Dict[str, Any]] = None,
    candidate_notes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    t: Dict[str, Any] = {
        K.OMISSION_CANDIDATE_ID: candidate_id,
        K.DETECTOR_ID: _DETECTOR_ID,
        K.DETECTOR_LAYER: "inferential",
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
    if detector_confidence is not None:
        t[K.DETECTOR_CONFIDENCE] = detector_confidence
    if extracted_slots is not None:
        t[K.EXTRACTED_SLOTS] = extracted_slots
    if candidate_notes is not None:
        t[K.CANDIDATE_NOTES] = candidate_notes
    return t


# -----------------------------
# Prompt
# -----------------------------

def _harvester_system_prompt() -> str:
    # Keep this prompt narrow and enforce verbatim anchoring.
    # IMPORTANT: trigger_text must be copied EXACTLY from the provided article_text.
    allowed_mpts = [
        K.MPT_BASELINE,
        K.MPT_DENOMINATOR,
        K.MPT_COMPARATOR_CLASS,
        K.MPT_TIME_WINDOW,
        K.MPT_ABSOLUTE_VALUE,
        K.MPT_POPULATION_SCOPE,
        K.MPT_DEFINITION,
        K.MPT_MECHANISM,
        K.MPT_EVIDENCE_TYPE,
        K.MPT_SOURCE_PROVENANCE,
    ]
    allowed_scopes = [K.SCOPE_LOCAL, K.SCOPE_PARAGRAPH, K.SCOPE_ARTICLE]
    allowed_stakes = [K.STAKES_LOW, K.STAKES_MODERATE, K.STAKES_ELEVATED, K.STAKES_HIGH]

    return f"""
You are BiasLens Pass A2: Obligation Harvester (candidates-only).

Your job:
- Read the article text.
- Identify SEMANTIC COMMITMENTS (trend, causation, comparison, scope generalization, definitional, attribution/provenance).
- For each commitment, output a *candidate ticket* describing what expected context is missing.

Hard rules:
- Output JSON ONLY.
- NO intent/motive language.
- NO external facts.
- Every candidate MUST include trigger_text copied VERBATIM from the article text (exact substring).
- Prefer trigger_text that is a single sentence. If a paragraph-level trigger is necessary, keep it short but still verbatim.

Schema:
{{
  "candidates": [
    {{
      "hypothesis_type": "trend_change|causation|comparison|generalization_scope|definition|source_provenance|other",
      "trigger_text": "verbatim substring from the article",
      "expected_missing": "what parameters/context are expected but absent",
      "impact_hypothesis": "how absence could affect interpretation (non-intent framing)",
      "missing_parameter_types": {json.dumps(allowed_mpts)},
      "scope_hint": {json.dumps(allowed_scopes)},
      "stakes_hint": {json.dumps(allowed_stakes)},
      "detector_confidence": "low|medium|high",
      "extracted_slots": {{}},
      "candidate_notes": []
    }}
  ]
}}

Constraints:
- Return at most {_MAX_CANDIDATES} candidates.
- missing_parameter_types MUST be a list using ONLY the allowed vocabulary.
- If you are unsure whether something is missing, either omit the candidate or set detector_confidence="low" and explain briefly in candidate_notes.
""".strip()


def _harvester_user_content(article_text: str) -> str:
    # Include a light hint about sentence boundaries for the model (non-binding).
    sents = [s.strip() for s in _SENT_SPLIT.split(article_text.strip()) if s.strip()]
    example = sents[0] if sents else ""
    return f"""ARTICLE_TEXT:
{article_text}

Reminder: trigger_text must be an exact substring. Example sentence (for anchoring style only): {example}"""


# -----------------------------
# Public API
# -----------------------------

def harvest_obligation_tickets(
    *,
    out: Dict[str, Any],
    llm_json_call: Callable[[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Produce inferential omission candidate tickets (internal only), anchored to evidence spans.

    Inputs:
    - out: Pass A output dict (already contains evidence_bank; run_metadata.input_text is preferred)
    - llm_json_call: callable(system_prompt, user_content) -> dict (parsed JSON)

    Output:
    - List of candidate ticket dicts, schema-compatible with omission_candidates_* streams.
    """
    if not isinstance(out, dict):
        return []

    full_text = _get_full_text(out)
    if not full_text.strip():
        # fail-closed: cannot anchor without full text
        return []

    # Ensure evidence_bank exists; tickets will add new EIDs for trigger spans.
    if not isinstance(out.get(K.EVIDENCE_BANK), list):
        out[K.EVIDENCE_BANK] = []
    evidence_bank: List[Dict[str, Any]] = out[K.EVIDENCE_BANK]  # type: ignore[assignment]

    source_title, source_url = _best_effort_source(out)

    # Call model
    sys_prompt = _harvester_system_prompt()
    user_content = _harvester_user_content(full_text)
    try:
        raw = llm_json_call(sys_prompt, user_content)
    except Exception:
        return []

    if not isinstance(raw, dict):
        return []

    cand_list = raw.get("candidates", [])
    if not isinstance(cand_list, list):
        return []

    tickets: List[Dict[str, Any]] = []
    seq = 1

    for c in cand_list:
        if len(tickets) >= _MAX_CANDIDATES:
            break
        if not isinstance(c, dict):
            continue

        trigger_text = c.get("trigger_text")
        if not isinstance(trigger_text, str) or not trigger_text.strip():
            continue

        span = _find_span(full_text, trigger_text.strip())
        if span is None:
            # fail-closed: no verbatim anchor, drop
            continue
        start_char, end_char = span

        hyp = c.get("hypothesis_type")
        if not isinstance(hyp, str) or not hyp.strip():
            hyp = "other"

        expected_missing = c.get("expected_missing")
        if not isinstance(expected_missing, str):
            expected_missing = ""

        impact = c.get("impact_hypothesis")
        if not isinstance(impact, str):
            impact = ""

        mpts_in = c.get("missing_parameter_types", [])
        mpts: List[str] = []
        if isinstance(mpts_in, list):
            for x in mpts_in:
                if _is_allowed_mpt(x):
                    mpts.append(x)

        scope_hint = _safe_scope_hint(c.get("scope_hint"))
        stakes_hint = _safe_stakes_hint(c.get("stakes_hint"))

        det_conf = c.get("detector_confidence")
        if not isinstance(det_conf, str):
            det_conf = None
        else:
            det_conf = det_conf.strip().lower()
            if det_conf not in {"low", "medium", "high"}:
                det_conf = None

        extracted_slots = c.get("extracted_slots")
        if not isinstance(extracted_slots, dict):
            extracted_slots = None

        notes_in = c.get("candidate_notes")
        notes: Optional[List[str]] = None
        if isinstance(notes_in, list):
            notes = [str(x).strip() for x in notes_in if str(x).strip()]
        elif isinstance(notes_in, str) and notes_in.strip():
            notes = [notes_in.strip()]

        trigger_eid = add_evidence_span(
            evidence_bank=evidence_bank,
            full_text=full_text,
            start_char=start_char,
            end_char=end_char,
            why_relevant=f"{_DETECTOR_ID} trigger",
            source_title=source_title,
            source_url=source_url,
        )
        if not trigger_eid:
            continue

        tickets.append(
            _mk_ticket(
                candidate_id=f"{_CAND_PREFIX}_{_DETECTOR_ID}_{seq:03d}",
                hypothesis_type=hyp.strip(),
                trigger_summary=trigger_text.strip(),
                expected_missing=expected_missing.strip(),
                impact_hypothesis=impact.strip(),
                evidence_eids=[trigger_eid],
                evidence_roles={trigger_eid: K.EVID_ROLE_TRIGGER},
                missing_parameter_types=mpts,
                scope_hint=scope_hint,
                stakes_hint=stakes_hint,
                detector_confidence=det_conf,
                extracted_slots=extracted_slots,
                candidate_notes=notes,
            )
        )
        seq += 1

    return tickets