#!/usr/bin/env python3
"""
FILE: modules/timeline/timeline_engine.py
VERSION: 0.1
PURPOSE: Timeline extraction + normalization utilities for BiasLens.

Notes:
- Deterministic MVP.
- Extracts timeline-capable events from claims using weekday + clock anchors.
- Normalizes weekday anchors into article-relative day_index (dominant-cluster rebasing).
- Attaches time-only events to the dominant anchored day (MVP heuristic).
- Produces a compact timeline_summary for downstream modules.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

from schema_names import K


# -----------------------------
# Patterns
# -----------------------------

_TIME_PAT = re.compile(
    r"(?i)\b("
    r"(?:mon|tues|wednes|thurs|fri|satur|sun)day"
    r"|jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?"
    r"|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    r")\b"
)

_CLOCK_PAT = re.compile(
    r"(?i)\b(\d{1,2}:\d{2})\s*((?:a\.?m\.?|p\.?m\.?|am|pm))(?=\s*[:\.,]|$)"
)

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


# -----------------------------
# Time parsing
# -----------------------------

def parse_clock_to_minutes(clock_str: str) -> int | None:
    """
    Parse times like "5:32 p.m." / "9:48 pm" / "1:47 a.m." into minutes since midnight.
    Returns None if parsing fails.
    """
    if not clock_str:
        return None

    s = clock_str.strip().lower()
    s = (
        s.replace("a.m.", "am")
        .replace("p.m.", "pm")
        .replace("a.m", "am")
        .replace("p.m", "pm")
    )
    s = " ".join(s.split())

    has_ampm = (" am" in f" {s}" or " pm" in f" {s}" or s.endswith("am") or s.endswith("pm"))
    if not has_ampm:
        m = re.search(r"(\d{1,2}):(\d{2})", s)
        if not m:
            return None
        hh = int(m.group(1))
        mm = int(m.group(2))
        if hh < 0 or hh > 12 or mm < 0 or mm > 59:
            return None
        hh = 0 if hh == 12 else hh
        return hh * 60 + mm

    try:
        dt = datetime.strptime(s, "%I:%M %p")
    except Exception:
        try:
            dt = datetime.strptime(s, "%I:%M%p")
        except Exception:
            return None

    return dt.hour * 60 + dt.minute


# -----------------------------
# Timeline computation
# -----------------------------

def extract_timeline_events(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract timeline-capable events from claims and impose a stable chronological order.
    Deterministic MVP chronology (weekday + clock anchors).
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
            minutes = parse_clock_to_minutes(clock_str) if clock_str else None
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

    # ---------- Phase 2.2: attach time-only events to the first anchored day ----------
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


def build_timeline_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
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

    time_events = sum(1 for e in events if isinstance(e.get(K.TIME_MINUTES), int))

    return {
        "total_events": len(events),
        "anchored_days": len(set(day_indexes)) if day_indexes else 0,
        "time_events": time_events,
        "first_day": min(day_indexes) if day_indexes else None,
        "last_day": max(day_indexes) if day_indexes else None,
    }


def compute_timeline(claims: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convenience wrapper for Pass B.
    Returns: (events, summary)
    """
    events = extract_timeline_events(claims)
    summary = build_timeline_summary(events)
    return events, summary
