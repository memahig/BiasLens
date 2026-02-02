
# integrity_validator.py
# BiasLens Integrity Gatekeeper
# Structural/type/schema legality only.
#
# Normative / scoring / cap / evidence-required-by-verdict rules live in:
#   integrity_enforcer.enforce_integrity()
#
# Validator responsibilities (no duplication):
# - output is a dict and has required top-level sections
# - sections have correct types (dict/list/str/int)
# - required IDs/text fields are present (fact_id, claim_id, etc.)
# - enumerated fields are from allowed sets (verdict/checkability/stakes)
# - evidence_bank items are well-formed (eid + verbatim quote)
# - any evidence_eids fields that ARE present reference existing evidence ids
#   (but validator does NOT decide when evidence_eids are required; enforcer does)

from __future__ import annotations

from typing import Any, Dict, List, Set

from schema_names import K
from integrity_enforcer import enforce_integrity


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

    # Structural sanity
    errors += validate_top_level(output)

    evidence_ids = collect_evidence_ids(output)

    # Normative rules (law): integrity objects, caps, evidence-required rules, etc.
    errors += enforce_integrity(output, evidence_ids)

    # Structural validators (no duplication of enforcer rules)
    errors += validate_evidence_bank(output)
    errors += validate_facts_layer(output, evidence_ids)
    errors += validate_claim_registry(output, evidence_ids)
    errors += _validate_report_pack_internal(output, evidence_ids)
    errors += validate_headline_body_delta(output, evidence_ids)
    errors += validate_evidence_density(output)
    errors += validate_new_analysis_modules(output)
    errors += validate_counterevidence_status(output)

    if errors:
        raise ValidationError("\n".join(errors))

    return True


# Backward-compat / convenience alias used by pipeline.py (older call sites)
def validate_report_pack(output: dict, evidence_ids: List[str] | Set[str]) -> List[str]:
    """
    Returns a list of errors (does NOT raise).
    """
    evidence_set = set(evidence_ids) if isinstance(evidence_ids, list) else evidence_ids
    return _validate_report_pack_internal(output, evidence_set)


# -----------------------------
# Top-level sanity
# -----------------------------
def validate_top_level(out: Any) -> List[str]:
    errs: List[str] = []
    if not isinstance(out, dict):
        return ["output must be an object/dict"]

    required = [
        K.SCHEMA_VERSION,
        K.RUN_METADATA,
        K.EVIDENCE_BANK,
        K.FACTS_LAYER,
        K.CLAIM_REGISTRY,
        K.METRICS,
        K.REPORT_PACK,
    ]
    for key in required:
        if key not in out:
            errs.append(f"missing top-level key: {key}")

    rm = out.get(K.RUN_METADATA)
    if rm is not None and not isinstance(rm, dict):
        errs.append(f"{K.RUN_METADATA} must be an object")

    sv = out.get(K.SCHEMA_VERSION)
    if sv is not None and (not isinstance(sv, str) or not sv.strip()):
        errs.append(f"{K.SCHEMA_VERSION} must be a non-empty string")

    return errs


# -----------------------------
# Evidence helpers
# -----------------------------
def collect_evidence_ids(out: Dict[str, Any]) -> Set[str]:
    bank = out.get(K.EVIDENCE_BANK, []) or []
    ids: Set[str] = set()

    if not isinstance(bank, list):
        return ids

    for item in bank:
        if not isinstance(item, dict):
            continue
        eid = (item.get(K.EID) or "").strip()
        if eid:
            ids.add(eid)

    return ids


