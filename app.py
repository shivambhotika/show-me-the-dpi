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
    .badge-gp-disclosed { background:#FFFBEB; color:#92400E; border-color:#FDE68A; }
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
        "classification": "GP-DISCLOSED",
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
        "classification": "GP-DISCLOSED",
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
        "classification": "GP-DISCLOSED",
        "badge_class": "badge-social",
        "coverage": 90,
        "period": "Dec 2024",
        "fund_count": 5,
        "notes": "Formal benchmarking report as of 12/31/2024. Most rigorous GP disclosure in dataset: Cambridge Associates quartile rankings, gross AND net metrics. Covers 5 funds.",
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
def load_gp_disclosed():
    if not os.path.exists("gp_disclosed_funds.csv"):
        return pd.DataFrame()

    df = pd.read_csv("gp_disclosed_funds.csv")
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


def _to_database_gp_df(gp_df: pd.DataFrame) -> pd.DataFrame:
    if gp_df.empty:
        return pd.DataFrame(columns=[
            "fund_name", "vintage_year", "source", "capital_committed", "tvpi", "dpi", "net_irr", "data_source_type"
        ])

    out = gp_df.copy()
    out["capital_committed"] = out["fund_size_usd_m"] * 1_000_000
    out["data_source_type"] = "GP-Disclosed"
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

    def source_type_badge(v):
        if str(v) == "GP-Disclosed":
            return '<span class="badge badge-gp-disclosed">GP</span>'
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
            source_type_cell = "<td>{0}</td>".format(source_type_badge(row.get("data_source_type")))

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


def render_fund_database(df_unified: pd.DataFrame, df_gp_disclosed: pd.DataFrame):
    lp_df = _to_database_lp_df(df_unified)
    gp_df = _to_database_gp_df(df_gp_disclosed)

    render_page_header(
        "FUND DATABASE",
        "PUBLIC LP DISCLOSURES — NORMALIZED & UNIFIED",
        "{0:,} FUNDS INDEXED".format(len(lp_df)),
    )

    source_type = st.radio(
        "DATA SOURCE TYPE",
        ["LP-Disclosed (FOIA)", "GP-Disclosed (Firm Published)", "Both"],
        horizontal=True,
        index=0,
        label_visibility="visible",
    )

    if source_type == "GP-Disclosed (Firm Published)":
        st.markdown(
            """
        <div class="insight-box">
            <div class="insight-label">● DATA SOURCE NOTE</div>
            <div class="insight-body">
                <strong>These figures are GP self-disclosed.</strong> a16z, Founders Fund, and
                Social Capital published this data voluntarily in blog posts and investor reports.
                GP-disclosed figures may reflect selective fund reporting and show gross metrics
                before fees and carry. <em>Compare with LP-disclosed data (from FOIA sources)
                for independent verification where available.</em>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    if source_type == "LP-Disclosed (FOIA)":
        base_df = lp_df.copy()
    elif source_type == "GP-Disclosed (Firm Published)":
        base_df = gp_df.copy()
    else:
        base_df = pd.concat([lp_df, gp_df], ignore_index=True)

    if "db_page" not in st.session_state:
        st.session_state["db_page"] = 0
    if st.session_state.get("db_source_type") != source_type:
        st.session_state["db_page"] = 0
        st.session_state["db_source_type"] = source_type

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

    show_source_type = source_type == "Both"
    render_fund_table(page_df, show_source_type=show_source_type)

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
    gp_only_gps = [gp for gp in gps if source_by_gp.get(gp) == ["GP-Disclosed"]]
    lp_gps = [gp for gp in gps if gp not in gp_only_gps]

    st.markdown('<div class="section-label">LP-DISCLOSED — INSTITUTIONAL SOURCES</div>', unsafe_allow_html=True)
    for i in range(0, len(lp_gps), 3):
        cols = st.columns(3)
        for j, gp in enumerate(lp_gps[i : i + 3]):
            with cols[j]:
                render_firm_card(gp, df_master[df_master["canonical_gp"] == gp])

    st.markdown('<div class="section-label">GP-DISCLOSED — FIRM PUBLISHED DATA</div>', unsafe_allow_html=True)
    st.markdown(
        """
    <div style="font-family:'Inter',sans-serif;font-size:13px;color:#6B7280;margin-bottom:1rem;
        padding:12px 16px;background:#FFFBEB;border-radius:6px;border:1px solid #FDE68A">
        Performance data below is self-reported by the fund manager, not independently
        verified by LP disclosure. Gross metrics shown where net unavailable.
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
    is_gp_disclosed = bool((gp_df["data_source_type"] == "GP-Disclosed").all())
    source_chip = '<span class="badge badge-gp-disclosed">GP-DISCLOSED</span>' if is_gp_disclosed else '<span class="badge badge-lp-disclosed">LP-DISCLOSED</span>'

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

    if is_gp_disclosed and str(selected_gp).lower() == "a16z":
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

    elif is_gp_disclosed:
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
        if is_gp_disclosed:
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

    gross_header = "<th class='right'>GROSS TVPI</th>" if is_gp_disclosed else ""
    _render_html(
        (
            '<table class="fund-table" style="margin-top:1rem;"><thead><tr>'
            "<th>FUND</th><th class=\"right\">VINTAGE</th><th>STRATEGY</th><th class=\"right\">SIZE</th>{0}"
            '<th class="right">NET TVPI</th><th class="right" style="color:#E8571F">NET DPI</th>'
            '<th class="right">NET IRR</th><th>STATUS</th>'
            "</tr></thead><tbody>{1}</tbody></table>"
        ).format(gross_header, rows_html)
    )

    if is_gp_disclosed and str(selected_gp).lower() == "a16z":
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


def render_insights(df_master: pd.DataFrame):
    render_page_header("INSIGHTS", "ANALYTICAL FINDINGS FROM PUBLIC LP DISCLOSURE DATA")

    st.markdown('<div class="section-label">KEY FINDINGS</div>', unsafe_allow_html=True)

    insight_cards = [
        {
            "number": "01",
            "label": "DPI DROUGHT",
            "headline": "Post-2017 = paper",
            "body": "Across LP and GP-disclosed data, no fund with 2017+ vintage has returned meaningful cash. a16z Fund V and Founders Fund VI both show DPI < 0.5x despite 3x+ TVPI.",
        },
        {
            "number": "02",
            "label": "HIGHEST DPI",
            "headline": "Founders Fund II",
            "body": "18.6x DPI on a $227M 2007 fund — the highest cash-returned figure in this entire dataset. Driven by Palantir, SpaceX, and Airbnb distributions.",
        },
        {
            "number": "03",
            "label": "BEST NET IRR",
            "headline": "Seq. US Venture XVI",
            "body": "30.8% Net IRR (UC Regents, 2018 vintage). Among GP-disclosed data, Social Capital Fund II leads at 26.2% Net IRR on a $1.5B fund.",
        },
        {
            "number": "04",
            "label": "FEE DRAG REALITY",
            "headline": "a16z Fund III",
            "body": "Gross TVPI 15.7x → Net TVPI 11.3x. The 4.4x drag on a $997M fund = ~$4.4B in fees and carry. Gross numbers in pitch decks tell a different story.",
        },
        {
            "number": "05",
            "label": "CONSISTENT ALPHA",
            "headline": "Social Capital",
            "body": "4 of 5 funds are Cambridge Associates Quartile 1 on TVPI. All 5 are Quartile 1 on DPI. The most consistent top-quartile track record in the GP-disclosed dataset.",
        },
    ]

    cols = st.columns(5)
    for i, card in enumerate(insight_cards):
        cols[i].markdown(
            """
        <div style="border:1px solid #E5E7EB;border-radius:6px;padding:16px;background:#fff;min-height:190px;">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:0.15em;text-transform:uppercase;color:#9CA3AF;margin-bottom:4px">{0} / {1}</div>
            <div style="font-family:'Inter',sans-serif;font-size:16px;font-weight:700;color:#111827;margin-bottom:8px">{2}</div>
            <div style="font-family:'Inter',sans-serif;font-size:12px;color:#6B7280;line-height:1.5">{3}</div>
        </div>
        """.format(
                html.escape(card["number"]),
                html.escape(card["label"]),
                html.escape(card["headline"]),
                html.escape(card["body"]),
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        """
    <div class="insight-box">
      <div class="insight-label">● LP REALIZATION ANCHORS</div>
      <div class="insight-body"><strong>Mayfield XIV</strong> and <strong>Khosla IV</strong> remain the clearest LP-disclosed examples of realized cash generation in this dataset.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    df = df_master.copy()
    df_lp = df[df["data_source_type"] == "LP-Disclosed"].copy()
    df_gp = df[df["data_source_type"] == "GP-Disclosed"].copy()

    st.markdown('<div class="section-label">01 / FIRM LANDSCAPE</div>', unsafe_allow_html=True)

    firm_summary = (
        df.groupby("canonical_gp", as_index=False)
        .agg(
            gp_display_name=("gp_display_name", "first"),
            firm_founded=("firm_founded", "min"),
            firm_aum_usd_b=("firm_aum_usd_b", "max"),
            total_capital_usd_m=("fund_size_usd_m", "sum"),
            primary_category=("fund_category", lambda s: s.mode().iloc[0] if not s.mode().empty else "Venture"),
        )
    )

    c1, c2 = st.columns([3, 2])
    with c1:
        fig1a = px.scatter(
            firm_summary,
            x="firm_founded",
            y="firm_aum_usd_b",
            size="total_capital_usd_m",
            color="canonical_gp",
            text="gp_display_name",
            size_max=55,
            template="plotly_white",
            labels={"firm_founded": "Founded", "firm_aum_usd_b": "Firm AUM ($B)"},
        )
        fig1a.update_traces(textposition="top center", textfont_size=10)
        _plot_common_layout(fig1a, "FIRM SCALE VS TENURE")
        fig1a.update_layout(height=420, showlegend=False)
        st.plotly_chart(fig1a, use_container_width=True)

    with c2:
        cap_by_firm = firm_summary.sort_values("total_capital_usd_m", ascending=True)
        colors = [CATEGORY_COLORS.get(cat, "#6B7280") for cat in cap_by_firm["primary_category"]]
        fig1b = go.Figure(
            go.Bar(
                y=cap_by_firm["canonical_gp"],
                x=cap_by_firm["total_capital_usd_m"],
                orientation="h",
                marker_color=colors,
                text=cap_by_firm["total_capital_usd_m"].round(0),
                textposition="outside",
            )
        )
        _plot_common_layout(fig1b, "CAPITAL IN DATASET BY FIRM")
        fig1b.update_layout(height=420, showlegend=False)
        st.plotly_chart(fig1b, use_container_width=True)

    st.markdown('<div class="section-label">02 / RETURNS — MEANINGFUL FUNDS ONLY</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-subtitle">Only includes LP-disclosed funds where vintage ≤ 2020 and IRR is non-placeholder</div>', unsafe_allow_html=True)

    df_perf_lp = df_lp[(df_lp["irr_meaningful"] == True) & df_lp["net_irr"].notna()].copy()
    df_perf_lp = df_perf_lp[df_perf_lp["net_irr"] <= 2.0].copy()
    df_perf_lp["marker_size"] = df_perf_lp["fund_size_usd_m"].clip(upper=3000)

    fig2a = px.scatter(
        df_perf_lp,
        x="vintage_year",
        y=df_perf_lp["net_irr"] * 100,
        color="canonical_gp",
        size="marker_size",
        template="plotly_white",
        custom_data=["fund_name", "tvpi", "dpi"],
    )
    fig2a.update_traces(
        marker=dict(line=dict(color="#E8571F", width=1.2)),
        hovertemplate="<b>%{customdata[0]}</b><br>IRR: %{y:.1f}%<br>TVPI: %{customdata[1]:.2f}x<br>DPI: %{customdata[2]:.2f}x<extra></extra>",
    )
    fig2a.add_hline(y=10, line_dash="dash", line_color="#DC2626", annotation_text="10% INSTITUTIONAL BENCHMARK")
    fig2a.add_hline(y=20, line_dash="dash", line_color="#16A34A", annotation_text="20% TOP QUARTILE VC")
    _plot_common_layout(fig2a, "NET IRR BY VINTAGE YEAR")
    fig2a.update_layout(height=500)
    st.plotly_chart(fig2a, use_container_width=True)

    fig2b = px.scatter(
        df_perf_lp,
        x="dpi",
        y="tvpi",
        color="canonical_gp",
        size="marker_size",
        template="plotly_white",
        custom_data=["fund_name", "vintage_year", "net_irr"],
    )
    fig2b.update_traces(
        marker=dict(line=dict(color="#E8571F", width=1.0)),
        hovertemplate="<b>%{customdata[0]}</b><br>Vintage: %{customdata[1]}<br>IRR: %{customdata[2]:.1%}<extra></extra>",
    )

    max_dpi = float(df_perf_lp["dpi"].max()) if not df_perf_lp["dpi"].dropna().empty else 3.0
    max_tvpi = float(df_perf_lp["tvpi"].max()) if not df_perf_lp["tvpi"].dropna().empty else 3.0
    max_val = max(max_dpi, max_tvpi) + 0.5
    fig2b.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="#9CA3AF", dash="dash"))
    fig2b.add_annotation(x=max_val * 0.2, y=max_val * 0.9, text="PAPER GAINS ZONE", showarrow=False, font=dict(size=10, color="#9CA3AF"))
    fig2b.add_annotation(x=max_val * 0.78, y=max_val * 0.78, text="FULLY REALIZED", textangle=45, showarrow=False, font=dict(size=10, color="#9CA3AF"))

    mayfield = df_perf_lp[df_perf_lp["fund_name"].astype(str).str.contains("Mayfield XIV", case=False, na=False)]
    if not mayfield.empty:
        r = mayfield.iloc[0]
        fig2b.add_trace(
            go.Scatter(
                x=[r["dpi"]], y=[r["tvpi"]], mode="markers",
                marker=dict(symbol="star", size=16, color="#E8571F", line=dict(color="#111827", width=1)),
                name="Mayfield XIV",
                hovertemplate="<b>Mayfield XIV</b><br>DPI: %{x:.2f}x<br>TVPI: %{y:.2f}x<extra></extra>",
            )
        )

    _plot_common_layout(fig2b, "TVPI VS DPI — THE REALIZATION MAP")
    fig2b.update_layout(height=560)
    fig2b.update_xaxes(range=[0, max_val])
    fig2b.update_yaxes(range=[0, max_val])
    st.markdown('<div class="chart-subtitle">Funds near the diagonal have returned real cash. Upper-left = paper gains only.</div>', unsafe_allow_html=True)
    st.plotly_chart(fig2b, use_container_width=True)

    rank = df_perf_lp.sort_values("net_irr", ascending=True).copy()
    rank["label"] = rank["fund_name"] + " (" + rank["canonical_gp"] + ")"

    def _irr_color(v):
        pct = v * 100
        if pct >= 20:
            return "#16A34A"
        if pct >= 10:
            return "#D97706"
        return "#DC2626"

    fig2c = go.Figure(go.Bar(y=rank["label"], x=rank["net_irr"] * 100, orientation="h", marker_color=[_irr_color(v) for v in rank["net_irr"]]))
    _plot_common_layout(fig2c, "NET IRR RANKING")
    fig2c.update_layout(height=620, showlegend=False)
    st.plotly_chart(fig2c, use_container_width=True)

    st.markdown('<div class="section-label">02B / GP-DISCLOSED PERFORMANCE (SELECT FIRMS)</div>', unsafe_allow_html=True)
    st.markdown(
        """
    <div class="chart-subtitle">
        Source: GP self-published data — a16z (as of 9/30/2025), Social Capital (12/31/2024),
        Founders Fund. These are the funds each firm has chosen to disclose. Caution:
        later and underperforming funds may be excluded.
    </div>
    """,
        unsafe_allow_html=True,
    )

    gp_dpi = df_gp[df_gp["dpi"].notna()].copy()
    gp_dpi = gp_dpi.sort_values("dpi", ascending=True)
    gp_dpi["label"] = gp_dpi["fund_name"] + " (" + gp_dpi["canonical_gp"] + ", " + gp_dpi["vintage_year"].astype("Int64").astype(str) + ")"

    def gp_dpi_color(v):
        if v > 2.0:
            return "#E8571F"
        if v >= 0.5:
            return "#D97706"
        return "#9CA3AF"

    fig_gp_dpi = go.Figure(
        go.Bar(
            y=gp_dpi["label"],
            x=gp_dpi["dpi"],
            orientation="h",
            marker_color=[gp_dpi_color(v) for v in gp_dpi["dpi"]],
            hovertemplate="<b>%{y}</b><br>Net DPI: %{x:.2f}x<extra></extra>",
        )
    )
    _plot_common_layout(fig_gp_dpi, "NET DPI RANKING — GP-DISCLOSED FUNDS")
    fig_gp_dpi.update_layout(height=550, showlegend=False)
    st.plotly_chart(fig_gp_dpi, use_container_width=True)

    lp_points = df_perf_lp.dropna(subset=["tvpi", "dpi"]).copy()
    gp_points = df_gp[df_gp["tvpi"].notna() & df_gp["dpi"].notna()].copy()

    fig_mix = go.Figure()
    fig_mix.add_trace(
        go.Scatter(
            x=lp_points["dpi"],
            y=lp_points["tvpi"],
            mode="markers",
            name="● LP-Disclosed",
            marker=dict(symbol="circle", size=9, color="#6B7280", opacity=0.55),
            customdata=np.stack([lp_points["fund_name"], lp_points["canonical_gp"]], axis=1) if not lp_points.empty else None,
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>DPI: %{x:.2f}x<br>TVPI: %{y:.2f}x<extra></extra>",
        )
    )
    fig_mix.add_trace(
        go.Scatter(
            x=gp_points["dpi"],
            y=gp_points["tvpi"],
            mode="markers",
            name="◆ GP-Disclosed",
            marker=dict(symbol="diamond", size=11, color="#E8571F", opacity=0.9, line=dict(color="#7C2D12", width=0.8)),
            customdata=np.stack([gp_points["fund_name"], gp_points["canonical_gp"]], axis=1) if not gp_points.empty else None,
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>DPI: %{x:.2f}x<br>TVPI: %{y:.2f}x<extra></extra>",
        )
    )

    max_lp = max(
        float(lp_points["dpi"].max()) if not lp_points.empty else 0,
        float(lp_points["tvpi"].max()) if not lp_points.empty else 0,
        float(gp_points["dpi"].max()) if not gp_points.empty else 0,
        float(gp_points["tvpi"].max()) if not gp_points.empty else 0,
    )
    max_lp = max(max_lp, 2.0) + 0.5
    fig_mix.add_shape(type="line", x0=0, y0=0, x1=max_lp, y1=max_lp, line=dict(color="#9CA3AF", dash="dash"))
    _plot_common_layout(fig_mix, "TVPI VS DPI — LP VS GP DISCLOSURES")
    fig_mix.update_layout(height=560)
    fig_mix.update_xaxes(title_text="DPI", range=[0, max_lp])
    fig_mix.update_yaxes(title_text="TVPI", range=[0, max_lp])
    st.plotly_chart(fig_mix, use_container_width=True)

    st.markdown('<div class="section-label">03 / VINTAGE COHORT ANALYSIS</div>', unsafe_allow_html=True)

    c3a, c3b = st.columns(2)
    with c3a:
        box_df = df_perf_lp.dropna(subset=["vintage_year", "tvpi"]).copy()
        fig3a = go.Figure()
        for vintage in sorted(box_df["vintage_year"].dropna().astype(int).unique().tolist()):
            sub = box_df[box_df["vintage_year"] == vintage]
            fig3a.add_trace(go.Box(y=sub["tvpi"], name=str(vintage), marker_color="#2C3E50", boxpoints="all", jitter=0.3, pointpos=0, marker=dict(size=5, opacity=0.5)))
        fig3a.add_hline(y=1.0, line_dash="solid", line_color="#9CA3AF")
        fig3a.add_hline(y=2.0, line_dash="dash", line_color="#16A34A")
        _plot_common_layout(fig3a, "TVPI DISTRIBUTION BY VINTAGE")
        fig3a.update_layout(height=450, showlegend=False)
        st.plotly_chart(fig3a, use_container_width=True)

    with c3b:
        stack_df = df_perf_lp.dropna(subset=["vintage_year", "dpi", "tvpi"]).copy()
        stack_df = stack_df[stack_df["tvpi"] > 0]
        stack_df["realized"] = (stack_df["dpi"] / stack_df["tvpi"]).clip(lower=0, upper=1)
        stack_agg = stack_df.groupby("vintage_year", as_index=False)["realized"].mean()
        stack_agg["unrealized"] = 1 - stack_agg["realized"]

        fig3b = go.Figure()
        fig3b.add_trace(go.Bar(x=stack_agg["vintage_year"], y=stack_agg["realized"], name="Realized", marker_color="#18A999"))
        fig3b.add_trace(go.Bar(x=stack_agg["vintage_year"], y=stack_agg["unrealized"], name="Unrealized", marker_color="#E5E7EB"))
        fig3b.add_annotation(xref="paper", yref="paper", x=0.8, y=0.08, text="0% realized", showarrow=True, arrowhead=2)
        _plot_common_layout(fig3b, "REALIZED VS UNREALIZED CAPITAL BY VINTAGE")
        fig3b.update_layout(height=450, barmode="stack")
        st.plotly_chart(fig3b, use_container_width=True)

    st.markdown('<div class="section-label">04 / GP PERFORMANCE TRAJECTORIES</div>', unsafe_allow_html=True)

    c4a, c4b = st.columns(2)
    with c4a:
        gp_counts = df_perf_lp.groupby("canonical_gp")["fund_name"].nunique()
        eligible = gp_counts[gp_counts >= 2].index.tolist()
        trend = df_perf_lp[df_perf_lp["canonical_gp"].isin(eligible)].copy().sort_values(["canonical_gp", "vintage_year"])

        fig4a = go.Figure()
        best_gp = trend.groupby("canonical_gp")["net_irr"].max().sort_values(ascending=False).index[0] if not trend.empty else None
        for gp, sub in trend.groupby("canonical_gp"):
            color = "#E8571F" if gp == best_gp else "#6B7280"
            fig4a.add_trace(go.Scatter(x=sub["vintage_year"], y=sub["net_irr"] * 100, mode="lines+markers", name=gp, line=dict(color=color, width=2), marker=dict(size=7)))

        _plot_common_layout(fig4a, "IRR TRAJECTORY ACROSS FUND GENERATIONS")
        fig4a.update_layout(height=460)
        st.plotly_chart(fig4a, use_container_width=True)

    with c4b:
        mix = df_lp.groupby(["canonical_gp", "fund_category"], as_index=False)["fund_size_usd_m"].sum()
        gp_order = mix.groupby("canonical_gp")["fund_size_usd_m"].sum().sort_values(ascending=True).index.tolist()

        fig4b = go.Figure()
        for cat in ["Venture", "Growth", "Opportunities", "PE", "Company Creation"]:
            sub = mix[mix["fund_category"] == cat]
            vals = []
            for gp in gp_order:
                m = sub[sub["canonical_gp"] == gp]["fund_size_usd_m"]
                vals.append(float(m.iloc[0]) if not m.empty else 0.0)
            fig4b.add_trace(go.Bar(y=gp_order, x=vals, orientation="h", marker_color=CATEGORY_COLORS.get(cat, "#6B7280"), name=cat))

        _plot_common_layout(fig4b, "CAPITAL BY STRATEGY PER FIRM")
        fig4b.update_layout(height=460, barmode="stack")
        st.plotly_chart(fig4b, use_container_width=True)

    st.markdown(
        """
    <div class="insight-box">
        <div class="insight-label">● ANALYST INSIGHT — GP vs LP DATA</div>
        <div class="insight-body">
            <strong>The gross/net gap is the most underappreciated number in VC.</strong>
            a16z Fund III shows 15.7x gross TVPI vs 11.3x net — a 28% reduction from fees
            and carry. Founders Fund's early funds show extraordinary DPI figures (18.6x for
            FFII), but these reflect $227M vehicles with exceptional concentration in
            Palantir and SpaceX. At $1.4B+ fund sizes (FFVI onward), DPI collapses to
            near-zero — the same structural challenge every large fund faces.
            <br><br>
            <em>Social Capital presents the most methodologically rigorous GP disclosure in
            this dataset: Cambridge Associates verified quartile rankings, net metrics only,
            no cherry-picking of fund vintage. Their Fund II (2013) at 26.2% net IRR and
            3.4x net DPI on $1.5B is genuinely exceptional at scale.</em>
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

    st.markdown('<div class="section-label">03 / GP-DISCLOSED SOURCES</div>', unsafe_allow_html=True)
    st.markdown(
        """
    <div style="font-family:'Inter',sans-serif;font-size:14px;color:#374151;line-height:1.7;
        padding:16px 20px;background:#FFFBEB;border-radius:6px;border:1px solid #FDE68A;margin-bottom:1.5rem">
        The following data comes from fund managers themselves, not independent LP disclosures.
        These are typically published in blog posts, investor letters, or formal benchmarking
        reports. While valuable, they carry selection bias risk — GPs tend to publish their
        best-performing funds and omit struggling vehicles.
    </div>
    """,
        unsafe_allow_html=True,
    )

    gp_counts = df_master[df_master["data_source_type"] == "GP-Disclosed"]["source"].value_counts(dropna=False).to_dict()
    for cfg in GP_SOURCES_CONFIG:
        row_count = int(gp_counts.get(cfg["source_key"], cfg["fund_count"]))
        render_source_row(cfg, row_count, coverage_label="DISCLOSED UNIVERSE COVERAGE")

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
            from pension systems and endowments with clearly-labeled GP self-disclosed performance where available.
            <br><br>
            The core metric is <strong>DPI</strong> (Distributed-to-Paid-In), shown in orange across the product.
            TVPI and IRR are included for context, but DPI is prioritized because it reflects realized outcomes,
            not only unrealized marks.
            <br><br>
            This is not investment advice and not a complete census of all funds. LP-reported and GP-reported numbers
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
          <li>Source transparency on every page, with LP vs GP disclosure separation.</li>
          <li>Analyst-friendly structure for fast comparison across firms, vintages, and source types.</li>
        </ul>
        """
    )


def render_footer():
    _render_html(
        """
        <div class="footer-wrap">
            <div class="footer-text">
                Data is compiled from public disclosures and select GP-published reports. Figures may differ by LP methodology,
                valuation date, and fee treatment. GP-disclosed data can include selection bias.
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
        df_gp_disclosed = load_gp_disclosed()
    except Exception as exc:
        st.error("Failed loading gp_disclosed_funds.csv: {0}".format(exc))
        df_gp_disclosed = pd.DataFrame()

    try:
        df_master = load_master_full()
    except Exception as exc:
        st.error("Failed loading vc_fund_master.csv: {0}".format(exc))
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
        render_insights(df_master)

    with tab_firms:
        render_firms(df_master)

    with tab_database:
        render_fund_database(df_unified, df_gp_disclosed)

    with tab_sources:
        render_sources(df_unified, df_master)

    render_footer()


if __name__ == "__main__":
    main()
