
#!/usr/bin/env python3
"""
renderer.py

Converts a Brick-7 BiasLens report pack into readable Markdown reports.

Outputs:
- Overview: short, readable, evidence-anchored
- Reader In-Depth: Facebook-friendly interpretation layer (structure-based, not intent-based)
- Scholar In-Depth: technical, evidence IDs, claims, and evaluations

This file does NOT call the LLM; it only renders what the engine already produced.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _d(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _l(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _s(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _bullet(lines: List[str], text: str) -> None:
    lines.append(f"- {text}")


def render_overview(pack: Dict[str, Any]) -> str:
    pack = _d(pack)
    article = _d(pack.get("article_layer"))
    onep = _s(article.get("one_paragraph_summary")) or "(No summary produced.)"

    title = _s(pack.get("source_title")) or "BiasLens Report"
    url = _s(pack.get("source_url"))

    claim_registry = _l(pack.get("claim_registry"))
    evidence_bank = _l(pack.get("evidence_bank"))

    hbd = _d(pack.get("headline_body_delta"))
    h_head = _s(hbd.get("headline"))
    h_qual = _s(hbd.get("body_key_qualifiers"))

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
    lines.append("## Headline–Body Delta (presentation integrity)")
    _bullet(lines, f"Headline: **{h_head or '(not provided)'}**")
    _bullet(lines, f"Body qualifiers: {h_qual or '(explicitly unknown / not extracted yet)'}")
    lines.append("")
    lines.append("## Notes on interpretation")
    lines.append(
        "BiasLens flags **structure-based information integrity risks** (evidence discipline, logic, omission-as-absence-of-context). "
        "It does **not** infer intent."
    )
    return "\n".join(lines)


def render_reader_in_depth(pack: Dict[str, Any]) -> str:
    pack = _d(pack)
    article = _d(pack.get("article_layer"))
    onep = _s(article.get("one_paragraph_summary")) or "(No summary produced.)"

    title = _s(pack.get("source_title")) or "BiasLens Report"

    reader = _d(pack.get("reader_interpretation"))
    mechs = _l(reader.get("named_mechanisms"))

    hbd = _d(pack.get("headline_body_delta"))
    h_head = _s(hbd.get("headline"))
    h_findings = _l(hbd.get("findings"))

    lines: List[str] = []
    lines.append(f"# 🧭 Reader In-Depth — {title}")
    lines.append("")
    lines.append("## One-paragraph summary")
    lines.append(onep)
    lines.append("")
    lines.append("## How this article may shape reader interpretation (structure, not intent)")
    if mechs:
        for m in mechs[:10]:
            md = _d(m)
            name = _s(md.get("mechanism_name")) or "Mechanism"
            expl = _s(md.get("plain_language_explanation")) or ""
            _bullet(lines, f"**{name}** — {expl}")
    else:
        _bullet(lines, "No mechanisms were listed in this build (placeholder).")

    lines.append("")
    lines.append("## Headline–Body Delta (reaction reporting risk)")
    _bullet(lines, f"Headline: **{h_head or '(not provided)'}**")
    if h_findings:
        for f in h_findings[:5]:
            fd = _d(f)
            _bullet(lines, _s(fd.get("finding_text")) or "(no headline/body finding text)")
    else:
        _bullet(lines, "No headline/body delta findings listed (placeholder).")

    lines.append("")
    lines.append("## What to look for as a reader")
    _bullet(lines, "Are key claims backed by **verbatim quoted evidence** or vague attribution?")
    _bullet(lines, "Do conclusions rely on **missing comparative context** (omission-dependent reasoning)?")
    _bullet(lines, "Does the headline amplify emotion beyond the article’s qualifiers?")
    _bullet(lines, "Are there **scope jumps** (local → universal) without support?")
    lines.append("")
    lines.append(
        "**Reminder:** Absence is reported only as *absence of expected context* — BiasLens does not claim motive or wrongdoing."
    )
    return "\n".join(lines)


def render_scholar_in_depth(pack: Dict[str, Any]) -> str:
    pack = _d(pack)

    title = _s(pack.get("source_title")) or "BiasLens Report"
    url = _s(pack.get("source_url"))

    evidence_bank = _l(pack.get("evidence_bank"))
    claim_registry = _l(pack.get("claim_registry"))
    claim_evals = _l(pack.get("claim_evaluations"))

    arg_layer = _d(pack.get("argument_layer"))
    arg_summary = _s(arg_layer.get("summary"))
    arg_map = arg_layer.get("argument_map")

    lines: List[str] = []
    lines.append(f"# 🧪 Scholar In-Depth — {title}")
    if url:
        lines.append(f"*Source:* {url}")
    lines.append("")

    lines.append("## Evidence Bank (verbatim)")
    for ev in evidence_bank[:25]:
        evd = _d(ev)
        eid = _s(evd.get("eid"))
        quote = _s(evd.get("quote"))
        if eid and quote:
            lines.append(f"- **{eid}**: {quote}")
    if len(evidence_bank) > 25:
        lines.append(f"\n*(Showing first 25 of {len(evidence_bank)} evidence items.)*")

    lines.append("")
    lines.append("## Claim Registry (discrete claims; each evaluation restates the claim)")
    for c in claim_registry[:25]:
        cd = _d(c)
        cid = _s(cd.get("claim_id"))
        ctext = _s(cd.get("claim_text"))
        state = _s(cd.get("epistemic_state") or cd.get("status") or cd.get("verification_status"))
        eids = cd.get("evidence_eids", [])
        lines.append(f"- **{cid}** ({state or 'unknown'}): {ctext}")
        lines.append(f"  - evidence_eids: {eids}")

    lines.append("")
    lines.append("## Claim Evaluations (evidence-anchored; fail-closed)")
    for ce in claim_evals[:25]:
        ced = _d(ce)
        cid = _s(ced.get("claim_id"))
        rest = _s(ced.get("claim_restatement"))
        lines.append(f"- **{cid}**: {rest}")
        findings = _l(ced.get("findings"))
        for f in findings[:8]:
            fd = _d(f)
            ftxt = _s(fd.get("finding_text"))
            ftype = _s(fd.get("finding_type"))
            feids = fd.get("evidence_eids", [])
            quotes = _l(fd.get("verbatim_quotes"))
            lines.append(f"  - [{ftype or 'finding'}] {ftxt}")
            lines.append(f"    - evidence_eids: {feids}")
            if quotes:
                lines.append(f"    - quote: {_s(quotes[0])}")

    lines.append("")
    lines.append("## Argument Layer")
    lines.append(arg_summary or "(no argument summary)")
    lines.append("")
    lines.append("### Argument map (raw)")
    lines.append("```json")
    lines.append(__import__("json").dumps(arg_map, indent=2, ensure_ascii=False))
    lines.append("```")

    return "\n".join(lines)
