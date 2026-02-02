#!/usr/bin/env python3
"""
FILE: pipeline.py
PURPOSE: Local BiasLens runner — resolves input → builds report pack → validates fail-closed.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from io_sources import resolve_input_text

# LOCK: This is the ONLY authorized report builder.
from report_stub import dummy_report_pack
from builders.report_builder import build_report

from integrity_validator import validate_output, ValidationError

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--url", type=str, default=None, help="Scrape and analyze a URL")
    p.add_argument("--text", type=str, default=None, help="Analyze provided text")
    p.add_argument("--file", type=str, default=None, help="Analyze a local text file")
    p.add_argument("--json", action="store_true", help="Print full report JSON")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    # Default behavior: integrity test
    if not args.url and not args.text and not args.file:
        report = dummy_report_pack()
        validate_output(report)
        print("✅ BiasLens integrity gate PASSED.")
        return 0

    # Determine input text
    try:
        text, source_title, source_url = resolve_input_text(
            args.url, args.file, args.text
        )
    except RuntimeError as e:
        print("❌ Input failed:")
        print(str(e))
        return 2

     # 🔒 Authorized builder boundary
    report = build_report(
        text=text,
        source_title=source_title,
        source_url=source_url,
    )

    if not isinstance(report, dict):
        raise RuntimeError("Builder violation: report must be a dict matching schema.")

   # Fail-closed validation
    try:
        validate_output(report)
    except ValidationError as e:
        print("❌ Validator failed (fail-closed):")
        print(str(e))
        return 3

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("✅ BiasLens run PASSED validator.\n")
        print(report["report_pack"]["summary_one_paragraph"])
        print("\nTip: re-run with --json to see the full structured output.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
