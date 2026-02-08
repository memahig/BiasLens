
#!/usr/bin/env python3
"""
BiasLens Validator (Brick 7)

Fail-closed validation for the full report pack produced by the BiasLens pipeline.

Design locks enforced here:
- Evidence discipline: no assertion/finding without verbatim quoted evidence + valid eid
- Facts/Claims/Counterevidence must carry explicit epistemic states (unknown/not found/insufficient)
- Omission findings are ONLY "absence of expected context" (never intent)
- Headline–Body Delta / Presentation Integrity block required
- Reader Interpretation / Public Guide output required
- Claim-by-claim model: every claim evaluation must restate full claim text immediately before analysis
- Counterevidence blocks may be empty, but must include search_scope + result (what was checked and what happened)

This validator is intentionally strict. If it rejects, the app should not render the report.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


# -----------------------------
# Exceptions
# -----------------------------

class ValidationError(ValueError):
    pass


# -----------------------------
# Basic helpers
# -----------------------------

def _path(p: str, key: str) -> str:
    return f"{p}.{key}" if p else key

def _is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""

def _is_list(x: Any) -> bool:
    return isinstance(x, list)

def _is_dict(x: Any) -> bool:
    return isinstance(x, dict)

def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValidationError(msg)

def _require_key(obj: Dict[str, Any], key: str, p: str) -> Any:
    _require(key in obj, f"Missing required field: {_path(p, key)}")
    return obj[key]

def _optional_key(obj: Dict[str, Any], key: str, default: Any = None) -> Any:
    return obj.get(key, default)

def _require_nonempty_str(obj: Dict[str, Any], key: str, p: str) -> str:
    v = _require_key(obj, key, p)
    _require(_is_nonempty_str(v), f"Field must be a non-empty string: {_path(p, key)}")
    return v.strip()

def _require_list(obj: Dict[str, Any], key: str, p: str) -> List[Any]:
    v = _require_key(obj, key, p)
    _require(_is_list(v), f"Field must be a list: {_path(p, key)}")
    return v

def _require_dict(obj: Dict[str, Any], key: str, p: str) -> Dict[str, Any]:
    v = _require_key(obj, key, p)
    _require(_is_dict(v), f"Field must be an object/dict: {_path(p, key)}")
    return v

def _collect_eids(evidence_bank: List[Dict[str, Any]]) -> Set[str]:
    eids: Set[str] = set()
    for i, e in enumerate(evidence_bank):
        p = f"evidence_bank[{i}]"
        _require(_is_dict(e), f"{p} must be an object/dict")
        eid = _require_nonempty_str(e, "eid", p)
        _require(eid not in eids, f"Duplicate eid found: {eid} at {p}.eid")
        quote = _require_nonempty_str(e, "quote", p)
        # Quote must be verbatim and not trivially short
        _require(len(quote) >= 12, f"{p}.quote is too short to be meaningful (min 12 chars)")
        # Basic metadata (not strictly required but strongly encouraged)
        # If present, validate types.
        start_char = _optional_key(e, "start_char")
        end_char = _optional_key(e, "end_char")
        if start_char is not None:
            _require(isinstance(start_char, int) and start_char >= 0, f"{p}.start_char must be int >= 0")
        if end_char is not None:
            _require(isinstance(end_char, int) and end_char >= 0, f"{p}.end_char must be int >= 0")
        why = _optional_key(e, "why_relevant")
        if why is not None:
            _require(_is_nonempty_str(why), f"{p}.why_relevant must be a non-empty string if present")

        eids.add(eid)
    return eids

def _validate_evidence_refs(eids: Set[str], refs: Any, p: str) -> None:
    _require(_is_list(refs), f"{p} must be a list of evidence_eids")
    for j, r in enumerate(refs):
        _require(_is_nonempty_str(r), f"{p}[{j}] must be a non-empty string eid")
        _require(r in eids, f"{p}[{j}] references unknown eid '{r}' (not found in evidence_bank)")

def _validate_epistemic_state(node: Dict[str, Any], p: str) -> None:
    """
    Enforces explicit epistemic states.
    Allowed states: "verified", "false", "mixed", "unknown", "not_found", "insufficient_evidence", "uncheckable"
    (You can extend later, but keep explicit.)
    """
    state = _optional_key(node, "epistemic_state")
    if state is None:
        # Some objects may use alternate field names; accept but require at least one explicit state field.
        alt = _optional_key(node, "status") or _optional_key(node, "verification_status")
        _require(_is_nonempty_str(alt), f"{p} must declare an explicit epistemic state (epistemic_state/status/verification_status)")
        state = str(alt).strip()

    allowed = {
        "verified",
        "false",
        "mixed",
        "unknown",
        "not_found",
        "insufficient_evidence",
        "uncheckable",
    }
    _require(str(state) in allowed, f"{p} epistemic state '{state}' not in allowed set {sorted(allowed)}")

def _ban_intent_language(text: str, p: str) -> None:
    """
    We can't perfectly police intent language, but we can ban the most direct claims.
    This is a guardrail; not a substitute for careful prompting.
    """
    lowered = text.lower()
    banned = [
        "on purpose",
        "intentionally",
        "deliberately",
        "they wanted to",
        "designed to mislead",
        "bad faith",
        "malicious",
        "propaganda intent",
        "purposeful omission",
    ]
    for b in banned:
        _require(b not in lowered, f"{p} contains intent-claim language ('{b}'). Omission must be framed as absence of expected context only.")


# -----------------------------
# Section validators
# -----------------------------

def validate_report_pack(report: Dict[str, Any]) -> None:
    """
    Main entrypoint. Raises ValidationError on first failure.
    """
    _require(_is_dict(report), "Report must be a dict/object")

    # 0) Required top-level blocks
    evidence_bank = _require_list(report, "evidence_bank", "")
    eids = _collect_eids(evidence_bank)

    # Facts -> Claims -> Arguments -> Article expected (some may be empty in early iterations, but must exist)
    facts = _require_list(report, "facts", "")
    claims = _require_list(report, "claim_registry", "")
    claim_evals = _require_list(report, "claim_evaluations", "")
    argument_layer = _require_dict(report, "argument_layer", "")
    article_layer = _require_dict(report, "article_layer", "")

    # Presentation integrity & reader interpretation are locked as required
    headline_body_delta = _require_dict(report, "headline_body_delta", "")
    reader_layer = _require_dict(report, "reader_interpretation", "")

    # 1) Validate Facts
    _validate_facts(facts, eids)

    # 2) Validate Claim registry
    _validate_claim_registry(claims, eids)

    # 3) Validate Claim evaluations (must restate full claim + evidence discipline)
    _validate_claim_evaluations(claim_evals, claims, eids)

    # 4) Validate Argument layer (presence + explicit states)
    _validate_argument_layer(argument_layer, eids)

    # 5) Validate Article layer (presence + explicit states)
    _validate_article_layer(article_layer, eids)

    # 6) Headline–Body Delta / Presentation Integrity
    _validate_headline_body_delta(headline_body_delta, eids)

    # 7) Reader Interpretation / Public Guide (one-paragraph summary + optional tiers)
    _validate_reader_interpretation(reader_layer, eids)

    # If we got here, it's valid.


def _validate_facts(facts: List[Any], eids: Set[str]) -> None:
    for i, f in enumerate(facts):
        p = f"facts[{i}]"
        _require(_is_dict(f), f"{p} must be an object/dict")
        _require_nonempty_str(f, "fact_id", p)
        _require_nonempty_str(f, "fact_text", p)

        # checkable classification required (first-class)
        checkable = _require_key(f, "checkable", p)
        _require(isinstance(checkable, bool), f"{p}.checkable must be boolean")

        # explicit epistemic state required
        _validate_epistemic_state(f, p)

        # evidence discipline for checkable facts
        ev = _optional_key(f, "evidence_eids", [])
        if checkable:
            _validate_evidence_refs(eids, ev, _path(p, "evidence_eids"))
        else:
            # uncheckable facts may still have evidence, but must be explicit about why
            if ev:
                _validate_evidence_refs(eids, ev, _path(p, "evidence_eids"))


def _validate_claim_registry(claims: List[Any], eids: Set[str]) -> None:
    seen_ids: Set[str] = set()
    for i, c in enumerate(claims):
        p = f"claim_registry[{i}]"
        _require(_is_dict(c), f"{p} must be an object/dict")
        cid = _require_nonempty_str(c, "claim_id", p)
        _require(cid not in seen_ids, f"Duplicate claim_id '{cid}' at {p}.claim_id")
        seen_ids.add(cid)

        _require_nonempty_str(c, "claim_text", p)

        # Evidence required for claims (core rule)
        ev = _require_key(c, "evidence_eids", p)
        _validate_evidence_refs(eids, ev, _path(p, "evidence_eids"))

        # explicit epistemic state required for claim registry entries
        _validate_epistemic_state(c, p)


def _validate_claim_evaluations(
    claim_evals: List[Any],
    claim_registry: List[Any],
    eids: Set[str],
) -> None:
    # Map claim_id -> claim_text for restatement checking
    id_to_text: Dict[str, str] = {}
    for c in claim_registry:
        if isinstance(c, dict) and _is_nonempty_str(c.get("claim_id")) and _is_nonempty_str(c.get("claim_text")):
            id_to_text[c["claim_id"].strip()] = c["claim_text"].strip()

    for i, ce in enumerate(claim_evals):
        p = f"claim_evaluations[{i}]"
        _require(_is_dict(ce), f"{p} must be an object/dict")
        cid = _require_nonempty_str(ce, "claim_id", p)

        # Locked UX rule: restate full claim text immediately before analysis
        restated = _require_nonempty_str(ce, "claim_restatement", p)
        if cid in id_to_text:
            # Must match exactly or be the same with trivial whitespace differences
            canonical = " ".join(id_to_text[cid].split())
            provided = " ".join(restated.split())
            _require(
                canonical == provided,
                f"{p}.claim_restatement must exactly match claim_registry claim_text for {cid} (restatement required and must be identical)."
            )

        _validate_epistemic_state(ce, p)

        # Findings: enforce evidence discipline + ban intent language
        findings = _require_list(ce, "findings", p)
        for j, f in enumerate(findings):
            fp = f"{p}.findings[{j}]"
            _require(_is_dict(f), f"{fp} must be an object/dict")
            f_text = _require_nonempty_str(f, "finding_text", fp)

            # Every finding must be evidence-tethered with verbatim quotes.
            ev = _require_key(f, "evidence_eids", fp)
            _validate_evidence_refs(eids, ev, _path(fp, "evidence_eids"))
            quotes = _require_list(f, "verbatim_quotes", fp)
            _require(len(quotes) >= 1, f"{fp}.verbatim_quotes must contain at least 1 quote")
            for qk, q in enumerate(quotes):
                _require(_is_nonempty_str(q), f"{fp}.verbatim_quotes[{qk}] must be a non-empty string")
                _require(len(q.strip()) >= 12, f"{fp}.verbatim_quotes[{qk}] too short (min 12 chars)")

            _ban_intent_language(f_text, _path(fp, "finding_text"))

            # Omission rule: only "absence of expected context"
            f_type = _optional_key(f, "finding_type")
            if _is_nonempty_str(f_type) and str(f_type).strip().lower() in {"omission", "systematic_omission", "comparative_suppression"}:
                # Must include expected_context + what was missing, without intent
                exp = _require_nonempty_str(f, "expected_context", fp)
                miss = _require_nonempty_str(f, "missing_context", fp)
                _ban_intent_language(exp, _path(fp, "expected_context"))
                _ban_intent_language(miss, _path(fp, "missing_context"))

            # Counterevidence: can be empty, but must include search scope + result
            if "counterevidence" in f:
                ce_block = f["counterevidence"]
                _require(_is_dict(ce_block), f"{fp}.counterevidence must be an object/dict")
                scope = _require_nonempty_str(ce_block, "search_scope", f"{fp}.counterevidence")
                result = _require_nonempty_str(ce_block, "result", f"{fp}.counterevidence")
                # If counterevidence_items present, they must be evidence-anchored
                items = _optional_key(ce_block, "items", [])
                _require(_is_list(items), f"{fp}.counterevidence.items must be a list if present")
                for kk, item in enumerate(items):
                    ip = f"{fp}.counterevidence.items[{kk}]"
                    _require(_is_dict(item), f"{ip} must be an object/dict")
                    _require_nonempty_str(item, "counterclaim_text", ip)
                    _validate_evidence_refs(eids, _require_key(item, "evidence_eids", ip), _path(ip, "evidence_eids"))
                    vq = _require_list(item, "verbatim_quotes", ip)
                    _require(len(vq) >= 1, f"{ip}.verbatim_quotes must contain at least 1 quote")

        # Improvement guidance encouraged; if present, must be non-empty
        imp = _optional_key(ce, "improvement_suggestions")
        if imp is not None:
            _require(_is_list(imp), f"{p}.improvement_suggestions must be a list if present")


def _validate_argument_layer(argument_layer: Dict[str, Any], eids: Set[str]) -> None:
    p = "argument_layer"
    _require_nonempty_str(argument_layer, "summary", p)
    _validate_epistemic_state(argument_layer, p)

    # If argument_map exists, it must be explicit
    amap = _optional_key(argument_layer, "argument_map")
    if amap is not None:
        _require(_is_list(amap), f"{p}.argument_map must be a list if present")


def _validate_article_layer(article_layer: Dict[str, Any], eids: Set[str]) -> None:
    p = "article_layer"
    _require_nonempty_str(article_layer, "one_paragraph_summary", p)
    _validate_epistemic_state(article_layer, p)

    # Star ratings (if used) should be 1..5
    for k in ["facts_rating", "claims_rating", "arguments_rating", "article_rating"]:
        if k in article_layer:
            v = article_layer[k]
            _require(isinstance(v, int) and 1 <= v <= 5, f"{p}.{k} must be an int from 1 to 5")


def _validate_headline_body_delta(hbd: Dict[str, Any], eids: Set[str]) -> None:
    p = "headline_body_delta"
    _require_nonempty_str(hbd, "headline", p)
    _require_nonempty_str(hbd, "body_key_qualifiers", p)

    # Must include at least one analysis finding and evidence for it
    findings = _require_list(hbd, "findings", p)
    _require(len(findings) >= 1, f"{p}.findings must contain at least 1 item")

    for i, f in enumerate(findings):
        fp = f"{p}.findings[{i}]"
        _require(_is_dict(f), f"{fp} must be an object/dict")
        text = _require_nonempty_str(f, "finding_text", fp)
        _ban_intent_language(text, _path(fp, "finding_text"))

        ev = _require_key(f, "evidence_eids", fp)
        _validate_evidence_refs(eids, ev, _path(fp, "evidence_eids"))

        vq = _require_list(f, "verbatim_quotes", fp)
        _require(len(vq) >= 1, f"{fp}.verbatim_quotes must contain at least 1 quote")


def _validate_reader_interpretation(reader: Dict[str, Any], eids: Set[str]) -> None:
    p = "reader_interpretation"

    # Locked reporting flow: always output one-paragraph summary first
    onep = _require_nonempty_str(reader, "one_paragraph_summary", p)
    _ban_intent_language(onep, _path(p, "one_paragraph_summary"))

    # Must include mechanism explanations in plain language (structure-based)
    mechanisms = _require_list(reader, "named_mechanisms", p)
    _require(len(mechanisms) >= 1, f"{p}.named_mechanisms must contain at least 1 item")
    for i, m in enumerate(mechanisms):
        mp = f"{p}.named_mechanisms[{i}]"
        _require(_is_dict(m), f"{mp} must be an object/dict")
        _require_nonempty_str(m, "mechanism_name", mp)
        _require_nonempty_str(m, "plain_language_explanation", mp)
        _ban_intent_language(m["plain_language_explanation"], _path(mp, "plain_language_explanation"))

    # Optional tiers: Reader In-depth + Scholar In-depth
    # Must exist as keys even if empty strings? (strictly require presence; allow empty but explicit)
    for tier_key in ["reader_in_depth", "scholar_in_depth"]:
        _require(tier_key in reader, f"Missing required field: {p}.{tier_key} (must be explicit even if empty)")
        tier_val = reader[tier_key]
        _require(isinstance(tier_val, str), f"{p}.{tier_key} must be a string (can be empty but explicit)")

    # Evidence constraint: Reader layer can cite evidence; if it does, enforce eids
    cited = _optional_key(reader, "evidence_eids")
    if cited is not None:
        _validate_evidence_refs(eids, cited, _path(p, "evidence_eids"))
