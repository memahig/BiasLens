#!/usr/bin/env python3
"""
FILE: tools/print_omission_candidates.py
VERSION: 0.1
LAST UPDATED: 2026-02-10
PURPOSE:
Calibration printer for INTERNAL omission candidates stored under run_metadata.
- Default: human-readable grouped output
- Optional: --json emits a compact JSON bundle (for assistant/regression/diff)
"""

from __future__ import annotations

import os
import sys
import argparse
import json
from typing import Any, Dict, List

# Ensure project root is on sys.path so imports like `schema_names` work when running as a script.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from schema_names import K


def _get_candidates(out: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    rm = out.get(K.RUN_METADATA, {})
    if not isinstance(rm, dict):
        rm = {}

    structural = rm.get(getattr(K, "OMISSION_CANDIDATES_STRUCTURAL", "omission_candidates_structural"), [])
    inferential = rm.get(getattr(K, "OMISSION_CANDIDATES_INFERENTIAL", "omission_candidates_inferential"), [])
    interpretive = rm.get(getattr(K, "OMISSION_CANDIDATES_INTERPRETIVE", "omission_candidates_interpretive"), [])

    def _as_list(x: Any) -> List[Dict[str, Any]]:
        return x if isinstance(x, list) else []

    return {
        "structural": _as_list(structural),
        "inferential": _as_list(inferential),
        "interpretive": _as_list(interpretive),
    }


def _compact_bundle(cands: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    return {
        "counts": {k: len(v) for k, v in cands.items()},
        "structural": cands["structural"],
        "inferential": cands["inferential"],
        "interpretive": cands["interpretive"],
    }


def _print_readable(cands: Dict[str, List[Dict[str, Any]]], max_items: int) -> None:
    def _p(s: str = "") -> None:
        print(s)

    _p("# Omission Finder — Calibration View (INTERNAL)")
    _p()

    for level in ("structural", "inferential", "interpretive"):
        items = cands[level]
        _p(f"## {level.upper()} — {len(items)} candidates")
        _p("-" * 60)

        if not items:
            _p("(none)")
            _p()
            continue

        shown = 0
        for it in items:
            if not isinstance(it, dict):
                continue
            shown += 1
            if shown > max_items:
                _p(f"... ({len(items) - max_items} more)")
                break

            cid = it.get(getattr(K, "OMISSION_CANDIDATE_ID", "candidate_id"), it.get("candidate_id", "UNKNOWN_ID"))

            # canonical: detector_id + hypothesis_type
            det = it.get(getattr(K, "DETECTOR_ID", "detector_id"), (it.get("finder_debug") or {}).get("detector_id", "unknown"))
            hyp = it.get(getattr(K, "HYPOTHESIS_TYPE", "hypothesis_type"), it.get("operator_type", "unknown"))

            # show hypothesis_type in the "(...)" slot (replaces operator_type)
            op = hyp

            trig = (it.get("trigger_text") or it.get("trigger_summary") or "").strip()
            exp = (it.get("expected_context") or it.get("expected_missing") or "").strip()
            sig = (it.get("absence_signal") or "").strip()
            imp = (it.get("impact_hypothesis") or "").strip()
            eids = it.get("evidence_eids", []) or []
            roles = it.get("evidence_roles", {}) or {}

            _p(f"[{cid}] ({op}) detector={det}")
            if trig:
                _p(f"  trigger: {trig}")
            if exp:
                _p(f"  expected: {exp}")
            if sig:
                _p(f"  signal: {sig}")
            if imp:
                _p(f"  impact: {imp}")
            if eids:
                _p(f"  eids: {eids}")
            if roles:
                _p(f"  roles: {roles}")

            _p()

        _p()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="Emit compact JSON bundle instead of readable view.")
    ap.add_argument("--both", action="store_true", help="Emit readable view, then JSON bundle.")
    ap.add_argument("--max", type=int, default=12, help="Max candidates shown per level in readable view.")
    args = ap.parse_args()

    try:
        out = json.load(sys.stdin)
    except Exception as e:
        print(f"ERROR: could not parse input JSON: {e}", file=sys.stderr)
        return 2

    cands = _get_candidates(out)

    if args.both:
        _print_readable(cands, args.max)
        print(json.dumps(_compact_bundle(cands), indent=2, ensure_ascii=False))
        return 0

    if args.json:
        print(json.dumps(_compact_bundle(cands), indent=2, ensure_ascii=False))
        return 0

    _print_readable(cands, args.max)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
