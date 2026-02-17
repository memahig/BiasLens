#!/usr/bin/env python3
"""
FILE: builders/report_builder.py
VERSION: 0.5.1
LAST UPDATED: 2026-02-17
PURPOSE:
Single authorized entry point for building BiasLens reports.

ARCHITECTURE RULE:
Pipeline MUST import the builder from this file. This creates a permanent 
abstraction boundary between extraction (Pass A) and audit (Pass B).

- Pass A (report_stub.py): Verbatim Extraction & Schema Emission.
- Pass B (builders/pass_b.py): Epistemic Audit, Scoring, & Timeline.
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from report_stub import analyze_text_to_report_pack
from builders.pass_b import run_pass_b   # ← correct function
from schema_names import K


# Internal key to ensure Pass B modules have access to raw source text.
_INPUT_TEXT_KEY = "input_text"


def build_report(
    *, 
    text: str, 
    source_title: Optional[str] = None, 
    source_url: Optional[str] = None,
    view_mode: str = "Overview"
) -> Dict[str, Any]:
    """
    Authorized builder wrapper.
    Executes Pass A (Extraction) then hands off to Pass B (Epistemic Audit).
    """

    # PASS A — Ground truth extraction
    report_pack = analyze_text_to_report_pack(
        text=text,
        source_title=source_title,
        source_url=source_url,
    )

    # Preserve full input text for structural modules (Timeline, Omissions, etc.)
    rm = report_pack.get(K.RUN_METADATA)
    if isinstance(rm, dict):
        rm.setdefault(_INPUT_TEXT_KEY, text)
    else:
        report_pack[K.RUN_METADATA] = {_INPUT_TEXT_KEY: text}

    # PASS B — Epistemic audit
    # NOTE:
    # run_pass_b currently does not accept view_mode.
    # This parameter is intentionally retained here as a forward-compatibility hook.
    final_report = run_pass_b(report_pack)

    return final_report
