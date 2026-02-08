#!/usr/bin/env python3
"""
FILE: modules/omissions/omissions_engine.py
VERSION: 0.2
LAST UPDATED: 2026-02-08
PURPOSE:
Detect *absence of expected context* (systematic omission) using text-only signals.

Safety/Locks:
- This module NEVER infers intent or wrongdoing.
- Findings are framed strictly as "missing expected context" and "possible interpretive impact."
- Text-only: no external world knowledge, no fact claims beyond the provided text.

Design:
- Triggered only by explicit language signals in the provided text.
- Each detector includes an explicit absence check inside the same text blob.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

from schema_names import K


# Where full input text is preserved (set in builders/report_builder.py).
_INPUT_TEXT_KEY = "input_text"


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

# Scope / generalization signals
_GENERALIZERS = re.compile(
    r"\b(all|always|never|everyone|no one|nobody|every|none|entire|completely)\b",
    re.IGNORECASE,
)

# A small, conservative set of group nouns. (Text-only heuristic; can expand later.)
_GROUP_NOUNS = re.compile(
    r"\b(people|americans|voters|patients|doctors|nurses|scientists|experts|journalists|media|police|students|teachers|immigrants|refugees|workers|democrats|republicans|conservatives|liberals|israelis|palestinians)\b",
    re.IGNORECASE,
)

_QUALIFIERS = re.compile(
    r"\b(some|many|often|sometimes|in some cases|in certain cases|in many cases|a number of|several|among|within|in this sample|in this study|in this report)\b",
    re.IGNORECASE,
)

# Comparison signals
_COMPARATIVES = re.compile(
    r"\b(more|less|higher|lower|fewer|greater|smaller|bigger|compared|versus|vs\.)\b",
    re.IGNORECASE,
)

_HAS_THAN_OR_FROM_TO = re.compile(
    r"\bthan\b|\bfrom\b.+\bto\b",
    re.IGNORECASE | re.DOTALL,
)

# Causal signals
_CAUSAL_WORDS = re.compile(
    r"\b(because|therefore|thus|hence|led to|leads to|caused|causes|resulted in|results in|due to)\b",
    re.IGNORECASE,
)

# Mechanism / evidence-type hints (still text-only)
_MECHANISM_HINTS = re.compile(
    r"\b(mechanism|pathway|through|by (means of)?|via)\b",
    re.IGNORECASE,
)

_EVIDENCE_TYPE_HINTS = re.compile(
    r"\b(according to|data|report|study|research|analysis|survey|records|documents|court filings|statistics)\b",
    re.IGNORECASE,
)


def _extract_text_blob(out: Dict[str, Any]) -> str:
    """
    Prefer full input text if preserved in run_metadata['input_text'].
    Otherwise fall back to concatenating evidence quotes.

    This keeps the omissions engine text-only and avoids requiring new schema fields.
    """
    # 1) Preferred: preserved input text (builder-provided)
    rm = out.get(K.RUN_METADATA)
    if isinstance(rm, dict):
        t = rm.get(_INPUT_TEXT_KEY)
        if isinstance(t, str) and t.strip():
            return t.strip()

    # 2) Fallback: evidence quotes
    parts: List[str] = []
    eb = out.get(K.EVIDENCE_BANK)
    if isinstance(eb, list):
        for item in eb:
            if isinstance(item, dict):
                q = item.get(K.QUOTE)
                if isinstance(q, str) and q.strip():
                    parts.append(q.strip())

    return "\n".join(parts).strip()


def _snippet(text: str, start: int, end: int, pad: int = 70) -> str:
    s = max(0, start - pad)
    e = min(len(text), end + pad)
    return text[s:e].replace("\n", " ").strip()


def _make_finding(
    *,
    omission_id: str,
    omission_type: str,
    trigger_text: str,
    expected_context: str,
    absence_signal: str,
    impact: str,
    severity: str,
) -> Dict[str, Any]:
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

    # --------------------------
    # OMIT_001: baseline missing
    # --------------------------
    if _MAGNITUDE_WORDS.search(text) and not _HAS_NUMBER.search(text):
        m = _MAGNITUDE_WORDS.search(text)
        trig = _snippet(text, m.start(), m.end())
        findings.append(
            _make_finding(
                omission_id="OMIT_001",
                omission_type="baseline_missing",
                trigger_text=trig,
                expected_context="Baseline/denominator (prior value, comparison point, or magnitude) for the claimed change.",
                absence_signal="Magnitude language present but no numeric baseline/denominator detected in the analyzed text.",
                impact="Without a baseline, readers cannot judge how large or unusual the change is; framing may overstate significance.",
                severity=K.SEV_MODERATE,
            )
        )

    # --------------------------
    # OMIT_002: time window missing
    # --------------------------
    if _TREND_WORDS.search(text) and not (_HAS_TIME_HINT.search(text) or _HAS_DATE.search(text)):
        m = _TREND_WORDS.search(text)
        trig = _snippet(text, m.start(), m.end())
        findings.append(
            _make_finding(
                omission_id="OMIT_002",
                omission_type="time_window_missing",
                trigger_text=trig,
                expected_context="Time window (dates/range) for the described trend.",
                absence_signal="Trend language present but no explicit time window/date anchors detected in the analyzed text.",
                impact="Without a time window, trend claims are hard to evaluate and can mislead via ambiguity (short-term blip vs long-term shift).",
                severity=K.SEV_MODERATE,
            )
        )

    # --------------------------
    # OMIT_003: scope boundary missing
    # Trigger: generalizers + group nouns
    # Absence: no nearby qualifiers (coarse text-wide check for MVP)
    # --------------------------
    if _GENERALIZERS.search(text) and _GROUP_NOUNS.search(text) and not _QUALIFIERS.search(text):
        mg = _GENERALIZERS.search(text)
        mn = _GROUP_NOUNS.search(text)
        start = min(mg.start(), mn.start())
        end = max(mg.end(), mn.end())
        trig = _snippet(text, start, end)
        findings.append(
            _make_finding(
                omission_id="OMIT_003",
                omission_type="scope_boundary_missing",
                trigger_text=trig,
                expected_context="Scope boundaries/qualifiers (who exactly, where, when, and under what conditions) for broad generalizations.",
                absence_signal="Generalizing language detected without offsetting qualifiers (e.g., some/many/often/among/within) in the analyzed text.",
                impact="Without scope boundaries, readers may overgeneralize from limited cases to an entire group or context.",
                severity=K.SEV_MODERATE,
            )
        )

    # --------------------------
    # OMIT_004: comparison class missing
    # Trigger: comparative language
    # Absence: no 'than' or 'from X to Y' structure (MVP coarse check)
    # --------------------------
    if _COMPARATIVES.search(text) and not _HAS_THAN_OR_FROM_TO.search(text):
        m = _COMPARATIVES.search(text)
        trig = _snippet(text, m.start(), m.end())
        findings.append(
            _make_finding(
                omission_id="OMIT_004",
                omission_type="comparison_class_missing",
                trigger_text=trig,
                expected_context="Explicit comparison class (compared to what/whom; from what baseline to what new value).",
                absence_signal="Comparative language detected but no explicit comparator structure (e.g., 'than', 'from ... to ...') found in the analyzed text.",
                impact="Without an explicit comparator, comparative claims can feel precise while remaining underspecified.",
                severity=K.SEV_MODERATE,
            )
        )

    # --------------------------
    # OMIT_005: causal bridge missing
    # Trigger: causal connectors
    # Absence: neither mechanism hints nor evidence-type hints (MVP coarse check)
    # --------------------------
    if _CAUSAL_WORDS.search(text) and not (_MECHANISM_HINTS.search(text) or _EVIDENCE_TYPE_HINTS.search(text)):
        m = _CAUSAL_WORDS.search(text)
        trig = _snippet(text, m.start(), m.end())
        findings.append(
            _make_finding(
                omission_id="OMIT_005",
                omission_type="causal_bridge_missing",
                trigger_text=trig,
                expected_context="Causal bridge: mechanism description and/or evidence type supporting the causal link.",
                absence_signal="Causal language detected but no mechanism markers or evidence-type markers found in the analyzed text.",
                impact="Without a causal bridge, readers may accept causal interpretation as settled when it may be only asserted or ambiguous.",
                severity=K.SEV_ELEVATED,
            )
        )

    return {
        K.MODULE_STATUS: K.MODULE_RUN,
        "findings": findings,
        "notes": [
            "Omissions scan uses text-only signals; it flags absence of expected context, not intent.",
            f"Text source: {'run_metadata.input_text' if isinstance(out.get(K.RUN_METADATA), dict) and isinstance(out.get(K.RUN_METADATA, {}).get(_INPUT_TEXT_KEY), str) else 'evidence_bank quotes'}",
        ],
    }
