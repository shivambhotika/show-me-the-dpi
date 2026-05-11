from __future__ import annotations

import math
import html
import os
import re
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from flask import Flask, Response, abort, render_template_string, request


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__)

LOGO_DEV_PUBLIC_KEY = os.environ.get("LOGO_DEV_PUBLIC_KEY", "pk_NTI52387TOGQE_Oukofcfw").strip()


NAV_ITEMS = [
    ("ABOUT", "about"),
    ("INSIGHTS", "insights"),
    ("TOP FIRMS", "top_firms"),
    ("FUND DATABASE", "fund_database"),
    ("SOURCES", "sources"),
    ("AUDIT", "audit"),
]


LOGO_DOMAINS = {
    "a16z": "a16z.com",
    "andreessen horowitz": "a16z.com",
    "arch venture partners": "archventure.com",
    "bessemer venture partners": "bvp.com",
    "benchmark": "benchmark.com",
    "founders fund": "foundersfund.com",
    "foundry group": "foundrygroup.com",
    "general catalyst": "generalcatalyst.com",
    "ggv": "ggvc.com",
    "greylock": "greylock.com",
    "hongshan": "hongshan.com",
    "index ventures": "indexventures.com",
    "insight partners": "insightpartners.com",
    "khosla ventures": "khoslaventures.com",
    "kleiner perkins": "kleinerperkins.com",
    "lightspeed": "lsvp.com",
    "mayfield": "mayfield.com",
    "nea": "nea.com",
    "peak xv": "peakxv.com",
    "sequoia": "sequoiacap.com",
    "social capital": "socialcapital.com",
    "union square ventures": "usv.com",
    "upfront ventures": "upfront.com",
}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def clean_number(value):
    if pd.isna(value):
        return None
    try:
        number = float(value)
        if not math.isfinite(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def clean_text(value, default: str = "") -> str:
    if value is None or pd.isna(value):
        return default
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "nat"}:
        return default
    return text


def fmt_multiple(value) -> str:
    value = clean_number(value)
    if value is None:
        return "-"
    return f"{value:.2f}x"


def fmt_percent(value) -> str:
    value = clean_number(value)
    if value is None:
        return "-"
    if abs(value) <= 1:
        value *= 100
    return f"{value:.1f}%"


def fmt_money(value) -> str:
    value = clean_number(value)
    if value is None:
        return "-"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.0f}M"
    return f"${value:,.0f}"


def fmt_commitment(value) -> str:
    value = clean_number(value)
    if value is None:
        return "-"
    if 0 < abs(value) < 10_000:
        value *= 1_000_000
    return fmt_money(value)


def fmt_fund_size_m(value) -> str:
    value = clean_number(value)
    if value is None:
        return "-"
    return fmt_money(value * 1_000_000)


def commitment_from_row(row):
    committed = clean_number(getattr(row, "capital_committed", None))
    if committed is not None:
        return committed
    fund_size_m = clean_number(getattr(row, "fund_size_usd_m", None))
    if fund_size_m is not None:
        return fund_size_m * 1_000_000
    return None


def safe_int(value) -> str:
    value = clean_number(value)
    if value is None:
        return "-"
    return str(int(value))


def parse_positive_int(value, default: int = 1) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(number, default)


