from __future__ import annotations

from typing import Any, Dict, List, Set

from .errors import ValidationError


def path(p: str, key: str) -> str:
    return f"{p}.{key}" if p else key


def is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def is_list(x: Any) -> bool:
    return isinstance(x, list)


def is_dict(x: Any) -> bool:
    return isinstance(x, dict)


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValidationError(msg)


def require_key(obj: Dict[str, Any], key: str, p: str) -> Any:
    require(key in obj, f"Missing required field: {path(p, key)}")
    return obj[key]


def optional_key(obj: Dict[str, Any], key: str, default: Any = None) -> Any:
    return obj.get(key, default)


def require_nonempty_str(obj: Dict[str, Any], key: str, p: str) -> str:
    v = require_key(obj, key, p)
    require(is_nonempty_str(v), f"Field must be a non-empty string: {path(p, key)}")
    return v.strip()


def require_list(obj: Dict[str, Any], key: str, p: str) -> List[Any]:
    v = require_key(obj, key, p)
    require(is_list(v), f"Field must be a list: {path(p, key)}")
    return v


def require_dict(obj: Dict[str, Any], key: str, p: str) -> Dict[str, Any]:
    v = require_key(obj, key, p)
    require(is_dict(v), f"Field must be an object/dict: {path(p, key)}")
    return v


def collect_eids(evidence_bank: List[Dict[str, Any]]) -> Set[str]:
    eids: Set[str] = set()
    for i, e in enumerate(evidence_bank):
        p = f"evidence_bank[{i}]"
        require(is_dict(e), f"{p} must be an object/dict")

        eid = require_nonempty_str(e, "eid", p)
        require(eid not in eids, f"Duplicate eid found: {eid} at {p}.eid")

        quote = require_nonempty_str(e, "quote", p)
        require(len(quote) >= 12, f"{p}.quote too short (min 12 chars)")

        start_char = optional_key(e, "start_char")
        end_char = optional_key(e, "end_char")
        if start_char is not None:
            require(isinstance(start_char, int) and start_char >= 0, f"{p}.start_char must be int >= 0")
        if end_char is not None:
            require(isinstance(end_char, int) and end_char >= 0, f"{p}.end_char must be int >= 0")

        why = optional_key(e, "why_relevant")
        if why is not None:
            require(is_nonempty_str(why), f"{p}.why_relevant must be non-empty if present")

        eids.add(eid)

    return eids


def validate_evidence_refs(eids: Set[str], refs: Any, p: str) -> None:
    require(is_list(refs), f"{p} must be a list of evidence_eids")
    for j, r in enumerate(refs):
        require(is_nonempty_str(r), f"{p}[{j}] must be a non-empty string eid")
        require(r in eids, f"{p}[{j}] references unknown eid '{r}'")


def validate_epistemic_state(node: Dict[str, Any], p: str) -> None:
    state = optional_key(node, "epistemic_state")
    if state is None:
        alt = optional_key(node, "status") or optional_key(node, "verification_status")
        require(is_nonempty_str(alt), f"{p} must declare epistemic_state/status/verification_status")
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
    require(str(state) in allowed, f"{p} epistemic state '{state}' not in {sorted(allowed)}")


def ban_intent_language(text: str, p: str) -> None:
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
        require(b not in lowered, f"{p} contains intent-claim language ('{b}')")
