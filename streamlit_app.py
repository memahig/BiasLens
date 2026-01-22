
import json
import hmac
import streamlit as st

import scraper
import engine

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
    view_mode_label = st.radio("Report View", ["Overview", "In-Depth"])
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

    if url:
        with st.status("🔍 Scraping...", expanded=False) as s:
            result = scraper.scrape_url(url)
            if result.success:
                content = result.text
                s.update(label="Scrape complete", state="complete")
            else:
                s.update(label="Scrape failed", state="error")
                st.error(result.text)
    elif manual_text.strip():
        content = manual_text.strip()
    else:
        st.warning("Please provide a URL or paste article text.")
        st.stop()

    # PASS A
    with st.status("🏗️ Pass A: Building Evidence Bank...", expanded=False) as s:
        raw_a = engine.run_pass_a(content)
        pass_a = engine._safe_json_loads(raw_a)

        if pass_a.get("_parse_error"):
            s.update(label="Pass A parse error", state="error")
            st.error("Pass A returned invalid JSON.")
            st.code(pass_a.get("_raw", ""), language="json")
            st.stop()

        # Repair offsets to make evidence inspectable
        repaired_bank, repair_notes = engine.repair_evidence_offsets(content, pass_a.get("evidence_bank", []))
        pass_a["evidence_bank"] = repaired_bank
        pass_a.setdefault("repair_notes", []).extend(repair_notes)

        st.session_state["pass_a"] = pass_a
        s.update(label="Evidence Bank ready", state="complete")

    # PASS B
    with st.status("⚖️ Pass B: Performing Constrained Audit...", expanded=False) as s:
        raw_b = engine.run_pass_b(json.dumps(st.session_state["pass_a"]), view_mode_label)
        pass_b = engine._safe_json_loads(raw_b)

        if pass_b.get("_parse_error"):
            s.update(label="Pass B parse error", state="error")
            st.error("Pass B returned invalid JSON.")
            st.code(pass_b.get("_raw", ""), language="json")
            st.stop()

        st.session_state["pass_b_raw"] = pass_b
        s.update(label="Audit complete (raw)", state="complete")

    # VALIDATE + NORMALIZE
    validated = engine.validate_and_normalize(st.session_state["pass_a"], st.session_state["pass_b_raw"])
    profile = engine.build_concern_profile(validated["audit_results"])
    summary = engine.generate_general_summary(validated["audit_results"])

    st.session_state["validated"] = validated
    st.session_state["concern_profile"] = profile
    st.session_state["general_summary"] = summary

# ─────────────────────────────────────────────────────────────
# Render
# ─────────────────────────────────────────────────────────────

validated = st.session_state.get("validated")
if validated:
    st.divider()
    st.subheader("📌 Information Integrity Profile (Nutrition Label)")

    # Profile display
    for cat, lvl in st.session_state.get("concern_profile", {}).items():
        st.write(f"**{cat}** — {lvl}")

    st.divider()
    st.subheader("🧾 General Summary (Evidence-Cited, Mechanical)")
    st.info(st.session_state.get("general_summary", ""))

    st.divider()

    if view_mode_label == "Overview":
        st.subheader("📝 Overview Findings (Elevated/High only)")
        for res in validated.get("audit_results", []):
            if res["concern_level"] in ("Elevated", "High"):
                st.warning(f"**{res['concern_level']} — {res['category']}**\n\n{res['finding']}\n\nEvidence: {res['evidence_eids']}")
    else:
        st.subheader("🕵️ In-Depth Audit (Expert)")

        col1, col2 = st.columns([1, 1])
        with col1:
            st.write("**Argument Map**")
            st.json(validated.get("argument_map", {}))
        with col2:
            st.write("**Validation Notes**")
            notes = validated.get("validation_notes", [])
            if notes:
                st.warning("\n".join([f"- {n}" for n in notes]))
            else:
                st.success("No validation removals.")

        st.divider()
        st.write("**All Retained Findings (Evidence-Cited)**")

        for res in validated.get("audit_results", []):
            with st.expander(f"{res['concern_level']} — {res['category']}", expanded=False):
                st.write(res["finding"])
                st.caption(f"Evidence: {res['evidence_eids']}")
                if res.get("logic_audit"):
                    st.write("**Logic Audit**")
                    st.json(res["logic_audit"])

    # Debug tools
    with st.expander("🛠️ Debug: Pass A (Evidence Bank)"):
        st.json(st.session_state.get("pass_a", {}))

    with st.expander("🛠️ Debug: Pass B (Raw)"):
        st.json(st.session_state.get("pass_b_raw", {}))
