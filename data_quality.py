"""Shared provenance, classification, and validation helpers.

The project intentionally keeps source values intact.  These helpers add
metadata and produce findings; they do not silently repair disputed records.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re

import numpy as np
import pandas as pd


PROVENANCE_COLUMNS = [
    "fund_tier",
    "strategy",
    "source_type",
    "source_url",
    "data_as_of",
    "published_at",
    "retrieved_at",
    "metric_basis",
    "verification_status",
    "calculation_method",
    "vintage_source",
    "story_candidate",
    "story_reason",
]


def _text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def source_type(row: pd.Series) -> str:
    raw = _text(row.get("data_source_type")) or _text(row.get("source"))
    if raw in {"LP-Disclosed", "Public LP disclosure"} or raw in {
        "CalPERS", "CalSTRS", "Oregon Treasury", "WSIB", "UTIMCO", "PSERS",
        "UC Regents", "Massachusetts PRIM", "Florida SBA", "Louisiana TRSL", "Louisiana Teachers",
    }:
        return "LP-disclosed performance"
    if "manager" in raw.lower() or "gp" in raw.lower() or "firm disclosure" in raw.lower():
        return "official manager disclosure"
    if any(token in raw.lower() for token in ("carta", "angellist", "administrator")):
        return "administrator/platform benchmark"
    if "benchmark" in raw.lower() or "msci" in raw.lower() or "colibri" in raw.lower():
        return "benchmark provider"
    return raw or "unknown"


def strategy_from_row(row: pd.Series) -> str:
    category = _text(row.get("fund_category")).lower()
    sub = _text(row.get("sub_strategy")).lower()
    text = " ".join((category, sub, _text(row.get("investment_focus")).lower()))
    if any(token in text for token in ("private equity", "buyout", "credit", "distress", "special situations", "pe ")):
        return "PE"
    return "Venture"


def popular_patterns(base_dir: Path) -> list[tuple[str, str]]:
    path = base_dir / "metadata" / "target_firms.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path).fillna("")
    return [(str(row.canonical_gp), str(row.match_pattern).lower()) for row in df.itertuples()]


def enrich_records(df: pd.DataFrame, base_dir: Path, *, retrieved_at: str | None = None) -> pd.DataFrame:
    """Add explicit classifications/provenance defaults without changing metrics."""
    out = df.copy()
    original_dpi = out["dpi"].notna() if "dpi" in out.columns else pd.Series(False, index=out.index)
    original_tvpi = out["tvpi"].notna() if "tvpi" in out.columns else pd.Series(False, index=out.index)
    today = retrieved_at or date.today().isoformat()
    for col in PROVENANCE_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    out["strategy"] = out.apply(strategy_from_row, axis=1)
    out["source_type"] = out.apply(source_type, axis=1)
    out["source_url"] = out["source_url"].fillna("")
    out["data_as_of"] = out["data_as_of"].fillna(out.get("reporting_period", pd.Series(index=out.index, dtype="object")))
    out["retrieved_at"] = out["retrieved_at"].fillna(today)
    metric_defaults = pd.Series(
        np.where(out["source_type"].eq("LP-disclosed performance"), "as-reported LP basis", "as-reported"),
        index=out.index,
    )
    verification_defaults = pd.Series(
        np.where(out["source_type"].eq("LP-disclosed performance"), "verified-source", "directional"),
        index=out.index,
    )
    out["metric_basis"] = out["metric_basis"].where(out["metric_basis"].notna(), metric_defaults)
    out["verification_status"] = out["verification_status"].where(out["verification_status"].notna(), verification_defaults)
    out["dispute_reason"] = out.get("dispute_reason", pd.Series("", index=out.index)).fillna("")
    out["calculation_method"] = out["calculation_method"].fillna("reported or normalized; see source")
    out["dpi_calculation_method"] = np.where(original_dpi, "reported", "derived from distributed/contributed when possible")
    out["tvpi_calculation_method"] = np.where(original_tvpi, "reported", "derived from distributed+NAV/contributed when possible")
    out["vintage_source"] = out["vintage_source"].fillna("reported" if "vintage_year" in out else "unknown")

    # A reported DPI above reported TVPI cannot be reconciled from the row's
    # available fields. Preserve both source values, but do not present the
    # row as verified until the source explains its basis or a reviewer clears
    # it. This is deliberately a classification, not a silent correction.
    if {"dpi", "tvpi"}.issubset(out.columns):
        dpi_values = pd.to_numeric(out["dpi"], errors="coerce")
        tvpi_values = pd.to_numeric(out["tvpi"], errors="coerce")
        disputed = dpi_values.notna() & tvpi_values.notna() & (dpi_values > tvpi_values + 0.05)
        out.loc[disputed, "verification_status"] = "disputed-source"
        out.loc[disputed, "dispute_reason"] = "reported DPI exceeds reported TVPI; source basis requires review"

    patterns = popular_patterns(base_dir)
    def tier(row: pd.Series) -> str:
        if row.get("strategy") == "PE":
            return "PE"
        gp = _text(row.get("canonical_gp") or row.get("gp_display_name")).lower()
        popular = any(pattern and pattern in gp for _, pattern in patterns)
        dpi = pd.to_numeric(pd.Series([row.get("dpi")]), errors="coerce").iloc[0]
        tvpi = pd.to_numeric(pd.Series([row.get("tvpi")]), errors="coerce").iloc[0]
        vintage = pd.to_numeric(pd.Series([row.get("vintage_year")]), errors="coerce").iloc[0]
        exceptional = bool((pd.notna(dpi) and dpi >= 3.0 and pd.notna(vintage) and vintage <= 2018) or (pd.notna(tvpi) and tvpi >= 5.0))
        if exceptional and row.get("verification_status") == "verified-source":
            return "exceptional"
        return "popular" if popular else "core"

    out["fund_tier"] = out.apply(tier, axis=1)
    out["story_candidate"] = out["fund_tier"].eq("exceptional")
    out["story_reason"] = out.apply(
        lambda row: "verified high realization or total value" if bool(row["story_candidate"]) else "",
        axis=1,
    )
    return out


def audit_frame(df: pd.DataFrame, *, source_name: str = "dataset") -> pd.DataFrame:
    """Return one row per validation finding; empty means no findings."""
    findings: list[dict] = []
    required = {"fund_name", "vintage_year", "source", "reporting_period"}
    missing = sorted(required - set(df.columns))
    for col in missing:
        findings.append({"source": source_name, "row": "", "metric": col, "severity": "fail", "finding": "required column missing", "disposition": "repair schema"})
    if missing:
        return pd.DataFrame(findings)

    numeric = {col: pd.to_numeric(df[col], errors="coerce") for col in ["capital_contributed", "capital_distributed", "nav", "dpi", "tvpi", "net_irr"] if col in df}
    for idx, row in df.iterrows():
        contributed = numeric.get("capital_contributed", pd.Series(dtype=float)).get(idx, np.nan)
        distributed = numeric.get("capital_distributed", pd.Series(dtype=float)).get(idx, np.nan)
        nav = numeric.get("nav", pd.Series(dtype=float)).get(idx, np.nan)
        dpi = numeric.get("dpi", pd.Series(dtype=float)).get(idx, np.nan)
        tvpi = numeric.get("tvpi", pd.Series(dtype=float)).get(idx, np.nan)
        if pd.notna(contributed) and contributed > 0 and pd.notna(distributed) and pd.notna(dpi):
            expected = distributed / contributed
            if not np.isclose(expected, dpi, rtol=0.015, atol=0.02):
                reported = row.get("dpi_calculation_method", "reported") == "reported"
                findings.append({"source": source_name, "row": idx, "metric": "dpi", "severity": "warn" if reported else "fail", "finding": f"reported {dpi:.4f} differs from distributed/contributed {expected:.4f}", "disposition": "document source basis" if reported else "repair calculation"})
        if pd.notna(contributed) and contributed > 0 and pd.notna(distributed) and pd.notna(nav) and pd.notna(tvpi):
            expected = (distributed + nav) / contributed
            if not np.isclose(expected, tvpi, rtol=0.015, atol=0.02):
                reported = row.get("tvpi_calculation_method", "reported") == "reported"
                findings.append({"source": source_name, "row": idx, "metric": "tvpi", "severity": "warn" if reported else "fail", "finding": f"reported {tvpi:.4f} differs from (distributed+nav)/contributed {expected:.4f}", "disposition": "document source basis" if reported else "repair calculation"})
        if pd.notna(dpi) and pd.notna(tvpi) and dpi > tvpi + 0.05:
            findings.append({"source": source_name, "row": idx, "metric": "dpi/tvpi", "severity": "disputed", "finding": f"DPI {dpi:.4f} exceeds TVPI {tvpi:.4f}", "disposition": "preserve values and exclude from verified rankings until source basis is confirmed"})
        irr = numeric.get("net_irr", pd.Series(dtype=float)).get(idx, np.nan)
        if pd.notna(irr) and abs(irr) > 10:
            findings.append({"source": source_name, "row": idx, "metric": "net_irr", "severity": "fail", "finding": "IRR is not normalized to decimal scale", "disposition": "normalize in pipeline"})

    dup_key = [col for col in ["fund_name", "vintage_year", "source", "reporting_period"] if col in df.columns]
    if dup_key:
        dupes = df[df.duplicated(dup_key, keep=False)]
        for idx in dupes.index:
            findings.append({"source": source_name, "row": idx, "metric": "dedup", "severity": "fail", "finding": "duplicate canonical key", "disposition": "deduplicate or retain as separate source period"})
    return pd.DataFrame(findings, columns=["source", "row", "metric", "severity", "finding", "disposition"])
