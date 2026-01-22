
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

    if content:
        with st.status("🏗️ Building Evidence Bank...") as s:
            raw_response = engine.run_pass_a(content)
            try:
                # Engine returns a string; we must convert to a dictionary
                st.session_state.evidence = json.loads(raw_response)
            except:
                st.session_state.evidence = raw_response
            s.update(label="Evidence Ready", state="complete")

        st.divider()
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("📍 Evidence Bank")
            st.json(st.session_state.evidence)

        with col2:
          # --- THE PRODUCTION REPORT ---
        st.subheader("📝 Final Audit Report")
        
        audit_data = st.session_state.get("audit", {})
        if "audit_results" in audit_data:
            for item in audit_data["audit_results"]:
                # The expander title now shows the Score immediately
                with st.expander(f"[{item['score']}/10] Audit: {item['claim'][:60]}...", expanded=True):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        # We use st.warning to make the bias stand out
                        st.warning(f"**Audit Findings:** {item['bias_detected']}")
                        st.info(f"**Auditor Deep-Dive:** {item['notes']}")
                    with col_b:
                        # A visual metric for the objectivity score
                        st.metric("Objectivity", f"{item['score']}/10")
        else:
            st.error("Audit Logic failed to return results. Check Debug Mode below.")
    else:
        st.warning("Please provide input.")