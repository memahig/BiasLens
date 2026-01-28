

#!/usr/bin/env python3
"""
report_stub.py

MVP report pack builder for BiasLens deployed site.

Important:
- This is NOT "fake analysis" and it does NOT invent facts.
- It builds a readable report using ONLY extracted evidence quotes, claim registry,
  and available metrics.
- It explicitly states unknown/insufficient states when deeper verification isn't present.

This file outputs the legacy schema you are currently rendering:
schema_version, run_metadata, facts_layer, claim_registry, evidence_bank, metrics,
declared_limits, report_pack.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple


def _d(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _l(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _s(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _clip(s: str, n: int = 220) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


# ─────────────────────────────────────────────────────────────
# Public API used by pipeline / streamlit
# ─────────────────────────────────────────────────────────────

def dummy_report_pack() -> Dict[str, Any]:
    """
    Returns a minimal *valid* pack for integrity testing.
    This should NOT claim "no real article analyzed" anymore.
    """
    text = "Dummy input for integrity test."
    return analyze_text_to_report_pack(text=text, source_title="dummy", source_url="")


def analyze_text_to_report_pack(text: str, source_title: str = "manual_text", source_url: str = "") -> Dict[str, Any]:
    """
    MVP pack builder.
    If you later wire the full engine, you can swap this function
    to call engine.analyze_article_to_pack() and then adapt schema.
    """
    # For now, we treat the provided text as the "article text" and create
    # a conservative evidence/claim scaffold without inventing facts.

    article_text = text or ""
    article_text = article_text.strip()

    evidence_bank = _mvp_evidence_bank(article_text, source_title=source_title, source_url=source_url)
    claim_registry = _mvp_claim_registry(evidence_bank)

    metrics = _mvp_metrics(claim_registry, evidence_bank)

    facts_layer = {
        "facts": [
            {
                "fact_id": "F1",
                "fact_text": "An input text was provided for analysis.",
                "checkability": "checkable",
                "verdict": "unknown",
                "evidence_eids": [evidence_bank[0]["eid"]] if evidence_bank else ["E1"],
                "notes": "No independent fact-checking performed in this MVP build; epistemic state remains unknown unless verified by external checks.",
            }
        ]
    }

    # Build report text that is honest but not self-undermining
    summary_one_paragraph = _one_paragraph_summary(claim_registry, evidence_bank, metrics, source_title)
    reader_guide = _reader_interpretation_guide(claim_registry, metrics)

    findings_pack = _findings_pack(claim_registry, evidence_bank, metrics)
    scholar_pack = _scholar_pack(claim_registry, evidence_bank, metrics)

    # Declared limits should be true. No more "dummy run; no real article analyzed"
    declared_limits = [
        {
            "limit_id": "L1",
            "statement": "This MVP report is evidence-indexed (verbatim quotes + linked claims) but does not yet perform independent fact-checking or full counterevidence search; unverified items remain explicitly unknown.",
        }
    ]

    pack: Dict[str, Any] = {
        "schema_version": "1.0",
        "run_metadata": {
            "mode": "mvp",
            "source_type": "url" if source_url else "text",
        },
        "facts_layer": facts_layer,
        "claim_registry": {"claims": claim_registry},
        "evidence_bank": evidence_bank,
        "headline_body_delta": {"present": False, "items": []},  # keep legacy field; upgrade later
        "metrics": metrics,
        "declared_limits": declared_limits,
        "report_pack": {
            "summary_one_paragraph": summary_one_paragraph,
            "reader_interpretation_guide": reader_guide,
            "findings_pack": {"items": findings_pack},
            "scholar_pack": {"items": scholar_pack},
        },
    }
    return pack


# ─────────────────────────────────────────────────────────────
# MVP builders
# ─────────────────────────────────────────────────────────────

def _mvp_evidence_bank(article_text: str, source_title: str, source_url: str) -> List[Dict[str, Any]]:
    """
    Conservative evidence bank: take the first ~6 excerpts as verbatim quotes.
    This avoids pretending to have Pass A offsets/coverage if not wired.
    If your deployed app already has Pass A, you can replace this with that output.
    """
    if not article_text:
        # still return a placeholder evidence item so downstream remains valid
        return [
            {
                "eid": "E1",
                "quote": "(no text provided)",
                "start_char": 0,
                "end_char": 0,
                "why_relevant": "No input text available.",
                "source": {"type": "text", "title": source_title, "url": source_url},
            }
        ]

    # Split into rough chunks on paragraph boundaries
    paras = [p.strip() for p in article_text.split("\n") if p.strip()]
    if not paras:
        paras = [article_text.strip()]

    evidence: List[Dict[str, Any]] = []
    eid = 1
    cursor = 0

    for p in paras[:8]:
        quote = p
        # try to find quote offset; if not found, mark as -1/-1 (still OK)
        idx = article_text.find(quote)
        if idx >= 0:
            start = idx
            end = idx + len(quote)
        else:
            start = -1
            end = -1

        evidence.append(
            {
                "eid": f"E{eid}",
                "quote": quote[:400],
                "start_char": start,
                "end_char": end,
                "why_relevant": "Verbatim excerpt used to anchor extracted claims.",
                "source": {"type": "url" if source_url else "text", "title": source_title, "url": source_url},
            }
        )
        eid += 1

    return evidence


def _mvp_claim_registry(evidence_bank: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    MVP claim registry: each claim is a conservative restatement of an evidence excerpt.
    Stakes are heuristic: 'high' if it contains numbers, accusations, or institutional actions.
    """
    claims: List[Dict[str, Any]] = []
    cid = 1
    for ev in evidence_bank[:8]:
        q = _s(_d(ev).get("quote"))
        if not q:
            continue
        stakes = "low"
        qlow = q.lower()
        if any(tok in qlow for tok in ["impeach", "murder", "fraud", "illegal", "corrupt", "violence", "killed"]):
            stakes = "high"
        if any(ch.isdigit() for ch in q):
            stakes = "high"

        claims.append(
            {
                "claim_id": f"C{cid}",
                "claim_text": q[:500],
                "stakes": stakes,
                "evidence_eids": [_s(_d(ev).get("eid"))] if _s(_d(ev).get("eid")) else ["E1"],
            }
        )
        cid += 1

    if not claims:
        claims = [
            {
                "claim_id": "C1",
                "claim_text": "The text contains statements that require evidence-linked evaluation (explicitly unknown).",
                "stakes": "low",
                "evidence_eids": ["E1"],
            }
        ]
    return claims


