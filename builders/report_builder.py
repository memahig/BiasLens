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

from report_stub import analyze_text_to_report_pack


def build_report(*, text, source_title=None, source_url=None):
    """
    Authorized builder wrapper.

    Today:
        → calls the MVP emitter

    Future:
        → orchestrates Pass A + Pass B
        → attaches retrieval
        → injects reasoning modules
        → runs synthesis
    """

    return analyze_text_to_report_pack(
        text=text,
        source_title=source_title,
        source_url=source_url,
    )
