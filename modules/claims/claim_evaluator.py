
#!/usr/bin/env python3
"""
FILE: modules/claims/claim_evaluator.py
VERSION: 0.4
LAST UPDATED: 2026-02-03
PURPOSE:
Deterministic Claim Evaluation Engine (Pass B).

Detects structural risk signals (text-only), not truth.

Locks:
- No randomness
- Stable ordering
- No motive inference (only flags intent-language presence)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from schema_names import K
from scoring_policy import score_claim_evaluations


# If True, flags "causes/caused/causing" as a *weak* causal signal,
# but NEVER as "causal_assertion".
FLAG_CAUSAL_VERB_PHRASE = False


RE_ABSOLUTES = re.compile(r"\b(always|never|everyone|no\s*one|all|none)\b", re.I)

# Strong causal connectors ONLY
RE_CAUSAL_CONNECTOR = re.compile(
    r"\b(because|therefore|thus|hence|due\s+to|as\s+a\s+result|result(?:s|ed)?\s+in|lead(?:s|ing)?\s+to)\b",
    re.I,
)

# Weak causal verb phrase (optional)
RE_CAUSAL_VERB = re.compile(r"\b(causes?|caused|causing)\b", re.I)

# Intent language (flag presence; do not infer motive)
RE_INTENT = re.compile(
    r"\b(wanted\s+to|intended\s+to|trying\s+to|planned\s+to|aimed\s+to|in\s+order\s+to|they\s+wanted\s+\w+)\b",
    re.I,
)

RE_PRONOUN = re.compile(r"\b(they|them|their|it|this|that|these|those)\b", re.I)
RE_NAMEISH = re.compile(r"\b[A-Z][a-z]{2,}\b")


def _s(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _l(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _d(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _claim_items(pack: Dict[str, Any]) -> List[Dict[str, Any]]:
    cr = _d(pack.get(K.CLAIM_REGISTRY))
    return [c for c in _l(cr.get(K.CLAIMS)) if isinstance(c, dict)]


def _claim_eids(claim: Dict[str, Any]) -> List[str]:
    eids = claim.get(K.EVIDENCE_EIDS)
    return [e for e in eids if isinstance(e, str) and e.strip()] if isinstance(eids, list) else []


def _mk_item(
    *, claim_id: str, issue_type: str, severity: str, explanation: str, eids: List[str]
) -> Dict[str, Any]:
    return {
        K.CLAIM_REF: claim_id,
        K.ISSUE_TYPE: issue_type,
        K.SEVERITY: severity,
        K.SUPPORT_CLASS: "text_signal_only",
        K.EXPLANATION: explanation,
        K.EVIDENCE_EIDS: eids,
    }


def _detect_for_claim(claim: Dict[str, Any]) -> List[Dict[str, Any]]:
    cid = _s(claim.get(K.CLAIM_ID)) or "C?"
    text = _s(claim.get(K.CLAIM_TEXT))
    eids = _claim_eids(claim)

    items: List[Dict[str, Any]] = []
    if not text:
        return items

    if RE_ABSOLUTES.search(text):
        items.append(
            _mk_item(
                claim_id=cid,
                issue_type="absolute_language",
                severity="moderate",
                explanation="Uses absolute terms requiring strong evidence or qualifiers.",
                eids=eids,
            )
        )

    # Strong causal assertion ONLY if explicit connector present
    if RE_CAUSAL_CONNECTOR.search(text):
        items.append(
            _mk_item(
                claim_id=cid,
                issue_type="causal_assertion",
                severity="moderate",
                explanation="Uses explicit causal connector language.",
                eids=eids,
            )
        )
    else:
        if FLAG_CAUSAL_VERB_PHRASE and RE_CAUSAL_VERB.search(text):
            items.append(
                _mk_item(
                    claim_id=cid,
                    issue_type="causal_verb_phrase",
                    severity="low",
                    explanation="Uses causal verb phrasing without explicit connector; mechanism/support may be needed.",
                    eids=eids,
                )
            )

    if RE_INTENT.search(text):
        items.append(
            _mk_item(
                claim_id=cid,
                issue_type="intent_inference_language",
                severity="elevated",
                explanation="Contains intent/motive language; requires strong evidence (flagged, not inferred).",
                eids=eids,
            )
        )

    if RE_PRONOUN.search(text):
        if not RE_NAMEISH.search(text):
            items.append(
                _mk_item(
                    claim_id=cid,
                    issue_type="ambiguous_referent",
                    severity="low",
                    explanation="Contains ambiguous referent (they/it/this) that may require disambiguation.",
                    eids=eids,
                )
            )

    return items


def run_claim_evaluator(pack: Dict[str, Any]) -> Dict[str, Any]:
    claims = _claim_items(pack)

    items: List[Dict[str, Any]] = []
    for c in claims:
        items.extend(_detect_for_claim(c))

    # Stable ordering => stable score + stable rendering
    items.sort(
        key=lambda x: (_s(x.get(K.CLAIM_REF)), _s(x.get(K.ISSUE_TYPE)), _s(x.get(K.SEVERITY)))
    )

    score, notes = score_claim_evaluations(items=items, claims=claims)

    return {
        K.MODULE_STATUS: "run",
        K.ITEMS: items,
        "score_0_100": int(score),
        "notes": ["Claim Evaluation Engine v0.4 — deterministic text signals.", *notes],
    }

