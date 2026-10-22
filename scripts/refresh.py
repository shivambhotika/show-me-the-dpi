#!/usr/bin/env python3
"""Manual refresh workflow with immutable snapshots and explicit approval."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_quality import audit_frame, enrich_records


ROOT = Path(__file__).resolve().parents[1]


def display_path(path: Path) -> str:
    """Render paths inside or outside the repository without failing."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def check_external_sources(path: Path, *, timeout: int = 12) -> pd.DataFrame:
    """Check configured source pages without ingesting or changing metrics."""
    if not path.exists():
        return pd.DataFrame([{
            "name": "source registry",
            "url": str(path),
            "status": "missing",
            "http_status": "",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "note": "registry file does not exist",
        }])
    registry = pd.read_csv(path).fillna("")
    rows = []
    checked_at = datetime.now(timezone.utc).isoformat()
    headers = {"User-Agent": "show-me-the-dpi-source-check/1.0"}
    for row in registry.itertuples(index=False):
        url = str(getattr(row, "url", "")).strip()
        name = str(getattr(row, "name", "")).strip()
        if not url:
            rows.append({"name": name, "url": url, "status": "missing-url", "http_status": "", "checked_at": checked_at, "note": "no configured source URL"})
            continue
        try:
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            status = "ok" if response.status_code < 400 else "http-error"
            note = f"final_url={response.url}"
            rows.append({"name": name, "url": url, "status": status, "http_status": response.status_code, "checked_at": checked_at, "note": note})
        except requests.RequestException as exc:
            rows.append({"name": name, "url": url, "status": "unreachable", "http_status": "", "checked_at": checked_at, "note": str(exc)[:240]})
    return pd.DataFrame(rows, columns=["name", "url", "status", "http_status", "checked_at", "note"])


def build_change_report(current: pd.DataFrame, previous: pd.DataFrame | None) -> pd.DataFrame:
    """Return a row-level diff without mutating either snapshot."""
    columns = ["change_type", "fund_name", "vintage_year", "source", "reporting_period", "field", "previous_value", "current_value"]
    if previous is None or previous.empty:
        return pd.DataFrame(columns=columns)
    key = ["fund_name", "vintage_year", "source", "reporting_period"]
    if not set(key).issubset(current.columns) or not set(key).issubset(previous.columns):
        return pd.DataFrame([{"change_type": "error", "field": "canonical_key", "previous_value": "", "current_value": "missing required key columns"}], columns=columns)
    # Normalize missing key components before indexing. Pandas NaN values do
    # not compare equal to themselves, which would otherwise create false
    # new/removed records on every refresh for funds without a vintage.
    old = previous.drop_duplicates(key).copy()
    new = current.drop_duplicates(key).copy()
    for frame in (old, new):
        for field in key:
            frame[field] = frame[field].where(frame[field].notna(), "__MISSING__").astype(str)
    old = old.set_index(key)
    new = new.set_index(key)
    rows = []
    for record_key in sorted(set(new.index) - set(old.index), key=str):
        rows.append({"change_type": "new", **dict(zip(key, record_key)), "field": "", "previous_value": "", "current_value": "record added"})
    for record_key in sorted(set(old.index) - set(new.index), key=str):
        rows.append({"change_type": "removed", **dict(zip(key, record_key)), "field": "", "previous_value": "record removed", "current_value": ""})
    compare_columns = sorted((set(old.columns) & set(new.columns)) - {"retrieved_at"})
    for record_key in sorted(set(old.index) & set(new.index), key=str):
        before = old.loc[record_key]
        after = new.loc[record_key]
        for field in compare_columns:
            left = "" if pd.isna(before[field]) else str(before[field])
            right = "" if pd.isna(after[field]) else str(after[field])
            if left != right:
                rows.append({"change_type": "changed", **dict(zip(key, record_key)), "field": field, "previous_value": left, "current_value": right})
    return pd.DataFrame(rows, columns=columns)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or approve a manual data refresh")
    parser.add_argument("command", choices=["check", "audit", "approve"])
    parser.add_argument("--input", default="data/unified_funds.csv")
    parser.add_argument("--snapshot-dir", default="data/snapshots")
    parser.add_argument("--report-dir", default="data/refresh_reports")
    parser.add_argument("--skip-source-check", action="store_true", help="skip network checks of configured benchmark/source pages")
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
    source_report_path = report_dir / f"source_check_{stamp}.csv"
    if args.skip_source_check:
        source_checks = pd.DataFrame(columns=["name", "url", "status", "http_status", "checked_at", "note"])
    else:
        source_checks = check_external_sources(ROOT / "data" / "external_benchmark_sources.csv")
    source_checks.to_csv(source_report_path, index=False)
    previous_paths = sorted(snapshot_dir.glob("unified_funds_*.csv"))
    previous_path = previous_paths[-1] if previous_paths else None
    previous = pd.read_csv(previous_path) if previous_path else None
    change_report = build_change_report(current, previous)
    change_report_path = report_dir / f"changes_{stamp}.csv"
    change_report.to_csv(change_report_path, index=False)

    if args.command == "check":
        print(f"Checked {len(current):,} rows; {len(findings):,} findings")
        print(f"Report: {display_path(report_path)}")
        print(f"Checked {len(source_checks):,} configured source pages; {int(source_checks['status'].eq('ok').sum()) if not source_checks.empty else 0} reachable")
        print(f"Source report: {display_path(source_report_path)}")
        print(f"Change report: {display_path(change_report_path)} ({len(change_report):,} changes)")
        print("No files were replaced. Use audit for the full report or approve after review.")
        source_failures = source_checks[~source_checks["status"].eq("ok")] if not source_checks.empty else source_checks
        return 1 if not findings.empty or not source_failures.empty else 0

    if args.command == "audit":
        print(f"Audit report: {report_path.relative_to(ROOT)}")
        print(f"Source report: {display_path(source_report_path)}")
        print(f"Change report: {display_path(change_report_path)} ({len(change_report):,} changes)")
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
