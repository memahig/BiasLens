
import streamlit as st
import scraper
import engine
import json

# ... (Auth logic remains the same) ...

st.title("🛡️ BiasLens: Epistemic Audit")
view_mode = st.radio("Report Depth", ["Overview Report", "In-Depth (Expert)"])

url = st.text_input("Article URL")

if st.button("Run Forensic Audit", type="primary"):
    if url:
        with st.status("🏗️ Executing Manifesto Protocol...") as s:
            result = scraper.scrape_url(url)
            raw_a = engine.run_pass_a(result.text)
            st.session_state.evidence = json.loads(raw_a)
            raw_b = engine.run_pass_b(raw_a)
            st.session_state.audit = json.loads(raw_b)
            s.update(label="Audit Complete", state="complete")

    audit = st.session_state.get("audit", {})
    
    if view_mode == "Overview Report":
        st.subheader("📝 Public Overview")
        st.info(audit.get("general_summary"))
        # Render high-concern findings only
        for res in audit.get("audit_results", []):
            if "High" in res['concern_level'] or "Elevated" in res['concern_level']:
                st.warning(f"**{res['category']}:** {res['finding']}")

    else:
        st.subheader("🕵️ Forensic Expert Audit")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Argument Map**")
            arg = audit.get("argument_map", {})
            st.json(arg)
        with col2:
            st.write("**Logic Audits**")
            for res in audit.get("audit_results", []):
                with st.expander(f"{res['category']} — {res['concern_level']}"):
                    st.write(res['finding'])
                    st.caption(f"Evidence: {res['evidence_eids']}")