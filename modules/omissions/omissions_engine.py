#!/usr/bin/env python3
"""
FILE: modules/omissions/omissions_engine.py
VERSION: 0.3
LAST UPDATED: 2026-02-08
PURPOSE:
Detect *absence of expected context* (systematic omission) using text-only signals.

Safety/Locks:
- This module NEVER infers intent or wrongdoing.
- Findings are framed strictly as "missing expected context" and "possible interpretive impact."
- Text-only: no external world knowledge, no fact claims beyond the provided text.

Design:
- Triggered only by explicit language signals in the provided text.
- Uses LOCAL WINDOW absence checks (not whole-document) to avoid false negatives.
- Caps findings per detector to avoid spam in MVP.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

from schema_names import K


# Where full input text is preserved (set in builders/report_builder.py).
_INPUT_TEXT_KEY = "input_text"

# MVP caps (per detector)
_MAX_FINDINGS_PER_DETECTOR = 2
_WINDOW_CHARS = 250


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

# Comparison triggers (tightened):
# IMPORTANT: DO NOT trigger on bare "more/less" (false positive: "more details emerge").
_COMPARISON_CUES = re.compile(
    r"\b(compared to|versus|vs\.?|relative to|more than|less than|higher than|lower than)\b",
    re.IGNORECASE,
)

# Paired rhetorical pattern: "more X ... less Y" (keeps legit rhetoric without bare "more" noise)
_MORE_LESS_PAIR = re.compile(
    r"\bmore\b[^.\n]{0,80}\bless\b|\bless\b[^.\n]{0,80}\bmore\b",
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
    """
    rm = out.get(K.RUN_METADATA)
    if isinstance(rm, dict):
        t = rm.get(_INPUT_TEXT_KEY)
        if isinstance(t, str) and t.strip():
            return t.strip()

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


def _window(text: str, start: int, end: int, size: int = _WINDOW_CHARS) -> str:
    s = max(0, start - size)
    e = min(len(text), end + size)
    return text[s:e]


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
    # OMIT_001: baseline missing (LOCAL window)
    # --------------------------
    n = 0
    for m in _MAGNITUDE_WORDS.finditer(text):
        w = _window(text, m.start(), m.end())
        if _HAS_NUMBER.search(w):
            continue
        trig = _snippet(text, m.start(), m.end())
        findings.append(
            _make_finding(
                omission_id="OMIT_001",
                omission_type="baseline_missing",
                trigger_text=trig,
                expected_context="Baseline/denominator (prior value, comparison point, or magnitude) for the claimed change.",
                absence_signal="Magnitude language appears without a nearby numeric baseline/denominator (local-window check).",
                impact="Without a baseline, readers cannot judge how large or unusual the change is; framing may overstate significance.",
                severity=K.SEV_MODERATE,
            )
        )
        n += 1
        if n >= _MAX_FINDINGS_PER_DETECTOR:
            break

    # --------------------------
    # OMIT_002: time window missing (LOCAL window)
    # --------------------------
    n = 0
    for m in _TREND_WORDS.finditer(text):
        w = _window(text, m.start(), m.end())
        if _HAS_TIME_HINT.search(w) or _HAS_DATE.search(w):
            continue
        trig = _snippet(text, m.start(), m.end())
        findings.append(
            _make_finding(
                omission_id="OMIT_002",
                omission_type="time_window_missing",
                trigger_text=trig,
                expected_context="Time window (dates/range) for the described trend.",
                absence_signal="Trend language appears without a nearby time window/date anchor (local-window check).",
                impact="Without a time window, trend claims can mislead via ambiguity (short-term blip vs long-term shift).",
                severity=K.SEV_MODERATE,
            )
        )
        n += 1
        if n >= _MAX_FINDINGS_PER_DETECTOR:
            break

    # --------------------------
    # OMIT_003: scope boundary missing (LOCAL window)
    # Trigger: generalizer + group noun near each other
    # Absence: no qualifiers in same window
    # --------------------------
    n = 0
    for mg in _GENERALIZERS.finditer(text):
        w = _window(text, mg.start(), mg.end())
        if not _GROUP_NOUNS.search(w):
            continue
        if _QUALIFIERS.search(w):
            continue
        trig = _snippet(text, mg.start(), mg.end())
        findings.append(
            _make_finding(
                omission_id="OMIT_003",
                omission_type="scope_boundary_missing",
                trigger_text=trig,
                expected_context="Scope boundaries/qualifiers (who exactly, where, when, and under what conditions) for broad generalizations.",
                absence_signal="Generalizing language appears near a group reference without nearby qualifiers (local-window check).",
                impact="Without scope boundaries, readers may overgeneralize from limited cases to an entire group or context.",
                severity=K.SEV_MODERATE,
            )
        )
        n += 1
        if n >= _MAX_FINDINGS_PER_DETECTOR:
            break

    # --------------------------
    # OMIT_004: comparison class missing (LOCAL window)
    # --------------------------
    n = 0
    for m in _COMPARISON_CUES.finditer(text):
        w = _window(text, m.start(), m.end())
        if _HAS_THAN_OR_FROM_TO.search(w):
            continue
        trig = _snippet(text, m.start(), m.end())
        findings.append(
            _make_finding(
                omission_id="OMIT_004",
                omission_type="comparison_class_missing",
                trigger_text=trig,
                expected_context="Explicit comparison class (compared to what/whom; from what baseline to what new value).",
                absence_signal="Comparative language appears without a nearby explicit comparator structure (local-window check).",
                impact="Without an explicit comparator, comparative claims can feel precise while remaining underspecified.",
                severity=K.SEV_MODERATE,
            )
        )
        n += 1
        if n >= _MAX_FINDINGS_PER_DETECTOR:
            break

    # --------------------------
    # OMIT_005: causal bridge missing (LOCAL window)
    # --------------------------
    n = 0
    for m in _CAUSAL_WORDS.finditer(text):
        w = _window(text, m.start(), m.end())
        if _MECHANISM_HINTS.search(w) or _EVIDENCE_TYPE_HINTS.search(w):
            continue
        trig = _snippet(text, m.start(), m.end())
        findings.append(
            _make_finding(
                omission_id="OMIT_005",
                omission_type="causal_bridge_missing",
                trigger_text=trig,
                expected_context="Causal bridge: mechanism description and/or evidence type supporting the causal link.",
                absence_signal="Causal language appears without nearby mechanism markers or evidence-type markers (local-window check).",
                impact="Without a causal bridge, readers may accept causal interpretation as settled when it may be only asserted or ambiguous.",
                severity=K.SEV_ELEVATED,
            )
        )
        n += 1
        if n >= _MAX_FINDINGS_PER_DETECTOR:
            break

    return {
        K.MODULE_STATUS: K.MODULE_RUN,
        "findings": findings,
        "notes": [
            "Omissions scan uses text-only signals; it flags absence of expected context, not intent.",
            f"Text source: {'run_metadata.input_text' if isinstance(out.get(K.RUN_METADATA), dict) and isinstance(out.get(K.RUN_METADATA, {}).get(_INPUT_TEXT_KEY), str) else 'evidence_bank quotes'}",
            f"Local-window checks enabled (±{_WINDOW_CHARS} chars), capped at {_MAX_FINDINGS_PER_DETECTOR} findings per detector.",
        ],
    }
