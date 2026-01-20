# 🛡️ BiasLens v1.0
**An Epistemic Integrity Analysis System**

BiasLens is a modular tool designed to audit news articles and public claims for information integrity signals. Unlike traditional "bias checkers," BiasLens focuses on **Observable Epistemic Properties**—such as missing context, vague sourcing, and logical fallacies—rather than political alignment or moral judgment.

---

## 🚀 Key Features
- **Fact/Opinion Extraction:** Uses Google Gemini to distill raw text into verifiable claims vs. subjective characterizations.
- **Epistemic Auditing:** Employs OpenAI GPT-4o-mini to identify "Omission Bias" and "False Equivalence."
- **Settled Domain Shield:** Non-negotiable guardrails that prevent "bothsidesism" on established scientific or historical consensus.
- **Source Hunter:** Automatically generates clickable Google Search links to verify numbers and vague attributions.
- **4-Level Concern Scale:** Standardized rating from `🟢 Low Concern` to `🔴 High Concern`.

---

## 📂 Project Structure
- `main.py`: The master hub that orchestrates the analysis pipeline.
- `extractor.py`: The Gemini-powered module for claim extraction.
- `cross_examiner.py`: The OpenAI-powered rhetorical and context auditor.
- `.env`: (Private) Stores your secure API keys for Google and OpenAI.

---

## 🛠️ Setup & Installation

### 1. Requirements
- Python 3.10+
- OpenAI & Google Generative AI Python SDKs
- A Mac Terminal (optimized for OSC 8 clickable links)

### 2. Installation
```bash
# Clone or download the files, then install dependencies
pip install -U google-generativeai openai python-dotenv