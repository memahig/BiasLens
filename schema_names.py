#!/usr/bin/env python3
"""
FILE: schema_names.py
VERSION: 0.4
LAST UPDATED: 2026-02-11
PURPOSE: Central key registry for BiasLens JSON schema fields (string constants).

Notes:
- This module is a contract layer. Keep keys stable; update deliberately.
- Import pattern: from schema_names import K
"""

from __future__ import annotations


class K:
    # --- Top-level ---
    SCHEMA_VERSION = "schema_version"

    # 🔒 Schema version discipline (do not edit without deliberate migration)
    # This is the producer version for all emitted report packs.
    SCHEMA_VERSION_CURRENT = "1.0.0"

    RUN_METADATA = "run_metadata"
    EVIDENCE_BANK = "evidence_bank"
    FACTS_LAYER = "facts_layer"
    CLAIM_REGISTRY = "claim_registry"
    HEADLINE_BODY_DELTA = "headline_body_delta"
    SYSTEMATIC_OMISSION = "systematic_omission"
    FINDINGS = "findings"
    METRICS = "metrics"
    DECLARED_LIMITS = "declared_limits"
    REPORT_PACK = "report_pack"


    # --- systematic omission finding fields ---
    OMISSION_ID = "omission_id"
    OMISSION_TYPE = "omission_type"
    TRIGGER_TEXT = "trigger_text"
    EXPECTED_CONTEXT = "expected_context"
    ABSENCE_SIGNAL = "absence_signal"
    IMPACT = "impact"

    # --- NEW CORE ANALYSIS MODULES ---
    PREMISE_INDEPENDENCE_ANALYSIS = "premise_independence_analysis"
    REALITY_ALIGNMENT_ANALYSIS = "reality_alignment_analysis"
    FRAMING_EVIDENCE_ALIGNMENT = "framing_evidence_alignment"

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

    # --- run_metadata (INTERNAL / not user-facing) ---
    OMISSION_CANDIDATES_STRUCTURAL = "omission_candidates_structural"
    OMISSION_CANDIDATES_INFERENTIAL = "omission_candidates_inferential"
    OMISSION_CANDIDATES_INTERPRETIVE = "omission_candidates_interpretive"
    OMISSION_FINDER_NOTES = "omission_finder_notes"

    MODE = "mode"
    SOURCE_TYPE = "source_type"

    # --- omission candidate item (INTERNAL / evaluator input) ---
    OMISSION_CANDIDATE_ID = "candidate_id"
    DETECTOR_ID = "detector_id"
    DETECTOR_LAYER = "detector_layer"  # structural | inferential | interpretive
    HYPOTHESIS_TYPE = "hypothesis_type"
    TRIGGER_SUMMARY = "trigger_summary"
    EXPECTED_MISSING = "expected_missing"
    IMPACT_HYPOTHESIS = "impact_hypothesis"

    # Evidence anchoring for candidates (Option A):
    # - Use K.EVIDENCE_EIDS for all EIDs (trigger + context).
    # - Use K.EVIDENCE_ROLES to label which EID is trigger vs context.
    EVIDENCE_ROLES = "evidence_roles"  # map: eid -> role
    EVID_ROLE_TRIGGER = "trigger"
    EVID_ROLE_CONTEXT = "context"

    MISSING_PARAMETER_TYPES = "missing_parameter_types"

    SCOPE_HINT = "scope_hint"
    SCOPE_LOCAL = "local"
    SCOPE_PARAGRAPH = "paragraph"
    SCOPE_ARTICLE = "article"

    STAKES_HINT = "stakes_hint"
    STAKES_LOW = "low"
    STAKES_MODERATE = "moderate"
    STAKES_ELEVATED = "elevated"
    STAKES_HIGH = "high"

    DETECTOR_CONFIDENCE = "detector_confidence"
    CANDIDATE_NOTES = "candidate_notes"
    EXTRACTED_SLOTS = "extracted_slots"

    # --- standardized missing_parameter_types vocabulary (canonical) ---
    MPT_BASELINE = "baseline"
    MPT_DENOMINATOR = "denominator"
    MPT_COMPARATOR_CLASS = "comparator_class"
    MPT_TIME_WINDOW = "time_window"
    MPT_ABSOLUTE_VALUE = "absolute_value"
    MPT_POPULATION_SCOPE = "population_scope"
    MPT_DEFINITION = "definition"
    MPT_MECHANISM = "mechanism"
    MPT_EVIDENCE_TYPE = "evidence_type"
    MPT_SOURCE_PROVENANCE = "source_provenance"

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

    # --- fact enums (constitutional) ---
    CHECKABILITY_CHECKABLE = "checkable"
    CHECKABILITY_CURRENTLY_UNCHECKABLE = "currently_uncheckable"

    VERDICT_TRUE = "true"
    VERDICT_FALSE = "false"
    VERDICT_MIXED = "mixed"
    VERDICT_UNKNOWN = "unknown"
    VERDICT_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    VERDICT_NOT_FOUND = "not_found"
    VERDICT_UNCHECKABLE = "uncheckable"

    # --- claim_registry ---
    CLAIMS = "claims"
    CLAIM_ID = "claim_id"
    CLAIM_TEXT = "claim_text"
    STAKES = "stakes"

    # --- headline_body_delta ---
    PRESENT = "present"
    ITEMS = "items"
    HEADLINE_TEXT = "headline_text"
    BODY_TEXT = "body_text"
    SOURCE_ID = "source_id"
    QUOTE_VERBATIM = "quote_verbatim"

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

    # WRITE AUTHORITY (new): avoids collision with module execution status
    COUNTEREVIDENCE_RUN_STATUS = "run_status"

    # LEGACY READ-ONLY (do not emit in new code)
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
    fact_verification = "fact_verification"
    CLAIM_EVALUATIONS = "claim_evaluations"
    claim_grounding = "claim_grounding"
    ARGUMENT_LAYER = "argument_layer"
    ARGUMENTS = "arguments"
    ARGUMENT_INTEGRITY = "argument_integrity"
    ARTICLE_LAYER = "article_layer"
    ARTICLE_INTEGRITY = "article_integrity"
    PRESENTATION_INTEGRITY = "presentation_integrity"

    # --- timeline (Pass B / Article Layer) ---
    TIMELINE_EVENTS = "timeline_events"
    TIMELINE_CONSISTENCY = "timeline_consistency"
    TIMELINE_SUMMARY = "timeline_summary"

    # timeline_event fields
    DAY_NAME = "day_name"
    DAY_INDEX = "day_index"
    TIME_ANCHOR = "time_anchor"
    TIME_HAS_MINUTES = "time_has_minutes"
    TIME_MINUTES = "time_minutes"
    EVENT_TEXT = "text"

    # integrity object fields
    SCORE_0_100 = "score_0_100"
    STARS = "stars"
    LABEL = "label"
    COLOR = "color"
    CONFIDENCE = "confidence"

    # epistemic confidence classification (closed vs open world)
    CONFIDENCE_CLASS = "confidence_class"
    CONFIDENCE_CLOSED = "closed_world"
    CONFIDENCE_OPEN = "open_world"

    RATIONALE_BULLETS = "rationale_bullets"
    HOW_TO_IMPROVE = "how_to_improve"
    MAINTENANCE_NOTES = "maintenance_notes"
    GATING_FLAGS = "gating_flags"

    # --- claim evaluation module (Pass B) ---
    CLAIM_EVALUATION_MODULE = "claim_evaluation_module"
    CLAIM_EVALUATION_ITEMS = "items"
    CLAIM_EVAL_ID = "claim_eval_id"
    CLAIM_REF = "claim_ref"
    ISSUE_TYPE = "issue_type"
    SEVERITY = "severity"
    EXPLANATION = "explanation"
    SUPPORT_CLASS = "support_class"

    # --- severity enums (constitutional) ---
    SEV_LOW = "low"
    SEV_MODERATE = "moderate"
    SEV_ELEVATED = "elevated"
    SEV_HIGH = "high"

    # --- module status enums (constitutional) ---
    MODULE_STATUS = "status"
    MODULE_RUN = "run"
    MODULE_NOT_RUN = "not_run"
