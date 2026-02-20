#!/usr/bin/env python3
"""

FILE: report_stub.py
VERSION: 1.0
LAST UPDATED: 2026-02-02
PURPOSE:
BiasLens MVP builder that produces schema-legal, fail-closed-friendly output.

Contract alignment (based on your actual codebase):
- schema_names.K is the key registry.
- integrity_validator.validate_output() requires:
    schema_version, run_metadata, evidence_bank, facts_layer, claim_registry, metrics, report_pack
  and requires metrics.evidence_density (with correct evidence_to_claim_ratio).
- enforcers.integrity_objects.enforce_integrity_objects() requires:
    facts_layer.fact_verification to be a valid integrity object.
    article_layer.article_integrity to be a valid integrity object.
- enforcers.article_enforcer.enforce_article_layer() requires:
    if article_layer present -> article_layer.presentation_integrity.status in {"run","not_run"}
- NEW REQUIRED PILLARS (enforcer):
    article_layer.premise_independence_analysis must exist (Reasoning Integrity pillar)
    facts_layer.reality_alignment_analysis must exist (Reality Alignment pillar)

MVP safety guarantees:
- No hallucinations: facts/claims are derived verbatim from input text.
- Verdicts remain "unknown" in MVP (no independent verification).
"""
# 🔒 ARCHITECTURE LOCK — PRIMARY EMITTER
# This file is the single authorized schema emitter for BiasLens.
#
# Rules:
# - Do NOT create alternate emitters.
# - Do NOT fork the schema.
# - Schema changes REQUIRE a version bump.
# - Pass B must extend this output, never replace it.

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from schema_names import K
from enforcers.integrity_objects import STAR_MAP, CONF_ALLOWED
from enforcers.facts_star_policy import clamp_fact_table_stars


_SENT_SPLIT_RE = re.compile(r"(?<=[\.\!\?])\s+")


