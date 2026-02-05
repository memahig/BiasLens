

#!/usr/bin/env python3
"""
FILE: reader_phrasebook.py
VERSION: 0.1
LAST UPDATED: 2026-02-04
PURPOSE: Central phrase/templating registry for BiasLens Reader Brain (Reader In-Depth voice).

This module is intentionally "content-only":
- No schema enforcement
- No validator logic
- No upstream writes
- Pure human-language scaffolding used by reader_brain.py

Design goals:
- Plain-language mechanism names
- Structure-based effects (never intent-based)
- Uncertainty-first compatible
- Improvement-oriented (“how to raise the score”)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


# ----------------------------
# Core data model
# ----------------------------

@dataclass(frozen=True)
class MechanismPhrase:
    """
    A single reader-facing mechanism phrase pack.

    Fields:
      - key: stable internal identifier used by reader_brain
      - title: short human label shown in Reader In-Depth
      - what_it_is: 1-2 sentence definition in plain language
      - reader_effect: how this can work on a reader (structure-based)
      - how_to_reduce: practical guidance to reduce concern / raise score
      - watch_for: short bullet-like fragments the reader can recognize
      - optional_closers: alternate closing lines to reduce repetition
    """
    key: str
    title: str
    what_it_is: str
    reader_effect: str
    how_to_reduce: str
    watch_for: List[str]
    optional_closers: List[str]


# ----------------------------
# Severity language (Reader voice)
# ----------------------------

SEVERITY_LEXICON: Dict[str, str] = {
    # Keep these stable; reader_brain can map stars/concern -> these labels.
    "low": "Low concern",
    "moderate": "Moderate concern",
    "elevated": "Elevated concern",
    "high": "High concern",
    "unknown": "Unknown concern (insufficient evidence)",
}


# ----------------------------
# Mechanism registry
# ----------------------------

MECHANISMS: Dict[str, MechanismPhrase] = {
    # --- Presentation / headline mechanics ---
    "headline_body_delta": MechanismPhrase(
        key="headline_body_delta",
        title="Headline escalation vs body qualifiers",
        what_it_is=(
            "The headline sets a strong impression, while the body adds qualifiers, uncertainty, or limits. "
            "Many readers absorb the headline but never fully update on the nuance."
        ),
        reader_effect=(
            "This can leave you with a more extreme takeaway than the article can responsibly support—"
            "even if the finer print is technically present later."
        ),
        how_to_reduce=(
            "Bring key qualifiers into the headline or subhead, match the headline’s strength to the "
            "strongest *verified* body claim, and avoid absolute or inflammatory phrasing when the body is conditional."
        ),
        watch_for=[
            "Headline sounds certain; body says “may,” “could,” “alleged,” or “unclear.”",
            "Strong moral language up top; careful hedging later.",
            "Body focuses on who said it, not what is verified.",
        ],
        optional_closers=[
            "If you only read the headline, your takeaway will likely be stronger than the evidence supports.",
            "A safer reading is to treat the headline as a hook, not a conclusion.",
        ],
    ),
    "reaction_reporting": MechanismPhrase(
        key="reaction_reporting",
        title="Reaction reporting risk (emotional payload transmission)",
        what_it_is=(
            "The piece mainly reports what people said or did in response—quotes, denunciations, praise, outrage—"
            "rather than verifying the underlying claims."
        ),
        reader_effect=(
            "Even if the outlet stays neutral, repeating charged statements can transmit their emotional force, "
            "nudging your interpretation before verification arrives (or without it)."
        ),
        how_to_reduce=(
            "Pair major reactions with verification context: what is confirmed, what isn’t, and what would change the story. "
            "De-emphasize unverified claims and avoid stacking multiple emotional quotes without independent grounding."
        ),
        watch_for=[
            "Lots of quotes; little independent confirmation.",
            "“X slammed Y” style framing dominates.",
            "The strongest lines are attributed, but not tested.",
        ],
        optional_closers=[
            "Treat reactions as information about politics and messaging, not as proof about reality.",
            "Ask: what is verified here, as opposed to merely reported?",
        ],
    ),

    # --- Evidence discipline / epistemic mechanics ---
    "attribution_as_authority": MechanismPhrase(
        key="attribution_as_authority",
        title="Attribution-as-authority (quotes feel like proof)",
        what_it_is=(
            "A claim is presented with a named speaker or source, which can *feel* like evidence even when "
            "it is still only an assertion."
        ),
        reader_effect=(
            "You may walk away believing the claim was established, when the article actually only established "
            "that someone said it."
        ),
        how_to_reduce=(
            "Separate “who said it” from “what is verified.” Add independent corroboration, link to primary evidence, "
            "or clearly label key assertions as unverified."
        ),
        watch_for=[
            "“According to…” appears where verification would normally go.",
            "A quote substitutes for evidence on a factual point.",
            "The story never returns to confirm or falsify the quote.",
        ],
        optional_closers=[
            "A quote can be newsworthy without being reliable evidence.",
            "Credible sourcing helps, but it’s not the same thing as verification.",
        ],
    ),
    "verification_gap": MechanismPhrase(
        key="verification_gap",
        title="Verification gap (checkable facts not checked)",
        what_it_is=(
            "The article relies on factual premises that look checkable, but it doesn’t show verification "
            "or provide enough sourcing to confirm them."
        ),
        reader_effect=(
            "If the premises are wrong—or even just uncertain—the downstream conclusions can become fragile."
        ),
        how_to_reduce=(
            "Cite primary documents, provide numbers and methods, and confirm the key factual predicates "
            "before building larger interpretations on top of them."
        ),
        watch_for=[
            "Strong factual claims without links, documents, or methods.",
            "Key numbers appear with no provenance.",
            "Major conclusions depend on a premise you can’t independently check from the article.",
        ],
        optional_closers=[
            "When premises are uncertain, conclusions should be proportionally cautious.",
            "The responsible stance is: interesting, but not yet established.",
        ],
    ),
    "uncertainty_mismatch": MechanismPhrase(
        key="uncertainty_mismatch",
        title="Uncertainty mismatch (language outruns evidence)",
        what_it_is=(
            "The article uses confident or absolute language while the evidence shown is partial, indirect, or disputed."
        ),
        reader_effect=(
            "This can cause you to over-update—treating a tentative claim as settled—because the tone implies certainty."
        ),
        how_to_reduce=(
            "Downgrade certainty words, quantify uncertainty where possible, and clearly separate what is known, "
            "what is inferred, and what is unknown."
        ),
        watch_for=[
            "Words like “proves,” “always,” “clearly,” “no doubt,” without supporting proof-level evidence.",
            "Certainty in the framing; ambiguity in the sourcing.",
        ],
        optional_closers=[
            "If the evidence is partial, the language should be proportionally modest.",
        ],
    ),

    # --- Reasoning / framing mechanics ---
    "scope_inflation": MechanismPhrase(
        key="scope_inflation",
        title="Scope inflation (small facts → big conclusions)",
        what_it_is=(
            "Specific events, anecdotes, or local facts are used to imply broad general conclusions—"
            "about a whole group, system, or trend—without adequate bridging evidence."
        ),
        reader_effect=(
            "You can be nudged from “this happened” to “this is how things are,” even when the evidence only supports "
            "a narrower claim."
        ),
        how_to_reduce=(
            "Fence claims with scope: where, when, who, how common. Use base rates, broader datasets, or explicitly "
            "label generalizations as hypotheses."
        ),
        watch_for=[
            "Anecdote presented as representative without data.",
            "“This is what they always do” leaps from a single case.",
            "Conclusions about an entire population from a narrow sample.",
        ],
        optional_closers=[
            "Treat broad conclusions as tentative unless the article earns them with breadth.",
        ],
    ),
    "omission_expected_context": MechanismPhrase(
        key="omission_expected_context",
        title="Omission-dependent reasoning (missing expected context)",
        what_it_is=(
            "The argument depends on context you would reasonably expect—comparisons, timelines, base rates, "
            "or counterexamples—but that context is absent."
        ),
        reader_effect=(
            "Without the missing context, one interpretation can look “obvious” when it is actually one of several plausible readings."
        ),
        how_to_reduce=(
            "Add the expected comparisons (or explain why they’re out of scope), include relevant prior cases, "
            "and show what facts would change the conclusion."
        ),
        watch_for=[
            "A pattern is implied but no comparison class is shown.",
            "Claims about uniqueness with no baseline.",
            "No mention of obvious alternative explanations or nearby cases.",
        ],
        optional_closers=[
            "Absence of expected context isn’t proof of wrongdoing—just a reason to hold conclusions more lightly.",
        ],
    ),
    "load_bearing_weak_claim": MechanismPhrase(
        key="load_bearing_weak_claim",
        title="Load-bearing weak claim (one fragile step holds the argument)",
        what_it_is=(
            "A major conclusion depends on a single intermediate claim that is weakly supported, ambiguous, or unverified."
        ),
        reader_effect=(
            "If that one step fails, the whole conclusion can collapse—or shrink dramatically."
        ),
        how_to_reduce=(
            "Strengthen the bridging claim with direct evidence, narrow the conclusion, or present multiple plausible pathways "
            "instead of one brittle chain."
        ),
        watch_for=[
            "A big conclusion with a thin bridge in the middle.",
            "“Therefore” appears after an assumption rather than evidence.",
            "Key causal step is asserted, not demonstrated.",
        ],
        optional_closers=[
            "Mentally test the argument by removing the weak step—see what still stands.",
        ],
    ),

    # --- Language realism / “Reality-Anchored Language Evaluation” ---
    "reality_anchored_language": MechanismPhrase(
        key="reality_anchored_language",
        title="Reality-anchored language drift (description becomes persuasion)",
        what_it_is=(
            "The language leans on loaded adjectives, moralizing labels, or dramatic phrasing that goes beyond what the evidence shows."
        ),
        reader_effect=(
            "This can steer your emotional stance and perceived certainty—even if the factual substrate is thin or mixed."
        ),
        how_to_reduce=(
            "Prefer checkable descriptors over loaded labels. Keep adjectives proportional to demonstrated facts. "
            "If a strong label is used, show the criteria and the evidence that meets it."
        ),
        watch_for=[
            "Heavy adjectives without corresponding evidence density.",
            "Moral condemnation where description would suffice.",
            "Implied motives presented as facts.",
        ],
        optional_closers=[
            "When tone outruns evidence, treat the tone as advocacy—not proof.",
        ],
    ),
}


# ----------------------------
# Utilities
# ----------------------------

def get_mechanism(key: str) -> Optional[MechanismPhrase]:
    """Fetch a mechanism phrase pack by key. Returns None if unknown."""
    return MECHANISMS.get(key)


def list_mechanism_keys() -> List[str]:
    """Stable ordering is not guaranteed; use for debugging/visibility only."""
    return sorted(MECHANISMS.keys())


def severity_label(sev: str) -> str:
    """Map internal severity strings to Reader labels."""
    return SEVERITY_LEXICON.get(sev, SEVERITY_LEXICON["unknown"])
