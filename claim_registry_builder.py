
from __future__ import annotations

import re
from typing import List, Dict

from schema_names import K


def _split_into_sentences(text: str) -> List[str]:
    # Very conservative sentence split; we already have quote chunks, so keep it simple.
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if p and p.strip()]


def _guess_stakes(sentence: str) -> str:
    s = (sentence or "").lower()

    # High: numbers, strong causal/attribution verbs, absolutes
    if re.search(r"\b\d+(\.\d+)?\b", s):
        return "high"
    if any(w in s for w in ["caused", "causes", "leads to", "results in", "proves", "evidence that", "therefore"]):
        return "high"
    if any(w in s for w in ["always", "never", "everyone", "no one", "all ", "none "]):
        return "high"

    # Medium: policy/should/claims about groups or institutions
    if any(w in s for w in ["should", "must", "need to", "policy", "government", "company", "study", "research"]):
        return "medium"

    return "low"


def build_claim_registry_from_evidence(evidence_bank: List[Dict], max_claims: int = 8) -> List[Dict]:
    """
    Build claims strictly from verbatim evidence quotes.
    Each claim is a sentence-like unit taken from quotes, with evidence_eids referencing the quote it came from.
    """
    claims: List[Dict] = []
    cid = 1

    for ev in evidence_bank:
        if len(claims) >= max_claims:
            break

        eid = (ev.get(K.EID) or "").strip()
        quote = (ev.get(K.QUOTE) or "").strip()
        if not eid or not quote:
            continue

        # Extract 1..N sentences from this quote (usually 1)
        for sent in _split_into_sentences(quote):
            if len(claims) >= max_claims:
                break

            # Skip extremely short fragments
            if len(sent) < 12:
                continue

            claims.append(
                {
                    K.CLAIM_ID: f"C{cid}",
                    K.CLAIM_TEXT: sent,
                    K.STAKES: _guess_stakes(sent),
                    K.EVIDENCE_EIDS: [eid],
                }
            )
            cid += 1

    # Fail-closed: ensure at least one claim exists
    if not claims:
        claims = [
            {
                K.CLAIM_ID: "C1",
                K.CLAIM_TEXT: "No extractable claim sentences were found in evidence quotes.",
                K.STAKES: "low",
                K.EVIDENCE_EIDS: [evidence_bank[0][K.EID]] if evidence_bank else ["E1"],
            }
        ]

    return claims
