import sqlite3
from contextlib import closing
from typing import Dict, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="Show Me the DPI", layout="wide")
st.title("Show Me the DPI")

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


@st.cache_data(show_spinner=False)
def load_data(db_path: str = "openlp.db") -> pd.DataFrame:
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


def generate_insight(dpi: float, rvpi: float, tvpi: float, vintage_year) -> str:
    insight_parts = []

    if pd.isna(dpi):
        insight_parts.append("DPI is unavailable because required cash flow data is missing.")
    elif dpi < 0.5:
        insight_parts.append("Low DPI suggests most value is still unrealized.")
    elif dpi > 1.0:
        insight_parts.append("Strong DPI indicates meaningful cash has already been returned to LPs.")
    else:
        insight_parts.append("DPI suggests a balanced mix of realized and unrealized value.")

    if pd.isna(rvpi) or pd.isna(dpi):
        insight_parts.append("Realization mix cannot be assessed due to missing data.")
    elif rvpi > dpi:
        insight_parts.append(
            "Performance currently relies more on unrealized portfolio value than distributions."
        )
    else:
        insight_parts.append("Realized distributions are contributing significantly to returns.")

    benchmark = _get_benchmark(vintage_year)
    bucket = _benchmark_bucket(tvpi, benchmark)
    if bucket == "top_quartile":
        insight_parts.append("TVPI sits above the top-quartile benchmark for this vintage.")
    elif bucket == "above_median":
        insight_parts.append("TVPI is above median compared with peers from the same vintage.")
    elif bucket == "below_median":
        insight_parts.append("TVPI trails the median benchmark for this vintage.")

    return " ".join(insight_parts) if insight_parts else "Not enough data to generate an insight yet."


def render_benchmark_section(
    vintage_year, tvpi: float, all_tvpi: pd.Series
) -> Optional[Dict[str, float]]:
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


def main() -> None:
    df = _add_metric_columns(load_data())

    # Sidebar filters
    st.sidebar.header("Filters")
    search_term = st.sidebar.text_input("Search fund")

    filtered_df = df.copy()
    if search_term:
        filtered_df = filtered_df[
            filtered_df["fund_name"].astype(str).str.contains(search_term, case=False, na=False)
        ]

    # Fund table
    st.subheader("Fund Database")
    table_columns = ["fund_name", "gp_name", "vintage_year", "TVPI", "DPI", "net_irr"]
    st.dataframe(filtered_df[table_columns], use_container_width=True)

    if filtered_df.empty:
        st.info("No funds match the current filters.")
        return

    # Fund detail view
    st.subheader("Fund Detail")
    fund_options = filtered_df["fund_name"].dropna().astype(str).tolist()
    if not fund_options:
        st.info("No fund names are available in the current dataset.")
        return

    selected_fund = st.selectbox("Select Fund", fund_options)
    selected_rows = filtered_df[filtered_df["fund_name"].astype(str) == selected_fund]
    if selected_rows.empty:
        st.info("Selected fund data is unavailable.")
        return

    selected_row = selected_rows.iloc[0]
    tvpi, dpi, rvpi = calculate_metrics(selected_row)

    # Metrics cards (TVPI, DPI, RVPI, IRR)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TVPI", _format_multiple(tvpi))
    c2.metric("DPI", _format_multiple(dpi))
    c3.metric("RVPI", _format_multiple(rvpi))
    c4.metric("Net IRR", _format_percent(selected_row.get("net_irr")))

    # Insight box
    st.subheader("Insight")
    st.info(generate_insight(dpi, rvpi, tvpi, selected_row.get("vintage_year")))

    # Benchmark comparison
    benchmark = render_benchmark_section(selected_row.get("vintage_year"), tvpi, df["TVPI"])

    # Charts and benchmark bar chart
    render_charts(selected_row, tvpi, benchmark)


if __name__ == "__main__":
    main()
