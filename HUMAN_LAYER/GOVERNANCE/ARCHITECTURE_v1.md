# 🛡️ BiasLens — ARCHITECTURE_LOCK_2026-01-21.md
Status: Architecture Freeze  
Date Locked: January 21, 2026  
System: BiasLens Epistemic / Information Integrity Audit

---
Authority Clarification

Subordinate to the BiasLens Constitution.
Where conflict exists, the Constitution prevails.

## 📌 Purpose of This Document

This file marks the formal transition of BiasLens from an LLM-driven “bias report generator” into an evidence-indexed epistemic audit system.

From this point forward, BiasLens is governed by a locked architecture, not by evolving prompts.

Any future development must conform to this design or explicitly declare a new version lock.

---

## 🧠 System Identity (Locked)

BiasLens is not a bias detector.

BiasLens is an:

Evidence-Indexed Epistemic / Information Integrity Audit System

It evaluates:
- factual grounding  
- evidence discipline  
- reasoning structure  
- contextual completeness  
- proportionality of language  
- influence and framing risks  

It does not:
- infer intent  
- assign political motives  
- label authors  
- generate unsupported claims  

All severity is framed only as:

Information Integrity Concern

Never quality, trustworthiness, or intent.

---

## 🏗️ Core Architecture (Locked)

BiasLens is a two-pass system.  
Collapsing this into a single prompt or single step is a system regression.

### PASS A — Evidence-Indexed Extraction  
(Ground Truth Layer)

Purpose:  
Build a hard evidence surface before any analysis.

Outputs:

evidence_bank[] = {
  eid,
  quote (verbatim),
  start_char,
  end_char,
  why_relevant
}

key_claims[] = {
  claim_id,
  claim_text,
  evidence_eids[]
}

Rules:
- Quotes must be verbatim substrings.
- Claims must reference evidence IDs.
- No analysis, no bias findings, no speculation.

This is the only allowed source of truth.

---

### PASS B — Constrained Audit Layer

Purpose:  
Perform epistemic analysis strictly constrained to Pass A outputs.

Hard rules:
- No finding without evidence_eids.
- Evidence IDs must exist in the evidence bank.
- Omission is framed only as absence of expected context, never intent.
- Uncertain cases → “Unclear” + what_to_check_next.

All analytic modules consume Pass A JSON only.

---

## 📚 Locked Taxonomy

1. Core Truthfulness  
2. Evidence & Attribution Discipline  
3. Systematic Omission (absence of expected context)  
4. Context & Proportionality (Contextual Proportionality)  
5. Reality-Anchored Language Evaluation  
6. Logical Structure & Argument Quality  
7. Influence / Framing Signals  
8. Internal Consistency  

No additional categories without a new architecture lock.

---

## ⚖️ Evidence Enforcement (System Law)

- Every finding must include valid evidence_eids.
- App-side validation removes uncited or invalid findings.
- Categories and concern levels are schema-locked.
- General summaries are mechanically derived from validated findings.

“No finding without evidence” is the highest system constraint.

---

## 📊 Report System (Locked)

BiasLens always produces one structured audit dataset.

It is rendered into two views:

### Overview Report (Public)
- Information Integrity concern profile
- Highest-risk findings only
- Evidence-backed summaries
- No deep logic graphs

Purpose: rapid epistemic risk scan.

---

### In-Depth Report (Expert)
Adds:
- Argument Map
- Instance-level logic audits
- Full retained findings
- Validation notes

Purpose: forensic epistemic inspection.

---

## 📈 Severity Scale (Locked)

🟢 Low concern  
🟡 Moderate concern  
🟠 Elevated concern  
🔴 High concern  

Scale always means:

Information Integrity Concern Level

---

## 🧩 Design Philosophy (Locked)

BiasLens has transitioned from:

“LLM writes a bias report”

to:

“System builds an evidence-indexed epistemic model and renders views.”

The model proposes.  
The system constrains.  
The evidence governs.

BiasLens is an information integrity instrument, not a commentator.

---

## 🚨 Regression Definition

Any system that:

- skips Pass A  
- allows uncited findings  
- merges Pass A and Pass B  
- infers intent  
- weakens omission handling  
- allows schema drift  
- removes validator enforcement  

is no longer BiasLens v0 architecture.

This document overrides prompts, refactors, and agent behavior.

---

## ✅ Architecture Status

As of 2026-01-21:

- Two-pass pipeline implemented  
- Evidence repair + validation active  
- Taxonomy locked  
- Concern synthesis active  
- Dual-report rendering active  
- Manifesto codified in system behavior  

This marks BiasLens v0 — Architecture Complete.