def median_or_nan(series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return float("nan")
    return float(values.median())


def normalize_logo_name(name: str) -> str:
    text = clean_text(name)
    if not text:
        return ""
    text = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    return " ".join(text.split())


def logo_domain(name: str) -> str:
    clean = normalize_logo_name(name)
    if clean in LOGO_DOMAINS:
        return LOGO_DOMAINS[clean]
    for key, domain in LOGO_DOMAINS.items():
        if key in clean or clean in key:
            return domain
    tokens = [t for t in clean.split() if t not in {"ventures", "venture", "partners", "capital", "fund", "funds"}]
    if tokens:
        return "".join(tokens[:2]) + ".com"
    return ""


def logo_img(name: str, size: int = 28) -> str:
    clean = normalize_logo_name(name)
    if not clean:
        return ""
    domain = logo_domain(clean)
    if not domain or not LOGO_DEV_PUBLIC_KEY:
        return ""
    src = f"https://img.logo.dev/{quote_plus(domain)}?token={quote_plus(LOGO_DEV_PUBLIC_KEY)}&size={int(size)}&format=png"
    alt = html.escape(str(name))
    initials = "".join(part[0].upper() for part in clean.split()[:2])[:2] or "GP"
    return (
        f'<span class="logo-wrap" style="width:{int(size)}px;height:{int(size)}px">'
        f'<span class="logo-fallback">{html.escape(initials)}</span>'
        f'<img class="logo" src="{src}" alt="{alt}" loading="lazy" '
        'onload="this.parentNode.classList.add(\'loaded\')" '
        'onerror="this.parentNode.classList.add(\'failed\');this.remove()">'
        '</span>'
    )


def load_unified() -> pd.DataFrame:
    df = read_csv(DATA_DIR / "unified_funds.csv")
    for col in ["vintage_year", "capital_committed", "capital_contributed", "capital_distributed", "nav", "net_irr", "tvpi", "dpi"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "data_source_type" not in df.columns:
        df["data_source_type"] = "LP-Disclosed"
    return df


def load_master() -> pd.DataFrame:
    df = read_csv(DATA_DIR / "vc_fund_master.csv")
    if df.empty:
        df = read_csv(BASE_DIR / "vc_fund_master.csv")
    for col in ["vintage_year", "fund_size_usd_m", "firm_aum_usd_b", "tvpi", "dpi", "net_irr", "gross_tvpi", "gross_dpi"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "canonical_gp" in df.columns:
        df = df[~df["canonical_gp"].astype(str).str.contains("Accel-KKR", case=False, na=False)].copy()
    if "fund_name" in df.columns:
        df = df[~df["fund_name"].astype(str).str.contains("Accel-KKR", case=False, na=False)].copy()
    if "fund_category" in df.columns:
        df = df[df["fund_category"].astype(str).ne("PE")].copy()
    if "vintage_year" in df.columns:
        df = df.dropna(subset=["vintage_year"]).copy()
        df["vintage_year"] = df["vintage_year"].astype(int)
    unified = load_unified()
    if not unified.empty and {"fund_name", "vintage_year"}.issubset(df.columns) and {"fund_name", "vintage_year"}.issubset(unified.columns):
        extra_cols = [c for c in ["capital_contributed", "capital_distributed", "nav", "scraped_date"] if c in unified.columns]
        if extra_cols:
            u = unified[["fund_name", "vintage_year"] + extra_cols].drop_duplicates(subset=["fund_name", "vintage_year"])
            df = pd.merge(df, u, on=["fund_name", "vintage_year"], how="left")
    if {"capital_contributed", "capital_distributed"}.issubset(df.columns):
        valid = pd.to_numeric(df["capital_contributed"], errors="coerce") > 0
        dpi_calc = df["capital_distributed"] / df["capital_contributed"]
        df["dpi"] = df["dpi"].fillna(dpi_calc.where(valid))
        if "nav" in df.columns:
            tvpi_calc = (df["capital_distributed"] + df["nav"]) / df["capital_contributed"]
            df["tvpi"] = df["tvpi"].fillna(tvpi_calc.where(valid))
    if {"source", "net_irr"}.issubset(df.columns):
        df.loc[(df["source"] == "CalPERS") & (df["net_irr"] == 1.0), "net_irr"] = pd.NA
    if "data_source_type" in df.columns:
        df["data_source_type"] = df["data_source_type"].fillna("LP-Disclosed")
    return df


def load_market() -> pd.DataFrame:
    df = load_master()
    if df.empty or "data_source_type" not in df.columns:
        df = read_csv(BASE_DIR / "gp_disclosed_funds.csv")
        for col in ["vintage_year", "fund_size_usd_m", "firm_aum_usd_b", "tvpi", "dpi", "net_irr", "gross_tvpi", "gross_dpi"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    source_type = df["data_source_type"].astype(str)
    return df[source_type.isin(["Market Intelligence", "GP-Disclosed"])].copy()


def load_benchmarks() -> pd.DataFrame:
    df = read_csv(BASE_DIR / "ca_benchmarks.csv")
    for col in df.columns:
        if col != "asset_class" and col != "notes" and col != "data_maturity":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def page_data() -> dict:
    unified = load_unified()
    master = load_master()
    market = load_market()
    benchmarks = load_benchmarks()
    return {
        "unified": unified,
        "master": master,
        "market": market,
        "benchmarks": benchmarks,
    }


def source_badge(source_type: str) -> str:
    label = str(source_type or "LP-Disclosed")
    css = "badge-gp" if label.startswith("GP") or label == "Market Intelligence" else "badge-lp"
    display = "Market Intelligence" if label.startswith("GP") else label
    return f'<span class="badge {css}">{html.escape(display)}</span>'


def source_type_mask(series: pd.Series, selected: str) -> pd.Series:
    selected = str(selected or "all")
    values = series.fillna("LP-Disclosed").astype(str)
    if selected == "all":
        return pd.Series(True, index=series.index)
    if selected in {"GP-Disclosed", "Market Intelligence"}:
        return values.isin(["GP-Disclosed", "Market Intelligence"])
    return values.eq(selected)


def plot_html(fig) -> str:
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=48, b=42),
        font=dict(family="Inter, Arial, sans-serif", color="#111827"),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        height=390,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False, "responsive": True})


def page_header(title: str, subtitle: str, meta: str = "") -> str:
    return f"""
    <section class="page-head">
      <div>
        <p class="eyebrow">{html.escape(subtitle)}</p>
        <h1>{html.escape(title)}</h1>
      </div>
      <div class="page-meta">{html.escape(meta)}</div>
    </section>
    """


def section_intro(num: str, title: str, body: str) -> str:
    return f"""
    <section class="section-intro">
      <div class="section-num">{html.escape(num)}</div>
      <div>
        <h2>{title}</h2>
        <p>{body}</p>
      </div>
    </section>
    """


def render_about(data: dict) -> str:
    unified = data["unified"]
    master = data["master"]
    market = data["market"]
    source_count = unified["source"].nunique() if "source" in unified else 0
    return f"""
    <section class="hero">
      <p class="eyebrow">PUBLIC LP DISCLOSURE RESEARCH</p>
      <h1>Show Me the DPI</h1>
      <p class="lede">A DPI-first research tool for evaluating VC and PE fund performance using public LP disclosures, explicit source attribution, benchmark context, and a separate market-intelligence lens.</p>
    </section>
    <section class="metric-grid">
      <div class="metric"><span>Funds in LP dataset</span><strong>{len(unified):,}</strong></div>
      <div class="metric"><span>LP sources</span><strong>{source_count:,}</strong></div>
      <div class="metric"><span>Focus firm rows</span><strong>{len(master):,}</strong></div>
      <div class="metric"><span>Market-intel rows</span><strong>{len(market):,}</strong></div>
    </section>
    <section class="panel">
      <h2>How to read this</h2>
      <p>DPI shows how much cash has actually been returned to LPs. TVPI includes remaining unrealized value. Net IRR is useful, but it can be noisy for young funds and should be interpreted with fund age and cash distributions.</p>
      <p>LP-disclosed rows and GP/market-intelligence rows are kept separate so you can see where each datapoint came from.</p>
    </section>
    <section class="panel two-col">
      <div>
        <h2>What this tool emphasizes</h2>
        <ul>
          <li>Cash realization first, then valuation context, then annualized return.</li>
          <li>Source transparency on every page.</li>
          <li>Analyst-friendly comparison across firms, vintages, and source types.</li>
        </ul>
      </div>
      <div>
        <h2>Limitations</h2>
        <ul>
          <li>This is not a complete census of every VC or PE fund.</li>
          <li>LP-reported numbers can differ for the same fund across reporters.</li>
          <li>Market-intelligence data can include provenance uncertainty and selection bias.</li>
        </ul>
      </div>
    </section>
    """


def render_insights(data: dict) -> str:
    master = data["master"].copy()
    bench = data["benchmarks"].copy()
    if master.empty:
        return '<section class="panel"><h2>Insights</h2><p>No master fund data found.</p></section>'

    lp_full = master[master["data_source_type"].fillna("LP-Disclosed").astype(str).eq("LP-Disclosed")].copy()
    total_funds = len(master)
    post17 = lp_full[(lp_full["vintage_year"] >= 2017) & lp_full["dpi"].notna()]
    drought_pct = int((post17["dpi"] < 0.5).mean() * 100) if len(post17) else 0
    top_dpi_df = lp_full[lp_full["dpi"].notna()].sort_values("dpi", ascending=False)
    top_dpi = top_dpi_df.iloc[0] if not top_dpi_df.empty else None
    top_dpi_val = float(top_dpi["dpi"]) if top_dpi is not None else 0
    top_dpi_fund = str(top_dpi.get("fund_name", "")) if top_dpi is not None else "-"
    top_dpi_gp = str(top_dpi.get("canonical_gp", "")) if top_dpi is not None else "-"

    by_vintage = lp_full.dropna(subset=["vintage_year", "dpi", "tvpi"]).copy()
    by_vintage["vintage_year"] = by_vintage["vintage_year"].astype(int)
    by_vintage = (
        by_vintage.groupby("vintage_year", as_index=False)
        .agg(median_dpi=("dpi", "median"), median_tvpi=("tvpi", "median"), funds=("fund_name", "count"))
    )
    by_vintage = by_vintage[(by_vintage["vintage_year"].between(2007, 2022)) & (by_vintage["funds"] >= 2)]
    pill_years = [2010, 2011, 2012, 2014, 2015, 2017, 2019, 2021]
    pill_html = ""
    for year in pill_years:
        rows = lp_full[lp_full["vintage_year"].eq(year)]["dpi"].dropna()
        dpi_value = float(rows.median()) if len(rows) >= 2 else None
        if dpi_value is None:
            pill_class, label, value = "pill-none", "No data", "-"
        elif dpi_value >= 2:
            pill_class, label, value = "pill-strong", "Realized", fmt_multiple(dpi_value)
        elif dpi_value >= 1:
            pill_class, label, value = "pill-mid", "Returning", fmt_multiple(dpi_value)
        elif dpi_value >= 0.1:
            pill_class, label, value = "pill-low", "Early", fmt_multiple(dpi_value)
        else:
            pill_class, label, value = "pill-none", "Cash-light", fmt_multiple(dpi_value)
        pill_html += f'<div class="pill {pill_class}"><span>{year}</span><strong>{value}</strong><small>{label}</small></div>'

    fig1 = go.Figure()
    colors = ["#E8571F" if y <= 2013 else "#D97706" if y <= 2016 else "#CBD5E1" for y in by_vintage["vintage_year"]]
    fig1.add_trace(go.Bar(
        x=by_vintage["vintage_year"].astype(str),
        y=by_vintage["median_dpi"],
        name="Median DPI",
        marker_color=colors,
        customdata=by_vintage["funds"],
        hovertemplate="Vintage %{x}<br>Median DPI %{y:.2f}x<br>n=%{customdata}<extra></extra>",
    ))
    fig1.add_trace(go.Scatter(
        x=by_vintage["vintage_year"].astype(str),
        y=by_vintage["median_tvpi"],
        name="Median TVPI",
        mode="lines+markers",
        line=dict(color="#111827", width=2, dash="dot"),
        hovertemplate="Vintage %{x}<br>Median TVPI %{y:.2f}x<extra></extra>",
    ))
    fig1.update_layout(title="DPI drought by vintage", xaxis_title="Vintage year", yaxis_title="Multiple")

    leaders = lp_full[lp_full["dpi"].notna() & (lp_full["dpi"] > 0)].sort_values("dpi", ascending=False).head(10)
    max_leader = max(float(leaders["dpi"].max()), 1.0) if not leaders.empty else 1.0
    leader_rows = "".join(
        f"""
        <div class="leader-row">
          <div class="logo-line">{logo_img(getattr(row, "canonical_gp", ""), 26)}<div><strong>{html.escape(str(row.fund_name))}</strong><span>{html.escape(str(getattr(row, "canonical_gp", "")))} · {safe_int(getattr(row, "vintage_year", None))} · {html.escape(str(getattr(row, "source", "")))}</span></div></div>
          <div class="leader-bar"><i style="width:{min(float(row.dpi) / max_leader * 100, 100):.1f}%"></i></div>
          <b>{fmt_multiple(row.dpi)}</b>
        </div>
        """
        for row in leaders.itertuples()
    )

    paper = by_vintage.copy()
    paper["unrealized"] = (paper["median_tvpi"] - paper["median_dpi"]).clip(lower=0)
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=paper["vintage_year"].astype(str), y=paper["median_dpi"], name="Realized DPI", marker_color="#E8571F"))
    fig2.add_trace(go.Bar(x=paper["vintage_year"].astype(str), y=paper["unrealized"], name="Unrealized TVPI less DPI", marker_color="#CBD5E1"))
    fig2.update_layout(title="Paper value versus returned cash", barmode="stack", xaxis_title="Vintage year", yaxis_title="Multiple")

    benchmark_html = ""
    if not bench.empty and "median_dpi" in bench.columns:
        bench_plot = bench[bench["vintage_year"].between(2007, 2022)].copy()
        fig_bench = go.Figure()
        fig_bench.add_trace(go.Scatter(
            x=by_vintage["vintage_year"],
            y=by_vintage["median_dpi"],
            mode="lines+markers",
            name="Observed LP median DPI",
            line=dict(color="#E8571F", width=3),
        ))
        fig_bench.add_trace(go.Scatter(
            x=bench_plot["vintage_year"],
            y=bench_plot["median_dpi"],
            mode="lines",
            name="Approx. CA median DPI",
            line=dict(color="#111827", width=2, dash="dash"),
        ))
        if "q1_dpi" in bench_plot:
            fig_bench.add_trace(go.Scatter(
                x=bench_plot["vintage_year"],
                y=bench_plot["q1_dpi"],
                mode="lines",
                name="Approx. CA top-quartile DPI",
                line=dict(color="#9CA3AF", width=2, dash="dot"),
            ))
        fig_bench.update_layout(title="LP-observed DPI versus approximate benchmark bands", xaxis_title="Vintage year", yaxis_title="DPI")
        benchmark_html = f"""
        {section_intro("04 / BENCHMARK CONTEXT", "DPI against directional CA-style bands", "The benchmark dataset is approximate, but it gives a useful sense of when the observed LP-disclosed cohort is tracking below, near, or above a broad US VC realization baseline.")}
        <section class="chart">{plot_html(fig_bench)}</section>
        <section class="footnote">Benchmark: approximate CA US VC quartiles synthesized from public LP annual reports and academic literature. Use as directional reference only.</section>
        """

    a16z = master[master["canonical_gp"].astype(str).str.lower().eq("a16z")].copy()
    a16z = a16z[a16z["gross_tvpi"].notna() & a16z["tvpi"].notna()].sort_values("vintage_year")
    fee_drag_html = ""
    if not a16z.empty:
        a16z_labels = [f"{row.fund_name}<br>{safe_int(row.vintage_year)}" for row in a16z.itertuples()]
        fig_fee = go.Figure()
        fig_fee.add_trace(go.Bar(x=a16z_labels, y=a16z["gross_tvpi"], name="Gross TVPI", marker_color="#CBD5E1"))
        fig_fee.add_trace(go.Bar(x=a16z_labels, y=a16z["tvpi"], name="Net TVPI", marker_color="#E8571F"))
        fig_fee.add_trace(go.Bar(x=a16z_labels, y=a16z["dpi"], name="Net DPI", marker_color="#111827"))
        fig_fee.update_layout(title="a16z gross vs net disclosure", barmode="group", xaxis_title="", yaxis_title="Multiple")
        fund_three = a16z[a16z["fund_name"].astype(str).str.contains("Fund III", case=False, na=False)].head(1)
        drag_text = ""
        if not fund_three.empty:
            row = fund_three.iloc[0]
            drag = clean_number(row["gross_tvpi"]) - clean_number(row["tvpi"])
            drag_text = f"<section class='callout'><strong>Fee drag snapshot.</strong> {html.escape(str(row['fund_name']))} shows gross TVPI {fmt_multiple(row['gross_tvpi'])} versus net TVPI {fmt_multiple(row['tvpi'])}. That is {fmt_multiple(drag)} of multiple drag before LP net returns are realized.</section>"
        fee_drag_html = f"""
        {section_intro("05 / GROSS-NET GAP", "Gross returns are not what LPs take home", "a16z is the clearest market-intelligence example in this dataset with gross and net metrics disclosed. The gap is fees and carry showing up in plain view.")}
        <section class="chart">{plot_html(fig_fee)}</section>
        {drag_text}
        """

    by_gp = (
        lp_full[lp_full["net_irr"].notna() & lp_full["canonical_gp"].notna()]
        .groupby("canonical_gp", dropna=True)
        .agg(min_irr=("net_irr", "min"), max_irr=("net_irr", "max"), funds=("fund_name", "count"))
        .reset_index()
    )
    by_gp = by_gp[by_gp["funds"] >= 2].sort_values("max_irr", ascending=False).head(8)
    fig3 = go.Figure()
    for row in by_gp.itertuples():
        fig3.add_trace(go.Scatter(
            x=[row.min_irr * 100, row.max_irr * 100],
            y=[row.canonical_gp, row.canonical_gp],
            mode="lines+markers",
            line=dict(color="#E8571F", width=5),
            marker=dict(size=8, color="#111827"),
            showlegend=False,
            hovertemplate=f"{html.escape(str(row.canonical_gp))}<br>%{{x:.1f}}%<extra></extra>",
        ))
    fig3.update_layout(title="Manager variance: best and worst IRR by GP", xaxis_title="Net IRR range", yaxis_title="")

    incomplete = data["unified"]
    incomplete_count = int((incomplete["vintage_year"].isna() | incomplete["capital_contributed"].isna()).sum()) if not incomplete.empty else 0

    return f"""
    <section class="insight-hero">
      <p class="eyebrow">INSIGHTS — LP DISCLOSURE DATA</p>
      <h1>Most VC funds haven't returned your money yet.<br><em>Here's who has.</em></h1>
      <p class="lede">We analyze public LP disclosures from CalPERS, CalSTRS, WSIB, UC Regents, UTIMCO and others, plus select market intelligence. DPI first. Everything else is context.</p>
    </section>
    <section class="metric-grid">
      <div class="metric"><span>Funds indexed</span><strong>{total_funds:,}</strong></div>
      <div class="metric"><span>Post-2017 funds with DPI &lt; 0.5x</span><strong>{drought_pct}%</strong></div>
      <div class="metric"><span>Highest LP-disclosed DPI</span><strong>{fmt_multiple(top_dpi_val)}</strong><small>{html.escape(top_dpi_gp)} · {html.escape(top_dpi_fund[:42])}</small></div>
      <div class="metric"><span>Rows needing enrichment</span><strong>{incomplete_count:,}</strong></div>
    </section>
    {section_intro("01 / DPI BY VINTAGE", "The DPI drought starts around 2017", "Pre-2015 funds have broadly returned capital. After 2016, the median fund in this dataset has returned little cash, even when TVPI still shows value on paper.")}
    <section class="chart">{plot_html(fig1)}</section>
    <section class="pill-grid">{pill_html}</section>
    <section class="callout"><strong>What this means for LPs.</strong> TVPI can look healthier than the cash reality. The 2017-2021 cohort has paper marks that may still be useful, but DPI is the number that tells you whether an LP can redeploy capital.</section>
    {section_intro("02 / DPI LEADERBOARD", "The funds that actually sent cash back", "A DPI-first leaderboard surfaces realized outcomes rather than unrealized marks. These are not marks. They are cash distributions reported by LPs.")}
    <section class="panel leader-list">{leader_rows}</section>
    <section class="two-col callout-grid">
      <div class="callout"><strong>Dark-horse signal.</strong> DPI-first sorting surfaces smaller or less visible managers that brand-driven narratives often miss.</div>
      <div class="callout"><strong>Vintage pattern.</strong> The cash-return leaderboard is dominated by older vintages where realization cycles have actually had time to play out.</div>
    </section>
    {section_intro("03 / PAPER VS REAL", "TVPI can look healthy while DPI is still thin", "The gap between TVPI and DPI is the unrealized portion. For newer vintages, that gap is the story.")}
    <section class="chart">{plot_html(fig2)}</section>
    <section class="callout"><strong>The key tension.</strong> Strong TVPI without DPI means LPs are sitting on paper gains that depend on exits that have not happened yet.</section>
    {benchmark_html}
    {fee_drag_html}
    {section_intro("06 / MANAGER VARIANCE", "Same manager, different fund outcomes", "Public LP data makes it easier to compare a firm's fund-level spread instead of relying on a single brand-level reputation.")}
    <section class="chart">{plot_html(fig3)}</section>
    <section class="two-col callout-grid">
      <div class="callout"><strong>Vintage timing is first-order.</strong> Picking the manager is one decision. Picking the fund cycle is another.</div>
      <div class="callout"><strong>Selection bias watch.</strong> Market-intelligence records often skew toward strong disclosed outcomes, so they should be treated as directional rather than audited.</div>
    </section>
    """


