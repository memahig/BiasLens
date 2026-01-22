

🛡️ BIASLENS — EPISTEMIC AUDIT SYSTEM
MANIFESTO / MEMORY ANCHOR
Last locked: 2026-01-21

This document is the authoritative design constitution for BiasLens.
All code, prompts, schemas, and AI behavior MUST conform to this file.

BiasLens is not a “bias detector.”
BiasLens is an EVIDENCE-INDEXED EPISTEMIC AUDIT SYSTEM.

────────────────────────────────
CORE IDENTITY
────────────────────────────────

BiasLens exists to evaluate the INFORMATION INTEGRITY of articles.

It audits:
• factual grounding
• evidence discipline
• reasoning structure
• contextual completeness
• proportionality of language
• influence and framing risks

BiasLens does NOT:
• infer intent
• assign political motives
• label authors
• generate unsupported claims
• issue uncited findings

All severity is framed ONLY as:
→ “Information Integrity Concern”

Never “quality,” “score,” or “grade.”

────────────────────────────────
ARCHITECTURAL LOCK
────────────────────────────────

BiasLens is a TWO-PASS SYSTEM.

It is forbidden to collapse this into a single prompt.

────────────
PASS A — EVIDENCE-INDEXED EXTRACTION
(Ground Truth Layer)
────────────

Purpose:
Build a hard evidence surface BEFORE analysis.

Outputs:

evidence_bank[] = {
  eid,
  quote,                // verbatim article text
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
• All quotes MUST be verbatim.
• All claims MUST reference evidence_eids.
• NO analysis.
• NO bias findings.
• NO speculation.

This layer is the ONLY allowed source of truth.

────────────
PASS B — CONSTRAINED AUDIT LAYER
────────────

Purpose:
Perform epistemic analysis strictly constrained to Pass A.

Hard rules:
• EVERY finding MUST reference evidence_eids.
• If no supporting quote exists → the finding is forbidden.
• Uncertain cases → mark “Unclear” + what_to_check_next.
• App-side validator removes uncited findings.

All analytic modules consume ONLY Pass A outputs.

────────────────────────────────
FINDING TYPES (LOCKED TAXONOMY)
────────────────────────────────

BiasLens audits the following categories only:

1. Core Truthfulness
2. Evidence & Attribution Discipline
3. Systematic Omission
   → framed ONLY as “absence of expected context”
4. Context & Proportionality
   (internal name: Contextual Proportionality)
5. Reality-Anchored Language Evaluation
   (public-facing name)
6. Logical Structure & Argument Quality
7. Influence / Framing Signals
8. Internal Consistency

Omission is NEVER framed as intent, motive, or deception.

────────────────────────────────
EVIDENCE ENFORCEMENT
────────────────────────────────

Every analytic object must include:

• evidence_eids[]
• optional evidence_quote
• optional evidence_location

Forbidden:
• free-floating claims
• uncited logic findings
• uncited summaries
• analyst intuition

“No finding without evidence” is the highest system law.

────────────────────────────────
REPORT SYSTEM (TWO VIEWS, ONE DATASET)
────────────────────────────────

BiasLens always generates ONE structured audit dataset.

It is rendered into TWO reports.

────────────
OVERVIEW REPORT (Public)
────────────

Purpose:
Fast epistemic risk scan.

Contains:
• Overall Information Integrity concern profile
• Highest-risk findings only
• Short evidence-backed explanations
• No deep logic maps

Think:
“nutrition label + executive summary”

────────────
IN-DEPTH REPORT (Expert)
────────────

Purpose:
Forensic epistemic audit.

Adds:

ARGUMENT MAP
argument_map[] = {
  conclusion,
  premises[],
  assumptions[],
  counterpoints_missing[],
  evidence_eids[]
}

LOGIC AUDITS
logic_audits[] = {
  pattern,
  mechanism,
  risk,
  concern,
  evidence_eids[]
}

Includes:
• full findings
• full evidence links
• instance-level logic audits
• validation notes

Think:
“inspectable epistemic model”

────────────────────────────────
GENERAL SUMMARY RULE
────────────────────────────────

The General Summary is NOT free-form.

It is mechanically generated from:
• highest-concern findings
• argument map conclusions
• repeated risk patterns
• validator output

Rule:
The summary may ONLY restate supported findings.
No new claims. No new analysis.

────────────────────────────────
SEVERITY SCALE (LOCKED)
────────────────────────────────

🟢 Low concern  
🟡 Moderate concern  
🟠 Elevated concern  
🔴 High concern  

Scale always means:
→ “Information Integrity Concern Level”

Never quality, reliability, or intent.

────────────────────────────────
DESIGN PHILOSOPHY
────────────────────────────────

BiasLens is designed to transition from:

“LLM writes a bias report”

to:

“System builds an evidence-indexed epistemic model and renders views.”

The model proposes.
The system constrains.
The evidence governs.

BiasLens is an information integrity instrument, not a commentator.

────────────────────────────────
DEVELOPER WARNING
────────────────────────────────

Any code or prompt that:
• skips Pass A
• allows uncited findings
• collapses reports into one view
• infers intent
• weakens omission handling
• removes evidence IDs

is a SYSTEM REGRESSION.

This file overrides all other instructions.
