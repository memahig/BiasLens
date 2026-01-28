
#!/usr/bin/env python3
import json
import streamlit as st

from io_sources import resolve_input_text
from report_stub import analyze_text_to_report_pack
from validator import validate_output, ValidationError

from renderer import render_overview, render_reader_in_depth, render_scholar_in_depth

BUILD_ID = "BUILD_2026-01-27_22-00"

st.set_page_config(page_title="BiasLens", page_icon="🛡️", layout="wide")

st.title("🛡️ BiasLens — Epistemic / Information Integrity")

st.caption(f"Build: {BUILD_ID}")

st.caption("Evidence-indexed, claim-by-claim analysis. Omission is reported only as absence of expected context (never intent).")


with st.sidebar:
    st.header("Input")
    mode = st.radio("Report mode", ["Overview", "Reader In-Depth", "Scholar In-Depth"], index=0)
    show_json = st.checkbox("Show raw JSON pack", value=False)


tab_url, tab_text = st.tabs(["Analyze URL", "Paste Text"])


url = None
raw_text = None

with tab_url:
    url = st.text_input("Article URL", value="", placeholder="https://...")
    go_url = st.button("Analyze URL", use_container_width=True)

with tab_text:
    raw_text = st.text_area("Paste article text", height=250, placeholder="Paste full article text here...")
    go_text = st.button("Analyze pasted text", use_container_width=True)


def _render(pack: dict) -> None:
    # Render three tabs regardless of sidebar selection (better UX)
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


def _run_analysis(url: str | None, text: str | None) -> None:
    try:
        article_text, source_title, source_url = resolve_input_text(url, None, text)
    except Exception as e:
        st.error(f"Input error: {e}")
        return

    with st.spinner("Running BiasLens (Pass A → Pass B → Validator)…"):
        pack = analyze_text_to_report_pack(
            text=article_text,
            source_title=source_title,
            source_url=source_url,
        )

        try:
            validate_output(pack)
        except ValidationError as e:
            st.error("❌ Validator failed (fail-closed).")
            st.code(str(e))
            return

    st.success("✅ Validator passed.")
    _render(pack)


if go_url and url:
    _run_analysis(url=url, text=None)
elif go_url and not url:
    st.warning("Please enter a URL.")
elif go_text and raw_text:
    _run_analysis(url=None, text=raw_text)
elif go_text and not raw_text:
    st.warning("Please paste some text.")
