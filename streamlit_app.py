
import streamlit as st
import scraper  
import engine   
import json

st.set_page_config(page_title="BiasLens", page_icon="🛡️", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Settings")
    analysis_depth = st.radio("Analysis Depth", ["Overview", "In-Depth Audit", "Sentence-by-Sentence"])
    st.divider()
    if st.button("Clear Session"):
        st.session_state.clear()
        st.rerun()

# --- AUTH ---
if "authenticated" not in st.session_state:
    password = st.text_input("Passkey", type="password")
    if password == st.secrets["APP_PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

# --- MAIN UI ---
st.title("🛡️ BiasLens: Epistemic Audit")
tab1, tab2 = st.tabs(["Link to Article", "Paste Text Manually"])
with tab1:
    url = st.text_input("Article URL")
with tab2:
    manual_text = st.text_area("Paste text here", height=400)

if st.button("Run Full Audit", type="primary"):
    content = ""
    if url:
        with st.status("🔍 Scraping...") as s:
            result = scraper.scrape_url(url)
            content = result.text if result.success else ""
            s.update(label="Loaded!", state="complete")
    elif manual_text:
        content = manual_text

    # --- THIS BLOCK MUST BE ALIGNED WITH THE BUTTON LOGIC ---
    if content:
        # STEP 1: Pass A
        with st.status("🏗️ Building Evidence Bank...") as s:
            raw_a = engine.run_pass_a(content)
            st.session_state.evidence = json.loads(raw_a)
            s.update(label="Evidence Ready", state="complete")

        # STEP 2: Pass B
        with st.status("⚖️ Performing Bias Audit...") as s:
            raw_b = engine.run_pass_b(json.dumps(st.session_state.evidence), analysis_depth)
            st.session_state.audit = json.loads(raw_b)
            s.update(label="Audit Complete!", state="complete")

        st.divider()

        # --- THE PRODUCTION REPORT ---
        st.subheader("📝 Final Audit Report")
        
        audit_data = st.session_state.get("audit", {})
        if "audit_results" in audit_data:
            for item in audit_data["audit_results"]:
                with st.expander(f"[{item['score']}/10] Audit: {item['claim'][:60]}...", expanded=True):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.warning(f"**Audit Findings:** {item['bias_detected']}")
                        st.info(f"**Auditor Deep-Dive:** {item['notes']}")
                    with col_b:
                        st.metric("Objectivity", f"{item['score']}/10")
        
        # --- DEBUGGER (Optional) ---
        with st.expander("🛠️ View Raw Evidence"):
            st.json(st.session_state.evidence)
            
    else:
        st.warning("Please provide input.")