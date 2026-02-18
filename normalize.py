import os

import pandas as pd

SOURCE_FILES = {
    "CalPERS": "data/calpers.csv",
    "CalSTRS": "data/calstrs.csv",
    "Oregon Treasury": "data/oregon.csv",
    "WSIB": "data/wsib.csv",
    "UC Regents": "data/uc_regents.csv",
    "Massachusetts PRIM": "data/massachusetts.csv",
    "Florida SBA": "data/florida.csv",
    "Louisiana Teachers": "data/louisiana.csv",
}

UNIFIED_SCHEMA = [
    "fund_name",
    "vintage_year",
    "capital_committed",
    "capital_contributed",
    "capital_distributed",
    "nav",
    "dpi",
    "tvpi",
    "net_irr",
    "source",
    "reporting_period",
    "scraped_date",
]

# Supports both current unified files and older source-specific extractions.
COLUMN_ALIASES = {
    "fund": "fund_name",
    "investment_name": "fund_name",
    "cash_in": "capital_contributed",
    "cash_out": "capital_distributed",
    "cash_out_&_remaining_value": "total_value",
    "investment_multiple": "tvpi",
    "initial_investment\ndate": "vintage_year",
    "capital\ncommitted": "capital_committed",
    "paid-in\ncapital\na": "capital_contributed",
    "capital\ndistributed_1\nc_": "capital_distributed",
    "current\nmarket_value\nb": "nav",
    "total_value\nb+c": "total_value",
    "total_value\nmultiple\nb+c_a": "tvpi",
    "net\nirr_2": "net_irr",
}


def _to_numeric(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    pct_mask = s.str.contains("%", na=False)

    s = s.str.replace(",", "", regex=False)
    s = s.str.replace("$", "", regex=False)
    s = s.str.replace("%", "", regex=False)
    s = s.str.replace("x", "", regex=False)
    s = s.str.replace("X", "", regex=False)
    s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)

    out = pd.to_numeric(s, errors="coerce")
    out = out.where(~pct_mask, out / 100.0)
    return out


