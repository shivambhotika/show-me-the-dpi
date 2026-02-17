import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("Show Me the DPI")

conn = sqlite3.connect("openlp.db")
df = pd.read_sql("SELECT * FROM funds", conn)
# ---- Simple benchmark table ----
benchmarks = {
    2017: {"median_tvpi": 1.6, "top_quartile_tvpi": 2.2},
    2018: {"median_tvpi": 1.4, "top_quartile_tvpi": 2.0},
    2019: {"median_tvpi": 1.2, "top_quartile_tvpi": 1.8},
}


def calc_metrics(row):
    cash_in = row["cash_in"]
    cash_out = row["cash_out"]
    remaining = row["remaining_value"]
    tvpi = (cash_out + remaining) / cash_in
    dpi = cash_out / cash_in
    rvpi = remaining / cash_in
    return tvpi, dpi, rvpi

df[["TVPI","DPI","RVPI"]] = df.apply(
    lambda r: pd.Series(calc_metrics(r)), axis=1
)

st.sidebar.header("Filters")

search = st.sidebar.text_input("Search fund")
if search:
    df = df[df["fund_name"].str.contains(search, case=False, na=False)]

st.subheader("Fund Database")
st.dataframe(df[["fund_name","gp_name","vintage_year","TVPI","DPI","net_irr"]])

st.subheader("Fund Detail")
fund = st.selectbox("Select Fund", df["fund_name"])
row = df[df["fund_name"] == fund].iloc[0]

tvpi, dpi, rvpi = calc_metrics(row)

c1, c2, c3, c4 = st.columns(4)
c1.metric("TVPI", f"{tvpi:.2f}x")
c2.metric("DPI", f"{dpi:.2f}x")
c3.metric("RVPI", f"{rvpi:.2f}x")
c4.metric("Net IRR", f"{row['net_irr']*100:.1f}%")

st.subheader("Insight")

# ---- Insight Engine ----
insight_parts = []

# DPI analysis
if dpi < 0.5:
    insight_parts.append("Low DPI suggests most value is still unrealized.")
elif dpi > 1.0:
    insight_parts.append("Strong DPI indicates meaningful cash has already been returned to LPs.")
else:
    insight_parts.append("DPI suggests a balanced mix of realized and unrealized value.")

# RVPI vs DPI
if rvpi > dpi:
    insight_parts.append("Performance currently relies more on unrealized portfolio value than distributions.")
else:
    insight_parts.append("Realized distributions are contributing significantly to returns.")

# Benchmark comparison
vintage = row["vintage_year"]

if vintage in benchmarks:
    bm = benchmarks[vintage]

    if tvpi >= bm["top_quartile_tvpi"]:
        insight_parts.append("TVPI sits above the top-quartile benchmark for this vintage.")
    elif tvpi >= bm["median_tvpi"]:
        insight_parts.append("TVPI is above median compared with peers from the same vintage.")
    else:
        insight_parts.append("TVPI trails the median benchmark for this vintage.")

# Final insight sentence
final_insight = " ".join(insight_parts)

st.info(final_insight)


st.subheader("Benchmark Comparison")

vintage = row["vintage_year"]

if vintage in benchmarks:
    bm = benchmarks[vintage]

    st.write(f"Vintage {vintage} median TVPI: **{bm['median_tvpi']}x**")
    st.write(f"Vintage {vintage} top quartile TVPI: **{bm['top_quartile_tvpi']}x**")

    if tvpi >= bm["top_quartile_tvpi"]:
        st.success("This fund is above top-quartile benchmark.")
    elif tvpi >= bm["median_tvpi"]:
        st.info("This fund is above median benchmark.")
    else:
        st.warning("This fund is below median benchmark.")
else:
    st.write("No benchmark available for this vintage yet.")

fig = go.Figure()
fig.add_bar(name="Cash In", x=["Capital"], y=[row["cash_in"]])
fig.add_bar(name="Cash Out", x=["Capital"], y=[row["cash_out"]])
fig.add_bar(name="Remaining Value", x=["Capital"], y=[row["remaining_value"]])

fig.update_layout(barmode="stack", height=400)
st.plotly_chart(fig, use_container_width=True)
