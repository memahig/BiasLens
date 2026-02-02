from __future__ import annotations

from typing import Any, Dict, List, Set

from .core import (
    ban_intent_language,
    is_dict,
    is_list,
    optional_key,
    path,
    require,
    require_dict,
    require_list,
    require_nonempty_str,
    validate_epistemic_state,
    validate_evidence_refs,
)


def validate_pass_b_pack(full_pack: Dict[str, Any], eids: Set[str]) -> None:
    """
    Validates Pass B / full report pack AFTER Pass A has validated.
    Requires:
      - claim_evaluations, argument_layer, article_layer
      - headline_body_delta, reader_interpretation
    Enforces claim-restatement matching claim_registry.
    """
    require(is_dict(full_pack), "Full pack must be a dict/object")

    claim_registry = require_list(full_pack, "claim_registry", "")
    id_to_text = _map_claims(claim_registry)

    claim_evaluations = require_list(full_pack, "claim_evaluations", "")
    argument_layer = require_dict(full_pack, "argument_layer", "")
    article_layer = require_dict(full_pack, "article_layer", "")

    headline_body_delta = require_dict(full_pack, "headline_body_delta", "")
    reader_interpretation = require_dict(full_pack, "reader_interpretation", "")

    _validate_claim_evaluations(claim_evaluations, id_to_text, eids)
    _validate_argument_layer(argument_layer)
    _validate_article_layer(article_layer)
    _validate_headline_body_delta(headline_body_delta, eids)
    _validate_reader_interpretation(reader_interpretation, eids)


def _map_claims(claim_registry: List[Any]) -> Dict[str, str]:
    id_to_text: Dict[str, str] = {}
    for c in claim_registry:
        if not isinstance(c, dict):
            continue
        cid = c.get("claim_id")
        ctext = c.get("claim_text")
        if isinstance(cid, str) and cid.strip() and isinstance(ctext, str) and ctext.strip():
            id_to_text[cid.strip()] = ctext.strip()
    return id_to_text


def _norm(s: str) -> str:
    return " ".join(s.split())


def _validate_claim_evaluations(
    claim_evals: List[Any],
    id_to_text: Dict[str, str],
    eids: Set[str],
) -> None:
    for i, ce in enumerate(claim_evals):
        p = f"claim_evaluations[{i}]"
        require(is_dict(ce), f"{p} must be an object/dict")

        cid = require_nonempty_str(ce, "claim_id", p)
        restated = require_nonempty_str(ce, "claim_restatement", p)

        if cid in id_to_text:
            require(
                _norm(id_to_text[cid]) == _norm(restated),
                f"{p}.claim_restatement must exactly match claim_registry claim_text for {cid}",
            )

        validate_epistemic_state(ce, p)

        findings = require_list(ce, "findings", p)
        for j, f in enumerate(findings):
            fp = f"{p}.findings[{j}]"
            require(is_dict(f), f"{fp} must be an object/dict")

            text = require_nonempty_str(f, "finding_text", fp)
            ban_intent_language(text, path(fp, "finding_text"))

            ev = f.get("evidence_eids")
            require(ev is not None, f"Missing required field: {fp}.evidence_eids")
            validate_evidence_refs(eids, ev, path(fp, "evidence_eids"))

            vq = f.get("verbatim_quotes")
            require(is_list(vq), f"{fp}.verbatim_quotes must be a list")
            require(len(vq) >= 1, f"{fp}.verbatim_quotes must include at least 1 quote")
            for qk, q in enumerate(vq):
                require(isinstance(q, str) and q.strip(), f"{fp}.verbatim_quotes[{qk}] must be non-empty string")
                require(len(q.strip()) >= 12, f"{fp}.verbatim_quotes[{qk}] too short (min 12 chars)")

            f_type = optional_key(f, "finding_type")
            if isinstance(f_type, str) and f_type.strip().lower() in {
                "omission",
                "systematic_omission",
                "comparative_suppression",
            }:
                exp = require_nonempty_str(f, "expected_context", fp)
                miss = require_nonempty_str(f, "missing_context", fp)
                ban_intent_language(exp, path(fp, "expected_context"))
                ban_intent_language(miss, path(fp, "missing_context"))

            if "counterevidence" in f:
                cb = f["counterevidence"]
                require(is_dict(cb), f"{fp}.counterevidence must be an object/dict")
                require_nonempty_str(cb, "search_scope", f"{fp}.counterevidence")
                require_nonempty_str(cb, "result", f"{fp}.counterevidence")

                items = cb.get("items", [])
                require(is_list(items), f"{fp}.counterevidence.items must be a list")
                for kk, item in enumerate(items):
                    ip = f"{fp}.counterevidence.items[{kk}]"
                    require(is_dict(item), f"{ip} must be an object/dict")
                    require_nonempty_str(item, "counterclaim_text", ip)
                    validate_evidence_refs(eids, item.get("evidence_eids"), path(ip, "evidence_eids"))
                    vq2 = item.get("verbatim_quotes")
                    require(is_list(vq2) and len(vq2) >= 1, f"{ip}.verbatim_quotes must have >= 1 quote")


