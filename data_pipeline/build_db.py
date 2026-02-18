import os
import sqlite3
from datetime import date

import pandas as pd

from ingest_calpers import ingest_calpers
from ingest_founders_fund import ingest_founders_fund
from ingest_psers import ingest_psers

DB_CANDIDATES = ["openlp.db", "openvc.db"]
DB_TABLE = "funds"

DB_COLUMNS = [
    "source",
    "fund_name",
    "gp_name",
    "vintage_year",
    "cash_in",
    "cash_out",
    "remaining_value",
    "total_value",
    "net_irr",
    "as_of_date",
]


def _select_db_path():
    for path in DB_CANDIDATES:
        if os.path.exists(path):
            return path
    return "openlp.db"


def _run_ingestors():
    outputs = []
    for name, func in [
        ("CalPERS", ingest_calpers),
        ("PSERS", ingest_psers),
        ("Founders Fund", ingest_founders_fund),
    ]:
        try:
            df = func()
        except Exception as exc:
            print(f"[{name}] Ingestion failed: {exc}")
            continue

        if df is None or df.empty:
            print(f"[{name}] No rows returned.")
            continue

        outputs.append(df)
    return outputs


def _ensure_db_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS funds (
            source TEXT,
            fund_name TEXT,
            gp_name TEXT,
            vintage_year INTEGER,
            cash_in REAL,
            cash_out REAL,
            remaining_value REAL,
            total_value REAL,
            net_irr REAL,
            as_of_date TEXT
        )
        """
    )
    conn.commit()


def main():
    frames = _run_ingestors()
    if not frames:
        print("[Build] No source data available. Nothing to load.")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined["as_of_date"] = combined["as_of_date"].fillna(str(date.today()))

    combined = combined.drop_duplicates(subset=["fund_name", "vintage_year", "source"], keep="last")

    os.makedirs("data", exist_ok=True)
    canonical_output = "data/unified_funds.csv"
    combined.to_csv(canonical_output, index=False)
    print(f"[Build] Saved unified canonical dataset: {canonical_output} ({len(combined)} rows)")

    db_path = _select_db_path()
    print(f"[Build] Target DB: {db_path}")

    db_ready = combined.reindex(columns=DB_COLUMNS)

    with sqlite3.connect(db_path) as conn:
        _ensure_db_schema(conn)

        try:
            existing = pd.read_sql(f"SELECT {', '.join(DB_COLUMNS)} FROM {DB_TABLE}", conn)
        except Exception:
            existing = pd.DataFrame(columns=DB_COLUMNS)

        merged = pd.concat([existing, db_ready], ignore_index=True)
        before = len(merged)
        merged = merged.drop_duplicates(subset=["fund_name", "vintage_year", "source"], keep="last")
        after = len(merged)

        merged.to_sql(DB_TABLE, conn, if_exists="replace", index=False)

    inserted = len(db_ready)
    deduped = before - after
    print(f"[Build] New rows prepared: {inserted}")
    print(f"[Build] Duplicates removed: {deduped}")
    print(f"[Build] Final table rows: {after}")


if __name__ == "__main__":
    main()
