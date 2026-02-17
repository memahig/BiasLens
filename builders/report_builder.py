#!/usr/bin/env python3
"""
FILE: builders/report_builder.py
VERSION: 0.5
LAST UPDATED: 2026-02-16
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
from builders.pass_b import run_pass_b_audit
from schema_names import K

# Internal key to ensure Pass B modules have access to raw source text for structural scans.
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
    
    # 1. PASS A: Ground truth extraction and schema initialization.
    # Logic is located in root/report_stub.py
    report_pack = analyze_text_to_report_pack(
        text=text,
        source_title=source_title,
        source_url=source_url,
    )

    # 2. METADATA PRESERVATION
    # We explicitly preserve the full input text in run_metadata. 
    # This is critical for Pass B modules (Timeline, Omissions) that 
    # need to re-scan the original text for structural patterns.
    rm = report_pack.get(K.RUN_METADATA)
    if isinstance(rm, dict):
        rm.setdefault(_INPUT_TEXT_KEY, text)
    else:
        report_pack[K.RUN_METADATA] = {_INPUT_TEXT_KEY: text}

    # 3. PASS B: Epistemic Audit, Scoring, and Timeline Generation.
    # Logic is located in builders/pass_b.py
    final_report = run_pass_b_audit(report_pack, view_mode=view_mode)

    return final_report