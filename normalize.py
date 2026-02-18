import os
import re
from datetime import date

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

DEDUP_COLUMNS = ["fund_name", "vintage_year", "source", "reporting_period"]

SOURCE_CONFIG = [
    {
        "name": "CalPERS",
        "path": "data/calpers.csv",
        "column_map": {
            "fund": "fund_name",
            "vintage_year": "vintage_year",
            "capital_committed": "capital_committed",
            "cash_in": "capital_contributed",
            "cash_out": "capital_distributed",
            "cash_out_&_remaining_value": "total_value",
            "investment_multiple": "tvpi",
            "net_irr": "net_irr",
            "source": "source",
            "scraped_date": "scraped_date",
            "reporting_period": "reporting_period",
        },
    },
    {
        "name": "CalSTRS",
        "path": "data/calstrs.csv",
        "column_map": {
            "fund_name": "fund_name",
            "vintage_year": "vintage_year",
            "capital_committed": "capital_committed",
            "capital_contributed": "capital_contributed",
            "capital_distributed": "capital_distributed",
            "nav": "nav",
            "net_irr": "net_irr",
            "tvpi": "tvpi",
            "dpi": "dpi",
            "source": "source",
            "scraped_date": "scraped_date",
            "reporting_period": "reporting_period",
        },
    },
    {
        "name": "Oregon Treasury",
        "path": "data/oregon.csv",
        "column_map": {
            "fund_name": "fund_name",
            "vintage_year": "vintage_year",
            "capital_committed": "capital_committed",
            "capital_contributed": "capital_contributed",
            "capital_distributed": "capital_distributed",
            "nav": "nav",
            "net_irr": "net_irr",
            "tvpi": "tvpi",
            "dpi": "dpi",
            "source": "source",
            "scraped_date": "scraped_date",
            "reporting_period": "reporting_period",
        },
    },
    {
        "name": "WSIB",
        "path": "data/wsib.csv",
        "column_map": {
            "investment_name": "fund_name",
            "initial_investment_date": "vintage_year",
            "capital_committed": "capital_committed",
            "paid-in_capital_a": "capital_contributed",
            "capital_distributed_1_c_": "capital_distributed",
            "current_market_value_b": "nav",
            "total_value_b+c": "total_value",
            "total_value_multiple_b+c_a": "tvpi",
            "net_irr_2": "net_irr",
            "source": "source",
            "scraped_date": "scraped_date",
            "reporting_period": "reporting_period",
        },
    },
    {
        "name": "UTIMCO",
        "path": "data/utimco.csv",
        "column_map": {
            "fund_name": "fund_name",
            "investment_name": "fund_name",
            "manager": "fund_name",
            "partnership": "fund_name",
            "col_0": "fund_name",
            "vintage_year": "vintage_year",
            "capital_committed": "capital_committed",
            "capital_contributed": "capital_contributed",
            "capital_distributed": "capital_distributed",
            "nav": "nav",
            "net_irr": "net_irr",
            "tvpi": "tvpi",
            "dpi": "dpi",
            "source": "source",
            "scraped_date": "scraped_date",
            "reporting_period": "reporting_period",
        },
    },
]

MISSING_TOKENS = {"", "-", "--", "na", "n/a", "n.m.", "n/m", "nm", "none", "null"}


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace("\n", "_", regex=False)
        .str.replace(" ", "_", regex=False)
    )
    return df


def clean_numeric(value):
    if pd.isna(value):
        return np.nan

    text = str(value).strip()
    if text.lower() in MISSING_TOKENS:
        return np.nan

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    has_percent = "%" in text
    text = text.replace("$", "").replace(",", "")
    text = text.replace("x", "").replace("X", "")
    text = text.replace("%", "")
    text = re.sub(r"[^0-9.\-]", "", text)

    if text in {"", ".", "-", "-."}:
        return np.nan

    try:
        num = float(text)
    except ValueError:
        return np.nan

    if negative:
        num = -num

    if has_percent:
        num = num / 100.0

    return num


def clean_fund_name(series: pd.Series) -> pd.Series:
    return (
        series.fillna("UNKNOWN_FUND")
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .replace({"": "UNKNOWN_FUND", "nan": "UNKNOWN_FUND", "None": "UNKNOWN_FUND"})
    )


