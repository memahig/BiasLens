#!/usr/bin/env python3
"""
FILE: modules/timeline/timeline_engine.py
VERSION: 0.2
LAST UPDATED: 2026-02-07
PURPOSE: Timeline extraction + normalization utilities for BiasLens.

Notes:
- Deterministic MVP.
- Extracts timeline-capable events from claims using weekday + clock anchors.
- Normalizes weekday anchors into article-relative day_index (dominant-cluster rebasing).
- Attaches time-only events to the dominant anchored day (MVP heuristic; deterministic).
- Produces a compact timeline_summary for downstream modules.
- Phase 4 (NEW): Chronology Intelligence — deterministic timeline coherence signals ONLY.
    - Detect temporal gaps
    - Detect compressed sequences
    - Detect ambiguous chronology
    - Emit deterministic signals only
    - ZERO heuristics that guess reality
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
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
# Phase 4 thresholds (deterministic constants)
# -----------------------------
# These are NOT "reality guesses" — they are purely mechanical thresholds
# used to describe *story chronology representation* within the article text.
GAP_MINUTES_LARGE = 180          # 3 hours
COMPRESS_MAX_DELTA_MINUTES = 3   # 3 minutes
COMPRESS_CLUSTER_WINDOW = 10     # 10 minutes (rolling cluster window)
MAX_DAY_SPAN_FOR_MISSING_DAY_CHECK = 14  # avoid weird spans; still deterministic


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
# Timeline computation (Phases 1–3)
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


# -----------------------------
# Phase 4: Chronology Intelligence (deterministic signals only)
# -----------------------------

def build_timeline_consistency(
    events: List[Dict[str, Any]],
    summary: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute deterministic timeline coherence signals.

    IMPORTANT:
    - This does NOT attempt to reconstruct absolute datetimes.
    - This does NOT infer what "really happened".
    - It ONLY describes properties of the article-relative timeline representation.

    Output is intended for downstream consumers:
    - Presentation Integrity (timeline coherence vs framing)
    - Reader layer (chronology clarity paragraph)
    """
    out: Dict[str, Any] = {
        K.MODULE_STATUS: K.MODULE_RUN,
        "flags": [],
        "stats": {},
        "notes": [
            "Deterministic chronology signals computed from article-relative day_index + time_minutes only.",
            "No absolute datetime reconstruction. No inference about real-world timing beyond anchors present in text.",
        ],
    }

    # Collect usable events: day_index in anchored range and time_minutes present
    usable: List[Dict[str, Any]] = []
    for e in events:
        di = e.get(K.DAY_INDEX)
        tm = e.get(K.TIME_MINUTES)
        if isinstance(di, int) and di < 10_000 and isinstance(tm, int):
            usable.append(e)

    # Basic counts
    total_events = int(summary.get("total_events") or 0)
    time_events = int(summary.get("time_events") or 0)
    anchored_days = int(summary.get("anchored_days") or 0)

    out["stats"]["total_events"] = total_events
    out["stats"]["time_events"] = time_events
    out["stats"]["anchored_days"] = anchored_days
    out["stats"]["usable_time_anchored_events"] = len(usable)

    flags: List[str] = []

    # If there's almost nothing to evaluate, state that deterministically
    if len(usable) < 2:
        flags.append("insufficient_time_anchors_for_gap_or_compression")
        out["stats"]["max_gap_minutes"] = None
        out["stats"]["num_large_gaps"] = 0
        out["stats"]["num_compressed_pairs"] = 0
        out["stats"]["num_compressed_clusters"] = 0
        out["stats"]["num_duplicate_timestamps"] = 0
        out["flags"] = flags
        return out

    # Group by day
    by_day: Dict[int, List[int]] = defaultdict(list)
    by_day_pairs: Dict[int, List[Tuple[int, Dict[str, Any]]]] = defaultdict(list)
    for e in usable:
        di = int(e[K.DAY_INDEX])
        tm = int(e[K.TIME_MINUTES])
        by_day[di].append(tm)
        by_day_pairs[di].append((tm, e))

    # Missing day indices in the anchored window (deterministic)
    first_day = summary.get("first_day")
    last_day = summary.get("last_day")
    missing_days: List[int] = []
    if isinstance(first_day, int) and isinstance(last_day, int):
        span = last_day - first_day
        if 0 <= span <= MAX_DAY_SPAN_FOR_MISSING_DAY_CHECK:
            present = set(int(d) for d in by_day.keys())
            for d in range(first_day, last_day + 1):
                if d not in present:
                    missing_days.append(d)
            if missing_days:
                flags.append("missing_day_indices_in_story_window")
        else:
            # Still deterministic: we are explicit that we did not compute this check.
            flags.append("missing_day_check_skipped_due_to_large_day_span")

    out["stats"]["missing_day_indices"] = missing_days

    # Within-day gaps + compression + duplicates
    max_gap = 0
    num_large_gaps = 0
    num_compressed_pairs = 0
    num_duplicate_timestamps = 0
    compressed_clusters = 0

    for di, times in by_day.items():
        t_sorted = sorted(times)
        if len(t_sorted) < 2:
            continue

        # Duplicate timestamps
        for i in range(1, len(t_sorted)):
            if t_sorted[i] == t_sorted[i - 1]:
                num_duplicate_timestamps += 1

        # Gaps + compressed pairs
        for i in range(1, len(t_sorted)):
            delta = t_sorted[i] - t_sorted[i - 1]
            if delta > max_gap:
                max_gap = delta
            if delta >= GAP_MINUTES_LARGE:
                num_large_gaps += 1
            if 0 <= delta <= COMPRESS_MAX_DELTA_MINUTES:
                num_compressed_pairs += 1

        # Compressed clusters (rolling window)
        # Count clusters where >=3 events fall within COMPRESS_CLUSTER_WINDOW minutes.
        # Deterministic algorithm: two-pointer window size.
        lo = 0
        for hi in range(len(t_sorted)):
            while t_sorted[hi] - t_sorted[lo] > COMPRESS_CLUSTER_WINDOW:
                lo += 1
            window_n = hi - lo + 1
            if window_n >= 3:
                compressed_clusters += 1
                # move lo forward to avoid counting the same dense run too many times
                lo += 1

    out["stats"]["max_gap_minutes"] = int(max_gap) if max_gap > 0 else 0
    out["stats"]["num_large_gaps"] = int(num_large_gaps)
    out["stats"]["num_compressed_pairs"] = int(num_compressed_pairs)
    out["stats"]["num_compressed_clusters"] = int(compressed_clusters)
    out["stats"]["num_duplicate_timestamps"] = int(num_duplicate_timestamps)

    # Flags from computed stats (deterministic)
    if num_large_gaps > 0:
        flags.append("large_time_gaps_present")
    if num_compressed_pairs > 0 or compressed_clusters > 0:
        flags.append("compressed_time_sequences_present")
    if num_duplicate_timestamps > 0:
        flags.append("duplicate_time_anchors_present")

    # Ambiguity: many events lack time_minutes even though timeline_events exists
    # (deterministic ratio check; does not assume anything about reality)
    if total_events > 0:
        no_time = max(0, total_events - time_events)
        out["stats"]["events_without_time_minutes"] = int(no_time)
        out["stats"]["pct_events_without_time_minutes"] = float(no_time) / float(total_events)
        if float(no_time) / float(total_events) >= 0.60 and total_events >= 5:
            flags.append("many_events_lack_time_minutes")
    else:
        out["stats"]["events_without_time_minutes"] = 0
        out["stats"]["pct_events_without_time_minutes"] = 0.0

    out["flags"] = flags
    return out


# -----------------------------
# Public wrappers
# -----------------------------

def compute_timeline(claims: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convenience wrapper for Pass B.
    Returns: (events, summary)
    """
    events = extract_timeline_events(claims)
    summary = build_timeline_summary(events)
    return events, summary


def compute_timeline_with_consistency(
    claims: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    """
    Phase 4-enabled convenience wrapper for Pass B.
    Returns: (events, summary, timeline_consistency)
    """
    events = extract_timeline_events(claims)
    summary = build_timeline_summary(events)
    consistency = build_timeline_consistency(events, summary)
    return events, summary, consistency
