#!/usr/bin/env python3
"""Run the reproducible data audit and write a dated report."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_quality import audit_frame, enrich_records


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/unified_funds.csv")
    parser.add_argument("--output-dir", default="data/audits")
    args = parser.parse_args()

    input_path = ROOT / args.input
    df = pd.read_csv(input_path)
    enriched = enrich_records(df, ROOT)
    findings = audit_frame(enriched, source_name=input_path.name)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"audit_{stamp}.csv"
    findings.to_csv(report_path, index=False)

    summary = {
        "input": str(input_path.relative_to(ROOT)),
        "rows": len(df),
        "findings": len(findings),
        "failures": int((findings["severity"] == "fail").sum()) if not findings.empty else 0,
        "report": str(report_path.relative_to(ROOT)) if report_path.is_relative_to(ROOT) else str(report_path),
    }
    print(pd.Series(summary).to_string())
    return 1 if summary["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
