

#!/usr/bin/env python3
"""
FILE: integrity_validator.py
PURPOSE: BiasLens structural validator — HARD LOCKED.

LOCK:
BiasLens enforces schema singularity via schema_names.K.
Literal key fallbacks are forbidden.
Validator fails closed on any non-K schema.
"""

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
    errors: List[str] = []

    errors += validate_top_level(output)

    evidence_ids = collect_evidence_ids(output)

    # Normative rules
    errors += enforce_integrity(output, evidence_ids)

    # Structural
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


# -----------------------------
# Top-level sanity
# -----------------------------
def validate_top_level(out: Any) -> List[str]:
    if not isinstance(out, dict):
        return ["output must be an object/dict"]

    errs: List[str] = []

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

    if not isinstance(out.get(K.RUN_METADATA), dict):
        errs.append(f"{K.RUN_METADATA} must be an object")

    sv = out.get(K.SCHEMA_VERSION)
    if not isinstance(sv, str) or not sv.strip():
        errs.append(f"{K.SCHEMA_VERSION} must be a non-empty string")

    return errs


# -----------------------------
# Evidence helpers
# -----------------------------
def collect_evidence_ids(out: Dict[str, Any]) -> Set[str]:
    bank = out.get(K.EVIDENCE_BANK)

    if not isinstance(bank, list):
        return set()

    ids: Set[str] = set()

    for item in bank:
        if isinstance(item, dict):
            eid = (item.get(K.EID) or "").strip()
            if eid:
                ids.add(eid)

    return ids


def validate_evidence_bank(out: Dict[str, Any]) -> List[str]:
    bank = out.get(K.EVIDENCE_BANK)

    if not isinstance(bank, list):
        return [f"{K.EVIDENCE_BANK} must be a list"]

    errs: List[str] = []
    seen: Set[str] = set()

    for i, item in enumerate(bank):
        ctx = f"{K.EVIDENCE_BANK}[{i}]"

        if not isinstance(item, dict):
            errs.append(f"{ctx} must be an object")
            continue

        eid = (item.get(K.EID) or "").strip()
        if not eid:
            errs.append(f"{ctx} missing {K.EID}")
        elif eid in seen:
            errs.append(f"duplicate evidence id: {eid}")
        else:
            seen.add(eid)

        quote = (item.get(K.QUOTE) or "").strip()
        if not quote:
            errs.append(f"{ctx} missing {K.QUOTE}")

        sc = item.get(K.START_CHAR)
        ec = item.get(K.END_CHAR)

        if sc is not None and (not isinstance(sc, int) or sc < 0):
            errs.append(f"{ctx}.{K.START_CHAR} invalid")

        if ec is not None and (not isinstance(ec, int) or ec < 0):
            errs.append(f"{ctx}.{K.END_CHAR} invalid")

        if isinstance(sc, int) and isinstance(ec, int) and ec < sc:
            errs.append(f"{ctx} end_char < start_char")

        src = item.get(K.SOURCE)
        if src is not None and not isinstance(src, dict):
            errs.append(f"{ctx}.{K.SOURCE} must be an object")

    return errs


def _validate_eids_if_present(eids: Any, evidence_ids: Set[str], ctx: str) -> List[str]:
    if eids is None:
        return []

    if not isinstance(eids, list):
        return [f"{ctx}.{K.EVIDENCE_EIDS} must be a list"]

    if len(eids) == 0:
        return [f"{ctx}.{K.EVIDENCE_EIDS} must be non-empty"]

    errs: List[str] = []

    for eid in eids:
        if not isinstance(eid, str) or not eid.strip():
            errs.append(f"{ctx}.{K.EVIDENCE_EIDS} contains invalid id")
        elif eid not in evidence_ids:
            errs.append(f"{ctx} references missing evidence_eid={eid}")

    return errs


# -----------------------------
# Facts layer
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
    fl = out.get(K.FACTS_LAYER)

    if not isinstance(fl, dict):
        return [f"{K.FACTS_LAYER} must be an object"]

    facts = fl.get(K.FACTS)

    if not isinstance(facts, list):
        return [f"{K.FACTS_LAYER}.{K.FACTS} must be a list"]

    errs: List[str] = []

    for i, f in enumerate(facts):
        ctx = f"{K.FACTS_LAYER}.{K.FACTS}[{i}]"

        if not isinstance(f, dict):
            errs.append(f"{ctx} must be an object")
            continue

        if not (f.get(K.FACT_ID) or "").strip():
            errs.append(f"{ctx} missing {K.FACT_ID}")

        if not (f.get(K.FACT_TEXT) or "").strip():
            errs.append(f"{ctx} missing {K.FACT_TEXT}")

        if f.get(K.CHECKABILITY) not in _ALLOWED_FACT_CHECKABILITY:
            errs.append(f"{ctx}.{K.CHECKABILITY} invalid")

        if f.get(K.VERDICT) not in _ALLOWED_FACT_VERDICTS:
            errs.append(f"{ctx}.{K.VERDICT} invalid")

        errs += _validate_eids_if_present(
            f.get(K.EVIDENCE_EIDS),
            evidence_ids,
            ctx,
        )

    return errs


