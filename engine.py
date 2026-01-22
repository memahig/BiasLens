
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
    """Analysis Phase: Performs a high-contrast Bias Audit"""
    prompt = f"""
    You are the Aggressive Auditor for BiasLens. 
    Your job is to find what the author is hiding or how they are manipulating the reader.
    Analyze the following evidence for a {depth} report.
    
    CRITERIA:
    - BIAS: Identify framing, loaded language, or cherry-picked data.
    - FALLACY: Identify 'Straw Man', 'Ad Hominem', or 'Appeal to Emotion'.
    - RATING: 1 (Highly Manipulative) to 10 (Purely Objective).

    Return ONLY a JSON object:
    {{
      "audit_results": [
        {{
          "claim": "...",
          "bias_detected": "FALLACY DETECTED: [Name it here]. [Describe the manipulation]",
          "score": 5,
          "notes": "Critique the evidence quality here."
        }}
      ]
    }}
    """
    return call_llm(prompt, evidence_json)