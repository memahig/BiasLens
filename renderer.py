
#!/usr/bin/env python3
"""
renderer.py

Renders BiasLens output into readable Markdown.

Supports TWO schemas:
A) Legacy/stub schema (your current deployed JSON):
   - run_metadata, facts_layer, claim_registry, evidence_bank, metrics, report_pack, etc.

B) Brick-7 pack schema (future/alternate):
   - article_layer, claim_registry (list), claim_evaluations, headline_body_delta (dict), reader_interpretation, etc.

Goal: Make the site feel real NOW (Reader voice + substantive Overview),
without forcing a schema migration first.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from rating_style import render_rating



# ─────────────────────────────────────────────────────────────
# small helpers
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

def _is_stub_schema(pack: Dict[str, Any]) -> bool:
    # Your pasted pack has these keys
    return "report_pack" in pack and "run_metadata" in pack and "facts_layer" in pack

def _title_url_from_stub(pack: Dict[str, Any]) -> Tuple[str, str]:
    # evidence_bank[0].source.title/url exists in your pack
    ev = _l(pack.get("evidence_bank"))
    if ev:
        src = _d(_d(ev[0]).get("source"))
        return _s(src.get("title")) or "scraped_url", _s(src.get("url"))
    return "BiasLens Report", ""

def _title_url_from_brick7(pack: Dict[str, Any]) -> Tuple[str, str]:
    return _s(pack.get("source_title")) or "BiasLens Report", _s(pack.get("source_url"))

def _rating_rank(rating) -> int:
    try:
        r = int(rating)
    except Exception:
        r = 3
    return max(1, min(5, r))

def _evidence_lookup(pack: Dict[str, Any]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for ev in _l(pack.get("evidence_bank")):
        evd = _d(ev)
        eid = _s(evd.get("eid"))
        quote = _s(evd.get("quote"))
        if eid and quote:
            lookup[eid] = quote
    return lookup


# ─────────────────────────────────────────────────────────────
# LEGACY/STUB schema rendering
# ─────────────────────────────────────────────────────────────

def _stub_overview(pack: Dict[str, Any]) -> str:
    title, url = _title_url_from_stub(pack)
    report_pack = _d(pack.get("report_pack"))
    onep = _s(report_pack.get("summary_one_paragraph")) or "(No summary.)"

    metrics = _d(pack.get("metrics"))
    density = _d(metrics.get("evidence_density"))
    ratio = density.get("evidence_to_claim_ratio", None)
    density_label = _s(density.get("density_label"))
    num_claims = density.get("num_claims", None)
    num_evidence = density.get("num_evidence_items", None)

    findings_pack = _d(report_pack.get("findings_pack"))
    items = _l(findings_pack.get("items"))

    evidence = _evidence_lookup(pack)

    # Take top findings (if any)
    top = items[:]
    top.sort(key=lambda x: _rating_rank(_d(x).get("rating")), reverse=True)
    top = top[:5]

    limits = _l(pack.get("declared_limits"))

    lines: List[str] = []
    lines.append(f"# 🛡️ BiasLens Overview — {title}")
    if url:
        lines.append(f"*Source:* {url}")
    lines.append("")
    lines.append("## One-paragraph summary")
    lines.append(onep)
    lines.append("")
    lines.append("## Top findings (evidence-cited)")
    if top:
        for it in top:
            itd = _d(it)
            rating = itd.get("rating", 3)
            claim_id = _s(itd.get("claim_id"))
            txt = _s(itd.get("finding_text"))
            eids = _l(itd.get("evidence_eids"))
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
            ld = _d(lim)
            _bullet(lines, _s(ld.get("statement")) or "(limit statement)")
    else:
        _bullet(lines, "No limits declared.")

    return "\n".join(lines)


def _stub_reader_in_depth(pack: Dict[str, Any]) -> str:
    """
    Canonical-ish “Public Guide” voice for the current stub schema,
    without inventing facts.
    """
    title, url = _title_url_from_stub(pack)
    report_pack = _d(pack.get("report_pack"))
    onep = _s(report_pack.get("summary_one_paragraph")) or "(No summary.)"

    metrics = _d(pack.get("metrics"))
    density = _d(metrics.get("evidence_density"))
    density_label = _s(density.get("density_label"))
    ratio = density.get("evidence_to_claim_ratio", None)

    counter = _d(metrics.get("counterevidence_status"))
    counter_required = bool(counter.get("required", False))
    counter_status = _s(counter.get("status"))
    counter_scope = _s(counter.get("search_scope"))
    counter_result = _s(counter.get("result"))

    hbd = _d(pack.get("headline_body_delta"))
    hbd_present = bool(hbd.get("present", False))
    hbd_items = _l(hbd.get("items"))

    claims = _d(pack.get("claim_registry")).get("claims", [])
    claims = _l(claims)
    hi_stakes = [c for c in claims if _s(_d(c).get("stakes")).lower() == "high"]

    guide = _s(report_pack.get("reader_interpretation_guide"))

    lines: List[str] = []
    lines.append(f"# 🧭 Reader In-Depth — {title}")
    if url:
        lines.append(f"*Source:* {url}")
    lines.append("")
    lines.append("## One-paragraph summary")
    lines.append(onep)
    lines.append("")
    lines.append("## What kind of piece is this (as a reader experience)?")

    # simple classification heuristics (structure-based only)
    if density_label in ("low",) or (ratio is not None and ratio < 0.8):
        _bullet(lines, "This reads like **assertion-forward reporting**: claims are presented, but the visible evidence footprint is relatively thin.")
    else:
        _bullet(lines, "This reads like **quote-driven political reporting**: multiple claims are anchored to quoted passages, but deeper verification may still be limited.")

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
    # Mechanism set that matches your terminology direction
    _bullet(lines, "**Attribution-as-authority:** quotes from actors can feel like evidence, but quotes are not verification.")
    _bullet(lines, "**Reaction reporting risk:** reporting others’ statements can transmit the emotional payload even when the article stays neutral.")
    _bullet(lines, "**Scope inflation watch:** local tactical claims can quietly become broad conclusions if not fenced with qualifiers.")
    _bullet(lines, "**Omission-dependent reasoning watch:** if key comparative context is missing, conclusions may lean on what isn’t said.")

    lines.append("")
    lines.append("## What BiasLens can and cannot conclude from this run")
    if guide:
        lines.append(_clip(guide, 600))
    else:
        lines.append(
            "This run is integrity-safe: it shows extracted evidence and claims without making strong factual judgments beyond the evidence provided. "
            "Where verification isn’t performed, the correct status is **unknown**, not speculation."
        )

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

    claims = _d(pack.get("claim_registry")).get("claims", [])
    claims = _l(claims)

    report_pack = _d(pack.get("report_pack"))
    findings_pack = _d(report_pack.get("findings_pack"))
    fitems = _l(findings_pack.get("items"))

    lines: List[str] = []
    lines.append(f"# 🧪 Scholar In-Depth — {title}")
    if url:
        lines.append(f"*Source:* {url}")
    lines.append("")

    lines.append("## Evidence bank (verbatim excerpts)")
    for eid, quote in list(evidence.items())[:25]:
        lines.append(f"- **{eid}**: {quote}")

    lines.append("")
    lines.append("## Claim registry (extracted)")
    for c in claims[:25]:
        cd = _d(c)
        lines.append(f"- **{_s(cd.get('claim_id'))}** (stakes: {_s(cd.get('stakes'))}): {_clip(_s(cd.get('claim_text')), 320)}")
        lines.append(f"  - evidence_eids: {cd.get('evidence_eids', [])}")

    lines.append("")
    lines.append("## Findings pack (current run)")
    if fitems:
        for it in fitems[:25]:
            itd = _d(it)
            claim_id = _s(itd.get("claim_id"))
            rest = _clip(_s(itd.get("restated_claim")), 240)
            txt = _s(itd.get("finding_text"))
            rating = itd.get("rating", 3)
            eids = itd.get("evidence_eids", [])
            lines.append(f"- {render_rating(rating)} **{claim_id}**: {rest}")
            lines.append(f"  - finding: {txt}")
            lines.append(f"  - evidence_eids: {eids}")
    else:
        lines.append("- (No scholar findings yet in this schema/run.)")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# BRICK-7 schema rendering (kept for forward compatibility)
# ─────────────────────────────────────────────────────────────

def _brick7_overview(pack: Dict[str, Any]) -> str:
    title, url = _title_url_from_brick7(pack)
    article = _d(pack.get("article_layer"))
    onep = _s(article.get("one_paragraph_summary")) or "(No summary.)"

    evidence_bank = _l(pack.get("evidence_bank"))
    claim_registry = _l(pack.get("claim_registry"))
    hbd = _d(pack.get("headline_body_delta"))

    lines: List[str] = []
    lines.append(f"# 🛡️ BiasLens Overview — {title}")
    if url:
        lines.append(f"*Source:* {url}")
    lines.append("")
    lines.append("## One-paragraph summary")
    lines.append(onep)
    lines.append("")
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
    article = _d(pack.get("article_layer"))
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
    return _stub_reader_in_depth(pack) if _is_stub_schema(pack) else _brick7_reader(pack)


def render_scholar_in_depth(pack: Dict[str, Any]) -> str:
    return _stub_scholar_in_depth(pack) if _is_stub_schema(pack) else _brick7_scholar(pack)
