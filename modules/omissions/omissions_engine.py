#!/usr/bin/env python3
"""
FILE: modules/omissions/omissions_engine.py
VERSION: 0.1
LAST UPDATED: 2026-02-08
PURPOSE:
Detect *absence of expected context* (systematic omission) using text-only signals.

Safety/Locks:
- This module NEVER infers intent or wrongdoing.
- Findings are framed strictly as "missing expected context" and "possible interpretive impact."
- Text-only MVP: no external world knowledge, no fact claims beyond the provided text.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

from schema_names import K


_MAGNITUDE_WORDS = re.compile(
    r"\b(surge|spike|soar|skyrocket|record|sharp|sharply|dramatic|dramatically|plunge|plumm(et|eted)|explod(e|ed))\b",
    re.IGNORECASE,
)

_TREND_WORDS = re.compile(
    r"\b(increas(e|ing|ed)|decreas(e|ing|ed)|ris(e|ing|en)|fall(ing|en)|climb(ing|ed)|declin(e|ing|ed)|trend(ing)?)\b",
    re.IGNORECASE,
)

_HAS_NUMBER = re.compile(r"\b\d+(\.\d+)?%?\b")
_HAS_TIME_HINT = re.compile(
    r"\b(today|yesterday|tomorrow|this week|last week|this month|last month|this year|last year|over the past|in the past|since)\b",
    re.IGNORECASE,
)

# very light date pattern: 2024, 2025, 2026, or Month Name
_HAS_DATE = re.compile(
    r"\b(20\d{2})\b|\b(Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)\b",
    re.IGNORECASE,
)


def _extract_text_blob(out: Dict[str, Any]) -> str:
    """
    Prefer report text if available; otherwise fall back to concatenating evidence quotes.
    This avoids requiring any new schema fields in MVP.
    """
    parts: List[str] = []

    # If you store headline/body elsewhere later, add it here.
    eb = out.get(K.EVIDENCE_BANK)
    if isinstance(eb, list):
        for item in eb:
            if isinstance(item, dict):
                q = item.get(K.QUOTE)
                if isinstance(q, str) and q.strip():
                    parts.append(q.strip())

    return "\n".join(parts).strip()


def _make_finding(*, omission_id: str, omission_type: str, trigger_text: str,
                  expected_context: str, absence_signal: str, impact: str, severity: str) -> Dict[str, Any]:
    return {
        "omission_id": omission_id,
        "omission_type": omission_type,
        "trigger_text": trigger_text,
        "expected_context": expected_context,
        "absence_signal": absence_signal,
        "impact": impact,
        "severity": severity,
    }


def run_omissions_engine(out: Dict[str, Any]) -> Dict[str, Any]:
    text = _extract_text_blob(out)
    findings: List[Dict[str, Any]] = []

    if not text:
        return {
            K.MODULE_STATUS: K.MODULE_RUN,
            "findings": [],
            "notes": ["No text/evidence quotes available for omission scan."],
        }

    # Baseline/denominator missing detector:
    # Trigger: magnitude words near a clause; absence: no numbers nearby.
    if _MAGNITUDE_WORDS.search(text) and not _HAS_NUMBER.search(text):
        # Grab a small trigger snippet (first match line)
        m = _MAGNITUDE_WORDS.search(text)
        snippet = text[max(0, m.start() - 60): min(len(text), m.end() + 60)].replace("\n", " ")
        findings.append(_make_finding(
            omission_id="OMIT_001",
            omission_type="baseline_missing",
            trigger_text=snippet,
            expected_context="Baseline/denominator (prior value, comparison point, or magnitude) for the claimed change.",
            absence_signal="Magnitude language present but no numeric baseline/denominator detected in extracted text.",
            impact="Without a baseline, readers cannot judge how large or unusual the change is; framing may overstate significance.",
            severity=K.SEV_MODERATE,
        ))

    # Time window missing detector:
    # Trigger: trend words; absence: no dates/time-hints nearby (MVP uses coarse check).
    if _TREND_WORDS.search(text) and not (_HAS_TIME_HINT.search(text) or _HAS_DATE.search(text)):
        m = _TREND_WORDS.search(text)
        snippet = text[max(0, m.start() - 60): min(len(text), m.end() + 60)].replace("\n", " ")
        findings.append(_make_finding(
            omission_id="OMIT_002",
            omission_type="time_window_missing",
            trigger_text=snippet,
            expected_context="Time window (dates/range) for the described trend.",
            absence_signal="Trend language present but no explicit time window/date anchors detected in extracted text.",
            impact="Without a time window, trend claims are hard to evaluate and can mislead via ambiguity (short-term blip vs long-term shift).",
            severity=K.SEV_MODERATE,
        ))

    return {
        K.MODULE_STATUS: K.MODULE_RUN,
        "findings": findings,
        "notes": [
            "MVP omissions scan uses text-only signals over extracted evidence quotes.",
            "Findings indicate absence of expected context, not intent.",
        ],
    }
