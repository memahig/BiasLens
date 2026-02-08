from __future__ import annotations

from typing import Any, Dict, List, Set

from .core import (
    ban_intent_language,
    collect_eids,
    is_dict,
    optional_key,
    path,
    require,
    require_key,
    require_list,
    require_nonempty_str,
    validate_epistemic_state,
    validate_evidence_refs,
)


def validate_pass_a_pack(pass_a: Dict[str, Any]) -> Set[str]:
    """
    Validates Pass A output:
      - evidence_bank
      - facts
      - claim_registry
    Returns the set of valid evidence EIDs for downstream use.
    """
    require(is_dict(pass_a), "Pass A pack must be a dict/object")

    evidence_bank = require_list(pass_a, "evidence_bank", "")
    eids = collect_eids(evidence_bank)

    facts = require_list(pass_a, "facts", "")
    claim_registry = require_list(pass_a, "claim_registry", "")

    _validate_facts(facts, eids)
    _validate_claim_registry(claim_registry, eids)

    return eids


def _validate_facts(facts: List[Any], eids: Set[str]) -> None:
    for i, f in enumerate(facts):
        p = f"facts[{i}]"
        require(is_dict(f), f"{p} must be an object/dict")

        require_nonempty_str(f, "fact_id", p)
        require_nonempty_str(f, "fact_text", p)

        checkable = require_key(f, "checkable", p)
        require(isinstance(checkable, bool), f"{p}.checkable must be boolean")

        validate_epistemic_state(f, p)

        ev = optional_key(f, "evidence_eids", [])
        if checkable:
            validate_evidence_refs(eids, ev, path(p, "evidence_eids"))
        else:
            if ev:
                validate_evidence_refs(eids, ev, path(p, "evidence_eids"))

        ban_intent_language(f["fact_text"], path(p, "fact_text"))


def _validate_claim_registry(claims: List[Any], eids: Set[str]) -> None:
    seen = set()
    for i, c in enumerate(claims):
        p = f"claim_registry[{i}]"
        require(is_dict(c), f"{p} must be an object/dict")

        cid = require_nonempty_str(c, "claim_id", p)
        require(cid not in seen, f"Duplicate claim_id '{cid}' at {p}.claim_id")
        seen.add(cid)

        require_nonempty_str(c, "claim_text", p)
        validate_epistemic_state(c, p)

        ev = require_key(c, "evidence_eids", p)
        validate_evidence_refs(eids, ev, path(p, "evidence_eids"))
