import argparse
import os
import re
import sys
from datetime import date, datetime
from glob import glob
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

UNIFIED_COLUMNS = [
    "fund_name",
    "vintage_year",
    "capital_committed",
    "capital_contributed",
    "capital_distributed",
    "nav",
    "net_irr",
    "tvpi",
    "dpi",
    "source",
    "scraped_date",
    "reporting_period",
]

DEDUP_KEY = ["fund_name", "vintage_year", "source", "reporting_period"]

SOURCE_FILES: Dict[str, str] = {
    "CalPERS": "data/calpers.csv",
    "CalSTRS": "data/calstrs.csv",
    "Oregon Treasury": "data/oregon.csv",
    "WSIB": "data/wsib.csv",
    "UTIMCO": "data/utimco_processed_for_openvc.csv",
    "PSERS": "data/psers.csv",
    "UC Regents": "data/uc_regents.csv",
    "Massachusetts PRIM": "data/massachusetts.csv",
    "Florida SBA": "data/florida.csv",
    "Louisiana TRSL": "data/louisiana.csv",
}

COMMON_ALIASES = {
    "fund": "fund_name",
    "investment_name": "fund_name",
    "description": "fund_name",
    "cash_in": "capital_contributed",
    "cash_out": "capital_distributed",
    "cash_out_&_remaining_value": "total_value",
    "total_value": "total_value",
    "investment_multiple": "tvpi",
    "capital_committed": "capital_committed",
    "capital_contributed": "capital_contributed",
    "capital_distributed": "capital_distributed",
    "current_market_value_b": "nav",
    "net_irr_2": "net_irr",
}


def normalize_col(col: str) -> str:
    c = str(col).strip().lower()
    c = c.replace("\n", "_").replace(" ", "_").replace("/", "_")
    c = c.replace("&", "and")
    c = re.sub(r"[^a-z0-9_]+", "", c)
    c = re.sub(r"_+", "_", c).strip("_")
    return c


def normalize_text(s: str) -> str:
    t = str(s or "").lower().strip()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def clean_numeric(values: pd.Series) -> pd.Series:
    s = values.astype(str).str.strip()
    lower = s.str.lower()
    missing_mask = lower.isin({"", "-", "--", "n/m", "nm", "n.a.", "na", "none", "null", "nan"})
    pct_mask = s.str.contains("%", na=False)

    s = s.str.replace(",", "", regex=False)
    s = s.str.replace("$", "", regex=False)
    s = s.str.replace("%", "", regex=False)
    s = s.str.replace("x", "", regex=False)
    s = s.str.replace("X", "", regex=False)
    s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    s = s.str.replace(r"\s+", "", regex=True)

    out = pd.to_numeric(s, errors="coerce")
    out = out.where(~pct_mask, out / 100.0)
    out = out.where(~missing_mask, np.nan)
    return out


def infer_gp_name_from_fund(fund_name: str) -> Optional[str]:
    name = str(fund_name or "").strip()
    if not name:
        return None
    split_pat = r"\b(Fund|Partners?|L\.P\.?|LP|Ltd\.?|LLC|Co\.?|Capital)\b"
    parts = re.split(split_pat, name, maxsplit=1, flags=re.IGNORECASE)
    base = (parts[0] if parts else name).strip(" ,.-")
    if not base:
        toks = name.split()
        base = " ".join(toks[:2]).strip() if toks else None
    return base or None


def infer_vintage_from_name(series: pd.Series) -> pd.Series:
    s = series.astype(str)
    start = s.str.extract(r"^\s*((?:19|20)\d{2})\b", expand=False)
    end = s.str.extract(r"\b((?:19|20)\d{2})\s*$", expand=False)
    any_year = s.str.extract(r"\b((?:19|20)\d{2})\b", expand=False)
    out = start.fillna(end).fillna(any_year)
    return pd.to_numeric(out, errors="coerce")


def detect_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = set(df.columns)
    for c in candidates:
        nc = normalize_col(c)
        if nc in cols:
            return nc
    return None


def source_file_scraped_date(path: str) -> str:
    try:
        return datetime.fromtimestamp(os.path.getmtime(path)).date().isoformat()
    except Exception:
        return str(date.today())


