

#!/usr/bin/env python3
"""
FILE: builders/pass_b.py
PURPOSE: Pass B orchestrator (post-Pass-A) — upgrades/extends a Pass A report pack.

ARCHITECTURE LOCK:
- Pass B MUST take a Pass A output dict and return a dict.
- Pass B MUST NOT re-scrape or re-run Pass A extraction.
- Pass B extends the existing schema output; it does not replace it.

Current behavior:
- Adds optional internal numeric scoring (score_0_100) to integrity objects
  WITHOUT changing stars (uses star-band midpoint to preserve consistency).
- Runs Claim Evaluation Engine and attaches output under claim_registry.claim_evaluations.
- NEW: Builds claim_registry.claim_grounding from claim_evaluations.score_0_100 (stars derived).
"""

from __future__ import annotations
import re

from typing import Any, Dict, List
from datetime import datetime

from schema_names import K
from rating_style import score_to_stars, stars_to_score_midpoint
from modules.claims.claim_evaluator import run_claim_evaluator

# -----------------------------
# Timeline Consistency Sensor (MVP)
# -----------------------------

STATE_MISSING = ("missing", "abduct", "kidnap")
STATE_ALIVE = ("seen", "spotted", "shopping", "called", "spoke", "met")

def _classify_event_state(text: str):
    t = text.lower()

    if any(w in t for w in STATE_MISSING):
        return "missing"

    if any(w in t for w in STATE_ALIVE):
        return "alive"

    return None


def _detect_timeline_conflicts(claims):

    states = []

    for c in claims:
        txt = c.get(K.CLAIM_TEXT, c.get("claim_text", ""))
        state = _classify_event_state(txt)

        if state:
            states.append(state)

    if "missing" in states and "alive" in states:
        return {
            K.MODULE_STATUS: "run",
            "flag": "timeline_conflict_candidate",
            "confidence": "low",
            "note": "Article contains signals suggesting both disappearance and post-disappearance activity. Requires verification."
        }

    return {
        K.MODULE_STATUS: "run",
        "flag": None
    }

# -----------------------------
# Timeline Extractor (MVP v0): time-anchor → ordered events
# -----------------------------

_TIME_PAT = re.compile(
    r"(?i)\b("
    r"(?:mon|tues|wednes|thurs|fri|satur|sun)day"
    r"|jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?"
    r"|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    r")\b"
)

_CLOCK_PAT = re.compile(r"(?i)\b(\d{1,2}:\d{2})\s*((?:a\.?m\.?|p\.?m\.?|am|pm))(?=\s*[:\.,]|$)")
_DAYNAME_PAT = re.compile(r"(?i)\b((?:mon|tues|wednes|thurs|fri|satur|sun)day)\b")

_DAY_TO_NUM = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _parse_clock_to_minutes(clock_str: str):
    """
    MVP: convert 'H:MM' (optionally with am/pm) into minutes since midnight.
    Returns None if parsing fails.
    """
    if not clock_str:
        return None

    s = clock_str.strip().lower()
    # remove dots in a.m./p.m.
    s = s.replace(".", "")
    m = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?", s)
    if not m:
        return None

    hh = int(m.group(1))
    mm = int(m.group(2))
    ap = m.group(3)

    if ap == "pm" and hh != 12:
        hh += 12
    if ap == "am" and hh == 12:
        hh = 0

    return hh * 60 + mm

def _parse_clock_to_minutes(clock_str: str) -> int | None:
    """
    Parse times like "5:32 p.m." / "9:48 pm" / "1:47 a.m." into minutes since midnight.
    Returns None if parsing fails.
    """
    if not clock_str:
        return None

    s = clock_str.strip().lower()
    # normalize punctuation/spacing: "p.m." -> "pm"
    s = s.replace("a.m.", "am").replace("p.m.", "pm").replace("a.m", "am").replace("p.m", "pm")
    s = " ".join(s.split())

    has_ampm = (" am" in f" {s}" or " pm" in f" {s}" or s.endswith("am") or s.endswith("pm"))
    if not has_ampm:
        # MVP: accept HH:MM as "minutes in a 12-hour clock with unknown meridiem"
        # This supports ordering *within a block* but MUST NOT be treated as absolute time.
        m = re.search(r"(\d{1,2}):(\d{2})", s)
        if not m:
            return None
        hh = int(m.group(1))
        mm = int(m.group(2))
        if hh < 0 or hh > 12 or mm < 0 or mm > 59:
            return None
        # Map 12 -> 0 (start of 12-hour cycle)
        hh = 0 if hh == 12 else hh
        return hh * 60 + mm


    try:
        dt = datetime.strptime(s, "%I:%M %p")
    except Exception:
        # also accept "5:32pm" without space
        try:
            dt = datetime.strptime(s, "%I:%M%p")
        except Exception:
            return None

    return dt.hour * 60 + dt.minute

