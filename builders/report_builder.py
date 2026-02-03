
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


def build_report(*, text, source_title=None, source_url=None):
    """
    Authorized builder wrapper.

    Today:
        Pass A -> emitter (report_stub.analyze_text_to_report_pack)
        Pass B -> post-processing layer (currently identity)

    Future:
        - Pass A: evidence bank + facts + claim registry + sockets
        - Pass B: verification + counterevidence + claim/argument integrity + synthesis
    """
    pass_a_out = analyze_text_to_report_pack(
        text=text,
        source_title=source_title,
        source_url=source_url,
    )

    return run_pass_b(pass_a_out)
