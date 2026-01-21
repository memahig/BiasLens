import streamlit as st
from openai import OpenAI
from newspaper import Article
import os

# --- 1. APP MEMORY (SESSION STATE) ---
# This ensures the app remembers you are logged in and keeps your text saved
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False
if "scraped_text" not in st.session_state:
    st.session_state["scraped_text"] = ""

# --- 2. PASSWORD GATE ---
def check_password():
    if st.session_state["password_correct"]:
        return True

    # This container makes the login look clean
    placeholder = st.empty()
    with placeholder.container():
        st.write("### 🔒 Security Check")
        pwd_input = st.text_input("Please enter the app password:", type="password")
        if pwd_input:
            if pwd_input == st.secrets.get("APP_PASSWORD"):
                st.session_state["password_correct"] = True
                placeholder.empty() # Remove the password box immediately
                st.rerun()
            else:
                st.error("😕 Password incorrect")
    return False

if not check_password():
    st.stop()

# --- 3. INITIALIZE NEW OPENAI CLIENT ---
# This is the "New Language" that replaces the old openai.ChatCompletion
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY"))

st.title("BiasLens: News Analysis Tool")

# --- 4. OPTION 1: THE SCRAPER ---
st.subheader("Option 1: Analyze via URL")
url = st.text_input("Paste News URL here and press Enter:", key="url_input")

if url:
    try:
        with st.spinner('Scraping article...'):
            article = Article(url)
            article.download()
            article.parse()
            # We save the text to session_state so it survives the next button click
            st.session_state["scraped_text"] = article.text
            st.success(f"Successfully grabbed: {article.title}")
    except Exception as e:
        st.error(f"Could not scrape URL: {e}")

st.divider()

# --- 5. OPTION 2: MANUAL TEXT ---
st.subheader("Option 2: Paste Text Manually")
# value=st.session_state["scraped_text"] pulls in the text from the scraper above
manual_text = st.text_area(
    "Edit or paste the article text here:", 
    value=st.session_state["scraped_text"], 
    height=300
)

# --- 6. THE AI ANALYSIS ---
if st.button("Analyze for Bias"):
    if not manual_text:
        st.warning("No text found! Please paste text or use a URL.")
    else:
        with st.spinner('AI is analyzing...'):
            try:
                # NEW SYNTAX: Using the 'client' object
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert in media bias. Analyze the text for political leaning, tone, and framing."},
                        {"role": "user", "content": manual_text[:4000]} # Limit text to stay within AI limits
                    ]
                )
                st.subheader("Analysis Results")
                # NEW SYNTAX: Accessing result via .content (not brackets)
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"AI Error: {e}")
