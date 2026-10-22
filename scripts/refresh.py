#!/usr/bin/env python3
"""Manual refresh workflow with immutable snapshots and explicit approval."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_quality import audit_frame, enrich_records


ROOT = Path(__file__).resolve().parents[1]


def display_path(path: Path) -> str:
    """Render paths inside or outside the repository without failing."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or approve a manual data refresh")
    parser.add_argument("command", choices=["check", "audit", "approve"])
    parser.add_argument("--input", default="data/unified_funds.csv")
    parser.add_argument("--snapshot-dir", default="data/snapshots")
    parser.add_argument("--report-dir", default="data/refresh_reports")
    args = parser.parse_args()

    input_path = ROOT / args.input
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_dir = ROOT / args.snapshot_dir
    report_dir = ROOT / args.report_dir
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    current = pd.read_csv(input_path)
    enriched = enrich_records(current, ROOT, retrieved_at=stamp)
    findings = audit_frame(enriched, source_name=input_path.name)
    report_path = report_dir / f"refresh_{stamp}.csv"
    findings.to_csv(report_path, index=False)

    if args.command == "check":
        print(f"Checked {len(current):,} rows; {len(findings):,} findings")
        print(f"Report: {display_path(report_path)}")
        print("No files were replaced. Use audit for the full report or approve after review.")
        return 1 if not findings.empty else 0

    if args.command == "audit":
        print(f"Audit report: {report_path.relative_to(ROOT)}")
        print(findings.to_string(index=False) if not findings.empty else "No findings.")
        return 1 if not findings.empty else 0

    blocking = findings[findings["severity"].eq("fail")] if not findings.empty else findings
    if not blocking.empty:
        print("Approval refused: resolve blocking schema or calculation failures before publishing.")
        print(f"Review: {display_path(report_path)}")
        return 1
    if not findings.empty:
        print(f"Publishing with {len(findings):,} documented warnings/disputes; these remain visible in the audit trail.")
    snapshot_path = snapshot_dir / f"unified_funds_{stamp}.csv"
    shutil.copy2(input_path, snapshot_path)
    print(f"Approved immutable snapshot: {display_path(snapshot_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