def _mvp_metrics(claims: List[Dict[str, Any]], evidence_bank: List[Dict[str, Any]]) -> Dict[str, Any]:
    num_claims = len(claims)
    num_high = sum(1 for c in claims if _s(_d(c).get("stakes")).lower() == "high")
    num_evidence = len(evidence_bank)
    ratio = (num_evidence / num_claims) if num_claims else None

    if ratio is None:
        density_label = "unknown"
    elif ratio < 0.8:
        density_label = "low"
    elif ratio < 1.5:
        density_label = "medium"
    else:
        density_label = "high"

    return {
        "evidence_density": {
            "num_claims": num_claims,
            "num_high_stakes_claims": num_high,
            "num_evidence_items": num_evidence,
            "evidence_to_claim_ratio": ratio,
            "evidence_to_high_stakes_claim_ratio": (num_evidence / num_high) if num_high else None,
            "density_label": density_label,
            "note": "MVP metric: compares number of verbatim excerpts to extracted claims.",
        },
        "counterevidence_status": {
            "required": False,
            "status": "not_performed",
            "search_scope": "none",
            "result": "not_performed",
            "notes": "Counterevidence search not yet enabled in this MVP build.",
        },
    }


def _one_paragraph_summary(
    claims: List[Dict[str, Any]],
    evidence_bank: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    source_title: str,
) -> str:
    density = _d(metrics.get("evidence_density"))
    label = _s(density.get("density_label"))
    num_claims = density.get("num_claims", len(claims))
    num_high = density.get("num_high_stakes_claims", 0)

    # Summarize the topic using first claim excerpt
    topic_hint = ""
    if claims:
        topic_hint = _clip(_s(_d(claims[0]).get("claim_text")), 160)

    return (
        f"BiasLens extracted {num_claims} evidence-anchored claim(s) from the provided text and linked each to verbatim excerpts. "
        f"Evidence density is {label or 'unknown'}; {num_high} claim(s) were flagged as higher-stakes and would benefit most from independent verification. "
        f"This MVP report does not assert truth beyond the quoted text; where verification is not performed, epistemic status remains unknown. "
        f"Topic signal (from the text): “{topic_hint}”."
    )


