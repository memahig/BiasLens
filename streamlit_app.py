
import streamlit as st
import scraper  # Your existing file
import engine   # Our new file

st.set_page_config(page_title="BiasLens", page_icon="🛡️")

st.title("🛡️ BiasLens: Epistemic Audit")

# 1. Simple Authentication (Password Gate)
if "authenticated" not in st.session_state:
    password = st.text_input("Enter Passkey", type="password")
    if password == st.secrets["APP_PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

# 2. Input Section
url = st.text_input("Paste Article URL")

if st.button("Run Audit"):
    if url:
        # Step A: Scrape
        with st.status("🔍 Scraping Article...") as status:
            text = scraper.get_text(url)
            status.update(label="Text Extracted!", state="complete")
        
        # Step B: Pass A (Evidence)
        with st.status("🏗️ Building Evidence Bank...") as status:
            evidence_json = engine.run_pass_a(text)
            st.session_state.evidence = evidence_json
            status.update(label="Evidence Indexed!", state="complete")
            
        # Display the Evidence Bank (Verification Step)
        st.subheader("📍 Evidence Bank (Ground Truth)")
        st.json(st.session_state.evidence)