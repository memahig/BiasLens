import openai
import streamlit as st
import json

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
    """PASS A: GROUND TRUTH EXTRACTION (MANIFESTO LOCK)"""
    prompt = """
    You are the Ground Truth Layer of BiasLens. Build a hard evidence surface.
    Return ONLY JSON:
    {
      "evidence_bank": [{"eid": "E1", "quote": "...", "why_relevant": "..."}],
      "key_claims": [{"claim_id": "C1", "claim_text": "...", "evidence_eids": ["E1"]}]
    }
    Rules: Verbatim quotes only. No analysis.
    """
    return call_llm(prompt, article_text)

def run_pass_b(pass_a_json):
    """PASS B: CONSTRAINED AUDIT LAYER (MANIFESTO LOCK)"""
    prompt = """
    You are the Epistemic Auditor. Audit the Evidence Bank strictly.
    Return ONLY JSON matching this forensic schema:
    {
      "audit_results": [
        {
          "category": "1-8 from Taxonomy",
          "concern_level": "Low/Moderate/Elevated/High concern",
          "finding": "...",
          "evidence_eids": ["E1"],
          "logic_check": "pattern mechanism"
        }
      ],
      "argument_map": {
        "conclusion": "...",
        "premises": ["..."],
        "assumptions": ["..."],
        "counterpoints_missing": ["..."],
        "evidence_eids": ["E1"]
      },
      "general_summary": "Mechanical restatement only."
    }
    """
    return call_llm(prompt, pass_a_json)