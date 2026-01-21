import streamlit as st
import openai
from newspaper import Article
import os

# 1. Setup API Key
if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    openai.api_key = os.getenv("OPENAI_API_KEY")

st.title("BiasLens: News Analysis Tool")

# --- SECTION 1: THE SCRAPER (OPTIONAL) ---
st.subheader("Option 1: Analyze via URL")
url = st.text_input("Paste News URL here (Press Enter to scrape):")

scraped_text = ""
if url:
    try:
        with st.spinner('Scraping article...'):
            article = Article(url)
            article.download()
            article.parse()
            scraped_text = article.text
            st.success(f"Successfully grabbed: {article.title}")
    except Exception as e:
        st.error(f"Could not scrape URL: {e}")

st.divider()

# --- SECTION 2: THE MANUAL WINDOW (YOUR ORIGINAL CORE) ---
st.subheader("Option 2: Paste Text Manually")
manual_text = st.text_area("Paste the article text here:", value=scraped_text, height=400)

# --- SECTION 3: THE ANALYSIS ---
if st.button("Analyze for Bias"):
    if not manual_text:
        st.warning("Please paste some text or a URL first!")
    else:
        with st.spinner('AI is analyzing...'):
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert in media bias. Analyze the text for political leaning, tone, and framing."},
                        {"role": "user", "content": manual_text[:4000]}
                    ]
                )
                st.subheader("Analysis Results")
                st.write(response.choices[0].message.content)
            except Exception as e:
                st.error(f"AI Error: {e}")