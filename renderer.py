#!/usr/bin/env python3
"""
FILE: renderer.py
VERSION: 0.6
LAST UPDATED: 2026-02-07
PURPOSE:
Render BiasLens output into readable Markdown for Streamlit.

Supports TWO schemas:
A) Stub/MVP schema (current JSON):
   - run_metadata, facts_layer, claim_registry (dict), evidence_bank, metrics, report_pack, etc.

B) Brick-7 pack schema (future/alternate):
   - article_layer, claim_registry (list), headline_body_delta (dict), reader_interpretation, etc.

Renderer goals (current step):
- Make the site feel real NOW, while staying integrity-safe.
- Surface pillar/socket run-status in Overview.
- Always expose pillar/socket raw objects in Scholar view for debugging.
- Reader view stays conservative: mention pillars only when meaningful; for MVP be explicit about "not run".

2026-02-07 ARCHITECTURE UPDATE:
- Timeline engine outputs are surfaced (Overview + Scholar) via renderer_sockets.py
- Dormant socket surfaced: article_layer.framing_evidence_alignment (status: not_run unless run)
- Scholar includes a small Pillar Index to prevent silent drift
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from rating_style import render_rating, score_to_stars
from schema_names import K

from reader_brain import build_reader_in_depth
from renderer_sockets import (
    build_article_sockets,
    append_overview_timeline,
    append_scholar_narrative_sockets,
)

# ─────────────────────────────────────────────────────────────
# Small helpers (type-safe, schema-tolerant)
# ─────────────────────────────────────────────────────────────


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


def _rating_rank(rating: Any) -> int:
    try:
        r = int(rating)
    except Exception:
        r = 3
    return max(1, min(5, r))


def _count_by_key(items: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        v = _s(it.get(key)) or "(missing)"
        counts[v] = counts.get(v, 0) + 1
    return counts


def _fmt_counts(counts: Dict[str, int]) -> str:
    parts = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ", ".join([f"{k}={v}" for k, v in parts]) if parts else "(none)"


# ─────────────────────────────────────────────────────────────
# Schema detection + title/url extraction
# ─────────────────────────────────────────────────────────────


def _is_stub_schema(pack: Dict[str, Any]) -> bool:
    return K.REPORT_PACK in pack and K.RUN_METADATA in pack and K.FACTS_LAYER in pack


def _title_url_from_stub(pack: Dict[str, Any]) -> Tuple[str, str]:
    ev = _l(pack.get(K.EVIDENCE_BANK))
    if ev:
        src = _d(_d(ev[0]).get(K.SOURCE))
        return _s(src.get(K.TITLE)) or "scraped_url", _s(src.get(K.URL))
    return "BiasLens Report", ""


def _title_url_from_brick7(pack: Dict[str, Any]) -> Tuple[str, str]:
    return _s(pack.get("source_title")) or "BiasLens Report", _s(pack.get("source_url"))


# ─────────────────────────────────────────────────────────────
# Evidence lookup (for quick quote surfacing)
# ─────────────────────────────────────────────────────────────


def _evidence_lookup(pack: Dict[str, Any]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for ev in _l(pack.get(K.EVIDENCE_BANK)):
        evd = _d(ev)
        eid = _s(evd.get(K.EID))
        quote = _s(evd.get(K.QUOTE))
        if eid and quote:
            lookup[eid] = quote
    return lookup


# ─────────────────────────────────────────────────────────────
# Pillar/socket status (schema-tolerant, integrity-safe)
# ─────────────────────────────────────────────────────────────


def _pillar_status_from_obj(obj: Any) -> str:
    """
    Conservative, schema-tolerant:
    - Uses K.MODULE_STATUS when present (run|not_run)
    - Falls back to legacy K.STATUS (read-only; never emit K.STATUS in new code)
    - Missing/unknown => not_run
    """
    if not isinstance(obj, dict):
        return K.MODULE_NOT_RUN

    st = obj.get(K.MODULE_STATUS) or obj.get(K.STATUS)  # legacy read-only support
    st = _s(st).lower()
    if st in (K.MODULE_RUN, K.MODULE_NOT_RUN):
        return st
    return K.MODULE_NOT_RUN


def _format_status(st: str) -> str:
    st = (st or "").strip().lower()
    return "✅ run" if st == K.MODULE_RUN else "⏳ not_run"


def _stub_pillar_statuses(pack: Dict[str, Any], sockets: Dict[str, Any]) -> Dict[str, str]:
    facts_layer = _d(pack.get(K.FACTS_LAYER))
    article_layer = _d(pack.get(K.ARTICLE_LAYER))

    return {
        "Reality Alignment": _pillar_status_from_obj(facts_layer.get(K.REALITY_ALIGNMENT_ANALYSIS)),
        "Reasoning Integrity (Premise Independence)": _pillar_status_from_obj(article_layer.get(K.PREMISE_INDEPENDENCE_ANALYSIS)),
        "Presentation Integrity": _pillar_status_from_obj(article_layer.get(K.PRESENTATION_INTEGRITY)),
        "Timeline (Narrative Structure)": _s(sockets.get("timeline_status")) or K.MODULE_NOT_RUN,
        "Framing ↔ Evidence Alignment": _s(sockets.get("framing_alignment_status")) or K.MODULE_NOT_RUN,
    }


def _append_overview_pillar_block(lines: List[str], pillar_status: Dict[str, str]) -> None:
    lines.append("## Pillars status")
    _bullet(lines, f"Reality Alignment: **{_format_status(pillar_status['Reality Alignment'])}**")
    _bullet(lines, f"Reasoning Integrity (Premise Independence): **{_format_status(pillar_status['Reasoning Integrity (Premise Independence)'])}**")
    _bullet(lines, f"Presentation Integrity: **{_format_status(pillar_status['Presentation Integrity'])}**")
    _bullet(lines, f"Timeline (Narrative Structure): **{_format_status(pillar_status['Timeline (Narrative Structure)'])}**")
    _bullet(lines, f"Framing ↔ Evidence Alignment: **{_format_status(pillar_status['Framing ↔ Evidence Alignment'])}**")
    lines.append("")


def _append_scholar_pillar_index(lines: List[str], pack: Dict[str, Any], sockets: Dict[str, Any]) -> None:
    facts_layer = _d(pack.get(K.FACTS_LAYER))
    article_layer = _d(pack.get(K.ARTICLE_LAYER))

    lines.append("## Pillar Index (status)")
    _bullet(lines, f"Reality Alignment: **{_format_status(_pillar_status_from_obj(facts_layer.get(K.REALITY_ALIGNMENT_ANALYSIS)))}**")
    _bullet(lines, f"Reasoning Integrity (Premise Independence): **{_format_status(_pillar_status_from_obj(article_layer.get(K.PREMISE_INDEPENDENCE_ANALYSIS)))}**")
    _bullet(lines, f"Presentation Integrity: **{_format_status(_pillar_status_from_obj(article_layer.get(K.PRESENTATION_INTEGRITY)))}**")
    _bullet(lines, f"Timeline (Narrative Structure): **{_format_status(_s(sockets.get('timeline_status')))}**")
    _bullet(lines, f"Framing ↔ Evidence Alignment: **{_format_status(_s(sockets.get('framing_alignment_status')))}**")
    lines.append("")


# ─────────────────────────────────────────────────────────────
# Integrity/grounding object lookup (naming drift tolerant)
# ─────────────────────────────────────────────────────────────


def _claim_integrity_obj(pack: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compatibility shim: claim integrity / grounding object has drifted in naming.
    We only read what exists; missing => {}.
    """
    cr = _d(pack.get(K.CLAIM_REGISTRY))

    key_candidates: List[str] = []
    for attr in ("CLAIM_GROUNDING", "CLAIM_INTEGRITY", "claim_grounding", "claim_integrity"):
        if hasattr(K, attr):
            key_candidates.append(getattr(K, attr))
    key_candidates.extend(["claim_grounding", "claim_integrity"])

    for k in key_candidates:
        obj = cr.get(k)
        if isinstance(obj, dict) and obj:
            return obj
    return {}