def diagnose_data_csvs(data_dir: str = "data") -> None:
    print("=== SOURCE FILE DIAGNOSTICS (data/*.csv) ===")
    files = sorted(glob(os.path.join(data_dir, "*.csv")))
    if not files:
        print("No CSV files found in data/\n")
        return

    for fp in files:
        fn = os.path.basename(fp)
        try:
            df = pd.read_csv(fp)
            print(f"\nFile: {fn}")
            print(f"raw_rows: {len(df)}")
            print(f"columns: {df.columns.tolist()}")
            sample = df.head(2)
            if sample.empty:
                print("sample: <empty>")
            else:
                print("sample_first_2_rows:")
                print(sample.to_string(index=False))
        except Exception as exc:
            print(f"\nFile: {fn}")
            print(f"ERROR reading file: {exc}")
    print("\n=== END DIAGNOSTICS ===\n")


def prepare_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [normalize_col(c) for c in out.columns]
    return out


def apply_common_mapping(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename_map = {}
    for c in out.columns:
        if c in COMMON_ALIASES:
            rename_map[c] = COMMON_ALIASES[c]
    if rename_map:
        out = out.rename(columns=rename_map)
    return out


def finalize_derived(df: pd.DataFrame, source_name: str, default_scraped: str) -> pd.DataFrame:
    out = df.copy()

    # Ensure columns exist.
    for col in [
        "fund_name",
        "vintage_year",
        "capital_committed",
        "capital_contributed",
        "capital_distributed",
        "nav",
        "total_value",
        "net_irr",
        "tvpi",
        "dpi",
        "source",
        "scraped_date",
        "reporting_period",
    ]:
        if col not in out.columns:
            out[col] = np.nan

    out["fund_name"] = out["fund_name"].astype(str).str.strip()
    out["fund_name"] = out["fund_name"].replace({"": np.nan, "nan": np.nan, "none": np.nan})
    out["fund_name"] = out["fund_name"].fillna("UNKNOWN_FUND")
    out["fund_name"] = out["fund_name"].str.replace(r"\s+", " ", regex=True)

    # Numeric cleaning.
    for col in [
        "vintage_year",
        "capital_committed",
        "capital_contributed",
        "capital_distributed",
        "nav",
        "total_value",
        "net_irr",
        "tvpi",
        "dpi",
    ]:
        out[col] = clean_numeric(out[col])

    # Vintage fallback from name.
    inferred_year = infer_vintage_from_name(out["fund_name"])
    out["vintage_year"] = out["vintage_year"].fillna(inferred_year)
    out["vintage_year"] = pd.to_numeric(out["vintage_year"], errors="coerce").astype("Int64")

    # net_irr decimal normalization.
    irr_vals = out["net_irr"].dropna()
    if not irr_vals.empty and irr_vals.median() > 1.5:
        out["net_irr"] = out["net_irr"] / 100.0

    # nav fallback from total_value - distributed.
    can_nav = out["nav"].isna() & out["total_value"].notna() & out["capital_distributed"].notna()
    out.loc[can_nav, "nav"] = out.loc[can_nav, "total_value"] - out.loc[can_nav, "capital_distributed"]

    contrib = pd.to_numeric(out["capital_contributed"], errors="coerce")
    dist = pd.to_numeric(out["capital_distributed"], errors="coerce")
    nav = pd.to_numeric(out["nav"], errors="coerce")

    # dpi derive when missing.
    dpi_derived = np.where(contrib > 0, dist / contrib, np.nan)
    out["dpi"] = out["dpi"].where(out["dpi"].notna(), dpi_derived)

    # tvpi derive when missing.
    tvpi_derived = np.where(contrib > 0, (dist + nav) / contrib, np.nan)
    out["tvpi"] = out["tvpi"].where(out["tvpi"].notna(), tvpi_derived)

    out["source"] = source_name
    out["scraped_date"] = out["scraped_date"].fillna(default_scraped)
    out["reporting_period"] = out["reporting_period"].fillna("unknown")

    return out


def map_utimco(raw_df: pd.DataFrame, filepath: str) -> pd.DataFrame:
    df = prepare_columns(raw_df)

    out = pd.DataFrame(index=df.index)

    fund_col = detect_column(df, ["fund_name", "description"])
    out["fund_name"] = df[fund_col] if fund_col else np.nan

    gp_col = detect_column(df, ["gp_name", "manager", "firm_name"])
    if gp_col:
        out["gp_name"] = df[gp_col]
    else:
        out["gp_name"] = out["fund_name"].map(infer_gp_name_from_fund)

    vint_col = detect_column(df, ["vintage_year", "vintage", "initial_investment_date"])
    out["vintage_year"] = df[vint_col] if vint_col else np.nan
    out["vintage_year"] = pd.to_numeric(out["vintage_year"], errors="coerce")
    out["vintage_year"] = out["vintage_year"].fillna(infer_vintage_from_name(out["fund_name"]))

    commit_col = detect_column(df, ["capital_committed", "committed", "commitment"])
    out["capital_committed"] = df[commit_col] if commit_col else np.nan

    contrib_col = detect_column(df, ["capital_contributed", "cash_in", "cash in", "paid_in_capital", "contributed"])
    out["capital_contributed"] = df[contrib_col] if contrib_col else np.nan

    dist_col = detect_column(df, ["capital_distributed", "cash_out", "cash out", "distributed"])
    out["capital_distributed"] = df[dist_col] if dist_col else np.nan

    total_col = detect_column(df, ["total_value", "cash_out_and_remaining_value", "cash_out_remaining_value"])
    out["total_value"] = df[total_col] if total_col else np.nan

    nav_col = detect_column(df, ["nav", "market_value", "current_market_value"])
    out["nav"] = df[nav_col] if nav_col else np.nan

    irr_col = detect_column(df, ["net_irr", "irr", "netirr"])
    out["net_irr"] = df[irr_col] if irr_col else np.nan

    tvpi_col = detect_column(df, ["tvpi", "investment_multiple", "multiple"])
    out["tvpi"] = df[tvpi_col] if tvpi_col else np.nan

    scraped_col = detect_column(df, ["scraped_date", "as_of_date", "date"])
    out["scraped_date"] = df[scraped_col] if scraped_col else source_file_scraped_date(filepath)

    rp_col = detect_column(df, ["reporting_period", "period", "report_period"])
    out["reporting_period"] = df[rp_col] if rp_col else "unknown"

    out = finalize_derived(out, "UTIMCO", source_file_scraped_date(filepath))
    return out


def map_generic(raw_df: pd.DataFrame, source_name: str, filepath: str) -> pd.DataFrame:
    df = prepare_columns(raw_df)
    df = apply_common_mapping(df)

    out = pd.DataFrame(index=df.index)

    # Prefer already unified names, then common alternates.
    out["fund_name"] = df[detect_column(df, ["fund_name", "fund", "investment_name", "description"]) ] if detect_column(df, ["fund_name", "fund", "investment_name", "description"]) else np.nan
    out["vintage_year"] = df[detect_column(df, ["vintage_year", "vintage", "initial_investment_date"]) ] if detect_column(df, ["vintage_year", "vintage", "initial_investment_date"]) else np.nan
    out["capital_committed"] = df[detect_column(df, ["capital_committed", "committed", "commitment"]) ] if detect_column(df, ["capital_committed", "committed", "commitment"]) else np.nan
    out["capital_contributed"] = df[detect_column(df, ["capital_contributed", "cash_in", "cash in", "paid_in_capital"]) ] if detect_column(df, ["capital_contributed", "cash_in", "cash in", "paid_in_capital"]) else np.nan
    out["capital_distributed"] = df[detect_column(df, ["capital_distributed", "cash_out", "cash out", "distributed"]) ] if detect_column(df, ["capital_distributed", "cash_out", "cash out", "distributed"]) else np.nan
    out["nav"] = df[detect_column(df, ["nav", "market_value", "current_market_value"]) ] if detect_column(df, ["nav", "market_value", "current_market_value"]) else np.nan
    out["total_value"] = df[detect_column(df, ["total_value", "cash_out_and_remaining_value"]) ] if detect_column(df, ["total_value", "cash_out_and_remaining_value"]) else np.nan
    out["net_irr"] = df[detect_column(df, ["net_irr", "irr"]) ] if detect_column(df, ["net_irr", "irr"]) else np.nan
    out["tvpi"] = df[detect_column(df, ["tvpi", "investment_multiple", "multiple"]) ] if detect_column(df, ["tvpi", "investment_multiple", "multiple"]) else np.nan
    out["dpi"] = df[detect_column(df, ["dpi"]) ] if detect_column(df, ["dpi"]) else np.nan
    out["scraped_date"] = df[detect_column(df, ["scraped_date", "as_of_date", "date"]) ] if detect_column(df, ["scraped_date", "as_of_date", "date"]) else source_file_scraped_date(filepath)
    out["reporting_period"] = df[detect_column(df, ["reporting_period", "period", "report_period"]) ] if detect_column(df, ["reporting_period", "period", "report_period"]) else "unknown"

    out = finalize_derived(out, source_name, source_file_scraped_date(filepath))
    return out


def map_source(raw_df: pd.DataFrame, source_name: str, filepath: str) -> pd.DataFrame:
    if source_name == "UTIMCO":
        return map_utimco(raw_df, filepath)
    return map_generic(raw_df, source_name, filepath)


def run_normalization(diagnose_only: bool = False) -> int:
    diagnose_data_csvs("data")
    if diagnose_only:
        return 0

    per_source_stats: List[Tuple[str, int, int, int, int]] = []
    frames: List[pd.DataFrame] = []
    fatal_errors: List[str] = []

    for source_name, filepath in SOURCE_FILES.items():
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found — skipping")
            continue

        try:
            raw = pd.read_csv(filepath)
        except Exception as exc:
            fatal_errors.append(f"{source_name} read error: {exc}")
            continue

        raw_rows = len(raw)

        try:
            mapped = map_source(raw, source_name, filepath)
        except Exception as exc:
            fatal_errors.append(f"{source_name} mapping error: {exc}")
            continue

        after_mapping = len(mapped)

        cleaned = mapped.copy()
        # Keep rows; only normalize fund_name text and keep UNKNOWN_FUND placeholders.
        cleaned["fund_name"] = cleaned["fund_name"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
        cleaned["fund_name"] = cleaned["fund_name"].replace({"": "UNKNOWN_FUND", "nan": "UNKNOWN_FUND", "none": "UNKNOWN_FUND"})
        after_cleaning = len(cleaned)

        deduped = cleaned.drop_duplicates(subset=DEDUP_KEY, keep="first")
        after_dedup = len(deduped)

        per_source_stats.append((source_name, raw_rows, after_mapping, after_cleaning, after_dedup))
        frames.append(deduped)

        print(
            f"Source: {source_name}\n"
            f"raw_rows={raw_rows}\n"
            f"after_mapping={after_mapping}\n"
            f"after_cleaning={after_cleaning}\n"
            f"after_dedup={after_dedup}\n"
        )

    if fatal_errors:
        print("Fatal parsing errors:")
        for err in fatal_errors:
            print(f"- {err}")
        return 1

    if not frames:
        print("No source files were normalized. Exiting.")
        return 1

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=DEDUP_KEY, keep="first")

    # Preserve schema order and type safety.
    for c in UNIFIED_COLUMNS:
        if c not in combined.columns:
            combined[c] = np.nan

    combined["vintage_year"] = pd.to_numeric(combined["vintage_year"], errors="coerce").astype("Int64")
    combined = combined[UNIFIED_COLUMNS].copy()
    combined = combined.sort_values(["vintage_year", "fund_name"], ascending=[False, True], na_position="last").reset_index(drop=True)

    os.makedirs("data", exist_ok=True)
    out_path = "data/unified_funds.csv"
    combined.to_csv(out_path, index=False)

    # Final summary, concise and source-first.
    print("=== NORMALIZATION SUMMARY ===")
    for source_name, raw_rows, after_mapping, after_cleaning, after_dedup in per_source_stats:
        print(f"{source_name}: {raw_rows} -> {after_mapping} -> {after_cleaning} -> {after_dedup}")

    print(f"Unified dataset: {len(combined)} rows saved to {out_path}")

    rows_with_dpi = int(combined["dpi"].notna().sum())
    rows_with_tvpi = int(combined["tvpi"].notna().sum())
    rows_with_irr = int(combined["net_irr"].notna().sum())
    print(f"ROWS_WITH_DPI: {rows_with_dpi}")
    print(f"ROWS_WITH_TVPI: {rows_with_tvpi}")
    print(f"ROWS_WITH_IRR: {rows_with_irr}")
    print(f"ROWS_PER_SOURCE: {combined['source'].value_counts(dropna=False).to_dict()}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize LP source CSVs into data/unified_funds.csv")
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Print per-source diagnostics from data/*.csv and exit",
    )
    args = parser.parse_args()
    return run_normalization(diagnose_only=args.diagnose)


if __name__ == "__main__":
    sys.exit(main())
