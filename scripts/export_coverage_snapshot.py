import os
import pandas as pd

FUNDS_PATH = "data/unified_funds.csv"
TARGET_PATH = "metadata/target_firms.csv"
OUTPUT_PATH = "data/coverage_snapshot.csv"

OUTPUT_COLUMNS = [
    "canonical_gp",
    "fund_name",
    "vintage_year",
    "source",
    "reporting_period",
    "tvpi",
    "dpi",
    "net_irr",
]


def load_csv_safe(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def main():
    funds_df = load_csv_safe(FUNDS_PATH)
    target_df = load_csv_safe(TARGET_PATH)

    if funds_df.empty or target_df.empty:
        output_df = pd.DataFrame(columns=OUTPUT_COLUMNS)
        os.makedirs("data", exist_ok=True)
        output_df.to_csv(OUTPUT_PATH, index=False)
        print("total rows exported: 0")
        print("unique firms covered: 0")
        return

    required_target_cols = {"canonical_gp", "match_pattern"}
    if not required_target_cols.issubset(set(target_df.columns)):
        output_df = pd.DataFrame(columns=OUTPUT_COLUMNS)
        os.makedirs("data", exist_ok=True)
        output_df.to_csv(OUTPUT_PATH, index=False)
        print("total rows exported: 0")
        print("unique firms covered: 0")
        return

    if "fund_name" not in funds_df.columns:
        funds_df["fund_name"] = ""

    funds_work = funds_df.copy()
    funds_work["fund_name_lc"] = funds_work["fund_name"].fillna("").astype(str).str.lower()
    funds_work["canonical_gp"] = pd.NA

    target_work = target_df[["canonical_gp", "match_pattern"]].copy()
    target_work["canonical_gp"] = target_work["canonical_gp"].fillna("").astype(str).str.strip()
    target_work["match_pattern"] = target_work["match_pattern"].fillna("").astype(str).str.strip().str.lower()
    target_work = target_work[(target_work["canonical_gp"] != "") & (target_work["match_pattern"] != "")]

    # Deterministic first-match assignment in source file order.
    for _, row in target_work.iterrows():
        pattern = row["match_pattern"]
        gp = row["canonical_gp"]
        mask = funds_work["fund_name_lc"].str.contains(pattern, regex=False, na=False)
        needs_assignment = funds_work["canonical_gp"].isna()
        funds_work.loc[mask & needs_assignment, "canonical_gp"] = gp

    matched = funds_work[funds_work["canonical_gp"].notna()].copy()

    for col in OUTPUT_COLUMNS:
        if col not in matched.columns:
            matched[col] = pd.NA

    matched["_vintage_sort"] = pd.to_numeric(matched["vintage_year"], errors="coerce")
    matched = matched.sort_values(
        ["canonical_gp", "_vintage_sort", "fund_name"],
        ascending=[True, True, True],
        na_position="last",
    )

    output_df = matched[OUTPUT_COLUMNS]

    os.makedirs("data", exist_ok=True)
    output_df.to_csv(OUTPUT_PATH, index=False)

    total_rows = int(len(output_df))
    unique_firms = int(output_df["canonical_gp"].dropna().astype(str).nunique())

    print(f"total rows exported: {total_rows}")
    print(f"unique firms covered: {unique_firms}")


if __name__ == "__main__":
    main()
