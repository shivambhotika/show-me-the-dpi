import html
import os
from textwrap import dedent

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit.delta_generator import DeltaGenerator


st.set_page_config(
    page_title="Show Me the DPI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# Dedent markdown on all containers (st, columns, expanders, etc.) so HTML never shows as raw code.
_orig_dg_markdown = DeltaGenerator.markdown


def _dg_markdown_dedent(self, body, *args, **kwargs):
    if isinstance(body, str):
        body = dedent(body)
    return _orig_dg_markdown(self, body, *args, **kwargs)


DeltaGenerator.markdown = _dg_markdown_dedent


def _render_html(html_text: str):
    st.markdown(dedent(html_text).strip(), unsafe_allow_html=True)


def inject_css():
    st.markdown(
        """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');

    :root, html, body, .stApp { color-scheme: light !important; }
    .main .block-container { padding: 1rem 1.8rem 1.1rem 1.8rem; max-width: 100%; }
    .stApp { background-color: #FFFFFF; color: #111827; font-family: 'Inter', sans-serif; }
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    .stTabs [data-baseweb="tab-list"] {
        background: #FFFFFF; border-bottom: 1px solid #E5E7EB; gap: 0; padding: 0; margin-bottom: 1.3rem;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'IBM Plex Mono', monospace; font-size: 11px; font-weight: 500;
        letter-spacing: 0.08em; text-transform: uppercase; color: #9CA3AF;
        padding: 12px 20px; border-bottom: 2px solid transparent; background: transparent;
    }
    .stTabs [aria-selected="true"] { color: #111827; border-bottom: 2px solid #E8571F; background: transparent; }
    .stTabs [data-baseweb="tab-panel"] { padding-top: 0; }

    .metric-card { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; padding: 20px 24px; }
    .metric-card-dpi { background: #FFF4EF; border: 2px solid #E8571F; border-radius: 6px; padding: 20px 24px; }
    .metric-label {
        font-family: 'IBM Plex Mono', monospace; font-size: 10px; font-weight: 500;
        letter-spacing: 0.1em; text-transform: uppercase; color: #6B7280; margin-bottom: 8px;
    }
    .metric-label-dpi {
        font-family: 'IBM Plex Mono', monospace; font-size: 10px; font-weight: 500;
        letter-spacing: 0.1em; text-transform: uppercase; color: #E8571F; margin-bottom: 8px;
    }
    .metric-value { font-family: 'Inter', sans-serif; font-size: 36px; font-weight: 700; color: #111827; line-height: 1; }
    .metric-value-dpi { font-family: 'Inter', sans-serif; font-size: 36px; font-weight: 700; color: #E8571F; line-height: 1; }

    .page-title {
        font-family: 'Inter', sans-serif; font-size: 32px; font-weight: 800;
        color: #111827; letter-spacing: -0.02em; margin-bottom: 4px;
    }
    .page-title-accent { color: #E8571F; }
    .page-subtitle {
        font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.1em;
        text-transform: uppercase; color: #9CA3AF; margin-bottom: 2rem;
    }
    .section-label {
        font-family: 'IBM Plex Mono', monospace; font-size: 10px; font-weight: 500;
        letter-spacing: 0.15em; text-transform: uppercase; color: #E8571F;
        border-top: 1px solid #E8571F; padding-top: 8px; margin: 2rem 0 1.25rem 0;
    }

    .fund-table { width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; }
    .fund-table th {
        font-family: 'IBM Plex Mono', monospace; font-size: 10px; font-weight: 500;
        letter-spacing: 0.1em; text-transform: uppercase; color: #9CA3AF;
        padding: 8px 12px; border-bottom: 1px solid #E5E7EB; text-align: left; background: #FAFAFA;
    }
    .fund-table th.right { text-align: right; }
    .fund-table td {
        padding: 12px 12px; border-bottom: 1px solid #F3F4F6;
        color: #111827; font-size: 14px; font-weight: 500; vertical-align: middle;
    }
    .fund-table td.id-col {
        font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #9CA3AF; width: 48px;
    }
    .fund-table td.numeric {
        font-family: 'IBM Plex Mono', monospace; font-size: 13px; text-align: right;
    }
    .fund-table td.dpi-col {
        font-family: 'IBM Plex Mono', monospace; font-size: 13px; font-weight: 500;
        color: #E8571F; text-align: right;
    }
    .fund-table tr:hover td { background: #FFF8F5; }

    .badge {
        display: inline-block; font-family: 'IBM Plex Mono', monospace; font-size: 10px;
        font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase;
        padding: 3px 8px; border-radius: 4px; border: 1px solid;
    }
    .badge-calpers   { background:#EEF2FF; color:#4F46E5; border-color:#C7D2FE; }
    .badge-calstrs   { background:#F0FDF4; color:#15803D; border-color:#BBF7D0; }
    .badge-oregon    { background:#FFF7ED; color:#C2410C; border-color:#FED7AA; }
    .badge-wsib      { background:#F5F3FF; color:#7C3AED; border-color:#DDD6FE; }
    .badge-uc        { background:#ECFDF5; color:#065F46; border-color:#A7F3D0; }
    .badge-mass      { background:#FEF2F2; color:#991B1B; border-color:#FECACA; }
    .badge-florida   { background:#FFFBEB; color:#92400E; border-color:#FDE68A; }
    .badge-louisiana { background:#F0F9FF; color:#0C4A6E; border-color:#BAE6FD; }
    .badge-estimated { background:#FFF4EF; color:#E8571F; border-color:#FED7AA; }

    .badge-a16z      { background:#F0F4FF; color:#1D4ED8; border-color:#BFDBFE; }
    .badge-founders  { background:#F9F0FF; color:#6B21A8; border-color:#E9D5FF; }
    .badge-social    { background:#F0FFFE; color:#0F766E; border-color:#99F6E4; }
    .badge-mi { background:#FFF7ED; color:#C2410C; border-color:#FED7AA; font-style:italic; }
    .badge-mi-a16z { background:#FFF7ED; color:#C2410C; border-color:#FED7AA; }
    .badge-mi-ff { background:#FAF5FF; color:#7E22CE; border-color:#E9D5FF; }
    .badge-mi-sc { background:#F0FDFA; color:#0F766E; border-color:#99F6E4; }
    .badge-lp-disclosed { background:#EEF2FF; color:#1D4ED8; border-color:#BFDBFE; }

    .insight-box {
        background: #FFF4EF; border-left: 3px solid #E8571F;
        border-radius: 6px; padding: 20px 24px; margin: 1.5rem 0;
    }
    .insight-label {
        font-family: 'IBM Plex Mono', monospace; font-size: 10px; font-weight: 500;
        letter-spacing: 0.12em; text-transform: uppercase; color: #E8571F; margin-bottom: 10px;
    }
    .insight-body { font-family: 'Inter', sans-serif; font-size: 14px; color: #111827; line-height: 1.6; }
    .insight-body strong { font-weight: 600; }
    .insight-body em { color: #6B7280; font-style: italic; }

    .coverage-bar-wrap { display: flex; align-items: center; gap: 10px; }
    .coverage-bar-bg { flex: 1; height: 6px; background: #E5E7EB; border-radius: 3px; }
    .coverage-bar-fill { height: 6px; border-radius: 3px; }
    .coverage-bar-fill.high { background: #16A34A; }
    .coverage-bar-fill.medium { background: #D97706; }
    .coverage-bar-fill.low { background: #DC2626; }

    .irr-high { color: #16A34A; font-weight: 600; font-family: 'IBM Plex Mono', monospace; }
    .irr-mid { color: #D97706; font-weight: 600; font-family: 'IBM Plex Mono', monospace; }
    .irr-low { color: #DC2626; font-weight: 600; font-family: 'IBM Plex Mono', monospace; }
    .irr-na { color: #9CA3AF; font-family: 'IBM Plex Mono', monospace; }

    .firm-card {
        border: 1px solid #E5E7EB; border-radius: 8px; padding: 20px;
        background: #FFFFFF; transition: border-color 0.15s; min-height: 220px;
    }
    .firm-card:hover { border-color: #E8571F; }
    .firm-name { font-family: 'Inter', sans-serif; font-size: 16px; font-weight: 700; color: #111827; margin-bottom: 2px; }
    .firm-meta {
        font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #9CA3AF;
        letter-spacing: 0.05em; margin-bottom: 12px;
    }
    .firm-aum-badge {
        display: inline-block; background: #F3F4F6; border-radius: 4px;
        padding: 4px 10px; font-family: 'IBM Plex Mono', monospace;
        font-size: 11px; font-weight: 500; color: #374151; margin-bottom: 12px;
    }
    .firm-best-irr-label {
        font-family: 'IBM Plex Mono', monospace; font-size: 9px; letter-spacing: 0.1em;
        text-transform: uppercase; color: #9CA3AF;
    }
    .firm-best-irr-value {
        font-family: 'IBM Plex Mono', monospace; font-size: 20px;
        font-weight: 500; color: #E8571F;
    }

    .source-row {
        display: grid; grid-template-columns: 220px 130px 220px 130px 1fr;
        align-items: center; padding: 18px 0; border-bottom: 1px solid #F3F4F6; gap: 16px;
    }
    .source-name { font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 600; color: #111827; }
    .source-notes { font-family: 'Inter', sans-serif; font-size: 12px; color: #6B7280; line-height: 1.5; }
    .source-sync { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #9CA3AF; }

    .stTextInput input,
    .stSelectbox select,
    .stSelectbox [data-baseweb="select"] > div,
    .stSelectbox [data-baseweb="select"] div,
    .stNumberInput input,
    .stButton > button {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 12px !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 6px !important;
        background: #FFFFFF !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }
    .stTextInput input::placeholder { color: #9CA3AF !important; }
    .stTextInput input:focus { border-color: #E8571F !important; box-shadow: 0 0 0 2px rgba(232, 87, 31, 0.1) !important; }
    .stRadio label, .stRadio div, .stSelectbox label, .stTextInput label { color: #111827 !important; }

    .record-count { font-family: 'IBM Plex Mono', monospace; font-size: 13px; font-weight: 500; color: #E8571F; margin-left: 12px; }
    .chart-subtitle { font-family: 'Inter', sans-serif; font-size: 12px; color: #9CA3AF; margin-bottom: 16px; }
    .footer-wrap { margin-top: 1.2rem; border-top: 1px solid #E5E7EB; padding-top: 12px; }
    .footer-text { font-family: 'Inter', sans-serif; font-size: 12px; color: #6B7280; line-height: 1.55; }
    .footer-links a { color: #E8571F; text-decoration: none; }
    .footer-links a:hover { text-decoration: underline; }
    </style>
    """,
        unsafe_allow_html=True,
    )


inject_css()


SOURCE_BADGE_CLASS = {
    "CalPERS": "badge-calpers",
    "CalSTRS": "badge-calstrs",
    "Oregon Treasury": "badge-oregon",
    "WSIB": "badge-wsib",
    "UC Regents": "badge-uc",
    "Massachusetts PRIM": "badge-mass",
    "Florida SBA": "badge-florida",
    "Louisiana Teachers": "badge-louisiana",
    "a16z Firm Disclosure": "badge-a16z",
    "Founders Fund Firm Disclosure": "badge-founders",
    "Social Capital Firm Disclosure": "badge-social",
}

SOURCE_SHORT = {
    "CalPERS": "CALPERS",
    "CalSTRS": "CALSTRS",
    "Oregon Treasury": "OREGON",
    "WSIB": "WSIB",
    "UC Regents": "UC_REGENTS",
    "Massachusetts PRIM": "MASS_PRIM",
    "Florida SBA": "FLORIDA_SBA",
    "Louisiana Teachers": "LOUISIANA",
    "a16z Firm Disclosure": "A16Z",
    "Founders Fund Firm Disclosure": "FOUNDERS",
    "Social Capital Firm Disclosure": "SOCIAL_CAP",
}

CATEGORY_COLORS = {
    "Venture": "#2C3E50",
    "Growth": "#18A999",
    "Opportunities": "#F4B942",
    "PE": "#8B4513",
    "Company Creation": "#7B68EE",
}

SOURCES_CONFIG = [
    {
        "name": "California Public Employees' (CalPERS)",
        "short": "CALPERS",
        "classification": "PUBLIC",
        "badge_class": "badge-calpers",
        "coverage": 92,
        "period": "2024 Q3",
        "notes": "Largest US public pension. PE/VC fund-level IRR, TVPI, DPI. Filed under California FOIA.",
        "row_count_key": "CalPERS",
    },
    {
        "name": "California Teachers (CalSTRS)",
        "short": "CALSTRS",
        "classification": "PUBLIC",
        "badge_class": "badge-calstrs",
        "coverage": 88,
        "period": "2024 Q3",
        "notes": "Teachers pension. Comprehensive alternative assets disclosure.",
        "row_count_key": "CalSTRS",
    },
    {
        "name": "Oregon State Treasury",
        "short": "OREGON",
        "classification": "PUBLIC",
        "badge_class": "badge-oregon",
        "coverage": 85,
        "period": "2024",
        "notes": "Oregon PERS. Text-format PDF parsed with regex extraction.",
        "row_count_key": "Oregon Treasury",
    },
    {
        "name": "Washington State Investment Board",
        "short": "WSIB",
        "classification": "PUBLIC",
        "badge_class": "badge-wsib",
        "coverage": 90,
        "period": "2024",
        "notes": "WSIB PE portfolio. Good vintage depth.",
        "row_count_key": "WSIB",
    },
    {
        "name": "UC Regents",
        "short": "UC_REGENTS",
        "classification": "PUBLIC",
        "badge_class": "badge-uc",
        "coverage": 95,
        "period": "Jun 2024",
        "notes": "Best VC coverage. Contains Sequoia, Khosla, GGV, HongShan, Peak XV fund data. University endowment.",
        "row_count_key": "UC Regents",
    },
    {
        "name": "Massachusetts PRIM",
        "short": "MASS_PRIM",
        "classification": "PUBLIC",
        "badge_class": "badge-mass",
        "coverage": 80,
        "period": "Mar 2020",
        "notes": "Older vintage data. IVP XIII/XIV coverage. Excel format.",
        "row_count_key": "Massachusetts PRIM",
    },
    {
        "name": "Florida State Board of Administration",
        "short": "FLORIDA_SBA",
        "classification": "PUBLIC",
        "badge_class": "badge-florida",
        "coverage": 78,
        "period": "Q2 2020",
        "notes": "PE-heavy. Large fund universe, good benchmark depth. 2020 vintage.",
        "row_count_key": "Florida SBA",
    },
    {
        "name": "Louisiana Teachers (TRSL)",
        "short": "LOUISIANA",
        "classification": "PUBLIC",
        "badge_class": "badge-louisiana",
        "coverage": 75,
        "period": "Dec 2019",
        "notes": "Historical PE vintage data. 2019 cutoff.",
        "row_count_key": "Louisiana Teachers",
    },
]

GP_SOURCES_CONFIG = [
    {
        "name": "Andreessen Horowitz (a16z)",
        "short": "A16Z",
        "classification": "MARKET INTEL",
        "badge_class": "badge-a16z",
        "coverage": 60,
        "period": "Sep 2025",
        "fund_count": 9,
        "notes": "Published in a16z blog post (2025). Covers 'Select First Era Funds 2009-2017' only. Excludes Bio funds, crypto funds, and all funds raised after 2017. Net TVPI and Net DPI shown.",
        "source_key": "a16z Firm Disclosure",
    },
    {
        "name": "Founders Fund",
        "short": "FOUNDERS",
        "classification": "MARKET INTEL",
        "badge_class": "badge-founders",
        "coverage": 80,
        "period": "2024 Q3",
        "fund_count": 10,
        "notes": "Circulated via investor materials. Covers all main vehicles FFI–FFVIII plus Growth funds. TVPI/DPI primary metrics; IRR figures less reliable on recent vintages.",
        "source_key": "Founders Fund Firm Disclosure",
    },
    {
        "name": "Social Capital",
        "short": "SOCIAL_CAP",
        "classification": "MARKET INTEL",
        "badge_class": "badge-social",
        "coverage": 90,
        "period": "Dec 2024",
        "fund_count": 5,
        "notes": "Formal benchmarking report as of 12/31/2024. Most rigorous market intelligence set in dataset: Cambridge Associates quartile rankings, gross AND net metrics. Covers 5 funds.",
        "source_key": "Social Capital Firm Disclosure",
    },
]


@st.cache_data
def load_unified():
    df = pd.read_csv("data/unified_funds.csv")
    df["vintage_year"] = pd.to_numeric(df.get("vintage_year"), errors="coerce").astype("Int64")
    df["net_irr"] = pd.to_numeric(df.get("net_irr"), errors="coerce")
    df["tvpi"] = pd.to_numeric(df.get("tvpi"), errors="coerce")
    df["dpi"] = pd.to_numeric(df.get("dpi"), errors="coerce")
    df["capital_committed"] = pd.to_numeric(df.get("capital_committed"), errors="coerce")
    df["source"] = df.get("source", pd.Series(index=df.index, dtype="object")).fillna("Unknown")
    return df


@st.cache_data
def load_market_intel():
    if not os.path.exists("gp_disclosed_funds.csv"):
        return pd.DataFrame()

    df = pd.read_csv("gp_disclosed_funds.csv")
    # Runtime override: this dataset is treated as market intelligence, not formal GP publication.
    df["data_source_type"] = "Market Intelligence"
    df["irr_meaningful"] = df["irr_meaningful"].map(
        lambda x: True if str(x).lower() in ["true", "1", "yes"] else False
    )
    for col in [
        "gross_tvpi",
        "tvpi",
        "gross_dpi",
        "dpi",
        "gross_irr",
        "net_irr",
        "fund_size_usd_m",
        "vintage_year",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["vintage_year"] = df["vintage_year"].astype("Int64")
    return df


@st.cache_data
def load_master_full():
    df = pd.read_csv("vc_fund_master.csv")
    if "data_source_type" not in df.columns:
        df["data_source_type"] = "LP-Disclosed"
    else:
        df["data_source_type"] = df["data_source_type"].fillna("LP-Disclosed")

    mi_gps = {"a16z", "founders fund", "social capital"}
    gp_series = df.get("canonical_gp", pd.Series(index=df.index, dtype="object")).astype(str).str.strip().str.lower()
    df.loc[gp_series.isin(mi_gps), "data_source_type"] = "Market Intelligence"

    for col in ["gross_tvpi", "gross_dpi"]:
        if col not in df.columns:
            df[col] = None

    df["irr_meaningful"] = df["irr_meaningful"].map(
        lambda x: True if str(x).lower() in ["true", "1", "yes"] else False
    )
    for col in [
        "net_irr",
        "tvpi",
        "dpi",
        "gross_tvpi",
        "gross_dpi",
        "vintage_year",
        "fund_size_usd_m",
        "firm_aum_usd_b",
        "firm_founded",
    ]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    df["vintage_year"] = df["vintage_year"].astype("Int64")
    return df


@st.cache_data
def load_benchmarks():
    df = pd.read_csv("ca_benchmarks.csv")
    for col in [
        "median_net_irr",
        "q1_net_irr",
        "q3_net_irr",
        "median_tvpi",
        "q1_tvpi",
        "q3_tvpi",
        "median_dpi",
        "q1_dpi",
    ]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    df["vintage_year"] = pd.to_numeric(df.get("vintage_year"), errors="coerce").astype("Int64")
    df = df[df["vintage_year"].notna()].copy()
    df["vintage_year"] = df["vintage_year"].astype(int)
    return df


def bench_disclaimer():
    st.markdown(
        """
    <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#9CA3AF;
        letter-spacing:0.05em;margin-top:4px;padding:6px 0;border-top:1px solid #F3F4F6">
        BENCHMARK: Approximate CA US VC quartiles — synthesized from public LP annual
        reports and academic literature (Harris, Jenkinson, Kaplan &amp; Stucke 2014).
        Actual Cambridge Associates data is proprietary. Use as directional reference only.
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str, count: str = None):
    count_html = '<span class="record-count">{0}</span>'.format(html.escape(count)) if count else ""
    _render_html(
        (
            '<div style="margin-bottom:0.5rem;">'
            '<div style="display:flex;align-items:baseline;gap:4px;">'
            '<span class="page-title">{0}<span class="page-title-accent">.</span></span>{1}'
            '</div>'
            '<div class="page-subtitle">{2}</div>'
            '</div>'
        ).format(html.escape(title), count_html, html.escape(subtitle))
    )


def _fmt_multiple(v):
    return "—" if pd.isna(v) else "{0:.2f}×".format(v)


def _fmt_irr(v):
    return "—" if pd.isna(v) else "{0:.1f}%".format(v * 100)


def _fmt_committed(v):
    return "—" if pd.isna(v) else "${0:.0f}M".format(v / 1_000_000)


def _to_database_market_intel_df(mi_df: pd.DataFrame) -> pd.DataFrame:
    if mi_df.empty:
        return pd.DataFrame(columns=[
            "fund_name", "vintage_year", "source", "capital_committed", "tvpi", "dpi", "net_irr", "data_source_type"
        ])

    out = mi_df.copy()
    out["capital_committed"] = out["fund_size_usd_m"] * 1_000_000
    out["data_source_type"] = "Market Intelligence"
    keep = ["fund_name", "vintage_year", "source", "capital_committed", "tvpi", "dpi", "net_irr", "data_source_type"]
    for col in keep:
        if col not in out.columns:
            out[col] = np.nan
    return out[keep].copy()


def _to_database_lp_df(lp_df: pd.DataFrame) -> pd.DataFrame:
    out = lp_df.copy()
    out["data_source_type"] = "LP-Disclosed"
    keep = ["fund_name", "vintage_year", "source", "capital_committed", "tvpi", "dpi", "net_irr", "data_source_type"]
    for col in keep:
        if col not in out.columns:
            out[col] = np.nan
    return out[keep].copy()


def render_fund_table(df_display: pd.DataFrame, show_source_type: bool = False):
    def irr_html(v):
        if pd.isna(v):
            return '<span class="irr-na">—</span>'
        pct = v * 100
        cls = "irr-high" if pct >= 20 else "irr-mid" if pct >= 10 else "irr-low"
        return '<span class="{0}">{1:.1f}%</span>'.format(cls, pct)

    def dpi_html(v):
        if pd.isna(v) or v == 0:
            return '<span class="irr-na">0.00×</span>'
        color = "#E8571F" if v > 0.5 else "#9CA3AF"
        return "<span style=\"color:{0};font-family:'IBM Plex Mono',monospace;font-weight:500\">{1:.2f}×</span>".format(color, v)

    def source_type_badge(row: pd.Series):
        v = str(row.get("data_source_type", ""))
        source = str(row.get("source", ""))
        if v == "Market Intelligence":
            if source == "a16z Firm Disclosure":
                return '<span class="badge badge-mi-a16z">INTEL ▸ A16Z</span>'
            if source == "Founders Fund Firm Disclosure":
                return '<span class="badge badge-mi-ff">INTEL ▸ FOUNDERS</span>'
            if source == "Social Capital Firm Disclosure":
                return '<span class="badge badge-mi-sc">INTEL ▸ SOCIAL CAP</span>'
            return '<span class="badge badge-mi">MARKET INTEL</span>'
        return '<span class="badge badge-lp-disclosed">LP</span>'

    rows_html = ""
    for i, (_, row) in enumerate(df_display.iterrows()):
        source = row.get("source")
        badge_class = SOURCE_BADGE_CLASS.get(source, "badge-estimated")
        badge_label = SOURCE_SHORT.get(source, str(source).upper()[:12])
        tvpi = _fmt_multiple(row.get("tvpi"))
        committed = _fmt_committed(row.get("capital_committed"))
        name = html.escape(str(row.get("fund_name", "")))
        vintage = "—" if pd.isna(row.get("vintage_year")) else str(int(row.get("vintage_year")))

        source_type_cell = ""
        if show_source_type:
            source_type_cell = "<td>{0}</td>".format(source_type_badge(row))

        rows_html += (
            "<tr>"
            '<td class="id-col">{0}</td>'
            '<td style="font-weight:500">{1}</td>'
            '<td class="numeric">{2}</td>'
            '<td><span class="badge {3}">{4}</span></td>'
            "{5}"
            '<td class="numeric">{6}</td>'
            '<td class="numeric">{7}</td>'
            '<td class="dpi-col">{8}</td>'
            '<td class="numeric">{9}</td>'
            "</tr>"
        ).format(
            str(i + 1).zfill(3),
            name,
            vintage,
            badge_class,
            html.escape(str(badge_label)),
            source_type_cell,
            committed,
            tvpi,
            dpi_html(row.get("dpi")),
            irr_html(row.get("net_irr")),
        )

    source_type_header = ""
    if show_source_type:
        source_type_header = "<th>SOURCE TYPE</th>"

    _render_html(
        (
            '<table class="fund-table"><thead><tr>'
            "<th>ID</th><th>FUND NAME</th><th class=\"right\">VINTAGE</th><th>SOURCE</th>{0}"
            '<th class="right">COMMITTED</th><th class="right">TVPI</th>'
            '<th class="right" style="color:#E8571F">DPI ▲</th><th class="right">IRR</th>'
            "</tr></thead><tbody>{1}</tbody></table>"
        ).format(source_type_header, rows_html)
    )


def render_fund_database(df_unified: pd.DataFrame, df_market_intel: pd.DataFrame):
    lp_df = _to_database_lp_df(df_unified)
    mi_df = _to_database_market_intel_df(df_market_intel)

    render_page_header(
        "FUND DATABASE",
        "PUBLIC LP DISCLOSURES — NORMALIZED & UNIFIED",
        "{0:,} FUNDS INDEXED".format(len(lp_df) + len(mi_df)),
    )

    with st.expander("ℹ About Market Intelligence Data (a16z, Founders Fund, Social Capital)", expanded=False):
        st.markdown(
            """
        <div class="insight-body" style="padding:4px 0">
            Performance data for <strong>Andreessen Horowitz</strong>, <strong>Founders Fund</strong>,
            and <strong>Social Capital</strong> circulated through industry channels — secondary
            market processes, LP reporting packages, and investor community sources.
            These are <em>not</em> formally published figures, and provenance cannot be fully
            verified. The vintage of marks is approximate. Treat as directional data,
            not audited performance records. LP-disclosed (FOIA) data from pension funds
            is independently reported and more reliable.
        </div>
        """,
            unsafe_allow_html=True,
        )

    base_df = pd.concat([lp_df, mi_df], ignore_index=True)

    if "db_page" not in st.session_state:
        st.session_state["db_page"] = 0

    cols = st.columns([3.3, 1.6, 1.6])
    with cols[0]:
        query = st.text_input("SEARCH FUND/GP", placeholder="TYPE QUERY HERE...")
    with cols[1]:
        source_list = sorted(base_df["source"].dropna().astype(str).unique().tolist())
        source_filter = st.selectbox("FILTER SOURCE", ["ALL SOURCES"] + source_list)
    with cols[2]:
        years = sorted(base_df["vintage_year"].dropna().astype(int).unique().tolist())
        year_filter = st.selectbox("VINTAGE", ["ALL YEARS"] + [str(y) for y in years])

    df_display = base_df.copy()
    if query:
        q = query.strip().lower()
        mask = (
            df_display["fund_name"].astype(str).str.lower().str.contains(q, na=False)
            | df_display["source"].astype(str).str.lower().str.contains(q, na=False)
        )
        df_display = df_display[mask]

    if source_filter != "ALL SOURCES":
        df_display = df_display[df_display["source"] == source_filter]

    if year_filter != "ALL YEARS":
        df_display = df_display[df_display["vintage_year"] == int(year_filter)]

    df_display = df_display.sort_values(["dpi", "tvpi"], ascending=[False, False], na_position="last")

    total = len(df_display)
    page_size = 25
    total_pages = max((total - 1) // page_size + 1, 1)
    page_idx = min(st.session_state.get("db_page", 0), total_pages - 1)
    st.session_state["db_page"] = page_idx

    start = page_idx * page_size
    end = min(start + page_size, total)
    page_df = df_display.iloc[start:end].copy()

    render_fund_table(page_df, show_source_type=True)

    nav_cols = st.columns([8, 2])
    with nav_cols[0]:
        txt = "SHOWING 0–0 OF 0" if total == 0 else "SHOWING {0}–{1} OF {2}".format(start + 1, end, total)
        st.markdown('<span class="irr-na">{0}</span>'.format(txt), unsafe_allow_html=True)
    with nav_cols[1]:
        pager_cols = st.columns([1, 1], gap="small")
        with pager_cols[0]:
            prev_clicked = st.button("← PREV", key="db_prev")
        with pager_cols[1]:
            next_clicked = st.button("NEXT →", key="db_next")

    if prev_clicked and page_idx > 0:
        st.session_state["db_page"] = page_idx - 1
        st.rerun()
    if next_clicked and page_idx < total_pages - 1:
        st.session_state["db_page"] = page_idx + 1
        st.rerun()


def render_firm_card(gp_name: str, gp_data: pd.DataFrame):
    row = gp_data.iloc[0]
    fund_count = len(gp_data)
    meaningful = gp_data[gp_data["irr_meaningful"] == True]
    best_irr = meaningful["net_irr"].max() if len(meaningful) > 0 else None

    founded = "—" if pd.isna(row.get("firm_founded")) else str(int(row.get("firm_founded")))
    aum_txt = "—" if pd.isna(row.get("firm_aum_usd_b")) else "${0:.0f}B AUM".format(row.get("firm_aum_usd_b"))
    best_irr_html = '<div class="firm-best-irr-value" style="color:#9CA3AF">N/A</div>'
    if best_irr is not None and pd.notna(best_irr):
        best_irr_html = '<div class="firm-best-irr-value">{0:.1f}%</div>'.format(best_irr * 100)

    categories = " / ".join(gp_data["fund_category"].dropna().astype(str).unique()[:3])

    st.markdown(
        """
    <div class="firm-card">
        <div class="firm-name">{0}</div>
        <div class="firm-meta">EST. {1} · {2}</div>
        <div class="firm-aum-badge">{3}</div>
        <div style="margin-bottom:12px"><span class="badge badge-estimated" style="margin-right:4px">{4}</span></div>
        <div style="display:flex;justify-content:space-between;align-items:flex-end">
            <div>
                <div class="firm-best-irr-label">BEST IRR (PUBLIC DATA)</div>
                {5}
            </div>
            <div style="text-align:right">
                <div class="firm-best-irr-label">FUNDS IN DATASET</div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:18px;font-weight:500;color:#374151">{6}</div>
            </div>
        </div>
    </div>
    """.format(
            html.escape(str(row.get("gp_display_name", gp_name))),
            founded,
            html.escape(str(row.get("hq_city", "—")).upper()),
            html.escape(aum_txt),
            html.escape(categories if categories else "N/A"),
            best_irr_html,
            fund_count,
        ),
        unsafe_allow_html=True,
    )


def _render_metric_card(label: str, value: str, dpi=False):
    card_class = "metric-card-dpi" if dpi else "metric-card"
    label_class = "metric-label-dpi" if dpi else "metric-label"
    value_class = "metric-value-dpi" if dpi else "metric-value"
    st.markdown(
        """
    <div class="{0}">
      <div class="{1}">{2}</div>
      <div class="{3}">{4}</div>
    </div>
    """.format(card_class, label_class, html.escape(label), value_class, html.escape(value)),
        unsafe_allow_html=True,
    )


def render_firms(df_master: pd.DataFrame):
    gps = sorted(df_master["canonical_gp"].dropna().astype(str).unique().tolist())

    render_page_header("TOP FIRMS", "VC & GROWTH EQUITY MANAGERS — PUBLIC LP DATA", "{0:,} FIRMS TRACKED".format(len(gps)))

    source_by_gp = (
        df_master.groupby("canonical_gp")["data_source_type"]
        .apply(lambda s: sorted(set(s.dropna().astype(str))))
        .to_dict()
    )
    gp_only_gps = [gp for gp in gps if source_by_gp.get(gp) == ["Market Intelligence"]]
    lp_gps = [gp for gp in gps if gp not in gp_only_gps]

    st.markdown('<div class="section-label">LP-DISCLOSED — INSTITUTIONAL SOURCES</div>', unsafe_allow_html=True)
    for i in range(0, len(lp_gps), 3):
        cols = st.columns(3)
        for j, gp in enumerate(lp_gps[i : i + 3]):
            with cols[j]:
                render_firm_card(gp, df_master[df_master["canonical_gp"] == gp])

    st.markdown('<div class="section-label">MARKET INTELLIGENCE — CIRCULATED DATA</div>', unsafe_allow_html=True)
    st.markdown(
        """
    <div style="font-family:'Inter',sans-serif;font-size:13px;color:#6B7280;margin-bottom:1rem;
        padding:12px 16px;background:#FFFBEB;border-radius:6px;border:1px solid #FDE68A">
        Performance data below comes from market intelligence channels (circulated LP packages,
        secondary processes, and investor community sources), not independent FOIA filing.
        Provenance is not fully verifiable.
    </div>
    """,
        unsafe_allow_html=True,
    )
    for i in range(0, len(gp_only_gps), 3):
        cols = st.columns(3)
        for j, gp in enumerate(gp_only_gps[i : i + 3]):
            with cols[j]:
                render_firm_card(gp, df_master[df_master["canonical_gp"] == gp])

    st.markdown('<div class="section-label">FUND PERFORMANCE DETAIL</div>', unsafe_allow_html=True)
    selected_gp = st.selectbox("SELECT FIRM", gps, label_visibility="collapsed")
    gp_df = df_master[df_master["canonical_gp"] == selected_gp].copy().sort_values(["vintage_year", "fund_name"], na_position="last")

    if gp_df.empty:
        st.info("No funds available for selected firm.")
        return

    row = gp_df.iloc[0]
    is_market_intel = bool((gp_df["data_source_type"] == "Market Intelligence").all())
    source_chip = '<span class="badge badge-mi">MARKET INTEL</span>' if is_market_intel else '<span class="badge badge-lp-disclosed">LP-DISCLOSED</span>'

    st.markdown(
        """
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1.5rem;padding:20px;background:#FAFAFA;border-radius:8px;border:1px solid #E5E7EB">
        <div>
            <div class="page-title" style="font-size:24px">{0}</div>
            <div style="margin:8px 0">{1}</div>
            <div class="page-subtitle" style="margin-bottom:0">{2} · {3}</div>
        </div>
        <div style="text-align:right">
            <div class="firm-best-irr-label">AUM</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:22px;font-weight:600;color:#111827">${4}B</div>
        </div>
    </div>
    """.format(
            html.escape(str(row.get("gp_display_name", selected_gp))),
            source_chip,
            html.escape(str(row.get("investment_focus", "—"))),
            html.escape(str(row.get("stage_focus", "—"))),
            "—" if pd.isna(row.get("firm_aum_usd_b")) else "{0:.1f}".format(row.get("firm_aum_usd_b")),
        ),
        unsafe_allow_html=True,
    )

    meaningful = gp_df[gp_df["irr_meaningful"] == True]

    if is_market_intel and str(selected_gp).lower() == "a16z":
        gross_tvpi = meaningful["gross_tvpi"].median() if not meaningful.empty else np.nan
        gross_dpi = meaningful["gross_dpi"].median() if not meaningful.empty else np.nan
        net_tvpi = meaningful["tvpi"].median() if not meaningful.empty else np.nan
        net_dpi = meaningful["dpi"].median() if not meaningful.empty else np.nan
        best_net_irr = meaningful["net_irr"].max() if not meaningful.empty else np.nan
        fee_drag = gross_tvpi - net_tvpi if pd.notna(gross_tvpi) and pd.notna(net_tvpi) else np.nan

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            _render_metric_card("MEDIAN GROSS TVPI", _fmt_multiple(gross_tvpi), dpi=False)
        with c2:
            _render_metric_card("MEDIAN GROSS DPI", _fmt_multiple(gross_dpi), dpi=False)
        with c3:
            _render_metric_card("MEDIAN TVPI DRAG", _fmt_multiple(fee_drag), dpi=False)
        with c4:
            _render_metric_card("FUNDS TRACKED", "{0}".format(len(gp_df)), dpi=False)

        c5, c6, c7, c8 = st.columns(4)
        with c5:
            _render_metric_card("MEDIAN NET TVPI", _fmt_multiple(net_tvpi), dpi=False)
        with c6:
            _render_metric_card("MEDIAN NET DPI", _fmt_multiple(net_dpi), dpi=True)
        with c7:
            _render_metric_card("BEST NET IRR", _fmt_irr(best_net_irr), dpi=False)
        with c8:
            _render_metric_card("MEANINGFUL FUNDS", "{0}".format(int(meaningful.shape[0])), dpi=False)

        st.markdown("<div style='font-size:12px;color:#9CA3AF;font-style:italic;margin-top:8px'>Gross metrics shown before fees and carry.</div>", unsafe_allow_html=True)

    elif is_market_intel:
        med_gross_tvpi = meaningful["gross_tvpi"].median() if not meaningful.empty else np.nan
        med_net_tvpi = meaningful["tvpi"].median() if not meaningful.empty else np.nan
        med_net_dpi = meaningful["dpi"].median() if not meaningful.empty else np.nan
        best_irr = meaningful["net_irr"].max() if not meaningful.empty else np.nan

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            _render_metric_card("MEDIAN GROSS TVPI", _fmt_multiple(med_gross_tvpi), dpi=False)
        with c2:
            _render_metric_card("MEDIAN NET TVPI", _fmt_multiple(med_net_tvpi), dpi=False)
        with c3:
            _render_metric_card("MEDIAN NET DPI", _fmt_multiple(med_net_dpi), dpi=True)
        with c4:
            _render_metric_card("BEST NET IRR", _fmt_irr(best_irr), dpi=False)

        st.markdown("<div style='font-size:12px;color:#9CA3AF;font-style:italic;margin-top:8px'>Gross metrics shown before fees and carry.</div>", unsafe_allow_html=True)

    else:
        med_tvpi = meaningful["tvpi"].median() if not meaningful.empty else np.nan
        med_dpi = meaningful["dpi"].median() if not meaningful.empty else np.nan
        best_irr = meaningful["net_irr"].max() if not meaningful.empty else np.nan

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            _render_metric_card("MEDIAN TVPI", _fmt_multiple(med_tvpi), dpi=False)
        with c2:
            _render_metric_card("MEDIAN DPI", _fmt_multiple(med_dpi), dpi=True)
        with c3:
            _render_metric_card("BEST IRR", _fmt_irr(best_irr), dpi=False)
        with c4:
            _render_metric_card("FUNDS TRACKED", "{0}".format(len(gp_df)), dpi=False)

    def _status_badge(v):
        if bool(v):
            return '<span class="badge" style="background:#ECFDF5;color:#166534;border-color:#86EFAC">MEANINGFUL</span>'
        return '<span class="badge" style="background:#F3F4F6;color:#6B7280;border-color:#D1D5DB">TOO EARLY</span>'

    rows_html = ""
    for _, r in gp_df.iterrows():
        vintage = "—" if pd.isna(r.get("vintage_year")) else str(int(r.get("vintage_year")))
        gross_col = ""
        gross_cell = ""
        if is_market_intel:
            gross_col = "<th class='right'>GROSS TVPI</th>"
            gross_cell = "<td class='numeric'>{0}</td>".format(_fmt_multiple(r.get("gross_tvpi")))

        rows_html += (
            "<tr>"
            '<td style="font-weight:500">{0}</td>'
            '<td class="numeric">{1}</td>'
            "<td>{2}</td>"
            '<td class="numeric">{3}</td>'
            "{4}"
            '<td class="numeric">{5}</td>'
            '<td class="dpi-col">{6}</td>'
            '<td class="numeric">{7}</td>'
            "<td>{8}</td>"
            "</tr>"
        ).format(
            html.escape(str(r.get("fund_name", ""))),
            vintage,
            html.escape(str(r.get("fund_category", "—"))),
            "—" if pd.isna(r.get("fund_size_usd_m")) else "${0:.0f}M".format(r.get("fund_size_usd_m")),
            gross_cell,
            _fmt_multiple(r.get("tvpi")),
            _fmt_multiple(r.get("dpi")),
            _fmt_irr(r.get("net_irr")),
            _status_badge(r.get("irr_meaningful")),
        )

    gross_header = "<th class='right'>GROSS TVPI</th>" if is_market_intel else ""
    _render_html(
        (
            '<table class="fund-table" style="margin-top:1rem;"><thead><tr>'
            "<th>FUND</th><th class=\"right\">VINTAGE</th><th>STRATEGY</th><th class=\"right\">SIZE</th>{0}"
            '<th class="right">NET TVPI</th><th class="right" style="color:#E8571F">NET DPI</th>'
            '<th class="right">NET IRR</th><th>STATUS</th>'
            "</tr></thead><tbody>{1}</tbody></table>"
        ).format(gross_header, rows_html)
    )

    if is_market_intel and str(selected_gp).lower() == "a16z":
        f3 = gp_df[gp_df["fund_name"].astype(str).str.contains("Fund III", case=False, na=False)]
        if not f3.empty:
            r = f3.iloc[0]
            if pd.notna(r.get("gross_tvpi")) and pd.notna(r.get("tvpi")):
                drag = r.get("gross_tvpi") - r.get("tvpi")
                st.markdown(
                    """
                <div class="insight-box">
                    <div class="insight-label">● FEE DRAG SNAPSHOT</div>
                    <div class="insight-body">
                        <strong>{0}</strong> shows gross TVPI {1} vs net TVPI {2}.
                        <em>That is {3} of multiple drag before LP net returns are realized.</em>
                    </div>
                </div>
                """.format(
                        html.escape(str(r.get("fund_name"))),
                        _fmt_multiple(r.get("gross_tvpi")),
                        _fmt_multiple(r.get("tvpi")),
                        _fmt_multiple(drag),
                    ),
                    unsafe_allow_html=True,
                )

    notable = str(row.get("notable_portfolio", "—"))
    st.markdown(
        """
    <div class="insight-box">
        <div class="insight-label">● NOTABLE PORTFOLIO</div>
        <div class="insight-body">{0}</div>
    </div>
    """.format(html.escape(notable)),
        unsafe_allow_html=True,
    )


def _plot_common_layout(fig, title_text: str):
    fig.update_layout(
        template="plotly_white",
        title=dict(text=title_text, font=dict(family="IBM Plex Mono", size=11, color="#6B7280")),
        margin=dict(l=40, r=40, t=50, b=40),
        font=dict(family="Inter", size=12),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
    )
    fig.update_xaxes(gridcolor="#F3F4F6", linecolor="#E5E7EB")
    fig.update_yaxes(gridcolor="#F3F4F6", linecolor="#E5E7EB")


def render_insights(df_master: pd.DataFrame, bench: pd.DataFrame):
    render_page_header("INSIGHTS", "ANALYTICAL FINDINGS FROM PUBLIC LP DISCLOSURE DATA")
    bench_meaningful = bench[bench["vintage_year"] <= 2020].sort_values("vintage_year")

    st.markdown('<div class="section-label">KEY FINDINGS</div>', unsafe_allow_html=True)
    insight_cards = [
        {
            "number": "01",
            "label": "DPI DROUGHT",
            "headline": "Post-2017 = paper",
            "body": "Every fund vintage 2017+ in this dataset — LP and market intel — has DPI < 0.5×. CA median DPI for 2017 vintage historically reaches ~1.0× by year 8. This cohort is running late.",
        },
        {
            "number": "02",
            "label": "HIGHEST DPI",
            "headline": "Founders Fund II: 18.6×",
            "body": "On a $227M 2007 vehicle. CA top-quartile DPI for 2007 vintage is ~2.1×. FFII at 18.6× is roughly 9× above top quartile — extreme concentration in Palantir and SpaceX.",
        },
        {
            "number": "03",
            "label": "BENCHMARK BEATER",
            "headline": "a16z Fund III",
            "body": "Net TVPI 11.3× vs CA Q1 of ~4.2× for 2012 vintage. Net DPI 5.5× vs CA Q1 of ~3.1×. Beats top quartile on both dimensions at $1B+ scale — exceptional.",
        },
        {
            "number": "04",
            "label": "FEE DRAG",
            "headline": "28% taken in carry",
            "body": "AH Fund III: Gross TVPI 15.7× → Net 11.3×. 28% of gross returns transferred to GP in fees and carry on a $997M fund ≈ $4.4B. Standard structure, rarely shown directly.",
        },
        {
            "number": "05",
            "label": "SELECTION BIAS",
            "headline": "Intel funds skew high",
            "body": "Market intelligence funds (a16z, Founders, Social Capital) in this dataset all sit above the CA Q1 line in IRR. The source of the leak may itself have been selective.",
        },
        {
            "number": "06",
            "label": "CHINA RISK",
            "headline": "HongShan collapse",
            "body": "HongShan 2010 vintage: 5.7× TVPI, 4.7× DPI. HongShan 2020 vintage: sub-1× TVPI, negative IRR. Same manager. China regulatory intervention erased the edge in 5 years.",
        },
    ]

    row1 = st.columns(3)
    row2 = st.columns(3)
    all_cols = row1 + row2
    for col, card in zip(all_cols, insight_cards):
        with col:
            st.markdown(
                """
            <div style="border:1px solid #E5E7EB;border-radius:6px;padding:16px;background:#fff;height:100%">
                <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:0.15em;
                    text-transform:uppercase;color:#9CA3AF;margin-bottom:4px">
                    {0} / {1}
                </div>
                <div style="font-family:'Inter',sans-serif;font-size:15px;font-weight:700;
                    color:#111827;margin-bottom:8px;line-height:1.2">
                    {2}
                </div>
                <div style="font-family:'Inter',sans-serif;font-size:12px;color:#6B7280;line-height:1.5">
                    {3}
                </div>
            </div>
            """.format(
                    html.escape(card["number"]),
                    html.escape(card["label"]),
                    html.escape(card["headline"]),
                    html.escape(card["body"]),
                ),
                unsafe_allow_html=True,
            )

    df = df_master.copy()
    lp_df = df[(df["irr_meaningful"] == True) & (df["data_source_type"] == "LP-Disclosed")].copy()
    mi_df = df[(df["irr_meaningful"] == True) & (df["data_source_type"] == "Market Intelligence")].copy()
    lp_df = lp_df[lp_df["net_irr"].notna() & (lp_df["net_irr"].abs() < 2.0)]
    mi_df = mi_df[mi_df["net_irr"].notna() & (mi_df["net_irr"].abs() < 2.0)]

    st.markdown('<div class="section-label">01 / FIRM LANDSCAPE</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown('<div class="chart-title">CASH RETURN RECORD</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-subtitle">X = funds with meaningful data · Y = median net DPI · size = total capital in dataset</div>', unsafe_allow_html=True)
        firm_summary = []
        for gp, grp in df.groupby("canonical_gp"):
            meaningful = grp[grp["irr_meaningful"] == True]
            r = grp.iloc[0]
            mode_source = grp["data_source_type"].mode()
            firm_summary.append(
                {
                    "firm": r.get("gp_display_name", gp),
                    "canonical_gp": gp,
                    "meaningful_count": len(meaningful),
                    "median_dpi": meaningful["dpi"].dropna().median() if len(meaningful) > 0 else 0,
                    "total_capital_bn": grp["fund_size_usd_m"].fillna(0).sum() / 1000.0,
                    "source_type": mode_source.iloc[0] if not mode_source.empty else "LP-Disclosed",
                }
            )
        firm_df = pd.DataFrame(firm_summary).dropna(subset=["median_dpi"])
        color_map = {"LP-Disclosed": "#2C3E50", "Market Intelligence": "#E8571F"}
        fig = px.scatter(
            firm_df,
            x="meaningful_count",
            y="median_dpi",
            size="total_capital_bn",
            text="firm",
            color="source_type",
            color_discrete_map=color_map,
            size_max=45,
            template="plotly_white",
            labels={"meaningful_count": "Funds with Meaningful Data", "median_dpi": "Median Net DPI (×)"},
        )
        fig.add_hline(
            y=1.0,
            line_dash="dash",
            line_color="#9CA3AF",
            line_width=1,
            annotation_text="1.0× — returned committed capital",
            annotation_position="bottom right",
            annotation_font_size=9,
        )
        fig.add_hline(
            y=2.0,
            line_dash="dash",
            line_color="#16A34A",
            line_width=1,
            annotation_text="2.0× — strong realization",
            annotation_position="bottom right",
            annotation_font_size=9,
        )
        fig.update_traces(textposition="top center", textfont_size=9, marker=dict(line=dict(width=1, color="white")))
        fig.update_layout(
            height=380,
            showlegend=True,
            legend=dict(title="Source", orientation="h", y=-0.18, font=dict(size=9)),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            xaxis=dict(gridcolor="#F3F4F6"),
            yaxis=dict(gridcolor="#F3F4F6"),
            font=dict(family="Inter", size=11),
            margin=dict(l=40, r=40, t=30, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="chart-title">FUND COVERAGE TIMELINE</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-subtitle">Each square = one fund · color = DPI realization level</div>', unsafe_allow_html=True)
        tl = df[df["vintage_year"].notna()].copy()
        tl["dpi_safe"] = tl["dpi"].fillna(0)

        def dpi_color(v):
            if v > 2.0:
                return "#E8571F"
            if v > 1.0:
                return "#6EE7B7"
            if v > 0.1:
                return "#FCD34D"
            return "#E5E7EB"

        tl["dot_color"] = tl["dpi_safe"].apply(dpi_color)
        fig2 = go.Figure()
        firms_order = tl.groupby("canonical_gp")["vintage_year"].min().sort_values().index
        for gp in firms_order:
            sub = tl[tl["canonical_gp"] == gp].sort_values("vintage_year")
            disp = str(sub.iloc[0].get("gp_display_name", gp))
            for _, r in sub.iterrows():
                fig2.add_trace(
                    go.Scatter(
                        x=[int(r["vintage_year"])],
                        y=[disp],
                        mode="markers",
                        marker=dict(symbol="square", size=12, color=r["dot_color"], line=dict(width=1, color="#9CA3AF")),
                        showlegend=False,
                        hovertemplate="<b>{0}</b><br>Vintage: {1}<br>DPI: {2}<br>TVPI: {3}<extra></extra>".format(
                            html.escape(str(r.get("fund_name", ""))),
                            r.get("vintage_year", "N/A"),
                            "N/A" if pd.isna(r.get("dpi")) else "{0:.2f}×".format(r.get("dpi")),
                            "N/A" if pd.isna(r.get("tvpi")) else "{0:.2f}×".format(r.get("tvpi")),
                        ),
                    )
                )
        for label, color in [
            ("> 2× DPI", "#E8571F"),
            ("1–2× DPI", "#6EE7B7"),
            ("0.1–1× DPI", "#FCD34D"),
            ("< 0.1× / None", "#E5E7EB"),
        ]:
            fig2.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="markers",
                    marker=dict(symbol="square", size=10, color=color, line=dict(width=1, color="#9CA3AF")),
                    name=label,
                    showlegend=True,
                )
            )
        fig2.update_layout(
            height=380,
            template="plotly_white",
            xaxis=dict(title="Vintage Year", gridcolor="#F3F4F6", dtick=3),
            yaxis=dict(title="", tickfont=dict(size=9)),
            legend=dict(title="DPI Range", font=dict(size=9), orientation="h", y=-0.18),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            font=dict(family="Inter", size=10),
            margin=dict(l=10, r=20, t=30, b=40),
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-label">02 / RETURNS — LP-DISCLOSED + MARKET INTEL vs CA BENCHMARK</div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(bench_meaningful["vintage_year"]) + list(bench_meaningful["vintage_year"])[::-1],
            y=list(bench_meaningful["q1_net_irr"] * 100) + list(bench_meaningful["q3_net_irr"] * 100)[::-1],
            fill="toself",
            fillcolor="rgba(16,185,129,0.07)",
            line=dict(color="rgba(0,0,0,0)"),
            name="CA Q3–Q1 Band (approx.)",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=bench_meaningful["vintage_year"],
            y=bench_meaningful["q1_net_irr"] * 100,
            mode="lines",
            line=dict(color="#16A34A", width=1.5, dash="dash"),
            name="CA Top Quartile (approx.)",
            hovertemplate="Vintage %{x}<br>CA Q1: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=bench_meaningful["vintage_year"],
            y=bench_meaningful["median_net_irr"] * 100,
            mode="lines",
            line=dict(color="#9CA3AF", width=1.5, dash="dot"),
            name="CA Median (approx.)",
            hovertemplate="Vintage %{x}<br>CA Median: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=lp_df["vintage_year"],
            y=lp_df["net_irr"] * 100,
            mode="markers",
            marker=dict(
                symbol="circle",
                size=lp_df["fund_size_usd_m"].fillna(50).clip(50, 3000) / 65,
                color="#2C3E50",
                opacity=0.7,
                line=dict(width=1, color="white"),
            ),
            name="LP-Disclosed (FOIA)",
            customdata=lp_df[["fund_name", "canonical_gp", "tvpi", "dpi"]].values,
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>IRR: %{y:.1f}%<br>TVPI: %{customdata[2]:.2f}×<br>DPI: %{customdata[3]:.2f}×<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=mi_df["vintage_year"],
            y=mi_df["net_irr"] * 100,
            mode="markers",
            marker=dict(
                symbol="diamond",
                size=mi_df["fund_size_usd_m"].fillna(50).clip(50, 3000) / 65,
                color="#FFF4EF",
                opacity=0.95,
                line=dict(width=2, color="#E8571F"),
            ),
            name="Market Intelligence (Circulated)",
            customdata=mi_df[["fund_name", "canonical_gp", "tvpi", "dpi"]].values,
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>IRR: %{y:.1f}%<br>TVPI: %{customdata[2]:.2f}×<br>DPI: %{customdata[3]:.2f}×<br><i>Market Intelligence — unverified provenance</i><extra></extra>",
        )
    )
    fig.add_annotation(
        x=2013,
        y=34,
        text="Market intel funds (◆)<br>cluster above Q1 line<br>— source may be selective",
        showarrow=True,
        arrowhead=2,
        arrowcolor="#E8571F",
        arrowwidth=1.5,
        font=dict(size=9, color="#E8571F", family="IBM Plex Mono"),
        bgcolor="#FFF4EF",
        bordercolor="#E8571F",
        borderwidth=1,
        borderpad=6,
        ax=80,
        ay=-50,
    )
    fig.update_layout(
        title=dict(
            text="NET IRR BY VINTAGE — LP-DISCLOSED vs MARKET INTEL vs CA BENCHMARK",
            font=dict(family="IBM Plex Mono", size=11, color="#6B7280"),
        ),
        height=500,
        template="plotly_white",
        xaxis=dict(title="Vintage Year", gridcolor="#F3F4F6", dtick=2),
        yaxis=dict(title="Net IRR (%)", gridcolor="#F3F4F6"),
        legend=dict(orientation="h", y=-0.2, font=dict(size=10)),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font=dict(family="Inter", size=12),
    )
    st.plotly_chart(fig, use_container_width=True)
    bench_disclaimer()
    st.markdown(
        """
    <div class="insight-box">
        <div class="insight-label">● READING THIS CHART</div>
        <div class="insight-body">
            <strong>● circles = LP-disclosed</strong> — independently reported by pension funds
            under FOIA. Scattered across the full distribution including underperformers.
            <strong>◆ diamonds = market intelligence</strong> — data that circulated through
            secondary market and LP channels for a16z, Founders Fund, and Social Capital.
            Notice diamonds cluster above the Q1 line. This may reflect genuine outperformance
            by these firms — or it may reflect that the source of the circulated data was
            selective. The green band is the approximate Cambridge Associates Q3–Q1 range.
            <em>Funds inside the band are performing between median and top quartile for their vintage.</em>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label" style="margin-top:2rem">02A / THE GROSS vs NET GAP — FEES QUANTIFIED</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-subtitle">a16z is the only firm in this dataset with both gross and net metrics in the circulated data. The gap = management fees + carry transferred from LP to GP.</div>', unsafe_allow_html=True)
    a16z_rows = [
        {"fund": "AH Fund I", "vintage": 2009, "size": 300, "gross_tvpi": 9.3, "net_tvpi": 6.9, "net_dpi": 6.0},
        {"fund": "AH Fund II", "vintage": 2010, "size": 656, "gross_tvpi": 4.9, "net_tvpi": 3.7, "net_dpi": 3.5},
        {"fund": "AH Annex", "vintage": 2011, "size": 204, "gross_tvpi": 7.2, "net_tvpi": 5.4, "net_dpi": 5.1},
        {"fund": "AH Fund III", "vintage": 2012, "size": 997, "gross_tvpi": 15.7, "net_tvpi": 11.3, "net_dpi": 5.5},
        {"fund": "AH Fund IV", "vintage": 2014, "size": 1173, "gross_tvpi": 5.5, "net_tvpi": 4.1, "net_dpi": 3.0},
        {"fund": "AH Fund V", "vintage": 2017, "size": 1189, "gross_tvpi": 4.0, "net_tvpi": 3.1, "net_dpi": 0.3},
    ]
    table_rows = ""
    for d in a16z_rows:
        drag = d["gross_tvpi"] - d["net_tvpi"]
        drag_pct = (drag / d["gross_tvpi"] * 100) if d["gross_tvpi"] else np.nan
        drag_usd_m = drag * d["size"]
        dpi_color = "#E8571F" if d["net_dpi"] >= 1.5 else ("#D97706" if d["net_dpi"] >= 0.5 else "#9CA3AF")
        table_rows += (
            "<tr>"
            '<td style="font-weight:500">{0}</td><td class="numeric">{1}</td><td class="numeric">${2:,}M</td>'
            '<td class="numeric" style="color:#6B7280">{3:.1f}×</td><td class="numeric" style="font-weight:600;color:#111827">{4:.1f}×</td>'
            '<td class="numeric" style="color:#DC2626">−{5:.1f}× <span style="font-size:9px;color:#9CA3AF">({6:.0f}% / ${7:.1f}B)</span></td>'
            '<td class="numeric" style="color:{8};font-weight:600">{9:.1f}×</td></tr>'
        ).format(
            d["fund"],
            d["vintage"],
            d["size"],
            d["gross_tvpi"],
            d["net_tvpi"],
            drag,
            drag_pct,
            drag_usd_m / 1000.0,
            dpi_color,
            d["net_dpi"],
        )
    _render_html(
        '<table class="fund-table"><thead><tr><th>FUND</th><th class="right">VINTAGE</th><th class="right">SIZE</th>'
        '<th class="right">GROSS TVPI</th><th class="right">NET TVPI</th>'
        '<th class="right" style="color:#DC2626">FEE DRAG (×  /  $)</th><th class="right" style="color:#E8571F">NET DPI ▲</th>'
        "</tr></thead><tbody>{0}</tbody></table>".format(table_rows)
    )
    st.markdown(
        """
    <div class="insight-box" style="margin-top:1rem">
        <div class="insight-label">● WHAT THIS TABLE SHOWS</div>
        <div class="insight-body">
            Fee drag = gross TVPI minus net TVPI. For AH Fund III, 4.4× drag on $997M ≈
            <strong>$4.4B transferred from LPs to a16z in management fees and carry</strong>.
            This is standard 2/20 structure — not predatory. But it's rarely shown this
            concretely. Note AH Fund V (2017): Net DPI is only 0.3× despite Net TVPI of 3.1×
            — <em>LPs have received less than a third of their committed capital back in cash,
            a decade in.</em>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label" style="margin-top:2rem">02B / THE REALIZATION MAP</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-subtitle">Each point = one fund. X = DPI (cash returned). Y = TVPI (total value including paper). Color = vintage era.</div>', unsafe_allow_html=True)
    plot_df = df[df["tvpi"].notna() & df["dpi"].notna()].copy()
    plot_df["vintage_bucket"] = pd.cut(
        plot_df["vintage_year"].astype(float),
        bins=[1999, 2014, 2017, 2030],
        labels=["Pre-2015 (Mature)", "2015–2017 (DPI Drought Onset)", "Post-2017 (Paper Only)"],
    )
    bucket_colors = {
        "Pre-2015 (Mature)": "#16A34A",
        "2015–2017 (DPI Drought Onset)": "#D97706",
        "Post-2017 (Paper Only)": "#DC2626",
    }
    max_dpi = min(plot_df["dpi"].max() + 0.5, 20) if not plot_df.empty else 4.0
    max_tvpi = min(plot_df["tvpi"].max() + 0.5, 20) if not plot_df.empty else 4.0
    max_val = max(max_dpi, max_tvpi)
    fig_map = go.Figure()
    fig_map.add_shape(type="rect", x0=0, y0=2.0, x1=0.99, y1=max_val, fillcolor="rgba(239,68,68,0.04)", line=dict(width=0))
    fig_map.add_shape(type="rect", x0=1.0, y0=2.0, x1=max_val, y1=max_val, fillcolor="rgba(22,163,74,0.04)", line=dict(width=0))
    fig_map.add_vline(
        x=1.0,
        line_dash="dash",
        line_color="#6B7280",
        line_width=1,
        annotation_text="1.0× DPI — committed capital returned",
        annotation_position="top right",
        annotation_font_size=9,
    )
    fig_map.add_trace(
        go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode="lines",
            line=dict(color="#9CA3AF", dash="dot", width=1),
            name="DPI = TVPI (fully realized)",
            showlegend=True,
            hoverinfo="skip",
        )
    )
    for bucket, color in bucket_colors.items():
        sub = plot_df[plot_df["vintage_bucket"].astype(str) == bucket]
        if len(sub) == 0:
            continue
        fig_map.add_trace(
            go.Scatter(
                x=sub["dpi"],
                y=sub["tvpi"],
                mode="markers",
                marker=dict(size=sub["fund_size_usd_m"].fillna(50).clip(50, 3000) / 55, color=color, opacity=0.70, line=dict(width=1, color="white")),
                name=bucket,
                customdata=sub[["fund_name", "canonical_gp", "vintage_year", "net_irr", "fund_size_usd_m", "data_source_type"]].values,
                hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<br>TVPI: %{y:.2f}× | DPI: %{x:.2f}×<br>IRR: %{customdata[3]:.1%}<br>%{customdata[5]}<extra></extra>",
            )
        )
    may = plot_df[plot_df["fund_name"].astype(str).str.contains("XIV", na=False)]
    if len(may):
        fig_map.add_trace(
            go.Scatter(
                x=may["dpi"],
                y=may["tvpi"],
                mode="markers+text",
                marker=dict(symbol="star", size=18, color="#E8571F", line=dict(width=1.5, color="white")),
                text=["Mayfield XIV"] * len(may),
                textposition="top right",
                textfont=dict(size=9, color="#E8571F", family="IBM Plex Mono"),
                name="Mayfield XIV ★",
                showlegend=True,
            )
        )
    fig_map.add_annotation(
        x=0.2,
        y=max_val * 0.88,
        text="PAPER GAINS ZONE<br>High TVPI, Low DPI",
        font=dict(size=9, color="#DC2626", family="IBM Plex Mono"),
        showarrow=False,
        bgcolor="rgba(254,242,242,0.85)",
    )
    fig_map.add_annotation(
        x=max_val * 0.65,
        y=max_val * 0.88,
        text="REAL RETURNS ZONE<br>High TVPI, High DPI",
        font=dict(size=9, color="#16A34A", family="IBM Plex Mono"),
        showarrow=False,
        bgcolor="rgba(240,253,244,0.85)",
    )
    fig_map.update_layout(
        title=dict(text="TVPI vs DPI — THE REALIZATION MAP", font=dict(family="IBM Plex Mono", size=11, color="#6B7280")),
        height=500,
        template="plotly_white",
        xaxis=dict(title="Net DPI (× distributed to LPs)", range=[0, max_val], gridcolor="#F3F4F6"),
        yaxis=dict(title="Net TVPI (× total value)", range=[0, max_val], gridcolor="#F3F4F6"),
        legend=dict(orientation="h", y=-0.2, font=dict(size=10)),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font=dict(family="Inter", size=12),
    )
    st.plotly_chart(fig_map, use_container_width=True)

    st.markdown('<div class="section-label" style="margin-top:2rem">02C / NET IRR RANKING — HOVER FOR vs BENCHMARK</div>', unsafe_allow_html=True)
    rank_df = lp_df.copy()
    rank_df = rank_df.merge(bench[["vintage_year", "median_net_irr", "q1_net_irr"]], on="vintage_year", how="left")
    rank_df["irr_pct"] = rank_df["net_irr"] * 100
    rank_df["vs_median_pp"] = rank_df["irr_pct"] - rank_df["median_net_irr"] * 100
    rank_df["vs_q1_pp"] = rank_df["irr_pct"] - rank_df["q1_net_irr"] * 100
    rank_df["est_quartile"] = rank_df["vs_q1_pp"].apply(lambda x: "Q1 (Top)" if x >= 0 else ("Q2" if x >= -5 else "Q3+"))
    rank_df["short_label"] = rank_df.apply(lambda r: "{0} ({1})".format(str(r["fund_name"])[:32], r["canonical_gp"]), axis=1)
    rank_df["bar_color"] = rank_df["irr_pct"].apply(lambda x: "#16A34A" if x >= 20 else ("#D97706" if x >= 10 else "#DC2626"))
    rank_df = rank_df.sort_values("irr_pct", ascending=True)
    avg_q1 = rank_df["q1_net_irr"].mean() * 100 if not rank_df.empty else 0
    fig_rank = go.Figure()
    fig_rank.add_trace(
        go.Bar(
            y=rank_df["short_label"],
            x=rank_df["irr_pct"],
            orientation="h",
            marker_color=rank_df["bar_color"].tolist(),
            customdata=rank_df[["vintage_year", "tvpi", "dpi", "vs_median_pp", "vs_q1_pp", "est_quartile"]].values,
            hovertemplate="<b>%{y}</b><br>IRR: %{x:.1f}%<br>Vintage: %{customdata[0]}<br>TVPI: %{customdata[1]:.2f}× | DPI: %{customdata[2]:.2f}×<br>vs CA Median: %{customdata[3]:+.1f}pp<br>vs CA Q1: %{customdata[4]:+.1f}pp<br>Est. Quartile: %{customdata[5]}<extra></extra>",
        )
    )
    fig_rank.add_vline(x=avg_q1, line_dash="dash", line_color="#16A34A", line_width=1, annotation_text="Avg CA Q1 ({0:.0f}%)".format(avg_q1), annotation_font_size=9)
    fig_rank.add_vline(x=10, line_dash="dot", line_color="#9CA3AF", line_width=1, annotation_text="10% floor", annotation_font_size=9)
    fig_rank.update_layout(
        height=max(400, len(rank_df) * 22),
        template="plotly_white",
        xaxis=dict(title="Net IRR (%)", gridcolor="#F3F4F6"),
        yaxis=dict(tickfont=dict(size=9)),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font=dict(family="Inter", size=10),
        margin=dict(l=300, r=80, t=30, b=40),
    )
    st.plotly_chart(fig_rank, use_container_width=True)
    bench_disclaimer()

    st.markdown('<div class="section-label">03 / VINTAGE COHORT ANALYSIS</div>', unsafe_allow_html=True)
    col3a, col3b = st.columns(2)
    with col3a:
        st.markdown('<div class="chart-title">TVPI BY VINTAGE — vs CA BENCHMARK</div>', unsafe_allow_html=True)
        tvpi_df = lp_df[lp_df["tvpi"].notna()].copy()
        tvpi_df["x_jitter"] = tvpi_df["vintage_year"].astype(float) + np.random.uniform(-0.25, 0.25, len(tvpi_df))
        fig_tvpi = go.Figure()
        fig_tvpi.add_trace(
            go.Scatter(
                x=list(bench_meaningful["vintage_year"]) + list(bench_meaningful["vintage_year"])[::-1],
                y=list(bench_meaningful["q1_tvpi"]) + list(bench_meaningful["q3_tvpi"])[::-1],
                fill="toself",
                fillcolor="rgba(16,185,129,0.07)",
                line=dict(color="rgba(0,0,0,0)"),
                name="CA Q3–Q1 TVPI Band",
                hoverinfo="skip",
            )
        )
        fig_tvpi.add_trace(
            go.Scatter(
                x=bench_meaningful["vintage_year"],
                y=bench_meaningful["median_tvpi"],
                mode="lines",
                line=dict(color="#9CA3AF", dash="dot", width=1.5),
                name="CA Median TVPI",
            )
        )
        fig_tvpi.add_trace(
            go.Scatter(
                x=tvpi_df["x_jitter"],
                y=tvpi_df["tvpi"],
                mode="markers",
                marker=dict(size=7, color="#2C3E50", opacity=0.6, line=dict(width=0.5, color="white")),
                name="LP-Disclosed Fund",
                customdata=tvpi_df[["fund_name", "canonical_gp", "dpi"]].values,
                hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>TVPI: %{y:.2f}× | DPI: %{customdata[2]:.2f}×<extra></extra>",
            )
        )
        medians = tvpi_df.groupby("vintage_year")["tvpi"].median().reset_index()
        fig_tvpi.add_trace(
            go.Scatter(
                x=medians["vintage_year"],
                y=medians["tvpi"],
                mode="lines+markers",
                line=dict(color="#E8571F", width=2),
                marker=dict(size=6, color="#E8571F"),
                name="This Dataset Median",
            )
        )
        fig_tvpi.add_hline(y=1.0, line_dash="dot", line_color="#9CA3AF", line_width=1)
        fig_tvpi.update_layout(
            height=380,
            template="plotly_white",
            xaxis=dict(title="Vintage Year", gridcolor="#F3F4F6", dtick=2),
            yaxis=dict(title="Net TVPI (×)", gridcolor="#F3F4F6"),
            legend=dict(font=dict(size=9)),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            font=dict(family="Inter", size=11),
            margin=dict(t=20, b=30),
        )
        st.plotly_chart(fig_tvpi, use_container_width=True)
        n_per = tvpi_df.groupby("vintage_year").size().to_dict()
        n_str = "  ·  ".join(["{0}: n={1}".format(y, n) for y, n in sorted(n_per.items()) if y >= 2005])
        st.markdown("<div style=\"font-family:'IBM Plex Mono',monospace;font-size:9px;color:#9CA3AF\">{0}</div>".format(html.escape(n_str)), unsafe_allow_html=True)
        bench_disclaimer()

    with col3b:
        st.markdown('<div class="chart-title">CAPITAL REALIZATION BY VINTAGE</div>', unsafe_allow_html=True)
        cohort = lp_df.copy()
        cohort["cap"] = cohort["fund_size_usd_m"].fillna(0)
        cohort["dist"] = cohort["dpi"].fillna(0) * cohort["cap"]
        agg = cohort.groupby("vintage_year").agg(total=("cap", "sum"), distributed=("dist", "sum")).reset_index()
        agg["unrealized"] = (agg["total"] - agg["distributed"]).clip(lower=0)
        agg["pct"] = (agg["distributed"] / agg["total"].replace(0, np.nan) * 100).clip(0, 100).round(0)
        agg = agg[agg["vintage_year"] >= 2005]
        fig_cap = go.Figure()
        fig_cap.add_trace(go.Bar(x=agg["vintage_year"], y=agg["distributed"] / 1000.0, name="Realized (DPI × Contributed)", marker_color="#E8571F"))
        fig_cap.add_trace(go.Bar(x=agg["vintage_year"], y=agg["unrealized"] / 1000.0, name="Unrealized (Paper)", marker_color="#E5E7EB"))
        for _, r in agg.iterrows():
            fig_cap.add_annotation(
                x=r["vintage_year"],
                y=r["total"] / 1000.0 + 0.1,
                text="{0:.0f}%".format(r["pct"]),
                showarrow=False,
                font=dict(size=8, color="#6B7280", family="IBM Plex Mono"),
            )
        fig_cap.update_layout(
            barmode="stack",
            height=380,
            template="plotly_white",
            xaxis=dict(title="Vintage Year", gridcolor="#F3F4F6", dtick=2),
            yaxis=dict(title="Capital ($B)", gridcolor="#F3F4F6"),
            legend=dict(font=dict(size=9), orientation="h", y=-0.18),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            font=dict(family="Inter", size=11),
            margin=dict(t=20, b=40),
        )
        st.plotly_chart(fig_cap, use_container_width=True)
        st.markdown("<div style=\"font-family:'IBM Plex Mono',monospace;font-size:9px;color:#9CA3AF\">% = realization rate per vintage. Orange = cash distributed to LPs. Grey = unrealized paper value.</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-label">04 / GP PERFORMANCE TRAJECTORIES</div>', unsafe_allow_html=True)
    col4a, col4b = st.columns(2)
    with col4a:
        st.markdown('<div class="chart-title">IRR TRAJECTORY — FIRMS WITH 3+ FUNDS</div>', unsafe_allow_html=True)
        traj = lp_df[lp_df["net_irr"].notna()].copy()
        eligible = traj.groupby("canonical_gp").size()
        eligible = eligible[eligible >= 3].index
        traj = traj[traj["canonical_gp"].isin(eligible)]
        traj = traj.merge(bench[["vintage_year", "median_net_irr"]], on="vintage_year", how="left")
        fig_traj = go.Figure()
        for gp in traj["canonical_gp"].dropna().unique():
            sub = traj[traj["canonical_gp"] == gp].sort_values("vintage_year")
            fig_traj.add_trace(
                go.Scatter(
                    x=sub["vintage_year"],
                    y=sub["net_irr"] * 100,
                    mode="lines+markers",
                    name=sub.iloc[0].get("gp_display_name", gp),
                    line=dict(width=2),
                    marker=dict(size=7),
                )
            )
        fig_traj.add_trace(
            go.Scatter(
                x=bench_meaningful["vintage_year"],
                y=bench_meaningful["median_net_irr"] * 100,
                mode="lines",
                name="CA Median (approx.)",
                line=dict(color="#9CA3AF", dash="dot", width=1.5),
            )
        )
        fig_traj.update_layout(
            height=380,
            template="plotly_white",
            xaxis=dict(gridcolor="#F3F4F6"),
            yaxis=dict(title="Net IRR (%)", gridcolor="#F3F4F6"),
            legend=dict(font=dict(size=9)),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            font=dict(family="Inter", size=11),
            margin=dict(t=20),
        )
        st.plotly_chart(fig_traj, use_container_width=True)
        bench_disclaimer()

    with col4b:
        st.markdown('<div class="chart-title">CASH RETURNED BY STRATEGY — CAPITAL-WEIGHTED DPI</div>', unsafe_allow_html=True)
        strat = lp_df[lp_df["dpi"].notna() & lp_df["fund_size_usd_m"].notna()].copy()
        strat["weighted"] = strat["dpi"] * strat["fund_size_usd_m"]
        agg_s = strat.groupby("fund_category").agg(weighted_sum=("weighted", "sum"), total_cap=("fund_size_usd_m", "sum"), n=("fund_name", "count")).reset_index()
        agg_s["wtd_dpi"] = agg_s["weighted_sum"] / agg_s["total_cap"]
        agg_s = agg_s.sort_values("wtd_dpi", ascending=True)
        colors = [CATEGORY_COLORS.get(c, "#9CA3AF") for c in agg_s["fund_category"]]
        fig_strat = go.Figure()
        fig_strat.add_trace(
            go.Bar(
                y=agg_s["fund_category"],
                x=agg_s["wtd_dpi"],
                orientation="h",
                marker_color=colors,
                customdata=agg_s[["total_cap", "n"]].values,
                hovertemplate="<b>%{y}</b><br>Wtd DPI: %{x:.2f}×<br>Capital: $%{customdata[0]:.0f}M<br>Funds: %{customdata[1]}<extra></extra>",
            )
        )
        fig_strat.add_vline(x=1.0, line_dash="dash", line_color="#9CA3AF", annotation_text="1.0×", annotation_font_size=9)
        fig_strat.update_layout(
            height=380,
            template="plotly_white",
            xaxis=dict(title="Capital-Weighted Avg Net DPI (×)", gridcolor="#F3F4F6"),
            yaxis=dict(gridcolor="#F3F4F6"),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            font=dict(family="Inter", size=11),
            margin=dict(t=20, l=20),
        )
        st.plotly_chart(fig_strat, use_container_width=True)
        st.markdown("<div style=\"font-family:'IBM Plex Mono',monospace;font-size:9px;color:#9CA3AF\">Capital-weighted: larger funds influence the average proportionally. LP-disclosed funds only.</div>", unsafe_allow_html=True)

    st.markdown(
        """
    <div class="insight-box" style="margin-top:2rem">
        <div class="insight-label">● ANALYST INSIGHT — MARKET INTEL vs LP DATA</div>
        <div class="insight-body">
            <strong>The gross/net gap is the most underappreciated number in VC.</strong>
            a16z Fund III shows 15.7× gross TVPI vs 11.3× net — a 28% reduction in returns
            from fees and carry. Founders Fund's early funds show extraordinary DPI figures
            (18.6× for FFII), but these reflect $227M vehicles with extreme concentration
            in Palantir and SpaceX. At $1.4B+ fund sizes (FFVI onward), DPI collapses to
            near-zero — the same structural challenge every large fund faces.
            <br><br>
            <em>The market intelligence data that circulates through the ecosystem tends to
            cluster above the CA top-quartile line. Whether this reflects genuine outperformance
            by the firms whose numbers circulate, or selection bias in what gets leaked and
            forwarded, is difficult to disentangle. Treat it as a directional signal, not
            a verified benchmark.</em>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_source_row(cfg: dict, row_count: int, coverage_label: str = "COVERAGE"):
    pct = cfg["coverage"]
    bar_class = "high" if pct >= 80 else "medium" if pct >= 50 else "low"

    st.markdown(
        """
    <div class="source-row">
        <div>
            <div class="source-name">{0}</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#9CA3AF;margin-top:2px">{1} RECORDS</div>
        </div>
        <div><span class="badge {2}">{3}</span></div>
        <div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:0.08em;text-transform:uppercase;color:#9CA3AF;margin-bottom:4px">{8}</div>
            <div class="coverage-bar-wrap">
                <div class="coverage-bar-bg"><div class="coverage-bar-fill {4}" style="width:{5}%"></div></div>
                <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#374151;min-width:32px">{5}%</span>
            </div>
        </div>
        <div class="source-sync">{6}</div>
        <div class="source-notes">{7}</div>
    </div>
    """.format(
            html.escape(cfg["name"]),
            "{0:,}".format(row_count),
            html.escape(cfg["badge_class"]),
            html.escape(cfg["classification"]),
            bar_class,
            pct,
            html.escape(cfg["period"]),
            html.escape(cfg["notes"]),
            html.escape(coverage_label),
        ),
        unsafe_allow_html=True,
    )


def render_sources(df_unified: pd.DataFrame, df_master: pd.DataFrame):
    render_page_header("SOURCES", "DATA PROVENANCE & COVERAGE TRANSPARENCY")

    st.markdown(
        """
    <div style="display:grid;grid-template-columns:160px 1fr;gap:2rem;padding:2rem 0;border-top:1px solid #E5E7EB">
        <div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.1em;color:#E8571F;text-transform:uppercase">01 / METHODOLOGY</div>
        </div>
        <div style="font-family:'Inter',sans-serif;font-size:14px;color:#374151;line-height:1.7">
            All data sourced from public LP disclosures filed under FOIA or published voluntarily
            by institutional investors. Performance metrics (IRR, TVPI, DPI) are as-reported by
            the LP, not the GP — meaning they reflect each LP's own cash flow timing and fee
            treatment. Figures from different LPs for the same fund may differ slightly.
            <br><br>
            DPI is computed as
            <code style="font-family:'IBM Plex Mono',monospace;background:#F3F4F6;padding:1px 6px;border-radius:3px">capital_distributed / capital_contributed</code>.
            TVPI is computed as
            <code style="font-family:'IBM Plex Mono',monospace;background:#F3F4F6;padding:1px 6px;border-radius:3px">(distributed + NAV) / contributed</code>
            where not directly reported.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">02 / DATA INTAKE LEDGER</div>', unsafe_allow_html=True)

    st.markdown(
        """
    <div class="source-row" style="border-bottom:1px solid #E5E7EB;padding:8px 0">
        <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#9CA3AF">SOURCE</span>
        <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#9CA3AF">CLASS</span>
        <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#9CA3AF">COVERAGE</span>
        <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#9CA3AF">PERIOD</span>
        <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#9CA3AF">NOTES</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    src_counts = df_unified["source"].value_counts(dropna=False).to_dict()
    for cfg in SOURCES_CONFIG:
        row_count = int(src_counts.get(cfg["row_count_key"], 0))
        render_source_row(cfg, row_count)

    st.markdown('<div class="section-label">03 / MARKET INTELLIGENCE SOURCES</div>', unsafe_allow_html=True)
    st.markdown(
        """
    <div style="font-family:'Inter',sans-serif;font-size:14px;color:#374151;line-height:1.7;
        padding:16px 20px;background:#FFF7ED;border-radius:6px;border:1px solid #FED7AA;margin-bottom:1.5rem">
        <strong>Market Intelligence</strong> refers to performance data that circulates through
        the private markets ecosystem — via secondary market processes, LP quarterly reports
        that get forwarded, placement agent materials, and investor community channels.
        Unlike LP-disclosed FOIA data, this data was not independently submitted under legal
        obligation. Provenance is unverified and mark vintage may vary. Figures are
        directionally useful but should not be treated as audited performance records.
    </div>
    """,
        unsafe_allow_html=True,
    )

    gp_counts = df_master[df_master["data_source_type"] == "Market Intelligence"]["source"].value_counts(dropna=False).to_dict()
    for cfg in GP_SOURCES_CONFIG:
        row_count = int(gp_counts.get(cfg["source_key"], cfg["fund_count"]))
        render_source_row(cfg, row_count, coverage_label="DISCLOSED UNIVERSE COVERAGE")

    st.markdown('<div class="section-label">04 / BENCHMARK DATA</div>', unsafe_allow_html=True)
    st.markdown(
        """
    <div style="display:grid;grid-template-columns:180px 1fr;gap:2rem;padding:2rem 0;border-top:1px solid #E5E7EB">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.1em;color:#E8571F;text-transform:uppercase">
            CA BENCHMARKS<br>(APPROXIMATE)
        </div>
        <div style="font-family:'Inter',sans-serif;font-size:14px;color:#374151;line-height:1.7">
            Benchmark figures (median IRR, top quartile IRR, median TVPI by vintage year) are
            <strong>approximate</strong> — synthesized from three public sources:
            <br><br>
            <strong>1. Public LP Annual Reports</strong> — CalPERS, WSIB, and other pensions
            routinely publish their portfolio returns compared to Cambridge Associates benchmarks.
            These references allow backward-inference of approximate CA values.<br>
            <strong>2. Academic Literature</strong> — Harris, Jenkinson, Kaplan &amp; Stucke (2014)
            using Burgiss fund-level data; Kaplan &amp; Schoar (2005). Burgiss data closely
            mirrors CA methodology.<br>
            <strong>3. Social Capital's CA Quartile Rankings</strong> — the only fund-level
            CA rankings in this dataset that are independently confirmed. Used as spot-check
            calibration points for 2011–2018 vintages.
            <br><br>
            Cambridge Associates' actual benchmark data is proprietary. The figures in
            <code style="font-family:'IBM Plex Mono',monospace;background:#F3F4F6;padding:1px 6px;border-radius:3px">ca_benchmarks.csv</code>
            are directional reference bands — accurate enough to identify top-quartile
            outperformers and underperformers, not precise enough for formal LP reporting.
            Every chart using these benchmarks includes a disclaimer.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <div class="insight-box" style="margin-top:2rem">
        <div class="insight-label">● DATA QUALITY NOTES</div>
        <div class="insight-body">
            <strong>IRR = 1.0 is a placeholder.</strong> CalPERS files report IRR = 1.0 for funds
            that are too early for meaningful measurement. These are flagged and excluded from
            all performance analysis.<br><br>
            <strong>DPI = 0.00× on post-2017 funds is expected.</strong> This reflects the
            industry-wide distribution drought, not a data error.<br><br>
            <em>Coverage % reflects completeness of IRR/TVPI/DPI fields, not fund count.
            All LP sources are publicly accessible without paywalls.</em>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_about():
    render_page_header("ABOUT", "PROJECT CONTEXT, METHOD, AND LIMITATIONS")

    _render_html(
        """
        <div style="font-family:'Inter',sans-serif;font-size:14px;color:#374151;line-height:1.75;
                    padding:18px 20px;background:#FAFAFA;border-radius:8px;border:1px solid #E5E7EB;">
            <strong>Show Me the DPI</strong> is a research project focused on one practical question:
            how much cash VC/PE funds have actually returned to LPs. The dataset combines public LP disclosures
            from pension systems and endowments with clearly-labeled market intelligence performance where available.
            <br><br>
            The core metric is <strong>DPI</strong> (Distributed-to-Paid-In), shown in orange across the product.
            TVPI and IRR are included for context, but DPI is prioritized because it reflects realized outcomes,
            not only unrealized marks.
            <br><br>
            This is not investment advice and not a complete census of all funds. LP-reported and market intelligence numbers
            can differ due to reporting dates, valuation policies, fees/carry treatment, and selective disclosure.
            Use this as a starting point for diligence and always cross-check original filings where possible.
        </div>
        """
    )

    st.markdown('<div class="section-label">WHAT THIS TOOL EMPHASIZES</div>', unsafe_allow_html=True)
    _render_html(
        """
        <ul style="margin-top:0; color:#374151; line-height:1.7;">
          <li>Cash realization first (DPI), then valuation context (TVPI), then annualized return (IRR).</li>
          <li>Source transparency on every page, with LP vs market intelligence separation.</li>
          <li>Analyst-friendly structure for fast comparison across firms, vintages, and source types.</li>
        </ul>
        """
    )


def render_footer():
    _render_html(
        """
        <div class="footer-wrap">
            <div class="footer-text">
                Data is compiled from public disclosures and select market intelligence records. Figures may differ by LP methodology,
                valuation date, and fee treatment. Market intelligence data can include selection bias and unverified provenance.
            </div>
            <div class="footer-text footer-links" style="margin-top:6px;">
                Created by resident venture nerd — Shivam Bhotika ·
                <a href="https://x.com/shivambhotika" target="_blank">Twitter</a> ·
                <a href="https://shivambhotika.github.io/" target="_blank">Website</a>
            </div>
        </div>
        """
    )


def main():
    try:
        df_unified = load_unified()
    except Exception as exc:
        st.error("Failed loading data/unified_funds.csv: {0}".format(exc))
        return

    try:
        df_market_intel = load_market_intel()
    except Exception as exc:
        st.error("Failed loading gp_disclosed_funds.csv: {0}".format(exc))
        df_market_intel = pd.DataFrame()

    try:
        df_master = load_master_full()
    except Exception as exc:
        st.error("Failed loading vc_fund_master.csv: {0}".format(exc))
        return

    try:
        bench = load_benchmarks()
    except Exception as exc:
        st.error("Failed loading ca_benchmarks.csv: {0}".format(exc))
        return

    _render_html(
        """
        <div style="display:flex;align-items:center;gap:10px;padding-bottom:0.6rem;border-bottom:1px solid #E5E7EB;margin-bottom:0;">
            <div style="width:26px;height:26px;background:#E8571F;border-radius:6px;display:flex;align-items:center;justify-content:center;">
                <span style="color:white;font-size:14px;font-weight:800">D</span>
            </div>
            <div>
                <span style="font-family:'Inter',sans-serif;font-size:14px;font-weight:800;color:#111827">SHOW ME THE </span>
                <span style="font-family:'Inter',sans-serif;font-size:14px;font-weight:800;color:#E8571F">DPI</span>
            </div>
            <div style="margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.1em;color:#9CA3AF">
                PUBLIC LP DISCLOSURE RESEARCH · {0:,} FUNDS
            </div>
        </div>
        """.format(len(df_unified))
    )

    tab_about, tab_insights, tab_firms, tab_database, tab_sources = st.tabs(
        ["ABOUT", "INSIGHTS", "TOP FIRMS", "FUND DATABASE", "SOURCES"]
    )

    with tab_about:
        render_about()

    with tab_insights:
        render_insights(df_master, bench)

    with tab_firms:
        render_firms(df_master)

    with tab_database:
        render_fund_database(df_unified, df_market_intel)

    with tab_sources:
        render_sources(df_unified, df_master)

    render_footer()


if __name__ == "__main__":
    main()