# -----------------------------
# Claim registry
# -----------------------------
_ALLOWED_STAKES = {"low", "medium", "high"}


def validate_claim_registry(out: Dict[str, Any], evidence_ids: Set[str]) -> List[str]:
    cr = out.get(K.CLAIM_REGISTRY)

    if not isinstance(cr, dict):
        return [f"{K.CLAIM_REGISTRY} must be an object"]

    claims = cr.get(K.CLAIMS)

    if not isinstance(claims, list):
        return [f"{K.CLAIM_REGISTRY}.{K.CLAIMS} must be a list"]

    errs: List[str] = []

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
            errs.append(f"{ctx}.{K.STAKES} invalid")

        errs += _validate_eids_if_present(
            c.get(K.EVIDENCE_EIDS),
            evidence_ids,
            ctx,
        )

    return errs


# -----------------------------
# Report pack
# -----------------------------
def _validate_rating(value: Any, ctx: str) -> List[str]:
    if not isinstance(value, int) or not (1 <= value <= 5):
        return [f"{ctx}.{K.RATING} must be 1–5"]
    return []


def _validate_report_pack_internal(out: Dict[str, Any], evidence_ids: Set[str]) -> List[str]:
    rp = out.get(K.REPORT_PACK)

    if not isinstance(rp, dict):
        return [f"{K.REPORT_PACK} must be an object"]

    errs: List[str] = []

    if not (rp.get(K.SUMMARY_ONE_PARAGRAPH) or "").strip():
        errs.append(f"{K.REPORT_PACK}.{K.SUMMARY_ONE_PARAGRAPH} required")

    if not (rp.get(K.READER_INTERPRETATION_GUIDE) or "").strip():
        errs.append(f"{K.REPORT_PACK}.{K.READER_INTERPRETATION_GUIDE} required")

    findings_pack = rp.get(K.FINDINGS_PACK)

    if not isinstance(findings_pack, dict):
        return [f"{K.REPORT_PACK}.{K.FINDINGS_PACK} must be an object"]

    findings = findings_pack.get(K.ITEMS)

    if not isinstance(findings, list):
        return [f"{K.REPORT_PACK}.{K.FINDINGS_PACK}.{K.ITEMS} must be a list"]

    for i, it in enumerate(findings):
        ctx = f"{K.REPORT_PACK}.{K.FINDINGS_PACK}.{K.ITEMS}[{i}]"

        if not isinstance(it, dict):
            errs.append(f"{ctx} must be an object")
            continue

        if not (it.get(K.FINDING_ID) or "").strip():
            errs.append(f"{ctx} missing {K.FINDING_ID}")

        if not (it.get(K.RESTATED_CLAIM) or "").strip():
            errs.append(f"{ctx} missing {K.RESTATED_CLAIM}")

        if not (it.get(K.FINDING_TEXT) or "").strip():
            errs.append(f"{ctx} missing {K.FINDING_TEXT}")

        errs += _validate_rating(it.get(K.RATING), ctx)

        errs += _validate_eids_if_present(
            it.get(K.EVIDENCE_EIDS),
            evidence_ids,
            ctx,
        )

    return errs


