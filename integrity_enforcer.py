#!/usr/bin/env python3
"""
FILE: integrity_enforcer.py
VERSION: 0.2
LAST UPDATED: 2026-02-02
PURPOSE: Aggregate normative enforcement for BiasLens (non-structural rules).
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from schema_names import K

from enforcers.integrity_objects import enforce_integrity_objects
from enforcers.facts_enforcer import enforce_facts
from enforcers.article_enforcer import enforce_article_layer


def enforce_integrity(out: Dict[str, Any], evidence_ids: Set[str]) -> List[str]:
    errs: List[str] = []

    errs += enforce_integrity_objects(out)
    errs += enforce_facts(out, evidence_ids)
    errs += enforce_article_layer(out)

    errs += _enforce_premise_independence(out)
    errs += _enforce_reality_alignment(out)

    return errs


# 🔒 NEW NORMATIVE LOCKS

def _enforce_premise_independence(out: Dict[str, Any]) -> List[str]:
    errs: List[str] = []

    article_layer = out.get(K.ARTICLE_LAYER)
    if article_layer is None:
        return errs

    if not isinstance(article_layer, dict):
        errs.append("article_layer must be an object for premise_independence_analysis enforcement")
        return errs

    pia = article_layer.get(K.PREMISE_INDEPENDENCE_ANALYSIS)

    if pia is None:
        errs.append(
            "premise_independence_analysis missing from article_layer (Reasoning Integrity pillar required)"
        )
        return errs

    if not isinstance(pia, dict):
        errs.append("premise_independence_analysis must be an object")

    return errs

def _enforce_reality_alignment(out: Dict[str, Any]) -> List[str]:
    errs: List[str] = []

    facts_layer = out.get(K.FACTS_LAYER)
    if facts_layer is None:
        return errs

    if not isinstance(facts_layer, dict):
        errs.append("facts_layer must be an object for reality_alignment_analysis enforcement")
        return errs

    raa = facts_layer.get(K.REALITY_ALIGNMENT_ANALYSIS)

    if raa is None:
        errs.append(
            "reality_alignment_analysis missing from facts_layer (Reality Alignment pillar required)"
        )
        return errs

    if not isinstance(raa, dict):
        errs.append("reality_alignment_analysis must be an object")

    return errs

