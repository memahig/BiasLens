
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