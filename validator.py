# validator.py
# BiasLens Integrity Gatekeeper
# Enforces evidence discipline, declared uncertainty, and structural legality

from __future__ import annotations

from typing import Any, Dict, List, Set, Optional


class ValidationError(Exception):
    pass


# -----------------------------
# Public entry point
# -----------------------------
def validate_output(output: dict) -> bool:
    """
    Validate a full BiasLens report pack.
    Raises ValidationError with newline-joined errors if anything fails.
    """
    errors: List[str] = []

    evidence_ids = collect_evidence_ids(output)

    errors += validate_evidence_bank(output)
    errors += validate_facts_layer(output, evidence_ids)
    errors += validate_claim_registry(output, evidence_ids)
    errors += validate_report_pack(output, evidence_ids)
    errors += validate_headline_body_delta(output, evidence_ids)
    errors += validate_evidence_density(output)
    errors += validate_counterevidence_status(output)

    if errors:
        raise ValidationError("\n".join(errors))

    return True


# Backward-compat / convenience alias used by pipeline.py
def validate_report_pack(output: dict, evidence_ids: List[str] | Set[str]) -> List[str]:
    """
    NOTE: This returns a list of errors (does NOT raise), matching older call sites.
    In the pipeline we call it inside _validate() and raise there.
    """
    if isinstance(evidence_ids, list):
        evidence_set = set(evidence_ids)
    else:
        evidence_set = evidence_ids
    return _validate_report_pack_internal(output, evidence_set)


# -----------------------------
# Evidence helpers
# -----------------------------
def collect_evidence_ids(out: Dict[str, Any]) -> Set[str]:
    bank = out.get("evidence_bank", []) or []
    ids: Set[str] = set()
    for item in bank:
        eid = (item.get("eid") or "").strip()
        if eid:
            ids.add(eid)
    return ids