# -----------------------------
# Headline-body delta
# -----------------------------
def validate_headline_body_delta(out: Dict[str, Any], evidence_ids: Set[str]) -> List[str]:
    hbd = out.get(K.HEADLINE_BODY_DELTA)

    if hbd is None:
        return []

    if not isinstance(hbd, dict):
        return [f"{K.HEADLINE_BODY_DELTA} must be an object"]

    errs: List[str] = []

    present = hbd.get(K.PRESENT)
    items = hbd.get(K.ITEMS)

    if present is not None and not isinstance(present, bool):
        errs.append(f"{K.HEADLINE_BODY_DELTA}.{K.PRESENT} must be boolean")

    if not isinstance(items, list):
        errs.append(f"{K.HEADLINE_BODY_DELTA}.{K.ITEMS} must be a list")
        return errs

    for i, item in enumerate(items):
        ctx = f"{K.HEADLINE_BODY_DELTA}.{K.ITEMS}[{i}]"

        if not isinstance(item, dict):
            errs.append(f"{ctx} must be an object")
            continue

        if not (item.get(K.HEADLINE_TEXT) or "").strip():
            errs.append(f"{ctx} missing {K.HEADLINE_TEXT}")

        if not (item.get(K.BODY_TEXT) or "").strip():
            errs.append(f"{ctx} missing {K.BODY_TEXT}")

        errs += _validate_eids_if_present(
            item.get(K.EVIDENCE_EIDS),
            evidence_ids,
            ctx,
        )

    return errs


# -----------------------------
# Evidence density
# -----------------------------
def validate_evidence_density(out: Dict[str, Any]) -> List[str]:
    metrics = out.get(K.METRICS)

    if not isinstance(metrics, dict):
        return [f"{K.METRICS} must be an object"]

    ed = metrics.get(K.EVIDENCE_DENSITY)

    if not isinstance(ed, dict):
        return [f"{K.METRICS}.{K.EVIDENCE_DENSITY} required"]

    errs: List[str] = []

    try:
        num_claims = int(ed.get(K.NUM_CLAIMS))
        num_evidence_items = int(ed.get(K.NUM_EVIDENCE_ITEMS))
        ratio = float(ed.get(K.EVIDENCE_TO_CLAIM_RATIO))
    except Exception:
        return [f"{K.METRICS}.{K.EVIDENCE_DENSITY} invalid numeric fields"]

    expected = num_evidence_items / max(1, num_claims)

    if abs(ratio - expected) > 1e-6:
        errs.append(f"{K.METRICS}.{K.EVIDENCE_DENSITY} ratio incorrect")

    return errs


# -----------------------------
# Counterevidence
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
    metrics = out.get(K.METRICS)

    if not isinstance(metrics, dict):
        return []

    cs = metrics.get(K.COUNTEREVIDENCE_STATUS)

    if cs is None:
        return []

    if not isinstance(cs, dict):
        return [f"{K.METRICS}.{K.COUNTEREVIDENCE_STATUS} must be an object"]

    errs: List[str] = []

    status = cs.get(K.STATUS)

    if status not in _ALLOWED_COUNTEREVIDENCE_STATUS:
        errs.append(f"{K.METRICS}.{K.COUNTEREVIDENCE_STATUS}.{K.STATUS} invalid")

    if status == "counterevidence_found":
        items = cs.get(K.ITEMS)

        if not isinstance(items, list) or not items:
            errs.append("counterevidence_found requires items")

        for i, it in enumerate(items):
            ctx = f"{K.METRICS}.{K.COUNTEREVIDENCE_STATUS}.{K.ITEMS}[{i}]"

            if not isinstance(it, dict):
                errs.append(f"{ctx} must be object")
                continue

            if not (it.get(K.SOURCE_ID) or "").strip():
                errs.append(f"{ctx} missing {K.SOURCE_ID}")

            if not (it.get(K.QUOTE_VERBATIM) or "").strip():
                errs.append(f"{ctx} missing {K.QUOTE_VERBATIM}")

    return errs


# -----------------------------
# New pillar sockets
# -----------------------------
def validate_new_analysis_modules(out: Dict[str, Any]) -> List[str]:
    errs: List[str] = []

    article_layer = out.get(K.ARTICLE_LAYER)
    if article_layer is not None and not isinstance(article_layer, dict):
        errs.append(f"{K.ARTICLE_LAYER} must be an object")

    if isinstance(article_layer, dict):
        pia = article_layer.get(K.PREMISE_INDEPENDENCE_ANALYSIS)
        if pia is not None and not isinstance(pia, dict):
            errs.append(f"{K.ARTICLE_LAYER}.{K.PREMISE_INDEPENDENCE_ANALYSIS} must be an object")

    facts_layer = out.get(K.FACTS_LAYER)
    if facts_layer is not None and not isinstance(facts_layer, dict):
        errs.append(f"{K.FACTS_LAYER} must be an object")

    if isinstance(facts_layer, dict):
        raa = facts_layer.get(K.REALITY_ALIGNMENT_ANALYSIS)
        if raa is not None and not isinstance(raa, dict):
            errs.append(f"{K.FACTS_LAYER}.{K.REALITY_ALIGNMENT_ANALYSIS} must be an object")

    return errs
