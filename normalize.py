import os
import re
from datetime import date

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

SOURCE_FILES = [
    ("data/calpers.csv", "CalPERS"),
    ("data/calstrs.csv", "CalSTRS"),
    ("data/oregon.csv", "Oregon Treasury"),
    ("data/wsib.csv", "WSIB"),
    ("data/utimco.csv", "UTIMCO"),
    ("data/psers.csv", "PSERS"),
]

DEDUP_COLUMNS = ["fund_name", "vintage_year", "source", "reporting_period"]

SOURCE_COLUMN_MAP = {
    "CalPERS": {
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
    "CalSTRS": {
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
    "Oregon Treasury": {
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
    "WSIB": {
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
    "UTIMCO": {
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
    "PSERS": {
        "fund_name": "fund_name",
        "partnership_name": "fund_name",
        "investment_name": "fund_name",
        "vintage_year": "vintage_year",
        "capital_committed": "capital_committed",
        "commitment": "capital_committed",
        "capital_contributed": "capital_contributed",
        "contributions": "capital_contributed",
        "capital_distributed": "capital_distributed",
        "distributions": "capital_distributed",
        "nav": "nav",
        "market_value": "nav",
        "net_irr": "net_irr",
        "irr": "net_irr",
        "tvpi": "tvpi",
        "dpi": "dpi",
        "source": "source",
        "scraped_date": "scraped_date",
        "reporting_period": "reporting_period",
    },
}

MISSING_TOKENS = {"", "-", "--", "na", "n/a", "n.m.", "n/m", "nm", "null", "none"}


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
        return float("nan")

    text = str(value).strip()
    if text.lower() in MISSING_TOKENS:
        return float("nan")

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    text = text.replace(",", "")
    text = text.replace("$", "")
    text = text.replace("%", "")
    text = text.replace("x", "").replace("X", "")
    text = text.strip()

    if text.lower() in MISSING_TOKENS:
        return float("nan")

    text = re.sub(r"[^0-9.\-]", "", text)
    if text in {"", ".", "-", "-."}:
        return float("nan")

    try:
        number = float(text)
    except ValueError:
        return float("nan")

    if negative:
        number = -number

    return number


def clean_irr(value):
    if pd.isna(value):
        return float("nan")

    original = str(value)
    had_percent = "%" in original
    number = clean_numeric(value)
    if pd.isna(number):
        return float("nan")

    if had_percent:
        return number / 100.0

    if abs(number) > 1 and abs(number) <= 100:
        return number / 100.0

    return number


def clean_year(value):
    if pd.isna(value):
        return float("nan")

    match = re.search(r"(19|20)\d{2}", str(value))
    if not match:
        return float("nan")

    try:
        return float(int(match.group(0)))
    except ValueError:
        return float("nan")


def safe_divide(numerator, denominator):
    num = pd.to_numeric(numerator, errors="coerce")
    den = pd.to_numeric(denominator, errors="coerce")
    den = den.where(den != 0)
    return num / den


def normalize_fund_name(series: pd.Series) -> pd.Series:
    result = series.fillna("UNKNOWN_FUND").astype(str)
    result = result.str.strip().str.replace(r"\s+", " ", regex=True)
    result = result.replace({"": "UNKNOWN_FUND", "nan": "UNKNOWN_FUND", "None": "UNKNOWN_FUND"})
    return result


def coalesce_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    while True:
        duplicated = pd.Series(df.columns).value_counts()
        duplicated = duplicated[duplicated > 1]
        if duplicated.empty:
            break

        col_name = duplicated.index[0]
        dup_df = df.loc[:, df.columns == col_name]
        merged = dup_df.bfill(axis=1).iloc[:, 0]
        df = df.loc[:, df.columns != col_name]
        df[col_name] = merged

    return df


def map_source_columns(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    source_map = SOURCE_COLUMN_MAP.get(source_name, {})
    rename_map = {col: source_map[col] for col in df.columns if col in source_map}
    mapped = df.rename(columns=rename_map)
    mapped = coalesce_duplicate_columns(mapped)
    return mapped


def remove_wsib_non_data_rows(df: pd.DataFrame) -> pd.DataFrame:
    if "fund_name" not in df.columns:
        return df

    result = df.copy()
    result = result[result["fund_name"].notna()]

    exclusion_terms = [
        "Corporate Finance",
        "Contributions",
        "Adjusted Market Value",
        "Distributions",
    ]

    pattern = "|".join(re.escape(term) for term in exclusion_terms)
    result = result[~result["fund_name"].astype(str).str.contains(pattern, case=False, na=False)]
    return result


def add_missing_unified_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in UNIFIED_COLUMNS:
        if col not in df.columns:
            df[col] = float("nan") if col not in {"fund_name", "source", "scraped_date", "reporting_period"} else None
    return df


def post_process_source(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    result = df.copy()

    if source_name == "WSIB":
        result = remove_wsib_non_data_rows(result)

    if "total_value" not in result.columns:
        result["total_value"] = float("nan")

    result = add_missing_unified_columns(result)

    result["fund_name"] = normalize_fund_name(result["fund_name"])
    result["vintage_year"] = result["vintage_year"].apply(clean_year)

    numeric_cols = [
        "capital_committed",
        "capital_contributed",
        "capital_distributed",
        "nav",
        "tvpi",
        "dpi",
        "total_value",
    ]
    for col in numeric_cols:
        result[col] = result[col].apply(clean_numeric)

    result["net_irr"] = result["net_irr"].apply(clean_irr)

    if source_name == "CalPERS":
        calpers_nav = result["total_value"] - result["capital_distributed"]
        result["nav"] = result["nav"].fillna(calpers_nav)

    derived_dpi = safe_divide(result["capital_distributed"], result["capital_contributed"])
    result["dpi"] = result["dpi"].fillna(derived_dpi)

    derived_tvpi = safe_divide(result["capital_distributed"].fillna(0) + result["nav"].fillna(0), result["capital_contributed"])
    result["tvpi"] = result["tvpi"].fillna(derived_tvpi)

    result["source"] = source_name

    if "scraped_date" not in result.columns:
        result["scraped_date"] = str(date.today())
    result["scraped_date"] = result["scraped_date"].fillna(str(date.today()))

    if "reporting_period" not in result.columns:
        result["reporting_period"] = "unknown"
    result["reporting_period"] = result["reporting_period"].fillna("unknown")

    return result


def print_source_diagnostics(source_name: str, raw_rows: int, after_mapping: int, after_cleaning: int, after_dedup: int) -> None:
    print(f"Source: {source_name}")
    print(f"raw_rows={raw_rows}")
    print(f"after_mapping={after_mapping}")
    print(f"after_cleaning={after_cleaning}")
    print(f"after_dedup={after_dedup}")


def build_unified_dataset():
    frames = []

    for filepath, source_name in SOURCE_FILES:
        if not os.path.exists(filepath):
            print_source_diagnostics(source_name, 0, 0, 0, 0)
            print(f"Warning: {filepath} not found — skipping")
            continue

        try:
            raw_df = pd.read_csv(filepath)
        except Exception as exc:
            print_source_diagnostics(source_name, 0, 0, 0, 0)
            print(f"Warning: failed to read {filepath}: {exc}")
            continue

        raw_rows = len(raw_df)

        standardized_df = standardize_column_names(raw_df)
        mapped_df = map_source_columns(standardized_df, source_name)
        after_mapping = len(mapped_df)

        cleaned_df = post_process_source(mapped_df, source_name)
        after_cleaning = len(cleaned_df)

        deduped_df = cleaned_df.drop_duplicates(subset=DEDUP_COLUMNS, keep="last")
        after_dedup = len(deduped_df)

        print_source_diagnostics(source_name, raw_rows, after_mapping, after_cleaning, after_dedup)

        frames.append(deduped_df[UNIFIED_COLUMNS])

    if not frames:
        print("No data files found. Run scrapers first.")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=DEDUP_COLUMNS, keep="last")

    combined["fund_name"] = normalize_fund_name(combined["fund_name"])
    combined["vintage_year"] = combined["vintage_year"].apply(clean_year)

    os.makedirs("data", exist_ok=True)
    combined.to_csv("data/unified_funds.csv", index=False)

    print(f"TOTAL_ROWS={len(combined)}")
    print(f"ROWS_WITH_DPI={int(combined['dpi'].notna().sum())}")
    print(f"ROWS_WITH_TVPI={int(combined['tvpi'].notna().sum())}")
    print(f"ROWS_WITH_IRR={int(combined['net_irr'].notna().sum())}")
    print("ROWS_PER_SOURCE")
    for source_name, count in combined["source"].value_counts(dropna=False).items():
        print(f"{source_name}={count}")


if __name__ == "__main__":
    build_unified_dataset()
