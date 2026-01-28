
from __future__ import annotations

import re
from typing import List, Optional

from schema_names import K

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _find_span(text: str, quote: str, start_search: int = 0) -> Optional[tuple[int, int]]:
    if not quote:
        return None
    i = text.find(quote, start_search)
    if i == -1:
        return None
    return i, i + len(quote)


def build_evidence_bank(
    text: str,
    source_title: str,
    source_url: Optional[str],
    max_items: int = 6,
) -> List[dict]:
    """
    Pass A foundation: extract a small set of verbatim quotes + offsets.
    Strategy: take first N sentence-like chunks, find exact spans, emit EIDs.
    """
    raw = (text or "")
    if not raw.strip():
        quote = "No text provided."
        return [
            {
                K.EID: "E1",
                K.QUOTE: quote,
                K.START_CHAR: 0,
                K.END_CHAR: len(quote),
                K.WHY_RELEVANT: "Input was empty; placeholder quote.",
                K.SOURCE: {K.TYPE: "text", K.TITLE: source_title, K.URL: source_url},
            }
        ]

    chunks = [c.strip() for c in _SENT_SPLIT.split(raw.strip()) if c.strip()]

    bank: List[dict] = []
    cursor = 0
    eid_n = 1

    for c in chunks:
        if len(bank) >= max_items:
            break

        quote = c
        if len(quote) > 280:
            quote = quote[:280].rstrip() + "…"

        unclipped = quote.replace("…", "")
        span = _find_span(raw, unclipped, start_search=cursor)
        if span is None:
            continue

        start, end = span
        cursor = end

        bank.append(
            {
                K.EID: f"E{eid_n}",
                K.QUOTE: raw[start:end],
                K.START_CHAR: start,
                K.END_CHAR: end,
                K.WHY_RELEVANT: "Pass A extracted verbatim quote for downstream claim linking.",
                K.SOURCE: {K.TYPE: "url" if source_url else "text", K.TITLE: source_title, K.URL: source_url},
            }
        )
        eid_n += 1

    if not bank:
        quote = raw.strip()[:280]
        bank = [
            {
                K.EID: "E1",
                K.QUOTE: quote,
                K.START_CHAR: 0,
                K.END_CHAR: len(quote),
                K.WHY_RELEVANT: "Fallback: could not segment; using leading substring.",
                K.SOURCE: {K.TYPE: "url" if source_url else "text", K.TITLE: source_title, K.URL: source_url},
            }
        ]

    return bank

