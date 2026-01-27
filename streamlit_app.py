
import hmac
import json
import streamlit as st

import scraper
from report_stub import analyze_text_to_report_pack
from validator import validate_output, ValidationError

st.set_page_config(page_title="BiasLens", page_icon="🛡️", layout="wide")


# ─────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────
def check_password() -> bool:
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], st.secrets["APP_PASSWORD"]):
            st.session_state["authenticated"] = True
            del st.session_state["password"]
        else:
            st.session_state["authenticated"] = False

    if st.session_state.get("authenticated", False):
        return True

    st.title("🛡️ BiasLens Login")
    st.text_input("Passkey", type="password", on_change=password_entered, key="password")
    if "authenticated" in st.session_state and not st.session_state["authenticated"]:
        st.error("Incorrect passkey.")
    return False


if not check_password():
    st.stop()


# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")
    st.caption("Foundation mode: Streamlit is a thin shell over the new modular core.")
    st.divider()
    if st.button("Clear Session"):
        st.session_state.clear()
        st.rerun()


# ─────────────────────────────────────────────────────────────
# Main UI
# ─────────────────────────────────────────────────────────────
st.title("🛡️ BiasLens: Epistemic / Information Integrity Audit")

tab1, tab2 = st.tabs(["Link to Article", "Paste Text Manually"])
with tab1:
    url = st.text_input("Article URL", placeholder="https://...")
with tab2:
    manual_text = st.text_area("Paste article text here", height=350)

run = st.button("Run Audit", type="primary")

if run:
    content = ""
    source_title = "manual_text"
    source_url = None

    if url:
        with st.status("🔍 Scraping...", expanded=False) as s:
            result = scraper.scrape_url(url)
            if result.success:
                content = result.text or ""
                source_title = "scraped_url"
                source_url = url
                s.update(label="Scrape complete", state="complete")
            else:
                s.update(label="Scrape failed", state="error")
                st.error(result.text)
                st.stop()
    elif manual_text.strip():
        content = manual_text.strip()
        source_title = "manual_text"
        source_url = None
    else:
        st.warning("Please provide a URL or paste article text.")
        st.stop()

    # NEW CORE: build report pack (stub for now) + validate fail-closed
    with st.status("🏗️ Building report pack + validating...", expanded=False) as s:
        report = analyze_text_to_report_pack(
            text=content,
            source_title=source_title,
            source_url=source_url,
        )
        try:
            validate_output(report)
        except ValidationError as e:
            s.update(label="Validator failed (fail-closed)", state="error")
            st.error("Validator failed. Report pack blocked.")
            st.code(str(e))
            st.stop()

        st.session_state["report"] = report
        s.update(label="Audit complete", state="complete")


# ─────────────────────────────────────────────────────────────
# Render (locked flow)
# Always show one-paragraph summary first,
# then offer Reader In-depth / Scholar In-depth
# ─────────────────────────────────────────────────────────────
report = st.session_state.get("report")
if report:
    st.divider()

    rp = report.get("report_pack", {}) or {}
    summary = rp.get("summary_one_paragraph", "")
    reader = rp.get("reader_interpretation_guide", "")
    findings_items = (rp.get("findings_pack", {}) or {}).get("items", []) or []
    scholar_items = (rp.get("scholar_pack", {}) or {}).get("items", []) or []

    # 1) Always show one-paragraph summary first
    st.subheader("🧾 One-Paragraph Summary")
    st.info(summary or "(missing)")

    # Options: Reader / Scholar
    rtab, stab = st.tabs(["Reader In-depth", "Scholar In-depth"])

    with rtab:
        st.subheader("📣 Reader Interpretation / Public Guide")
        st.write(reader or "(missing)")

        st.divider()
        st.subheader("Findings (evidence-cited)")
        if findings_items:
            for it in findings_items:
                title = f"{it.get('severity','')} — {it.get('finding_id','')}"
                with st.expander(title, expanded=False):
                    st.write(f"**Restated claim:** {it.get('restated_claim','')}")
                    st.write(f"**Finding:** {it.get('finding_text','')}")
                    st.caption(f"Evidence: {it.get('evidence_eids', [])}")
        else:
            st.caption("No findings in this stub run.")

    with stab:
        st.subheader("🎓 Scholar In-depth")
        if scholar_items:
            st.json(scholar_items)
        else:
            st.caption("No scholar items in this stub run (expected in foundation mode).")

    with st.expander("🛠️ Debug: Full Report JSON"):
        st.code(json.dumps(report, indent=2, ensure_ascii=False), language="json")
