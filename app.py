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
        sentence_one = "DPI is unavailable, so realized distributions cannot be quantified from the reported cash flows."
    else:
        sentence_one = (
            f"DPI is {dpi_value}, which means investors have received {dpi_value} of realized distributions "
            "for each 1.0x of paid-in capital."
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
        realization_mix = "the realized versus unrealized split cannot be assessed"
        ratio_text = "N/A"
    else:
        ratio = _safe_divide(dpi, tvpi)
        ratio_text = "N/A" if pd.isna(ratio) else f"{ratio:.2f}"
        realization_mix = (
            "returns appear primarily realized"
            if not pd.isna(ratio) and ratio >= 0.5
            else "returns appear primarily unrealized"
        )

    if pd.isna(median_dpi):
        sentence_two = (
            f"Median DPI for the same vintage is unavailable in this database, and {realization_mix} "
            f"based on a DPI/TVPI ratio of {ratio_text}."
        )
    else:
        comparison = "above" if not pd.isna(dpi) and dpi > median_dpi else "below"
        if not pd.isna(dpi) and abs(dpi - median_dpi) < 1e-9:
            comparison = "in line with"
        sentence_two = (
            f"Median DPI for the same vintage is {_format_multiple(median_dpi)}; this fund is {comparison} "
            f"that level, and {realization_mix} based on a DPI/TVPI ratio of {ratio_text}."
        )

    return f"{sentence_one} {sentence_two}"


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


def _render_fund_database_tab(filtered_df: pd.DataFrame) -> None:
    st.subheader("Fund Database")
    table_columns = ["fund_name", "gp_name", "vintage_year", "TVPI", "DPI", "net_irr"]
    st.dataframe(filtered_df.reindex(columns=table_columns), use_container_width=True)

    if filtered_df.empty:
        st.info("No funds match the current filters.")


def _render_fund_detail_tab(filtered_df: pd.DataFrame, all_funds_df: pd.DataFrame) -> None:
    st.subheader("Fund Detail")
    st.caption("Start by selecting a fund below.")

    if filtered_df.empty:
        st.info("No funds available for detail view under current filters.")
        return

    if "fund_name" not in filtered_df.columns:
        st.info("Fund names are unavailable in this dataset.")
        return

    fund_options = filtered_df["fund_name"].dropna().astype(str).tolist()
    if not fund_options:
        st.info("No fund names are available in the current dataset.")
        return

    selected_fund = st.selectbox(
        "Select Fund",
        fund_options,
        index=0,
        key="detail_selected_fund",
    )
    selected_rows = filtered_df[filtered_df["fund_name"].astype(str) == selected_fund]
    if selected_rows.empty:
        st.info("Selected fund data is unavailable.")
        return

    selected_row = selected_rows.iloc[0]
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
    st.caption(
        f"Quartile based on {sample_size} funds in our database from {vintage_label} vintage."
    )

    benchmark = render_benchmark_section(
        vintage_year,
        tvpi,
        all_tvpi,
    )
    render_charts(selected_row, tvpi, benchmark)

    st.subheader("Insight")
    st.info(generate_insight(tvpi=tvpi, dpi=dpi, vintage_year=vintage_year, all_funds_df=all_funds_df))


def _render_calculator_tab() -> None:
    st.subheader("Calculator")
    st.info("Performance calculator coming soon.")


def _render_summary_row(df: pd.DataFrame) -> None:
    fund_count = int(len(df))
    gp_count = int(df["gp_name"].dropna().nunique()) if "gp_name" in df.columns else 0
    median_tvpi = pd.to_numeric(df["TVPI"], errors="coerce").median() if "TVPI" in df.columns else float("nan")
    median_vintage = (
        pd.to_numeric(df["vintage_year"], errors="coerce").median()
        if "vintage_year" in df.columns
        else float("nan")
    )
    median_vintage_display = "N/A" if pd.isna(median_vintage) else f"{int(round(median_vintage))}"

    metric_help = _metric_help_text()
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Funds", f"{fund_count}")
    s2.metric("Unique GPs", f"{gp_count}")
    s3.metric("Median TVPI", _format_multiple(median_tvpi), help=metric_help["TVPI"])
    s4.metric("Median Vintage Year", median_vintage_display)


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


def _render_about_data() -> None:
    with st.expander("About the Data"):
        st.write(
            "This database is assembled from public pension LP disclosures and reflects only funds that appear in "
            "those public records. Reporting dates and valuation points can vary by LP, so as-of periods are not "
            "fully aligned across funds. Results may also reflect survivorship bias because disclosure coverage is "
            "not uniform across managers or vintages. Quartile and percentile statistics are calculated only from "
            "funds currently present in this database, not from the full market."
        )


def main() -> None:
    df = _add_metric_columns(load_data())

    # Sidebar filters
    st.sidebar.header("Filters")
    search_term = st.sidebar.text_input("Search fund")

    filtered_df = df.copy()
    if search_term and "fund_name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["fund_name"].astype(str).str.contains(search_term, case=False, na=False)
        ]

    _render_intro_banner()
    _render_summary_row(df)

    tab1, tab2, tab3 = st.tabs(["Database", "Fund Detail", "Calculator"])

    with tab1:
        _render_fund_database_tab(filtered_df)

    with tab2:
        _render_fund_detail_tab(filtered_df, df)

    with tab3:
        _render_calculator_tab()

    _render_about_data()


if __name__ == "__main__":
    main()