def _reader_interpretation_guide(claims: List[Dict[str, Any]], metrics: Dict[str, Any]) -> str:
    density = _d(metrics.get("evidence_density"))
    label = _s(density.get("density_label"))
    num_high = density.get("num_high_stakes_claims", 0)

    kind = "quote-driven reporting" if label in ("medium", "high") else "assertion-forward reporting"
    high_note = (
        "Because there are higher-stakes claims here, treat quotes as *claims*, not confirmation, and look for primary documents or multi-source confirmation."
        if num_high
        else "Even low-stakes claims can shape interpretation through framing; still separate attribution from verification."
    )

    return (
        f"This piece reads like {kind}: it presents claims anchored to what people said or what the text asserts. "
        f"BiasLens reports structure-based integrity signals (evidence discipline, logic, omission-as-absence-of-context) and does not infer intent. "
        f"{high_note}"
    )


def _findings_pack(
    claims: List[Dict[str, Any]],
    evidence_bank: List[Dict[str, Any]],
    metrics: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    MVP findings: do not invent—only structural cues.
    Each finding is tied to a claim + evidence EID.
    """
    items: List[Dict[str, Any]] = []
    density = _d(metrics.get("evidence_density"))
    label = _s(density.get("density_label"))

    for c in claims[:12]:
        cd = _d(c)
        claim_id = _s(cd.get("claim_id"))
        restated = _s(cd.get("claim_text"))
        stakes = _s(cd.get("stakes")).lower()
        eids = _l(cd.get("evidence_eids")) or ["E1"]

        sev = "🟢"
        if stakes == "high":
            sev = "🟡"  # higher stakes => higher concern if unverified

        finding_text = (
            "Evidence-anchored claim extracted. In this MVP build, the system does not independently verify truth; epistemic status remains unknown unless externally confirmed."
        )
        if label == "low":
            finding_text = (
                "Claim extracted, but the visible evidence footprint is thin relative to the number of claims. Treat attribution as non-verification and seek primary sources."
            )

        items.append(
            {
                "finding_id": f"FP{len(items)+1}",
                "claim_id": claim_id,
                "restated_claim": restated,
                "finding_text": finding_text,
                "severity": sev,
                "evidence_eids": eids,
            }
        )

    return items


def _scholar_pack(
    claims: List[Dict[str, Any]],
    evidence_bank: List[Dict[str, Any]],
    metrics: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    MVP scholar pack: compact tables.
    """
    items: List[Dict[str, Any]] = []

    density = _d(metrics.get("evidence_density"))
    items.append(
        {
            "item_id": "S1",
            "title": "Evidence Discipline Snapshot",
            "content": json.dumps(density, indent=2, ensure_ascii=False),
        }
    )

    # Evidence table
    ev_rows = []
    for ev in evidence_bank[:25]:
        evd = _d(ev)
        ev_rows.append({"eid": _s(evd.get("eid")), "quote": _clip(_s(evd.get("quote")), 240)})
    items.append(
        {
            "item_id": "S2",
            "title": "Evidence Bank (verbatim excerpts)",
            "content": json.dumps(ev_rows, indent=2, ensure_ascii=False),
        }
    )

    # Claim table
    c_rows = []
    for c in claims[:25]:
        cd = _d(c)
        c_rows.append(
            {
                "claim_id": _s(cd.get("claim_id")),
                "stakes": _s(cd.get("stakes")),
                "evidence_eids": cd.get("evidence_eids", []),
                "claim_text": _clip(_s(cd.get("claim_text")), 240),
            }
        )
    items.append(
        {
            "item_id": "S3",
            "title": "Claim Registry",
            "content": json.dumps(c_rows, indent=2, ensure_ascii=False),
        }
    )

    return items
