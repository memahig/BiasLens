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

# --- 3. INITIALIZE NEW OPENAI CLIENT (THE FINAL FIX) ---
import os
from dotenv import load_dotenv

# Try to load local .env file if it exists
load_dotenv() 

# Priority 1: Check Streamlit Secrets (for Deployment)
# Priority 2: Check Environment Variables (for Local .env)
api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("❌ Key Error: No OpenAI Key found in .env or Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=api_key)

# --- 4. OPTION 1: THE SCRAPER (FIXED) ---
from newspaper import Article, Config  # Ensure Config is imported at the top

st.subheader("Option 1: Analyze via URL")
url = st.text_input("Paste News URL here and press Enter:", key="url_input")

if url:
    try:
        with st.spinner('Scraping article...'):
            config = Config()
            # This mimics a full modern Chrome browser on Windows 10
            config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            config.request_timeout = 20
            # Adding extra headers helps bypass "Forbidden" 403 blocks
            config.headers = {
                'Referer': 'https://www.google.com/',
                'Accept-Language': 'en-US,en;q=0.9',
            }

            article = Article(url, config=config)
            article.download()
            article.parse()
            
            if not article.text:
                st.error("Scraper succeeded but no text was found. The site might be blocking script access.")
            else:
                # 3. Save to session_state
                st.session_state["scraped_text"] = article.text
                st.success(f"Successfully grabbed: {article.title}")
                
    except Exception as e:
        if "429" in str(e):
            st.error("Error 429: The website is blocking us. Try again in 5 minutes or use 'Copy/Paste' instead.")
        else:
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
