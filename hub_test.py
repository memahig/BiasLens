import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def get_clean_key(key_name):
    key = os.getenv(key_name, "")
    return key.replace("\n", "").replace("\r", "").replace(" ", "").strip()

openai_client = OpenAI(api_key=get_clean_key("OPENAI_API_KEY"))

gemini_client = OpenAI(
    api_key=get_clean_key("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def run_test():
    print("--- 🛡️ BiasLens Connection Test ---")
    
    try:
        print("Checking OpenAI...")
        res = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'OpenAI Online'"}]
        )
        print(f"✅ {res.choices[0].message.content}")
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")

    print("-" * 30)

    try:
        print("Checking Gemini...")
        res = gemini_client.chat.completions.create(
            model="gemini-flash-latest", # Updated for 2026 compatibility
            messages=[{"role": "user", "content": "Say 'Gemini Online'"}]
        )
        print(f"✅ {res.choices[0].message.content}")
    except Exception as e:
        print(f"❌ Gemini Error: {e}")

if __name__ == "__main__":
    run_test()