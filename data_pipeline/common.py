import re
from datetime import date
from typing import Optional

import pandas as pd

CANONICAL_COLUMNS = [
    "fund_name",
    "gp_name",
    "vintage_year",
    "committed",
    "cash_in",
    "cash_out",
    "remaining_value",
    "total_value",
    "tvpi",
    "dpi",
    "rvpi",
    "net_irr",
    "source",
    "as_of_date",
]

MISSING_TOKENS = {"", "-", "--", "n/m", "nm", "n.m.", "na", "n/a", "none", "null"}

GP_KEYWORDS = {
    "lightspeed": "Lightspeed",
    "khosla ventures": "Khosla Ventures",
    "mayfield": "Mayfield",
    "founders fund": "Founders Fund",
    "sequoia": "Sequoia",
    "benchmark": "Benchmark",
    "accel": "Accel",
    "a16z": "Andreessen Horowitz",
    "andreessen": "Andreessen Horowitz",
    "bessemer": "Bessemer",
    "greylock": "Greylock",
    "general catalyst": "General Catalyst",
}


def clean_token(value):
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in MISSING_TOKENS:
        return None
    return text


def parse_number(value):
    token = clean_token(value)
    if token is None:
        return None

    text = token.replace("$", "").replace(",", "").strip()
    negative = False

    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    multiplier = 1.0
    if text.endswith(("B", "b")):
        multiplier = 1_000_000_000.0
        text = text[:-1]
    elif text.endswith(("M", "m")):
        multiplier = 1_000_000.0
        text = text[:-1]
    elif text.endswith(("K", "k")):
        multiplier = 1_000.0
        text = text[:-1]

    if text.endswith("x"):
        text = text[:-1]
    if text.endswith("%"):
        text = text[:-1]

    text = text.strip()
    if text.lower() in MISSING_TOKENS:
        return None

    try:
        number = float(text) * multiplier
    except ValueError:
        return None

    if negative:
        number = -number
    return number


def parse_percent(value):
    token = clean_token(value)
    if token is None:
        return None
    text = token.strip().replace("%", "")
    try:
        return float(text) / 100.0
    except ValueError:
        return None


def parse_multiple(value):
    token = clean_token(value)
    if token is None:
        return None
    text = token.strip().replace("x", "").replace("X", "")
    try:
        return float(text)
    except ValueError:
        return None


def parse_year(value):
    token = clean_token(value)
    if token is None:
        return None
    match = re.search(r"(19|20)\d{2}", token)
    if not match:
        return None
    return int(match.group(0))


def safe_divide(numerator, denominator):
    if denominator in (None, 0) or pd.isna(denominator):
        return None
    if numerator is None or pd.isna(numerator):
        return None
    try:
        return float(numerator) / float(denominator)
    except Exception:
        return None


def normalize_gp_name(fund_name: Optional[str]) -> Optional[str]:
    token = clean_token(fund_name)
    if token is None:
        return None

    lower = token.lower()
    for keyword, normalized in GP_KEYWORDS.items():
        if keyword in lower:
            return normalized

    words = token.split()
    if not words:
        return None
    if len(words) == 1:
        return words[0]
    return f"{words[0]} {words[1]}"


def finalize_canonical(df: pd.DataFrame, source: str, as_of_date: Optional[str]) -> pd.DataFrame:
    df = df.copy()

    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    if "source" not in df.columns or df["source"].isna().all():
        df["source"] = source
    else:
        df["source"] = df["source"].fillna(source)

    if as_of_date is None:
        as_of_date = str(date.today())
    df["as_of_date"] = df["as_of_date"].fillna(as_of_date)

    if "gp_name" not in df.columns:
        df["gp_name"] = None
    df["gp_name"] = df["gp_name"].where(df["gp_name"].notna(), df["fund_name"].map(normalize_gp_name))

    if "total_value" in df.columns:
        missing_total = df["total_value"].isna()
        df.loc[missing_total, "total_value"] = (
            pd.to_numeric(df.loc[missing_total, "cash_out"], errors="coerce")
            + pd.to_numeric(df.loc[missing_total, "remaining_value"], errors="coerce")
        )

    if "tvpi" in df.columns:
        missing_tvpi = df["tvpi"].isna()
        df.loc[missing_tvpi, "tvpi"] = df.loc[missing_tvpi].apply(
            lambda r: safe_divide(r.get("total_value"), r.get("cash_in")), axis=1
        )

    if "dpi" in df.columns:
        missing_dpi = df["dpi"].isna()
        df.loc[missing_dpi, "dpi"] = df.loc[missing_dpi].apply(
            lambda r: safe_divide(r.get("cash_out"), r.get("cash_in")), axis=1
        )

    if "rvpi" in df.columns:
        missing_rvpi = df["rvpi"].isna()
        df.loc[missing_rvpi, "rvpi"] = df.loc[missing_rvpi].apply(
            lambda r: safe_divide(r.get("remaining_value"), r.get("cash_in")), axis=1
        )

    # Keep only canonical output columns in consistent order.
    return df[CANONICAL_COLUMNS]
