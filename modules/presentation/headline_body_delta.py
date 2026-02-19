#!/usr/bin/env python3
"""
FILE: modules/presentation/headline_body_delta.py
VERSION: 0.2
LAST UPDATED: 2026-02-18
PURPOSE:
Headline–Body Delta (Presentation Integrity) evaluator — Pass B.

LOCKS:
- Does NOT change the Pass A container shape.
- Does NOT invent new schema fields for items in MVP.
- Emits deterministic notes and sets MODULE_STATUS to RUN.
- If data is missing, fails closed by keeping items empty and noting limits.

SEMANTICS LOCK (Option 2):
- hb.present means "a real headline exists for a headline-bearing source type"
  (i.e., source_type != 'text' AND headline_text is non-empty).
- For source_type == 'text', present MUST be False (source_title is a label).
"""

from __future__ import annotations

from typing import Any, Dict, List

from schema_names import K


def _get_source_type(out: Dict[str, Any]) -> str:
    rm = out.get(K.RUN_METADATA)
    if isinstance(rm, dict):
        st = rm.get(K.SOURCE_TYPE)
        if isinstance(st, str) and st.strip():
            return st.strip()
    return "text"


def _derive_present(*, source_type: str, headline: str) -> bool:
    # Option 2 semantics: only headline-bearing sources count as "present"
    if not isinstance(headline, str):
        return False
    return (source_type != "text") and bool(headline.strip())


def evaluate_headline_body_delta(out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate the Pass A headline_body_delta container (presentation integrity).
    MVP: no item schema yet -> items remains [].
    """
    hb = out.get(K.HEADLINE_BODY_DELTA)
    if not isinstance(hb, dict):
        return {
            K.MODULE_STATUS: K.MODULE_RUN,
            K.PRESENT: False,
            K.HEADLINE_TEXT: "",
            K.BODY_TEXT: "",
            K.ITEMS: [],
            K.NOTES: [
                "Headline–Body Delta evaluator ran, but Pass A container was missing or invalid.",
                "No delta evaluation performed (MVP); items remain empty.",
            ],
        }

    source_type = _get_source_type(out)

    headline = hb.get(K.HEADLINE_TEXT, "")
    body = hb.get(K.BODY_TEXT, "")

    # Normalize strings (without rewriting content)
    if not isinstance(headline, str):
        headline = ""
        hb[K.HEADLINE_TEXT] = ""
    if not isinstance(body, str):
        body = ""
        hb[K.BODY_TEXT] = ""

    # Respect Pass A semantics. If Pass A forgot present, derive it deterministically.
    present_val = hb.get(K.PRESENT, None)
    if isinstance(present_val, bool):
        present = present_val
    else:
        present = _derive_present(source_type=source_type, headline=headline)
        hb[K.PRESENT] = present

    # Items must exist and be a list
    items = hb.get(K.ITEMS, [])
    if not isinstance(items, list):
        items = []
    hb[K.ITEMS] = items

    # Deterministic notes
    notes: List[str] = [
        "Headline–Body Delta evaluator ran (MVP).",
        "This phase does not yet emit delta items (item schema not locked); items remain empty by design.",
        f"Semantic lock: present=True only for headline-bearing sources (source_type != 'text'). source_type={source_type!r}.",
    ]

    if not present:
        notes.insert(
            0,
            "No headline present for this source type; headline–body delta evaluation skipped.",
        )
        if source_type == "text" and headline.strip():
            notes.append("Note: headline_text is treated as a label for raw text input; not considered a true headline.")
    else:
        notes.insert(0, "No headline–body delta issues found (MVP: no item emission).")

    hb[K.MODULE_STATUS] = K.MODULE_RUN
    hb[K.NOTES] = notes

    return hb