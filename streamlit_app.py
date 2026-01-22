
import streamlit as st
import scraper  
import engine   

st.set_page_config(page_title="BiasLens", page_icon="🛡️", layout="wide")

# --- SIDEBAR (RESTORED) ---
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
    manual_text = st.text_area("Paste text here", height=300)

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
            evidence = engine.run_pass_a(content)
            st.session_state.evidence = evidence
            s.update(label="Evidence Ready", state="complete")

        st.divider()

        # --- THE RESTORED REPORT INTERFACE ---
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("📍 Evidence Bank")
            # We keep the raw data here for your reference
            st.json(st.session_state.evidence)

        with col2:
            st.subheader("📝 Final Audit Report")
            
            # This is the "Printing" logic we lost!
            # It loops through the JSON and makes it look like a report.
            if "claims" in st.session_state.evidence:
                for claim in st.session_state.evidence["claims"]:
                    with st.expander(f"Claim: {claim['claim_text'][:60]}...", expanded=True):
                        st.write(f"**The Claim:** {claim['claim_text']}")
                        st.write(f"**Supporting Evidence:**")
                        # Finding the quote that matches the ID
                        for quote in st.session_state.evidence.get("evidence_bank", []):
                            if quote['eid'] in claim.get('evidence_ids', []):
                                st.info(f"\"{quote['quote']}\"")
            else:
                st.write(st.session_state.evidence) # Fallback if structure varies
    else:
        st.warning("Please provide input.")