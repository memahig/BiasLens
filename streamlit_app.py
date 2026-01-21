import streamlit as st
import openai
from newspaper import Article
import os

# 1. Setup API Key (Pulling from Streamlit Secrets)
if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    # Fallback for local testing (uses your .env.txt on your Mac)
    openai.api_key = os.getenv("OPENAI_API_KEY")

st.title("BiasLens: News Analysis Tool")
st.write("Paste a news URL below to analyze it for bias.")

# 2. URL Input
url = st.text_input("Enter News URL:")

if url:
    try:
        # 3. Scraping the Article
        with st.spinner('Scraping article content...'):
            article = Article(url)
            article.download()
            article.parse()
            text = article.text
        
        st.success("Article successfully scraped!")
        st.subheader(f"Title: {article.title}")

        # 4. AI Analysis
        if st.button("Analyze Bias"):
            with st.spinner('AI is analyzing the text...'):
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert in media bias and political science."},
                        {"role": "user", "content": f"Analyze the following news text for political bias, tone, and framing. Provide a concise summary:\n\n{text[:3000]}"}
                    ]
                )
                analysis = response.choices[0].message.content
                st.write(analysis)

    except Exception as e:
        st.error(f"Error: {e}")