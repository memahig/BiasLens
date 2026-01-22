import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import openai
import streamlit as st


# ─────────────────────────────────────────────────────────────
# Locked enums (Manifesto)
# ─────────────────────────────────────────────────────────────

TAXONOMY = [
    "1. Core Truthfulness",
    "2. Evidence & Attribution Discipline",
    "3. Systematic Omission (Absence of Expected Context)",
    "4. Context & Proportionality (Contextual Proportionality)",
    "5. Reality-Anchored Language Evaluation",
    "6. Logical Structure & Argument Quality",
    "7. Influence / Framing Signals",
    "8. Internal Consistency",
]

CONCERN_LEVELS = ["Low", "Moderate", "Elevated", "High"]  # Information Integrity concern only

VIEW_MODES = ["Overview", "In-Depth"]


# ─────────────────────────────────────────────────────────────
# OpenAI helper
# ─────────────────────────────────────────────────────────────

def _get_client() -> openai.OpenAI:
    return openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def call_llm(system_prompt: str, user_content: str) -> str:
    client = _get_client()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return resp.choices[0].message.content


# ─────────────────────────────────────────────────────────────
# Pass A: Evidence bank + key claims
# ─────────────────────────────────────────────────────────────

PASS_A_SYSTEM_PROMPT = f"""
You are PASS A (Evidence-Indexed Extraction) for BiasLens.

HARD RULES:
- Output JSON ONLY (no markdown).
- NO analysis, NO bias findings, NO intent.
- Evidence quotes MUST be verbatim substrings from the input article text.
- Every key claim MUST cite one or more evidence_eids.

You MUST return this exact schema:

{{
  "evidence_bank": [
    {{
      "eid": "E1",
      "quote": "verbatim quote from article",
      "start_char": 0,
      "end_char": 0,
      "why_relevant": "short explanation of why this quote matters"
    }}
  ],
  "key_claims": [
    {{
      "claim_id": "C1",
      "claim_text": "claim stated in neutral terms",
      "evidence_eids": ["E1"]
    }}
  ]
}}

Constraints:
- Include 8–20 evidence items (prefer fewer if the article is short).
- start_char / end_char must match the quote location in the article text.
- If you cannot locate exact offsets, still output the quote verbatim; the app may repair offsets.
"""


def run_pass_a(article_text: str) -> str:
    """PASS A: Ground truth extraction (Manifesto locked)."""
    return call_llm(PASS_A_SYSTEM_PROMPT.strip(), article_text)


# ─────────────────────────────────────────────────────────────
# Pass B: Constrained audit (findings must reference evidence_eids)
# ─────────────────────────────────────────────────────────────

def _pass_b_system_prompt(view_mode: str) -> str:
    assert view_mode in VIEW_MODES

    in_depth = (view_mode == "In-Depth")

    # In-depth requires argument_map; overview allows it to be omitted or empty.
    arg_map_note = (
        "Argument map is REQUIRED in In-Depth."
        if in_depth
        else "Argument map may be omitted or empty in Overview."
    )

    return f"""
You are PASS B (Constrained Epistemic Audit) for BiasLens.

NON-NEGOTIABLE RULES:
- Output JSON ONLY.
- You are auditing strictly based on Pass A JSON.
- Every finding MUST include evidence_eids that exist in evidence_bank.
- If you cannot cite evidence_eids, DO NOT produce that finding.
- Omission MUST be framed only as "absence of expected context" (never intent).
- Concern levels are Information Integrity concern only: {CONCERN_LEVELS}.
- Categories MUST be one of these exact strings:
{json.dumps(TAXONOMY, indent=2)}

Return this exact schema:

{{
  "audit_results": [
    {{
      "category": "{TAXONOMY[0]}",
      "concern_level": "Low|Moderate|Elevated|High",
      "finding": "concise evidence-based finding",
      "evidence_eids": ["E1"],
      "logic_audit": {{
        "pattern": "e.g., strawman|false balance|appeal to authority|unsupported leap|ambiguity|loaded language|cherry-picking|etc.",
        "mechanism": "how the pattern appears here, tied to evidence",
        "risk": "why it matters"
      }}
    }}
  ],
  "argument_map": {{
    "conclusion": "what the article is arguing overall",
    "premises": ["..."],
    "assumptions": ["..."],
    "counterpoints_missing": ["absence of expected context only"],
    "evidence_eids": ["E1"]
  }},
  "validator_hints": {{
    "notes": ["optional: warn if any claim is hard to support with evidence"]
  }}
}}

Notes:
- {arg_map_note}
- Keep audit_results to 6–18 entries depending on article length.
- No moralizing, no mind-reading, no intent inference.
""".strip()


def run_pass_b(pass_a_json: str, view_mode: str) -> str:
    """PASS B: Constrained audit layer (Manifesto locked)."""
    return call_llm(_pass_b_system_prompt(view_mode), pass_a_json)


# ─────────────────────────────────────────────────────────────
# Validation + repair (app-side enforcement)
# ─────────────────────────────────────────────────────────────

def _safe_json_loads(raw: str) -> Dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception:
        # Return something parseable so the app can show error details
        return {"_parse_error": True, "_raw": raw}


