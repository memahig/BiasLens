#!/usr/bin/env python3
"""
FILE: builders/report_builder.py
PURPOSE: Single authorized entry point for building BiasLens reports.

ARCHITECTURE RULE:
Pipeline MUST import the builder from this file — never directly from emitters.

This creates a permanent abstraction boundary so future Pass B,
retrieval systems, and reasoning modules can be added WITHOUT
rewiring the execution spine.
"""

from __future__ import annotations

from report_stub import analyze_text_to_report_pack
from builders.pass_b import run_pass_b
from schema_names import K


# MVP internal field (safe): gives Pass B modules access to full input text.
# Not intent-bearing; used only for text-only perception (e.g., omissions).
_INPUT_TEXT_KEY = "input_text"


def build_report(*, text, source_title=None, source_url=None):
    """
    Authorized builder wrapper.

    Today:
        Pass A -> emitter (report_stub.analyze_text_to_report_pack)
        Pass B -> post-processing layer

    Future:
        - Pass A: evidence bank + facts + claim registry + sockets
        - Pass B: verification + counterevidence + claim/argument integrity + synthesis
    """
    pass_a_out = analyze_text_to_report_pack(
        text=text,
        source_title=source_title,
        source_url=source_url,
    )

    # Provide the full input text to Pass B modules in a bounded, explicit place.
    # This does not re-scrape or change Pass A extraction; it only preserves input.
    rm = pass_a_out.get(K.RUN_METADATA)
    if isinstance(rm, dict):
        rm.setdefault(_INPUT_TEXT_KEY, text)
    else:
        pass_a_out[K.RUN_METADATA] = {_INPUT_TEXT_KEY: text}

    return run_pass_b(pass_a_out)
