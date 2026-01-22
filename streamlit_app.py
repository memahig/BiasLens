
import streamlit as st
import scraper  
import engine   

st.set_page_config(page_title="BiasLens", page_icon="🛡️")
st.title("🛡️ BiasLens: Epistemic Audit")

# 1. Authentication
if "authenticated" not in st.session_state:
    password = st.text_input("Enter Passkey", type="password")
    if password == st.secrets["APP_PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

# 2. Input Options (The "Body" of the app)
tab1, tab2 = st.tabs(["Link to Article", "Paste Text Manually"])

with tab1:
    url = st.text_input("Article URL")

with tab2:
    manual_text = st.text_area("Paste article text here", height=300)

# 3. Execution Logic
if st.button("Run Audit"):
    article_content = ""
    
    if url:
        with st.status("🔍 Scraping Article...") as status:
            # Match the function name and object in your scraper.py
            result = scraper.scrape_url(url) 
            
            if result.success:
                article_content = result.text
                st.success(f"Successfully scraped: {result.title}")
                status.update(label="Text Extracted!", state="complete")
            else:
                st.error(f"Scraping failed: {result.error}")
                status.stop()
                
    elif manual_text:
        article_content = manual_text
    
    if article_content:
        # Step: Pass A (The Ground Truth Layer)
        with st.status("🏗️ Building Evidence Bank...") as status:
            evidence_json = engine.run_pass_a(article_content)
            st.session_state.evidence = evidence_json
            status.update(label="Evidence Indexed!", state="complete")
            
        st.subheader("📍 Evidence Bank (Ground Truth)")
        st.info("This is the indexed evidence that will be used for the audit.")
        st.json(st.session_state.evidence)
    else:
        st.warning("Please provide a URL or paste some text first.")