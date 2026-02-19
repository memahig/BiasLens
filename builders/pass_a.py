#!/usr/bin/env python3
"""
FILE: builders/pass_a.py
VERSION: 0.2
LAST UPDATED: 2026-02-18
PURPOSE:
Pass A explicit entrypoint — produces the Pass A report pack (extraction only).

ARCHITECTURE LOCK:
- Pass A MUST perform extraction/registry emission only (no analysis/findings).
- Pass A MUST emit schema-legal containers/sockets needed by Pass B.
- Pass A MUST return a dict report pack.

HEADLINE_BODY_DELTA SEMANTICS (LOCKED):
- headline_body_delta.present means "a real headline exists for this source type"
  (i.e., headline-bearing sources like URL/articles), NOT merely "source_title is non-empty".
- For source_type == "text", present MUST be False (source_title is treated as a label).
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

    if not isinstance(out, dict):
        raise RuntimeError("Pass A contract violation: output must be a dict report pack.")

    # Determine source_type (set by report_stub; e.g., "text" for --text mode)
    rm = out.get(K.RUN_METADATA, {})
    source_type = rm.get(K.SOURCE_TYPE, "text") if isinstance(rm, dict) else "text"

    # Ensure HEADLINE_BODY_DELTA container exists as a Pass A socket.
    # Headline = source_title (when available), body = full extracted input text.
    if K.HEADLINE_BODY_DELTA not in out:
        headline = (source_title or "").strip()
        body = (text or "").strip()

        # Option 2 semantics: only headline-bearing sources count as "present"
        headline_present = (source_type != "text") and bool(headline)

        notes = [
            "Pass A extracted headline/body; no delta evaluation performed.",
            f"Semantic lock: present=True only for headline-bearing sources (source_type != 'text'). source_type={source_type!r}.",
        ]
        if source_type == "text" and headline:
            notes.append("Note: source_title is treated as a label for raw text input; not considered a true headline.")

        out[K.HEADLINE_BODY_DELTA] = {
            K.PRESENT: headline_present,
            K.HEADLINE_TEXT: headline,
            K.BODY_TEXT: body,
            K.ITEMS: [],
            K.MODULE_STATUS: K.MODULE_NOT_RUN,
            K.NOTES: notes,
        }

    return out