def validate_evidence_bank(out: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    bank = out.get(K.EVIDENCE_BANK, []) or []

    if not isinstance(bank, list):
        return [f"{K.EVIDENCE_BANK} must be a list"]

    seen: Set[str] = set()
    for i, item in enumerate(bank):
        if not isinstance(item, dict):
            errs.append(f"{K.EVIDENCE_BANK}[{i}] must be an object")
            continue

        eid = (item.get(K.EID) or "").strip()
        if not eid:
            errs.append(f"{K.EVIDENCE_BANK}[{i}] missing {K.EID}")
        elif eid in seen:
            errs.append(f"duplicate evidence id: {eid}")
        else:
            seen.add(eid)

        quote = (item.get(K.QUOTE) or "").strip()
        if not quote:
            errs.append(f"{K.EVIDENCE_BANK}[{i}] missing {K.QUOTE} (verbatim)")

        # start_char/end_char are recommended; validate if present (accept literal keys)
        sc = item.get(K.START_CHAR, item.get("start_char"))
        ec = item.get(K.END_CHAR, item.get("end_char"))
        if sc is not None and (not isinstance(sc, int) or sc < 0):
            errs.append(f"{K.EVIDENCE_BANK}[{i}].start_char invalid")
        if ec is not None and (not isinstance(ec, int) or ec < 0):
            errs.append(f"{K.EVIDENCE_BANK}[{i}].end_char invalid")
        if isinstance(sc, int) and isinstance(ec, int) and ec < sc:
            errs.append(f"{K.EVIDENCE_BANK}[{i}] end_char < start_char")

        src = item.get(K.SOURCE, item.get("source"))
        if src is not None and not isinstance(src, dict):
            errs.append(f"{K.EVIDENCE_BANK}[{i}].source must be an object if present")

    return errs


def _validate_eids_if_present(eids: Any, evidence_ids: Set[str], ctx: str) -> List[str]:
    """
    Validator-only: if evidence_eids exists, it must be a non-empty list of valid EIDs.
    The validator does NOT decide when evidence_eids is required; enforcer does.
    """
    if eids is None:
        return []
    if not isinstance(eids, list):
        return [f"{ctx}.evidence_eids must be a list"]
    if len(eids) == 0:
        return [f"{ctx}.evidence_eids must be non-empty when present"]

    errs: List[str] = []
    for eid in eids:
        if not isinstance(eid, str) or not eid.strip():
            errs.append(f"{ctx}.evidence_eids contains blank/invalid id")
        elif eid not in evidence_ids:
            errs.append(f"{ctx} references missing evidence_eid={eid}")
    return errs


# -----------------------------
# Facts layer validation (structural only)
# -----------------------------
_ALLOWED_FACT_VERDICTS = {
    "true",
    "false",
    "mixed",
    "unknown",
    "insufficient_evidence",
    "not_found",
    "uncheckable",
}

_ALLOWED_FACT_CHECKABILITY = {"checkable", "currently_uncheckable"}


def validate_facts_layer(out: Dict[str, Any], evidence_ids: Set[str]) -> List[str]:
    errs: List[str] = []
    fl = out.get(K.FACTS_LAYER)
    if fl is None:
        return [f"{K.FACTS_LAYER} is required"]
    if not isinstance(fl, dict):
        return [f"{K.FACTS_LAYER} must be an object"]

    facts = fl.get(K.FACTS, [])
    if not isinstance(facts, list):
        return [f"{K.FACTS_LAYER}.{K.FACTS} must be a list"]

    for i, f in enumerate(facts):
        ctx = f"{K.FACTS_LAYER}.{K.FACTS}[{i}]"
        if not isinstance(f, dict):
            errs.append(f"{ctx} must be an object")
            continue

        if not (f.get(K.FACT_ID) or "").strip():
            errs.append(f"{ctx} missing {K.FACT_ID}")
        if not (f.get(K.FACT_TEXT) or "").strip():
            errs.append(f"{ctx} missing {K.FACT_TEXT}")

        checkability = f.get(K.CHECKABILITY)
        if checkability not in _ALLOWED_FACT_CHECKABILITY:
            errs.append(f"{ctx}.{K.CHECKABILITY} must be one of {sorted(_ALLOWED_FACT_CHECKABILITY)}")

        verdict = f.get(K.VERDICT)
        if verdict not in _ALLOWED_FACT_VERDICTS:
            errs.append(f"{ctx}.{K.VERDICT} must be one of {sorted(_ALLOWED_FACT_VERDICTS)}")

        # If evidence_eids is present, it must reference valid EIDs (requirement lives in enforcer)
        errs += _validate_eids_if_present(f.get(K.EVIDENCE_EIDS) or f.get("evidence_eids"), evidence_ids, ctx)

    return errs


# -----------------------------
# Claim Registry validation (structural + reference checks)
# -----------------------------
_ALLOWED_STAKES = {"low", "medium", "high"}


def validate_claim_registry(out: Dict[str, Any], evidence_ids: Set[str]) -> List[str]:
    errs: List[str] = []
    cr = out.get(K.CLAIM_REGISTRY)
    if cr is None:
        return [f"{K.CLAIM_REGISTRY} is required"]
    if not isinstance(cr, dict):
        return [f"{K.CLAIM_REGISTRY} must be an object"]

    claims = cr.get(K.CLAIMS, [])
    if not isinstance(claims, list):
        return [f"{K.CLAIM_REGISTRY}.{K.CLAIMS} must be a list"]

    for i, c in enumerate(claims):
        ctx = f"{K.CLAIM_REGISTRY}.{K.CLAIMS}[{i}]"
        if not isinstance(c, dict):
            errs.append(f"{ctx} must be an object")
            continue

        if not (c.get(K.CLAIM_ID) or "").strip():
            errs.append(f"{ctx} missing {K.CLAIM_ID}")
        if not (c.get(K.CLAIM_TEXT) or "").strip():
            errs.append(f"{ctx} missing {K.CLAIM_TEXT}")

        stakes = c.get(K.STAKES)
        if stakes is not None and stakes not in _ALLOWED_STAKES:
            errs.append(f"{ctx}.{K.STAKES} must be one of {sorted(_ALLOWED_STAKES)} if present")

        # If evidence_eids is present, validate refs (requirement lives in enforcer for future unification)
        errs += _validate_eids_if_present(c.get(K.EVIDENCE_EIDS) or c.get("evidence_eids"), evidence_ids, ctx)

    return errs


# -----------------------------
# Report pack validation
# -----------------------------
def _validate_rating(value: Any, ctx: str) -> List[str]:
    if value is None:
        return [f"{ctx} missing {K.RATING}"]
    if not isinstance(value, int):
        return [f"{ctx}.{K.RATING} must be an integer 1–5"]
    if value < 1 or value > 5:
        return [f"{ctx}.{K.RATING} must be between 1 and 5"]
    return []


def _validate_report_pack_internal(out: Dict[str, Any], evidence_ids: Set[str]) -> List[str]:
    errs: List[str] = []
    rp = out.get(K.REPORT_PACK, {})

    if not isinstance(rp, dict):
        return [f"{K.REPORT_PACK} must be an object"]

    if not (rp.get(K.SUMMARY_ONE_PARAGRAPH) or rp.get("summary_one_paragraph") or "").strip():
        errs.append(f"{K.REPORT_PACK}.summary_one_paragraph is required")

    if not (rp.get(K.READER_INTERPRETATION_GUIDE) or rp.get("reader_interpretation_guide") or "").strip():
        errs.append(f"{K.REPORT_PACK}.reader_interpretation_guide is required")

    findings_pack = rp.get(K.FINDINGS_PACK, {}) or {}
    if not isinstance(findings_pack, dict):
        errs.append(f"{K.REPORT_PACK}.{K.FINDINGS_PACK} must be an object")
        return errs

    # findings_pack currently uses literal "items"
    findings = findings_pack.get("items", []) or []
    if not isinstance(findings, list):
        errs.append(f"{K.REPORT_PACK}.{K.FINDINGS_PACK}.items must be a list")
        return errs

    for i, it in enumerate(findings):
        ctx = f"{K.REPORT_PACK}.{K.FINDINGS_PACK}.items[{i}]"
        if not isinstance(it, dict):
            errs.append(f"{ctx} must be an object")
            continue

        if not (it.get(K.FINDING_ID) or it.get("finding_id") or "").strip():
            errs.append(f"{ctx} missing finding_id")

        if not (it.get(K.RESTATED_CLAIM) or it.get("restated_claim") or "").strip():
            errs.append(f"{ctx} missing restated_claim")

        if not (it.get(K.FINDING_TEXT) or it.get("finding_text") or "").strip():
            errs.append(f"{ctx} missing finding_text")

        errs += _validate_rating(it.get(K.RATING) if K.RATING in it else it.get("rating"), ctx)

        # If evidence_eids is present, validate refs (normative requirement will live in enforcer later)
        errs += _validate_eids_if_present(it.get(K.EVIDENCE_EIDS) or it.get("evidence_eids"), evidence_ids, ctx)

    # scholar_pack optional
    scholar_pack = rp.get(K.SCHOLAR_PACK) if K.SCHOLAR_PACK in rp else rp.get("scholar_pack")
    if scholar_pack is not None:
        if not isinstance(scholar_pack, dict):
            errs.append(f"{K.REPORT_PACK}.scholar_pack must be an object if present")
        else:
            items = scholar_pack.get("items", [])
            if items is not None and not isinstance(items, list):
                errs.append(f"{K.REPORT_PACK}.scholar_pack.items must be a list if present")

    return errs


# -----------------------------
# Presentation integrity / headline-body delta
# -----------------------------
def validate_headline_body_delta(out: Dict[str, Any], evidence_ids: Set[str]) -> List[str]:
    """
    Structural validation only.
    headline_body_delta: { present: bool, items: [] }
    If an item includes evidence_eids, validate that references exist.
    """
    errs: List[str] = []
    hbd = out.get(K.HEADLINE_BODY_DELTA, out.get("headline_body_delta"))
    if hbd is None:
        return errs  # optional

    if not isinstance(hbd, dict):
        return ["headline_body_delta must be an object if present"]

    present = hbd.get(K.PRESENT, hbd.get("present"))
    items = hbd.get(K.ITEMS, hbd.get("items", [])) or []

    if present is not None and not isinstance(present, bool):
        errs.append("headline_body_delta.present must be boolean if present")

    if not isinstance(items, list):
        errs.append("headline_body_delta.items must be a list")
        return errs

    for i, item in enumerate(items):
        ctx = f"headline_body_delta.items[{i}]"
        if not isinstance(item, dict):
            errs.append(f"{ctx} must be an object")
            continue

        headline = (item.get("headline_text") or item.get("headline") or "")
        body = (item.get("body_text") or item.get("body") or "")
        if not isinstance(headline, str) or not headline.strip():
            errs.append(f"{ctx} missing headline_text/headline")
        if not isinstance(body, str) or not body.strip():
            errs.append(f"{ctx} missing body_text/body")

        errs += _validate_eids_if_present(item.get(K.EVIDENCE_EIDS) or item.get("evidence_eids"), evidence_ids, ctx)

    return errs


# -----------------------------
# Evidence density (metrics)
# -----------------------------
def validate_evidence_density(out: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    metrics = out.get(K.METRICS, {}) or {}
    ed = metrics.get(K.EVIDENCE_DENSITY, metrics.get("evidence_density", {}))

    if not isinstance(ed, dict) or not ed:
        return ["metrics.evidence_density is required"]

    try:
        num_claims = int(ed.get(K.NUM_CLAIMS, ed.get("num_claims", -1)))
        num_evidence_items = int(ed.get(K.NUM_EVIDENCE_ITEMS, ed.get("num_evidence_items", -1)))
        ratio = ed.get(K.EVIDENCE_TO_CLAIM_RATIO, ed.get("evidence_to_claim_ratio"))
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
    Structural validation only.
    If counterevidence_found, require items with verbatim quote fields (shape only).
    """
    errs: List[str] = []
    metrics = out.get(K.METRICS, {}) or {}
    cs = metrics.get(K.COUNTEREVIDENCE_STATUS, metrics.get("counterevidence_status"))

    if cs is None:
        return errs  # optional for now

    if not isinstance(cs, dict):
        return ["metrics.counterevidence_status must be an object if present"]

    status = cs.get(K.STATUS, cs.get("status"))
    if status not in _ALLOWED_COUNTEREVIDENCE_STATUS:
        errs.append(
            f"metrics.counterevidence_status.status must be one of {sorted(_ALLOWED_COUNTEREVIDENCE_STATUS)}"
        )

    if status != "not_applicable":
        if not (cs.get(K.SEARCH_SCOPE, cs.get("search_scope")) or "").strip():
            errs.append("metrics.counterevidence_status.search_scope is required when status != not_applicable")
        if not (cs.get(K.RESULT, cs.get("result")) or "").strip():
            errs.append("metrics.counterevidence_status.result is required when status != not_applicable")

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


# -----------------------------
# NEW ANALYSIS MODULE VALIDATOR
# -----------------------------
def validate_new_analysis_modules(out: Dict[str, Any]) -> List[str]:
    """
    Structural-only checks for new pillar sockets.
    Uses literal keys for now to avoid schema_names drift.
    (We can add K constants after this is stable.)
    """
    errs: List[str] = []

    # Optional new sockets (legacy schema may omit them)
    article_layer = out.get("article_layer", None)
    if article_layer is not None and not isinstance(article_layer, dict):
        errs.append("article_layer must be an object if present")
        return errs

    if isinstance(article_layer, dict):
        pia = article_layer.get("premise_independence_analysis", None)
        if pia is not None and not isinstance(pia, dict):
            errs.append("article_layer.premise_independence_analysis must be an object")

    facts_layer = out.get(K.FACTS_LAYER, None)
    if facts_layer is not None and not isinstance(facts_layer, dict):
        errs.append("facts_layer must be an object")
        return errs

    if isinstance(facts_layer, dict):
        raa = facts_layer.get("reality_alignment_analysis", None)
        if raa is not None and not isinstance(raa, dict):
            errs.append("facts_layer.reality_alignment_analysis must be an object")

    return errs


