import sqlite3
from contextlib import closing
import math
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


def _distribution_weights(fund_life_years: int, distribution_pace: int) -> list:
    if fund_life_years <= 0:
        return []
    if fund_life_years == 1:
        return [1.0]

    # 0 = very back-ended, 100 = very front-ended
    pace_strength = (distribution_pace - 50) / 12.5
    weights = []
    for idx in range(fund_life_years):
        position = idx / (fund_life_years - 1)
        weights.append(math.exp((0.5 - position) * pace_strength))

    total_weight = sum(weights)
    if total_weight <= 0:
        return [1.0 / fund_life_years] * fund_life_years
    return [w / total_weight for w in weights]


def _calculate_irr(cash_flows: list) -> float:
    clean_flows = [0.0 if pd.isna(cf) else float(cf) for cf in cash_flows]
    if not clean_flows:
        return float("nan")
    if not any(cf < 0 for cf in clean_flows) or not any(cf > 0 for cf in clean_flows):
        return float("nan")

    def npv(rate: float) -> float:
        total = 0.0
        for period, cf in enumerate(clean_flows):
            total += cf / ((1.0 + rate) ** period)
        return total

    low = -0.9999
    high = 10.0
    npv_low = npv(low)
    npv_high = npv(high)

    while npv_low * npv_high > 0 and high < 1_000_000:
        high *= 2
        npv_high = npv(high)

    if npv_low * npv_high > 0:
        return float("nan")

    for _ in range(120):
        mid = (low + high) / 2
        npv_mid = npv(mid)

        if abs(npv_mid) < 1e-8:
            return mid

        if npv_low * npv_mid <= 0:
            high = mid
            npv_high = npv_mid
        else:
            low = mid
            npv_low = npv_mid

    return (low + high) / 2


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


def generate_insight(
    tvpi: float,
    dpi: float,
    rvpi: float,
    benchmark_position: Optional[str],
    percentile_rank: Optional[int],
) -> str:
    if pd.isna(dpi) or pd.isna(rvpi):
        realization_note = "realization mix cannot be assessed from available cash-flow data"
    elif rvpi > dpi:
        realization_note = "value is currently weighted toward unrealized gains"
    elif dpi > rvpi:
        realization_note = "value is currently weighted toward realized distributions"
    else:
        realization_note = "realized and unrealized value are currently balanced"

    sentence_one = (
        f"TVPI is {_format_multiple(tvpi)}, DPI is {_format_multiple(dpi)}, and "
        f"RVPI is {_format_multiple(rvpi)}; {realization_note}."
    )

    if benchmark_position == "top_quartile":
        benchmark_text = "above the top-quartile benchmark"
    elif benchmark_position == "above_median":
        benchmark_text = "above the median benchmark"
    elif benchmark_position == "below_median":
        benchmark_text = "below the median benchmark"
    else:
        benchmark_text = "unavailable"

    if percentile_rank is None:
        percentile_text = "percentile rank is unavailable"
    else:
        percentile_text = f"the fund is in the {percentile_rank}th percentile by TVPI"

    if benchmark_text == "unavailable":
        sentence_two = f"Benchmark position is unavailable, and {percentile_text}."
    else:
        sentence_two = f"Benchmark position is {benchmark_text}, and {percentile_text}."

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
    st.dataframe(filtered_df[table_columns], use_container_width=True)

    if filtered_df.empty:
        st.info("No funds match the current filters.")