def repair_evidence_offsets(article_text: str, evidence_bank: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Ensure each evidence item has correct start_char/end_char.
    If missing or invalid, try to locate quote in article_text.
    """
    notes: List[str] = []
    repaired: List[Dict[str, Any]] = []

    for ev in evidence_bank or []:
        eid = str(ev.get("eid", "")).strip()
        quote = ev.get("quote", "")

        start = ev.get("start_char", None)
        end = ev.get("end_char", None)

        def valid_offsets() -> bool:
            if not isinstance(start, int) or not isinstance(end, int):
                return False
            if start < 0 or end < 0 or end <= start:
                return False
            if end > len(article_text):
                return False
            return article_text[start:end] == quote

        if not quote or not eid:
            notes.append("Dropped an evidence item missing eid or quote.")
            continue

        if not valid_offsets():
            idx = article_text.find(quote)
            if idx != -1:
                start = idx
                end = idx + len(quote)
                notes.append(f"Repaired offsets for {eid}.")
            else:
                # Keep but mark unknown offsets; still usable for EID linking.
                start = -1
                end = -1
                notes.append(f"Could not locate quote offsets for {eid} (kept quote).")

        repaired.append({
            "eid": eid,
            "quote": quote,
            "start_char": int(start),
            "end_char": int(end),
            "why_relevant": ev.get("why_relevant", ""),
        })

    return repaired, notes


def validate_and_normalize(pass_a: Dict[str, Any], pass_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enforce 'no finding without evidence' by dropping findings whose evidence_eids
    do not exist in the evidence_bank.
    Also normalizes categories and concern levels; drops invalid ones.
    """
    validation_notes: List[str] = []

    evidence_bank = pass_a.get("evidence_bank", []) or []
    eid_set = {str(ev.get("eid", "")).strip() for ev in evidence_bank if ev.get("eid")}

    audit_results = pass_b.get("audit_results", []) or []
    kept_results: List[Dict[str, Any]] = []

    for i, res in enumerate(audit_results, start=1):
        category = str(res.get("category", "")).strip()
        concern = str(res.get("concern_level", "")).strip()
        eids = res.get("evidence_eids", []) or []

        # Category must be exact
        if category not in TAXONOMY:
            validation_notes.append(f"Dropped finding #{i}: invalid category '{category}'.")
            continue

        # Concern must be allowed
        if concern not in CONCERN_LEVELS:
            validation_notes.append(f"Dropped finding #{i}: invalid concern_level '{concern}'.")
            continue

        # Evidence must exist
        eids_norm = [str(e).strip() for e in eids if str(e).strip()]
        if not eids_norm:
            validation_notes.append(f"Dropped finding #{i}: missing evidence_eids.")
            continue

        missing = [e for e in eids_norm if e not in eid_set]
        if missing:
            validation_notes.append(f"Dropped finding #{i}: evidence_eids not found in evidence_bank: {missing}.")
            continue

        kept_results.append({
            "category": category,
            "concern_level": concern,
            "finding": str(res.get("finding", "")).strip(),
            "evidence_eids": eids_norm,
            "logic_audit": res.get("logic_audit", {}),
        })

    # Argument map handling: keep only in-depth, and require evidence eids if present
    argument_map = pass_b.get("argument_map", {}) or {}
    arg_eids = [str(e).strip() for e in (argument_map.get("evidence_eids", []) or []) if str(e).strip()]
    arg_missing = [e for e in arg_eids if e not in eid_set]
    if arg_eids and arg_missing:
        validation_notes.append(f"Argument map had unknown evidence_eids; removing unknown: {arg_missing}.")
        argument_map["evidence_eids"] = [e for e in arg_eids if e in eid_set]

    return {
        "audit_results": kept_results,
        "argument_map": argument_map,
        "validation_notes": validation_notes,
        "validator_hints": pass_b.get("validator_hints", {}),
    }


def build_concern_profile(audit_results: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Produce a nutrition-label style concern profile by taxonomy category.
    Highest concern among findings in that category wins.
    """
    rank = {"Low": 1, "Moderate": 2, "Elevated": 3, "High": 4}
    inv = {1: "🟢 Low", 2: "🟡 Moderate", 3: "🟠 Elevated", 4: "🔴 High"}

    by_cat: Dict[str, int] = {cat: 0 for cat in TAXONOMY}
    for res in audit_results or []:
        cat = res.get("category")
        lvl = res.get("concern_level")
        if cat in by_cat and lvl in rank:
            by_cat[cat] = max(by_cat[cat], rank[lvl])

    return {cat: inv.get(score, "🟢 Low") for cat, score in by_cat.items()}


def generate_general_summary(audit_results: List[Dict[str, Any]]) -> str:
    """
    Mechanical summary (Manifesto): derived from validated results only.
    """
    if not audit_results:
        return "No evidence-cited findings were retained after validation."

    # Take top concerns first
    priority = {"High": 4, "Elevated": 3, "Moderate": 2, "Low": 1}
    sorted_results = sorted(
        audit_results,
        key=lambda r: priority.get(r.get("concern_level", "Low"), 1),
        reverse=True,
    )

    top = sorted_results[:5]
    bullets = []
    for r in top:
        bullets.append(f"- {r['concern_level']} concern in {r['category']}: {r['finding']}")

    return "Top evidence-cited concerns:\n" + "\n".join(bullets)