# ─────────────────────────────────────────────────────────────
# STUB/MVP schema rendering
# ─────────────────────────────────────────────────────────────


def _stub_overview(pack: Dict[str, Any]) -> str:
    title, url = _title_url_from_stub(pack)

    report_pack = _d(pack.get(K.REPORT_PACK))
    onep = _s(report_pack.get(K.SUMMARY_ONE_PARAGRAPH)) or "(No summary.)"

    metrics = _d(pack.get(K.METRICS))
    density = _d(metrics.get(K.EVIDENCE_DENSITY))
    ratio = density.get(K.EVIDENCE_TO_CLAIM_RATIO, None)
    density_label = _s(density.get(K.DENSITY_LABEL))
    num_claims = density.get(K.NUM_CLAIMS, None)
    num_evidence = density.get(K.NUM_EVIDENCE_ITEMS, None)

    findings_pack = _d(report_pack.get(K.FINDINGS_PACK))
    items = _l(findings_pack.get(K.ITEMS))  # findings_pack uses literal "items"

    evidence = _evidence_lookup(pack)

    # Sort findings by rating (desc), take top 5
    top = [_d(x) for x in items]
    top.sort(key=lambda x: _rating_rank(x.get(K.RATING)), reverse=True)
    top = top[:5]

    limits = _l(pack.get(K.DECLARED_LIMITS))

    article_layer = _d(pack.get(K.ARTICLE_LAYER))
    sockets = build_article_sockets(
        article_layer,
        module_status_key=K.MODULE_STATUS,
        legacy_status_key=K.STATUS,  # legacy read-only support
    )
    pillar_status = _stub_pillar_statuses(pack, sockets)

    lines: List[str] = []
    lines.append(f"# 🛡️ BiasLens Overview — {title}")
    if url:
        lines.append(f"*Source:* {url}")
    lines.append("")
    lines.append("## One-paragraph summary")
    lines.append(onep)
    lines.append("")

    _append_overview_pillar_block(lines, pillar_status)

    # Timeline mini-surface (Overview-only; emitted objects only)
    append_overview_timeline(lines, sockets)

    lines.append("## Top findings (evidence-cited)")
    if top:
        for itd in top:
            rating = itd.get(K.RATING, 3)
            claim_id = _s(itd.get(K.CLAIM_ID))
            txt = _s(itd.get(K.FINDING_TEXT))
            eids = _l(itd.get(K.EVIDENCE_EIDS))
            eid_str = ", ".join([_s(e) for e in eids if _s(e)])

            quote = ""
            if eids:
                q = evidence.get(_s(eids[0]), "")
                if q:
                    quote = _clip(q, 180)

            lines.append(f"- {render_rating(rating)} **{claim_id or 'Claim'}** — {txt}")
            if eid_str:
                lines.append(f"  - evidence: `{eid_str}`")
            if quote:
                lines.append(f"  - quote: “{quote}”")
    else:
        _bullet(lines, "No findings were emitted in this run.")

    # Claim Integrity snapshot (best-effort)
    ci = _claim_integrity_obj(pack)
    if ci:
        stars = ci.get(K.STARS, 3)
        lines.append("")
        lines.append("## Claim Integrity")
        _bullet(lines, f"Rating: **{render_rating(stars)}**")
        for b in _l(ci.get(K.RATIONALE_BULLETS))[:3]:
            _bullet(lines, _clip(_s(b), 160))

    lines.append("")
    lines.append("## Evidence discipline snapshot")
    if num_claims is not None and num_evidence is not None:
        _bullet(lines, f"Claims extracted: **{num_claims}**")
        _bullet(lines, f"Evidence quotes extracted: **{num_evidence}**")
    if ratio is not None:
        _bullet(lines, f"Evidence-to-claim ratio: **{ratio}** ({density_label or 'n/a'})")

    lines.append("")
    lines.append("## Declared limits / epistemic humility")
    if limits:
        for lim in limits[:5]:
            _bullet(lines, _s(_d(lim).get(K.STATEMENT)) or "(limit statement)")
    else:
        _bullet(lines, "No limits declared.")

    return "\n".join(lines)


