
import os
import json
import hmac
from typing import Any, Dict, Optional, List

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# Modular Import: Assumes your scraper file is named scraper.py
try:
    from scraper import scrape_url
except ImportError:
    st.error("Error: 'scraper.py' not found. Ensure it is in the same directory.")

# =========================
# BiasLens — Streamlit App
# =========================

st.set_page_config(page_title="BiasLens", page_icon="🛡️", layout="wide")


# -------------------------
# 0) Session State
# -------------------------
def _init_state():
    defaults = {
        "password_correct": False,
        "article_text": "",
        "report_obj": None,
        "raw_report_json": "",
        "last_run_mode": "overview",
        "last_run_model": "gpt-4o-mini", # Changed to gpt-4o-mini for 2026 cost-efficiency
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


# -------------------------
# 1) Password Gate
# -------------------------
def check_password() -> bool:
    if st.session_state.get("password_correct", False):
        return True

    placeholder = st.empty()
    with placeholder.container():
        st.title("🛡️ BiasLens Login")
        st.caption("Enter the password to access the system.")

        pwd = st.text_input("Password", type="password", key="password_input")
        if pwd:
            stored = st.secrets.get("APP_PASSWORD", "")
            if stored and hmac.compare_digest(pwd, stored):
                st.session_state["password_correct"] = True
                if "password_input" in st.session_state:
                    del st.session_state["password_input"]
                placeholder.empty()
                st.rerun()
            else:
                st.error("Password incorrect.")
    return False


if not check_password():
    st.stop()


# -------------------------
# 2) OpenAI Client
# -------------------------
load_dotenv()
api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("❌ No OpenAI API key found. Add OPENAI_API_KEY to Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=api_key)


# -------------------------
# 3) BiasLens Constants & Taxonomy
# -------------------------
CONCERN_LEVELS = ["🟢 Low", "🟡 Moderate", "🟠 Elevated", "🔴 High"]

ISSUE_TAXONOMY = [
    {
        "tier": "Core truthfulness",
        "items": ["Factual accuracy", "Evidence discipline", "Checkability & sourcing", "Attribution quality"],
    },
    {
        "tier": "Context & proportionality",
        "items": [
            "Systematic omission (absence of expected context)",
            "Statistical distortion",
            "Internal consistency",
            "Reality-Anchored Language Evaluation",
        ],
    },
    {
        "tier": "Framing & influence signals",
        "items": [
            "Rhetorical framing & loaded language",
            "Narrative imbalance / one-sided emphasis",
            "False balance",
            "Call-to-action / persuasion markers",
        ],
    },
]

OUTPUT_SCHEMA_HINT = {
    "information_integrity_profile": {
        "overall_concern": "🟢 Low|🟡 Moderate|🟠 Elevated|🔴 High",
        "one_sentence_summary": "string",
        "top_concerns": [{"label": "string", "concern": "Level", "why_it_matters": "string"}],
    },
    "key_claims": [{"claim_id": "C1", "claim": "string", "claim_type": "string", "support_strength": "string", "notes": "string"}],
    "findings": [{"module": "string", "concern": "Level", "finding": "string", "evidence_snippet": "string", "what_to_check_next": "string"}],
    "absence_of_expected_context": [{"trigger_claim_id": "C1", "expected_context": "string", "why_expected": "string", "confidence": "High|Medium|Low"}],
    "reality_anchored_language_evaluation": [{"phrase": "string", "surface_tone": "string", "reality_anchor": "string", "concern": "Level"}],
    "logic_and_argument_quality": [{"pattern": "string", "where": "string", "why_it_matters": "string", "concern": "Level"}],
    "recommendations": {"reader_questions": ["string"], "verification_steps": ["string"]},
}

SYSTEM_PROMPT = f"""
You are BiasLens, an Epistemic / Information Integrity evaluation system.
Non-negotiable rules:
- Report concern levels as: {", ".join(CONCERN_LEVELS)}.
- Systematic omission must be framed ONLY as "absence of expected context" and NEVER as intent.
- Output MUST be valid JSON only. No markdown. No extra keys.
""".strip()


# -------------------------
# 4) Utility Functions
# -------------------------
def split_text(text: str, max_chars: int) -> List[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        cut = text.rfind("\n\n", start, end)
        if cut == -1 or cut <= start + int(max_chars * 0.5):
            cut = end
        chunks.append(text[start:cut].strip())
        start = cut
    return [c for c in chunks if c]


def summarize_long_text(text: str, model: str) -> str:
    chunks = split_text(text, 9000)
    if len(chunks) == 1:
        return text

    st.info(f"Long article detected. Summarizing {len(chunks)} chunks...")
    chunk_summaries = []
    for ch in chunks:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Summarize for integrity analysis. Keep key claims, actors, and notable wording."},
                {"role": "user", "content": ch},
            ],
        )
        chunk_summaries.append(resp.choices[0].message.content.strip())

    merged = "\n\n".join(chunk_summaries)
    resp2 = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Compress into a single brief <= 12,000 chars. Keep key claims. No opinions."},
            {"role": "user", "content": merged},
        ],
    )
    return resp2.choices[0].message.content.strip()


