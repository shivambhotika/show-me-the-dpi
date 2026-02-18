import os
import re
import sqlite3
from contextlib import closing
from typing import Dict, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="Show Me the DPI", layout="wide")

# Simple benchmark table (unchanged assumptions)
BENCHMARKS = {
    2017: {"median_tvpi": 1.6, "top_quartile_tvpi": 2.2},
    2018: {"median_tvpi": 1.4, "top_quartile_tvpi": 2.0},
    2019: {"median_tvpi": 1.2, "top_quartile_tvpi": 1.8},
}

REQUIRED_COLUMNS = [
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

NUMERIC_COLUMNS = ["vintage_year", "cash_in", "cash_out", "remaining_value", "total_value", "net_irr"]

RESOURCE_METADATA_CANDIDATES = [
    "data/source_metadata.csv",
    "data/resources.csv",
    "data/source_catalog.csv",
]

TARGET_FIRMS_PATH = "metadata/target_firms.csv"
MASTER_DATA_PATH = "data/vc_fund_master.csv"
FAMILY_KEYWORDS = {
    "growth": "Growth",
    "opportunity": "Opportunity",
    "seed": "Seed",
    "select": "Select",
    "sidecar": "Sidecar",
    "continuation": "Continuation",
}
CATEGORY_COLORS = {
    "Venture": "#2C3E50",
    "Growth": "#18A999",
    "Opportunities": "#F4B942",
    "PE": "#8B4513",
    "Company Creation": "#7B68EE",
}


ABOUT_COPY = """
LP disclosures are public. Fund performance is not secret — it's just scattered across government pension websites, buried in quarterly PDFs, and formatted in ways that make it genuinely painful to find.
This tool pulls that data together.
Every number here comes from publicly disclosed reports filed by large institutional LPs — CalPERS, CalSTRS, Washington State Investment Board, and others. These are pension funds managing teachers' and public employees' retirement money, which means they're required by law to disclose what they invest in and how those investments are performing.
We didn't get any of this from the GPs themselves. We just did the PDF parsing so you don't have to.

What You're Looking At

Net IRR — returns after fees and carry. The number that matters.
TVPI — total value to paid-in capital. Every dollar returned plus unrealized value, divided by every dollar invested.
DPI — distributed to paid-in. Cash actually returned to LPs. The only number VCs can't spin.

Vintage year matters enormously when reading these. A 2019 fund and a 2022 fund at the same IRR are having very different lives. We've kept vintage years visible throughout for exactly this reason.

What This Is Not
This is not investment advice. This is not a complete picture of any fund's performance. This is not endorsed by, affiliated with, or even known to any of the GPs listed here.
Reported figures reflect a single LP's position in a fund, at a specific reporting date, under that LP's accounting methodology. Different LPs in the same fund can and do report different numbers for the same vintage. Data is updated quarterly as LPs publish new disclosures — which means there's always some lag.
Use this as a starting point for your own research. Not an ending point for anything.

A Note On Coverage
We cover what's publicly available. That skews toward larger, established funds that institutional LPs have historically backed. If a fund isn't here, it doesn't mean it's performing badly — it likely means none of our source LPs have disclosed a position, or the fund is too recent to have meaningful reported data.
The absence of a fund is data about our sources, not about the fund.

Built because the information was always public. It just needed somewhere to live.
"""


def _empty_funds_df() -> pd.DataFrame:
    base = {}
    for column in REQUIRED_COLUMNS:
        if column in NUMERIC_COLUMNS:
            base[column] = pd.Series(dtype="float64")
        else:
            base[column] = pd.Series(dtype="object")
    return pd.DataFrame(base)


def _safe_divide(numerator, denominator) -> float:
    if pd.isna(denominator) or float(denominator) == 0:
        return float("nan")
    if pd.isna(numerator):
        numerator = 0.0
    return float(numerator) / float(denominator)


def _format_multiple(value: float) -> str:
    return "N/A" if pd.isna(value) else f"{value:.2f}x"


def _format_percent(value: float) -> str:
    return "N/A" if pd.isna(value) else f"{value * 100:.1f}%"


def _get_benchmark(vintage_year) -> Optional[Dict[str, float]]:
    if pd.isna(vintage_year):
        return None
    try:
        return BENCHMARKS.get(int(vintage_year))
    except (TypeError, ValueError):
        return None


def _benchmark_bucket(tvpi: float, benchmark: Optional[Dict[str, float]]) -> Optional[str]:
    if benchmark is None or pd.isna(tvpi):
        return None
    if tvpi >= benchmark["top_quartile_tvpi"]:
        return "top_quartile"
    if tvpi >= benchmark["median_tvpi"]:
        return "above_median"
    return "below_median"


def _calculate_tvpi_percentile(selected_tvpi: float, tvpi_series: pd.Series) -> Optional[int]:
    if pd.isna(selected_tvpi):
        return None

    valid_tvpi = pd.to_numeric(tvpi_series, errors="coerce").dropna()
    if valid_tvpi.empty:
        return None

    percentile = (valid_tvpi <= float(selected_tvpi)).mean() * 100
    percentile_int = int(round(percentile))
    return max(1, min(100, percentile_int))


def _metric_help_text() -> Dict[str, str]:
    return {
        "TVPI": "Total Value to Paid-In: (distributed cash + remaining value) divided by paid-in capital.",
        "DPI": "Distributions to Paid-In: distributed cash divided by paid-in capital.",
        "RVPI": "Residual Value to Paid-In: remaining unrealized value divided by paid-in capital.",
        "IRR": "Internal Rate of Return: annualized net return implied by fund cash flows.",
    }


def _metric_data_label(row: pd.Series) -> str:
    # TODO: Populate `as_of_date` for every fund row in the ingestion pipeline.
    # TODO: Populate `source` for every fund row in the ingestion pipeline.
    as_of_date = row.get("as_of_date")
    source = row.get("source")

    as_of_text = None if pd.isna(as_of_date) else str(as_of_date).strip()
    source_text = None if pd.isna(source) else str(source).strip()

    if as_of_text and source_text:
        return f"as of {as_of_text} · Source: {source_text}"
    return "as-of date unavailable · Source unknown"


def _compute_vintage_quartile(tvpi: float, vintage_year, all_funds_df: pd.DataFrame) -> Tuple[Optional[str], int]:
    if pd.isna(tvpi) or "vintage_year" not in all_funds_df.columns or "TVPI" not in all_funds_df.columns:
        return None, 0

    vintage_series = pd.to_numeric(all_funds_df["vintage_year"], errors="coerce")
    if pd.isna(vintage_year):
        return None, 0

    try:
        vintage_value = float(vintage_year)
    except (TypeError, ValueError):
        return None, 0

    same_vintage_tvpi = pd.to_numeric(
        all_funds_df.loc[vintage_series == vintage_value, "TVPI"],
        errors="coerce",
    ).dropna()

    sample_size = int(len(same_vintage_tvpi))
    if sample_size == 0:
        return None, 0

    percentile = (same_vintage_tvpi <= float(tvpi)).mean()
    if percentile >= 0.75:
        return "Top Quartile", sample_size
    if percentile >= 0.50:
        return "Second Quartile", sample_size
    if percentile >= 0.25:
        return "Third Quartile", sample_size
    return "Bottom Quartile", sample_size


@st.cache_data(show_spinner=False)
def load_data(db_path: str = "openlp.db") -> pd.DataFrame:
    try:
        df = pd.read_csv("data/unified_funds.csv")

        if "capital_contributed" in df.columns and "cash_in" not in df.columns:
            df["cash_in"] = df["capital_contributed"]
        if "capital_distributed" in df.columns and "cash_out" not in df.columns:
            df["cash_out"] = df["capital_distributed"]
        if "nav" in df.columns and "remaining_value" not in df.columns:
            df["remaining_value"] = df["nav"]
    except Exception:
        try:
            with closing(sqlite3.connect(db_path)) as conn:
                df = pd.read_sql("SELECT * FROM funds", conn)
        except Exception:
            return _empty_funds_df()

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            if column in NUMERIC_COLUMNS:
                df[column] = pd.Series(dtype="float64")
            else:
                df[column] = pd.Series(dtype="object")

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


@st.cache_data
def load_vc_master():
    return pd.read_csv("data/vc_fund_master.csv")


@st.cache_data(show_spinner=False)
def load_master_data(master_path: str = MASTER_DATA_PATH) -> pd.DataFrame:
    expected_cols = [
        "canonical_gp",
        "fund_name",
        "vintage_year",
        "fund_category",
        "fund_size_usd_m",
        "firm_aum_usd_b",
        "source",
        "reporting_period",
        "tvpi",
        "dpi",
        "net_irr",
        "irr_meaningful",
    ]

    try:
        df = load_vc_master()
    except Exception:
        return pd.DataFrame(columns=expected_cols + ["net_irr_clean", "irr_meaningful_flag"])

    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.NA

    df["fund_size_usd_m"] = pd.to_numeric(df["fund_size_usd_m"], errors="coerce")
    df["firm_aum_usd_b"] = pd.to_numeric(df["firm_aum_usd_b"], errors="coerce")
    df["tvpi"] = pd.to_numeric(df["tvpi"], errors="coerce")
    df["dpi"] = pd.to_numeric(df["dpi"], errors="coerce")
    df["vintage_year"] = pd.to_numeric(df["vintage_year"], errors="coerce")
    df["net_irr"] = pd.to_numeric(df["net_irr"], errors="coerce")

    calpers_placeholder_mask = (
        df["source"].fillna("").astype(str).str.lower().eq("calpers")
        & df["net_irr"].eq(1.0)
    )
    net_irr_clean = df["net_irr"].mask(calpers_placeholder_mask, pd.NA)

    median_irr = pd.to_numeric(net_irr_clean, errors="coerce").dropna().median()
    if pd.notna(median_irr) and median_irr > 1.5:
        net_irr_clean = pd.to_numeric(net_irr_clean, errors="coerce") / 100.0

    df["net_irr_clean"] = pd.to_numeric(net_irr_clean, errors="coerce")

    meaningful_text = df["irr_meaningful"].fillna(False).astype(str).str.strip().str.lower()
    df["irr_meaningful_flag"] = meaningful_text.isin(["true", "1", "yes", "y"])

    return df


def calculate_metrics(row: pd.Series) -> Tuple[float, float, float]:
    cash_in = row.get("cash_in")
    cash_out = row.get("cash_out")
    remaining_value = row.get("remaining_value")

    cash_out = 0.0 if pd.isna(cash_out) else float(cash_out)
    remaining_value = 0.0 if pd.isna(remaining_value) else float(remaining_value)

    tvpi = _safe_divide(cash_out + remaining_value, cash_in)
    dpi = _safe_divide(cash_out, cash_in)
    rvpi = _safe_divide(remaining_value, cash_in)
    return tvpi, dpi, rvpi


def _add_metric_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        df = df.copy()
        df["TVPI"] = pd.Series(dtype="float64")
        df["DPI"] = pd.Series(dtype="float64")
        df["RVPI"] = pd.Series(dtype="float64")
        return df

    metrics = df.apply(
        lambda row: pd.Series(calculate_metrics(row), index=["TVPI", "DPI", "RVPI"]),
        axis=1,
    )
    return pd.concat([df, metrics], axis=1)


def generate_insight(tvpi: float, dpi: float, vintage_year, all_funds_df: pd.DataFrame) -> str:
    dpi_value = _format_multiple(dpi)
    if pd.isna(dpi):
        sentence_one = "DPI is unavailable, so realized distributions cannot be quantified from reported cash flows."
    else:
        sentence_one = (
            f"DPI is {dpi_value}, indicating investors have received {dpi_value} of realized distributions per 1.0x paid-in capital."
        )

    median_dpi = float("nan")
    if "vintage_year" in all_funds_df.columns and "DPI" in all_funds_df.columns and not pd.isna(vintage_year):
        vintage_series = pd.to_numeric(all_funds_df["vintage_year"], errors="coerce")
        try:
            vintage_value = float(vintage_year)
            median_dpi = pd.to_numeric(
                all_funds_df.loc[vintage_series == vintage_value, "DPI"],
                errors="coerce",
            ).median()
        except (TypeError, ValueError):
            median_dpi = float("nan")

    if pd.isna(tvpi) or tvpi == 0 or pd.isna(dpi):
        realization_mix = "realized versus unrealized mix is not assessable"
        ratio_text = "N/A"
    else:
        ratio = _safe_divide(dpi, tvpi)
        ratio_text = "N/A" if pd.isna(ratio) else f"{ratio:.2f}"
        realization_mix = "returns appear primarily realized" if not pd.isna(ratio) and ratio >= 0.5 else "returns appear primarily unrealized"

    if pd.isna(median_dpi):
        sentence_two = f"Same-vintage median DPI is unavailable, and {realization_mix} based on DPI/TVPI of {ratio_text}."
    else:
        comparison = "above" if not pd.isna(dpi) and dpi > median_dpi else "below"
        if not pd.isna(dpi) and abs(dpi - median_dpi) < 1e-9:
            comparison = "in line with"
        sentence_two = (
            f"Same-vintage median DPI is {_format_multiple(median_dpi)}; this fund is {comparison} that level, "
            f"and {realization_mix} based on DPI/TVPI of {ratio_text}."
        )

    return f"{sentence_one} {sentence_two}"


def render_benchmark_section(vintage_year, tvpi: float, all_tvpi: pd.Series) -> Optional[Dict[str, float]]:
    st.subheader("Benchmark Comparison")

    percentile_rank = _calculate_tvpi_percentile(tvpi, all_tvpi)
    if percentile_rank is None:
        st.write("TVPI percentile is unavailable due to missing or invalid data.")
    else:
        st.write(f"This fund is in the {percentile_rank}th percentile by TVPI.")

    benchmark = _get_benchmark(vintage_year)
    if benchmark is None:
        st.write("No benchmark available for this vintage yet.")
        return None

    try:
        vintage_label = int(vintage_year)
    except (TypeError, ValueError):
        vintage_label = vintage_year

    st.write(f"Vintage {vintage_label} median TVPI: **{benchmark['median_tvpi']}x**")
    st.write(f"Vintage {vintage_label} top quartile TVPI: **{benchmark['top_quartile_tvpi']}x**")

    bucket = _benchmark_bucket(tvpi, benchmark)
    if bucket == "top_quartile":
        st.success("This fund is above top-quartile benchmark.")
    elif bucket == "above_median":
        st.info("This fund is above median benchmark.")
    elif bucket == "below_median":
        st.warning("This fund is below median benchmark.")
    else:
        st.info("Benchmark comparison is unavailable due to missing metric data.")

    return benchmark


def render_charts(row: pd.Series, tvpi: float, benchmark: Optional[Dict[str, float]]) -> None:
    st.subheader("Charts")
    chart_col1, chart_col2 = st.columns(2)

    cash_in = 0.0 if pd.isna(row.get("cash_in")) else float(row.get("cash_in"))
    cash_out = 0.0 if pd.isna(row.get("cash_out")) else float(row.get("cash_out"))
    remaining_value = 0.0 if pd.isna(row.get("remaining_value")) else float(row.get("remaining_value"))

    capital_fig = go.Figure()
    capital_fig.add_bar(name="Cash In", x=["Capital"], y=[cash_in], marker_color="#2C3E50")
    capital_fig.add_bar(name="Cash Out", x=["Capital"], y=[cash_out], marker_color="#18A999")
    capital_fig.add_bar(name="Remaining Value", x=["Capital"], y=[remaining_value], marker_color="#F4B942")
    capital_fig.update_layout(
        barmode="stack",
        height=360,
        template="plotly_white",
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        title="Capital Breakdown",
    )
    chart_col1.plotly_chart(capital_fig, use_container_width=True)

    benchmark_fig = go.Figure()
    if benchmark is None:
        benchmark_fig.add_bar(
            x=["Fund TVPI"],
            y=[0],
            marker_color="#D9D9D9",
            text=["No benchmark"],
            textposition="outside",
        )
        benchmark_fig.update_layout(title="Benchmark Bar Chart")
    else:
        fund_tvpi_value = 0.0 if pd.isna(tvpi) else float(tvpi)
        benchmark_fig.add_bar(
            x=["Fund TVPI", "Median TVPI", "Top Quartile TVPI"],
            y=[fund_tvpi_value, benchmark["median_tvpi"], benchmark["top_quartile_tvpi"]],
            marker_color=["#2F6CAD", "#7AA6D1", "#1D3557"],
        )
        benchmark_fig.update_layout(title="Benchmark Bar Chart")
        if pd.isna(tvpi):
            benchmark_fig.add_annotation(
                text="Fund TVPI unavailable",
                x=0,
                y=0,
                showarrow=False,
                yshift=10,
            )

    benchmark_fig.update_layout(
        height=360,
        template="plotly_white",
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        showlegend=False,
    )
    chart_col2.plotly_chart(benchmark_fig, use_container_width=True)


def _load_resources_table() -> pd.DataFrame:
    required_cols = ["Source", "Type", "Coverage", "Last Updated", "Notes"]

    for path in RESOURCE_METADATA_CANDIDATES:
        if os.path.exists(path):
            try:
                meta_df = pd.read_csv(path)
                if all(col in meta_df.columns for col in required_cols):
                    return meta_df[required_cols]
            except Exception:
                continue

    return pd.DataFrame(
        [
            {
                "Source": "CalPERS",
                "Type": "Public LP disclosure",
                "Coverage": "Private Equity fund performance",
                "Last Updated": "See source file",
                "Notes": "Printer-friendly fund performance table.",
            },
            {
                "Source": "CalSTRS",
                "Type": "Public LP disclosure",
                "Coverage": "Private Equity portfolio performance",
                "Last Updated": "See source file",
                "Notes": "Extracted from annual portfolio report PDF.",
            },
            {
                "Source": "Oregon Treasury",
                "Type": "Public LP disclosure",
                "Coverage": "Private Equity portfolio holdings and performance",
                "Last Updated": "See source file",
                "Notes": "Quarterly performance and holdings PDF.",
            },
            {
                "Source": "WSIB",
                "Type": "Public LP disclosure",
                "Coverage": "Private markets IRR report",
                "Last Updated": "See source file",
                "Notes": "Quarterly WSIB IRR report extraction.",
            },
            {
                "Source": "UTIMCO",
                "Type": "Public LP disclosure",
                "Coverage": "Investment performance summary",
                "Last Updated": "See source file",
                "Notes": "Current extraction quality may be limited.",
            },
            {
                "Source": "PSERS",
                "Type": "Public LP disclosure",
                "Coverage": "Private equity investment performance",
                "Last Updated": "Manual/periodic",
                "Notes": "May require manual PDF retrieval for some periods.",
            },
        ]
    )


def _load_target_firms() -> pd.DataFrame:
    required_cols = ["canonical_gp", "match_pattern", "priority"]
    if not os.path.exists(TARGET_FIRMS_PATH):
        return pd.DataFrame(columns=required_cols)

    try:
        target_df = pd.read_csv(TARGET_FIRMS_PATH)
    except Exception:
        return pd.DataFrame(columns=required_cols)

    if not all(col in target_df.columns for col in required_cols):
        return pd.DataFrame(columns=required_cols)

    target_df = target_df[required_cols].copy()
    target_df["canonical_gp"] = target_df["canonical_gp"].astype(str).str.strip()
    target_df["match_pattern"] = target_df["match_pattern"].astype(str).str.strip().str.lower()
    target_df["priority"] = target_df["priority"].astype(str).str.strip()
    target_df = target_df[(target_df["canonical_gp"] != "") & (target_df["match_pattern"] != "")]
    return target_df


def _match_target_funds(df: pd.DataFrame, target_df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or target_df.empty or "fund_name" not in df.columns:
        return pd.DataFrame(columns=list(df.columns) + ["canonical_gp", "priority"])

    fund_series = df["fund_name"].fillna("").astype(str).str.lower()
    matched_frames = []

    for _, row in target_df.iterrows():
        pattern = row["match_pattern"]
        if not pattern:
            continue

        mask = fund_series.str.contains(pattern, regex=False, na=False)
        if not mask.any():
            continue

        matched = df.loc[mask].copy()
        matched["canonical_gp"] = row["canonical_gp"]
        matched["priority"] = row["priority"]
        matched_frames.append(matched)

    if not matched_frames:
        return pd.DataFrame(columns=list(df.columns) + ["canonical_gp", "priority"])

    matched_df = pd.concat(matched_frames, ignore_index=True)

    dedup_candidates = ["canonical_gp", "fund_name", "vintage_year", "source", "as_of_date"]
    dedup_subset = [col for col in dedup_candidates if col in matched_df.columns]
    if dedup_subset:
        matched_df = matched_df.drop_duplicates(subset=dedup_subset, keep="first")

    return matched_df


def _roman_to_int(token: str) -> Optional[int]:
    if not token:
        return None
    token = token.upper()
    roman_values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    if any(ch not in roman_values for ch in token):
        return None
    total = 0
    prev = 0
    for ch in reversed(token):
        val = roman_values[ch]
        if val < prev:
            total -= val
        else:
            total += val
            prev = val
    return total if total > 0 else None


def _classify_fund_family(fund_name: str, canonical_gp: str) -> Tuple[str, int]:
    fund_text = "" if pd.isna(fund_name) else str(fund_name)
    gp_text = "" if pd.isna(canonical_gp) else str(canonical_gp)

    stripped = fund_text
    if gp_text:
        stripped = re.sub(re.escape(gp_text), "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    stripped_lower = stripped.lower()

    family = "Core Venture"
    for keyword, label in FAMILY_KEYWORDS.items():
        if keyword in stripped_lower:
            family = label
            break

    order_signal = 9999
    trailing_num_match = re.search(r"(\d+)\s*$", stripped)
    if trailing_num_match:
        try:
            order_signal = int(trailing_num_match.group(1))
        except ValueError:
            order_signal = 9999
    else:
        roman_matches = re.findall(r"\b[MCDLXVI]+\b", stripped.upper())
        for token in reversed(roman_matches):
            roman_value = _roman_to_int(token)
            if roman_value is not None:
                order_signal = roman_value
                break

    return family, order_signal


def _summarize_gp_funds(gp_funds: pd.DataFrame, canonical_gp: str) -> pd.DataFrame:
    if gp_funds.empty or "fund_name" not in gp_funds.columns:
        return pd.DataFrame(columns=["fund_name", "vintage_year", "source_count", "TVPI", "DPI", "fund_family", "order_signal"])

    rows = []
    grouped = gp_funds.groupby("fund_name", dropna=False)
    for fund_name, group in grouped:
        source_count = int(group["source"].dropna().astype(str).nunique()) if "source" in group.columns else 0
        vintage_series = pd.to_numeric(group["vintage_year"], errors="coerce").dropna() if "vintage_year" in group.columns else pd.Series(dtype="float64")
        tvpi_series = pd.to_numeric(group["TVPI"], errors="coerce").dropna() if "TVPI" in group.columns else pd.Series(dtype="float64")
        dpi_series = pd.to_numeric(group["DPI"], errors="coerce").dropna() if "DPI" in group.columns else pd.Series(dtype="float64")

        vintage_value = vintage_series.iloc[0] if not vintage_series.empty else float("nan")
        tvpi_value = float(tvpi_series.median()) if not tvpi_series.empty else float("nan")
        dpi_value = float(dpi_series.median()) if not dpi_series.empty else float("nan")

        family, order_signal = _classify_fund_family(fund_name, canonical_gp)
        rows.append(
            {
                "fund_name": fund_name,
                "vintage_year": vintage_value,
                "source_count": source_count,
                "TVPI": tvpi_value,
                "DPI": dpi_value,
                "fund_family": family,
                "order_signal": order_signal,
            }
        )

    summary_df = pd.DataFrame(rows)
    if summary_df.empty:
        return summary_df

    family_sort_order = {"Core Venture": 0, "Growth": 1, "Opportunity": 2, "Seed": 3, "Select": 4, "Sidecar": 5, "Continuation": 6}
    summary_df["family_sort"] = summary_df["fund_family"].map(family_sort_order).fillna(99)
    summary_df = summary_df.sort_values(["family_sort", "order_signal", "fund_name"], ascending=[True, True, True]).reset_index(drop=True)
    return summary_df


def _select_best_fund_row(gp_funds: pd.DataFrame, selected_fund_name: str) -> Optional[pd.Series]:
    if gp_funds.empty or "fund_name" not in gp_funds.columns:
        return None

    selected = gp_funds[gp_funds["fund_name"].astype(str) == str(selected_fund_name)].copy()
    if selected.empty:
        return None

    completeness_cols = [col for col in ["cash_in", "cash_out", "remaining_value", "net_irr"] if col in selected.columns]
    if completeness_cols:
        selected["completeness"] = selected[completeness_cols].notna().sum(axis=1)
    else:
        selected["completeness"] = 0

    if "as_of_date" in selected.columns:
        selected["as_of_sort"] = pd.to_datetime(selected["as_of_date"], errors="coerce")
    else:
        selected["as_of_sort"] = pd.NaT

    selected = selected.sort_values(["as_of_sort", "completeness"], ascending=[False, False], na_position="last")
    return selected.iloc[0]


def _build_coverage_table(df: pd.DataFrame) -> pd.DataFrame:
    output_columns = ["canonical_gp", "priority", "matching_funds", "sources", "status"]
    target_df = _load_target_firms()
    if target_df.empty:
        return pd.DataFrame(columns=output_columns)

    matched_df = _match_target_funds(df, target_df)

    rows = []
    gp_reference = target_df.groupby("canonical_gp", dropna=False)["priority"].first()
    for canonical_gp, priority in gp_reference.items():
        gp_matches = matched_df[matched_df["canonical_gp"] == canonical_gp] if not matched_df.empty else matched_df

        matching_funds = (
            gp_matches["fund_name"].fillna("UNKNOWN_FUND").astype(str).str.strip().replace("", "UNKNOWN_FUND").nunique()
            if "fund_name" in gp_matches.columns
            else 0
        )
        sources = (
            ", ".join(sorted(gp_matches["source"].dropna().astype(str).unique().tolist()))
            if "source" in gp_matches.columns and not gp_matches.empty
            else ""
        )

        if matching_funds >= 3:
            status = "Covered"
        elif matching_funds >= 1:
            status = "Partial"
        else:
            status = "Missing"

        rows.append(
            {
                "canonical_gp": canonical_gp,
                "priority": priority,
                "matching_funds": int(matching_funds),
                "sources": sources,
                "status": status,
            }
        )

    coverage_df = pd.DataFrame(rows)
    if coverage_df.empty:
        return pd.DataFrame(columns=output_columns)

    status_order = {"Covered": 0, "Partial": 1, "Missing": 2}
    coverage_df["status_sort"] = coverage_df["status"].map(status_order).fillna(3)
    coverage_df = coverage_df.sort_values(["status_sort", "canonical_gp"], ascending=[True, True]).drop(columns=["status_sort"])
    return coverage_df[output_columns]


def _render_intro_banner() -> None:
    st.markdown(
        """
        <div style="border:1px solid #E5E7EB;border-radius:6px;padding:12px 14px;margin:4px 0 12px 0;">
          <div style="font-weight:600;margin-bottom:6px;">Public VC Fund Performance Database</div>
          <div style="margin-bottom:4px;">This is a free searchable database of VC fund performance built from public pension LP disclosures.</div>
          <div>Source fields are shown where available to keep disclosure provenance transparent.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_overview_metrics(df: pd.DataFrame) -> None:
    total_funds = int(len(df))
    funds_with_dpi = int(pd.to_numeric(df["DPI"], errors="coerce").notna().sum()) if "DPI" in df.columns else 0
    target_df = _load_target_firms()
    matched_df = _match_target_funds(df, target_df) if not target_df.empty else pd.DataFrame()
    target_firms_covered = int(matched_df["canonical_gp"].dropna().astype(str).nunique()) if not matched_df.empty else 0
    data_sources_count = int(df["source"].dropna().astype(str).nunique()) if "source" in df.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Funds", f"{total_funds}")
    c2.metric("Funds with DPI available", f"{funds_with_dpi}")
    c3.metric("Target Firms Covered", f"{target_firms_covered}")
    c4.metric("Data Sources", f"{data_sources_count}")


def _render_selected_fund_analysis(selected_row: pd.Series, all_funds_df: pd.DataFrame) -> None:
    tvpi, dpi, rvpi = calculate_metrics(selected_row)
    vintage_year = selected_row.get("vintage_year")
    all_tvpi = all_funds_df["TVPI"] if "TVPI" in all_funds_df.columns else pd.Series(dtype="float64")
    metric_help = _metric_help_text()
    metadata_text = _metric_data_label(selected_row)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TVPI", _format_multiple(tvpi), help=metric_help["TVPI"])
    c2.metric("DPI", _format_multiple(dpi), help=metric_help["DPI"])
    c3.metric("RVPI", _format_multiple(rvpi), help=metric_help["RVPI"])
    c4.metric("IRR", _format_percent(selected_row.get("net_irr")), help=metric_help["IRR"])
    c1.caption(metadata_text)
    c2.caption(metadata_text)
    c3.caption(metadata_text)
    c4.caption(metadata_text)

    quartile_label, sample_size = _compute_vintage_quartile(tvpi, vintage_year, all_funds_df)
    try:
        vintage_label = int(float(vintage_year))
    except (TypeError, ValueError):
        vintage_label = "unknown"

    st.write(f"Quartile: {quartile_label if quartile_label else 'Unavailable'}")
    st.caption(f"Quartile based on {sample_size} funds in our database from {vintage_label} vintage.")

    benchmark = render_benchmark_section(vintage_year, tvpi, all_tvpi)
    render_charts(selected_row, tvpi, benchmark)

    st.subheader("Insight")
    st.write(generate_insight(tvpi=tvpi, dpi=dpi, vintage_year=vintage_year, all_funds_df=all_funds_df))


def _render_callout_card(headline: str, body: str) -> None:
    st.markdown(
        f"""
<div style="border:1px solid #E5E7EB;border-radius:6px;
            padding:12px 14px;min-height:160px;">
  <div style="font-weight:600;margin-bottom:6px;">{headline}</div>
  <div style="font-size:0.85rem;color:#4B5563;">{body}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_insights_page(master_df: pd.DataFrame) -> None:
    st.header("INSIGHTS")
    st.caption(
        "Performance analysis across leading VC and growth firms. Based on public LP disclosures. "
        "Only funds with meaningful reported data are included in performance charts."
    )

    if master_df.empty:
        st.info("vc_fund_master.csv not found in data/.")
        return

    all_df = master_df.copy()
    perf_df = all_df[all_df["irr_meaningful_flag"]].copy()

    callouts = [
        (
            "The DPI Drought",
            "Across all funds in this dataset with vintage 2017 or later, aggregate DPI is effectively zero. "
            "No distributions of scale have been returned. The entire asset class is sitting on paper gains.",
        ),
        (
            "Mayfield is the Outlier",
            "Mayfield XIV (2013) is the single best-performing fund with public LP data in this dataset: "
            "3.8x TVPI, 2.75x DPI, 19.8% IRR. For a $200M fund, this is exceptional performance. "
            "Mayfield XV and XVI show the firm's consistency isn't an accident.",
        ),
        (
            "Lightspeed's 2022 Cohort",
            "The XIV-A/B (early) and Opportunity II (crossover) funds are tracking above 16–23% IRR at 3 years. "
            "If these hold, they will be among the better 2022 vintage funds across any publicly disclosed dataset.",
        ),
        (
            "China Risk",
            "HongShan's Seed III and Venture IX (both 2022) are posting negative IRRs (-9.6% and -8.5%). "
            "Both reflect the Chinese tech regulatory environment post-2021. "
            "HongShan spun out from Sequoia China in 2023 and is now fully independent.",
        ),
        (
            "Megafund vs Boutique",
            "There's a clear structural split emerging: Lightspeed ($40B AUM), Sequoia ($56B), and GC ($32B) are now global multi-strategy "
            "platforms. Mayfield ($3B) and Khosla ($15B) remain focused. The irony: our best-performing fund data comes from the boutique (Mayfield).",
        ),
    ]
    card_cols = st.columns(5)
    for col, (headline, body) in zip(card_cols, callouts):
        with col:
            _render_callout_card(headline, body)

    # Chart 1 — IRR by Vintage (Scatter)
    st.subheader("Net IRR by Vintage Year")
    irr_scatter_df = perf_df.dropna(subset=["vintage_year", "net_irr_clean"]).copy()
    if irr_scatter_df.empty:
        st.info("No meaningful IRR observations are available for the vintage scatter chart.")
    else:
        fig_irr = go.Figure()
        for gp, gp_df in irr_scatter_df.groupby("canonical_gp", dropna=False):
            size_raw = pd.to_numeric(gp_df["fund_size_usd_m"], errors="coerce")
            if size_raw.notna().any():
                size_rank = size_raw.rank(pct=True).fillna(0.5)
                marker_size = 10 + (size_rank * 24)
            else:
                marker_size = pd.Series([14] * len(gp_df), index=gp_df.index)

            fig_irr.add_trace(
                go.Scatter(
                    x=gp_df["vintage_year"],
                    y=gp_df["net_irr_clean"] * 100.0,
                    mode="markers",
                    name=str(gp),
                    marker={"size": marker_size, "opacity": 0.8},
                    customdata=gp_df[["fund_name", "source", "fund_size_usd_m"]],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "GP: " + str(gp) + "<br>"
                        "Vintage: %{x}<br>"
                        "Net IRR: %{y:.1f}%<br>"
                        "Source: %{customdata[1]}<br>"
                        "Fund Size ($M): %{customdata[2]:,.0f}<extra></extra>"
                    ),
                )
            )

        fig_irr.add_shape(
            type="line",
            xref="paper",
            yref="y",
            x0=0,
            x1=1,
            y0=10,
            y1=10,
            line={"color": "#9CA3AF", "width": 1.5, "dash": "dash"},
        )
        fig_irr.add_shape(
            type="line",
            xref="paper",
            yref="y",
            x0=0,
            x1=1,
            y0=20,
            y1=20,
            line={"color": "#16A34A", "width": 1.5, "dash": "dash"},
        )
        fig_irr.add_annotation(xref="paper", yref="y", x=1, y=10, text="Institutional benchmark", showarrow=False, xanchor="left")
        fig_irr.add_annotation(xref="paper", yref="y", x=1, y=20, text="Top quartile VC", showarrow=False, xanchor="left")
        fig_irr.update_layout(
            title="Net IRR by Vintage Year",
            template="plotly_white",
            margin={"l": 10, "r": 10, "t": 40, "b": 10},
            xaxis_title="Vintage Year",
            yaxis_title="Net IRR (%)",
        )
        st.plotly_chart(fig_irr, use_container_width=True)

    # Chart 2 — TVPI vs DPI (Realization Chart)
    st.subheader("TVPI vs DPI — Realization Chart")
    realization_df = perf_df.dropna(subset=["dpi", "tvpi"]).copy()
    if realization_df.empty:
        st.info("No meaningful TVPI/DPI observations are available for the realization chart.")
    else:
        fig_realization = go.Figure()
        for gp, gp_df in realization_df.groupby("canonical_gp", dropna=False):
            size_raw = pd.to_numeric(gp_df["fund_size_usd_m"], errors="coerce")
            if size_raw.notna().any():
                size_rank = size_raw.rank(pct=True).fillna(0.5)
                marker_size = 10 + (size_rank * 24)
            else:
                marker_size = pd.Series([14] * len(gp_df), index=gp_df.index)

            fig_realization.add_trace(
                go.Scatter(
                    x=gp_df["dpi"],
                    y=gp_df["tvpi"],
                    mode="markers",
                    name=str(gp),
                    marker={"size": marker_size, "opacity": 0.8},
                    customdata=gp_df[["fund_name", "vintage_year", "tvpi", "dpi", "net_irr_clean", "source"]],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Vintage: %{customdata[1]}<br>"
                        "TVPI: %{customdata[2]:.2f}x<br>"
                        "DPI: %{customdata[3]:.2f}x<br>"
                        "Net IRR: %{customdata[4]:.1%}<br>"
                        "Source: %{customdata[5]}<extra></extra>"
                    ),
                )
            )

        max_axis = max(
            4.0,
            float(pd.to_numeric(realization_df["tvpi"], errors="coerce").max(skipna=True) or 0),
            float(pd.to_numeric(realization_df["dpi"], errors="coerce").max(skipna=True) or 0),
        )
        fig_realization.add_shape(
            type="line",
            x0=0,
            y0=0,
            x1=max_axis,
            y1=max_axis,
            line={"color": "#9CA3AF", "width": 1.5, "dash": "dash"},
        )
        fig_realization.add_annotation(x=max_axis, y=max_axis, text="Fully realized", showarrow=False, xanchor="left", yanchor="bottom")
        fig_realization.update_layout(
            title="TVPI vs DPI — Realization Chart",
            template="plotly_white",
            margin={"l": 10, "r": 10, "t": 40, "b": 10},
            xaxis_title="DPI",
            yaxis_title="TVPI",
        )
        st.plotly_chart(fig_realization, use_container_width=True)

    # Chart 3 — Fund Count by Strategy per GP
    st.subheader("Strategy Mix by GP")
    strategy_df = all_df.dropna(subset=["canonical_gp"]).copy()
    if strategy_df.empty:
        st.info("No firm/category data is available for strategy mix.")
    else:
        mix = (
            strategy_df.groupby(["canonical_gp", "fund_category"], dropna=False)
            .size()
            .reset_index(name="fund_count")
        )
        gp_order = sorted(mix["canonical_gp"].astype(str).unique().tolist())
        categories = list(CATEGORY_COLORS.keys())
        extra_categories = [c for c in sorted(mix["fund_category"].dropna().astype(str).unique().tolist()) if c not in categories]
        categories.extend(extra_categories)

        fig_mix = go.Figure()
        for category in categories:
            cat_rows = mix[mix["fund_category"].astype(str) == category]
            y_values = []
            for gp in gp_order:
                val = cat_rows.loc[cat_rows["canonical_gp"].astype(str) == gp, "fund_count"]
                y_values.append(int(val.iloc[0]) if not val.empty else 0)
            fig_mix.add_trace(
                go.Bar(
                    x=gp_order,
                    y=y_values,
                    name=category,
                    marker_color=CATEGORY_COLORS.get(category, "#6B7280"),
                )
            )

        fig_mix.update_layout(
            title="Strategy Mix by GP",
            barmode="stack",
            template="plotly_white",
            margin={"l": 10, "r": 10, "t": 40, "b": 10},
            xaxis_title="Canonical GP",
            yaxis_title="Fund Count",
        )
        st.plotly_chart(fig_mix, use_container_width=True)

    # Chart 4 — IRR Trend per GP
    st.subheader("IRR Trajectory Across Fund Cycles")
    trend_base = perf_df.dropna(subset=["vintage_year", "net_irr_clean"]).copy()
    if trend_base.empty:
        st.info("No meaningful IRR observations are available for trend analysis.")
    else:
        gp_counts = trend_base.groupby("canonical_gp")["fund_name"].nunique()
        eligible_gps = gp_counts[gp_counts >= 3].index.tolist()
        trend_df = trend_base[trend_base["canonical_gp"].isin(eligible_gps)].copy()

        if trend_df.empty:
            st.info("No GP has at least three meaningful funds for trend analysis.")
        else:
            fig_trend = go.Figure()
            for gp, gp_df in trend_df.groupby("canonical_gp", dropna=False):
                gp_df = gp_df.sort_values("vintage_year", ascending=True)
                fig_trend.add_trace(
                    go.Scatter(
                        x=gp_df["vintage_year"],
                        y=gp_df["net_irr_clean"] * 100.0,
                        mode="lines+markers",
                        name=str(gp),
                        customdata=gp_df[["fund_name"]],
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>"
                            "Vintage: %{x}<br>"
                            "Net IRR: %{y:.1f}%<extra></extra>"
                        ),
                    )
                )

            fig_trend.update_layout(
                title="IRR Trajectory Across Fund Cycles",
                template="plotly_white",
                margin={"l": 10, "r": 10, "t": 40, "b": 10},
                xaxis_title="Vintage Year",
                yaxis_title="Net IRR (%)",
            )
            st.plotly_chart(fig_trend, use_container_width=True)


def _render_overview_page(df: pd.DataFrame) -> None:
    st.title("Show Me the DPI")
    _render_intro_banner()
    _render_overview_metrics(df)


def _render_fund_database_page(df: pd.DataFrame) -> None:
    st.header("Fund Database")
    st.caption("Raw LP-reported fund performance records with source and vintage filters.")

    filtered_df = df.copy()

    if "source" in filtered_df.columns:
        source_options = ["All"] + sorted(filtered_df["source"].dropna().astype(str).unique().tolist())
        selected_source = st.selectbox("Source", options=source_options, index=0, key="database_source")
        if selected_source != "All":
            filtered_df = filtered_df[filtered_df["source"].astype(str) == selected_source]

    if "vintage_year" in filtered_df.columns:
        vintages = pd.to_numeric(filtered_df["vintage_year"], errors="coerce").dropna().astype(int)
        vintage_options = ["All"] + sorted(vintages.unique().tolist())
        selected_vintage = st.selectbox("Vintage Year", options=vintage_options, index=0, key="database_vintage")
        if selected_vintage != "All":
            filtered_df = filtered_df[pd.to_numeric(filtered_df["vintage_year"], errors="coerce") == int(selected_vintage)]

    table_columns = ["fund_name", "gp_name", "vintage_year", "TVPI", "DPI", "RVPI", "net_irr", "source", "as_of_date"]
    st.dataframe(filtered_df.reindex(columns=table_columns), use_container_width=True)

    if filtered_df.empty:
        st.info("No funds match the current filters.")


def _render_firms_page(master_df: pd.DataFrame) -> None:
    st.header("Firms & Fund Families")
    st.caption("Curated VC fund-family view driven by vc_fund_master.csv.")

    if master_df.empty:
        st.info("No firms data available. Add data/vc_fund_master.csv to enable this view.")
        return

    firms_df = master_df.copy()
    for col in ["canonical_gp", "fund_name", "fund_category", "source", "reporting_period"]:
        if col not in firms_df.columns:
            firms_df[col] = pd.NA
    for col in ["vintage_year", "tvpi", "dpi", "net_irr"]:
        if col not in firms_df.columns:
            firms_df[col] = pd.NA
        firms_df[col] = pd.to_numeric(firms_df[col], errors="coerce")

    gp_options = sorted(
        firms_df["canonical_gp"].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique().tolist()
    )
    if not gp_options:
        st.info("No canonical GP values are available in vc_fund_master.csv.")
        return

    selected_gp = st.selectbox("Select Canonical GP", gp_options, index=0, key="firm_selected_gp")
    gp_funds = firms_df[firms_df["canonical_gp"].astype(str).str.strip() == selected_gp].copy()

    if gp_funds.empty:
        st.info("No funds available for this firm.")
        return

    family_map = {
        "Venture": "Core Venture",
        "Growth": "Growth",
        "Opportunities": "Opportunity",
        "Company Creation": "Company Creation",
        "PE": "Other",
    }
    gp_funds["fund_family"] = gp_funds["fund_category"].astype(str).map(family_map).fillna("Other")
    gp_funds["fund_name"] = gp_funds["fund_name"].fillna("UNKNOWN_FUND").astype(str).str.strip()
    gp_funds["source"] = gp_funds["source"].fillna("Unknown").astype(str).str.strip()
    gp_funds = gp_funds.sort_values(["fund_family", "vintage_year", "fund_name"], ascending=[True, True, True])

    total_fund_count = int(gp_funds["fund_name"].nunique())
    source_count = int(gp_funds["source"].dropna().astype(str).nunique()) if "source" in gp_funds.columns else 0

    if total_fund_count >= 5 or source_count >= 2:
        coverage_strength = "Strong"
    elif total_fund_count >= 2:
        coverage_strength = "Moderate"
    else:
        coverage_strength = "Thin"

    st.write(f"Coverage: {coverage_strength} ({total_fund_count} funds across {source_count} LP sources).")

    st.subheader("Fund Families")
    family_order = ["Core Venture", "Growth", "Opportunity", "Company Creation", "Other"]
    for family in family_order:
        family_df = gp_funds[gp_funds["fund_family"] == family].copy()
        if family_df.empty:
            continue

        display_df = pd.DataFrame(
            {
                "fund_name": family_df["fund_name"].astype(str),
                "vintage_year": family_df["vintage_year"].apply(lambda x: "N/A" if pd.isna(x) else str(int(x))),
                "source": family_df["source"].astype(str),
                "tvpi": family_df["tvpi"].apply(_format_multiple),
                "dpi": family_df["dpi"].apply(_format_multiple),
            }
        )
        with st.expander(family, expanded=True):
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    fund_options = sorted(gp_funds["fund_name"].dropna().astype(str).unique().tolist())
    selected_fund_name = st.selectbox("Select Fund", fund_options, index=0, key="firm_selected_fund")
    analysis_df = gp_funds.copy()
    analysis_df["cash_in"] = pd.Series([1.0] * len(analysis_df), index=analysis_df.index)
    analysis_df["cash_out"] = pd.to_numeric(analysis_df["dpi"], errors="coerce") * analysis_df["cash_in"]
    analysis_df["remaining_value"] = pd.to_numeric(analysis_df["tvpi"], errors="coerce") - pd.to_numeric(analysis_df["dpi"], errors="coerce")
    analysis_df["total_value"] = pd.to_numeric(analysis_df["tvpi"], errors="coerce") * analysis_df["cash_in"]
    analysis_df["as_of_date"] = analysis_df.get("reporting_period", pd.NA)
    analysis_df["TVPI"] = pd.to_numeric(analysis_df["tvpi"], errors="coerce")
    analysis_df["DPI"] = pd.to_numeric(analysis_df["dpi"], errors="coerce")
    analysis_df["RVPI"] = analysis_df["TVPI"] - analysis_df["DPI"]

    selected_row = _select_best_fund_row(analysis_df, selected_fund_name)
    if selected_row is None:
        st.info("Selected fund data is unavailable.")
        return

    st.subheader(str(selected_fund_name))
    st.caption(f"Canonical GP: {selected_gp}")
    _render_selected_fund_analysis(selected_row, analysis_df)


def _render_sources_page(df: pd.DataFrame) -> None:
    del df  # page-level argument kept for a consistent call signature
    st.header("Sources")
    st.caption("Data provenance and disclosure context.")
    st.markdown(
        """
- LP disclosures are not synchronized; reporting dates vary by institution and period.
- Different LPs can report different values for the same underlying fund and vintage.
- Figures in this app reflect LP-reported perspectives rather than GP-reported official records.
        """
    )
    resources_df = _load_resources_table()
    st.dataframe(resources_df, use_container_width=True)


def _render_about_page() -> None:
    st.header("About This")
    st.markdown(ABOUT_COPY)


def main() -> None:
    df = _add_metric_columns(load_data())
    master_df = load_master_data()

    st.sidebar.header("Navigation")
    section = st.sidebar.selectbox(
        "Section",
        ["OVERVIEW", "FUND DATABASE", "FIRMS & FUND FAMILIES", "INSIGHTS", "SOURCES", "ABOUT"],
        index=0,
    )

    if section == "OVERVIEW":
        _render_overview_page(df)
    elif section == "FUND DATABASE":
        _render_fund_database_page(df)
    elif section == "FIRMS & FUND FAMILIES":
        _render_firms_page(master_df)
    elif section == "INSIGHTS":
        _render_insights_page(master_df)
    elif section == "SOURCES":
        _render_sources_page(df)
    else:
        _render_about_page()


if __name__ == "__main__":
    main()
