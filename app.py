import html
import os
import re
from difflib import SequenceMatcher
from datetime import date, datetime
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&family=Lora:ital,wght@0,400;0,600;0,700;1,400&family=DM+Mono:wght@400;500&display=swap');

    :root, html, body, .stApp { color-scheme: light !important; }
    .main .block-container { padding: 1rem 1.8rem 1.1rem 1.8rem; max-width: 100%; }
    .stApp { background-color: #FFFFFF; color: #111827; font-family: 'Inter', sans-serif; }
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* Editorial Headings */
    .editorial-header {
        font-family: 'Lora', serif;
        font-size: 42px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.5rem;
        line-height: 1.1;
    }
    .editorial-subtitle {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #E8571F;
        margin-bottom: 2rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        background: #FFFFFF !important; border-bottom: 1px solid #E5E7EB !important; gap: 0; padding: 0; margin-bottom: 1.3rem;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'IBM Plex Mono', monospace !important; font-size: 11px !important; font-weight: 500 !important;
        letter-spacing: 0.08em !important; text-transform: uppercase !important; 
        color: #9CA3AF !important;
        padding: 12px 20px !important; border-bottom: 2px solid transparent !important; 
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab"] button,
    .stTabs [data-baseweb="tab"] span,
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] div {
        color: #9CA3AF !important;
        background: transparent !important;
    }
    .stTabs [aria-selected="true"] { 
        color: #111827 !important; 
        border-bottom: 2px solid #E8571F !important; 
        background: transparent !important; 
    }
    .stTabs [aria-selected="true"] button,
    .stTabs [aria-selected="true"] span,
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] div {
        color: #111827 !important;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab-panel"] { padding-top: 0; }

    .hero-stat-card {
        padding: 24px;
        background: #FAFAFA;
        border: 1px solid #E5E7EB;
        border-radius: 4px;
        height: 100%;
    }
    .hero-stat-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        color: #9CA3AF;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
        text-transform: uppercase;
    }
    .hero-stat-value {
        font-family: 'Inter', sans-serif;
        font-size: 28px;
        font-weight: 800;
        color: #111827;
        line-height: 1.2;
    }
    .hero-stat-sub {
        font-family: 'Lora', serif;
        font-size: 13px;
        font-style: italic;
        color: #6B7280;
        margin-top: 4px;
    }

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
        font-family: 'Lora', serif; font-size: 11px; font-weight: 700;
        letter-spacing: 0.15em; text-transform: uppercase; color: #E8571F;
        border-top: 2px solid #E8571F; padding-top: 8px; margin: 3rem 0 1.25rem 0;
    }
    .chart-title {
        font-family: 'Lora', serif;
        font-size: 18px;
        font-weight: 700;
        color: #111827;
        margin: 1.5rem 0 0.5rem 0;
    }
    .chart-subtitle {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        letter-spacing: 0.07em;
        color: #9CA3AF;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }

    .fund-table { width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; }
    .fund-table th {
        font-family: 'IBM Plex Mono', monospace; font-size: 10px; font-weight: 600;
        letter-spacing: 0.1em; text-transform: uppercase; color: #9CA3AF;
        padding: 10px 12px; border-bottom: 1px solid #E5E7EB; text-align: left; background: #FAFAFA;
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
        font-family: 'IBM Plex Mono', monospace; font-size: 13px; font-weight: 600;
        color: #E8571F; text-align: right;
    }
    .fund-table tr:hover td { background: #FFF8F5; }

    .badge {
        display: inline-block; font-family: 'IBM Plex Mono', monospace; font-size: 10px;
        font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase;
        padding: 3px 8px; border-radius: 4px; border: 1px solid;
    }
    .badge-realized { background:#ECFDF5; color:#065F46; border-color:#86EFAC; }
    .badge-returning { background:#EFF6FF; color:#1D4ED8; border-color:#BFDBFE; }
    .badge-early { background:#FFFBEB; color:#92400E; border-color:#FDE68A; }
    .badge-cashlight { background:#FEF2F2; color:#991B1B; border-color:#FECACA; }

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
    .badge-lp-disclosed { border: 1px solid #E5E7EB; color: #6B7280; background: transparent; }

    .insight-box {
        background: #FAFAFA; border-left: 3px solid #E8571F;
        border-radius: 4px; padding: 20px 24px; margin: 1.5rem 0;
    }
    .insight-label {
        font-family: 'IBM Plex Mono', monospace; font-size: 10px; font-weight: 600;
        letter-spacing: 0.12em; text-transform: uppercase; color: #111827; margin-bottom: 10px;
    }
    .insight-body { font-family: 'Lora', serif; font-size: 15px; color: #374151; line-height: 1.6; }
    .insight-body strong { font-weight: 700; color: #111827; }

    .footer-wrap { margin-top: 4rem; border-top: 1px solid #E5E7EB; padding-top: 24px; padding-bottom: 2rem; }
    .footer-text { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #9CA3AF; line-height: 1.6; }

    /* Plotly Clean Overrides */
    .modebar, .modebar-container, .plotly-notifier { display: none !important; }

    /* ── CARTA-STYLE INSIGHTS ── */
    /* Loading animation */
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(20px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes shimmer {
      0%   { background-position: -600px 0; }
      100% { background-position: 600px 0; }
    }
    @keyframes pulse-dot {
      0%, 100% { opacity: 0.2; transform: scale(0.8); }
      50%       { opacity: 1;   transform: scale(1.1); }
    }

    .ins-loader {
      display: flex; align-items: center; gap: 14px;
      padding: 28px 0 40px;
    }
    .ins-loader-mark {
      width: 32px; height: 32px; border-radius: 8px;
      background: #E8571F; color: white;
      font-family: 'Lora', serif; font-size: 18px; font-weight: 700;
      display: flex; align-items: center; justify-content: center;
    }
    .ins-loader-dots { display: flex; gap: 5px; }
    .ins-loader-dots span {
      width: 6px; height: 6px; border-radius: 50%;
      background: #E8571F; display: block;
      animation: pulse-dot 1.2s ease-in-out infinite;
    }
    .ins-loader-dots span:nth-child(2) { animation-delay: 0.2s; }
    .ins-loader-dots span:nth-child(3) { animation-delay: 0.4s; }
    .ins-loader-text {
      font-family: 'DM Mono', monospace; font-size: 11px;
      letter-spacing: 0.1em; text-transform: uppercase; color: #9CA3AF;
    }

    /* Section entry animations */
    .ins-section {
      animation: fadeUp 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
    }
    .ins-section:nth-child(1) { animation-delay: 0.05s; }
    .ins-section:nth-child(2) { animation-delay: 0.12s; }
    .ins-section:nth-child(3) { animation-delay: 0.19s; }
    .ins-section:nth-child(4) { animation-delay: 0.26s; }
    .ins-section:nth-child(5) { animation-delay: 0.33s; }

    /* Page hero */
    .ins-eyebrow {
      font-family: 'DM Mono', monospace; font-size: 10px; font-weight: 500;
      letter-spacing: 0.15em; text-transform: uppercase; color: #E8571F;
      margin-bottom: 10px;
    }
    .ins-headline {
      font-family: 'Lora', serif; font-size: 34px; font-weight: 700;
      color: #111827; letter-spacing: -0.02em; line-height: 1.18;
      margin-bottom: 14px;
    }
    .ins-headline em { font-style: italic; color: #E8571F; }
    .ins-deck {
      font-family: 'Inter', sans-serif; font-size: 15px; color: #374151;
      line-height: 1.7; max-width: 620px;
      border-left: 3px solid #E8571F; padding-left: 18px;
      margin-bottom: 40px;
    }

    /* Hero stat grid */
    .ins-stat-row {
      display: grid; grid-template-columns: repeat(4, 1fr);
      gap: 1px; background: #E5E7EB;
      border: 1px solid #E5E7EB; border-radius: 10px;
      overflow: hidden; margin-bottom: 64px;
    }
    .ins-stat-cell {
      background: #FFFFFF; padding: 22px 26px 18px;
    }
    .ins-stat-cell.accent { background: #FFF4EF; }
    .ins-stat-label {
      font-family: 'DM Mono', monospace; font-size: 9px; font-weight: 500;
      letter-spacing: 0.12em; text-transform: uppercase;
      color: #9CA3AF; margin-bottom: 8px;
    }
    .ins-stat-cell.accent .ins-stat-label { color: #E8571F; }
    .ins-stat-value {
      font-family: 'Lora', serif; font-size: 32px; font-weight: 700;
      color: #111827; line-height: 1; margin-bottom: 5px;
    }
    .ins-stat-cell.accent .ins-stat-value { color: #E8571F; }
    .ins-stat-sub { font-family: 'Inter', sans-serif; font-size: 12px; color: #9CA3AF; line-height: 1.4; }

    /* Section structure */
    .ins-section-rule {
      display: flex; align-items: flex-start; gap: 14px;
      margin-bottom: 30px;
    }
    .ins-section-num {
      font-family: 'DM Mono', monospace; font-size: 10px; font-weight: 500;
      letter-spacing: 0.15em; text-transform: uppercase; color: #E8571F;
      border-top: 2px solid #E8571F; padding-top: 8px; flex-shrink: 0;
    }
    .ins-section-line { flex: 1; height: 1px; background: #E5E7EB; margin-top: 13px; }

    /* Chart block */
    .ins-chart-headline {
      font-family: 'Lora', serif; font-size: 21px; font-weight: 700;
      color: #111827; letter-spacing: -0.015em; line-height: 1.25;
      margin-bottom: 8px;
    }
    .ins-chart-headline em { font-style: italic; color: #E8571F; }
    .ins-chart-standfirst {
      font-family: 'Inter', sans-serif; font-size: 14px; color: #374151;
      line-height: 1.65; max-width: 620px; margin-bottom: 22px;
    }
    .ins-chart-frame {
      background: #FAFAFA; border: 1px solid #E5E7EB;
      border-radius: 10px; padding: 24px 24px 16px;
      margin-bottom: 14px;
    }
    .ins-takeaway {
      background: #FFF4EF; border-left: 3px solid #E8571F;
      border-radius: 0 6px 6px 0; padding: 14px 18px;
      font-family: 'Inter', sans-serif; font-size: 13px;
      color: #374151; line-height: 1.6; margin-top: 12px;
    }
    .ins-takeaway strong { color: #111827; }
    .ins-footnote {
      font-family: 'DM Mono', monospace; font-size: 9px;
      color: #9CA3AF; letter-spacing: 0.04em; margin-top: 8px;
    }

    /* Vintage pills */
    .ins-pill-grid {
      display: grid; grid-template-columns: repeat(8, 1fr);
      gap: 8px; margin-bottom: 12px;
    }
    .ins-pill {
      text-align: center; border-radius: 8px;
      padding: 14px 6px 12px; border: 1px solid #E5E7EB;
      background: #FAFAFA;
    }
    .ins-pill.p-strong { background: #FFF4EF; border-color: #FED7AA; }
    .ins-pill.p-mid    { background: #ECFDF5; border-color: #BBF7D0; }
    .ins-pill.p-low    { background: #FFFBEB; border-color: #FDE68A; }
    .ins-pill.p-none   { background: #F9FAFB; border-color: #E5E7EB; }
    .ins-pill-year {
      font-family: 'DM Mono', monospace; font-size: 9px; color: #9CA3AF;
      letter-spacing: 0.05em; margin-bottom: 5px;
    }
    .ins-pill-val {
      font-family: 'Lora', serif; font-size: 17px; font-weight: 700;
      line-height: 1; margin-bottom: 4px;
    }
    .ins-pill.p-strong .ins-pill-val { color: #E8571F; }
    .ins-pill.p-mid    .ins-pill-val { color: #16A34A; }
    .ins-pill.p-low    .ins-pill-val { color: #D97706; }
    .ins-pill.p-none   .ins-pill-val { color: #9CA3AF; }
    .ins-pill-label { font-family: 'DM Mono', monospace; font-size: 8px; letter-spacing: 0.08em; text-transform: uppercase; color: #9CA3AF; }

    /* Leaderboard */
    .ins-lb { width: 100%; border-collapse: collapse; }
    .ins-lb th {
      font-family: 'DM Mono', monospace; font-size: 9px; font-weight: 500;
      letter-spacing: 0.1em; text-transform: uppercase; color: #9CA3AF;
      padding: 8px 12px 10px; border-bottom: 2px solid #111827; text-align: left;
    }
    .ins-lb th.r { text-align: right; }
    .ins-lb td {
      padding: 12px 12px; border-bottom: 1px solid #F3F4F6;
      font-family: 'Inter', sans-serif; font-size: 13px; color: #111827;
      vertical-align: middle;
    }
    .ins-lb td.mono { font-family: 'DM Mono', monospace; font-size: 12px; text-align: right; }
    .ins-lb td.dpi-col { font-family: 'DM Mono', monospace; font-size: 13px; font-weight: 600; color: #E8571F; text-align: right; }
    .ins-lb td.green-col { font-family: 'DM Mono', monospace; font-size: 12px; color: #16A34A; text-align: right; }
    .ins-lb td.num { font-family: 'DM Mono', monospace; font-size: 11px; color: #9CA3AF; }
    .ins-lb tr:hover td { background: #FFF8F5; }
    .ins-fund-name { font-weight: 500; }
    .ins-fund-gp { font-family: 'DM Mono', monospace; font-size: 10px; color: #9CA3AF; margin-top: 1px; }
    .ins-bar-wrap { height: 3px; background: #E5E7EB; border-radius: 2px; margin-top: 5px; max-width: 100px; }
    .ins-bar-fill { height: 3px; background: #E8571F; border-radius: 2px; }

    /* Two-up callout cards */
    .ins-callouts { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 24px; }
    .ins-callout {
      background: #FAFAFA; border: 1px solid #E5E7EB;
      border-radius: 10px; padding: 22px;
    }
    .ins-callout.featured { background: #FFF4EF; border-color: #FED7AA; }
    .ins-callout-eye {
      font-family: 'DM Mono', monospace; font-size: 9px; font-weight: 500;
      letter-spacing: 0.12em; text-transform: uppercase;
      color: #9CA3AF; margin-bottom: 8px;
    }
    .ins-callout.featured .ins-callout-eye { color: #E8571F; }
    .ins-callout-num {
      font-family: 'Lora', serif; font-size: 38px; font-weight: 700;
      color: #111827; line-height: 1; margin-bottom: 8px;
    }
    .ins-callout.featured .ins-callout-num { color: #E8571F; }
    .ins-callout-body { font-family: 'Inter', sans-serif; font-size: 13px; color: #374151; line-height: 1.55; }

    /* Realization progress bars */
    .ins-real-row { display: grid; grid-template-columns: 72px 1fr 52px; gap: 12px; align-items: center; padding: 7px 0; }
    .ins-real-year { font-family: 'DM Mono', monospace; font-size: 11px; color: #374151; }
    .ins-real-track { height: 14px; background: #F3F4F6; border-radius: 3px; overflow: hidden; }
    .ins-real-fill { height: 14px; border-radius: 3px; }
    .ins-real-pct { font-family: 'DM Mono', monospace; font-size: 11px; font-weight: 500; text-align: right; }

    /* Manager variance */
    .ins-mgr-table { width: 100%; }
    .ins-mgr-row { display: grid; grid-template-columns: 180px 1fr 62px 62px; gap: 14px; align-items: center; padding: 13px 0; border-bottom: 1px solid #F3F4F6; }
    .ins-mgr-row.header { border-bottom: 2px solid #111827; padding-bottom: 8px; }
    .ins-mgr-name { font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 500; }
    .ins-mgr-hdr { font-family: 'DM Mono', monospace; font-size: 9px; font-weight: 500; letter-spacing: 0.1em; text-transform: uppercase; color: #9CA3AF; }
    .ins-mgr-hdr.r { text-align: right; }
    .ins-mgr-range { position: relative; height: 10px; }
    .ins-mgr-track { position: absolute; top: 2px; left: 0; right: 0; height: 6px; background: #F3F4F6; border-radius: 3px; }
    .ins-mgr-fill { position: absolute; top: 2px; height: 6px; background: #E8571F; border-radius: 3px; opacity: 0.65; }
    .ins-mgr-dot { position: absolute; top: -1px; width: 8px; height: 8px; border-radius: 50%; border: 1.5px solid white; }
    .ins-mgr-val { font-family: 'DM Mono', monospace; font-size: 12px; text-align: right; }
    .ins-mgr-val.max { color: #E8571F; font-weight: 600; }
    .ins-mgr-val.min { color: #9CA3AF; }

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
def load_data():
    master_path = "data/vc_fund_master.csv"
    unified_path = "data/unified_funds.csv"
    
    if not os.path.exists(master_path):
        return pd.DataFrame()
        
    df_m = pd.read_csv(master_path)
    
    # Pre-cleaning numeric columns
    for col in ['vintage_year', 'tvpi', 'dpi', 'net_irr', 'gross_tvpi', 'gross_dpi', 'fund_size_usd_m']:
        if col in df_m.columns:
            df_m[col] = pd.to_numeric(df_m[col], errors='coerce')
            
    # Remove Accel-KKR permanently as requested
    if 'canonical_gp' in df_m.columns:
        df_m = df_m[~df_m['canonical_gp'].str.contains('Accel-KKR', case=False, na=False)]
        
    # Exclude PE-only funds from aggregate views
    if 'fund_category' in df_m.columns:
        df_m = df_m[df_m['fund_category'] != 'PE']
        
    # Drop rows without vintage_year or invalid vintage
    df_m = df_m.dropna(subset=['vintage_year'])
    df_m['vintage_year'] = df_m['vintage_year'].astype(int)
    
    # Join with Unified for capital columns (scraped_date, nav, contributed, distributed)
    if os.path.exists(unified_path):
        df_u = pd.read_csv(unified_path)
        for col in ['capital_contributed', 'capital_distributed', 'nav', 'vintage_year']:
            if col in df_u.columns:
                df_u[col] = pd.to_numeric(df_u[col], errors='coerce')
        
        # Merge on fund_name and vintage_year
        join_cols = ['fund_name', 'vintage_year']
        available_join = [c for c in join_cols if c in df_u.columns and c in df_m.columns]
        
        extra_cols = [c for c in ['capital_contributed', 'capital_distributed', 'nav', 'scraped_date'] if c in df_u.columns]
        
        if available_join:
            df_u_subset = df_u[available_join + extra_cols].drop_duplicates(subset=available_join)
            df = pd.merge(df_m, df_u_subset, on=available_join, how='left')
        else:
            df = df_m
    else:
        df = df_m
        
    # Calculate missing DPI and TVPI from capital columns if missing
    if 'capital_contributed' in df.columns and 'capital_distributed' in df.columns:
        valid_contrib = (df['capital_contributed'] > 0)
        df['dpi'] = df['dpi'].fillna(np.where(valid_contrib, df['capital_distributed'] / df['capital_contributed'], np.nan))
        if 'nav' in df.columns:
            df['tvpi'] = df['tvpi'].fillna(np.where(valid_contrib, (df['capital_distributed'] + df['nav']) / df['capital_contributed'], np.nan))
            
    # CalPERS Fix: net_irr 1.0 is often a placeholder for "Not Meaningful"
    if 'source' in df.columns and 'net_irr' in df.columns:
        df.loc[(df['source'] == 'CalPERS') & (df['net_irr'] == 1.0), 'net_irr'] = np.nan
        
    # data_source_type normalization
    if 'data_source_type' in df.columns:
        df['data_source_type'] = df['data_source_type'].fillna('LP-Disclosed')
        
    # Handle infinities
    df = df.replace([np.inf, -np.inf], np.nan)
    
    return df

@st.cache_data
def load_unified():
    """Alias for backward compatibility with database and firmas logic."""
    return load_data()

@st.cache_data
def load_master_full():
    """Alias for backward compatibility with top firms logic."""
    return load_data()

@st.cache_data
def load_market_intel():
    """Returns only market intelligence subset from the master."""
    df = load_data()
    if df.empty: return df
    return df[df['data_source_type'] == 'Market Intelligence']


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
def _norm_text(v):
    if pd.isna(v):
        return ""
    v = str(v).lower().strip()
    v = re.sub(r'[^a-z0-9 ]', ' ', v)
    return " ".join(v.split())



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
        title="",
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
    if v is None or pd.isna(v):
        return "—"
    try:
        return "{0:.2f}×".format(float(v))
    except (ValueError, TypeError):
        return "—"


def _fmt_irr(v):
    if v is None or pd.isna(v):
        return "—"
    try:
        return "{0:.1f}%".format(float(v) * 100)
    except (ValueError, TypeError):
        return "—"


def _fmt_committed(v):
    if v is None or pd.isna(v):
        return "—"
    try:
        return "${0:.0f}M".format(float(v) / 1_000_000)
    except (ValueError, TypeError):
        return "—"


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
        source = str(row.get("source", "")) if pd.notna(row.get("source")) else ""
        badge_class = SOURCE_BADGE_CLASS.get(source, "badge-estimated")
        badge_label = SOURCE_SHORT.get(source, str(source).upper()[:12])
        
        tvpi_val = row.get("tvpi")
        tvpi_val = float(tvpi_val) if pd.notna(tvpi_val) else None
        tvpi = _fmt_multiple(tvpi_val)
        
        committed_val = row.get("capital_committed")
        committed_val = float(committed_val) if pd.notna(committed_val) else None
        committed = _fmt_committed(committed_val)
        
        name = html.escape(str(row.get("fund_name", "")))
        
        vintage_val = row.get("vintage_year")
        vintage = "—" if pd.isna(vintage_val) else str(int(float(vintage_val)))
        
        dpi_val = row.get("dpi")
        dpi_val = float(dpi_val) if pd.notna(dpi_val) else None
        
        irr_val = row.get("net_irr")
        irr_val = float(irr_val) if pd.notna(irr_val) else None

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
            dpi_html(dpi_val),
            irr_html(irr_val),
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
    med_dpi = float(dpi_series.median()) if not dpi_series.empty else np.nan
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
    founded_val = float(founded_val) if pd.notna(founded_val) else None
    founded = "—" if founded_val is None else str(int(founded_val))

    aum_val = row.get("firm_aum_usd_b")
    if pd.isna(aum_val) and "aum_approx" in meta:
        aum_val = meta["aum_approx"]
    aum_val = float(aum_val) if pd.notna(aum_val) else None
    aum_txt = "—" if aum_val is None else "${0:.1f}B AUM".format(aum_val)

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
        best_fund_name = str(best_fund.get("fund_name", ""))
        best_fund_dpi = best_fund.get("dpi")
        best_fund_dpi = float(best_fund_dpi) if pd.notna(best_fund_dpi) else None
        if best_fund_dpi is not None:
            best_fund_line = "Best: {0} · {1:.2f}×".format(best_fund_name, best_fund_dpi)

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
            "—" if pd.isna(row.get("firm_aum_usd_b")) else "{0:.1f}".format(float(row.get("firm_aum_usd_b"))),
        ),
        unsafe_allow_html=True,
    )

    meaningful = gp_df[gp_df["irr_meaningful"] == True]

    if is_market_intel and str(selected_gp).lower() == "a16z":
        gross_tvpi = float(meaningful["gross_tvpi"].median()) if not meaningful.empty else np.nan
        gross_dpi = float(meaningful["gross_dpi"].median()) if not meaningful.empty else np.nan
        net_tvpi = float(meaningful["tvpi"].median()) if not meaningful.empty else np.nan
        net_dpi = float(meaningful["dpi"].median()) if not meaningful.empty else np.nan
        best_net_irr = float(meaningful["net_irr"].max()) if not meaningful.empty else np.nan
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
        med_gross_tvpi = float(meaningful["gross_tvpi"].median()) if not meaningful.empty else np.nan
        med_net_tvpi = float(meaningful["tvpi"].median()) if not meaningful.empty else np.nan
        med_net_dpi = float(meaningful["dpi"].median()) if not meaningful.empty else np.nan
        best_irr = float(meaningful["net_irr"].max()) if not meaningful.empty else np.nan

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
        med_tvpi = float(meaningful["tvpi"].median()) if not meaningful.empty else np.nan
        med_dpi = float(meaningful["dpi"].median()) if not meaningful.empty else np.nan
        best_irr = float(meaningful["net_irr"].max()) if not meaningful.empty else np.nan

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
        vintage_val = r.get("vintage_year")
        vintage = "—" if pd.isna(vintage_val) else str(int(float(vintage_val)))
        gross_col = ""
        gross_cell = ""
        if is_market_intel:
            gross_col = "<th class='right'>GROSS TVPI</th>"
            gross_tvpi_val = r.get("gross_tvpi")
            gross_tvpi_val = float(gross_tvpi_val) if pd.notna(gross_tvpi_val) else None
            gross_cell = "<td class='numeric'>{0}</td>".format(_fmt_multiple(gross_tvpi_val))

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
            "—" if pd.isna(r.get("fund_size_usd_m")) else "${0:.0f}M".format(float(r.get("fund_size_usd_m"))),
            gross_cell,
            _fmt_multiple(float(r.get("tvpi")) if pd.notna(r.get("tvpi")) else None),
            _fmt_multiple(float(r.get("dpi")) if pd.notna(r.get("dpi")) else None),
            _fmt_irr(float(r.get("net_irr")) if pd.notna(r.get("net_irr")) else None),
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
            gross_tvpi_val = r.get("gross_tvpi")
            tvpi_val = r.get("tvpi")
            if pd.notna(gross_tvpi_val) and pd.notna(tvpi_val):
                gross_tvpi_val = float(gross_tvpi_val)
                tvpi_val = float(tvpi_val)
                drag = gross_tvpi_val - tvpi_val
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
                        _fmt_multiple(gross_tvpi_val),
                        _fmt_multiple(tvpi_val),
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




def render_insights_hero(df):
    total_funds = len(df)
    drought_df = df[df['vintage_year'] >= 2017]
    drought_pct = (drought_df['dpi'] < 0.1).mean() * 100 if not drought_df.empty else 0
    top_idx = df['dpi'].idxmax() if not df.empty and df['dpi'].notna().any() else None
    top_dpi = df.loc[top_idx, 'dpi'] if top_idx is not None else 0
    top_fund = df.loc[top_idx, 'fund_name'] if top_idx is not None else 'N/A'
    drag_df = df[df['gross_tvpi'].notna() & df['tvpi'].notna()]
    avg_drag = (drag_df['gross_tvpi'] - drag_df['tvpi']).mean() if not drag_df.empty else 0
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="hero-stat-card"><div class="hero-stat-label">Funds Tracked</div><div class="hero-stat-value">{total_funds:,}</div><div class="hero-stat-sub">Public LP + Intel</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="hero-stat-card"><div class="hero-stat-label">DPI Drought</div><div class="hero-stat-value">{drought_pct:.0f}%</div><div class="hero-stat-sub">2017+ funds < 0.1x DPI</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="hero-stat-card"><div class="hero-stat-label">Top Returner</div><div class="hero-stat-value">{top_dpi:.1f}x</div><div class="hero-stat-sub">{top_fund}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="hero-stat-card"><div class="hero-stat-label">Avg. Fee Drag</div><div class="hero-stat-value">{avg_drag:.2f}x</div><div class="hero-stat-sub">Gross vs Net gap</div></div>', unsafe_allow_html=True)

def render_section_1_vintage(df):
    st.markdown('<div class="section-label">01 / DPI BY VINTAGE — REALIZATION PROGRESS</div>', unsafe_allow_html=True)
    v_agg = df.groupby('vintage_year').agg({'dpi': 'median', 'tvpi': 'median'}).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=v_agg['vintage_year'], y=v_agg['dpi'], name='Median DPI (Cash)', marker_color='#E8571F'))
    fig.add_trace(go.Scatter(x=v_agg['vintage_year'], y=v_agg['tvpi'], name='Median TVPI (Total)', mode='lines+markers', line=dict(color='#111827', width=2)))
    fig.update_layout(template='plotly_white', height=400, legend=dict(orientation="h", y=1.1, x=1), xaxis=dict(dtick=2), margin=dict(t=50))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def render_section_2_leaderboard(df):
    st.markdown('<div class="section-label">02 / CASH RETURN LEADERBOARD — TOP 10 LP-DISCLOSED</div>', unsafe_allow_html=True)
    top_10 = df[df['data_source_type'] == 'LP-Disclosed'].nlargest(10, 'dpi')[['fund_name', 'canonical_gp', 'vintage_year', 'tvpi', 'dpi']]
    st.dataframe(top_10, use_container_width=True, hide_index=True, column_config={'dpi': st.column_config.NumberColumn("DPI", format="%.2fx"), 'tvpi': st.column_config.NumberColumn("TVPI", format="%.2fx"), 'vintage_year': st.column_config.NumberColumn("Vintage", format="%d")})

def render_section_3_gap(df):
    st.markdown('<div class="section-label">03 / REALIZATION GAP — VINTAGE DEPTH</div>', unsafe_allow_html=True)
    v_agg = df[df['vintage_year'] >= 2010].groupby('vintage_year').agg({'dpi': 'median', 'tvpi': 'median'}).reset_index()
    v_agg['rvpi'] = (v_agg['tvpi'] - v_agg['dpi']).clip(lower=0)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=v_agg['vintage_year'], y=v_agg['dpi'], name='Cash (DPI)', marker_color='#E8571F'))
    fig.add_trace(go.Bar(x=v_agg['vintage_year'], y=v_agg['rvpi'], name='Remaining (RVPI)', marker_color='#E5E7EB'))
    fig.update_layout(barmode='stack', template='plotly_white', height=400, legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

@st.cache_data(show_spinner=False)
def _precompute_insights(df_master_hash: str, df_master: pd.DataFrame, bench: pd.DataFrame):
    """Cache heavy pandas aggregations for the Insights page."""
    lp_full = df_master[df_master["data_source_type"] == "LP-Disclosed"].copy()
    
    vy = (
        lp_full[lp_full["vintage_year"].notna() & lp_full["dpi"].notna()]
        .groupby("vintage_year")
        .agg(med_dpi=("dpi","median"), med_tvpi=("tvpi","median"), n=("fund_name","count"))
        .reset_index()
    )
    pr = (
        lp_full[lp_full["vintage_year"].notna() & lp_full["dpi"].notna() & lp_full["tvpi"].notna()]
        .groupby("vintage_year")
        .agg(med_dpi=("dpi","median"), med_tvpi=("tvpi","median"), n=("fund_name","count"))
        .reset_index()
    )
    return vy, pr


def render_insights(df_master: pd.DataFrame, bench: pd.DataFrame, incomplete_rows: pd.DataFrame = None):
    # A. LOADING ANIMATION
    loader_slot = st.empty()
    loader_slot.markdown("""
    <div class="ins-loader">
      <div class="ins-loader-mark">D</div>
      <div>
        <div class="ins-loader-text">Analysing fund records</div>
        <div class="ins-loader-dots">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    # B. DATA PREPARATION
    # ── Base slices ──────────────────────────────────────────
    lp_full = df_master[df_master["data_source_type"] == "LP-Disclosed"].copy()
    
    lp_irr = df_master[
        (df_master["data_source_type"] == "LP-Disclosed") &
        (df_master["irr_meaningful"] == True)
    ].copy()
    lp_irr = lp_irr[lp_irr["net_irr"].notna() & (lp_irr["net_irr"].abs() < 2.0)]
    
    # ── Hero stats ────────────────────────────────────────────
    total_funds = len(df_master)
    
    post17 = lp_full[lp_full["vintage_year"].notna() & (lp_full["vintage_year"] >= 2017) & lp_full["dpi"].notna()]
    drought_pct = int((post17["dpi"] < 0.5).mean() * 100) if len(post17) > 0 else 100
    
    top_dpi_df = lp_full[lp_full["dpi"].notna()].sort_values("dpi", ascending=False)
    if not top_dpi_df.empty:
        top_dpi_val  = float(top_dpi_df.iloc[0]["dpi"])
        top_dpi_fund = str(top_dpi_df.iloc[0].get("fund_name", ""))
        top_dpi_gp   = str(top_dpi_df.iloc[0].get("canonical_gp", ""))
    else:
        top_dpi_val, top_dpi_fund, top_dpi_gp = 0.0, "", ""
    
    A16Z_DRAG = 4.4
    
    # ── Section 1: DPI by vintage ────────────────────────────
    _df_hash = str(len(df_master)) + str(df_master.columns.tolist())
    _vy_cached, _pr_cached = _precompute_insights(_df_hash, df_master, bench)
    
    vy = _vy_cached[
        (_vy_cached["vintage_year"] >= 2007) &
        (_vy_cached["vintage_year"] <= 2022) &
        (_vy_cached["n"] >= 3)
    ].sort_values("vintage_year").copy()
    vy["vintage_year"] = vy["vintage_year"].astype(int)
    
    # ── Section 1: Vintage pills ───────────
    PILL_YEARS = [2010, 2011, 2012, 2014, 2015, 2017, 2019, 2021]
    pill_data = {}
    for yr in PILL_YEARS:
        rows = lp_full[lp_full["vintage_year"] == yr]["dpi"].dropna()
        pill_data[yr] = float(rows.median()) if len(rows) >= 2 else None
    
    # ── Section 2: DPI Leaderboard ──
    leaders = (
        lp_full[lp_full["dpi"].notna() & (lp_full["dpi"] > 0)]
        .sort_values("dpi", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    max_leader_dpi = float(leaders["dpi"].max()) if not leaders.empty else 1.0
    
    # ── Section 3: Paper vs Real ────────────────
    pr = _pr_cached[
        (_pr_cached["vintage_year"] >= 2007) &
        (_pr_cached["vintage_year"] <= 2022) &
        (_pr_cached["n"] >= 2)
    ].sort_values("vintage_year").copy()
    pr["vintage_year"] = pr["vintage_year"].astype(int)
    pr["unrealized"] = (pr["med_tvpi"] - pr["med_dpi"]).clip(lower=0)
    
    # ── Section 3: Realization rate bars ───
    REAL_YEARS = [2010, 2012, 2014, 2016, 2018, 2020, 2022]
    real_rates = {}
    for yr in REAL_YEARS:
        rows = lp_full[lp_full["vintage_year"] == yr]["dpi"].dropna()
        if len(rows) >= 2:
            real_rates[yr] = min(int(float(rows.median()) * 100), 100)
        else:
            real_rates[yr] = None
    
    # ── Section 4: a16z Fee Drag ─────────────────
    A16Z_FUNDS = [
        {"fund": "AH Fund I",  "vintage": 2009, "size_m":  300, "gross_tvpi":  9.3, "net_tvpi":  6.9, "net_dpi": 6.0},
        {"fund": "AH Fund II", "vintage": 2010, "size_m":  656, "gross_tvpi":  4.9, "net_tvpi":  3.7, "net_dpi": 3.5},
        {"fund": "AH Annex",   "vintage": 2011, "size_m":  204, "gross_tvpi":  7.2, "net_tvpi":  5.4, "net_dpi": 5.1},
        {"fund": "AH Fund III","vintage": 2012, "size_m":  997, "gross_tvpi": 15.7, "net_tvpi": 11.3, "net_dpi": 5.5},
        {"fund": "AH Fund IV", "vintage": 2014, "size_m": 1173, "gross_tvpi":  5.5, "net_tvpi":  4.1, "net_dpi": 3.0},
        {"fund": "AH Fund V",  "vintage": 2017, "size_m": 1189, "gross_tvpi":  4.0, "net_tvpi":  3.1, "net_dpi": 0.3},
    ]
    
    # ── Section 5: Manager variance ──────
    var_df = df_master[
        (df_master["source"].astype(str).str.upper() == "UTIMCO") &
        df_master["net_irr"].notna() &
        df_master["canonical_gp"].notna()
    ].copy()
    gp_var = (
        var_df.groupby("canonical_gp")
        .agg(min_irr=("net_irr","min"), max_irr=("net_irr","max"), n=("fund_name","count"))
        .reset_index()
    )
    gp_var = (
        gp_var[gp_var["n"] >= 2]
        .sort_values("max_irr", ascending=False)
        .head(7)
        .reset_index(drop=True)
    )
    gp_irr_axis_min = float(gp_var["min_irr"].min()) if not gp_var.empty else -0.05
    gp_irr_axis_max = float(gp_var["max_irr"].max()) if not gp_var.empty else 0.55
    gp_irr_axis_span = max(gp_irr_axis_max - gp_irr_axis_min, 0.01)
    
    # C. CLEAR LOADER
    loader_slot.empty()
    
    # D. PAGE HERO
    _render_html("""
    <div class="ins-eyebrow">Insights — LP Disclosure Data</div>
    <div class="ins-headline">
      Most VC funds haven't returned your money yet.<br>
      <em>Here's who has.</em>
    </div>
    <div class="ins-deck">
      We analysed public LP disclosures from CalPERS, CalSTRS, WSIB, UC Regents, UTIMCO, 
      and others — plus select market intelligence — to surface the funds that actually 
      returned cash. DPI first. Everything else is context.
    </div>
    """)
    
    # E. HERO STAT ROW
    top_dpi_short = (top_dpi_fund[:28] + "…") if len(top_dpi_fund) > 28 else top_dpi_fund
    
    _render_html(f"""
    <div class="ins-stat-row ins-section">
      <div class="ins-stat-cell">
        <div class="ins-stat-label">Funds Indexed</div>
        <div class="ins-stat-value" id="st-funds">{total_funds:,}</div>
        <div class="ins-stat-sub">Across 9 institutional LP sources</div>
      </div>
      <div class="ins-stat-cell">
        <div class="ins-stat-label">Post-2017 Funds with DPI &lt; 0.5×</div>
        <div class="ins-stat-value" id="st-drought">{drought_pct}%</div>
        <div class="ins-stat-sub">Every post-2017 fund is cash-light</div>
      </div>
      <div class="ins-stat-cell">
        <div class="ins-stat-label">Highest LP-Disclosed DPI</div>
        <div class="ins-stat-value" id="st-dpi">{top_dpi_val:.2f}×</div>
        <div class="ins-stat-sub">{html.escape(top_dpi_short)}</div>
      </div>
      <div class="ins-stat-cell accent">
        <div class="ins-stat-label">a16z Fund III Fee Drag</div>
        <div class="ins-stat-value" id="st-drag">{A16Z_DRAG}×</div>
        <div class="ins-stat-sub">Gross 15.7× → Net 11.3× on $997M</div>
      </div>
    </div>
    """)
    
    _render_html("""
    <script>
    (function() {
      function animateCounter(id, end, decimals, suffix, duration) {
        var el = document.getElementById(id);
        if (!el) return;
        var start = 0, startTime = null;
        function step(ts) {
          if (!startTime) startTime = ts;
          var progress = Math.min((ts - startTime) / duration, 1);
          var ease = 1 - Math.pow(1 - progress, 3);
          var val = start + (end - start) * ease;
          el.textContent = (decimals > 0 ? val.toFixed(decimals) : Math.round(val).toLocaleString()) + suffix;
          if (progress < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      }
      setTimeout(function() {
        animateCounter('st-funds',  """ + str(total_funds) + """, 0, '+', 1200);
        animateCounter('st-drought',""" + str(drought_pct) + """, 0, '%', 900);
        animateCounter('st-dpi',    """ + str(round(top_dpi_val, 2)) + """, 2, '×', 1400);
        animateCounter('st-drag',   """ + str(A16Z_DRAG) + """, 1, '×', 1000);
      }, 120);
    })();
    </script>
    """)
    
    # F. SECTION 1 — DPI BY VINTAGE
    _render_html("""
    <div class="ins-section ins-section-rule" style="margin-top: 56px;">
      <div class="ins-section-num">01 / DPI by Vintage</div>
      <div class="ins-section-line"></div>
    </div>
    <div class="ins-chart-headline">
      The DPI drought is real — and it starts exactly at <em>2017</em>
    </div>
    <div class="ins-chart-standfirst">
      Median DPI by vintage tells the clearest story in this dataset. Pre-2015 funds have broadly 
      returned capital. After 2016, the median fund has returned less than 20 cents per dollar 
      invested — not because they're bad funds, but because distributions haven't come. 
      IRR can look strong while DPI flatlines.
    </div>
    """)
    
    bar_colors = []
    for v in vy["vintage_year"]:
        if v <= 2013:
            bar_colors.append("#E8571F")
        elif v <= 2016:
            bar_colors.append("#D97706")
        else:
            bar_colors.append("#CBD5E1")
    
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=vy["vintage_year"].astype(str),
        y=vy["med_dpi"].round(2),
        name="Median DPI",
        marker_color=bar_colors,
        marker_line_width=0,
        width=0.55,
        hovertemplate="<b>Vintage %{x}</b><br>Median DPI: %{y:.2f}×<br><i>n=%{customdata} funds</i><extra></extra>",
        customdata=vy["n"],
    ))
    fig1.add_trace(go.Scatter(
        x=vy["vintage_year"].astype(str),
        y=vy["med_tvpi"].round(2),
        name="Median TVPI",
        mode="lines+markers",
        line=dict(color="#CBD5E1", width=2, dash="dot"),
        marker=dict(size=5, color="#CBD5E1"),
        hovertemplate="Vintage %{x}<br>Median TVPI: %{y:.2f}×<extra></extra>",
    ))
    fig1.update_layout(
        height=240,
        plot_bgcolor="#FAFAFA", paper_bgcolor="#FAFAFA",
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(
            orientation="h", y=1.12, x=1, xanchor="right",
            font=dict(family="DM Mono, monospace", size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(gridcolor="#F3F4F6", title="", tickfont=dict(family="DM Mono, monospace", size=10), fixedrange=True),
        yaxis=dict(gridcolor="#F3F4F6", title="", ticksuffix="×", tickfont=dict(family="DM Mono, monospace", size=10), fixedrange=True),
        bargap=0.25,
    )
    st.markdown('<div class="ins-chart-frame">', unsafe_allow_html=True)
    st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)
    
    _render_html("""
    <div class="ins-takeaway">
      <strong>What this means for LPs:</strong> TVPI looks healthier than it is. The 2017–2021 
      vintage cohort has high paper marks but almost no cash returned. IRR figures for these 
      vintages are still directionally meaningful, but DPI is the only number that tells you 
      whether an LP can actually redeploy capital.
    </div>
    <div class="ins-footnote">Source: LP-disclosed data (CalPERS, CalSTRS, WSIB, UC Regents, UTIMCO, others). 
    Bars = median DPI per vintage (n ≥ 3 funds). Line = median TVPI. Orange = pre-2014 · Amber = 2014–2016 · Gray = post-2016.</div>
    """)
    
    # Vintage pills
    def pill_class(dpi_val):
        if dpi_val is None: return "p-none"
        if dpi_val >= 2.0:  return "p-strong"
        if dpi_val >= 1.0:  return "p-mid"
        if dpi_val >= 0.1:  return "p-low"
        return "p-none"
    
    def pill_label(dpi_val):
        if dpi_val is None: return "No data"
        if dpi_val >= 2.0:  return "Realized"
        if dpi_val >= 1.0:  return "Returning"
        if dpi_val >= 0.1:  return "Early"
        return "Cash-light"
    
    pills_html = '<div class="ins-pill-grid">'
    for yr in PILL_YEARS:
        v = pill_data.get(yr)
        cls = pill_class(v)
        lbl = pill_label(v)
        val_str = f"{v:.2f}×" if v is not None else "—"
        pills_html += f"""
        <div class="ins-pill {cls}">
          <div class="ins-pill-year">{yr}</div>
          <div class="ins-pill-val">{val_str}</div>
          <div class="ins-pill-label">{lbl}</div>
        </div>"""
    pills_html += '</div>'
    
    _render_html(f"""
    <div style="margin-top: 36px;">
      <div class="ins-chart-headline" style="font-size:18px; margin-bottom:6px;">
        How each vintage looks at a glance
      </div>
      <div class="ins-chart-standfirst" style="margin-bottom:14px;">
        Median DPI per vintage · colour = realization level · LP-disclosed only
      </div>
      {pills_html}
      <div class="ins-footnote">Orange = 2.0×+ DPI · Green = 1.0–2.0× · Amber = 0.1–1.0× · Gray = &lt;0.1× or insufficient data</div>
    </div>
    """)
    
    # G. SECTION 2 — DPI LEADERBOARD
    _render_html("""
    <div class="ins-section ins-section-rule" style="margin-top: 64px;">
      <div class="ins-section-num">02 / Cash Return Leaders</div>
      <div class="ins-section-line"></div>
    </div>
    <div class="ins-chart-headline">
      The funds that actually returned the money. <em>LP-disclosed only.</em>
    </div>
    <div class="ins-chart-standfirst">
      Ranked by DPI — capital returned as a multiple of what was invested. These are not marks. 
      They are wire transfers. Every number here came from a public pension disclosure filed under FOIA.
    </div>
    """)
    
    lb_rows_html = ""
    for i, row in leaders.iterrows():
        fund_name  = html.escape(str(row.get("fund_name", ""))[:40])
        gp         = html.escape(str(row.get("canonical_gp", ""))[:30])
        vintage    = "—" if pd.isna(row.get("vintage_year")) else str(int(float(row["vintage_year"])))
        dpi_val    = float(row.get("dpi")) if pd.notna(row.get("dpi")) else None
        tvpi_val   = float(row.get("tvpi")) if pd.notna(row.get("tvpi")) else None
        irr_val    = float(row.get("net_irr")) if pd.notna(row.get("net_irr")) else None
        
        dpi_str    = f"{dpi_val:.2f}×"  if dpi_val is not None  else "—"
        tvpi_str   = f"{tvpi_val:.2f}×" if tvpi_val is not None else "—"
        irr_str    = f"{irr_val*100:.1f}%" if irr_val is not None else "—"
        irr_cls    = "green-col" if irr_val is not None and irr_val > 0.15 else "mono"
        bar_pct    = int((dpi_val / max_leader_dpi) * 100) if dpi_val is not None and max_leader_dpi > 0 else 0
        
        lb_rows_html += f"""
        <tr>
          <td class="num">{str(i+1).zfill(2)}</td>
          <td>
            <div class="ins-fund-name">{fund_name}</div>
            <div class="ins-fund-gp">{gp} · {vintage}</div>
            <div class="ins-bar-wrap"><div class="ins-bar-fill" style="width:{bar_pct}%"></div></div>
          </td>
          <td class="mono">{tvpi_str}</td>
          <td class="dpi-col">{dpi_str}</td>
          <td class="{irr_cls}">{irr_str}</td>
        </tr>"""
    
    _render_html(f"""
    <div class="ins-chart-frame">
      <table class="ins-lb">
        <thead>
          <tr>
            <th style="width:32px">#</th>
            <th>Fund / Manager</th>
            <th class="r">TVPI</th>
            <th class="r" style="color:#E8571F">DPI ▲</th>
            <th class="r">Net IRR</th>
          </tr>
        </thead>
        <tbody>{lb_rows_html}</tbody>
      </table>
    </div>
    """)
    
    top1 = leaders.iloc[0] if len(leaders) >= 1 else None
    top2 = leaders.iloc[1] if len(leaders) >= 2 else None
    
    if top1 is not None and top2 is not None:
        t1_name = html.escape(str(top1.get("canonical_gp",""))[:30])
        t1_dpi  = f"{float(top1['dpi']):.2f}×"
        t2_name = html.escape(str(top2.get("canonical_gp",""))[:30])
        t2_dpi  = f"{float(top2['dpi']):.2f}×"
        _render_html(f"""
        <div class="ins-callouts">
          <div class="ins-callout featured">
            <div class="ins-callout-eye">Dark horse of the dataset</div>
            <div class="ins-callout-num">{t2_dpi}</div>
            <div class="ins-callout-body">
              {t2_name} DPI — a smaller, less-visible manager that surfaces as a top cash returner. 
              Public LP records consistently surface leaders that brand-based narratives miss entirely.
            </div>
          </div>
          <div class="ins-callout">
            <div class="ins-callout-eye">The realization pattern</div>
            <div class="ins-callout-num" style="font-size:24px;color:#374151;">Pre-2015 vintage</div>
            <div class="ins-callout-body">
              Every fund in the top 10 is a pre-2015 vintage. The top cohort is concentrated where 
              realization cycles have fully played out — not where brand reputation is strongest.
            </div>
          </div>
        </div>
        """)
    
    _render_html('<div class="ins-footnote" style="margin-top:8px;">Source: LP-disclosed institutional data only (FOIA). DPI = capital_distributed / capital_contributed as reported by LP. Market intelligence funds excluded.</div>')
    
    # H. SECTION 3 — PAPER vs REAL
    _render_html("""
    <div class="ins-section ins-section-rule" style="margin-top: 64px;">
      <div class="ins-section-num">03 / Paper vs Cash</div>
      <div class="ins-section-line"></div>
    </div>
    <div class="ins-chart-headline">
      The gap between paper value and actual cash<br>has never been <em>wider than right now</em>
    </div>
    <div class="ins-chart-standfirst">
      TVPI measures the total value of a fund — distributions plus remaining NAV. DPI measures only 
      what has been wired to LPs. The gap between them is unrealized. In 2020–2022 vintages, 
      that gap is nearly everything.
    </div>
    """)
    
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=pr["vintage_year"].astype(str),
        y=pr["med_dpi"].round(2),
        name="DPI (Cash Returned)",
        marker_color="#E8571F",
        marker_line_width=0,
        hovertemplate="<b>Vintage %{x}</b><br>Median DPI: %{y:.2f}×<extra></extra>",
    ))
    fig3.add_trace(go.Bar(
        x=pr["vintage_year"].astype(str),
        y=pr["unrealized"].round(2),
        name="Unrealized (TVPI − DPI)",
        marker_color="#E5E7EB",
        marker_line_width=0,
        hovertemplate="Vintage %{x}<br>Unrealized: %{y:.2f}×<extra></extra>",
    ))
    fig3.update_layout(
        barmode="stack", height=260,
        plot_bgcolor="#FAFAFA", paper_bgcolor="#FAFAFA",
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(
            orientation="h", y=1.12, x=1, xanchor="right",
            font=dict(family="DM Mono, monospace", size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(gridcolor="#F3F4F6", title="", tickfont=dict(family="DM Mono, monospace", size=10), fixedrange=True),
        yaxis=dict(gridcolor="#F3F4F6", title="", ticksuffix="×", tickfont=dict(family="DM Mono, monospace", size=10), fixedrange=True),
    )
    st.markdown('<div class="ins-chart-frame">', unsafe_allow_html=True)
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)
    
    _render_html("""
    <div class="ins-takeaway">
      <strong>The key tension:</strong> Strong TVPI without DPI means LPs are sitting on paper gains 
      that depend on exits that haven't happened — and may not at current marks. 
      Post-2020 vintages show median TVPI above 1.0× with DPI near zero. Those marks will be 
      tested when funds need to actually return capital.
    </div>
    <div class="ins-footnote">Bars show dataset median. TVPI includes both distributed capital (DPI) and remaining NAV at LP-reported mark.</div>
    """)
    
    real_bar_rows = ""
    for yr in REAL_YEARS:
        rate = real_rates.get(yr)
        if rate is None:
            continue
        if rate >= 80:
            fill_color = "#E8571F"
            pct_color  = "#E8571F"
        elif rate >= 40:
            fill_color = "#D97706"
            pct_color  = "#D97706"
        else:
            fill_color = "#E5E7EB"
            pct_color  = "#9CA3AF"
        
        real_bar_rows += f"""
        <div class="ins-real-row">
          <div class="ins-real-year">{yr}</div>
          <div class="ins-real-track">
            <div class="ins-real-fill" style="width:{rate}%; background:{fill_color}"></div>
          </div>
          <div class="ins-real-pct" style="color:{pct_color}">{rate}%</div>
        </div>"""
    
    _render_html(f"""
    <div style="margin-top: 36px;">
      <div class="ins-chart-headline" style="font-size:18px; margin-bottom:6px;">
        What percentage of capital has actually been returned?
      </div>
      <div class="ins-chart-standfirst" style="margin-bottom:16px;">
        Realization rate = median DPI per vintage expressed as % (1.0× DPI = 100%). Capped at 100%.
      </div>
      <div class="ins-chart-frame" style="padding: 18px 24px;">
        <div class="ins-real-row" style="padding-bottom:8px; border-bottom:2px solid #111827; margin-bottom:6px;">
          <div class="ins-footnote" style="margin:0">Vintage</div>
          <div class="ins-footnote" style="margin:0">Realization Rate</div>
          <div class="ins-footnote" style="margin:0;text-align:right">%</div>
        </div>
        {real_bar_rows}
      </div>
      <div class="ins-footnote">LP-disclosed funds · Orange = strong realization · Gray = minimal distributions yet</div>
    </div>
    """)
    
    # I. SECTION 4 — FEE DRAG
    _render_html("""
    <div class="ins-section ins-section-rule" style="margin-top: 64px;">
      <div class="ins-section-num">04 / The Gross-Net Gap</div>
      <div class="ins-section-line"></div>
    </div>
    <div class="ins-chart-headline">
      a16z Fund III: 15.7× gross became <em>11.3× net</em>.<br>
      That's ~$4.4B transferred from LPs to the GP.
    </div>
    <div class="ins-chart-standfirst">
      a16z is the only firm in this dataset with both gross and net metrics disclosed. The gap is 
      not unusual — it is what standard 2/20 economics look like when a fund performs well. 
      But it is rarely shown this concretely. Fees and carry are highest in absolute dollar terms 
      precisely when performance is strongest.
    </div>
    """)
    
    gross_vals = [f["gross_tvpi"] for f in A16Z_FUNDS]
    net_vals   = [f["net_tvpi"]   for f in A16Z_FUNDS]
    dpi_vals   = [f["net_dpi"]    for f in A16Z_FUNDS]
    fund_labels= [f"{f['fund']}\n{f['vintage']} · ${f['size_m']:,}M" for f in A16Z_FUNDS]
    
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(
        name="Gross TVPI",
        x=fund_labels, y=gross_vals,
        marker_color="#E5E7EB", marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Gross TVPI: %{y:.1f}×<extra></extra>",
    ))
    fig4.add_trace(go.Bar(
        name="Net TVPI",
        x=fund_labels, y=net_vals,
        marker_color="#E8571F", marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Net TVPI: %{y:.1f}×<extra></extra>",
    ))
    fig4.add_trace(go.Bar(
        name="Net DPI",
        x=fund_labels, y=dpi_vals,
        marker_color="#2C3E50", marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Net DPI: %{y:.1f}×<extra></extra>",
    ))
    fig4.update_layout(
        barmode="group", height=260,
        plot_bgcolor="#FAFAFA", paper_bgcolor="#FAFAFA",
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(
            orientation="h", y=1.12, x=1, xanchor="right",
            font=dict(family="DM Mono, monospace", size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(gridcolor="#F3F4F6", title="", tickfont=dict(family="DM Mono, monospace", size=9), fixedrange=True),
        yaxis=dict(gridcolor="#F3F4F6", title="", ticksuffix="×", tickfont=dict(family="DM Mono, monospace", size=10), fixedrange=True),
        bargap=0.2, bargroupgap=0.05,
    )
    st.markdown('<div class="ins-chart-frame">', unsafe_allow_html=True)
    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)
    
    _render_html("""
    <div class="ins-takeaway">
      <strong>The AH Fund V story is the one LPs should study:</strong> Net DPI of only 0.3× despite 
      Net TVPI of 3.1×, nearly a decade in. LPs have received less than a third of their committed 
      capital in cash. High IRR and high TVPI can coexist with genuine LP frustration when 
      distributions don't materialise.
    </div>
    <div class="ins-footnote">Source: a16z firm disclosure (Sep 2025). Gray = Gross TVPI · Orange = Net TVPI · Dark = Net DPI. 
    Difference between gray and orange = fees + carry transferred from LP to GP. a16z is the only firm in this dataset with both gross and net disclosed.</div>
    """)
    
    # J. SECTION 5 — MANAGER VARIANCE
    _render_html("""
    <div class="ins-section ins-section-rule" style="margin-top: 64px;">
      <div class="ins-section-num">05 / Within-Manager Variance</div>
      <div class="ins-section-line"></div>
    </div>
    <div class="ins-chart-headline">
      The brand is consistent. <em>The returns aren't.</em>
    </div>
    <div class="ins-chart-standfirst">
      Same manager, same team, wildly different outcomes across vintages. Vintage timing — and the 
      macro cycle a fund invests through — can matter as much as manager quality. The range between 
      a manager's best and worst fund is often larger than the spread between top and median managers.
    </div>
    """)
    
    if not gp_var.empty:
        mgr_rows_html = ""
        for _, r in gp_var.iterrows():
            gp_name  = html.escape(str(r["canonical_gp"])[:28])
            min_irr  = float(r["min_irr"])
            max_irr  = float(r["max_irr"])
            irr_span = gp_irr_axis_span
            
            left_pct  = ((min_irr - gp_irr_axis_min) / irr_span * 100)
            right_pct = ((max_irr - gp_irr_axis_min) / irr_span * 100)
            fill_w    = right_pct - left_pct
            
            min_str = f"{min_irr*100:.1f}%"
            max_str = f"{max_irr*100:.1f}%"
            
            mgr_rows_html += f"""
            <div class="ins-mgr-row">
              <div class="ins-mgr-name">{gp_name}</div>
              <div class="ins-mgr-range">
                <div class="ins-mgr-track"></div>
                <div class="ins-mgr-fill" style="left:{left_pct:.1f}%;width:{fill_w:.1f}%"></div>
                <div class="ins-mgr-dot" style="left:calc({left_pct:.1f}% - 4px);background:#9CA3AF"></div>
                <div class="ins-mgr-dot" style="left:calc({right_pct:.1f}% - 4px);background:#E8571F"></div>
              </div>
              <div class="ins-mgr-val max">{max_str}</div>
              <div class="ins-mgr-val min">{min_str}</div>
            </div>"""
        
        _render_html(f"""
        <div class="ins-chart-frame" style="padding: 20px 28px;">
          <div class="ins-mgr-row header">
            <div class="ins-mgr-hdr">Manager</div>
            <div class="ins-mgr-hdr">Net IRR Range — best fund → worst fund</div>
            <div class="ins-mgr-hdr r">Best</div>
            <div class="ins-mgr-hdr r">Worst</div>
          </div>
          {mgr_rows_html}
        </div>
        """)
        
        _render_html("""
        <div class="ins-takeaway">
          <strong>Vintage timing is a first-order variable.</strong> USV's range spans from 52% IRR 
          (2012 vintage — caught the Coinbase cycle) to single-digit IRR on later funds. This isn't 
          a failure of the manager. It is the structural reality of VC. Picking the manager is one 
          decision. Picking which fund cycle to back is another entirely.
        </div>
        <div class="ins-footnote">Source: UTIMCO LP disclosure (2023). Net IRR stored as decimal in dataset. 
        Range = min to max net IRR across all funds with n ≥ 2 from that manager in UTIMCO records.</div>
        """)
        
        _render_html("""
        <div class="ins-callouts" style="margin-top: 28px;">
          <div class="ins-callout">
            <div class="ins-callout-eye">The China risk signal</div>
            <div class="ins-callout-num" style="font-size:22px;color:#374151;">Same GP.<br>Different macro.</div>
            <div class="ins-callout-body">HongShan 2010 vintage shows strong realized outcomes. 
            HongShan 2020 vintage sits near sub-1× with weaker IRR. Same platform, same team — 
            but the regulatory and exit environment shifted entirely between those fund cycles.</div>
          </div>
          <div class="ins-callout">
            <div class="ins-callout-eye">Selection bias in market intelligence</div>
            <div class="ins-callout-num" style="font-size:22px;color:#374151;">Above Q1.<br>Always?</div>
            <div class="ins-callout-body">Market intelligence funds (a16z, Founders Fund, Social Capital) 
            cluster above the Cambridge Associates Q1 line in this dataset. That may reflect genuine 
            outperformance — or it may reflect that only strong numbers get circulated and forwarded. 
            Treat as directional, not verified.</div>
          </div>
        </div>
        """)
    else:
        st.info("Insufficient UTIMCO data for manager variance analysis.")



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


def render_audit(df_lp: pd.DataFrame, df_mi: pd.DataFrame, df_master: pd.DataFrame):
    render_page_header("⚙ AUDIT", "INTERNAL DATA VALIDATION AND PIPELINE HEALTH")
    
    # 1. Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total LP Funds", len(df_lp))
    with m2:
        st.metric("Total MI Funds", len(df_mi))
    with m3:
        # Derived irr_meaningful
        meaningful_count = (
            df_master["vintage_year"].notna() & 
            (df_master["vintage_year"] <= 2020) & 
            df_master["net_irr"].notna()
        ).sum()
        st.metric("Meaningful IRR", meaningful_count)
    with m4:
        st.metric("Sources", df_lp["source"].nunique())

    # 2. DPI Leaderboard
    st.markdown('<div class="section-label">TOP 20 LP-DISCLOSED BY DPI</div>', unsafe_allow_html=True)
    top_20 = df_lp.nlargest(20, "dpi")[["fund_name", "vintage_year", "dpi", "tvpi", "source"]]
    st.dataframe(top_20, use_container_width=True)

    # 3. Dynamic Validation Checks
    st.markdown('<div class="section-label">ACTIVE ALERTS</div>', unsafe_allow_html=True)
    
    # FAIL Check: Insight Card 01 - DPI Drought (2017+ < 0.5x)
    drought_fail = df_master[(df_master['vintage_year'] >= 2017) & (df_master['dpi'] >= 0.5)]
    if not drought_fail.empty:
        st.error(f"FAIL: DPI Drought Headline is incorrect. {len(drought_fail)} funds from 2017+ vintages have DPI ≥ 0.5x.")
        st.dataframe(drought_fail[['fund_name', 'vintage_year', 'dpi', 'source']])

    # FAIL Check: Dark Horse Missing
    ia_exists = df_master['fund_name'].str.contains("IA Venture Strategies", case=False, na=False).any()
    if not ia_exists:
        st.error("FAIL: 'IA Venture Strategies' (Card 08 Dark Horse) is missing from vc_fund_master.csv. The card will link to a non-existent firm.")

    # FAIL Check: Impossible DPI
    bad_dpi = df_lp[df_lp['dpi'] > df_lp['tvpi'] + 0.05]
    if not bad_dpi.empty:
        st.error(f"FAIL: {len(bad_dpi)} rows found where DPI > TVPI (calculation error).")
        st.dataframe(bad_dpi[['fund_name', 'dpi', 'tvpi', 'source']])

    # WARN Check: Vintage Placeholder
    placeholders = df_lp[(df_lp['tvpi'] == 1.0) & (df_lp['vintage_year'] <= 2018)]
    if not placeholders.empty:
        st.warning(f"WARN: {len(placeholders)} funds from 2018 or earlier still show TVPI = 1.0. Suspicious lack of marks.")

    # WARN Check: Duplicate Dedup Key
    dup_key = ["fund_name", "vintage_year", "source", "reporting_period"]
    dups = df_lp[df_lp.duplicated(subset=dup_key, keep=False)]
    if not dups.empty:
        st.warning(f"WARN: {len(dups)} redundant records found in unified_funds.csv (dedup failed).")

    if drought_fail.empty and bad_dpi.empty and dups.empty and ia_exists:
        st.success("No critical validation failures detected in the current session.")



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
        <div style="text-align:center; padding:1.5rem 0; color:#9CA3AF; font-size:10px; font-family:'IBM Plex Mono',monospace; opacity:0.6;">
            v0.9.5-PROD · LAYOUT-HOTFIX_03 · {0}
        </div>
        """.format(datetime.now().strftime("%H:%M:%S"))
    )


def main():
    st.sidebar.success("✅ Ver: 0.9.5-PROD ACTIVE")
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

    SHOW_AUDIT = os.environ.get('SHOW_AUDIT', '0') == '1'
    nav_options = ["ABOUT", "INSIGHTS", "TOP FIRMS", "FUND DATABASE", "SOURCES"]
    if SHOW_AUDIT:
        nav_options.append("⚙ AUDIT")

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
    elif active_page == "⚙ AUDIT":
        try:
            df_unified = load_unified()
            df_master = load_master_full()
            df_market_intel = load_market_intel()
        except Exception as exc:
            st.error("Failed loading audit datasets: {0}".format(exc))
            render_footer()
            return
        render_audit(df_unified, df_market_intel, df_master)

    render_footer()


if __name__ == "__main__":
    main()
