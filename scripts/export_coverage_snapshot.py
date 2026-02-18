import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from normalize import build_coverage_outputs, load_target_firms, match_target_funds

FUNDS_PATH = "data/unified_funds.csv"
TARGET_PATH = "metadata/target_firms.csv"  # kept for compatibility
OUTPUT_PATH = "data/coverage_snapshot.csv"


def load_csv_safe(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def main():
    funds_df = load_csv_safe(FUNDS_PATH)
    _ = TARGET_PATH

    if funds_df.empty:
        os.makedirs("data", exist_ok=True)
        pd.DataFrame(
            columns=[
                "canonical_gp",
                "fund_name",
                "vintage_year",
                "source",
                "reporting_period",
                "tvpi",
                "dpi",
                "net_irr",
            ]
        ).to_csv(OUTPUT_PATH, index=False)
        print("total rows exported: 0")
        print("unique firms covered: 0")
        return

    target_df = load_target_firms()
    matched_df = match_target_funds(funds_df, target_df)
    snapshot_df = build_coverage_outputs(matched_df, target_df)

    total_rows = int(len(snapshot_df))
    unique_firms = int(snapshot_df["canonical_gp"].dropna().astype(str).nunique()) if not snapshot_df.empty else 0

    print(f"total rows exported: {total_rows}")
    print(f"unique firms covered: {unique_firms}")


if __name__ == "__main__":
    main()
