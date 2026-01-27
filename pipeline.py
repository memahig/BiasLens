#!/usr/bin/env python3
"""
BiasLens Pipeline (local runner)

Supports:
  - python3 pipeline.py                       (runs integrity self-test / dummy pack)
  - python3 pipeline.py --url "https://..."   (scrape article text then run)
  - python3 pipeline.py --text "..."          (analyze provided text then run)
  - python3 pipeline.py --file path.txt       (analyze text file then run)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Optional

from validator import validate_report_pack
from schema_names import K



def _validate(report: dict) -> None:
    eids = [e.get(K.EID) for e in report.get(K.EVIDENCE_BANK, []) if e.get(K.EID)]
    validate_report_pack(report, eids)



# -----------------------------
# Optional scraper integration
# -----------------------------
@dataclass
class ScrapeResult:
    text: str
    success: bool


def _try_scrape(url: str) -> ScrapeResult:
    """
    Uses scraper.py if present. Fails safely with a user-readable message.
    """
    try:
        import scraper  # type: ignore

        if hasattr(scraper, "scrape_url"):
            res = scraper.scrape_url(url)  # expected to return ScrapeResult-like object
            text = getattr(res, "text", "")
            success = bool(getattr(res, "success", False))
            return ScrapeResult(text=text, success=success)

        return ScrapeResult(
            text="scraper.py is present but does not define scrape_url(url).",
            success=False,
        )
    except Exception as e:
        return ScrapeResult(text=f"Scrape exception: {e}", success=False)


# -----------------------------
# Core pipeline stubs (today)
# -----------------------------
def _dummy_report_pack() -> dict:
    """
    Minimal report pack that should PASS the validator.
    This is your integrity gate test.
    """
    return {
        "schema_version": "1.0",
        "run_metadata": {
            "mode": "test",
            "source_type": "dummy",
        },
        "facts_layer": {
            "facts": [
                {
                    "fact_id": "F1",
                    "fact_text": "This is a dummy fact used to verify validator behavior.",
                    "checkability": "checkable",
                    "verdict": "unknown",
                    "evidence_eids": ["E1"],
                    "notes": "Dummy run: not actually verified.",
                }
            ]
        },
        "claim_registry": {
            "claims": [
                {
                    "claim_id": "C1",
                    "claim_text": "The article makes at least one declarative statement.",
                    "stakes": "low",
                    "evidence_eids": ["E1"],
                }
            ]
        },
        "evidence_bank": [
            {
                "eid": "E1",
                "quote": "This is a dummy quoted passage to test the evidence requirement.",
                "start_char": 0,
                "end_char": 60,
                "why_relevant": "Supports the dummy fact/claim.",
                "source": {
                    "type": "internal",
                    "title": "dummy",
                    "url": None,
                },
            }
        ],
        "headline_body_delta": {
            "present": False,
            "items": [],
        },
        "metrics": {
            "evidence_density": {
                "num_claims": 1,
                "num_high_stakes_claims": 0,
                "num_evidence_items": 1,
                "evidence_to_claim_ratio": 1.0,
                "evidence_to_high_stakes_claim_ratio": None,
                "density_label": "medium",
                "note": "One claim supported by one quoted passage.",
            },
            "counterevidence_status": {
                "required": False,
                "status": "not_applicable",
                "search_scope": "none",
                "result": "not_applicable",
                "notes": "Dummy run: no refutation requested.",
            },
        },
        "declared_limits": [
            {
                "limit_id": "L1",
                "statement": "This is a dummy run; no real article was analyzed.",
            }
        ],
        "report_pack": {
            "summary_one_paragraph": "This is a dummy BiasLens run used to verify system integrity gates.",
            "reader_interpretation_guide": "BiasLens is currently running in test mode. No real article has been analyzed.",
            "findings_pack": {
                "items": [
                    {
                        "finding_id": "FP1",
                        "claim_id": "C1",
                        "restated_claim": "The article makes at least one declarative statement.",
                        "finding_text": "The article contains at least one declarative sentence.",
                        "severity": "🟢",
                        "evidence_eids": ["E1"],
                    }
                ]
            },
            "scholar_pack": {
                "items": []
            },
        },
    }


def _analyze_text_to_report_pack(text: str, source_title: str, source_url: Optional[str]) -> dict:
    """
    Placeholder for your real Pass A/Pass B engine later.
    For now, we produce a safe, honest 'unknown' pack that still passes the validator.
    """
    report = _dummy_report_pack()

    snippet = (text or "").strip()
    if len(snippet) > 240:
        snippet = snippet[:240] + "…"

    report["run_metadata"] = {
        "mode": "stub",
        "source_type": "url" if source_url else ("file_or_text" if source_title else "text"),
    }

    # Replace dummy evidence with an actual quote snippet from the input text (verbatim)
    quote = snippet if snippet else "No text provided."
    report["evidence_bank"][0]["quote"] = quote
    report["evidence_bank"][0]["start_char"] = 0
    report["evidence_bank"][0]["end_char"] = len(quote)
    report["evidence_bank"][0]["source"]["type"] = "url" if source_url else "text"
    report["evidence_bank"][0]["source"]["title"] = source_title
    report["evidence_bank"][0]["source"]["url"] = source_url

    report["facts_layer"]["facts"][0]["fact_text"] = "An input text was provided for analysis."
    report["facts_layer"]["facts"][0]["notes"] = "Stub mode: no fact-checking performed."
    report["claim_registry"]["claims"][0]["claim_text"] = "The input contains text to analyze."

    report["report_pack"]["summary_one_paragraph"] = (
        "BiasLens ran in stub mode: the input text was ingested, but full Pass A/Pass B extraction "
        "and verification are not wired yet, so substantive factual judgments are marked unknown."
    )
    report["report_pack"]["reader_interpretation_guide"] = (
        "This output is an integrity-safe placeholder: it shows how the system will present evidence, "
        "claims, and findings without inventing facts. Substantive checks will appear once the engine is wired."
    )

    return report


# -----------------------------
# CLI
# -----------------------------
def _load_text_from_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--url", type=str, default=None, help="Scrape and analyze a URL")
    p.add_argument("--text", type=str, default=None, help="Analyze provided text")
    p.add_argument("--file", type=str, default=None, help="Analyze a local text file")
    p.add_argument("--json", action="store_true", help="Print full report JSON")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    # Default behavior: integrity test
    if not args.url and not args.text and not args.file:
        report = _dummy_report_pack()
        _validate(report)  # should raise if invalid
        print("✅ BiasLens integrity gate PASSED.")
        return 0

    # Determine input text
    source_title = "manual_text"
    source_url: Optional[str] = None
    text: str = ""

    if args.url:
        source_title = "scraped_url"
        source_url = args.url
        sr = _try_scrape(args.url)
        if not sr.success:
            print("❌ Scrape failed:")
            print(sr.text)
            return 2
        text = sr.text or ""

    elif args.file:
        source_title = args.file
        text = _load_text_from_file(args.file)

    elif args.text is not None:
        source_title = "manual_text"
        text = args.text

    report = _analyze_text_to_report_pack(text=text, source_title=source_title, source_url=source_url)

    # Validate before output (fail closed)
    _validate(report)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("✅ BiasLens run PASSED validator.")
        print()
        print(report["report_pack"]["summary_one_paragraph"])
        print()
        print("Tip: re-run with --json to see the full structured output.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