def _stub_reader_in_depth(pack: Dict[str, Any]) -> str:
    title, url = _title_url_from_stub(pack)
    report_pack = _d(pack.get(K.REPORT_PACK))
    onep = _s(report_pack.get(K.SUMMARY_ONE_PARAGRAPH)) or "(No summary.)"

    metrics = _d(pack.get(K.METRICS))
    density = _d(metrics.get(K.EVIDENCE_DENSITY))
    density_label = _s(density.get(K.DENSITY_LABEL))
    ratio = density.get(K.EVIDENCE_TO_CLAIM_RATIO, None)

    counter = _d(metrics.get(K.COUNTEREVIDENCE_STATUS))
    counter_required = bool(counter.get(K.REQUIRED, False))
    counter_status = _s(counter.get(K.COUNTEREVIDENCE_RUN_STATUS) or counter.get(K.MODULE_STATUS) or counter.get(K.STATUS))
    counter_scope = _s(counter.get(K.SEARCH_SCOPE))
    counter_result = _s(counter.get(K.RESULT))

    hbd = _d(pack.get(K.HEADLINE_BODY_DELTA))
    hbd_present = bool(hbd.get(K.PRESENT, False))
    hbd_items = _l(hbd.get(K.ITEMS))

    claims = _l(_d(pack.get(K.CLAIM_REGISTRY)).get(K.CLAIMS))
    hi_stakes = [c for c in claims if _s(_d(c).get(K.STAKES)).lower() == "high"]

    guide = _s(report_pack.get(K.READER_INTERPRETATION_GUIDE))

    article_layer = _d(pack.get(K.ARTICLE_LAYER))
    sockets = build_article_sockets(article_layer, module_status_key=K.MODULE_STATUS, legacy_status_key=K.STATUS)
    pillar_status = _stub_pillar_statuses(pack, sockets)

    lines: List[str] = []
    lines.append(f"# 🧭 Reader In-Depth — {title}")
    if url:
        lines.append(f"*Source:* {url}")
    lines.append("")
    lines.append("## One-paragraph summary")
    lines.append(onep)
    lines.append("")
    lines.append("## What kind of piece is this (as a reader experience)?")

    if density_label in ("low",) or (isinstance(ratio, (int, float)) and ratio < 0.8):
        _bullet(lines, "This reads like **assertion-forward reporting**: claims are presented, but the visible evidence footprint is relatively thin.")
    else:
        _bullet(lines, "This reads like **quote-driven reporting**: multiple claims are anchored to quoted passages, but deeper verification may still be limited.")

    if hi_stakes:
        _bullet(lines, f"It contains **{len(hi_stakes)} high-stakes claim(s)** (higher consequences if wrong), which merit stronger sourcing and counterevidence checks.")
    else:
        _bullet(lines, "Most extracted claims are **low-stakes** (but can still shape interpretation through framing).")

    if hbd_present or hbd_items:
        _bullet(lines, "A **Headline–Body Delta** signal is present (headline framing may outpace body qualifiers).")
    else:
        _bullet(lines, "Headline–Body Delta was **not flagged** in this run (or not computed).")

    lines.append("")
    lines.append("## How it can work on readers (structure-based mechanisms)")
    _bullet(lines, "**Attribution-as-authority:** quotes from actors can feel like evidence, but quotes are not verification.")
    _bullet(lines, "**Reaction reporting risk:** repeating charged statements can transmit emotional payload even when the article stays neutral.")
    _bullet(lines, "**Scope inflation watch:** narrow facts can quietly become broad conclusions if not fenced with qualifiers.")
    _bullet(lines, "**Absence of expected context:** if key comparative cases are missing, conclusions may lean on what isn’t said.")

    lines.append("")
    lines.append("## What BiasLens can and cannot conclude from this run")

    ra = pillar_status["Reality Alignment"]
    pi = pillar_status["Reasoning Integrity (Premise Independence)"]
    pr = pillar_status["Presentation Integrity"]

    if ra != K.MODULE_RUN or pi != K.MODULE_RUN:
        lines.append(
            "This build did **not** run the two core analysis pillars yet (**Reality Alignment** and **Reasoning Integrity / Premise Independence**). "
            "So treat extracted claims as an **evidence index** (what was said), not as a determination of what is true or well-supported."
        )
    if pr != K.MODULE_RUN:
        lines.append(
            "Presentation Integrity was also **not run** here, so headline/body effects should be treated as unassessed unless explicitly flagged."
        )

    if guide:
        lines.append("")
        lines.append(_clip(guide, 600))

    lines.append("")
    lines.append("## Counterevidence status")
    _bullet(lines, f"Required: **{counter_required}**")
    _bullet(lines, f"Status: **{counter_status or 'n/a'}**")
    if counter_scope:
        _bullet(lines, f"Search scope: {counter_scope}")
    if counter_result:
        _bullet(lines, f"Result: {counter_result}")

    lines.append("")
    lines.append("## Reader checklist (quick)")
    _bullet(lines, "Ask: *What would change my mind?* (What counterevidence would matter?)")
    _bullet(lines, "Separate **who said it** from **whether it’s true**.")
    _bullet(lines, "Look for missing comparison cases or missing numbers (absence of expected context).")
    _bullet(lines, "Notice if the headline makes you feel something the body does not fully warrant.")

    return "\n".join(lines)


