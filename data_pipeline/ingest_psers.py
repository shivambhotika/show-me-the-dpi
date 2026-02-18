import os
import re
from datetime import date

import pandas as pd
import pdfplumber

from common import (
    clean_token,
    finalize_canonical,
    parse_multiple,
    parse_number,
    parse_percent,
    parse_year,
)

PSERS_CANDIDATE_PATHS = [
    "/Users/shivambhotika/Documents/Venture/Show me the DPI/psers portfolio quarterly public disclosure report q1-24 - final.pdf",
    "data/psers portfolio quarterly public disclosure report q1-24 - final.pdf",
]

SUMMARY_KEYWORDS = [
    "total private",
    "liquidated",
    "psers total",
    "reporting period",
    "asset class",
    "vintage total commitment",
    "as of:",
    "portfolio summary by asset class",
    "totals",
]


def _find_psers_pdf_path():
    for path in PSERS_CANDIDATE_PATHS:
        if os.path.exists(path):
            return path
    return None


def _extract_as_of_date(pdf_text: str):
    match = re.search(r"As of\s+([A-Za-z]+\s+\d{4})", pdf_text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return str(date.today())


def _iter_table_lines(page):
    tables = page.extract_tables() or []
    for table in tables:
        for row in table:
            if not row:
                continue
            for cell in row:
                if not cell:
                    continue
                for raw_line in str(cell).splitlines():
                    line = " ".join(raw_line.split())
                    if line:
                        yield line


def _is_summary_row(text: str):
    lower = text.lower()
    return any(keyword in lower for keyword in SUMMARY_KEYWORDS)


def _is_metric_token(token: str):
    token_clean = clean_token(token)
    if token_clean is None:
        return True
    if parse_number(token_clean) is not None:
        return True
    if parse_percent(token_clean) is not None:
        return True
    if parse_multiple(token_clean) is not None:
        return True
    return token_clean.lower() in {"n.m.", "nm", "n/m", "na", "n/a", "-"}


def _parse_psers_line(line: str):
    tokens = line.split()
    if len(tokens) < 8:
        return None

    vintage_token = tokens[-7]
    vintage_year = parse_year(vintage_token)
    if vintage_year is None:
        return None

    metric_tokens = tokens[-6:]
    if not all(_is_metric_token(tok) for tok in metric_tokens):
        return None

    fund_name = " ".join(tokens[:-7]).strip()
    if not fund_name or _is_summary_row(fund_name):
        return None

    commitment, contributions, distributions, nav, net_irr, tvpi = metric_tokens

    return {
        "fund_name": fund_name,
        "gp_name": None,
        "vintage_year": vintage_year,
        "committed": parse_number(commitment),
        "cash_in": parse_number(contributions),
        "cash_out": parse_number(distributions),
        "remaining_value": parse_number(nav),
        "total_value": None,
        "tvpi": parse_multiple(tvpi),
        "dpi": None,
        "rvpi": None,
        "net_irr": parse_percent(net_irr),
        "source": "PSERS",
        "as_of_date": None,
    }


def ingest_psers():
    path = _find_psers_pdf_path()
    if not path:
        print("[PSERS] File not found. Skipping.")
        return pd.DataFrame()

    print(f"[PSERS] Reading PDF file: {path}")

    rows = []
    skipped = 0
    all_text_chunks = []

    in_private_equity_section = False

    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                all_text_chunks.append(page_text)
                page_lower = page_text.lower()

                if "private equity active partnerships" in page_lower:
                    in_private_equity_section = True
                if any(
                    marker in page_lower
                    for marker in [
                        "private real estate active partnerships",
                        "private credit active partnerships",
                        "private infrastructure active partnerships",
                        "private commodities active partnerships",
                    ]
                ):
                    in_private_equity_section = False

                for line in _iter_table_lines(page):
                    if not in_private_equity_section and "venture" not in line.lower():
                        continue

                    parsed = _parse_psers_line(line)
                    if parsed is None:
                        skipped += 1
                        continue
                    rows.append(parsed)
    except Exception as exc:
        print(f"[PSERS] Extraction failed: {exc}")
        return pd.DataFrame()

    if not rows:
        print("[PSERS] No fund-level PE/VC rows extracted.")
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    as_of_date = _extract_as_of_date("\n".join(all_text_chunks))
    result["as_of_date"] = as_of_date
    result = finalize_canonical(result, source="PSERS", as_of_date=as_of_date)

    if result["fund_name"].isna().any():
        print("[PSERS] Warning: missing fund_name in extracted rows.")
    if result["vintage_year"].isna().any():
        print("[PSERS] Warning: missing vintage_year in extracted rows.")

    os.makedirs("data", exist_ok=True)
    output_path = "data/ingested_psers.csv"
    result.to_csv(output_path, index=False)

    print(f"[PSERS] Extracted rows: {len(result)}")
    print(f"[PSERS] Skipped rows: {skipped}")
    print(f"[PSERS] Saved: {output_path}")
    return result


if __name__ == "__main__":
    ingest_psers()
