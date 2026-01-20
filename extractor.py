import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def get_clean_key(key_name):
    key = os.getenv(key_name, "")
    return key.replace("\n", "").replace("\r", "").replace(" ", "").strip()

# We'll use Gemini for the heavy lifting of extraction
client = OpenAI(
    api_key=get_clean_key("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def extract_claims(text):
    print(f"\n🔍 Analyzing: '{text[:50]}...'")
    
    prompt = f"""
    You are a professional fact-checker. Break the following text down into a list of individual, factual claims. 
    Separate the 'Facts' from the 'Opinions' or 'Characterizations'.
    
    Text: "{text}"
    
    Format your response as a numbered list.
    """

    # Using the model name we confirmed earlier
    response = client.chat.completions.create(
        model="gemini-flash-latest", 
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content

if __name__ == "__main__":
    sample_text = "The city's new congestion tax is a desperate grab for cash that will hurt local small businesses."
    claims = extract_claims(sample_text)
    print("\n--- EXTRACTED CLAIMS ---")
    print(claims)