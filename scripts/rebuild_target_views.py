import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from normalize import (
    build_coverage_outputs,
    build_source_metadata,
    build_vc_fund_master,
    load_target_firms,
    match_target_funds,
)

UNIFIED_PATH = "data/unified_funds.csv"


def main():
    if not os.path.exists(UNIFIED_PATH):
        print("data/unified_funds.csv not found. Run python3 normalize.py first.")
        return

    unified_df = pd.read_csv(UNIFIED_PATH)
    target_df = load_target_firms()
    matched_df = match_target_funds(unified_df, target_df)

    coverage_snapshot = build_coverage_outputs(matched_df, target_df)
    vc_master = build_vc_fund_master(matched_df)
    build_source_metadata(unified_df)

    print(f"coverage snapshot rows: {len(coverage_snapshot)}")
    print(f"vc_fund_master rows: {len(vc_master)}")


if __name__ == "__main__":
    main()
