#!/usr/bin/env python3
"""
FILE: builders/pass_a.py
VERSION: 0.1.1
LAST UPDATED: 2026-02-18
PURPOSE:
Pass A explicit entrypoint — produces the Pass A report pack (extraction only).

ARCHITECTURE LOCK:
- Pass A MUST perform extraction/registry emission only (no analysis/findings).
- Pass A MUST emit schema-legal containers/sockets needed by Pass B.
- Pass A MUST return a dict report pack.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from schema_names import K
from report_stub import analyze_text_to_report_pack


def run_pass_a(
    *,
    text: str,
    source_title: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Pass A extraction wrapper (explicit module).
    """
    out = analyze_text_to_report_pack(
        text=text,
        source_title=source_title,
        source_url=source_url,
    )

    # Ensure HEADLINE_BODY_DELTA container exists as a Pass A socket.
    headline_key = getattr(K, "HEADLINE_BODY_DELTA", "headline_body_delta")

    if isinstance(out, dict) and headline_key not in out:
        headline = (source_title or "").strip()
        body = (text or "").strip()

        out[headline_key] = {
            K.PRESENT: bool(headline),
            K.HEADLINE_TEXT: headline,
            K.BODY_TEXT: body,
            K.ITEMS: [],
            K.MODULE_STATUS: K.MODULE_NOT_RUN,
            K.NOTES: ["Pass A extracted headline/body; no delta evaluation performed."],
        }

    return out