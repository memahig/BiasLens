# enforcers/article_enforcer.py
from __future__ import annotations

from typing import Any, Dict, List

from schema_names import K


def enforce_article_layer(out: Dict[str, Any]) -> List[str]:
    errs: List[str] = []

    article_layer = out.get(K.ARTICLE_LAYER)
    if article_layer is None:
        return errs

    if not isinstance(article_layer, dict):
        return ["article_layer must be an object if present"]

    pres = article_layer.get(K.PRESENTATION_INTEGRITY)
    if pres is None:
        errs.append("article_layer.presentation_integrity is required (status run|not_run)")
        return errs

    if not isinstance(pres, dict):
        errs.append("article_layer.presentation_integrity must be an object")
        return errs

    status = pres.get(K.MODULE_STATUS, pres.get(K.STATUS))
    if status not in {"run", "not_run"}:
        errs.append(
            "article_layer.presentation_integrity.status must be 'run' or 'not_run'"
        )

    return errs
