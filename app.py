import html
import os
import re
from difflib import SequenceMatcher
from datetime import date
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
    .badge-utimco    { background:#F0F9FF; color:#075985; border-color:#BAE6FD; }
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

    /* Premium Navigation Bar Styling */
    div[data-testid="stSegmentedControl"] {
        background: white !important;
        margin-bottom: 2rem !important;
        width: 100% !important;
    }
    div[data-testid="stSegmentedControl"] > div {
        background: #F9FAFB !important;
        border: 1px solid #E5E7EB !important;
        padding: 4px !important;
        border-radius: 12px !important;
        width: fit-content !important;
        display: flex !important;
        gap: 4px !important;
    }
    div[data-testid="stSegmentedControl"] button, 
    div[data-testid="stSegmentedControl"] [role="radio"],
    div[data-testid="stSegmentedControl"] label {
        background-color: transparent !important;
        background: transparent !important;
        color: #6B7280 !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        padding: 8px 18px !important;
        box-shadow: none !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stSegmentedControl"] button[data-checked="true"], 
    div[data-testid="stSegmentedControl"] [aria-checked="true"],
    div[data-testid="stSegmentedControl"] [data-checked="true"] label {
        background-color: white !important;
        background: white !important;
        color: #E8571F !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
        font-weight: 700 !important;
        text-decoration: underline !important;
        text-underline-offset: 4px !important;
    }
    div[data-testid="stSegmentedControl"] button:hover {
        background-color: rgba(0,0,0,0.03) !important;
        color: #111827 !important;
    }
    div[data-testid="stSegmentedControl"] button[data-checked="true"]:hover {
        background-color: white !important;
        color: #E8571F !important;
    }

    /* Aggressive Plotly "Undefined" & Modebar Fix */
    .js-plotly-plot .plotly .modebar, 
    .js-plotly-plot .plotly .modebar-container,
    .js-plotly-plot .plotly .modebar-btn,
    div[data-testid="stPlotlyChart"] .modebar {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }
    /* Stop the "undefined" tooltip frame from appearing when hovering modebar area */
    .plotly-notifier, .modebar-container { display: none !important; }

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
    "Louisiana TRSL": "badge-louisiana",
    "UTIMCO": "badge-utimco",
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
    "Louisiana TRSL": "LOUISIANA_TRSL",
    "UTIMCO": "UTIMCO",
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

CANONICAL_GP_ALIASES = {
    "a16z": "Andreessen Horowitz",
    "usv": "Union Square Ventures",
    "sequoia": "Sequoia Capital",
    "ggv": "GGV Capital",
    "peak xv": "Peak XV Partners",
}


def normalize_canonical_gp_label(value):
    if pd.isna(value):
        return value
    raw = str(value).strip()
    if not raw:
        return raw
    return CANONICAL_GP_ALIASES.get(raw.lower(), raw)


FOCUS_FIRM_SPECS = [
    {"canonical_gp": "a16z", "gp_display_name": "Andreessen Horowitz", "include": [r"ah fund", r"andreessen", r"\ba16z\b"], "exclude": []},
    {"canonical_gp": "Union Square Ventures", "gp_display_name": "Union Square Ventures", "include": [r"union square ventures", r"\busv\b"], "exclude": []},
    {"canonical_gp": "Spark Capital", "gp_display_name": "Spark Capital", "include": [r"spark capital"], "exclude": []},
    {"canonical_gp": "Social Capital", "gp_display_name": "Social Capital", "include": [r"social capital"], "exclude": []},
    {"canonical_gp": "NEA", "gp_display_name": "New Enterprise Associates", "include": [r"new enterprise associates", r"\bnea\b"], "exclude": []},
    {"canonical_gp": "Kleiner Perkins", "gp_display_name": "Kleiner Perkins", "include": [r"kleiner", r"\bkpcb\b"], "exclude": []},
    {"canonical_gp": "Greylock Partners", "gp_display_name": "Greylock Partners", "include": [r"greylock"], "exclude": []},
    {"canonical_gp": "Battery Ventures", "gp_display_name": "Battery Ventures", "include": [r"battery ventures", r"\bbattery\b"], "exclude": []},
    {"canonical_gp": "Index Ventures", "gp_display_name": "Index Ventures", "include": [r"index ventures", r"index venture"], "exclude": []},
    {"canonical_gp": "Accel", "gp_display_name": "Accel", "include": [r"\baccel\b"], "exclude": [r"accel-kkr", r"acceleration"]},
    {"canonical_gp": "Founders Fund", "gp_display_name": "Founders Fund", "include": [r"founders fund"], "exclude": []},
    {"canonical_gp": "Insight Partners", "gp_display_name": "Insight Partners", "include": [r"insight venture", r"insight partners"], "exclude": []},
    {"canonical_gp": "Coatue", "gp_display_name": "Coatue", "include": [r"coatue"], "exclude": []},
    {"canonical_gp": "ARCH Venture Partners", "gp_display_name": "ARCH Venture Partners", "include": [r"arch venture"], "exclude": []},
    {"canonical_gp": "Foundry Group", "gp_display_name": "Foundry Group", "include": [r"foundry"], "exclude": []},
    {"canonical_gp": "True Ventures", "gp_display_name": "True Ventures", "include": [r"true ventures"], "exclude": []},
    {"canonical_gp": "Forerunner Ventures", "gp_display_name": "Forerunner Ventures", "include": [r"forerunner"], "exclude": []},
    {"canonical_gp": "IA Ventures", "gp_display_name": "IA Ventures", "include": [r"ia venture"], "exclude": []},
    {"canonical_gp": "Technology Crossover Ventures", "gp_display_name": "Technology Crossover Ventures", "include": [r"\\btcv\\b", r"technology crossover ventures"], "exclude": []},
    {"canonical_gp": "TLV Partners", "gp_display_name": "TLV Partners", "include": [r"tlv partners"], "exclude": []},
    {"canonical_gp": "Techstars", "gp_display_name": "Techstars", "include": [r"techstars"], "exclude": []},
    {"canonical_gp": "Upfront Ventures", "gp_display_name": "Upfront Ventures", "include": [r"upfront"], "exclude": []},
    {"canonical_gp": "Morgenthaler Ventures", "gp_display_name": "Morgenthaler Ventures", "include": [r"morgenthaler"], "exclude": []},
    {"canonical_gp": "Sofinnova Ventures", "gp_display_name": "Sofinnova Ventures", "include": [r"sofinnova"], "exclude": []},
    {"canonical_gp": "Mosaic Ventures", "gp_display_name": "Mosaic Ventures", "include": [r"mosaic ventures"], "exclude": []},
    {"canonical_gp": "Correlation Ventures", "gp_display_name": "Correlation Ventures", "include": [r"correlation ventures"], "exclude": []},
    {"canonical_gp": "Austin Ventures", "gp_display_name": "Austin Ventures", "include": [r"austin ventures"], "exclude": []},
    {"canonical_gp": "Ampersand Capital Partners", "gp_display_name": "Ampersand Capital Partners", "include": [r"ampersand"], "exclude": []},
    {"canonical_gp": "Wingate Partners", "gp_display_name": "Wingate Partners", "include": [r"wingate partners"], "exclude": []},
    {"canonical_gp": "Alta Partners", "gp_display_name": "Alta Partners", "include": [r"alta partners"], "exclude": []},
    {"canonical_gp": "Sante Ventures", "gp_display_name": "Sante Ventures", "include": [r"sante"], "exclude": []},
    {"canonical_gp": "Cendana Capital", "gp_display_name": "Cendana Capital", "include": [r"cendana"], "exclude": []},
]

GP_METADATA = {
    "Union Square Ventures": {"hq": "New York, NY", "founded": 2003, "strategy": "Generalist VC — early stage, network effects", "aum_approx": 3.0, "notable": "Twitter, Tumblr, Coinbase, Etsy"},
    "Foundry Group": {"hq": "Boulder, CO", "founded": 2007, "strategy": "Early stage VC — themes-based", "aum_approx": 2.0, "notable": "Fitbit, Zynga, SendGrid, Duo Security"},
    "True Ventures": {"hq": "San Francisco, CA", "founded": 2005, "strategy": "Early stage VC — founder-first", "aum_approx": 2.5, "notable": "Ring, Peloton, Blue Bottle, Automattic"},
    "Spark Capital": {"hq": "Boston/San Francisco", "founded": 2005, "strategy": "Multi-stage VC", "aum_approx": 3.5, "notable": "Twitter, Tumblr, Slack, Wayfair"},
    "Forerunner Ventures": {"hq": "San Francisco, CA", "founded": 2012, "strategy": "Consumer VC", "aum_approx": 2.0, "notable": "Dollar Shave Club, Warby Parker, Away, Chime"},
    "ARCH Venture Partners": {"hq": "Chicago, IL", "founded": 1986, "strategy": "Deep science VC", "aum_approx": 3.0, "notable": "Illumina, Editas, Alnylam, GRAIL"},
    "IA Ventures": {"hq": "New York, NY", "founded": 2010, "strategy": "Data-driven early stage VC", "aum_approx": 0.5, "notable": "Wise, The Trade Desk, Betterment"},
    "Technology Crossover Ventures": {"hq": "Palo Alto, CA", "founded": 1995, "strategy": "Growth/late-stage VC", "aum_approx": 20.0, "notable": "Facebook, Netflix, Spotify, Airbnb"},
    "TLV Partners": {"hq": "Tel Aviv, Israel", "founded": 2012, "strategy": "Israeli early-stage VC", "aum_approx": 0.5, "notable": "Next Insurance, Lusha, Firebolt"},
    "Techstars": {"hq": "Boulder, CO", "founded": 2006, "strategy": "Accelerator seed-stage", "aum_approx": 1.0, "notable": "SendGrid, ClassPass, PillPack"},
    "Upfront Ventures": {"hq": "Los Angeles, CA", "founded": 1996, "strategy": "LA-focused early-stage VC", "aum_approx": 2.0, "notable": "Ring, TrueCar, Maker Studios"},
    "Morgenthaler Ventures": {"hq": "Cleveland, OH / Menlo Park, CA", "founded": 1968, "strategy": "Generalist VC", "aum_approx": 3.0, "notable": "Quanta, Xoma, Advanced Energy"},
    "Sofinnova Ventures": {"hq": "San Francisco, CA", "founded": 1976, "strategy": "Life sciences VC", "aum_approx": 2.0, "notable": "Pharmacyclics, Rigel, Arena"},
    "Mosaic Ventures": {"hq": "London, UK", "founded": 2014, "strategy": "European early-stage VC", "aum_approx": 0.5, "notable": "Wayve, Cleo, Beamery"},
    "Correlation Ventures": {"hq": "San Diego, CA", "founded": 2012, "strategy": "Quantitative co-invest VC", "aum_approx": 0.3, "notable": "Data-driven co-investment strategy"},
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
        "row_count_key": "Louisiana TRSL",
    },
    {
        "name": "University of Texas IMC (UTIMCO)",
        "short": "UTIMCO",
        "classification": "PUBLIC",
        "badge_class": "badge-utimco",
        "coverage": 78,
        "period": "2023-02-28 (+ 2009–2016 history)",
        "notes": (
            "UTIMCO (~$78B AUM). 2023 report is primary, with fund-by-fund DPI/TVPI/IRR and capital_contributed. "
            "Vintage years are inferred where possible; capital_committed is not disclosed."
        ),
        "row_count_key": "UTIMCO",
        "coverage_breakdown": {
            "fund_name": 100,
            "vintage_year": 80,
            "tvpi": 100,
            "dpi": 100,
            "net_irr": 100,
            "capital_contributed": 100,
            "capital_committed": 0,
        },
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
    df["capital_contributed"] = pd.to_numeric(df.get("capital_contributed"), errors="coerce")
    df["capital_distributed"] = pd.to_numeric(df.get("capital_distributed"), errors="coerce")
    df["nav"] = pd.to_numeric(df.get("nav"), errors="coerce")
    df["source"] = df.get("source", pd.Series(index=df.index, dtype="object")).fillna("Unknown")

    # Optional UTIMCO fallback merge for local runs before normalize.py has been re-run.
    utimco_path = "data/utimco_2023.csv"
    if os.path.exists(utimco_path):
        ut = load_utimco_for_app(utimco_path)
        if not ut.empty:
            keep_cols = [
                "fund_name",
                "vintage_year",
                "capital_committed",
                "capital_contributed",
                "capital_distributed",
                "nav",
                "net_irr",
                "tvpi",
                "dpi",
                "source",
                "scraped_date",
                "reporting_period",
            ]
            for c in keep_cols:
                if c not in df.columns:
                    df[c] = np.nan
                if c not in ut.columns:
                    ut[c] = np.nan
            merged = pd.concat([df[keep_cols], ut[keep_cols]], ignore_index=True)
            merged["vintage_year"] = pd.to_numeric(merged["vintage_year"], errors="coerce").astype("Int64")
            merged = merged.drop_duplicates(
                subset=["fund_name", "vintage_year", "source", "reporting_period"], keep="first"
            ).reset_index(drop=True)
            df = merged
    return df


def _norm_text(s: str) -> str:
    t = str(s or "").lower().strip()
    t = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in t)
    t = " ".join(t.split())
    return t


def _clean_num(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    pct = s.str.contains("%", na=False)
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace("$", "", regex=False)
    s = s.str.replace("%", "", regex=False)
    s = s.str.replace("x", "", regex=False)
    s = s.str.replace("X", "", regex=False)
    s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    s = s.replace({"": np.nan, "-": np.nan, "--": np.nan, "N/M": np.nan, "NM": np.nan})
    out = pd.to_numeric(s, errors="coerce")
    out = out.where(~pct, out / 100.0)
    return out


def _infer_vintage_from_name(name: str):
    text = str(name or "")
    m_start = re.search(r"^\s*((?:19|20)\d{2})\b", text)
    if m_start:
        return int(m_start.group(1))
    m_end = re.search(r"\b((?:19|20)\d{2})\s*$", text)
    if m_end:
        return int(m_end.group(1))
    m_any = re.search(r"\b((?:19|20)\d{2})\b", text)
    if m_any:
        return int(m_any.group(1))
    return np.nan


def load_utimco_for_app(filepath: str) -> pd.DataFrame:
    raw = pd.read_csv(filepath)
    cols = {str(c).strip().lower().replace("\n", "_").replace(" ", "_"): c for c in raw.columns}

    def pick(*names):
        for n in names:
            if n in cols:
                return raw[cols[n]]
        return pd.Series([np.nan] * len(raw))

    out = pd.DataFrame(index=raw.index)
    out["fund_name"] = pick("fund_name", "description").astype(str).str.strip()
    out["fund_name"] = out["fund_name"].replace({"": np.nan, "nan": np.nan}).fillna("UNKNOWN_FUND")
    out["vintage_year"] = pd.to_numeric(pick("vintage_year"), errors="coerce")
    out["vintage_year"] = out["vintage_year"].fillna(out["fund_name"].map(_infer_vintage_from_name))
    out["capital_committed"] = _clean_num(pick("capital_committed"))  # UTIMCO 2023 generally does not provide this
    out["capital_contributed"] = _clean_num(pick("capital_contributed", "capital_invested", "cash_in"))
    out["capital_distributed"] = _clean_num(pick("capital_distributed", "cash_out"))
    total_value = _clean_num(pick("total_value"))
    out["nav"] = _clean_num(pick("nav"))
    out["nav"] = out["nav"].where(out["nav"].notna(), total_value - out["capital_distributed"])
    out["net_irr"] = _clean_num(pick("net_irr"))
    irr_med = out["net_irr"].dropna().median()
    if pd.notna(irr_med) and irr_med > 1.5:
        out["net_irr"] = out["net_irr"] / 100.0
    out["tvpi"] = _clean_num(pick("tvpi"))
    contrib = pd.to_numeric(out["capital_contributed"], errors="coerce")
    out["tvpi"] = out["tvpi"].where(out["tvpi"].notna(), np.where(contrib > 0, (out["capital_distributed"] + out["nav"]) / contrib, np.nan))
    out["dpi"] = np.where(contrib > 0, out["capital_distributed"] / contrib, np.nan)
    out["source"] = "UTIMCO"
    out["scraped_date"] = pick("scraped_date").fillna(str(date.today()))
    out["reporting_period"] = pick("reporting_period").fillna("2023-02-28")
    out["vintage_year"] = pd.to_numeric(out["vintage_year"], errors="coerce").astype("Int64")
    return out


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

    if "canonical_gp" in df.columns:
        df["canonical_gp"] = df["canonical_gp"].map(normalize_canonical_gp_label)

    mi_gps = {"a16z", "andreessen horowitz", "founders fund", "social capital"}
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

    if "vintage_source" not in df.columns:
        df["vintage_source"] = "unknown"

    # Merge canonical UTIMCO rows into master with reporting-period precedence.
    utimco_path = "data/utimco_2023.csv"
    if os.path.exists(utimco_path):
        ut = pd.read_csv(utimco_path)
        if not ut.empty and "fund_name" in ut.columns:
            def _bucket_to_category(v):
                s = str(v or "").lower()
                if "pe" in s:
                    return "PE"
                if "growth" in s:
                    return "Growth"
                if "fund of funds" in s:
                    return "Opportunities"
                return "Venture"

            ut_rows = pd.DataFrame({
                "canonical_gp": ut.get("canonical_gp").map(normalize_canonical_gp_label),
                "gp_display_name": ut.get("canonical_gp").map(normalize_canonical_gp_label),
                "fund_name": ut.get("fund_name"),
                "vintage_year": pd.to_numeric(ut.get("vintage_year"), errors="coerce").astype("Int64"),
                "vintage_source": ut.get("vintage_source", "unknown"),
                "fund_category": ut.get("fund_category", pd.Series(index=ut.index, dtype="object")).map(_bucket_to_category),
                "sub_strategy": ut.get("fund_category"),
                "fund_size_usd_m": pd.to_numeric(ut.get("capital_contributed"), errors="coerce") / 1_000_000.0,
                "fund_size_confidence": "Derived from UTIMCO capital_contributed",
                "firm_aum_usd_b": np.nan,
                "firm_founded": np.nan,
                "hq_city": "",
                "investment_focus": ut.get("fund_category"),
                "stage_focus": "",
                "notable_portfolio": "",
                "source": "UTIMCO",
                "reporting_period": ut.get("reporting_period", "2023-02-28"),
                "tvpi": pd.to_numeric(ut.get("tvpi"), errors="coerce"),
                "dpi": pd.to_numeric(ut.get("dpi"), errors="coerce"),
                "net_irr": pd.to_numeric(ut.get("net_irr"), errors="coerce"),
                "irr_meaningful": ut.get("vintage_year").notna() & (pd.to_numeric(ut.get("vintage_year"), errors="coerce") <= 2020),
                "performance_note": "UTIMCO LP disclosure (2023-02-28).",
                "gross_tvpi": np.nan,
                "gross_dpi": np.nan,
                "data_source_type": "LP-Disclosed",
            })

            for c in ut_rows.columns:
                if c not in df.columns:
                    df[c] = np.nan
            for c in df.columns:
                if c not in ut_rows.columns:
                    ut_rows[c] = np.nan

            combined = pd.concat([df, ut_rows[df.columns]], ignore_index=True, sort=False)

            def _parse_reporting_period(v):
                s = str(v or "").strip()
                if not s or s.lower() in {"nan", "none", "unknown"}:
                    return None
                m = re.match(r"^(\\d{4})-(\\d{2})-(\\d{2})$", s)
                if m:
                    y, mn, d = map(int, m.groups())
                    return date(y, mn, d)
                m = re.match(r"^(\\d{4})-Q([1-4])$", s, flags=re.I)
                if m:
                    y, q = int(m.group(1)), int(m.group(2))
                    md = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
                    mn, d = md[q]
                    return date(y, mn, d)
                m = re.match(r"^ir(\\d{2})(\\d{2})(\\d{2})$", s, flags=re.I)
                if m:
                    mm, dd, yy = map(int, m.groups())
                    return date(2000 + yy, mm, dd)
                m = re.search(r"(\\d{4})", s)
                if m:
                    return date(int(m.group(1)), 1, 1)
                return None

            combined["__rp_date"] = combined["reporting_period"].map(_parse_reporting_period)
            combined["__rp_ord"] = combined["__rp_date"].map(lambda d: d.toordinal() if d else -1)
            combined["__utimco_bonus"] = (
                (combined["source"].astype(str) == "UTIMCO")
                & (combined["reporting_period"].astype(str) == "2023-02-28")
            ).astype(int)

            combined = (
                combined.sort_values(["fund_name", "__rp_ord", "__utimco_bonus"])
                .drop_duplicates(subset=["fund_name"], keep="last")
                .drop(columns=["__rp_date", "__rp_ord", "__utimco_bonus"])
                .reset_index(drop=True)
            )
            combined["canonical_gp"] = combined["canonical_gp"].map(normalize_canonical_gp_label)
            combined["gp_display_name"] = combined["gp_display_name"].where(
                combined["gp_display_name"].notna(), combined["canonical_gp"]
            )
            df = combined

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


@st.cache_data
def load_target_firm_patterns():
    path = "metadata/target_firms.csv"
    out = {}
    if os.path.exists(path):
        df = pd.read_csv(path)
        if {"canonical_gp", "match_pattern"}.issubset(df.columns):
            for gp, grp in df.groupby("canonical_gp"):
                pats = [p for p in grp["match_pattern"].astype(str).tolist() if str(p).strip()]
                if pats:
                    out[str(gp)] = pats
            return out

    fallback = "data/coverage_snapshot.csv"
    if os.path.exists(fallback):
        df = pd.read_csv(fallback)
        if {"canonical_gp", "fund_name"}.issubset(df.columns):
            for gp, grp in df.groupby("canonical_gp"):
                # fallback patterns from first 3 words of fund name
                pats = []
                for f in grp["fund_name"].dropna().astype(str).head(5):
                    toks = _norm_text(f).split()
                    if toks:
                        pats.append(" ".join(toks[: min(3, len(toks))]))
                if pats:
                    out[str(gp)] = sorted(set(pats))
    return out


def canonical_gp_for_fund_name(fund_name: str, pattern_map: dict):
    text_norm = _norm_text(fund_name)
    if not text_norm:
        return None
    text_tokens = set(text_norm.split())
    best = None
    best_score = -1.0

    # Fast deterministic pass: substring/token-only checks.
    for canonical_gp, patterns in pattern_map.items():
        for p in patterns:
            p_norm = str(p)
            if not p_norm:
                continue
            if p_norm in text_norm:
                score = len(p_norm) + 5.0
            else:
                ptoks = [t for t in p_norm.split() if t]
                if ptoks and all(t in text_tokens for t in ptoks):
                    score = float(len(p_norm))
                else:
                    continue
            if score > best_score:
                best = canonical_gp
                best_score = score

    if best is not None:
        return best

    # Fuzzy fallback: only for hard misses, with strict gates to keep this cheap.
    for canonical_gp, patterns in pattern_map.items():
        for p in patterns:
            p_norm = str(p)
            if len(p_norm) < 5:
                continue
            ptoks = [t for t in p_norm.split() if t]
            if ptoks and not any(t in text_tokens for t in ptoks):
                continue
            ratio = SequenceMatcher(None, p_norm, text_norm).ratio()
            if ratio >= 0.9 and ratio > best_score:
                best = canonical_gp
                best_score = ratio
    return best


def _infer_category_from_name(name: str) -> str:
    s = str(name).lower()
    if "opportun" in s:
        return "Opportunities"
    if "growth" in s:
        return "Growth"
    if any(k in s for k in ["buyout", "credit", "distress", "special situations", "structured"]):
        return "PE"
    return "Venture"


def style_chart_readability(fig: go.Figure):
    current_margin = fig.layout.margin if fig.layout.margin is not None else go.layout.Margin()
    current_left = current_margin.l if current_margin.l is not None else 40
    current_right = current_margin.r if current_margin.r is not None else 40
    current_top = current_margin.t if current_margin.t is not None else 40
    current_bottom = current_margin.b if current_margin.b is not None else 40

    fig.update_layout(
        font=dict(family="Inter", size=14, color="#111827"),
        title_font=dict(color="#111827"),
        xaxis=dict(
            title_font=dict(color="#111827"),
            tickfont=dict(color="#111827"),
            gridcolor="#F3F4F6",
        ),
        yaxis=dict(
            title_font=dict(color="#111827"),
            tickfont=dict(color="#111827"),
            gridcolor="#F3F4F6",
        ),
        legend=dict(
            font=dict(color="#111827"),
            title_font=dict(color="#111827"),
        ),
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#D1D5DB",
            font=dict(family="Inter", size=13, color="#111827"),
            align="left",
        ),
        margin=dict(
            l=max(72, current_left),
            r=max(36, current_right),
            t=max(56, current_top),
            b=max(50, current_bottom),
        ),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        modebar=dict(remove=["zoom", "pan", "select", "lasso2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d", "hoverClosestCartesian", "hoverCompareCartesian"]),
    )
    if fig.layout.legend is not None:
        legend_orientation = getattr(fig.layout.legend, "orientation", None)
        if legend_orientation == "h":
            fig.update_layout(
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.08,
                    xanchor="left",
                    x=0,
                    font=dict(size=12),
                )
            )
        else:
            fig.update_layout(legend=dict(font=dict(size=12)))

    fig.update_xaxes(
        title_font=dict(size=15),
        tickfont=dict(size=13),
        automargin=True,
        title_standoff=16,
        ticklabelposition="outside",
    )
    fig.update_yaxes(
        title_font=dict(size=15),
        tickfont=dict(size=13),
        automargin=True,
        title_standoff=14,
        ticklabelposition="outside",
    )


def build_focus_master(df_master: pd.DataFrame, df_unified: pd.DataFrame, pattern_map: dict = None) -> pd.DataFrame:
    # Remove Accel-KKR globally; keep only Accel VC rows if/when available.
    master = df_master.copy()
    if "canonical_gp" in master.columns:
        master["canonical_gp"] = master["canonical_gp"].map(normalize_canonical_gp_label)
    if "gp_display_name" in master.columns:
        master["gp_display_name"] = master["gp_display_name"].where(master["gp_display_name"].notna(), master.get("canonical_gp"))
    master_gp = master.get("canonical_gp", pd.Series(index=master.index, dtype="object")).astype(str)
    master_fn = master.get("fund_name", pd.Series(index=master.index, dtype="object")).astype(str)
    drop_mask = master_gp.str.contains("accel-kkr", case=False, na=False) | master_fn.str.contains("accel-kkr", case=False, na=False)
    master = master[~drop_mask].copy()

    u = df_unified.copy()
    if u.empty:
        return master

    for col in ["fund_name", "source", "reporting_period"]:
        if col not in u.columns:
            u[col] = np.nan
    for col in ["vintage_year", "capital_committed", "tvpi", "dpi", "net_irr"]:
        u[col] = pd.to_numeric(u.get(col), errors="coerce")

    # Combine metadata-driven mapping with explicit fallback patterns used in the current product.
    merged_patterns = {}
    if pattern_map:
        for gp, patterns in pattern_map.items():
            canonical_gp = normalize_canonical_gp_label(gp)
            existing = merged_patterns.get(canonical_gp, [])
            normed = [_norm_text(p) for p in patterns if str(p).strip()]
            merged_patterns[canonical_gp] = sorted(set(existing + normed), key=len, reverse=True)
    for spec in FOCUS_FIRM_SPECS:
        gp = normalize_canonical_gp_label(spec["canonical_gp"])
        base = merged_patterns.get(gp, [])
        add = []
        for p in spec["include"]:
            if not str(p).strip():
                continue
            p_text = str(p).replace("\\\\b", "").replace("\\b", "").replace("\\", "")
            add.append(_norm_text(p_text))
        merged_patterns[gp] = sorted(set(base + add), key=len, reverse=True)

    # Canonicalize unified rows to target firms.
    u["canonical_gp"] = u["fund_name"].astype(str).map(lambda x: canonical_gp_for_fund_name(x, merged_patterns))
    u["canonical_gp"] = u["canonical_gp"].map(normalize_canonical_gp_label)
    u = u[u["canonical_gp"].notna()].copy()

    # Exclude known non-target aliases where needed (e.g., Accel-KKR should not map to Accel).
    exclude_mask = u["fund_name"].astype(str).str.contains(r"accel-kkr", case=False, na=False)
    u = u[~exclude_mask].copy()

    rows = []
    for canonical_gp, sub in u.groupby("canonical_gp"):
        sub = sub.copy()
        if sub.empty:
            continue

        # Normalize IRR scale and useful numeric defaults.
        irr = pd.to_numeric(sub["net_irr"], errors="coerce")
        sub["net_irr"] = np.where(irr.abs() > 2, irr / 100.0, irr)
        sub["fund_size_usd_m"] = pd.to_numeric(sub["capital_committed"], errors="coerce") / 1_000_000.0
        sub["fund_category"] = sub["fund_name"].astype(str).map(_infer_category_from_name)
        sub["sub_strategy"] = np.where(sub["fund_category"].eq("Growth"), "Growth Equity", "Venture")
        sub["irr_meaningful"] = (
            pd.to_numeric(sub["vintage_year"], errors="coerce").le(2020)
            & sub["net_irr"].notna()
            & sub["net_irr"].abs().ne(1.0)
        )
        sub["gp_display_name"] = canonical_gp
        sub["fund_size_confidence"] = "Derived from LP committed capital"
        sub["firm_aum_usd_b"] = np.nan
        sub["firm_founded"] = np.nan
        sub["hq_city"] = ""
        sub["investment_focus"] = ""
        sub["stage_focus"] = ""
        sub["notable_portfolio"] = ""
        sub["performance_note"] = "Auto-added from LP-disclosed unified database matching."
        sub["data_source_type"] = "LP-Disclosed"
        sub["gross_tvpi"] = np.nan
        sub["gross_dpi"] = np.nan

        rows.append(
            sub[
                [
                    "canonical_gp",
                    "gp_display_name",
                    "fund_name",
                    "vintage_year",
                    "fund_category",
                    "sub_strategy",
                    "fund_size_usd_m",
                    "fund_size_confidence",
                    "firm_aum_usd_b",
                    "firm_founded",
                    "hq_city",
                    "investment_focus",
                    "stage_focus",
                    "notable_portfolio",
                    "source",
                    "reporting_period",
                    "gross_tvpi",
                    "tvpi",
                    "gross_dpi",
                    "dpi",
                    "net_irr",
                    "irr_meaningful",
                    "performance_note",
                    "data_source_type",
                ]
            ].copy()
        )

    if not rows:
        return master

    added = pd.concat(rows, ignore_index=True)
    combined = pd.concat([master, added], ignore_index=True, sort=False)
    combined["canonical_gp"] = combined["canonical_gp"].map(normalize_canonical_gp_label)
    combined["gp_display_name"] = combined.get("gp_display_name", pd.Series(index=combined.index, dtype="object")).where(
        combined.get("gp_display_name", pd.Series(index=combined.index, dtype="object")).notna(),
        combined["canonical_gp"],
    )
    combined["vintage_year"] = pd.to_numeric(combined.get("vintage_year"), errors="coerce").astype("Int64")

    # De-dupe within a GP while preserving multi-source rows where reporting periods differ.
    for col in ["source", "reporting_period"]:
        if col not in combined.columns:
            combined[col] = np.nan
    combined = combined.drop_duplicates(
        subset=["canonical_gp", "fund_name", "vintage_year", "source", "reporting_period"],
        keep="first",
    ).reset_index(drop=True)

    # Final Accel-KKR safety filter.
    gp2 = combined.get("canonical_gp", pd.Series(index=combined.index, dtype="object")).astype(str)
    fn2 = combined.get("fund_name", pd.Series(index=combined.index, dtype="object")).astype(str)
    combined = combined[
        ~gp2.str.contains("accel-kkr", case=False, na=False)
        & ~fn2.str.contains("accel-kkr", case=False, na=False)
    ].copy()

    return combined


@st.cache_data(show_spinner=False)
def build_focus_master_cached(df_master: pd.DataFrame, df_unified: pd.DataFrame, pattern_items: tuple) -> pd.DataFrame:
    pattern_map = {gp: list(patterns) for gp, patterns in pattern_items}
    return build_focus_master(df_master, df_unified, pattern_map)


def get_focus_master(df_master: pd.DataFrame, df_unified: pd.DataFrame, target_patterns: dict = None) -> pd.DataFrame:
    safe_patterns = target_patterns or {}
    pattern_items = tuple(
        sorted(
            (
                str(gp),
                tuple(sorted({_norm_text(p) for p in pats if str(p).strip()})),
            )
            for gp, pats in safe_patterns.items()
        )
    )
    return build_focus_master_cached(df_master, df_unified, pattern_items)


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
    meta = GP_METADATA.get(gp_name, {})
    fund_count = len(gp_data)
    vintage_series = pd.to_numeric(gp_data["vintage_year"], errors="coerce").dropna()
    if vintage_series.empty:
        vintage_range = "—"
    else:
        vintage_range = "{0}–{1}".format(int(vintage_series.min()), int(vintage_series.max()))

    dpi_series = pd.to_numeric(gp_data["dpi"], errors="coerce").dropna()
    med_dpi = dpi_series.median() if not dpi_series.empty else np.nan
    if pd.isna(med_dpi):
        dpi_color = "#9CA3AF"
    elif med_dpi >= 2:
        dpi_color = "#E8571F"
    elif med_dpi >= 1:
        dpi_color = "#16A34A"
    else:
        dpi_color = "#6B7280"

    dpi_for_best = pd.to_numeric(gp_data["dpi"], errors="coerce")
    dpi_nonnull = dpi_for_best.dropna()
    best_dpi_idx = dpi_nonnull.idxmax() if not dpi_nonnull.empty else None
    best_fund = None
    if best_dpi_idx is not None and best_dpi_idx in gp_data.index and pd.notna(gp_data.loc[best_dpi_idx, "dpi"]):
        best_fund = gp_data.loc[best_dpi_idx]

    founded_val = row.get("firm_founded")
    if pd.isna(founded_val) and "founded" in meta:
        founded_val = meta["founded"]
    founded = "—" if pd.isna(founded_val) else str(int(float(founded_val)))

    aum_val = row.get("firm_aum_usd_b")
    if pd.isna(aum_val) and "aum_approx" in meta:
        aum_val = meta["aum_approx"]
    aum_txt = "—" if pd.isna(aum_val) else "${0:.1f}B AUM".format(float(aum_val))

    hq = str(row.get("hq_city", "")).strip()
    if (not hq or hq.lower() in {"nan", "none"}) and meta.get("hq"):
        hq = meta["hq"]
    if not hq:
        hq = "—"

    strategy = meta.get("strategy", "")
    if not strategy:
        strategy = " / ".join(gp_data["fund_category"].dropna().astype(str).unique()[:2])
    notable = meta.get("notable", str(row.get("notable_portfolio", "")))
    notable_tokens = [t.strip() for t in str(notable).split(",") if t.strip()]
    notable_short = ", ".join(notable_tokens[:4]) if notable_tokens else "—"

    best_fund_line = "Best: —"
    if best_fund is not None:
        best_fund_line = "Best: {0} · {1:.2f}×".format(str(best_fund.get("fund_name", "")), float(best_fund.get("dpi")))

    st.markdown(
        """
    <div class="firm-card">
        <div class="firm-name">{0}</div>
        <div class="firm-meta">EST. {1} · {2}</div>
        <div style="margin-bottom:8px"><span class="badge badge-utimco">UTIMCO</span></div>
        <div class="firm-aum-badge">{3}</div>
        <div style="margin-bottom:8px;font-family:'IBM Plex Mono',monospace;font-size:10px;color:#9CA3AF;letter-spacing:0.06em;text-transform:uppercase">{4}</div>
        <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:8px">
            <div>
                <div class="firm-best-irr-label">MEDIAN DPI</div>
                <div class="firm-best-irr-value" style="color:{5}">{6}</div>
            </div>
            <div style="text-align:right">
                <div class="firm-best-irr-label">FUNDS · VINTAGE</div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:16px;font-weight:500;color:#374151">{7} · {8}</div>
            </div>
        </div>
        <div style="font-size:12px;color:#374151;line-height:1.5"><strong>{9}</strong></div>
        <div style="font-size:11px;color:#6B7280;margin-top:6px;line-height:1.5">{10}</div>
    </div>
    """.format(
            html.escape(str(row.get("gp_display_name", gp_name))),
            founded,
            html.escape(hq.upper()),
            html.escape(aum_txt),
            html.escape(strategy if strategy else "N/A"),
            dpi_color,
            "—" if pd.isna(med_dpi) else "{0:.2f}×".format(float(med_dpi)),
            fund_count,
            html.escape(vintage_range),
            html.escape(best_fund_line),
            html.escape(notable_short),
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

    def _as_bool(v) -> bool:
        if pd.isna(v):
            return False
        if isinstance(v, str):
            return v.strip().lower() in {"true", "1", "yes", "y", "t"}
        return bool(v)

    row = gp_df.iloc[0]
    if "data_source_type" in gp_df.columns:
        is_market_intel = len(gp_df) > 0 and gp_df["data_source_type"].astype(str).str.strip().eq("Market Intelligence").all()
    else:
        is_market_intel = False
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
        if _as_bool(v):
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


def render_insights(df_master: pd.DataFrame, bench: pd.DataFrame, incomplete_rows: pd.DataFrame = None):
    render_page_header("INSIGHTS", "ANALYTICAL FINDINGS FROM PUBLIC LP DISCLOSURE DATA")
    bench_meaningful = bench[bench["vintage_year"] <= 2020].sort_values("vintage_year")

    st.markdown('<div class="section-label">KEY FINDINGS</div>', unsafe_allow_html=True)
    insight_cards = [
        {
            "number": "01",
            "label": "DPI DROUGHT",
            "headline": "Every 2017+ fund: DPI < 0.5×",
            "body": "Across LP-disclosed and market-intel sources, every 2017+ vintage remains cash-light. ARCH XI (2017) has 26.2% IRR with 0.00× DPI; True Ventures VI (2019) is 0.01× DPI.",
        },
        {
            "number": "02",
            "label": "HIGHEST LP-DISCLOSED DPI",
            "headline": "USV 2012 Fund: 22.86×",
            "body": "Union Square Ventures 2012 Fund returned 22.86× DPI and 24.88× TVPI on ~$26M contributed. It is now the highest cash-return multiple in LP-disclosed data.",
        },
        {
            "number": "03",
            "label": "LP BENCHMARK BEATER",
            "headline": "USV 2012: 24.88× TVPI",
            "body": "Against an approximate 2012 CA Q1 TVPI near 4.0×, USV 2012 is a clear outlier. IA Ventures Fund II at 20.6× TVPI is another under-the-radar benchmark beater.",
        },
        {
            "number": "04",
            "label": "FEE DRAG",
            "headline": "a16z Fund III",
            "body": "Gross 15.7× to net 11.3× implies meaningful carry and fee drag at scale. The gross/net gap remains one of the most important LP realities.",
        },
        {
            "number": "05",
            "label": "SELECTION BIAS",
            "headline": "Intel sample skews high",
            "body": "Market-intelligence funds cluster above benchmark lines. That may indicate real alpha, but it may also reflect selection effects in what gets circulated.",
        },
        {
            "number": "06",
            "label": "CHINA RISK",
            "headline": "HongShan regime shift",
            "body": "2010 vintage HongShan funds show strong realized outcomes; 2020 vintage funds sit near/sub-1× with weaker IRR. Same platform, very different macro regime.",
        },
        {
            "number": "07",
            "label": "MANAGER VARIANCE",
            "headline": "Same GP, wide dispersion",
            "body": "USV, ARCH, and True Ventures show dramatic fund-to-fund spread across vintages. Vintage timing and distribution cycles can matter as much as manager brand.",
        },
        {
            "number": "08",
            "label": "DARK HORSE",
            "headline": "IA Ventures Fund II",
            "body": "20.6× TVPI and 9.64× DPI from a smaller, less-visible manager. LP-level records often surface leaders missed by reputation-first narratives.",
        },
    ]

    # Render in 2 rows x 4 columns
    chunks = [insight_cards[i : i + 4] for i in range(0, len(insight_cards), 4)]
    for chunk in chunks:
        cols = st.columns(4)
        for col, card in zip(cols, chunk):
            with col:
                st.markdown(
                    """
                <div style="border:1px solid #E5E7EB;border-radius:6px;padding:16px;background:#fff;height:100%;min-height:220px;display:flex;flex-direction:column">
                    <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:0.15em;
                        text-transform:uppercase;color:#9CA3AF;margin-bottom:4px">
                        {0} / {1}
                    </div>
                    <div style="font-family:'Inter',sans-serif;font-size:15px;font-weight:700;
                        color:#111827;margin-bottom:8px;line-height:1.2;flex-grow:0">
                        {2}
                    </div>
                    <div style="font-family:'Inter',sans-serif;font-size:12px;color:#6B7280;line-height:1.5;flex-grow:1">
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
    firm_df["x_plot"] = pd.to_numeric(firm_df["meaningful_count"], errors="coerce").astype(float)
    firm_df["y_plot"] = pd.to_numeric(firm_df["median_dpi"], errors="coerce").astype(float)
    # Reduce visual dominance of very large firms while keeping relative scale.
    firm_df["bubble_size"] = np.log1p(firm_df["total_capital_bn"].clip(lower=0) * 8.0)
    if firm_df["bubble_size"].max() == 0:
        firm_df["bubble_size"] = 1.0
    # De-overlap dense cluster in lower-left region.
    dense = (firm_df["x_plot"] <= 4.0) & (firm_df["y_plot"] <= 1.5)
    if dense.any():
        dense_df = firm_df[dense].sort_values(["x_plot", "y_plot", "firm"]).copy()
        n = len(dense_df)
        x_offsets = np.tile(np.array([-0.35, 0.0, 0.35]), int(np.ceil(n / 3)))[:n]
        y_offsets = np.tile(np.array([0.14, 0.0, -0.14]), int(np.ceil(n / 3)))[:n]
        firm_df.loc[dense_df.index, "x_plot"] = dense_df["x_plot"].values + x_offsets
        firm_df.loc[dense_df.index, "y_plot"] = dense_df["y_plot"].values + y_offsets
    # Label only high-signal firms to avoid text collisions.
    firm_df["label_text"] = np.where(
        (firm_df["y_plot"] >= 1.75)
        | (firm_df["x_plot"] >= 8.0)
        | (firm_df["source_type"] == "Market Intelligence"),
        firm_df["firm"],
        "",
    )

    color_map = {"LP-Disclosed": "#2C3E50", "Market Intelligence": "#E8571F"}
    fig = px.scatter(
        firm_df,
        x="x_plot",
        y="y_plot",
        size="bubble_size",
        text="label_text",
        color="source_type",
        color_discrete_map=color_map,
        size_max=36,
        template="plotly_white",
        labels={"meaningful_count": "Funds with Meaningful Data", "median_dpi": "Median Net DPI (×)"},
        custom_data=["firm", "canonical_gp", "total_capital_bn", "meaningful_count", "median_dpi", "source_type"],
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
    fig.update_traces(
        textposition="top center",
        textfont_size=10,
        marker=dict(line=dict(width=1.2, color="white"), opacity=0.8),
        hovertemplate="<b>%{customdata[0]}</b><br>Canonical GP: %{customdata[1]}<br>Data Source Type: %{customdata[5]}<br>Funds with meaningful data: %{customdata[3]}<br>Median net DPI: %{customdata[4]:.2f}×<br>Total capital represented: %{customdata[2]:.2f}B<br><br><i>1.0× means LPs have gotten their invested capital back. 2.0× means strong realized cash performance.</i><extra></extra>",
    )
    fig.update_layout(
        height=430,
        showlegend=True,
        legend=dict(title="Source", orientation="h", font=dict(size=10)),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        xaxis=dict(gridcolor="#F3F4F6"),
        yaxis=dict(gridcolor="#F3F4F6"),
        font=dict(family="Inter", size=11),
        margin=dict(l=50, r=40, t=30, b=60),
    )
    fig.update_xaxes(title_text="Funds with Meaningful Data")
    fig.update_yaxes(title_text="Median Net DPI (×)")
    style_chart_readability(fig)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        """
    <div class="insight-box" style="margin-top:0.2rem">
        <div class="insight-label">● HOW TO READ THIS</div>
        <div class="insight-body">
            Firms higher on the chart have stronger realized cash performance (higher median DPI).
            Larger bubbles represent firms with more capital represented in this dataset.
            Orange bubbles are market intelligence data; slate bubbles are LP-disclosed records.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="chart-title" style="margin-top:1.0rem">FUND COVERAGE TIMELINE</div>', unsafe_allow_html=True)
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
    tl["firm_display"] = tl["gp_display_name"].where(
        tl["gp_display_name"].notna(), tl["canonical_gp"]
    ).astype(str)
    tl["dpi_fmt"] = np.where(tl["dpi"].notna(), tl["dpi"].map(lambda v: "{0:.2f}×".format(v)), "N/A")
    tl["tvpi_fmt"] = np.where(tl["tvpi"].notna(), tl["tvpi"].map(lambda v: "{0:.2f}×".format(v)), "N/A")

    gp_order = tl.groupby("canonical_gp")["vintage_year"].min().sort_values().index.tolist()
    label_lookup = (
        tl.sort_values("vintage_year")
        .drop_duplicates("canonical_gp")
        .set_index("canonical_gp")["firm_display"]
        .to_dict()
    )
    firms_order = [label_lookup.get(gp, str(gp)) for gp in gp_order]

    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=tl["vintage_year"].astype(int),
            y=tl["firm_display"],
            mode="markers",
            marker=dict(symbol="square", size=10, color=tl["dot_color"], line=dict(width=1, color="#9CA3AF")),
            showlegend=False,
            customdata=tl[["fund_name", "vintage_year", "dpi_fmt", "tvpi_fmt"]].values,
            hovertemplate="<b>%{customdata[0]}</b><br>Vintage: %{customdata[1]}<br>DPI: %{customdata[2]}<br>TVPI: %{customdata[3]}<extra></extra>",
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
        height=max(430, len(firms_order) * 26 + 150),
        template="plotly_white",
        xaxis=dict(title="Vintage Year", gridcolor="#F3F4F6", dtick=3),
        yaxis=dict(title="", tickfont=dict(size=10), categoryorder="array", categoryarray=firms_order),
        legend=dict(title="DPI Range", font=dict(size=10), orientation="h"),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font=dict(family="Inter", size=10),
        margin=dict(l=120, r=30, t=30, b=60),
    )
    style_chart_readability(fig2)
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

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

    # High-signal UTIMCO outlier annotations.
    for pat, label, ax, ay in [
        (r"Union Square Ventures 2012 Fund", "USV 2012<br>24.9× TVPI", 35, -55),
        (r"Spark Capital II", "Spark II", -20, -45),
        (r"Union Square Ventures 2004", "USV 2004", 20, -55),
    ]:
        sub_lp = lp_df[lp_df["fund_name"].astype(str).str.contains(pat, case=False, na=False)]
        if not sub_lp.empty:
            r0 = sub_lp.iloc[0]
            if pd.notna(r0.get("vintage_year")) and pd.notna(r0.get("net_irr")):
                fig.add_annotation(
                    x=float(r0["vintage_year"]),
                    y=float(r0["net_irr"]) * 100.0,
                    text=label,
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor="#E8571F",
                    arrowwidth=1.2,
                    font=dict(size=9, color="#E8571F", family="IBM Plex Mono"),
                    bgcolor="#FFF4EF",
                    bordercolor="#E8571F",
                    borderwidth=1,
                    borderpad=5,
                    ax=ax,
                    ay=ay,
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
    style_chart_readability(fig)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
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

    if incomplete_rows is not None and not incomplete_rows.empty:
        with st.expander("Developer: Incomplete rows (missing vintage_year or capital_contributed)", expanded=False):
            show_cols = [
                c
                for c in ["source", "fund_name", "vintage_year", "capital_contributed", "reporting_period", "net_irr", "tvpi", "dpi"]
                if c in incomplete_rows.columns
            ]
            st.dataframe(
                incomplete_rows[show_cols].sort_values(["source", "fund_name"], na_position="last"),
                use_container_width=True,
                hide_index=True,
            )

    st.markdown('<div class="section-label" style="margin-top:2rem">02B / DPI LEADERBOARD — TOP LP-DISCLOSED CASH RETURNS</div>', unsafe_allow_html=True)
    dpi_df = df[(df["data_source_type"] == "LP-Disclosed") & pd.to_numeric(df["dpi"], errors="coerce").gt(0)].copy()
    dpi_df["dpi"] = pd.to_numeric(dpi_df["dpi"], errors="coerce")
    dpi_df["tvpi"] = pd.to_numeric(dpi_df["tvpi"], errors="coerce")
    dpi_df["net_irr"] = pd.to_numeric(dpi_df["net_irr"], errors="coerce")
    dpi_df = dpi_df.sort_values("dpi", ascending=False).head(15).reset_index(drop=True)

    leaderboard_html = ""
    for i, r in dpi_df.iterrows():
        name = html.escape(str(r.get("fund_name", "")))
        gp = html.escape(str(r.get("canonical_gp", "")))
        vintage = "—" if pd.isna(r.get("vintage_year")) else str(int(r.get("vintage_year")))
        dpi_val = r.get("dpi")
        dpi_str = "—" if pd.isna(dpi_val) else "{0:.2f}×".format(dpi_val)
        tvpi_str = "—" if pd.isna(r.get("tvpi")) else "{0:.2f}×".format(r.get("tvpi"))
        irr_str = "—" if pd.isna(r.get("net_irr")) else "{0:.1f}%".format(r.get("net_irr") * 100)
        source_raw = str(r.get("source", ""))
        source_cls = SOURCE_BADGE_CLASS.get(source_raw, "badge-estimated")
        source_lbl = SOURCE_SHORT.get(source_raw, source_raw[:10])

        dpi_color = "#E8571F" if dpi_val and dpi_val >= 1.0 else "#111827"
        
        leaderboard_html += (
            "<tr>"
            '<td class="id-col">{0}</td>'
            '<td style="font-weight:600">{1} <span style="font-weight:400;color:#6B7280;margin-left:4px">/ {2}</span></td>'
            '<td class="numeric">{3}</td>'
            '<td><span class="badge {4}">{5}</span></td>'
            '<td class="numeric">{6}</td>'
            '<td class="numeric" style="color:{7};font-weight:600">{8}</td>'
            '<td class="numeric">{9}</td>'
            "</tr>"
        ).format(
            str(i + 1).zfill(2), 
            name, gp,
            vintage,
            source_cls, html.escape(source_lbl),
            tvpi_str,
            dpi_color, dpi_str,
            irr_str
        )

    _render_html(
        (
            '<table class="fund-table"><thead><tr>'
            "<th>#</th><th>FUND / GP</th><th class=\"right\">VINTAGE</th><th>SOURCE</th>"
            '<th class="right">TVPI</th><th class="right" style="color:#E8571F">DPI ▲</th><th class="right">IRR</th>'
            "</tr></thead><tbody>{0}</tbody></table>"
        ).format(leaderboard_html)
    )

    st.markdown(
        """
    <div class="insight-box">
        <div class="insight-label">● ANALYST INSIGHT — THE DPI LEADERBOARD</div>
        <div class="insight-body">
            <strong>USV 2012 Fund now leads LP-disclosed DPI in this dataset.</strong>
            The top cohort is concentrated in smaller vintage funds where realization cycles have fully played out.
            UTIMCO materially improves visibility into this segment and highlights how distribution outcomes can diverge
            from brand-based expectations.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label" style="margin-top:2rem">02C / THE GROSS vs NET GAP — FEES QUANTIFIED</div>', unsafe_allow_html=True)
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

    st.markdown('<div class="section-label" style="margin-top:2rem">02D / THE REALIZATION MAP</div>', unsafe_allow_html=True)
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
    style_chart_readability(fig_map)
    st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="section-label" style="margin-top:2rem">02E / NET IRR RANKING — HOVER FOR vs BENCHMARK</div>', unsafe_allow_html=True)
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
    style_chart_readability(fig_rank)
    st.plotly_chart(fig_rank, use_container_width=True, config={"displayModeBar": False})
    bench_disclaimer()

    st.markdown('<div class="section-label">03 / VINTAGE COHORT ANALYSIS</div>', unsafe_allow_html=True)
    
    # Chart 3A: TVPI by Vintage
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
        height=450,
        template="plotly_white",
        xaxis=dict(title="Vintage Year", gridcolor="#F3F4F6", dtick=2),
        yaxis=dict(title="Net TVPI (×)", gridcolor="#F3F4F6"),
        legend=dict(font=dict(size=9)),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font=dict(family="Inter", size=11, color="#111827"),
        margin=dict(t=20, b=30),
    )
    style_chart_readability(fig_tvpi)
    st.plotly_chart(fig_tvpi, use_container_width=True, config={"displayModeBar": False})
    n_per = tvpi_df.groupby("vintage_year").size().to_dict()
    n_str = "  ·  ".join(["{0}: n={1}".format(y, n) for y, n in sorted(n_per.items()) if y >= 2005])
    st.markdown("<div style=\"font-family:'IBM Plex Mono',monospace;font-size:9px;color:#9CA3AF\">{0}</div>".format(html.escape(n_str)), unsafe_allow_html=True)
    bench_disclaimer()

    # Chart 3B: Capital Realization
    st.markdown('<div class="chart-title" style="margin-top: 3rem;">CAPITAL REALIZATION BY VINTAGE</div>', unsafe_allow_html=True)
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
            font=dict(size=9, color="#111827", family="IBM Plex Mono"),
        )
    fig_cap.update_layout(
        barmode="stack",
        height=450,
        template="plotly_white",
        xaxis=dict(title="Vintage Year", gridcolor="#F3F4F6", dtick=2),
        yaxis=dict(title="Capital ($B)", gridcolor="#F3F4F6"),
        legend=dict(font=dict(size=9), orientation="h", y=-0.15),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font=dict(family="Inter", size=11, color="#111827"),
        margin=dict(t=20, b=40),
    )
    style_chart_readability(fig_cap)
    st.plotly_chart(fig_cap, use_container_width=True, config={"displayModeBar": False})
    st.markdown("<div style=\"font-family:'IBM Plex Mono',monospace;font-size:9px;color:#9CA3AF\">% = realization rate per vintage. Orange = cash distributed to LPs. Grey = unrealized paper value.</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-label">04 / GP PERFORMANCE TRAJECTORIES</div>', unsafe_allow_html=True)
    
    try:
        # Chart 4A: IRR Trajectory
        traj = lp_df[lp_df["net_irr"].notna()].copy()
        if not traj.empty:
            st.markdown('<div class="chart-title">IRR TRAJECTORY — FIRMS WITH 3+ FUNDS</div>', unsafe_allow_html=True)
            eligible = traj.groupby("canonical_gp").size()
            eligible = eligible[eligible >= 3].index
            traj = traj[traj["canonical_gp"].isin(eligible)]
            if not traj.empty:
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
                    height=450,
                    template="plotly_white",
                    xaxis=dict(gridcolor="#F3F4F6", cursor="pointer"),
                    yaxis=dict(title="Net IRR (%)", gridcolor="#F3F4F6"),
                    legend=dict(font=dict(size=9)),
                    plot_bgcolor="#FFFFFF",
                    paper_bgcolor="#FFFFFF",
                    font=dict(family="Inter", size=11, color="#111827"),
                    margin=dict(t=20),
                )
                style_chart_readability(fig_traj)
                st.plotly_chart(fig_traj, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})
                bench_disclaimer()
            else:
                st.info("No firms in dataset with 3+ funds for trajectory analysis.")
        else:
            st.info("Insufficient data for IRR trajectories.")

        # Chart 4B: Cash Returned by Strategy
        strat = lp_df[lp_df["dpi"].notna() & lp_df["fund_size_usd_m"].notna()].copy()
        if not strat.empty:
            st.markdown('<div class="chart-title" style="margin-top: 3rem;">CASH RETURNED BY STRATEGY — CAPITAL-WEIGHTED DPI</div>', unsafe_allow_html=True)
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
                height=450,
                template="plotly_white",
                xaxis=dict(title="Capital-Weighted Avg Net DPI (×)", gridcolor="#F3F4F6"),
                yaxis=dict(gridcolor="#F3F4F6"),
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                font=dict(family="Inter", size=11, color="#111827"),
                margin=dict(t=20, l=20),
            )
            style_chart_readability(fig_strat)
            st.plotly_chart(fig_strat, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})
            st.markdown("<div style=\"font-family:'IBM Plex Mono',monospace;font-size:9px;color:#9CA3AF\">Capital-weighted: larger funds influence the average proportionally. LP-disclosed funds only.</div>", unsafe_allow_html=True)
        else:
            st.info("Insufficient data for strategy returns analysis.")

    except Exception as e:
        st.warning("Additional GP Performance Trajectories are not available for this data slice.")


    st.markdown('<div class="section-label">05 / WITHIN-GP VARIANCE — IRR RANGE (UTIMCO)</div>', unsafe_allow_html=True)
    var_df = df[
        (df["source"].astype(str) == "UTIMCO")
        & df["net_irr"].notna()
        & df["canonical_gp"].notna()
    ].copy()
    gp_stats = (
        var_df.groupby("canonical_gp")
        .agg(min_irr=("net_irr", "min"), max_irr=("net_irr", "max"), n=("fund_name", "count"))
        .reset_index()
    )
    gp_stats = gp_stats[gp_stats["n"] >= 2].copy()
    if not gp_stats.empty:
        gp_stats["range"] = gp_stats["max_irr"] - gp_stats["min_irr"]
        gp_stats = gp_stats.sort_values("range", ascending=True)
        fig_var = go.Figure()
        fig_var.add_trace(
            go.Scatter(
                x=(gp_stats["min_irr"] * 100),
                y=gp_stats["canonical_gp"],
                mode="markers",
                marker=dict(color="#9CA3AF", size=8),
                name="Min IRR",
            )
        )
        fig_var.add_trace(
            go.Scatter(
                x=(gp_stats["max_irr"] * 100),
                y=gp_stats["canonical_gp"],
                mode="markers",
                marker=dict(color="#E8571F", size=9),
                name="Max IRR",
            )
        )
        for _, r in gp_stats.iterrows():
            fig_var.add_shape(
                type="line",
                x0=float(r["min_irr"]) * 100,
                x1=float(r["max_irr"]) * 100,
                y0=r["canonical_gp"],
                y1=r["canonical_gp"],
                line=dict(color="#CBD5E1", width=2),
            )
        variance_annotations = {
            "Union Square Ventures": "USV: 22.86× DPI to near-zero DPI across vintages",
            "ARCH Venture Partners": "ARCH: 4.64× DPI (Fund VII) vs 0.00× (Fund XII)",
            "True Ventures": "True: 4.29× DPI (Fund IV) vs 0.01× (Fund VI)",
        }
        for gp, note in variance_annotations.items():
            sub = gp_stats[gp_stats["canonical_gp"] == gp]
            if sub.empty:
                continue
            r0 = sub.iloc[0]
            fig_var.add_annotation(
                x=float(r0["max_irr"]) * 100.0,
                y=gp,
                text=note,
                showarrow=False,
                xshift=10,
                align="left",
                font=dict(size=9, color="#6B7280", family="IBM Plex Mono"),
                bgcolor="rgba(255,255,255,0.75)",
            )
        fig_var.update_layout(
            height=max(320, 28 * len(gp_stats) + 120),
            template="plotly_white",
            xaxis=dict(title="Net IRR (%)", gridcolor="#F3F4F6"),
            yaxis=dict(title="", gridcolor="#FFFFFF"),
            legend=dict(orientation="h"),
            margin=dict(l=90, r=30, t=20, b=50),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            font=dict(color="#111827"),
        )
        style_chart_readability(fig_var)
        st.plotly_chart(fig_var, use_container_width=True, config={"displayModeBar": False})

        st.markdown(
            """
        <div class="insight-box">
            <div class="insight-label">● VARIANCE READ</div>
            <div class="insight-body">
                UTIMCO fund-by-fund history shows large dispersion inside the same manager franchise.
                USV, ARCH, and True Ventures each show wide internal ranges across vintages.
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

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

    st.markdown(
        """
    <div class="insight-box" style="margin-top:-0.5rem; margin-bottom:1.5rem">
        <div class="insight-label">● UTIMCO DATA NOTES</div>
        <div class="insight-body">
            <strong>Vintage year note:</strong> UTIMCO does not disclose vintage year in fund
            performance reports. Vintages marked as inferred are derived from fund names and
            cross-referenced close windows. Funds with unknown vintage are excluded from benchmark
            comparisons.<br><br>
            <strong>Capital committed vs contributed:</strong> UTIMCO reports capital invested
            (contributed/called capital) rather than original commitment. This value is used as
            denominator for DPI/TVPI context in this source.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">03 / MARKET INTELLIGENCE SOURCES</div>', unsafe_allow_html=True)
    st.markdown(
        """
    <div style="font-family:'Inter',sans-serif;font-size:14px;color:#374151;line-height:1.7; margin-bottom:1.5rem">
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
        <div style="font-family:'Inter',sans-serif;font-size:14px;color:#374151;line-height:1.75; margin-bottom: 2rem;">
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
        </div>
        """
    )

    nav_options = ["ABOUT", "INSIGHTS", "TOP FIRMS", "FUND DATABASE", "SOURCES"]
    if hasattr(st, "segmented_control"):
        active_page = st.segmented_control(
            "Navigate",
            nav_options,
            default=nav_options[0],
            label_visibility="collapsed",
        )
    else:
        active_page = st.radio(
            "Navigate",
            nav_options,
            horizontal=True,
            label_visibility="collapsed",
        )

    if not active_page:
        active_page = nav_options[0]

    if active_page == "ABOUT":
        render_about()
    elif active_page == "FUND DATABASE":
        try:
            df_unified = load_unified()
        except Exception as exc:
            st.error("Failed loading data/unified_funds.csv: {0}".format(exc))
            render_footer()
            return
        try:
            df_market_intel = load_market_intel()
        except Exception as exc:
            st.error("Failed loading gp_disclosed_funds.csv: {0}".format(exc))
            df_market_intel = pd.DataFrame()
        render_fund_database(df_unified, df_market_intel)
    elif active_page == "TOP FIRMS":
        try:
            df_unified = load_unified()
            df_master = load_master_full()
            target_patterns = load_target_firm_patterns()
            df_focus_master = get_focus_master(df_master, df_unified, target_patterns)
        except Exception as exc:
            st.error("Failed loading firm datasets: {0}".format(exc))
            render_footer()
            return
        render_firms(df_focus_master)
    elif active_page == "INSIGHTS":
        try:
            df_unified = load_unified()
            df_master = load_master_full()
            bench = load_benchmarks()
            target_patterns = load_target_firm_patterns()
            df_focus_master = get_focus_master(df_master, df_unified, target_patterns)
        except Exception as exc:
            st.error("Failed loading insights datasets: {0}".format(exc))
            render_footer()
            return

        incomplete_rows = df_unified[
            df_unified["vintage_year"].isna() | pd.to_numeric(df_unified.get("capital_contributed"), errors="coerce").isna()
        ].copy()
        render_insights(df_focus_master, bench, incomplete_rows)
    elif active_page == "SOURCES":
        try:
            df_unified = load_unified()
            df_master = load_master_full()
        except Exception as exc:
            st.error("Failed loading source datasets: {0}".format(exc))
            render_footer()
            return
        render_sources(df_unified, df_master)

    render_footer()


if __name__ == "__main__":
    main()