def _validate_argument_layer(argument_layer: Dict[str, Any]) -> None:
    p = "argument_layer"
    require_nonempty_str(argument_layer, "summary", p)
    validate_epistemic_state(argument_layer, p)


def _validate_article_layer(article_layer: Dict[str, Any]) -> None:
    p = "article_layer"
    require_nonempty_str(article_layer, "one_paragraph_summary", p)
    validate_epistemic_state(article_layer, p)

    for k in ["facts_rating", "claims_rating", "arguments_rating", "article_rating"]:
        if k in article_layer:
            v = article_layer[k]
            require(isinstance(v, int) and 1 <= v <= 5, f"{p}.{k} must be int 1..5")


def _validate_headline_body_delta(hbd: Dict[str, Any], eids: Set[str]) -> None:
    p = "headline_body_delta"
    require_nonempty_str(hbd, "headline", p)
    require_nonempty_str(hbd, "body_key_qualifiers", p)

    findings = require_list(hbd, "findings", p)
    require(len(findings) >= 1, f"{p}.findings must contain at least 1 item")

    for i, f in enumerate(findings):
        fp = f"{p}.findings[{i}]"
        require(is_dict(f), f"{fp} must be an object/dict")

        text = require_nonempty_str(f, "finding_text", fp)
        ban_intent_language(text, path(fp, "finding_text"))

        validate_evidence_refs(eids, f.get("evidence_eids"), path(fp, "evidence_eids"))

        vq = f.get("verbatim_quotes")
        require(is_list(vq) and len(vq) >= 1, f"{fp}.verbatim_quotes must include at least 1 quote")


def _validate_reader_interpretation(reader: Dict[str, Any], eids: Set[str]) -> None:
    p = "reader_interpretation"

    onep = require_nonempty_str(reader, "one_paragraph_summary", p)
    ban_intent_language(onep, path(p, "one_paragraph_summary"))

    mechanisms = require_list(reader, "named_mechanisms", p)
    require(len(mechanisms) >= 1, f"{p}.named_mechanisms must contain at least 1 item")

    for i, m in enumerate(mechanisms):
        mp = f"{p}.named_mechanisms[{i}]"
        require(is_dict(m), f"{mp} must be an object/dict")
        require_nonempty_str(m, "mechanism_name", mp)
        expl = require_nonempty_str(m, "plain_language_explanation", mp)
        ban_intent_language(expl, path(mp, "plain_language_explanation"))

    for tier_key in ["reader_in_depth", "scholar_in_depth"]:
        require(tier_key in reader, f"Missing required field: {p}.{tier_key}")
        require(isinstance(reader[tier_key], str), f"{p}.{tier_key} must be a string")

    cited = optional_key(reader, "evidence_eids")
    if cited is not None:
        validate_evidence_refs(eids, cited, path(p, "evidence_eids"))