def _extract_timeline_events(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract timeline-capable events from claims and impose a stable chronological order.
    """

    events: List[Dict[str, Any]] = []

    for c in claims:
        txt = (c.get(K.CLAIM_TEXT, c.get("claim_text", "")) or "").strip()
        if not txt:
            continue

        has_day_or_month = bool(_TIME_PAT.search(txt))

        clock = _CLOCK_PAT.search(txt)
        if clock:
            hhmm = (clock.group(1) or "").strip()
            ampm = (clock.group(2) or "").strip()
            clock_str = (hhmm + (" " + ampm if ampm else "")).strip()
        else:
            clock_str = None

        if has_day_or_month or clock_str:
            minutes = _parse_clock_to_minutes(clock_str) if clock_str else None
            mday = _DAYNAME_PAT.search(txt)
            day_name = mday.group(1).lower() if mday else None

            events.append(
                {
                    K.CLAIM_REF: c.get(K.CLAIM_ID, c.get("claim_id", "")),
                    K.DAY_NAME: day_name,
                    K.TIME_ANCHOR: clock_str,
                    K.TIME_HAS_MINUTES: minutes is not None,
                    K.TIME_MINUTES: minutes,
                    K.EVENT_TEXT: txt,
                }
            )

    # ---------- Phase 2: normalize day anchors ----------
    last_abs = None
    week_offset = 0
    known_abs: List[int] = []

    for e in events:
        dn = e.get(K.DAY_NAME)

        if not dn or dn not in _DAY_TO_NUM:
            e[K.DAY_INDEX] = None
            continue

        base = _DAY_TO_NUM[dn]

        if last_abs is None:
            abs_day = base
        else:
            candidate = base + week_offset

            # Detect wrap (Sunday -> Monday)
            if candidate < last_abs - 3:
                week_offset += 7
                candidate = base + week_offset

            abs_day = candidate

        last_abs = abs_day
        e[K.DAY_INDEX] = abs_day
        known_abs.append(abs_day)

    # ---------- Rebase to dominant cluster ----------
    if known_abs:
        from collections import Counter

        mode_day = Counter(known_abs).most_common(1)[0][0]

        for e in events:
            di = e.get(K.DAY_INDEX)
            if di is not None:
                e[K.DAY_INDEX] = di - mode_day

    # ---------- Push earlier stray days to end ----------
    for e in events:
        di = e.get(K.DAY_INDEX)
        if isinstance(di, int) and di < 0:
            e[K.DAY_INDEX] = 10_000 + abs(di)

    # Phase 2.2 (MVP): if we have any anchored day, attach time-only events to the first day
    anchored = [
        e.get(K.DAY_INDEX)
        for e in events
        if isinstance(e.get(K.DAY_INDEX), int) and e.get(K.DAY_INDEX) < 10_000
    ]
    if anchored:
        base_day = min(anchored)
        for e in events:
            if e.get(K.DAY_INDEX) is None and isinstance(e.get(K.TIME_MINUTES), int):
                e[K.DAY_INDEX] = base_day

    # ---------- Stable chronological sort ----------

    def _sort_key(pair):
        i, e = pair
        di = e.get(K.DAY_INDEX)
        tm = e.get(K.TIME_MINUTES)

        return (
            10_000 if di is None else di,
            -1 if tm is None else tm,
            i,
        )

    events = [e for _, e in sorted(list(enumerate(events)), key=_sort_key)]

    return events


def _build_timeline_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    MVP summary so downstream modules never need to scan raw events.
    Deterministic. No heuristics beyond presence checks.
    """

    if not events:
        return {
            "total_events": 0,
            "anchored_days": 0,
            "time_events": 0,
            "first_day": None,
            "last_day": None,
        }

    day_indexes = [
        e.get(K.DAY_INDEX)
        for e in events
        if isinstance(e.get(K.DAY_INDEX), int) and e.get(K.DAY_INDEX) < 10_000
    ]

    time_events = sum(
        1 for e in events if isinstance(e.get(K.TIME_MINUTES), int)
    )

    return {
        "total_events": len(events),
        "anchored_days": len(set(day_indexes)) if day_indexes else 0,
        "time_events": time_events,
        "first_day": min(day_indexes) if day_indexes else None,
        "last_day": max(day_indexes) if day_indexes else None,
    }

# Single optional field name (allowed by integrity_objects)
_SCORE_KEY = "score_0_100"


def _ensure_score_midpoint(integ: Dict[str, Any]) -> None:
    """
    If score_0_100 is missing, set it to a stable midpoint for the current stars.
    Does NOT change stars/label/color.
    """
    if not isinstance(integ, dict):
        return
    if _SCORE_KEY in integ:
        return
    stars = integ.get(K.STARS)
    if not isinstance(stars, int):
        return
    integ[_SCORE_KEY] = stars_to_score_midpoint(stars)


def _build_claim_grounding(*, claim_eval: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a schema-legal integrity object for claim-level integrity.

    Notes:
    - Deterministic
    - Uses score_0_100 -> stars mapping
    - Does NOT claim truth; this is structural-risk scoring only (text signals).
    """
    score = claim_eval.get(_SCORE_KEY, 50)
    try:
        score_int = int(score)
    except Exception:
        score_int = 50
    score_int = max(0, min(100, score_int))

    stars = score_to_stars(score_int)

    # Import here to avoid circular import hazards at module load time
    from enforcers.integrity_objects import STAR_MAP  # locked semantics

    label, color = STAR_MAP[stars]

    items = claim_eval.get(K.ITEMS, [])
    n_items = len(items) if isinstance(items, list) else 0

    rationale: List[str] = [
        "Claim Integrity is computed from deterministic structural signals in Pass B (text-only), not truth verification.",
        f"Claim Evaluation Engine emitted {n_items} issue item(s); score_0_100 summarizes severity-weighted structure risk.",
    ]

    how: List[str] = [
        "Add disambiguating nouns/names when using pronouns (they/it/this).",
        "Avoid absolute terms (always/never) unless you provide strong evidence and scope limits.",
        "When asserting causality, include mechanism + evidence and consider alternative explanations.",
        "Treat motive/intent language as a hypothesis; add direct supporting evidence or rephrase as uncertainty.",
    ]

    return {
        K.STARS: stars,
        K.LABEL: label,
        K.COLOR: color,
        K.CONFIDENCE: "low",  # MVP: text-signal engine; later can rise with retrieval/verification
        K.RATIONALE_BULLETS: rationale,
        K.HOW_TO_IMPROVE: how if stars <= 4 else ["Maintain: keep claims specific, qualified, and evidence-tethered."],
        K.GATING_FLAGS: [],
        _SCORE_KEY: score_int,
    }


def run_pass_b(pass_a_out: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(pass_a_out, dict):
        raise RuntimeError("Pass B contract violation: input must be a dict.")

    out = pass_a_out

    # 1) Attach midpoint scores to existing integrity objects (stable behavior)
    facts_layer = out.get(K.FACTS_LAYER)
    if isinstance(facts_layer, dict):
        integ = facts_layer.get(K.fact_verification)
        if isinstance(integ, dict):
            _ensure_score_midpoint(integ)

    article_layer = out.get(K.ARTICLE_LAYER)
    if isinstance(article_layer, dict):
        integ = article_layer.get(K.ARTICLE_INTEGRITY)
        if isinstance(integ, dict):
            _ensure_score_midpoint(integ)

    # 2) Run Claim Evaluation Engine and attach under claim_registry.claim_evaluations
    claim_module = run_claim_evaluator(out)

    cr = out.get(K.CLAIM_REGISTRY)
    if isinstance(cr, dict):
        cr[K.CLAIM_EVALUATIONS] = claim_module

        # 3) NEW: Claim Integrity object derived from claim_evaluations.score_0_100
        cr[K.claim_grounding] = _build_claim_grounding(claim_eval=claim_module)

    # ---- Timeline consistency (Article Layer) ----
    article_layer = out.get(K.ARTICLE_LAYER)

    if isinstance(article_layer, dict) and isinstance(cr, dict):
        claims = cr.get(K.CLAIMS, [])
        events = _extract_timeline_events(claims)
        article_layer[K.TIMELINE_EVENTS] = events
        article_layer["timeline_summary"] = _build_timeline_summary(events)
        article_layer[K.TIMELINE_CONSISTENCY] = {
            K.MODULE_STATUS: K.MODULE_RUN,
            K.NOTES: [
                "Timeline events extracted using weekday and clock anchors.",
                "Weekday anchors were normalized into an article-relative day_index (dominant-cluster rebasing).",
                "Time-only events were attached to the dominant anchored day (MVP heuristic).",
                "Earlier stray weekday mentions were pushed to the end to preserve the dominant chronology.",
                "This is heuristic chronology, not absolute datetime reconstruction.",
            ],
        }



    return out
