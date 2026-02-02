
#!/usr/bin/env python3
"""
FILE: enforcers/facts_enforcer.py
VERSION: 0.2
LAST UPDATED: 2026-01-31
PURPOSE: Normative enforcement for Facts Layer in BiasLens.

Notes:
- Enforces evidence requirements for checkable facts with non-unknown verdicts.
- Enforces star caps for facts_layer.fact_table_integrity via shared policy
  (see enforcers/facts_star_policy.py) to prevent drift between producer and enforcer.
- Structural legality remains the responsibility of integrity_validator.py.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from schema_names import K
from enforcers.facts_star_policy import compute_fact_table_max_star, UNKNOWN_VERDICTS


def enforce_facts(out: Dict[str, Any], evidence_ids: Set[str]) -> List[str]:
    errs: List[str] = []

    fl = out.get(K.FACTS_LAYER)
    if not isinstance(fl, dict):
        return errs

    facts = fl.get(K.FACTS, [])
    if not isinstance(facts, list):
        return errs

    # --- Evidence required rules (normative)
    for i, f in enumerate(facts):
        if not isinstance(f, dict):
            continue

        verdict = f.get(K.VERDICT)
        checkability = f.get(K.CHECKABILITY)

        if checkability != "checkable":
            continue
        if verdict in UNKNOWN_VERDICTS:
            continue

        eids = f.get(K.EVIDENCE_EIDS)
        ctx = f"facts_layer.facts[{i}]"

        if not isinstance(eids, list) or len(eids) == 0:
            errs.append(f"{ctx}.evidence_eids required when verdict != unknown-like")
            continue

        for eid in eids:
            if not isinstance(eid, str) or not eid.strip():
                errs.append(f"{ctx}.evidence_eids contains blank id")
            elif eid not in evidence_ids:
                errs.append(f"{ctx} references missing evidence_eid={eid}")

    # --- Star caps based on epistemic outcomes (normative; shared policy)
    integ = fl.get(K.FACT_TABLE_INTEGRITY)
    if not isinstance(integ, dict):
        return errs

    stars = integ.get(K.STARS)
    if not isinstance(stars, int):
        return errs

    max_star = compute_fact_table_max_star(facts)

    if stars > max_star:
        errs.append(f"facts_layer.fact_table_integrity.stars={stars} violates cap max={max_star}")

    return errs
