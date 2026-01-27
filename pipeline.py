#!/usr/bin/env python3
"""
BiasLens Pipeline (local runner)

Supports:
  - python3 pipeline.py                       (runs integrity self-test / dummy pack)
  - python3 pipeline.py --url "https://..."   (scrape article text then run)
  - python3 pipeline.py --text "..."          (analyze provided text)
  - python3 pipeline.py --file path.txt       (analyze text file)
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from io_sources import resolve_input_text
from report_stub import dummy_report_pack, analyze_text_to_report_pack
from validator import validate_output, ValidationError


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
        text, source_title, source_url = resolve_input_text(args.url, args.file, args.text)
    except RuntimeError as e:
        print("❌ Input failed:")
        print(str(e))
        return 2

    report = analyze_text_to_report_pack(text=text, source_title=source_title, source_url=source_url)

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
