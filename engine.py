
import openai
import streamlit as st

def call_llm(system_prompt, user_content):
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

def run_pass_a(article_text):
    """Extraction Phase: Builds the Evidence Bank"""
    prompt = """
    You are the Ground Truth Layer of BiasLens. 
    Extract 5-8 verbatim quotes that represent the core pillars of this article.
    Return ONLY a JSON object:
    {
      "evidence_bank": [{"eid": "E1", "quote": "...", "why_relevant": "..."}],
      "key_claims": [{"claim": "...", "evidence_eids": ["E1"]}]
    }
    """
    return call_llm(prompt, article_text)

def run_pass_b(evidence_json, depth):
    """Analysis Phase: Performs the Bias Audit based on the Evidence Bank"""
    prompt = f"""
    You are the Senior Auditor of BiasLens. 
    Review the following Evidence Bank and Claims. 
    Perform a {depth} analysis.
    
    For each claim, identify:
    1. Potential Bias (e.g., Framing, Omission, Loaded Language).
    2. Logical Fallacies.
    3. Epistemic Quality (How well does the evidence support the claim?).

    Return ONLY a JSON object:
    {{
      "audit_results": [
        {{
          "claim": "...",
          "bias_detected": "...",
          "score": 5,
          "notes": "..."
        }}
      ]
    }}
    """
    return call_llm(prompt, evidence_json)