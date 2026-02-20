
#!/usr/bin/env python3
"""
FILE: evidence_bank_builder.py
VERSION: 0.2
LAST UPDATED: 2026-01-31
PURPOSE: Pass A evidence_bank extraction (verbatim quotes + offsets) for downstream claim linking.

Contract:
- Output: List[dict] where each dict includes:
    - K.EID, K.QUOTE, K.START_CHAR, K.END_CHAR, K.WHY_RELEVANT, K.SOURCE
- Quotes MUST be verbatim slices from the input text.
- start_char/end_char MUST point into the original input text.

Design notes (MVP but real):
- Prefer paragraph blocks first (news articles are paragraph-structured).
- Then fill with sentence chunks as needed.
- No paraphrase, no fuzzy matching; if exact span not found, skip.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from schema_names import K


# Conservative sentence split: tries to avoid splitting on abbreviations (still imperfect).
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
# Paragraph blocks: separated by one or more blank lines.
_PARA_BLOCK = re.compile(r"(?:^|\n)([^\n].*?)(?=\n\s*\n|\Z)", re.DOTALL)

# Common abbreviations that should NOT be treated as sentence boundaries.
# Keep this list small + conservative; it can be extended safely later.
_ABBREV_NO_SPLIT = {
    "U.S.", "U.K.", "E.U.", "U.N.",
    "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.",
    "St.", "Mt.",
    "Inc.", "Ltd.", "Co.",
    "vs.", "No.", "Fig.", "Dept.",
}

def _join_false_sentence_splits(chunks: List[str]) -> List[str]:
    """
    Re-join chunks that were incorrectly split at an abbreviation like 'U.S.'.
    Deterministic, conservative heuristic:
      - if a chunk ends with a known abbreviation, join it with the next chunk
      - also handles patterns like 'U.S.' where last token is X.X. (all-caps)
    """
    if not chunks:
        return []

    out: List[str] = []
    i = 0
    while i < len(chunks):
        cur = (chunks[i] or "").strip()
        if not cur:
            i += 1
            continue

        if i + 1 < len(chunks):
            nxt = (chunks[i + 1] or "").strip()
            last_token = cur.split()[-1] if cur.split() else ""

            # Known abbreviations
            if last_token in _ABBREV_NO_SPLIT:
                out.append((cur + " " + nxt).strip())
                i += 2
                continue

            # Pattern like 'U.S.' / 'E.U.' / 'U.N.' (all caps segments)
            # Keep conservative: only 2-3 segments, all 1-2 letters.
            if re.fullmatch(r"(?:[A-Z]{1,2}\.){2,3}", last_token):
                out.append((cur + " " + nxt).strip())
                i += 2
                continue

        out.append(cur)
        i += 1

    return out

def _clip_at_boundary(s: str, max_len: int) -> str:
    """
    Clip s to <= max_len but try hard to end on a sentence/phrase boundary.
    Returns a verbatim prefix (no ellipsis) so span-finding stays exact.
    """
    s = (s or "").strip()
    if len(s) <= max_len:
        return s

    prefix = s[:max_len]

    # Prefer sentence end inside prefix
    for pat in (".", "?", "!"):
        i = prefix.rfind(pat)
        if i >= int(max_len * 0.55):  # don't clip too aggressively
            return prefix[: i + 1].rstrip()

    # Then phrase/clause boundaries
    for pat in ("; ", ": ", ", ", " — ", " - "):
        i = prefix.rfind(pat)
        if i >= int(max_len * 0.55):
            return prefix[: i + len(pat)].rstrip()

    # Then last whitespace
    j = prefix.rfind(" ")
    if j >= int(max_len * 0.55):
        return prefix[:j].rstrip()

    return prefix.rstrip()


def _find_span(text: str, quote: str, start_search: int = 0) -> Optional[Tuple[int, int]]:
    if not quote:
        return None
    i = text.find(quote, start_search)
    if i == -1:
        return None
    return i, i + len(quote)


def _normalize_newlines(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")

def next_eid(evidence_bank: List[dict]) -> str:
    """
    Return the next sequential EID using the project's canonical E{n} convention.
    Only trusts existing EIDs that match /^E\\d+$/.
    """
    max_n = 0
    for ev in evidence_bank or []:
        if not isinstance(ev, dict):
            continue
        eid = ev.get(K.EID, "")
        if isinstance(eid, str) and eid.startswith("E") and eid[1:].isdigit():
            n = int(eid[1:])
            if n > max_n:
                max_n = n
    return f"E{max_n + 1}"


def add_evidence_span(
    *,
    evidence_bank: List[dict],
    full_text: str,
    start_char: int,
    end_char: int,
    why_relevant: str,
    source_title: str,
    source_url: Optional[str],
) -> Optional[str]:
    """
    Canonical evidence writer.
    - Quote is an exact verbatim slice from full_text[start_char:end_char].
    - Appends a new evidence_bank item with next sequential EID.
    - Returns the new EID, or None if span invalid/empty.
    """
    if not isinstance(start_char, int) or not isinstance(end_char, int):
        return None
    if start_char < 0 or end_char <= start_char:
        return None
    if end_char > len(full_text):
        return None

    quote_verbatim = full_text[start_char:end_char]
    if not quote_verbatim.strip():
        return None

    eid = next_eid(evidence_bank)

    evidence_bank.append(
        {
            K.EID: eid,
            K.QUOTE: quote_verbatim,
            K.START_CHAR: start_char,
            K.END_CHAR: end_char,
            K.WHY_RELEVANT: why_relevant,
            K.SOURCE: {
                K.TYPE: "url" if (source_url or "").strip() else "text",
                K.TITLE: source_title or "",
                K.URL: (source_url or ""),
            },
        }
    )
    return eid


def build_evidence_bank(
    text: str,
    source_title: str,
    source_url: Optional[str],
    max_items: int = 40,
) -> List[dict]:
    """
    Pass A foundation: extract a set of verbatim quotes + offsets.
    Strategy:
      1) paragraph blocks (clipped for length but offsets reflect the emitted quote)
      2) sentence-like chunks to fill remaining slots
    """
    raw = _normalize_newlines(text)

    if not raw.strip():
        quote = "No text provided."
        return [
            {
                K.EID: "E1",
                K.QUOTE: quote,
                K.START_CHAR: 0,
                K.END_CHAR: len(quote),
                K.WHY_RELEVANT: "Input was empty; placeholder quote.",
                K.SOURCE: {K.TYPE: "text", K.TITLE: source_title or "", K.URL: (source_url or "")},
            }
        ]

    bank: List[dict] = []
    cursor = 0

    def _emit(start: int, end: int, why: str) -> None:
        add_evidence_span(
            evidence_bank=bank,
            full_text=raw,
            start_char=start,
            end_char=end,
            why_relevant=why,
            source_title=source_title,
            source_url=source_url,
        )


    # -----------------------------
    # 1) Paragraph blocks first
    # -----------------------------
    for m in _PARA_BLOCK.finditer(raw):
        if len(bank) >= max_items:
            break
        block = (m.group(1) or "").strip()
        if not block:
            continue

        # clip to keep evidence items readable (still verbatim prefix)
        clip = _clip_at_boundary(block, 420)
        # locate span of the clipped prefix inside the block region
        start = m.start(1)
        span = _find_span(raw, clip, start_search=start)
        if span is None:
            continue
        s, e = span
        # advance cursor to avoid repeatedly capturing earlier regions
        cursor = max(cursor, e)
        _emit(s, e, "Pass A extracted paragraph passage (verbatim prefix) for downstream claim linking.")

    # -----------------------------
    # 2) Sentence chunks to fill remainder
    # -----------------------------
    if len(bank) < max_items:
        chunks = [c.strip() for c in _SENT_SPLIT.split(raw.strip()) if c.strip()]
        chunks = _join_false_sentence_splits(chunks)

        for c in chunks:
            if len(bank) >= max_items:
                break

            quote = _clip_at_boundary(c, 280)

            span = _find_span(raw, quote, start_search=cursor)
            if span is None:
                # try again from 0 in case cursor skipped a valid earlier occurrence
                span = _find_span(raw, quote, start_search=0)
            if span is None:
                continue

            start, end = span
            cursor = max(cursor, end)
            _emit(start, end, "Pass A extracted sentence passage (verbatim) for downstream claim linking.")

    # Fallback: ensure at least one evidence item
    if not bank:
        quote = raw.strip()
        if len(quote) > 280:
            quote = quote[:280].rstrip()
        span = _find_span(raw, quote, start_search=0)
        if span is None:
            # last-resort: just emit leading substring with honest offsets
            bank = [
                {
                    K.EID: "E1",
                    K.QUOTE: quote,
                    K.START_CHAR: 0,
                    K.END_CHAR: len(quote),
                    K.WHY_RELEVANT: "Fallback: could not segment; using leading substring.",
                    K.SOURCE: {K.TYPE: "url" if (source_url or "").strip() else "text", K.TITLE: source_title or "", K.URL: (source_url or "")},
                }
            ]
        else:
            s, e = span
            _emit(s, e, "Fallback: could not segment cleanly; using leading substring span.")

    return bank
