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
    SEVERITY = "severity"
