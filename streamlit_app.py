

#!/usr/bin/env python3
"""
FILE: streamlit_app.py
VERSION: 0.4
LAST UPDATED: 2026-02-03
PURPOSE:
Streamlit UI for BiasLens.

Inputs:
- Analyze URL: best-effort scrape/download via io_sources.resolve_input_text()
- Paste Text: bypasses scraping entirely; directly analyzes provided text (recommended during development)

ARCHITECTURE LOCK:
- UI MUST call builders.report_builder.build_report (Pass A → Pass B).
- UI MUST NOT call report_stub/analyze_text_to_report_pack directly.

Fail-closed:
- Always validates the produced report pack; if validation fails, nothing renders as "passed".
"""

from __future__ import annotations

import json
import re
import streamlit as st

from io_sources import resolve_input_text

# 🔒 Authorized execution spine
from builders.report_builder import build_report

from integrity_validator import validate_output, ValidationError
from renderer import render_overview, render_reader_in_depth, render_scholar_in_depth

BUILD_ID = "BUILD_2026-02-03_00-45"


# -----------------------------
# UI config
# -----------------------------
st.set_page_config(page_title="BiasLens", page_icon="🛡️", layout="wide")

st.title("🛡️ BiasLens — Epistemic / Information Integrity")
st.caption(f"Build: {BUILD_ID}")
st.caption(
    "Evidence-indexed, claim-by-claim analysis. Omission is reported only as absence of expected context (never intent)."
)

with st.sidebar:
    st.header("Output")
    show_json = st.checkbox("Show raw JSON pack", value=False)

tab_url, tab_text = st.tabs(["Analyze URL", "Paste Text"])


# -----------------------------
# Helpers
# -----------------------------
_URL_RE = re.compile(r"^\s*https?://", re.IGNORECASE)


def _render(pack: dict) -> None:
    t1, t2, t3 = st.tabs(["Overview", "Reader In-Depth", "Scholar In-Depth"])

    with t1:
        st.markdown(render_overview(pack))

    with t2:
        st.markdown(render_reader_in_depth(pack))

    with t3:
        st.markdown(render_scholar_in_depth(pack))

    if show_json:
        st.divider()
        st.subheader("Raw report pack JSON")
        st.code(json.dumps(pack, indent=2, ensure_ascii=False), language="json")


def _run_report(*, text: str, source_title: str, source_url: str) -> None:
    with st.spinner("Running BiasLens (Pass A → Pass B → Validator)…"):
        pack = build_report(text=text, source_title=source_title, source_url=source_url)

        try:
            validate_output(pack)
        except ValidationError as e:
            st.error("❌ Validator failed (fail-closed).")
            st.code(str(e))
            return

    st.success("✅ Validator passed.")
    _render(pack)


def _run_from_text(text: str) -> None:
    article_text = (text or "").strip()
    if not article_text:
        st.warning("Please paste some article text.")
        return

    # If user pasted a URL into the text box, warn clearly (common confusion).
    if _URL_RE.match(article_text) and len(article_text.split()) == 1:
        st.error(
            "That looks like a URL pasted into the text box. "
            "Use the 'Analyze URL' tab for URLs, or paste the article BODY text here."
        )
        return

    _run_report(text=article_text, source_title="pasted_text", source_url="")


def _run_from_url(url: str) -> None:
    u = (url or "").strip()
    if not u:
        st.warning("Please enter a URL.")
        return

    # URL mode: allow resolve_input_text to do its thing; if blocked, guide user.
    try:
        article_text, source_title, source_url = resolve_input_text(u, None, None)
    except Exception as e:
        st.error(f"Input error: Could not download URL (possibly blocked or requires JS/login).\n\nDetails: {e}")
        st.info(
            "Workaround (recommended right now): open the article in your browser, copy the BODY text, "
            "then use the 'Paste Text' tab."
        )
        return

    _run_report(text=article_text, source_title=source_title, source_url=source_url)


# -----------------------------
# Tab: URL
# -----------------------------
with tab_url:
    url = st.text_input("Article URL", value="", placeholder="https://...")
    go_url = st.button("Analyze URL", use_container_width=True)

    if go_url:
        _run_from_url(url)


# -----------------------------
# Tab: Paste Text
# -----------------------------
with tab_text:
    raw_text = st.text_area(
        "Paste article body text",
        height=300,
        placeholder="Paste the full article text here (not the URL).",
    )
    go_text = st.button("Analyze pasted text", use_container_width=True)

    if go_text:
        _run_from_text(raw_text)
