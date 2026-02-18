import os
import pandas as pd

DATA_FILES = [
    ("CalPERS", "data/calpers.csv"),
    ("CalSTRS", "data/calstrs.csv"),
    ("Oregon Treasury", "data/oregon.csv"),
    ("WSIB", "data/wsib.csv"),
    ("UTIMCO", "data/utimco.csv"),
    ("PSERS", "data/psers.csv"),
]

FUND_KEYWORDS = ["fund", "partnership", "investment", "name"]


def detect_fund_candidates(columns):
    candidates = []
    for col in columns:
        lower = str(col).lower()
        if any(keyword in lower for keyword in FUND_KEYWORDS):
            candidates.append(col)
    return candidates


def main():
    for source_name, path in DATA_FILES:
        print("\n" + "=" * 80)
        print(f"Source: {source_name}")
        print(f"File: {path}")

        if not os.path.exists(path):
            print("Status: file not found")
            continue

        try:
            df = pd.read_csv(path)
        except Exception as exc:
            print(f"Status: failed to read CSV ({exc})")
            continue

        print(f"Row count: {len(df)}")
        print("Columns:")
        print(list(df.columns))

        print("First 2 rows:")
        if df.empty:
            print("[]")
        else:
            print(df.head(2).to_dict("records"))

        candidates = detect_fund_candidates(df.columns)
        print("Fund-name candidates:")
        if not candidates:
            print("None")
        else:
            for col in candidates:
                non_null = int(df[col].notna().sum())
                print(f"- {col}: non-null={non_null}")


if __name__ == "__main__":
    main()