def normalize_source(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    df = df.copy()

    # Rename legacy columns when present.
    rename_map = {}
    for old, new in COLUMN_ALIASES.items():
        if old in df.columns:
            rename_map[old] = new
    if rename_map:
        df = df.rename(columns=rename_map)

    if "fund_name" not in df.columns:
        df["fund_name"] = None

    # Drop rows with null/empty fund names to avoid dedup collapse.
    df = df.dropna(subset=["fund_name"])
    df["fund_name"] = df["fund_name"].astype(str).str.strip()
    df = df[df["fund_name"] != ""]
    df = df[df["fund_name"].str.lower() != "nan"]

    # Ensure expected columns exist before coercion.
    for col in [
        "vintage_year",
        "capital_committed",
        "capital_contributed",
        "capital_distributed",
        "nav",
        "tvpi",
        "net_irr",
        "dpi",
        "reporting_period",
        "scraped_date",
    ]:
        if col not in df.columns:
            df[col] = None

    # Coerce numerics with currency/percent cleanup.
    for col in [
        "vintage_year",
        "capital_committed",
        "capital_contributed",
        "capital_distributed",
        "nav",
        "tvpi",
        "net_irr",
        "dpi",
    ]:
        df[col] = _to_numeric(df[col])

    if "total_value" in df.columns:
        df["total_value"] = _to_numeric(df["total_value"])

    # If vintage year came through as date text, extract year fallback.
    raw_vintage = pd.to_datetime(df.get("vintage_year"), errors="coerce").dt.year
    df["vintage_year"] = df["vintage_year"].where(df["vintage_year"].notna(), raw_vintage)
    df["vintage_year"] = pd.to_numeric(df["vintage_year"], errors="coerce").astype("Int64")

    # Normalize IRR to decimal.
    irr_as_pct = df["net_irr"].notna() & (df["net_irr"].abs() > 2)
    df.loc[irr_as_pct, "net_irr"] = df.loc[irr_as_pct, "net_irr"] / 100.0

    # Derive NAV for legacy CalPERS where total value is provided.
    if "total_value" in df.columns:
        nav_missing = df["nav"].isna()
        can_nav = nav_missing & df["total_value"].notna() & df["capital_distributed"].notna()
        df.loc[can_nav, "nav"] = df.loc[can_nav, "total_value"] - df.loc[can_nav, "capital_distributed"]

    # Compute DPI if missing.
    if "dpi" not in df.columns:
        df["dpi"] = None
    dpi_missing = df["dpi"].isna()
    dpi_ready = (
        dpi_missing
        & df["capital_distributed"].notna()
        & df["capital_contributed"].notna()
        & (df["capital_contributed"] > 0)
    )
    df.loc[dpi_ready, "dpi"] = (
        df.loc[dpi_ready, "capital_distributed"]
        / df.loc[dpi_ready, "capital_contributed"]
    )

    # Compute TVPI if missing.
    tvpi_missing = df["tvpi"].isna()
    tvpi_ready = (
        tvpi_missing
        & df["capital_distributed"].notna()
        & df["nav"].notna()
        & df["capital_contributed"].notna()
        & (df["capital_contributed"] > 0)
    )
    df.loc[tvpi_ready, "tvpi"] = (
        df.loc[tvpi_ready, "capital_distributed"] + df.loc[tvpi_ready, "nav"]
    ) / df.loc[tvpi_ready, "capital_contributed"]

    # Enforce source name consistency from file mapping.
    df["source"] = source_name

    for col in UNIFIED_SCHEMA:
        if col not in df.columns:
            df[col] = None

    return df[UNIFIED_SCHEMA].copy()


def run():
    all_dfs = []

    for source_name, filepath in SOURCE_FILES.items():
        if not os.path.exists(filepath):
            print("⚠ MISSING: {0}".format(filepath))
            continue

        raw = pd.read_csv(filepath)
        raw_count = len(raw)

        mapped = normalize_source(raw, source_name)
        mapped_count = len(mapped)

        cleaned = mapped.copy()
        cleaned_count = len(cleaned)

        all_dfs.append(cleaned)
        print(
            "{0}: {1} rows loaded -> {2} mapped -> {3} after cleaning".format(
                source_name, raw_count, mapped_count, cleaned_count
            )
        )

    if not all_dfs:
        print("No source files found. Nothing to normalize.")
        return

    combined = pd.concat(all_dfs, ignore_index=True)

    before_dedup = len(combined)
    combined = combined.drop_duplicates(subset=["fund_name", "vintage_year", "source"])
    after_dedup = len(combined)
    print("\n✓ Deduplication: {0} -> {1} rows ({2} removed)".format(before_dedup, after_dedup, before_dedup - after_dedup))

    combined = combined.sort_values(["vintage_year", "fund_name"], ascending=[True, True], na_position="last").reset_index(drop=True)

    os.makedirs("data", exist_ok=True)
    combined.to_csv("data/unified_funds.csv", index=False)

    print("\n=== NORMALIZE DIAGNOSTICS ===")
    for src in combined["source"].dropna().unique():
        sub = combined[combined["source"] == src]
        dpi_f = sub["dpi"].notna().sum()
        tvpi_f = sub["tvpi"].notna().sum()
        irr_f = sub["net_irr"].notna().sum()
        print("{0}: {1} rows | DPI: {2} | TVPI: {3} | IRR: {4}".format(src, len(sub), dpi_f, tvpi_f, irr_f))

    print("TOTAL: {0} rows".format(len(combined)))
    print("\nOutput: data/unified_funds.csv ✓")

    # Validate gp_disclosed_funds.csv exists and is loadable
    if os.path.exists("gp_disclosed_funds.csv"):
        gp_df = pd.read_csv("gp_disclosed_funds.csv")
        gp_true = gp_df["irr_meaningful"].map(
            lambda x: True if str(x).lower() in ["true", "1", "yes"] else False
        )
        print("\n✓ GP-Disclosed: {0} funds loaded (a16z, Founders Fund, Social Capital)".format(len(gp_df)))
        print("  irr_meaningful=TRUE: {0} funds".format(int(gp_true.sum())))
    else:
        print("\n⚠ gp_disclosed_funds.csv not found — GP-disclosed data unavailable")


if __name__ == "__main__":
    run()