def biaslens_analyze(article_text: str, report_mode: str, model: str, title: Optional[str] = None) -> Dict[str, Any]:
    user_prompt = f"Mode: {report_mode}\nTitle: {title}\nTaxonomy: {json.dumps(ISSUE_TAXONOMY)}\nSchema: {json.dumps(OUTPUT_SCHEMA_HINT)}\nText: {article_text}"
    
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return json.loads(resp.choices[0].message.content)


# -------------------------
# 5) Main UI
# -------------------------
st.title("🛡️ BiasLens")
st.caption("Epistemic / Information Integrity reports with Overview and In-Depth views.")

with st.sidebar:
    st.subheader("Report Settings")
    view = st.radio("View", ["Overview", "In-Depth"], index=0)
    report_mode = view.lower().replace("-", "_")
    model_choice = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "gpt-4.5-preview"], index=0)

    st.divider()
    if st.button("Clear report / reset", use_container_width=True):
        st.session_state.update({"report_obj": None, "raw_report_json": "", "article_text": ""})
        st.rerun()

tab_input, tab_report, tab_debug = st.tabs(["Input", "Report", "Debug"])

with tab_input:
    url_input = st.text_input("Import from URL")
    if st.button("Scrape & Import"):
        if url_input:
            with st.spinner("Scraping..."):
                res = scrape_url(url_input)
                if res.success:
                    st.session_state["article_text"] = res.text
                    st.success(f"Success: {res.title}")
                else:
                    st.error(res.error)

    article_text = st.text_area("Article Text:", value=st.session_state["article_text"], height=400)
    st.session_state["article_text"] = article_text

    if st.button("Run BiasLens Report", type="primary"):
        if not article_text.strip():
            st.warning("No text found.")
        else:
            try:
                working_text = article_text.strip()
                if len(working_text) > 14000:
                    working_text = summarize_long_text(working_text, model_choice)
                with st.spinner("Analyzing..."):
                    report = biaslens_analyze(working_text, report_mode, model_choice, "Analysis")
                    st.session_state["report_obj"] = report
                    st.session_state["raw_report_json"] = json.dumps(report, indent=2)
                    st.success("Done!")
            except Exception as e:
                st.error(f"Error: {e}")

# Note: The rendering logic in tab_report should follow the keys in OUTPUT_SCHEMA_HINT
with tab_report:
    if st.session_state["report_obj"]:
        report = st.session_state["report_obj"]
        profile = report.get("information_integrity_profile", {})
        st.subheader("Information Integrity Profile")
        st.metric("Overall Concern", profile.get("overall_concern", "N/A"))
        st.write(profile.get("one_sentence_summary", ""))
        
        st.divider()
        st.subheader("Key Findings")
        for f in report.get("findings", []):
            with st.expander(f"{f.get('concern')} — {f.get('module')}"):
                st.write(f.get("finding"))
                if f.get("evidence_snippet"): st.caption(f"Evidence: {f.get('evidence_snippet')}")
    else:
        st.info("Run report in Input tab.")

with tab_debug:
    st.code(st.session_state.get("raw_report_json", "{}"), language="json")