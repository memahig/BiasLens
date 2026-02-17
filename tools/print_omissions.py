#!/usr/bin/env python3
"""
FILE: tools/print_omissions.py
VERSION: 0.2
LAST UPDATED: 2026-02-08
PURPOSE:
Human-readable omissions calibration view.

Reads a BiasLens report pack JSON from stdin and prints a Markdown report:
- Trigger text
- Omission type/id/severity
- Expected context + absence signal + impact
- OPTIONAL: local excerpt window (±N chars) from run_metadata["input_text"]

Notes:
- Does NOT modify the report pack or require schema changes.
- Excerpt extraction is best-effort: finds the first occurrence of trigger_text in input_text.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


WINDOW_CHARS = 250


def _get(d: Dict[str, Any], *path: str, default=None):
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
    return cur if cur is not None else default


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _find_excerpt(full_text: str, trigger_text: str, window_chars: int = WINDOW_CHARS) -> Optional[str]:
    """
    Best-effort: locate trigger_text in full_text and return ±window_chars excerpt.
    Returns None if full_text or trigger_text missing, or match not found.
    """
    if not full_text or not trigger_text:
        return None

    ft = full_text
    tt = _clean(trigger_text)

    # Try exact match first
    idx = ft.find(tt)
    if idx == -1:
        # Try normalized whitespace match (search in cleaned full text)
        ft_clean = _clean(ft)
        idx2 = ft_clean.find(tt)
        if idx2 == -1:
            return None
        start = max(0, idx2 - window_chars)
        end = min(len(ft_clean), idx2 + len(tt) + window_chars)
        return ft_clean[start:end].strip()

    start = max(0, idx - window_chars)
    end = min(len(ft), idx + len(tt) + window_chars)
    return _clean(ft[start:end])


def main() -> int:
    report = json.load(sys.stdin)

    so = _get(report, "article_layer", "systematic_omission", default={})
    status = _get(so, "status", default="(missing)")
    notes = _get(so, "notes", default=[])
    findings: List[Dict[str, Any]] = _get(so, "findings", default=[]) or []

    input_text = _get(report, "run_metadata", "input_text", default=None)
    has_input_text = isinstance(input_text, str) and input_text.strip()

    print("# Systematic Omission — Calibration View\n")
    print(f"- status: **{status}**")
    print(f"- findings: **{len(findings)}**")
    print(f"- excerpt_source: **{'run_metadata.input_text' if has_input_text else 'unavailable'}**\n")

    if notes:
        print("## Notes")
        for n in notes:
            print(f"- {n}")
        print()

    if not findings:
        print("_No omission findings._")
        return 0

    print("## Findings\n")
    for i, f in enumerate(findings, start=1):
        oid = f.get("omission_id", "")
        otype = f.get("omission_type", "")
        sev = f.get("severity", "")
        trig = (f.get("trigger_text") or "").strip()
        exp = (f.get("expected_context") or "").strip()
        absig = (f.get("absence_signal") or "").strip()
        impact = (f.get("impact") or "").strip()

        print(f"### {i}. {oid} — {otype} — severity: {sev}\n")

        if trig:
            print("**Trigger snippet:**")
            print(f"> {_clean(trig)}\n")

        if has_input_text and trig:
            ex = _find_excerpt(input_text, trig, WINDOW_CHARS)
            if ex:
                print(f"**Local excerpt (±{WINDOW_CHARS} chars):**")
                print(f"> {ex}\n")
            else:
                print(f"**Local excerpt (±{WINDOW_CHARS} chars):** _not found in input_text (best-effort match)_\n")

        if exp:
            print(f"**Expected context:** {exp}\n")
        if absig:
            print(f"**Absence signal:** {absig}\n")
        if impact:
            print(f"**Interpretive impact:** {impact}\n")

        print("---\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