# -----------------------------
# Small helpers
# -----------------------------
def _s(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _split_sentences(text: str) -> List[str]:
    t = (text or "").strip()
    if not t:
        return []
    parts = _SENT_SPLIT_RE.split(t)
    out: List[str] = []
    for p in parts:
        p = p.strip()
        if p:
            out.append(p)
    return out


def _safe_confidence(conf: str) -> str:
    return conf if conf in CONF_ALLOWED else sorted(CONF_ALLOWED)[0]


# -----------------------------
# Integrity object factory (must match enforcers/integrity_objects.py)
# -----------------------------
def _integrity_object(
    *,
    stars: int,
    confidence: str,
    rationale_bullets: List[str],
    how_to_improve: List[str],
    gating_flags: Optional[List[str]] = None,
    maintenance_notes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if stars not in STAR_MAP:
        stars = 3

    label, color = STAR_MAP[stars]
    confidence = _safe_confidence(confidence)

    rb = list(rationale_bullets or [])
    if len(rb) == 0:
        rb = ["MVP: limited verification; interpret conservatively."]

    gf = list(gating_flags or [])
    how = list(how_to_improve or [])
    maint = list(maintenance_notes or [])

    # Contract requirements:
    # - rationale_bullets non-empty always
    # - how_to_improve non-empty for stars <= 4
    if stars <= 4 and len(how) == 0:
        how = [
            "Add independent verification and evidence for high-impact claims.",
            "Reduce unknown/uncertain states by expanding retrieval scope and checks.",
        ]

    return {
        K.STARS: stars,
        K.LABEL: label,
        K.COLOR: color,
        K.CONFIDENCE: confidence,
        K.RATIONALE_BULLETS: rb,
        K.GATING_FLAGS: gf,
        K.HOW_TO_IMPROVE: how,
        K.MAINTENANCE_NOTES: maint,
    }


# -----------------------------
# Evidence / Facts / Claims builders (MVP)
# -----------------------------
def _build_evidence_bank(
    *,
    text: str,
    source_title: Optional[str],
    source_url: Optional[str],
    max_items: int = 40,
) -> List[Dict[str, Any]]:
    t = (text or "").strip()
    if not t:
        return []

    sents = _split_sentences(t)
    if not sents:
        sents = [t]

    bank: List[Dict[str, Any]] = []
    cursor = 0
    eid_n = 1

    for s in sents:
        if len(bank) >= max_items:
            break
        s = s.strip()
        if not s:
            continue

        idx = t.find(s, cursor)
        if idx < 0:
            idx = t.find(s)
        if idx < 0:
            continue

        start = idx
        end = idx + len(s)
        cursor = end

        eid = f"E{eid_n}"
        eid_n += 1

        bank.append(
            {
                K.EID: eid,
                K.QUOTE: s,
                K.START_CHAR: int(start),
                K.END_CHAR: int(end),
                K.SOURCE: {
                    K.TYPE: "text",
                    K.TITLE: _s(source_title),
                    K.URL: _s(source_url),
                },
            }
        )

    return bank


def _extract_facts_from_evidence(evidence_bank: List[Dict[str, Any]], *, max_facts: int = 40) -> List[Dict[str, Any]]:
    facts: List[Dict[str, Any]] = []
    fid_n = 1
    for e in evidence_bank:
        if len(facts) >= max_facts:
            break
        if not isinstance(e, dict):
            continue
        quote = _s(e.get(K.QUOTE))
        eid = _s(e.get(K.EID))
        if not quote or not eid:
            continue

        facts.append(
            {
                K.FACT_ID: f"F{fid_n}",
                K.FACT_TEXT: quote,
                K.CHECKABILITY: "checkable",
                K.VERDICT: "unknown",
                K.EVIDENCE_EIDS: [eid],
                K.NOTES: "MVP: verbatim sentence-fact; not independently verified.",
            }
        )
        fid_n += 1
    return facts


def _build_claims_from_evidence(evidence_bank: List[Dict[str, Any]], *, max_claims: int = 25) -> List[Dict[str, Any]]:
    claims: List[Dict[str, Any]] = []
    cid_n = 1
    for e in evidence_bank:
        if len(claims) >= max_claims:
            break
        if not isinstance(e, dict):
            continue
        quote = _s(e.get(K.QUOTE))
        eid = _s(e.get(K.EID))
        if not quote or not eid:
            continue

        claims.append(
            {
                K.CLAIM_ID: f"C{cid_n}",
                K.CLAIM_TEXT: quote,
                K.STAKES: "low",
                K.EVIDENCE_EIDS: [eid],
            }
        )
        cid_n += 1
    return claims


# -----------------------------
# Public builder
# -----------------------------
def analyze_text_to_report_pack(
    *,
    text: str,
    source_title: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Dict[str, Any]:
    evidence_bank = _build_evidence_bank(text=text, source_title=source_title, source_url=source_url, max_items=40)
    print(f"[DBG][PASS_A][report_stub.py:241] evidence_bank_items={len(evidence_bank)}")
    us_hits = [ev for ev in evidence_bank if ev.get(K.QUOTE, "").strip() in ("The U.S.", "The U.S")]
    print(f"[DBG][PASS_A][report_stub.py:241] us_sentence_hits={len(us_hits)} eids={[ev.get(K.EID) for ev in us_hits]}")
    facts = _extract_facts_from_evidence(evidence_bank, max_facts=40)
    claims = _build_claims_from_evidence(evidence_bank, max_claims=25)

    proposed_stars = 3
    final_stars, max_star = clamp_fact_table_stars(stars=proposed_stars, facts=facts)

    fact_verification = _integrity_object(
        stars=final_stars,
        confidence="low",
        rationale_bullets=[
            "MVP: facts are verbatim sentence-facts derived from evidence quotes; no independent verification performed (verdict=unknown).",
            f"Stars are clamped by policy based on verdict distribution (max_allowed={max_star}).",
        ],
        how_to_improve=[
            "Add independent fact-checking so checkable facts can move from 'unknown' to true/false with sourced support.",
            "Expand verification coverage to reduce the proportion of unknown verdicts.",
        ],
        gating_flags=["mvp:no_independent_fact_check", "policy:fact_table_star_cap"],
    )

    # REQUIRED PILLAR: Reality Alignment analysis (placeholder; not_run)
    reality_alignment_analysis = {
        K.MODULE_STATUS: "not_run",
        "notes": [
            "Required pillar socket present. MVP does not yet perform independent fact-checking/retrieval.",
            "When implemented, this module will independently verify checkable facts against external sources (not just quoted actors).",
        ],
    }

    # Article integrity (required by current integrity_objects enforcer)
    article_integrity = _integrity_object(
        stars=2,
        confidence="low",
        rationale_bullets=[
            "MVP: no independent verification or argument evaluation performed; article-level integrity is conservative by default.",
            "This rating is a placeholder integrity object required by the current enforcer contract.",
        ],
        how_to_improve=[
            "Run Fact Layer verification (reality alignment) and update verdict distributions.",
            "Evaluate claim-level support, premise dependence, and argument structure before raising this rating.",
        ],
        gating_flags=["mvp:article_integrity_placeholder"],
    )

    # Presentation integrity socket (article_enforcer requires status if article_layer exists)
    presentation_integrity = {K.MODULE_STATUS: "not_run"}

    # REQUIRED PILLAR: Premise Independence / Reasoning Integrity (placeholder; not_run)
    premise_independence_analysis = {
        K.MODULE_STATUS: "not_run",
        "notes": [
            "Required pillar socket present. MVP does not yet compute premise dependence / premise-independence.",
            "When implemented, this module will identify claims whose support depends on accepting contested premises (and report that at Scholar level; Reader level when it changes meaning).",
        ],
    }

    num_claims = len(claims)
    num_evidence_items = len(evidence_bank)
    evidence_to_claim_ratio = num_evidence_items / max(1, num_claims)

    out: Dict[str, Any] = {
        K.SCHEMA_VERSION: K.SCHEMA_VERSION_CURRENT,
        K.RUN_METADATA: {K.MODE: "mvp", K.SOURCE_TYPE: "text"},
        K.EVIDENCE_BANK: evidence_bank,
        K.FACTS_LAYER: {
            K.FACTS: facts,
            K.fact_verification: fact_verification,
            # new required pillar socket
            K.REALITY_ALIGNMENT_ANALYSIS: reality_alignment_analysis,
        },
        K.CLAIM_REGISTRY: {K.CLAIMS: claims},
        K.ARTICLE_LAYER: {
            K.ARTICLE_INTEGRITY: article_integrity,
            K.PRESENTATION_INTEGRITY: presentation_integrity,
            # new required pillar socket
            K.PREMISE_INDEPENDENCE_ANALYSIS: premise_independence_analysis,
        },
        K.METRICS: {
            K.EVIDENCE_DENSITY: {
                K.NUM_CLAIMS: num_claims,
                K.NUM_EVIDENCE_ITEMS: num_evidence_items,
                K.EVIDENCE_TO_CLAIM_RATIO: evidence_to_claim_ratio,
                K.DENSITY_LABEL: "mvp",
                K.NOTE: "MVP density is computed from verbatim stated-passage claims and evidence items.",
            }
        },
        K.DECLARED_LIMITS: [
            {
                K.LIMIT_ID: "L1",
                K.STATEMENT: (
                    "This MVP build extracts an evidence bank from input text, then derives sentence-facts and stated-passage claims. "
                    "No independent verification or counterevidence retrieval is performed; fact verdicts remain 'unknown'."
                ),
            }
        ],
        K.REPORT_PACK: {
            K.SUMMARY_ONE_PARAGRAPH: (
                "BiasLens MVP extracted verbatim evidence passages from the input text, then produced a minimal Facts Layer "
                "and a conservative Claim Registry tethered to those passages. No independent verification was performed, "
                "so checkable facts remain 'unknown' and integrity ratings should be interpreted conservatively."
            ),
            K.READER_INTERPRETATION_GUIDE: (
                "Reader guide (MVP): This output is quote-tethered and conservative: it shows what was said (verbatim) but does not "
                "yet verify accuracy. Treat it as an evidence index and a checklist for what to verify next, not as a fact-check."
            ),
            K.FINDINGS_PACK: {K.ITEMS: []},
        },
    }

    return out


def dummy_report_pack() -> Dict[str, Any]:
    return analyze_text_to_report_pack(
        text="This is a dummy test sentence. It exists to verify validator/enforcer behavior.",
        source_title="dummy",
        source_url="",
    )