def _render_fund_detail_tab(filtered_df: pd.DataFrame, all_funds_df: pd.DataFrame) -> None:
    st.subheader("Fund Detail & Insights")
    if filtered_df.empty:
        st.info("No funds available for detail view under current filters.")
        return

    fund_options = filtered_df["fund_name"].dropna().astype(str).tolist()
    if not fund_options:
        st.info("No fund names are available in the current dataset.")
        return

    selected_fund = st.selectbox("Select Fund", fund_options, key="detail_selected_fund")
    selected_rows = filtered_df[filtered_df["fund_name"].astype(str) == selected_fund]
    if selected_rows.empty:
        st.info("Selected fund data is unavailable.")
        return

    selected_row = selected_rows.iloc[0]
    tvpi, dpi, rvpi = calculate_metrics(selected_row)
    benchmark = _get_benchmark(selected_row.get("vintage_year"))
    benchmark_position = _benchmark_bucket(tvpi, benchmark)
    percentile_rank = _calculate_tvpi_percentile(tvpi, all_funds_df["TVPI"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TVPI", _format_multiple(tvpi))
    c2.metric("DPI", _format_multiple(dpi))
    c3.metric("RVPI", _format_multiple(rvpi))
    c4.metric("Net IRR", _format_percent(selected_row.get("net_irr")))

    st.subheader("Insight")
    st.info(
        generate_insight(
            tvpi=tvpi,
            dpi=dpi,
            rvpi=rvpi,
            benchmark_position=benchmark_position,
            percentile_rank=percentile_rank,
        )
    )

    benchmark = render_benchmark_section(
        selected_row.get("vintage_year"),
        tvpi,
        all_funds_df["TVPI"],
    )
    render_charts(selected_row, tvpi, benchmark)


def _render_performance_calculator_tab() -> None:
    st.subheader("Performance Calculator")
    st.caption("Simple model using paid-in capital, fund life, exit multiple, and distribution pace.")

    i1, i2, i3 = st.columns(3)
    paid_in = i1.number_input("Paid-In Capital", min_value=0.0, value=10_000_000.0, step=500_000.0)
    fund_life_years = int(i2.number_input("Fund Life (Years)", min_value=1, value=10, step=1))
    exit_multiple = i3.number_input("Exit Multiple", min_value=0.0, value=2.0, step=0.1)
    distribution_pace = st.slider("Distribution Pace", min_value=0, max_value=100, value=50)

    total_value = paid_in * exit_multiple
    realized_share = max(0.25, min(0.95, distribution_pace / 100.0))
    cash_out = total_value * realized_share
    remaining_value = max(0.0, total_value - cash_out)

    modeled_row = pd.Series(
        {
            "cash_in": paid_in,
            "cash_out": cash_out,
            "remaining_value": remaining_value,
        }
    )
    modeled_tvpi, modeled_dpi, _ = calculate_metrics(modeled_row)

    weights = _distribution_weights(fund_life_years, distribution_pace)
    yearly_distributions = [cash_out * w for w in weights]
    if yearly_distributions:
        yearly_distributions[-1] += remaining_value

    cash_flows = [-paid_in] + yearly_distributions
    modeled_irr = _calculate_irr(cash_flows)

    o1, o2, o3 = st.columns(3)
    o1.metric("Modeled TVPI", _format_multiple(modeled_tvpi))
    o2.metric("Modeled DPI", _format_multiple(modeled_dpi))
    o3.metric("Modeled IRR", _format_percent(modeled_irr))

    if paid_in <= 0:
        st.info("Enter a non-zero Paid-In Capital value to model performance metrics.")

    years = list(range(0, fund_life_years + 1))
    cumulative_cash = []
    running_total = 0.0
    for cf in cash_flows:
        running_total += cf
        cumulative_cash.append(running_total)

    cumulative_fig = go.Figure()
    cumulative_fig.add_scatter(
        x=years,
        y=cumulative_cash,
        mode="lines+markers",
        name="Cumulative Net Cash",
        line={"color": "#2C3E50", "width": 3},
    )
    cumulative_fig.update_layout(
        title="Cumulative Cash (Modeled)",
        template="plotly_white",
        height=320,
        margin={"l": 10, "r": 10, "t": 35, "b": 10},
        xaxis_title="Year",
        yaxis_title="Cumulative Net Cash",
        showlegend=False,
    )
    st.plotly_chart(cumulative_fig, use_container_width=True)


def _render_glossary_tab() -> None:
    st.subheader("Glossary")
    st.markdown(
        """
        - **TVPI (Total Value to Paid-In):** `(Cash Out + Remaining Value) / Cash In`
        - **DPI (Distributions to Paid-In):** `Cash Out / Cash In`
        - **RVPI (Residual Value to Paid-In):** `Remaining Value / Cash In`
        - **Net IRR:** Annualized return net of fees and carry.
        - **Median TVPI Benchmark:** Typical fund TVPI for a vintage year.
        - **Top Quartile TVPI Benchmark:** 75th percentile TVPI for a vintage year.
        """
    )


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

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Fund Database", "Fund Detail & Insights", "Performance Calculator", "Glossary"]
    )

    with tab1:
        _render_fund_database_tab(filtered_df)

    with tab2:
        _render_fund_detail_tab(filtered_df, df)

    with tab3:
        _render_performance_calculator_tab()

    with tab4:
        _render_glossary_tab()


if __name__ == "__main__":
    main()
