import streamlit as st
import openai

# 1. Setup Page Title
st.set_page_config(page_title="BiasLens", page_icon="🛡️")

st.title("🛡️ BIASLENS: Epistemic Integrity System")
st.write("Analyze articles for bias and hidden context using AI.")

# 2. Get the API Key from Streamlit Secrets
# This matches the name you put in the "Secrets" box
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
except:
    st.error("OpenAI API Key not found. Please check your Streamlit Secrets.")

# 3. The User Interface
text_to_scan = st.text_area("Paste your article below:", height=300)

if st.button("Start Audit"):
    if not text_to_scan.strip():
        st.warning("Please paste some text first!")
    else:
        with st.spinner("Analyzing claims and checking context..."):
            try:
                # Use OpenAI to do the work
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a bias-detection expert. Extract key claims and audit them for integrity, identifying facts vs opinions."},
                        {"role": "user", "content": text_to_scan}
                    ]
                )
                
                report = response.choices[0].message.content
                
                st.subheader("📢 FINAL BIASLENS INTELLIGENCE REPORT")
                st.markdown(report)
                
            except Exception as e:
                st.error(f"An error occurred: {e}")