def render_top_firms(data: dict) -> str:
    master = data["master"].copy()
    if master.empty:
        return '<section class="panel"><h2>Top Firms</h2><p>No firm data found.</p></section>'
    firm = request.args.get("firm", "").strip()
    mature = master[pd.to_numeric(master.get("vintage_year"), errors="coerce") <= 2018].copy()
    table = (
        master.groupby(["canonical_gp", "gp_display_name"], dropna=True)
        .agg(
            funds=("fund_name", "count"),
            mature_funds=("vintage_year", lambda s: int((pd.to_numeric(s, errors="coerce") <= 2018).sum())),
            median_dpi=("dpi", median_or_nan),
            median_tvpi=("tvpi", median_or_nan),
            median_irr=("net_irr", median_or_nan),
            aum=("firm_aum_usd_b", "max"),
            hq=("hq_city", "first"),
            focus=("investment_focus", "first"),
            data_type=("data_source_type", lambda s: " / ".join(sorted(set(s.dropna().astype(str))))),
        )
        .reset_index()
        .sort_values(["median_dpi", "funds"], ascending=[False, False])
    )
    selected = firm or (str(table.iloc[0]["canonical_gp"]) if not table.empty else "")
    card_rows = table.head(24)
    cards = "".join(
        f"""
        <a class="firm-card" href="/?page=top_firms&firm={quote_plus(str(row.canonical_gp))}">
          <div class="firm-title logo-line">{logo_img(row.gp_display_name, 32)}<span>{html.escape(str(row.gp_display_name))}</span></div>
          <div class="firm-sub">{html.escape(clean_text(row.hq, "-"))} · {html.escape(clean_text(row.data_type, "-"))}</div>
          <div class="firm-stats">
            <span><b>{fmt_multiple(row.median_dpi)}</b>DPI</span>
            <span><b>{fmt_multiple(row.median_tvpi)}</b>TVPI</span>
            <span><b>{int(row.funds)}</b>funds</span>
          </div>
          <div class="muted">{html.escape(clean_text(row.focus, "-"))[:90]}</div>
        </a>
        """
        for row in card_rows.itertuples()
    )
    gp_df = master[master["canonical_gp"].astype(str).eq(selected)].copy().sort_values(["vintage_year", "fund_name"], na_position="last")
    if gp_df.empty:
        gp_df = master[master["canonical_gp"].astype(str).eq(str(table.iloc[0]["canonical_gp"]))].copy() if not table.empty else master.head(0)
    detail_title = str(gp_df.iloc[0].get("gp_display_name", selected)) if not gp_df.empty else selected
    meaningful = gp_df[gp_df["vintage_year"].notna() & (gp_df["vintage_year"] <= 2018)]
    fund_rows = "".join(
        f"""
        <tr>
          <td><strong>{html.escape(str(row.fund_name))}</strong><div class="muted">{html.escape(str(getattr(row, "performance_note", "")))[:120]}</div></td>
          <td>{safe_int(getattr(row, "vintage_year", None))}</td>
          <td>{fmt_fund_size_m(getattr(row, "fund_size_usd_m", None))}</td>
          <td>{fmt_multiple(getattr(row, "dpi", None))}</td>
          <td>{fmt_multiple(getattr(row, "tvpi", None))}</td>
          <td>{fmt_percent(getattr(row, "net_irr", None))}</td>
          <td>{html.escape(str(getattr(row, "source", "-")))}</td>
          <td>{source_badge(getattr(row, "data_source_type", "LP-Disclosed"))}</td>
        </tr>
        """
        for row in gp_df.itertuples()
    )
    return f"""
    {page_header("TOP FIRMS", "VC & GROWTH EQUITY MANAGERS — PUBLIC LP DATA", f"{table.shape[0]:,} FIRMS TRACKED")}
    <section class="firm-grid">{cards}</section>
    <section class="panel">
      <h2 class="logo-line">{logo_img(detail_title, 34)}<span>{html.escape(detail_title)}</span></h2>
      <p>Firm detail keeps LP-disclosed and market-intelligence records visible side by side. Mature-fund medians are used for comparison because young DPI is usually not meaningful.</p>
      <section class="metric-grid compact">
        <div class="metric"><span>Funds tracked</span><strong>{len(gp_df):,}</strong></div>
        <div class="metric"><span>Mature funds</span><strong>{len(meaningful):,}</strong></div>
        <div class="metric"><span>Median DPI</span><strong>{fmt_multiple(median_or_nan(meaningful["dpi"]))}</strong></div>
        <div class="metric"><span>Median TVPI</span><strong>{fmt_multiple(median_or_nan(meaningful["tvpi"]))}</strong></div>
      </section>
      <div class="table-wrap"><table>
        <thead><tr><th>Fund</th><th>Vintage</th><th>Size</th><th>DPI</th><th>TVPI</th><th>Net IRR</th><th>Source</th><th>Type</th></tr></thead>
        <tbody>{fund_rows}</tbody>
      </table></div>
    </section>
    """