def apply_source_mapping(df: pd.DataFrame, source_map: dict) -> pd.DataFrame:
    rename_map = {col: source_map[col] for col in df.columns if col in source_map}
    mapped = df.rename(columns=rename_map)

    # Coalesce duplicate columns if multiple source columns map to one unified name.
    if mapped.columns.duplicated().any():
        deduped = pd.DataFrame(index=mapped.index)
        for col in mapped.columns.unique():
            same_cols = mapped.loc[:, mapped.columns == col]
            deduped[col] = same_cols.bfill(axis=1).iloc[:, 0]
        mapped = deduped

    return mapped


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in UNIFIED_COLUMNS + ["total_value"]:
        if col not in df.columns:
            if col in {"fund_name", "source", "scraped_date", "reporting_period"}:
                df[col] = None
            else:
                df[col] = np.nan
    return df


def post_process_source(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    out = ensure_columns(df)

    out["fund_name"] = clean_fund_name(out["fund_name"])

    numeric_cols = [
        "vintage_year",
        "capital_committed",
        "capital_contributed",
        "capital_distributed",
        "nav",
        "net_irr",
        "tvpi",
        "dpi",
        "total_value",
    ]
    for col in numeric_cols:
        out[col] = out[col].apply(clean_numeric)

    if source_name == "CalPERS":
        nav_from_total = out["total_value"] - out["capital_distributed"]
        out["nav"] = out["nav"].where(out["nav"].notna(), nav_from_total)

    capital_contributed = pd.to_numeric(out["capital_contributed"], errors="coerce")
    capital_distributed = pd.to_numeric(out["capital_distributed"], errors="coerce")
    nav = pd.to_numeric(out["nav"], errors="coerce")

    source_dpi = pd.to_numeric(out["dpi"], errors="coerce")
    source_tvpi = pd.to_numeric(out["tvpi"], errors="coerce")

    derived_dpi = np.where(capital_contributed > 0, capital_distributed / capital_contributed, np.nan)
    derived_tvpi = np.where(capital_contributed > 0, (capital_distributed + nav) / capital_contributed, np.nan)

    out["dpi"] = np.where(source_dpi.notna(), source_dpi, derived_dpi)
    out["tvpi"] = np.where(source_tvpi.notna(), source_tvpi, derived_tvpi)

    out["source"] = source_name
    out["scraped_date"] = out["scraped_date"].fillna(str(date.today()))
    out["reporting_period"] = out["reporting_period"].fillna("unknown")

    return out


def build_unified_dataset():
    frames = []

    for source_cfg in SOURCE_CONFIG:
        source_name = source_cfg["name"]
        path = source_cfg["path"]
        source_map = source_cfg["column_map"]

        if not os.path.exists(path):
            print(f"{source_name}: file not found at {path} — skipping")
            continue

        try:
            raw_df = pd.read_csv(path)
        except Exception as exc:
            print(f"{source_name}: failed to load {path} ({exc})")
            continue

        raw_rows = len(raw_df)
        print(f"\n{source_name} raw columns: {raw_df.columns.tolist()}")

        standardized_df = standardize_column_names(raw_df)
        mapped_df = apply_source_mapping(standardized_df, source_map)
        mapped_rows = len(mapped_df)

        processed_df = post_process_source(mapped_df, source_name)

        deduped_df = processed_df.drop_duplicates(subset=DEDUP_COLUMNS, keep="last")
        dedup_rows = len(deduped_df)

        print(f"{source_name}: {raw_rows} rows loaded -> {mapped_rows} mapped -> {dedup_rows} after dedup")

        frames.append(deduped_df[UNIFIED_COLUMNS].copy())

    if not frames:
        print("No data files found. Run scrapers first.")
        return

    combined = pd.concat(frames, ignore_index=True)

    combined["fund_name"] = clean_fund_name(combined["fund_name"])
    combined["vintage_year"] = pd.to_numeric(combined["vintage_year"], errors="coerce")

    combined = combined.drop_duplicates(subset=DEDUP_COLUMNS, keep="last")
    combined = combined.sort_values("vintage_year", ascending=False, na_position="last")

    os.makedirs("data", exist_ok=True)
    output_path = "data/unified_funds.csv"
    combined.to_csv(output_path, index=False)

    print(f"\nUnified dataset: {len(combined)} total fund entries")
    print(f"Sources: {combined['source'].value_counts(dropna=False).to_dict()}")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    build_unified_dataset()