def _stub_scholar_in_depth(pack: Dict[str, Any]) -> str:
    title, url = _title_url_from_stub(pack)
    evidence = _evidence_lookup(pack)

    cr = _d(pack.get(K.CLAIM_REGISTRY))
    claims = _l(cr.get(K.CLAIMS))

    claim_evals = _d(cr.get(K.CLAIM_EVALUATIONS))
    ce_items = _l(claim_evals.get(K.ITEMS))
    ce_status = _s(claim_evals.get(K.MODULE_STATUS) or claim_evals.get(K.STATUS))
    ce_score = claim_evals.get(K.SCORE_0_100, claim_evals.get("score_0_100", None))

    report_pack = _d(pack.get(K.REPORT_PACK))
    findings_pack = _d(report_pack.get(K.FINDINGS_PACK))
    fitems = _l(findings_pack.get(K.ITEMS))  # literal "items"

    facts_layer = _d(pack.get(K.FACTS_LAYER))
    article_layer = _d(pack.get(K.ARTICLE_LAYER))

    sockets = build_article_sockets(article_layer, module_status_key=K.MODULE_STATUS, legacy_status_key=K.STATUS)

    lines: List[str] = []
    lines.append(f"# 🧪 Scholar In-Depth — {title}")
    if url:
        lines.append(f"*Source:* {url}")
    lines.append("")

    _append_scholar_pillar_index(lines, pack, sockets)

    lines.append("## Pillars (raw objects)")
    lines.append("### facts_layer.reality_alignment_analysis")
    lines.append("```json")
    lines.append(json.dumps(facts_layer.get(K.REALITY_ALIGNMENT_ANALYSIS, {}), indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")
    lines.append("### article_layer.premise_independence_analysis")
    lines.append("```json")
    lines.append(json.dumps(article_layer.get(K.PREMISE_INDEPENDENCE_ANALYSIS, {}), indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")
    lines.append("### article_layer.presentation_integrity")
    lines.append("```json")
    lines.append(json.dumps(article_layer.get(K.PRESENTATION_INTEGRITY, {}), indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    lines.append("## Narrative sockets (raw objects)")
    append_scholar_narrative_sockets(lines, sockets)

    lines.append("## Evidence bank (verbatim excerpts)")
    for eid, quote in list(evidence.items())[:25]:
        lines.append(f"- **{eid}**: {quote}")

    lines.append("")
    lines.append("## Claim registry (extracted)")
    for c in claims[:25]:
        cd = _d(c)
        lines.append(
            f"- **{_s(cd.get(K.CLAIM_ID))}** (stakes: {_s(cd.get(K.STAKES))}): "
            f"{_clip(_s(cd.get(K.CLAIM_TEXT)), 320)}"
        )
        lines.append(f"  - evidence_eids: {cd.get(K.EVIDENCE_EIDS, [])}")

    lines.append("")
    lines.append("## Claim Evaluation Engine (Pass B v0.1)")
    if claim_evals:
        _bullet(lines, f"Status: **{ce_status or 'n/a'}**")
        if isinstance(ce_score, (int, float)):
            stars = score_to_stars(int(ce_score))
            _bullet(lines, f"Score (0–100): **{ce_score}**  →  {render_rating(stars)}")
        else:
            _bullet(lines, "Score (0–100): (not provided)")

        if ce_items:
            typed = _count_by_key([_d(x) for x in ce_items], K.ISSUE_TYPE)
            sevd = _count_by_key([_d(x) for x in ce_items], K.SEVERITY)
            _bullet(lines, f"Issue types: {_fmt_counts(typed)}")
            _bullet(lines, f"Severities: {_fmt_counts(sevd)}")

            lines.append("")
            lines.append("### Top flagged items")
            sev_rank = {K.SEV_HIGH: 4, K.SEV_ELEVATED: 3, K.SEV_MODERATE: 2, K.SEV_LOW: 1}
            sorted_items = sorted(
                [_d(x) for x in ce_items],
                key=lambda it: (sev_rank.get(_s(it.get(K.SEVERITY)).lower(), 0), _s(it.get(K.CLAIM_REF))),
                reverse=True,
            )

            for it in sorted_items[:12]:
                claim_ref = _s(it.get(K.CLAIM_REF)) or "(claim?)"
                issue = _s(it.get(K.ISSUE_TYPE)) or "(issue?)"
                sev = _s(it.get(K.SEVERITY)) or "(sev?)"
                support = _s(it.get(K.SUPPORT_CLASS)) or "(support?)"
                expl = _s(it.get(K.EXPLANATION)) or ""
                eids = _l(it.get(K.EVIDENCE_EIDS))
                eid_str = ", ".join([_s(e) for e in eids if _s(e)])

                quote = ""
                if eids:
                    q = evidence.get(_s(eids[0]), "")
                    if q:
                        quote = _clip(q, 200)

                lines.append(f"- **{claim_ref}** — `{issue}` (severity: **{sev}**, support: **{support}**)")
                if expl:
                    lines.append(f"  - {expl}")
                if eid_str:
                    lines.append(f"  - evidence: `{eid_str}`")
                if quote:
                    lines.append(f"  - quote: “{quote}”")
        else:
            _bullet(lines, "No claim evaluation items emitted.")
    else:
        _bullet(lines, "claim_registry.claim_evaluations not present in this run.")

    lines.append("")
    lines.append("## Findings pack (current run)")
    if fitems:
        for it in fitems[:25]:
            itd = _d(it)
            claim_id = _s(itd.get(K.CLAIM_ID))
            rest = _clip(_s(itd.get(K.RESTATED_CLAIM)), 240)
            txt = _s(itd.get(K.FINDING_TEXT))
            rating = itd.get(K.RATING, 3)
            eids = itd.get(K.EVIDENCE_EIDS, [])
            lines.append(f"- {render_rating(rating)} **{claim_id}**: {rest}")
            lines.append(f"  - finding: {txt}")
            lines.append(f"  - evidence_eids: {eids}")
    else:
        lines.append("- (No scholar findings yet in this schema/run.)")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# BRICK-7 schema rendering (forward-compat)
# ─────────────────────────────────────────────────────────────


def _brick7_overview(pack: Dict[str, Any]) -> str:
    title, url = _title_url_from_brick7(pack)

    article_layer = _d(pack.get(K.ARTICLE_LAYER))
    onep = _s(article_layer.get("one_paragraph_summary")) or "(No summary.)"

    evidence_bank = _l(pack.get(K.EVIDENCE_BANK))
    claim_registry = _l(pack.get(K.CLAIM_REGISTRY))
    hbd = _d(pack.get(K.HEADLINE_BODY_DELTA))
    facts_layer = _d(pack.get(K.FACTS_LAYER))

    sockets = build_article_sockets(article_layer, module_status_key=K.MODULE_STATUS, legacy_status_key=K.STATUS)

    # Reuse the same labels/keys as stub pillar block (but compute from Brick7 objects)
    pillar_status = {
        "Reality Alignment": _pillar_status_from_obj(facts_layer.get(K.REALITY_ALIGNMENT_ANALYSIS)),
        "Reasoning Integrity (Premise Independence)": _pillar_status_from_obj(article_layer.get(K.PREMISE_INDEPENDENCE_ANALYSIS)),
        "Presentation Integrity": _pillar_status_from_obj(article_layer.get(K.PRESENTATION_INTEGRITY)),
        "Timeline (Narrative Structure)": _s(sockets.get("timeline_status")) or K.MODULE_NOT_RUN,
        "Framing ↔ Evidence Alignment": _s(sockets.get("framing_alignment_status")) or K.MODULE_NOT_RUN,
    }

    lines: List[str] = []
    lines.append(f"# 🛡️ BiasLens Overview — {title}")
    if url:
        lines.append(f"*Source:* {url}")
    lines.append("")
    lines.append("## One-paragraph summary")
    lines.append(onep)
    lines.append("")

    _append_overview_pillar_block(lines, pillar_status)
    append_overview_timeline(lines, sockets)

    lines.append("## What was analyzed")
    _bullet(lines, f"Evidence quotes extracted: **{len(evidence_bank)}**")
    _bullet(lines, f"Claims extracted: **{len(claim_registry)}**")
    lines.append("")

    lines.append("## Headline–Body Delta")
    _bullet(lines, f"Headline: **{_s(hbd.get('headline')) or '(not provided)'}**")
    _bullet(lines, f"Body qualifiers: {_s(hbd.get('body_key_qualifiers')) or '(unknown)'}")

    return "\n".join(lines)


def _brick7_reader(pack: Dict[str, Any]) -> str:
    title, url = _title_url_from_brick7(pack)
    article = _d(pack.get(K.ARTICLE_LAYER))
    onep = _s(article.get("one_paragraph_summary")) or "(No summary.)"
    reader = _d(pack.get("reader_interpretation"))
    mechs = _l(reader.get("named_mechanisms"))

    lines: List[str] = []
    lines.append(f"# 🧭 Reader In-Depth — {title}")
    if url:
        lines.append(f"*Source:* {url}")
    lines.append("")
    lines.append("## One-paragraph summary")
    lines.append(onep)
    lines.append("")
    lines.append("## Mechanisms (structure-based)")
    if mechs:
        for m in mechs[:12]:
            md = _d(m)
            _bullet(lines, f"**{_s(md.get('mechanism_name'))}** — {_s(md.get('plain_language_explanation'))}")
    else:
        _bullet(lines, "(No mechanisms listed.)")

    return "\n".join(lines)


def _brick7_scholar(pack: Dict[str, Any]) -> str:
    title, url = _title_url_from_brick7(pack)
    lines: List[str] = []
    lines.append(f"# 🧪 Scholar In-Depth — {title}")
    if url:
        lines.append(f"*Source:* {url}")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(pack, indent=2, ensure_ascii=False))
    lines.append("```")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Public API used by streamlit_app.py
# ─────────────────────────────────────────────────────────────


def render_overview(pack: Dict[str, Any]) -> str:
    return _stub_overview(pack) if _is_stub_schema(pack) else _brick7_overview(pack)


def render_reader_in_depth(pack: Dict[str, Any]) -> str:
    # Reader Brain is downstream rendering intelligence (Phase B).
    return build_reader_in_depth(pack) if _is_stub_schema(pack) else _brick7_reader(pack)


def render_scholar_in_depth(pack: Dict[str, Any]) -> str:
    return _stub_scholar_in_depth(pack) if _is_stub_schema(pack) else _brick7_scholar(pack)
