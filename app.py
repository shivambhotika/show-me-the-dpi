from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from flask import Flask, abort, render_template_string, request


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__)


NAV_ITEMS = [
    ("ABOUT", "about"),
    ("INSIGHTS", "insights"),
    ("TOP FIRMS", "top_firms"),
    ("FUND DATABASE", "fund_database"),
    ("SOURCES", "sources"),
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def clean_number(value):
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def safe_int(value) -> str:
    value = clean_number(value)
    if value is None or math.isnan(value):
        return "-"
    return str(int(value))


def load_unified() -> pd.DataFrame:
    df = read_csv(DATA_DIR / "unified_funds.csv")
    for col in ["vintage_year", "capital_committed", "capital_contributed", "capital_distributed", "nav", "net_irr", "tvpi", "dpi"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "data_source_type" not in df.columns:
        df["data_source_type"] = "LP-Disclosed"
    return df


def load_master() -> pd.DataFrame:
    df = read_csv(BASE_DIR / "vc_fund_master.csv")
    for col in ["vintage_year", "fund_size_usd_m", "firm_aum_usd_b", "tvpi", "dpi", "net_irr", "gross_tvpi", "gross_dpi"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_market() -> pd.DataFrame:
    df = read_csv(BASE_DIR / "gp_disclosed_funds.csv")
    for col in ["vintage_year", "fund_size_usd_m", "firm_aum_usd_b", "tvpi", "dpi", "net_irr", "gross_tvpi", "gross_dpi"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


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
    css = "badge-gp" if str(source_type).startswith("GP") else "badge-lp"
    return f'<span class="badge {css}">{source_type}</span>'


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


def render_about(data: dict) -> str:
    unified = data["unified"]
    master = data["master"]
    market = data["market"]
    source_count = unified["source"].nunique() if "source" in unified else 0
    return f"""
    <section class="hero">
      <p class="eyebrow">PUBLIC LP DISCLOSURE RESEARCH</p>
      <h1>Show Me the DPI</h1>
      <p class="lede">An analyst-focused research tool for evaluating VC and PE fund performance using LP-disclosed data, explicit source attribution, and benchmark context.</p>
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
    """


def render_insights(data: dict) -> str:
    master = data["master"].copy()
    bench = data["benchmarks"].copy()
    if master.empty:
        return '<section class="panel"><h2>Insights</h2><p>No master fund data found.</p></section>'

    mature = master[pd.to_numeric(master.get("vintage_year"), errors="coerce") <= 2018].copy()
    by_gp = (
        mature.groupby("gp_display_name", dropna=True)
        .agg(funds=("fund_name", "count"), median_dpi=("dpi", "median"), median_tvpi=("tvpi", "median"), median_irr=("net_irr", "median"))
        .reset_index()
        .sort_values(["median_dpi", "funds"], ascending=[False, False])
        .head(15)
    )
    fig1 = px.bar(by_gp, x="median_dpi", y="gp_display_name", orientation="h", title="Mature fund median DPI by firm", labels={"median_dpi": "Median DPI", "gp_display_name": ""})
    fig1.update_traces(marker_color="#E8571F", hovertemplate="%{y}<br>DPI %{x:.2f}x<extra></extra>")
    fig1.update_yaxes(autorange="reversed")

    by_vintage = master.dropna(subset=["vintage_year", "dpi", "tvpi"]).copy()
    by_vintage["vintage_year"] = by_vintage["vintage_year"].astype(int)
    by_vintage = by_vintage.groupby("vintage_year", as_index=False).agg(median_dpi=("dpi", "median"), median_tvpi=("tvpi", "median"), funds=("fund_name", "count"))
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=by_vintage["vintage_year"], y=by_vintage["median_dpi"], mode="lines+markers", name="Observed DPI", line=dict(color="#E8571F", width=3)))
    if not bench.empty and "median_dpi" in bench:
        fig2.add_trace(go.Scatter(x=bench["vintage_year"], y=bench["median_dpi"], mode="lines", name="Benchmark median DPI", line=dict(color="#111827", dash="dash")))
    fig2.update_layout(title="DPI by vintage year", xaxis_title="Vintage", yaxis_title="DPI")

    incomplete = data["unified"]
    incomplete_count = int((incomplete["vintage_year"].isna() | incomplete["capital_contributed"].isna()).sum()) if not incomplete.empty else 0

    return f"""
    <section class="metric-grid">
      <div class="metric"><span>Mature focus funds</span><strong>{len(mature):,}</strong></div>
      <div class="metric"><span>Median mature DPI</span><strong>{fmt_multiple(mature["dpi"].median())}</strong></div>
      <div class="metric"><span>Median mature TVPI</span><strong>{fmt_multiple(mature["tvpi"].median())}</strong></div>
      <div class="metric"><span>Rows needing enrichment</span><strong>{incomplete_count:,}</strong></div>
    </section>
    <section class="chart">{plot_html(fig1)}</section>
    <section class="chart">{plot_html(fig2)}</section>
    """


def render_top_firms(data: dict) -> str:
    master = data["master"].copy()
    if master.empty:
        return '<section class="panel"><h2>Top Firms</h2><p>No firm data found.</p></section>'
    mature = master[pd.to_numeric(master.get("vintage_year"), errors="coerce") <= 2018].copy()
    table = (
        mature.groupby(["canonical_gp", "gp_display_name"], dropna=True)
        .agg(funds=("fund_name", "count"), median_dpi=("dpi", "median"), median_tvpi=("tvpi", "median"), median_irr=("net_irr", "median"), aum=("firm_aum_usd_b", "max"))
        .reset_index()
        .sort_values(["median_dpi", "funds"], ascending=[False, False])
        .head(30)
    )
    rows = "".join(
        f"""
        <tr>
          <td><strong>{row.gp_display_name}</strong></td>
          <td>{int(row.funds)}</td>
          <td>{fmt_multiple(row.median_dpi)}</td>
          <td>{fmt_multiple(row.median_tvpi)}</td>
          <td>{fmt_percent(row.median_irr)}</td>
          <td>{'-' if pd.isna(row.aum) else '$' + format(row.aum, '.1f') + 'B'}</td>
        </tr>
        """
        for row in table.itertuples()
    )
    return f"""
    <section class="panel">
      <h2>Top Firms</h2>
      <p>Mature funds only, sorted by median DPI. Young funds are excluded because DPI is not yet meaningful.</p>
      <div class="table-wrap"><table>
        <thead><tr><th>Firm</th><th>Funds</th><th>Median DPI</th><th>Median TVPI</th><th>Median IRR</th><th>AUM</th></tr></thead>
        <tbody>{rows}</tbody>
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
    sort = request.args.get("sort", "dpi")
    page = max(int(request.args.get("p", "1") or "1"), 1)
    per_page = 50

    display = combined.copy()
    if q:
        mask = display["fund_name"].fillna("").str.contains(q, case=False, regex=False)
        if "canonical_gp" in display:
            mask = mask | display["canonical_gp"].fillna("").str.contains(q, case=False, regex=False)
        display = display[mask]
    if source_filter != "all" and "data_source_type" in display:
        display = display[display["data_source_type"].fillna("LP-Disclosed") == source_filter]

    if sort in display.columns:
        display = display.sort_values(sort, ascending=False, na_position="last")
    total = len(display)
    display = display.iloc[(page - 1) * per_page : page * per_page]

    rows = "".join(
        f"""
        <tr>
          <td><strong>{getattr(row, "fund_name", "")}</strong><div class="muted">{getattr(row, "canonical_gp", "") if hasattr(row, "canonical_gp") else ""}</div></td>
          <td>{safe_int(getattr(row, "vintage_year", None))}</td>
          <td>{fmt_money(getattr(row, "capital_committed", None) if hasattr(row, "capital_committed") else getattr(row, "fund_size_usd_m", None) * 1_000_000 if clean_number(getattr(row, "fund_size_usd_m", None)) is not None else None)}</td>
          <td>{fmt_multiple(getattr(row, "dpi", None))}</td>
          <td>{fmt_multiple(getattr(row, "tvpi", None))}</td>
          <td>{fmt_percent(getattr(row, "net_irr", None))}</td>
          <td>{getattr(row, "source", "-")}</td>
          <td>{source_badge(getattr(row, "data_source_type", "LP-Disclosed"))}</td>
        </tr>
        """
        for row in display.itertuples()
    )
    next_link = f'?page=fund_database&q={q}&source={source_filter}&sort={sort}&p={page + 1}' if page * per_page < total else ""
    prev_link = f'?page=fund_database&q={q}&source={source_filter}&sort={sort}&p={page - 1}' if page > 1 else ""
    prev_html = f'<a href="{prev_link}">Previous</a>' if prev_link else ""
    next_html = f'<a href="{next_link}">Next</a>' if next_link else ""
    pager = f'<div class="pager">{prev_html}<span>Showing {len(display):,} of {total:,}</span>{next_html}</div>'

    return f"""
    <section class="panel">
      <h2>Fund Database</h2>
      <form class="filters" method="get">
        <input type="hidden" name="page" value="fund_database">
        <input name="q" value="{q}" placeholder="Search fund or GP">
        <select name="source">
          <option value="all" {"selected" if source_filter == "all" else ""}>All source types</option>
          <option value="LP-Disclosed" {"selected" if source_filter == "LP-Disclosed" else ""}>LP-disclosed</option>
          <option value="GP-Disclosed" {"selected" if source_filter == "GP-Disclosed" else ""}>Market intelligence</option>
        </select>
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
    <section class="panel">
      <h2>LP-disclosed sources</h2>
      <div class="table-wrap"><table><thead><tr><th>Source</th><th>Rows</th><th>Latest scrape</th></tr></thead><tbody>{lp_rows}</tbody></table></div>
    </section>
    <section class="panel">
      <h2>Market-intelligence sources</h2>
      <div class="table-wrap"><table><thead><tr><th>Source</th><th>Rows</th><th>Period</th></tr></thead><tbody>{market_rows}</tbody></table></div>
    </section>
    <section class="panel">
      <h2>Benchmark provenance</h2>
      <p>The benchmark file is a CA-approximate dataset used for directional context. It should be read as a comparison lens, not a definitive institutional benchmark product.</p>
    </section>
    """


PAGE_RENDERERS = {
    "about": render_about,
    "insights": render_insights,
    "top_firms": render_top_firms,
    "fund_database": render_fund_database,
    "sources": render_sources,
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
    .metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin: 0 0 22px; }
    .metric { border: 1px solid var(--line); background: var(--soft); border-radius: 4px; padding: 18px; min-height: 106px; }
    .metric span { display: block; color: var(--muted); font-family: "IBM Plex Mono", monospace; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 10px; }
    .metric strong { font-size: 31px; line-height: 1.1; }
    .panel, .chart { border-top: 1px solid var(--line); padding: 24px 0; margin-top: 8px; }
    .panel p { color: #374151; line-height: 1.6; max-width: 960px; }
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
    current_page = request.args.get("page", "about")
    if current_page not in PAGE_RENDERERS:
        abort(404)
    data = page_data()
    content = PAGE_RENDERERS[current_page](data)
    return render_template_string(BASE_TEMPLATE, nav_items=NAV_ITEMS, current_page=current_page, content=content)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "app": "show-me-the-dpi"}


if __name__ == "__main__":
    app.run(debug=True)