def render_fund_database(data: dict) -> str:
    unified = data["unified"].copy()
    market = data["market"].copy()
    if not market.empty:
        market = market.rename(columns={"gp_display_name": "source_gp"})
        market["source"] = market.get("source", "Market Intelligence")
    combined = pd.concat([unified, market], ignore_index=True, sort=False)
    if combined.empty:
        return '<section class="panel"><h2>Fund Database</h2><p>No fund rows found.</p></section>'

    q = request.args.get("q", "").strip()
    source_filter = request.args.get("source", "all")
    year_filter = request.args.get("year", "all")
    sort = request.args.get("sort", "dpi")
    page = parse_positive_int(request.args.get("p", "1"), 1)
    per_page = 50

    display = combined.copy()
    if q:
        mask = display["fund_name"].fillna("").str.contains(q, case=False, regex=False)
        if "canonical_gp" in display:
            mask = mask | display["canonical_gp"].fillna("").str.contains(q, case=False, regex=False)
        if "source" in display:
            mask = mask | display["source"].fillna("").str.contains(q, case=False, regex=False)
        display = display[mask]
    if "data_source_type" in display:
        display = display[source_type_mask(display["data_source_type"], source_filter)]
    if year_filter != "all":
        year_value = clean_number(year_filter)
        if year_value is not None:
            display = display[pd.to_numeric(display["vintage_year"], errors="coerce").eq(float(year_value))]

    if sort in display.columns:
        display = display.sort_values(sort, ascending=False, na_position="last")
    total = len(display)
    max_page = max((total - 1) // per_page + 1, 1)
    page = min(page, max_page)
    display = display.iloc[(page - 1) * per_page : page * per_page]

    rows = "".join(
        f"""
        <tr>
          <td><div class="logo-line table-logo">{logo_img(getattr(row, "canonical_gp", ""), 22)}<div><strong>{html.escape(clean_text(getattr(row, "fund_name", ""), "-"))}</strong><div class="muted">{html.escape(clean_text(getattr(row, "canonical_gp", ""))) if hasattr(row, "canonical_gp") else ""}</div></div></div></td>
          <td>{safe_int(getattr(row, "vintage_year", None))}</td>
          <td>{fmt_commitment(commitment_from_row(row))}</td>
          <td>{fmt_multiple(getattr(row, "dpi", None))}</td>
          <td>{fmt_multiple(getattr(row, "tvpi", None))}</td>
          <td>{fmt_percent(getattr(row, "net_irr", None))}</td>
          <td>{html.escape(clean_text(getattr(row, "source", ""), "-"))}</td>
          <td>{source_badge(getattr(row, "data_source_type", "LP-Disclosed"))}</td>
        </tr>
        """
        for row in display.itertuples()
    )
    years = sorted({int(y) for y in pd.to_numeric(combined["vintage_year"], errors="coerce").dropna().tolist()})
    year_options = '<option value="all">All years</option>' + "".join(
        f'<option value="{year}" {"selected" if year_filter == str(year) else ""}>{year}</option>' for year in years
    )
    next_link = f'?page=fund_database&q={quote_plus(q)}&source={quote_plus(source_filter)}&year={quote_plus(year_filter)}&sort={quote_plus(sort)}&p={page + 1}' if page * per_page < total else ""
    prev_link = f'?page=fund_database&q={quote_plus(q)}&source={quote_plus(source_filter)}&year={quote_plus(year_filter)}&sort={quote_plus(sort)}&p={page - 1}' if page > 1 else ""
    prev_html = f'<a href="{prev_link}">Previous</a>' if prev_link else ""
    next_html = f'<a href="{next_link}">Next</a>' if next_link else ""
    pager = f'<div class="pager">{prev_html}<span>Showing {len(display):,} of {total:,}</span>{next_html}</div>'

    return f"""
    {page_header("FUND DATABASE", "PUBLIC LP DISCLOSURES — NORMALIZED & UNIFIED", f"{len(combined):,} FUNDS INDEXED")}
    <section class="panel">
      <form class="filters" method="get">
        <input type="hidden" name="page" value="fund_database">
        <input name="q" value="{html.escape(q)}" placeholder="Search fund, GP, or source">
        <select name="source">
          <option value="all" {"selected" if source_filter == "all" else ""}>All source types</option>
          <option value="LP-Disclosed" {"selected" if source_filter == "LP-Disclosed" else ""}>LP-disclosed</option>
          <option value="GP-Disclosed" {"selected" if source_filter in ["GP-Disclosed", "Market Intelligence"] else ""}>Market intelligence</option>
        </select>
        <select name="year">{year_options}</select>
        <select name="sort">
          <option value="dpi" {"selected" if sort == "dpi" else ""}>Sort by DPI</option>
          <option value="tvpi" {"selected" if sort == "tvpi" else ""}>Sort by TVPI</option>
          <option value="net_irr" {"selected" if sort == "net_irr" else ""}>Sort by IRR</option>
          <option value="vintage_year" {"selected" if sort == "vintage_year" else ""}>Sort by vintage</option>
        </select>
        <button type="submit">Apply</button>
      </form>
      <div class="table-wrap"><table>
        <thead><tr><th>Fund</th><th>Vintage</th><th>Size / commitment</th><th>DPI</th><th>TVPI</th><th>Net IRR</th><th>Source</th><th>Type</th></tr></thead>
        <tbody>{rows}</tbody>
      </table></div>
      {pager}
    </section>
    """


def render_sources(data: dict) -> str:
    unified = data["unified"]
    market = data["market"]
    lp_rows = ""
    if not unified.empty:
        source_table = unified.groupby("source", dropna=False).agg(funds=("fund_name", "count"), latest_scrape=("scraped_date", "max")).reset_index().sort_values("funds", ascending=False)
        lp_rows = "".join(f"<tr><td>{row.source}</td><td>{int(row.funds):,}</td><td>{row.latest_scrape}</td></tr>" for row in source_table.itertuples())
    market_rows = ""
    if not market.empty:
        market_table = market.groupby("source", dropna=False).agg(funds=("fund_name", "count"), period=("reporting_period", "max")).reset_index().sort_values("funds", ascending=False)
        market_rows = "".join(f"<tr><td>{row.source}</td><td>{int(row.funds):,}</td><td>{row.period}</td></tr>" for row in market_table.itertuples())
    return f"""
    {page_header("SOURCES", "DATA PROVENANCE & COVERAGE TRANSPARENCY")}
    <section class="source-method">
      <div class="section-num">01 / METHODOLOGY</div>
      <div>
        <p>All data is sourced from public LP disclosures filed under FOIA or published voluntarily by institutional investors. Performance metrics are as-reported by the LP, which means they reflect that LP's own timing, fee treatment, and valuation date.</p>
        <p>DPI is calculated as <code>capital_distributed / capital_contributed</code>. TVPI is calculated as <code>(distributed + NAV) / contributed</code> where it is not directly reported.</p>
      </div>
    </section>
    <section class="panel">
      <h2>02 / LP-disclosed source ledger</h2>
      <div class="table-wrap"><table><thead><tr><th>Source</th><th>Rows</th><th>Latest scrape</th></tr></thead><tbody>{lp_rows}</tbody></table></div>
    </section>
    <section class="callout">
      <strong>UTIMCO data notes.</strong> UTIMCO does not always disclose vintage year in fund performance reports. Inferred vintages are derived from fund names and cross-referenced close windows. UTIMCO reports invested capital rather than original commitment, so contribution fields should be read carefully.
    </section>
    <section class="panel">
      <h2>03 / Market-intelligence sources</h2>
      <p>Market intelligence refers to performance data circulating through LP reports, secondary processes, placement materials, and investor community channels. It is directionally useful but not the same as audited LP disclosure.</p>
      <div class="table-wrap"><table><thead><tr><th>Source</th><th>Rows</th><th>Period</th></tr></thead><tbody>{market_rows}</tbody></table></div>
    </section>
    <section class="panel">
      <h2>04 / Benchmark provenance</h2>
      <p>The CA benchmark file is approximate. It is synthesized from public LP annual reports, academic literature, and public quartile references. Cambridge Associates' actual benchmark data is proprietary, so these figures are directional reference bands rather than formal LP reporting values.</p>
    </section>
    <section class="callout">
      <strong>Data quality notes.</strong> IRR values can be non-meaningful for very young funds. DPI of 0.00x on post-2017 funds is often expected in a distribution drought. LPs may report the same fund differently because of accounting treatment and valuation dates.
    </section>
    """


def render_audit(data: dict) -> str:
    lp = data["unified"].copy()
    market = data["market"].copy()
    master = data["master"].copy()
    meaningful_count = 0
    source_count = 0
    if not master.empty:
        meaningful_count = int(
            (
                pd.to_numeric(master.get("vintage_year"), errors="coerce").le(2020)
                & pd.to_numeric(master.get("net_irr"), errors="coerce").notna()
            ).sum()
        )
    if not lp.empty and "source" in lp:
        source_count = int(lp["source"].nunique())

    alerts = []
    if not master.empty:
        drought_fail = master[(master["vintage_year"] >= 2017) & (master["dpi"] >= 0.5)]
        if not drought_fail.empty:
            alerts.append(("fail", f"DPI drought headline needs caveat: {len(drought_fail):,} 2017+ rows have DPI >= 0.5x."))
        ia_exists = master["fund_name"].astype(str).str.contains("IA Venture Strategies", case=False, na=False).any()
        if not ia_exists:
            alerts.append(("fail", "IA Venture Strategies is missing from the master dataset. Any dark-horse copy should not link to it."))
    if not lp.empty:
        bad_dpi = lp[lp["dpi"] > lp["tvpi"] + 0.05]
        if not bad_dpi.empty:
            alerts.append(("fail", f"{len(bad_dpi):,} LP rows have DPI greater than TVPI by more than 0.05x."))
        placeholders = lp[(lp["tvpi"] == 1.0) & (lp["vintage_year"] <= 2018)]
        if not placeholders.empty:
            alerts.append(("warn", f"{len(placeholders):,} older LP rows still show TVPI = 1.0x."))
        dup_key = ["fund_name", "vintage_year", "source", "reporting_period"]
        if set(dup_key).issubset(lp.columns):
            dups = lp[lp.duplicated(subset=dup_key, keep=False)]
            if not dups.empty:
                alerts.append(("warn", f"{len(dups):,} duplicate LP records share fund, vintage, source, and reporting period."))
    if not alerts:
        alerts.append(("ok", "No critical validation failures detected in the current dataset."))

    alert_html = "".join(
        f'<div class="alert alert-{kind}"><strong>{kind.upper()}</strong><span>{html.escape(text)}</span></div>'
        for kind, text in alerts
    )
    top_rows = ""
    if not lp.empty:
        top = lp[lp["dpi"].notna()].sort_values("dpi", ascending=False).head(20)
        top_rows = "".join(
            f"""
            <tr>
              <td><strong>{html.escape(str(row.fund_name))}</strong></td>
              <td>{safe_int(getattr(row, "vintage_year", None))}</td>
              <td>{fmt_multiple(getattr(row, "dpi", None))}</td>
              <td>{fmt_multiple(getattr(row, "tvpi", None))}</td>
              <td>{html.escape(str(getattr(row, "source", "-")))}</td>
            </tr>
            """
            for row in top.itertuples()
        )
    return f"""
    {page_header("AUDIT", "INTERNAL DATA VALIDATION AND PIPELINE HEALTH", "VERCEL HTML PORT")}
    <section class="metric-grid">
      <div class="metric"><span>Total LP funds</span><strong>{len(lp):,}</strong></div>
      <div class="metric"><span>Total market-intel funds</span><strong>{len(market):,}</strong></div>
      <div class="metric"><span>Meaningful IRR rows</span><strong>{meaningful_count:,}</strong></div>
      <div class="metric"><span>LP sources</span><strong>{source_count:,}</strong></div>
    </section>
    <section class="panel">
      <h2>Active alerts</h2>
      <div class="alert-list">{alert_html}</div>
    </section>
    <section class="panel">
      <h2>Top 20 LP-disclosed by DPI</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Fund</th><th>Vintage</th><th>DPI</th><th>TVPI</th><th>Source</th></tr></thead>
        <tbody>{top_rows}</tbody>
      </table></div>
    </section>
    """


PAGE_RENDERERS = {
    "about": render_about,
    "insights": render_insights,
    "top_firms": render_top_firms,
    "fund_database": render_fund_database,
    "sources": render_sources,
    "audit": render_audit,
}


BASE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Show Me the DPI</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Lora:wght@600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root { --ink:#111827; --muted:#6B7280; --line:#E5E7EB; --accent:#E8571F; --soft:#FAFAFA; --green:#0F766E; }
    * { box-sizing: border-box; }
    body { margin: 0; color: var(--ink); background: #fff; font-family: Inter, Arial, sans-serif; }
    .shell { width: min(1480px, calc(100vw - 44px)); margin: 0 auto; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 24px; padding: 18px 0 13px; border-bottom: 1px solid var(--line); }
    .brand { display: flex; align-items: center; gap: 10px; color: var(--ink); text-decoration: none; font-weight: 800; letter-spacing: .01em; }
    .mark { width: 30px; height: 30px; border-radius: 4px; background: var(--accent); color: white; display: grid; place-items: center; font-weight: 800; }
    .brand span span { color: var(--accent); }
    nav { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 24px; }
    nav a { color: var(--ink); text-decoration: none; font-size: 12px; font-weight: 600; letter-spacing: .06em; padding-bottom: 4px; border-bottom: 2px solid transparent; }
    nav a.active { color: var(--accent); border-bottom-color: var(--accent); }
    main { padding: 26px 0 40px; }
    .hero { padding: 36px 0 28px; max-width: 920px; }
    .eyebrow { margin: 0 0 12px; font-family: "IBM Plex Mono", monospace; color: var(--accent); font-size: 12px; letter-spacing: .12em; }
    h1 { margin: 0; font-family: Lora, Georgia, serif; font-size: clamp(42px, 7vw, 82px); line-height: .98; }
    h2 { margin: 0 0 10px; font-family: Lora, Georgia, serif; font-size: 28px; }
    .lede { color: #374151; font-size: 19px; line-height: 1.58; max-width: 860px; }
    .page-head { display:flex; justify-content:space-between; align-items:flex-end; gap:24px; padding:30px 0 22px; border-bottom:1px solid var(--line); margin-bottom:18px; }
    .page-head h1 { font-size: clamp(38px, 5vw, 60px); }
    .page-meta { font-family:"IBM Plex Mono", monospace; color:var(--muted); font-size:12px; letter-spacing:.08em; text-transform:uppercase; white-space:nowrap; }
    .insight-hero { padding:38px 0 32px; max-width:1120px; }
    .insight-hero h1 { font-size: clamp(42px, 6.6vw, 80px); line-height:1.02; }
    .insight-hero em { color:var(--accent); font-style:italic; }
    .metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin: 0 0 22px; }
    .metric-grid.compact { margin-top:16px; }
    .metric { border: 1px solid var(--line); background: var(--soft); border-radius: 4px; padding: 18px; min-height: 106px; }
    .metric span { display: block; color: var(--muted); font-family: "IBM Plex Mono", monospace; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 10px; }
    .metric strong { font-size: 31px; line-height: 1.1; }
    .metric small { display:block; color:var(--muted); line-height:1.35; margin-top:8px; }
    .panel, .chart { border-top: 1px solid var(--line); padding: 24px 0; margin-top: 8px; }
    .panel p { color: #374151; line-height: 1.6; max-width: 960px; }
    .panel ul { color:#374151; line-height:1.75; padding-left:20px; }
    .two-col { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:34px; }
    .section-intro { display:grid; grid-template-columns:190px 1fr; gap:26px; border-top:1px solid var(--line); padding:30px 0 12px; margin-top:24px; }
    .section-num { font-family:"IBM Plex Mono", monospace; color:var(--accent); font-size:11px; letter-spacing:.1em; text-transform:uppercase; }
    .section-intro p { margin:0; color:#374151; line-height:1.65; max-width:900px; }
    .leader-list { display:grid; gap:12px; }
    .leader-row { display:grid; grid-template-columns: minmax(260px, 1.5fr) minmax(160px, 1fr) 80px; gap:14px; align-items:center; padding:12px 0; border-bottom:1px solid var(--line); }
    .leader-row span { display:block; color:var(--muted); font-size:12px; margin-top:4px; }
    .leader-bar { height:9px; background:#F3F4F6; border-radius:99px; overflow:hidden; }
    .leader-bar i { display:block; height:100%; background:var(--accent); }
    .logo-line { display:flex; align-items:center; gap:10px; min-width:0; }
    .logo-wrap { position:relative; display:inline-grid; place-items:center; border-radius:6px; background:#fff; border:1px solid var(--line); flex:0 0 auto; overflow:hidden; }
    .logo-fallback { font-family:"IBM Plex Mono", monospace; font-size:10px; font-weight:700; color:#6B7280; }
    .logo { position:absolute; inset:0; width:100%; height:100%; object-fit:contain; background:#fff; opacity:0; transition:opacity .12s ease; }
    .logo-wrap.loaded .logo { opacity:1; }
    .logo-wrap.loaded .logo-fallback { visibility:hidden; }
    .table-logo .logo-wrap { border-radius:5px; }
    .footnote { font-family:"IBM Plex Mono", monospace; color:var(--muted); font-size:11px; line-height:1.6; padding:10px 0 18px; border-top:1px solid #F3F4F6; }
    .firm-grid { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:14px; margin:20px 0 28px; }
    .firm-card { display:block; color:var(--ink); text-decoration:none; border:1px solid var(--line); border-radius:4px; padding:16px; background:#fff; min-height:176px; }
    .firm-card:hover { border-color:var(--accent); }
    .firm-title { font-family:Lora, Georgia, serif; font-weight:700; font-size:22px; margin-bottom:4px; }
    .firm-title .logo { width:32px; height:32px; }
    .firm-sub { color:var(--muted); font-size:12px; min-height:34px; }
    .firm-stats { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:14px 0; }
    .firm-stats span { border-top:1px solid var(--line); padding-top:8px; color:var(--muted); font-size:11px; text-transform:uppercase; }
    .firm-stats b { display:block; color:var(--ink); font-size:18px; text-transform:none; }
    .source-method { display:grid; grid-template-columns:190px 1fr; gap:28px; padding:30px 0; border-bottom:1px solid var(--line); }
    .source-method p { color:#374151; line-height:1.7; margin-top:0; }
    code { font-family:"IBM Plex Mono", monospace; background:#F3F4F6; padding:2px 6px; border-radius:3px; }
    .callout { background:#FFFBEB; border:1px solid #FDE68A; border-radius:4px; color:#374151; padding:16px; line-height:1.65; margin:18px 0; }
    .callout-grid { border-top:0; padding-top:0; }
    .pill-grid { display:grid; grid-template-columns:repeat(8, minmax(0,1fr)); gap:10px; margin:16px 0 24px; }
    .pill { border:1px solid var(--line); border-radius:4px; padding:12px; background:#fff; }
    .pill span { display:block; font-family:"IBM Plex Mono", monospace; color:var(--muted); font-size:11px; margin-bottom:8px; }
    .pill strong { display:block; font-size:20px; color:var(--ink); }
    .pill small { color:var(--muted); }
    .pill-strong { border-color:#FDBA74; background:#FFF7ED; }
    .pill-mid { border-color:#86EFAC; background:#F0FDF4; }
    .pill-low { border-color:#FDE68A; background:#FFFBEB; }
    .pill-none { background:#F9FAFB; }
    .alert-list { display:grid; gap:10px; }
    .alert { display:grid; grid-template-columns:80px 1fr; gap:12px; border-radius:4px; padding:12px 14px; line-height:1.5; }
    .alert strong { font-family:"IBM Plex Mono", monospace; font-size:11px; letter-spacing:.08em; }
    .alert-fail { background:#FEF2F2; border:1px solid #FECACA; color:#7F1D1D; }
    .alert-warn { background:#FFFBEB; border:1px solid #FDE68A; color:#78350F; }
    .alert-ok { background:#ECFDF5; border:1px solid #A7F3D0; color:#064E3B; }
    .table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 4px; }
    table { width: 100%; border-collapse: collapse; min-width: 860px; background: #fff; }
    th, td { padding: 12px 14px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 14px; }
    th { background: var(--soft); font-family: "IBM Plex Mono", monospace; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: #4B5563; }
    tr:last-child td { border-bottom: 0; }
    .muted { color: var(--muted); font-size: 12px; margin-top: 4px; }
    .badge { display: inline-block; border-radius: 999px; padding: 4px 8px; font-size: 11px; font-weight: 700; white-space: nowrap; }
    .badge-lp { color: #1D4ED8; background: #EFF6FF; }
    .badge-gp { color: var(--green); background: #ECFDF5; }
    .filters { display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0; }
    input, select, button { height: 40px; border: 1px solid var(--line); border-radius: 4px; padding: 0 11px; font: inherit; background: #fff; }
    input { min-width: 260px; }
    button { background: var(--ink); color: #fff; cursor: pointer; border-color: var(--ink); font-weight: 700; }
    .pager { display: flex; justify-content: flex-end; align-items: center; gap: 14px; margin-top: 14px; color: var(--muted); }
    .pager a { color: var(--accent); text-decoration: none; font-weight: 700; }
    footer { border-top: 1px solid var(--line); padding: 18px 0 26px; color: var(--muted); font-size: 12px; }
    @media (max-width: 820px) {
      .shell { width: min(100vw - 28px, 1480px); }
      header { align-items: flex-start; flex-direction: column; }
      nav { justify-content: flex-start; gap: 14px 18px; }
      .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .firm-grid, .two-col { grid-template-columns:1fr; }
      .pill-grid { grid-template-columns:repeat(2, minmax(0,1fr)); }
      .section-intro, .source-method { grid-template-columns:1fr; gap:10px; }
      .leader-row { grid-template-columns:1fr; }
      .page-head { align-items:flex-start; flex-direction:column; }
      h1 { font-size: 44px; }
    }
    @media (max-width: 520px) {
      .metric-grid { grid-template-columns: 1fr; }
      input, select, button { width: 100%; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <a class="brand" href="/"><span class="mark">D</span><span>SHOW ME THE <span>DPI</span></span></a>
      <nav>
        {% for label, key in nav_items %}
          <a href="/?page={{ key }}" class="{% if key == current_page %}active{% endif %}">{{ label }}</a>
        {% endfor %}
      </nav>
    </header>
    <main>{{ content|safe }}</main>
    <footer>Source disclosures vary by reporting period and definitions. LP-disclosed and market-intelligence data are intentionally labeled separately.</footer>
  </div>
</body>
</html>
"""


@app.get("/")
def index():
    current_page = request.args.get("page", "fund_database")
    if current_page not in PAGE_RENDERERS:
        abort(404)
    data = page_data()
    content = PAGE_RENDERERS[current_page](data)
    return render_template_string(BASE_TEMPLATE, nav_items=NAV_ITEMS, current_page=current_page, content=content)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "app": "show-me-the-dpi"}


@app.get("/logo/<path:name>")
def logo(name: str):
    import requests

    token = os.environ.get("LOGO_DEV_TOKEN", "").strip() or LOGO_DEV_PUBLIC_KEY
    domain = logo_domain(name)
    if not token or not domain:
        abort(404)
    size = request.args.get("size", "64")
    try:
        logo_url = f"https://img.logo.dev/{domain}?token={token}&size={int(size)}&format=png"
        resp = requests.get(logo_url, timeout=6)
        if resp.status_code >= 400 or not resp.content:
            abort(404)
        content_type = resp.headers.get("content-type", "image/png")
        return Response(
            resp.content,
            content_type=content_type,
            headers={"Cache-Control": "public, max-age=86400, s-maxage=604800"},
        )
    except Exception:
        abort(404)


if __name__ == "__main__":
    app.run(debug=True)
