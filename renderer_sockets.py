#!/usr/bin/env python3
"""
FILE: renderer_sockets.py
VERSION: 0.2
LAST UPDATED: 2026-02-07
PURPOSE:
Renderer-side surfacing for "sensor sockets" that live in article_layer.

This module is intentionally dumb:
- It does NOT add interpretation.
- It only (a) extracts socket objects, (b) infers run/not_run conservatively,
  and (c) appends minimal Markdown blocks for Overview + Scholar.

Integrity rules:
- Prefer schema_names.K.MODULE_STATUS (write authority).
- Accept schema_names.K.STATUS as LEGACY READ-ONLY fallback only.
- Missing/unknown => not_run (fail-closed rendering posture).

Current sockets covered:
- timeline_events, timeline_summary, timeline_consistency
- framing_evidence_alignment (dormant, status: not_run unless explicitly run)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from schema_names import K


def _d(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _l(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _s(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _clip(s: str, n: int = 260) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _bullet(lines: List[str], text: str) -> None:
    lines.append(f"- {text}")


def _pillar_status_from_obj(obj: Any, module_status_key: str, legacy_status_key: str) -> str:
    """
    Conservative:
    - Prefer module_status_key if present (run|not_run)
    - Accept legacy_status_key read-only for backward compatibility
    - Missing/unknown => not_run
    """
    if not isinstance(obj, dict):
        return K.MODULE_NOT_RUN
    st = obj.get(module_status_key) or obj.get(legacy_status_key)
    st = _s(st).lower()
    return st if st in (K.MODULE_RUN, K.MODULE_NOT_RUN) else K.MODULE_NOT_RUN


def build_article_sockets(
    article_layer: Dict[str, Any],
    *,
    module_status_key: str,
    legacy_status_key: str,
) -> Dict[str, Any]:
    """
    Returns a normalized sockets dict.

    Notes:
    - Literal socket field names are used ("timeline_events", etc.) to avoid coupling
      to schema_names expansion timing for every future socket.
    - Status inference is conservative:
        * If an explicit status exists on the socket object, obey it.
        * Else infer "run" only if there is meaningful emitted content.
        * Else "not_run".
    """
    t_events = _l(article_layer.get(K.TIMELINE_EVENTS))
    t_summary = _s(article_layer.get(K.TIMELINE_SUMMARY))
    t_consistency = _d(article_layer.get(K.TIMELINE_CONSISTENCY))

    framing_align = _d(article_layer.get(K.FRAMING_EVIDENCE_ALIGNMENT))

    # ── Timeline status ────────────────────────────────────────
    t_status = K.MODULE_NOT_RUN

    if t_consistency:
        # If explicit status key is present (either new or legacy), obey it.
        has_explicit = (module_status_key in t_consistency) or (legacy_status_key in t_consistency)
        if has_explicit:
            t_status = _pillar_status_from_obj(t_consistency, module_status_key, legacy_status_key)
        else:
            # No explicit status: infer run only if there is content
            t_status = K.MODULE_RUN if (t_events or t_summary or t_consistency) else K.MODULE_NOT_RUN
    else:
        # No consistency object: infer from events/summary presence only
        t_status = K.MODULE_RUN if (t_events or t_summary) else K.MODULE_NOT_RUN

    # ── Framing↔Evidence Alignment status ──────────────────────
    # Dormant socket: default not_run unless explicitly marked run.
    fa_status = _pillar_status_from_obj(framing_align, module_status_key, legacy_status_key)

    return {
        "timeline_events": t_events,
        "timeline_summary": t_summary,
        "timeline_consistency": t_consistency,
        "timeline_status": t_status,
        "framing_evidence_alignment": framing_align,
        "framing_alignment_status": fa_status,
    }


def append_overview_timeline(lines: List[str], sockets: Dict[str, Any]) -> None:
    """
    Overview-only minimal surfacing. No new claims. No interpretation.
    """
    lines.append("## Timeline (narrative structure)")
    if _s(sockets.get("timeline_status")) == K.MODULE_RUN:
        events = _l(sockets.get("timeline_events"))
        summary = _s(sockets.get("timeline_summary"))
        consistency = _d(sockets.get("timeline_consistency"))

        _bullet(lines, f"Events detected: **{len(events)}**")
        if summary:
            _bullet(lines, f"Summary: {_clip(summary, 280)}")

        verdict = _s(consistency.get("verdict")) or _s(consistency.get("status_label"))
        if verdict:
            _bullet(lines, f"Consistency: **{_clip(verdict, 120)}**")
    else:
        _bullet(lines, "Not run in this build.")
    lines.append("")


def append_scholar_narrative_sockets(lines: List[str], sockets: Dict[str, Any]) -> None:
    """
    Scholar-side raw object surfacing for audit/debug.
    """
    # Timeline
    lines.append("### article_layer.timeline_consistency")
    lines.append("```json")
    lines.append(json.dumps(_d(sockets.get("timeline_consistency")), indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")
    lines.append("### article_layer.timeline_summary")
    ts = _s(sockets.get("timeline_summary"))
    lines.append(_clip(ts, 3000) if ts else "(none)")
    lines.append("")
    lines.append("### article_layer.timeline_events (first 50)")
    te = _l(sockets.get("timeline_events"))
    if te:
        lines.append("```json")
        lines.append(json.dumps(te[:50], indent=2, ensure_ascii=False))
        lines.append("```")
    else:
        lines.append("(none)")
    lines.append("")

    # Dormant socket
    lines.append("### article_layer.framing_evidence_alignment")
    lines.append("```json")
    lines.append(json.dumps(_d(sockets.get("framing_evidence_alignment")), indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")
