
#!/usr/bin/env python3
"""
FILE: schema_names.py
VERSION: 0.3
LAST UPDATED: 2026-02-02
PURPOSE: Central key registry for BiasLens JSON schema fields (string constants).

Notes:
- This module is a contract layer. Keep keys stable; update deliberately.
- Import pattern: from schema_names import K
"""

from __future__ import annotations


class K:
    # --- Top-level ---
    SCHEMA_VERSION = "schema_version"
    RUN_METADATA = "run_metadata"
    EVIDENCE_BANK = "evidence_bank"
    FACTS_LAYER = "facts_layer"
    CLAIM_REGISTRY = "claim_registry"
    HEADLINE_BODY_DELTA = "headline_body_delta"
    METRICS = "metrics"
    DECLARED_LIMITS = "declared_limits"
    REPORT_PACK = "report_pack"

    # --- NEW CORE ANALYSIS MODULES ---
    PREMISE_INDEPENDENCE_ANALYSIS = "premise_independence_analysis"
    REALITY_ALIGNMENT_ANALYSIS = "reality_alignment_analysis"

    # --- premise independence fields ---
    INDEPENDENCE_LEVEL = "independence_level"
    PRIMARY_PREMISES = "primary_premises"
    EXTERNAL_VERIFIABILITY = "external_verifiability"
    AUTHORITY_DEPENDENCE = "authority_dependence"
    CIRCULARITY_FLAG = "circularity_flag"
    ARGUMENT_CRITICAL = "argument_critical"

    # --- reality alignment fields ---
    EPISTEMIC_STABILITY = "epistemic_stability"
    EVIDENCE_CONVERGENCE = "evidence_convergence"
    INDEPENDENCE_OF_SOURCES = "independence_of_sources"
    CONTESTATION_LEVEL = "contestation_level"
    STABILITY_RATIONALE = "stability_rationale"

    # --- run_metadata ---
    MODE = "mode"
    SOURCE_TYPE = "source_type"

    # --- evidence_bank item ---
    EID = "eid"
    QUOTE = "quote"
    START_CHAR = "start_char"
    END_CHAR = "end_char"
    WHY_RELEVANT = "why_relevant"
    SOURCE = "source"

    # --- evidence source ---
    TYPE = "type"
    TITLE = "title"
    URL = "url"

    # --- facts_layer ---
    FACTS = "facts"
    FACT_ID = "fact_id"
    FACT_TEXT = "fact_text"
    CHECKABILITY = "checkability"
    VERDICT = "verdict"
    EVIDENCE_EIDS = "evidence_eids"
    NOTES = "notes"

    # --- claim_registry ---
    CLAIMS = "claims"
    CLAIM_ID = "claim_id"
    CLAIM_TEXT = "claim_text"
    STAKES = "stakes"

    # --- headline_body_delta ---
    PRESENT = "present"
    ITEMS = "items"

    # --- metrics ---
    EVIDENCE_DENSITY = "evidence_density"
    COUNTEREVIDENCE_STATUS = "counterevidence_status"

    # --- evidence_density ---
    NUM_CLAIMS = "num_claims"
    NUM_HIGH_STAKES_CLAIMS = "num_high_stakes_claims"
    NUM_EVIDENCE_ITEMS = "num_evidence_items"
    EVIDENCE_TO_CLAIM_RATIO = "evidence_to_claim_ratio"
    EVIDENCE_TO_HIGH_STAKES_CLAIM_RATIO = "evidence_to_high_stakes_claim_ratio"
    DENSITY_LABEL = "density_label"
    NOTE = "note"

    # --- counterevidence_status ---
    REQUIRED = "required"
    STATUS = "status"
    SEARCH_SCOPE = "search_scope"
    RESULT = "result"

    # --- declared_limits ---
    LIMIT_ID = "limit_id"
    STATEMENT = "statement"

    # --- report_pack ---
    SUMMARY_ONE_PARAGRAPH = "summary_one_paragraph"
    READER_INTERPRETATION_GUIDE = "reader_interpretation_guide"
    FINDINGS_PACK = "findings_pack"
    SCHOLAR_PACK = "scholar_pack"

    # --- findings_pack item ---
    FINDING_ID = "finding_id"
    RESTATED_CLAIM = "restated_claim"
    FINDING_TEXT = "finding_text"

    # --- ratings ---
    RATING = "rating"

    # --- integrity layers ---
    FACT_TABLE_INTEGRITY = "fact_table_integrity"
    CLAIM_EVALUATIONS = "claim_evaluations"
    CLAIM_INTEGRITY = "claim_integrity"
    ARGUMENT_LAYER = "argument_layer"
    ARGUMENTS = "arguments"
    ARGUMENT_INTEGRITY = "argument_integrity"
    ARTICLE_LAYER = "article_layer"
    ARTICLE_INTEGRITY = "article_integrity"
    PRESENTATION_INTEGRITY = "presentation_integrity"

    # integrity object fields
    STARS = "stars"
    LABEL = "label"
    COLOR = "color"
    CONFIDENCE = "confidence"
    RATIONALE_BULLETS = "rationale_bullets"
    HOW_TO_IMPROVE = "how_to_improve"
    MAINTENANCE_NOTES = "maintenance_notes"
    GATING_FLAGS = "gating_flags"

    # presentation_integrity fields
    MODULE_STATUS = "status"