def validate_evidence_bank(out: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    bank = out.get("evidence_bank", []) or []

    if not isinstance(bank, list):
        return ["evidence_bank must be a list"]

    for i, item in enumerate(bank):
        if not isinstance(item, dict):
            errs.append(f"evidence_bank[{i}] must be an object")
            continue

        eid = (item.get("eid") or "").strip()
        if not eid:
            errs.append(f"evidence_bank[{i}] missing eid")

        quote = (item.get("quote") or "").strip()
        if not quote:
            errs.append(f"evidence_bank[{i}] missing quote (verbatim)")

        # start_char/end_char are recommended; validate if present
        sc = item.get("start_char")
        ec = item.get("end_char")
        if sc is not None and (not isinstance(sc, int) or sc < 0):
            errs.append(f"evidence_bank[{i}].start_char invalid")
        if ec is not None and (not isinstance(ec, int) or ec < 0):
            errs.append(f"evidence_bank[{i}].end_char invalid")
        if isinstance(sc, int) and isinstance(ec, int) and ec < sc:
            errs.append(f"evidence_bank[{i}] end_char < start_char")

        # source block (soft requirement but helps stability)
        src = item.get("source")
        if src is not None and not isinstance(src, dict):
            errs.append(f"evidence_bank[{i}].source must be an object if present")

    return errs


def _validate_eids_exist(eids: Any, evidence_ids: Set[str], ctx: str) -> List[str]:
    errs: List[str] = []
    if eids is None:
        return [f"{ctx} missing evidence_eids"]
    if not isinstance(eids, list):
        return [f"{ctx}.evidence_eids must be a list"]
    if len(eids) == 0:
        return [f"{ctx} evidence_eids empty"]

    for eid in eids:
        if not isinstance(eid, str) or not eid.strip():
            errs.append(f"{ctx} has blank/invalid evidence_eid")
            continue
        if eid not in evidence_ids:
            errs.append(f"{ctx} references missing evidence_eid={eid}")
    return errs


# -----------------------------
# Facts layer validation
# -----------------------------
_ALLOWED_FACT_VERDICTS = {
    # explicit epistemic states
    "true",
    "false",
    "mixed",
    "unknown",
    "insufficient_evidence",
    "not_found",
    # acceptable alias if you use it internally
    "uncheckable",
}

_ALLOWED_FACT_CHECKABILITY = {"checkable", "currently_uncheckable"}


def validate_facts_layer(out: Dict[str, Any], evidence_ids: Set[str]) -> List[str]:
    errs: List[str] = []
    fl = out.get("facts_layer")
    if fl is None:
        return ["facts_layer is required"]

    if not isinstance(fl, dict):
        return ["facts_layer must be an object"]

    facts = fl.get("facts", [])
    if not isinstance(facts, list):
        return ["facts_layer.facts must be a list"]

    for i, f in enumerate(facts):
        ctx = f"facts_layer.facts[{i}]"
        if not isinstance(f, dict):
            errs.append(f"{ctx} must be an object")
            continue

        if not (f.get("fact_id") or "").strip():
            errs.append(f"{ctx} missing fact_id")
        if not (f.get("fact_text") or "").strip():
            errs.append(f"{ctx} missing fact_text")

        checkability = f.get("checkability")
        if checkability not in _ALLOWED_FACT_CHECKABILITY:
            errs.append(
                f"{ctx}.checkability must be one of {sorted(_ALLOWED_FACT_CHECKABILITY)}"
            )

        verdict = f.get("verdict")
        if verdict not in _ALLOWED_FACT_VERDICTS:
            errs.append(f"{ctx}.verdict must be one of {sorted(_ALLOWED_FACT_VERDICTS)}")

        # If the fact is marked checkable, we require evidence_eids to exist (can still be unknown).
        if checkability == "checkable":
            errs += _validate_eids_exist(f.get("evidence_eids", []), evidence_ids, ctx)

    return errs


# -----------------------------
# Claim Registry validation
# -----------------------------
_ALLOWED_STAKES = {"low", "medium", "high"}


def validate_claim_registry(out: Dict[str, Any], evidence_ids: Set[str]) -> List[str]:
    errs: List[str] = []
    cr = out.get("claim_registry")
    if cr is None:
        return ["claim_registry is required"]

    if not isinstance(cr, dict):
        return ["claim_registry must be an object"]

    claims = cr.get("claims", [])
    if not isinstance(claims, list):
        return ["claim_registry.claims must be a list"]

    for i, c in enumerate(claims):
        ctx = f"claim_registry.claims[{i}]"
        if not isinstance(c, dict):
            errs.append(f"{ctx} must be an object")
            continue

        if not (c.get("claim_id") or "").strip():
            errs.append(f"{ctx} missing claim_id")
        if not (c.get("claim_text") or "").strip():
            errs.append(f"{ctx} missing claim_text")

        stakes = c.get("stakes")
        if stakes is not None and stakes not in _ALLOWED_STAKES:
            errs.append(f"{ctx}.stakes must be one of {sorted(_ALLOWED_STAKES)} if present")

        errs += _validate_eids_exist(c.get("evidence_eids", []), evidence_ids, ctx)

    return errs


# -----------------------------
# Report pack validation
# -----------------------------
_ALLOWED_SEVERITIES = {"🟢", "🟡", "🟠", "🔴"}


def _validate_report_pack_internal(out: Dict[str, Any], evidence_ids: Set[str]) -> List[str]:
    errs: List[str] = []
    rp = out.get("report_pack", {})

    if not isinstance(rp, dict):
        return ["report_pack must be an object"]

    if not (rp.get("summary_one_paragraph") or "").strip():
        errs.append("report_pack.summary_one_paragraph is required")

    if not (rp.get("reader_interpretation_guide") or "").strip():
        errs.append("report_pack.reader_interpretation_guide is required")

    findings_pack = rp.get("findings_pack", {}) or {}
    if not isinstance(findings_pack, dict):
        errs.append("report_pack.findings_pack must be an object")
        return errs

    findings = findings_pack.get("items", []) or []
    if not isinstance(findings, list):
        errs.append("report_pack.findings_pack.items must be a list")
        return errs

    for i, it in enumerate(findings):
        ctx = f"report_pack.findings_pack.items[{i}]"
        if not isinstance(it, dict):
            errs.append(f"{ctx} must be an object")
            continue

        if not (it.get("finding_id") or "").strip():
            errs.append(f"{ctx} missing finding_id")

        # UX lock: restate full claim before analysis
        if not (it.get("restated_claim") or "").strip():
            errs.append(f"{ctx} missing restated_claim")

        if not (it.get("finding_text") or "").strip():
            errs.append(f"{ctx} missing finding_text")

        sev = it.get("severity")
        if sev not in _ALLOWED_SEVERITIES:
            errs.append(f"{ctx}.severity must be one of {sorted(_ALLOWED_SEVERITIES)}")

        errs += _validate_eids_exist(it.get("evidence_eids", []), evidence_ids, ctx)

    # scholar_pack is optional; if present, validate shape
    scholar_pack = rp.get("scholar_pack")
    if scholar_pack is not None:
        if not isinstance(scholar_pack, dict):
            errs.append("report_pack.scholar_pack must be an object if present")
        else:
            items = scholar_pack.get("items", [])
            if items is not None and not isinstance(items, list):
                errs.append("report_pack.scholar_pack.items must be a list if present")

    return errs


# -----------------------------
# Presentation integrity / headline-body delta
# -----------------------------
def validate_headline_body_delta(out: Dict[str, Any], evidence_ids: Set[str]) -> List[str]:
    """
    Matches current pipeline shape:
      headline_body_delta: { present: bool, items: [] }
    Each item (if any) must cite evidence_eids that exist.
    """
    errs: List[str] = []
    hbd = out.get("headline_body_delta")
    if hbd is None:
        # optional
        return errs

    if not isinstance(hbd, dict):
        return ["headline_body_delta must be an object if present"]

    present = hbd.get("present")
    items = hbd.get("items", []) or []

    if present not in {True, False, None}:
        errs.append("headline_body_delta.present must be boolean if present")

    if not isinstance(items, list):
        errs.append("headline_body_delta.items must be a list")
        return errs

    if present is True and len(items) == 0:
        errs.append("headline_body_delta.present=true but items is empty")

    for i, item in enumerate(items):
        ctx = f"headline_body_delta.items[{i}]"
        if not isinstance(item, dict):
            errs.append(f"{ctx} must be an object")
            continue

        # minimal helpful requirements if you populate it
        if not (item.get("headline_text") or item.get("headline") or "").strip():
            # allow either key
            errs.append(f"{ctx} missing headline_text/headline")
        if not (item.get("body_text") or item.get("body") or "").strip():
            errs.append(f"{ctx} missing body_text/body")

        eids = item.get("evidence_eids", []) or []
        if len(eids) == 0:
            errs.append(f"{ctx} missing evidence_eids")
        else:
            errs += _validate_eids_exist(eids, evidence_ids, ctx)

    return errs


# -----------------------------
# Evidence density (metrics)
# -----------------------------
def validate_evidence_density(out: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    ed = (out.get("metrics", {}) or {}).get("evidence_density", {})

    if not isinstance(ed, dict) or not ed:
        return ["metrics.evidence_density is required"]

    try:
        num_claims = int(ed.get("num_claims", -1))
        num_evidence_items = int(ed.get("num_evidence_items", -1))
        ratio = ed.get("evidence_to_claim_ratio")
    except Exception:
        return ["metrics.evidence_density has invalid numeric fields"]

    if num_claims < 0:
        errs.append("metrics.evidence_density.num_claims missing or invalid")
    if num_evidence_items < 0:
        errs.append("metrics.evidence_density.num_evidence_items missing or invalid")

    expected = num_evidence_items / max(1, num_claims)
    if ratio is None:
        errs.append("metrics.evidence_density.evidence_to_claim_ratio missing")
    else:
        try:
            r = float(ratio)
            if abs(r - expected) > 1e-6:
                errs.append("metrics.evidence_density.evidence_to_claim_ratio incorrect")
        except Exception:
            errs.append("metrics.evidence_density.evidence_to_claim_ratio not numeric")

    return errs


# -----------------------------
# Counterevidence status (global)
# -----------------------------
_ALLOWED_COUNTEREVIDENCE_STATUS = {
    "not_applicable",
    "not_performed",
    "no_counterevidence_found_in_checked_sources",
    "sources_insufficient_for_question",
    "retrieval_failed",
    "counterevidence_found",
}


def validate_counterevidence_status(out: Dict[str, Any]) -> List[str]:
    """
    Matches pipeline dummy pack:
      metrics: { counterevidence_status: { required, status, search_scope, result, notes } }
    If status says counterevidence_found, require items with verbatim quotes and stable IDs
    (we allow either metrics.counterevidence_status.items or a top-level counterevidence block later).
    """
    errs: List[str] = []
    cs = (out.get("metrics", {}) or {}).get("counterevidence_status")

    if cs is None:
        # optional for now
        return errs

    if not isinstance(cs, dict):
        return ["metrics.counterevidence_status must be an object if present"]

    status = cs.get("status")
    if status not in _ALLOWED_COUNTEREVIDENCE_STATUS:
        errs.append(
            f"metrics.counterevidence_status.status must be one of {sorted(_ALLOWED_COUNTEREVIDENCE_STATUS)}"
        )

    # Must declare scope/result when not not_applicable
    if status != "not_applicable":
        if not (cs.get("search_scope") or "").strip():
            errs.append("metrics.counterevidence_status.search_scope is required when status != not_applicable")
        if not (cs.get("result") or "").strip():
            errs.append("metrics.counterevidence_status.result is required when status != not_applicable")

    # If counterevidence is claimed found, require items with verbatim quotes + stable IDs.
    if status == "counterevidence_found":
        items = cs.get("items", [])
        if not isinstance(items, list) or len(items) == 0:
            errs.append("metrics.counterevidence_status.items required when status=counterevidence_found")
        else:
            for i, it in enumerate(items):
                ctx = f"metrics.counterevidence_status.items[{i}]"
                if not isinstance(it, dict):
                    errs.append(f"{ctx} must be an object")
                    continue
                if not (it.get("source_id") or "").strip():
                    errs.append(f"{ctx} missing source_id")
                if not (it.get("quote_verbatim") or it.get("quote") or "").strip():
                    errs.append(f"{ctx} missing quote_verbatim/quote (verbatim required)")

    return errs
