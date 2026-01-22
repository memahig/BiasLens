import streamlit as st
import scraper  
import engine   
import json

st.set_page_config(page_title="BiasLens", page_icon="🛡️", layout="wide")

# --- SIDEBAR (AS PER MANIFESTO) ---
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

# --- INPUT ---
st.title("🛡️ BiasLens: Epistemic Audit")
tab1, tab2 = st.tabs(["Link to Article", "Paste Text Manually"])
with tab1:
    url = st.text_input("Article URL")
with tab2:
    manual_text = st.text_area("Paste text here", height=400) # Per Manifesto: height=400

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
        # STEP 1: Pass A (The Data)
        with st.status("🏗️ Building Evidence Bank...") as s:
            # Note: engine.run_pass_a returns a JSON string
            raw_response = engine.run_pass_a(content)
            try:
                st.session_state.evidence = json.loads(raw_response)
            except:
                st.session_state.evidence = raw_response
            s.update(label="Evidence Ready", state="complete")

        st.divider()

        # --- THE RESTORED REPORT INTERFACE (SYNCED TO MANIFESTO) ---
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("📍 Evidence Bank")
            st.json(st.session_state.evidence)

        with col2:
            st.subheader("📝 Final Audit Report")
            
            data = st.session_state.evidence
            
            # Use the keys defined in the Manifesto: 'key_claims' and 'claim'
            if isinstance(data, dict) and "key_claims" in data:
                for claim in data["key_claims"]:
                    with st.expander(f"Claim: {claim['claim'][:60]}...", expanded=True):
                        st.write(f"**The Claim:** {claim['claim']}")
                        st.write(f"**Supporting Evidence:**")
                        
                        # Use the key defined in Manifesto: 'evidence_eids'
                        target_ids = claim.get('evidence_eids', [])
                        
                        # Match the EIDs to the quotes in the bank
                        for quote_item in data.get("evidence_bank", []):
                            if quote_item['eid'] in target_ids:
                                st.info(f"\"{quote_item['quote']}\"")
            else:
                st.warning("Could not render report. Check the raw JSON on the left.")
    else:
        st.warning("Please provide input.")
