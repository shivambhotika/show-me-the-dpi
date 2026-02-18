import os
import re
from datetime import date

import pandas as pd

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover
    BeautifulSoup = None

from common import (
    finalize_canonical,
    parse_multiple,
    parse_number,
    parse_percent,
    parse_year,
)

CALPERS_CANDIDATE_PATHS = [
    "/Users/shivambhotika/Documents/Venture/Show me the DPI/Private Equity Program Fund Performance Review- Printer-friendly - CalPERS.html",
    "data/Private Equity Program Fund Performance Review- Printer-friendly - CalPERS.html",
]


def _find_calpers_html_path():
    for path in CALPERS_CANDIDATE_PATHS:
        if os.path.exists(path):
            return path
    return None


def _extract_as_of_date_from_html(html_text: str):
    patterns = [
        r"As of\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        r"As of\s+([A-Za-z]+\s+\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return str(date.today())


def ingest_calpers():
    path = _find_calpers_html_path()
    if not path:
        print("[CalPERS] File not found. Skipping.")
        return pd.DataFrame()

    print(f"[CalPERS] Reading HTML file: {path}")

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            html_text = f.read()
    except Exception as exc:
        print(f"[CalPERS] Failed to read file: {exc}")
        return pd.DataFrame()

    as_of_date = _extract_as_of_date_from_html(html_text)

    try:
        if BeautifulSoup is not None:
            soup = BeautifulSoup(html_text, "html.parser")
            table = soup.find("table")
            if table is not None:
                raw_df = pd.read_html(str(table))[0]
            else:
                raw_df = pd.read_html(path)[0]
        else:
            raw_df = pd.read_html(path)[0]
    except Exception as exc:
        print(f"[CalPERS] Table extraction failed: {exc}")
        return pd.DataFrame()

    if raw_df.empty:
        print("[CalPERS] No rows extracted.")
        return pd.DataFrame()

    raw_df.columns = [str(c).strip().lower().replace(" ", "_").replace("&", "and") for c in raw_df.columns]

    rows = []
    skipped = 0

    for _, row in raw_df.iterrows():
        fund_name = row.get("fund")
        if fund_name is None or str(fund_name).strip() == "":
            skipped += 1
            continue

        normalized = {
            "fund_name": str(fund_name).strip(),
            "gp_name": None,
            "vintage_year": parse_year(row.get("vintage_year")),
            "committed": parse_number(row.get("capital_committed")),
            "cash_in": parse_number(row.get("cash_in")),
            "cash_out": parse_number(row.get("cash_out")),
            "remaining_value": None,
            "total_value": parse_number(row.get("cash_out_and_remaining_value")),
            "tvpi": parse_multiple(row.get("investment_multiple")),
            "dpi": None,
            "rvpi": None,
            "net_irr": parse_percent(row.get("net_irr")),
            "source": "CalPERS",
            "as_of_date": as_of_date,
        }

        if normalized["total_value"] is not None and normalized["cash_out"] is not None:
            normalized["remaining_value"] = normalized["total_value"] - normalized["cash_out"]

        rows.append(normalized)

    result = pd.DataFrame(rows)
    result = finalize_canonical(result, source="CalPERS", as_of_date=as_of_date)

    if result["fund_name"].isna().any():
        print("[CalPERS] Warning: missing fund_name in extracted rows.")

    os.makedirs("data", exist_ok=True)
    output_path = "data/ingested_calpers.csv"
    result.to_csv(output_path, index=False)

    print(f"[CalPERS] Extracted rows: {len(result)}")
    print(f"[CalPERS] Skipped rows: {skipped}")
    print(f"[CalPERS] Saved: {output_path}")
    return result


if __name__ == "__main__":
    ingest_calpers()
