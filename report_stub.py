from __future__ import annotations

from typing import Optional

from schema_names import K


def dummy_report_pack() -> dict:
    return {
        K.SCHEMA_VERSION: "1.0",
        K.RUN_METADATA: {K.MODE: "test", K.SOURCE_TYPE: "dummy"},
        K.FACTS_LAYER: {
            K.FACTS: [
                {
                    K.FACT_ID: "F1",
                    K.FACT_TEXT: "This is a dummy fact used to verify validator behavior.",
                    K.CHECKABILITY: "checkable",
                    K.VERDICT: "unknown",
                    K.EVIDENCE_EIDS: ["E1"],
                    K.NOTES: "Dummy run: not actually verified.",
                }
            ]
        },
        K.CLAIM_REGISTRY: {
            K.CLAIMS: [
                {
                    K.CLAIM_ID: "C1",
                    K.CLAIM_TEXT: "The article makes at least one declarative statement.",
                    K.STAKES: "low",
                    K.EVIDENCE_EIDS: ["E1"],
                }
            ]
        },
        K.EVIDENCE_BANK: [
            {
                K.EID: "E1",
                K.QUOTE: "This is a dummy quoted passage to test the evidence requirement.",
                K.START_CHAR: 0,
                K.END_CHAR: 60,
                K.WHY_RELEVANT: "Supports the dummy fact/claim.",
                K.SOURCE: {K.TYPE: "internal", K.TITLE: "dummy", K.URL: None},
            }
        ],
        K.HEADLINE_BODY_DELTA: {K.PRESENT: False, K.ITEMS: []},
        K.METRICS: {
            K.EVIDENCE_DENSITY: {
                K.NUM_CLAIMS: 1,
                K.NUM_HIGH_STAKES_CLAIMS: 0,
                K.NUM_EVIDENCE_ITEMS: 1,
                K.EVIDENCE_TO_CLAIM_RATIO: 1.0,
                K.EVIDENCE_TO_HIGH_STAKES_CLAIM_RATIO: None,
                K.DENSITY_LABEL: "medium",
                K.NOTE: "One claim supported by one quoted passage.",
            },
            K.COUNTEREVIDENCE_STATUS: {
                K.REQUIRED: False,
                K.STATUS: "not_applicable",
                K.SEARCH_SCOPE: "none",
                K.RESULT: "not_applicable",
                K.NOTES: "Dummy run: no refutation requested.",
            },
        },
        K.DECLARED_LIMITS: [
            {K.LIMIT_ID: "L1", K.STATEMENT: "This is a dummy run; no real article was analyzed."}
        ],
        K.REPORT_PACK: {
            K.SUMMARY_ONE_PARAGRAPH: "This is a dummy BiasLens run used to verify system integrity gates.",
            K.READER_INTERPRETATION_GUIDE: "BiasLens is currently running in test mode. No real article has been analyzed.",
            K.FINDINGS_PACK: {
                K.ITEMS: [
                    {
                        K.FINDING_ID: "FP1",
                        K.CLAIM_ID: "C1",
                        K.RESTATED_CLAIM: "The article makes at least one declarative statement.",
                        K.FINDING_TEXT: "The article contains at least one declarative sentence.",
                        K.SEVERITY: "🟢",
                        K.EVIDENCE_EIDS: ["E1"],
                    }
                ]
            },
            K.SCHOLAR_PACK: {K.ITEMS: []},
        },
    }


def analyze_text_to_report_pack(text: str, source_title: str, source_url: Optional[str]) -> dict:
    report = dummy_report_pack()

    snippet = (text or "").strip()
    if len(snippet) > 240:
        snippet = snippet[:240] + "…"

    report[K.RUN_METADATA] = {
        K.MODE: "stub",
        K.SOURCE_TYPE: "url" if source_url else "text",
    }

    quote = snippet if snippet else "No text provided."
    report[K.EVIDENCE_BANK][0][K.QUOTE] = quote
    report[K.EVIDENCE_BANK][0][K.START_CHAR] = 0
    report[K.EVIDENCE_BANK][0][K.END_CHAR] = len(quote)
    report[K.EVIDENCE_BANK][0][K.SOURCE][K.TYPE] = "url" if source_url else "text"
    report[K.EVIDENCE_BANK][0][K.SOURCE][K.TITLE] = source_title
    report[K.EVIDENCE_BANK][0][K.SOURCE][K.URL] = source_url

    report[K.FACTS_LAYER][K.FACTS][0][K.FACT_TEXT] = "An input text was provided for analysis."
    report[K.FACTS_LAYER][K.FACTS][0][K.NOTES] = "Stub mode: no fact-checking performed."
    report[K.CLAIM_REGISTRY][K.CLAIMS][0][K.CLAIM_TEXT] = "The input contains text to analyze."

    report[K.REPORT_PACK][K.SUMMARY_ONE_PARAGRAPH] = (
        "BiasLens ran in stub mode: the input text was ingested, but full Pass A/Pass B extraction "
        "and verification are not wired yet, so substantive factual judgments are marked unknown."
    )
    report[K.REPORT_PACK][K.READER_INTERPRETATION_GUIDE] = (
        "This output is an integrity-safe placeholder: it shows how the system will present evidence, "
        "claims, and findings without inventing facts. Substantive checks will appear once the engine is wired."
    )

    return report
