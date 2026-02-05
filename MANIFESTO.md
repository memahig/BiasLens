🛡️ BIASLENS — EPISTEMIC AUDIT SYSTEM  
MANIFESTO / MEMORY ANCHOR  
Last locked: 2026-02-05  

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
• reality alignment  

BiasLens does NOT:
• infer intent  
• assign political motives  
• label authors  
• generate unsupported claims  
• issue uncited findings  
• adjudicate belief systems  
• declare metaphysical truth  

All severity is framed ONLY as:  
→ “Information Integrity Concern”

Never “quality,” “score,” or “grade.”

────────────────────────────────
THREE EPISTEMIC PILLARS (NON-NEGOTIABLE)
────────────────────────────────

BiasLens is built on three load-bearing pillars:

🔒 Evidence Discipline  
No finding without evidence.

🔒 Reasoning Integrity  
Arguments are evaluated for structural soundness, including detection of premise-dependent reasoning.

🔒 Reality Alignment  
Claims are evaluated against independently verifiable external evidence when such evidence is available.

No pillar may be weakened without constituting a system regression.

────────────────────────────────
EPISTEMIC STABILITY DOCTRINE
────────────────────────────────

BiasLens evaluates the epistemic stability of claims based on the strength and convergence of independent evidence.

Some claims achieve foundational stability due to overwhelming, replicated, and convergent evidence.

Other claims remain provisional, contested, interpretive, or currently unresolvable.

BiasLens does not present knowledge as binary when reality is graduated.

Calibrated confidence is mandatory.  
Artificial skepticism is forbidden.  
Artificial certainty is forbidden.

────────────────────────────────
REALITY CONTACT DOCTRINE
────────────────────────────────

BiasLens is a diagnostic epistemic system. Interpretation must never outrun verification.

Before any article-level integrity judgment is produced, the system must attempt direct contact with external reality through structured fact verification. Structural coherence, rhetorical discipline, or analytic elegance may never substitute for verified ground truth.

A claim is load-bearing when the article’s central conclusion would materially weaken if the claim were false, unsupported, or misleading. Load-bearing claims must be explicitly identified and evaluated for evidentiary support before argument or article-level integrity assessments are permitted.

If load-bearing claims depend on facts that are false, contested, insufficiently supported, or currently unverifiable, BiasLens must surface this condition clearly and downgrade epistemic confidence. Unknown is not treated as safe, and unverified core claims prohibit high-integrity ratings.

Analytical completeness without reality contact is treated as a system failure.

MANDATORY EXECUTION ORDER  
Evidence → Facts → Fact Verification → Claims → Load-Bearing Identification → Claim Verification → Argument → Article  

No module may bypass this sequence. Any analysis that emits an article-level assessment without completed load-bearing verification is invalid and must fail closed.

BiasLens is designed to function as an epistemic instrument, not a commentary engine.  
Reality contact precedes interpretive authority.

────────────────────────────────
AUTHORITY AND CONSENSUS
────────────────────────────────

Authority, tradition, consensus, and textual origin are modeled as epistemic signals — not proof.

Consensus is treated as a verifiable social fact while remaining distinct from empirical validation.

BiasLens distinguishes between:

• what a text states  
• how it is interpreted  
• how widely interpretations are shared  
• whether claims are supported by external evidence  

Alignment between these layers increases epistemic confidence.  
Divergence is treated as analytically significant.

Authority is never self-validating.

────────────────────────────────
PREMISE INDEPENDENCE INVARIANT
────────────────────────────────

BiasLens evaluates whether conclusions rely on independently verifiable premises or on premises that must be accepted for the conclusion to hold.

Premise-dependent reasoning structures — including circular validation and self-authenticating authority — must be detected and surfaced at the argument level.

BiasLens maps reasoning structure.  
It does not attack belief.

Civilizational axioms, normative frameworks, and interpretive traditions are not treated as reasoning defects, but their epistemic role must remain visible.

────────────────────────────────
CLAIM DOMAIN DISTINCTION
────────────────────────────────

BiasLens explicitly distinguishes between:

• Empirical claims — testable against external reality  
• Interpretive claims — derived from texts or analytical frameworks  
• Normative claims — value-based or philosophical  

These domains require different epistemic handling and must never be conflated.

Category errors constitute system failure.

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
  quote,
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
5. Reality-Anchored Language Evaluation  
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

OVERVIEW → fast epistemic scan  
IN-DEPTH → forensic audit  

The model proposes.  
The system constrains.  
The evidence governs.

BiasLens is an information integrity instrument — not a commentator.

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
• blurs claim domains  
• treats authority as proof  
• suppresses premise dependence  
• overstates certainty  
• bypasses reality contact  
• emits article judgments without load-bearing verification  

is a SYSTEM REGRESSION.

This file overrides all other instructions.
