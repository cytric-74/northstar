from __future__ import annotations

import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import hashlib
from datetime import datetime
from io import BytesIO
from html import escape
from typing import Any, Iterable
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from app.data_quality import clean_sales_data, dataframe_to_csv_bytes
from app.database import save_analysis_run
from app.kpi_engine import KPI_DEFINITIONS, calculate_kpis
from app.sample_generator import generate_rich_sales_data
from app.sql_analytics import run_predefined_query, run_custom_query, PREDEFINED_QUERIES
from app.trend_analysis import calculate_trends
from app.root_cause import analyze_root_cause
from app.forecasting import generate_forecast
from app.recommendations import generate_recommendations
from app.statistics import (
    profile_dataframe,
    numeric_summary,
    categorical_summary,
    correlation_matrix,
    top_correlations,
    missing_by_column,
    value_counts_frame,
    distribution_reference,
)

st.set_page_config(
    page_title="Northstar · KPI Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

SAMPLE_DATA_PATH = Path("data/raw/sales_data.csv")
try:
    if not SAMPLE_DATA_PATH.exists():
        generate_rich_sales_data(SAMPLE_DATA_PATH)
except Exception:
    pass

NAV = {
    "KPI Dashboard": "◉",
    "Upload & Quality": "⇪",
    "Statistical Studio": "∑",
    "SQL Playground": "⌘",
    "Trends & Root Cause": "⇅",
    "Forecasting": "◇",
    "Recommendations": "✦",
    "Power BI Guide": "▤",
}

NAV_DESC = {
    "KPI Dashboard": "Executive metrics, trends and leaderboards at a glance.",
    "Upload & Quality": "Import a sales CSV and run the cleaning + quality engine.",
    "Statistical Studio": "Upload any CSV for distributions, correlations and outliers.",
    "SQL Playground": "Query your active dataset with live SQLite.",
    "Trends & Root Cause": "Timelines plus automated decline decomposition.",
    "Forecasting": "Project daily sales with moving-average and regression models.",
    "Recommendations": "Prioritised, rule-based business actions.",
    "Power BI Guide": "Rebuild this platform inside Microsoft Power BI.",
}

UPLOAD_SECTIONS = {"Upload & Quality", "Statistical Studio"}


def theme_bundle(light: bool) -> dict[str, Any]:
    if light:
        css_vars = {
            "--bg": "#e9ebe2",
            "--panel": "#f6f8f1",
            "--card": "#ffffff",
            "--card-2": "#f2f4ec",
            "--ink": "#141810",
            "--ink-dim": "#4d5247",
            "--ink-faint": "#7c8274",
            "--border": "rgba(18,22,14,.09)",
            "--border-hi": "rgba(18,22,14,.16)",
            "--accent": "#a8e02a",
            "--accent-soft": "rgba(168,224,42,.16)",
            "--accent-ink": "#161a10",
            "--rail": "#f6f8f1",
            "--rail-ink": "#3a3f34",
            "--shadow": "0 18px 40px rgba(60,66,38,.14)",
            "--good": "#2f9e57",
            "--bad": "#d84a4a",
        }
        plot = {
            "ink": "#232720", "axis": "#525749", "grid": "rgba(18,22,14,.14)",
            "rev": "#6f9e1e", "profit": "#2f6fd6", "pos": "#1f9d63", "neg": "#d64545",
            "total": "#6f9e1e", "band": "rgba(47,111,214,.16)", "surface": "rgba(18,22,14,.02)",
            "categ": ["#3b82c4", "#e0821f", "#1f9d63", "#9d5bd6", "#6f9e1e"],
            "div": [[0.0, "#d64545"], [0.5, "#e6e8df"], [1.0, "#2f6fd6"]],
        }
    else:
        css_vars = {
            "--bg": "#0d0f0c",
            "--panel": "#151813",
            "--card": "#181b16",
            "--card-2": "#1e221c",
            "--ink": "#f1f4ea",
            "--ink-dim": "#c2c7b6",
            "--ink-faint": "#868c7a",
            "--border": "rgba(255,255,255,.08)",
            "--border-hi": "rgba(201,242,77,.38)",
            "--accent": "#c9f24d",
            "--accent-soft": "rgba(201,242,77,.12)",
            "--accent-ink": "#12140d",
            "--rail": "#12140f",
            "--rail-ink": "#d3d8c7",
            "--shadow": "0 14px 30px rgba(0,0,0,.34)",
            "--good": "#4fd99a",
            "--bad": "#fb7185",
        }
        plot = {
            "ink": "#e2e6d8", "axis": "#aeb3a2", "grid": "rgba(255,255,255,.12)",
            "rev": "#c9f24d", "profit": "#6ea8fe", "pos": "#4fd99a", "neg": "#fb7185",
            "total": "#c9f24d", "band": "rgba(110,168,254,.2)", "surface": "rgba(255,255,255,.022)",
            "categ": ["#6ea8fe", "#f6a54a", "#4fd99a", "#c98bff", "#c9f24d"],
            "div": [[0.0, "#fb7185"], [0.5, "#3f4539"], [1.0, "#6ea8fe"]],
        }
    return {"vars": css_vars, "plot": plot, "light": light}


LIGHT_MODE = bool(st.session_state.get("theme_light", False))
THEME = theme_bundle(LIGHT_MODE)
P = THEME["plot"]
_ROOT_VARS = "".join(f"{k}:{v};" for k, v in THEME["vars"].items())

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');
    :root {{ {_ROOT_VARS} }}

    html, body, [data-testid="stAppViewContainer"] {{
        background:
            radial-gradient(900px 480px at 88% -12%, var(--accent-soft), transparent 55%),
            var(--bg) !important;
        font-family:'Manrope',sans-serif !important;
        color:var(--ink) !important;
    }}
    [data-testid="stHeader"] {{ background:transparent !important; }}
    [data-testid="stMainBlockContainer"] {{ padding:1.6rem 2.4rem 4rem !important; max-width:1560px !important; }}
    h1,h2,h3,h4,h5,h6,p,label,div,button,span {{ font-family:'Manrope',sans-serif !important; }}
    [data-testid="stMain"] p,[data-testid="stMain"] li,[data-testid="stMain"] label,
    [data-testid="stMain"] .stMarkdown {{ color:var(--ink-dim) !important; }}
    h1 {{ font-size:2rem !important; font-weight:800 !important; letter-spacing:-1.4px !important; color:var(--ink) !important; }}
    h2,h3 {{ color:var(--ink) !important; font-weight:750 !important; letter-spacing:-.7px !important; }}
    h3 {{ font-size:1.12rem !important; }}
    a, a:visited {{ color:var(--accent) !important; }}

    [data-testid="stSidebar"] {{
        background:var(--rail) !important;
        border-right:1px solid var(--border) !important;
        min-width:264px !important;
    }}
    [data-testid="stSidebarContent"] {{ padding:1.15rem .95rem !important; }}
    [data-testid="stSidebar"] * {{ color:var(--rail-ink) !important; }}
    .brand {{ display:flex; align-items:center; gap:11px; padding:6px 8px 4px; }}
    .brand-mark {{
        width:38px; height:38px; border-radius:12px; display:grid; place-items:center;
        background:var(--accent); color:var(--accent-ink); font-size:1.15rem; font-weight:800;
        box-shadow:0 6px 18px var(--accent-soft);
    }}
    .brand-name {{ font-size:1.16rem; font-weight:800; letter-spacing:-.6px; color:var(--ink) !important; line-height:1; }}
    .brand-sub {{ font-size:.62rem; letter-spacing:2.4px; text-transform:uppercase; color:var(--ink-faint) !important; margin-top:3px; }}
    .rail-label {{ font-size:.6rem; letter-spacing:1.8px; text-transform:uppercase; color:var(--ink-faint) !important; margin:18px 8px 4px; }}

    [data-testid="stSidebar"] [role="radiogroup"] {{ gap:4px !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label {{
        display:flex !important; align-items:center !important;
        padding:.62rem .8rem !important; border-radius:12px !important; margin:0 !important;
        border:1px solid transparent !important;
        transition:background .18s ease, transform .12s ease, border-color .18s ease; cursor:pointer;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] > label:hover {{ background:var(--card-2) !important; border-color:var(--border) !important; transform:translateX(2px); }}
    [data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {{
        position:absolute !important; width:1px !important; height:1px !important;
        overflow:hidden !important; clip:rect(0 0 0 0) !important; opacity:0 !important;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] > label > div:last-child {{ width:100% !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] label p {{ font-size:.92rem !important; font-weight:600 !important; color:var(--rail-ink) !important; margin:0 !important; letter-spacing:.1px; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {{ background:var(--accent) !important; border-color:var(--accent) !important; box-shadow:0 8px 20px var(--accent-soft); }}
    [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p {{ color:var(--accent-ink) !important; font-weight:750 !important; }}

    .rail-hint {{ margin:10px 4px 0; padding:11px 13px; border-radius:13px; background:var(--card-2); border:1px solid var(--border); }}
    .rail-hint-desc {{ font-size:.76rem; line-height:1.4; color:var(--ink-dim) !important; }}
    .rail-hint-tag {{ display:inline-block; margin-top:9px; font-size:.66rem; font-weight:750; letter-spacing:.3px; padding:4px 9px; border-radius:999px; background:var(--accent); color:var(--accent-ink) !important; }}
    .rail-note {{ margin:9px 6px 0; font-size:.7rem; line-height:1.45; color:var(--ink-faint) !important; }}
    .rail-note b {{ color:var(--rail-ink) !important; }}
    .rail-stat {{ background:var(--card-2); border:1px solid var(--border); border-radius:14px; padding:12px 14px; margin:6px 4px 0; }}
    .rail-stat .rs-top {{ display:flex; justify-content:space-between; align-items:center; }}
    .rail-stat .rs-k {{ font-size:.68rem; color:var(--ink-faint) !important; text-transform:uppercase; letter-spacing:1px; }}
    .rail-stat .rs-v {{ font-size:1.02rem; font-weight:750; color:var(--ink) !important; }}
    .dot {{ width:8px; height:8px; border-radius:50%; display:inline-block; background:var(--good); box-shadow:0 0 0 4px color-mix(in srgb, var(--good) 22%, transparent); animation:pulse 2.4s ease-in-out infinite; }}
    @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.45}} }}

    .topbar {{
        display:flex; align-items:center; justify-content:space-between; gap:16px;
        background:var(--panel); border:1px solid var(--border); border-radius:20px;
        padding:14px 18px; margin-bottom:22px; box-shadow:var(--shadow);
        animation:rise .34s ease-out both;
    }}
    .tb-left {{ display:flex; flex-direction:column; gap:2px; min-width:0; }}
    .tb-eyebrow {{ font-size:.63rem; letter-spacing:2px; text-transform:uppercase; color:var(--accent) !important; font-weight:700; }}
    .tb-title {{ font-size:1.32rem; font-weight:800; letter-spacing:-.7px; color:var(--ink) !important; line-height:1.1; }}
    .tb-right {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; justify-content:flex-end; }}
    .chip {{ display:flex; align-items:center; gap:8px; background:var(--card-2); border:1px solid var(--border); border-radius:999px; padding:7px 13px; white-space:nowrap; }}
    .chip .ck {{ font-size:.6rem; letter-spacing:1px; text-transform:uppercase; color:var(--ink-faint) !important; }}
    .chip .cv {{ font-size:.82rem; font-weight:700; color:var(--ink) !important; }}
    .chip.mono .cv {{ font-family:'JetBrains Mono',monospace !important; }}
    .avatar {{ width:38px; height:38px; border-radius:50%; display:grid; place-items:center; background:var(--accent); color:var(--accent-ink); font-weight:800; font-size:.92rem; }}

    .card {{
        position:relative; background:var(--card); border:1px solid var(--border); border-radius:20px;
        padding:18px 19px; margin-bottom:18px; box-shadow:var(--shadow); overflow:hidden;
        transition:transform .2s cubic-bezier(.2,.75,.3,1), border-color .2s ease;
        animation:rise .34s ease-out both;
    }}
    .card:hover {{ transform:translateY(-3px); border-color:var(--border-hi); }}
    .card.hero {{ background:linear-gradient(150deg, var(--accent) 0%, color-mix(in srgb, var(--accent) 78%, #7fae12) 100%); border-color:transparent; }}
    .card.hero .m-label, .card.hero .m-value, .card.hero .m-ico {{ color:var(--accent-ink) !important; }}
    .card.hero .m-label {{ opacity:.72; }}
    .m-head {{ display:flex; align-items:center; gap:10px; margin-bottom:14px; }}
    .m-ico {{ width:34px; height:34px; border-radius:11px; display:grid; place-items:center; background:var(--accent-soft); color:var(--accent) !important; font-size:1rem; }}
    .card.hero .m-ico {{ background:rgba(18,20,13,.14); }}
    .m-label {{ font-size:.72rem; letter-spacing:.4px; text-transform:uppercase; color:var(--ink-dim) !important; font-weight:600; }}
    .m-value {{ font-size:1.78rem; font-weight:800; letter-spacing:-1.2px; color:var(--ink) !important; line-height:1; }}
    .m-foot {{ display:flex; align-items:center; justify-content:space-between; gap:8px; margin-top:12px; flex-wrap:wrap; }}
    .m-delta {{ display:inline-flex; align-items:center; gap:5px; font-size:.76rem; font-weight:750; padding:3px 9px; border-radius:999px; }}
    .m-delta.up {{ color:var(--good); background:color-mix(in srgb, var(--good) 15%, transparent); }}
    .m-delta.down {{ color:var(--bad); background:color-mix(in srgb, var(--bad) 15%, transparent); }}
    .m-delta.flat {{ color:var(--ink-dim); background:var(--card-2); }}
    .card.hero .m-delta {{ background:rgba(18,20,13,.16); color:var(--accent-ink); }}
    .m-spark {{ width:96px; height:38px; display:block; }}

    .eyebrow {{ font-size:.66rem; letter-spacing:2px; text-transform:uppercase; color:var(--accent) !important; font-weight:700; margin:6px 0 2px; }}

    .panel {{ background:var(--card); border:1px solid var(--border); border-radius:20px; padding:20px 22px; margin-bottom:18px; box-shadow:var(--shadow); }}
    .panel h4 {{ margin:0 0 6px; color:var(--ink) !important; }}
    .list-row {{ display:flex; align-items:center; justify-content:space-between; gap:12px; padding:11px 0; border-bottom:1px solid var(--border); }}
    .list-row:last-child {{ border-bottom:0; }}
    .lr-left {{ display:flex; align-items:center; gap:12px; min-width:0; }}
    .lr-rank {{ width:26px; height:26px; border-radius:8px; display:grid; place-items:center; background:var(--accent-soft); color:var(--accent) !important; font-weight:750; font-size:.78rem; flex:none; }}
    .lr-name {{ font-size:.9rem; font-weight:650; color:var(--ink) !important; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .lr-sub {{ font-size:.72rem; color:var(--ink-faint) !important; }}
    .lr-val {{ font-size:.9rem; font-weight:750; color:var(--ink) !important; font-family:'JetBrains Mono',monospace !important; }}
    .lr-bar {{ height:5px; border-radius:99px; background:var(--accent); margin-top:6px; }}
    .lr-track {{ flex:1; }}

    .badge {{ display:inline-block; font-size:.66rem; font-weight:750; letter-spacing:.4px; padding:3px 9px; border-radius:999px; text-transform:uppercase; }}
    .badge-accent {{ background:var(--accent); color:var(--accent-ink); }}
    .badge-ghost {{ background:var(--card-2); color:var(--ink-dim); border:1px solid var(--border); }}

    .rec {{ background:var(--card); border:1px solid var(--border); border-left:4px solid var(--rec-color); border-radius:16px; padding:18px 20px; margin-bottom:14px; box-shadow:var(--shadow); transition:transform .18s ease; }}
    .rec:hover {{ transform:translateX(4px); }}
    .rec-tags {{ display:flex; align-items:center; gap:8px; margin-bottom:9px; }}
    .rec-pri {{ font-size:.64rem; font-weight:750; letter-spacing:.6px; text-transform:uppercase; color:var(--rec-color) !important; border:1px solid var(--rec-color); padding:2px 8px; border-radius:999px; }}
    .rec-cat {{ font-size:.64rem; letter-spacing:1.2px; text-transform:uppercase; color:var(--ink-faint) !important; }}
    .rec h4 {{ margin:0 0 7px; color:var(--ink) !important; font-size:1rem; }}
    .rec .rec-trig {{ font-size:.82rem; color:var(--ink-dim) !important; margin:0 0 8px; }}
    .rec .rec-desc {{ font-size:.86rem; color:var(--ink) !important; line-height:1.5; margin:0; }}

    div.stButton > button {{
        background:var(--card-2) !important; color:var(--ink) !important; font-weight:700 !important;
        border:1px solid var(--border) !important; border-radius:12px !important; padding:9px 16px !important;
        transition:transform .16s ease, background .16s ease, color .16s ease, box-shadow .16s ease !important; width:100% !important;
    }}
    div.stButton > button:hover {{ background:var(--accent) !important; color:var(--accent-ink) !important; border-color:var(--accent) !important; box-shadow:0 10px 24px var(--accent-soft) !important; transform:translateY(-2px); }}
    div.stButton > button:active {{ transform:scale(.97); }}
    div.stDownloadButton > button {{ background:var(--accent) !important; color:var(--accent-ink) !important; border:0 !important; border-radius:12px !important; font-weight:750 !important; transition:transform .16s ease, box-shadow .16s ease !important; }}
    div.stDownloadButton > button:hover {{ transform:translateY(-2px); box-shadow:0 12px 26px var(--accent-soft) !important; }}

    [data-baseweb="select"] > div, .stTextArea textarea, .stNumberInput input, .stTextInput input {{
        background:var(--card-2) !important; border:1px solid var(--border) !important; border-radius:12px !important; color:var(--ink) !important;
    }}
    [data-baseweb="select"] > div:focus-within, .stTextArea textarea:focus {{ border-color:var(--accent) !important; box-shadow:0 0 0 3px var(--accent-soft) !important; }}
    [data-baseweb="popover"] li:hover {{ background:var(--accent-soft) !important; }}
    [data-testid="stToggle"] {{ align-items:center; }}

    span[data-testid="stIconMaterial"], [data-testid="stIconMaterial"], .material-symbols-rounded, .material-symbols-outlined {{
        font-family:'Material Symbols Rounded','Material Symbols Outlined','Material Symbols Sharp' !important;
        font-weight:normal !important; font-style:normal !important; letter-spacing:normal !important;
        text-transform:none !important; white-space:nowrap !important; direction:ltr !important;
        -webkit-font-feature-settings:'liga' !important; font-feature-settings:'liga' !important;
    }}
    [data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stBaseButton-headerNoPadding"] {{
        background:var(--card-2) !important; border:1px solid var(--border) !important;
        border-radius:999px !important; color:var(--rail-ink) !important; width:auto !important;
        padding:5px 10px !important; box-shadow:var(--shadow) !important;
        transition:background .18s ease, color .18s ease, transform .18s ease !important;
    }}
    [data-testid="stSidebarCollapseButton"] button:hover, [data-testid="stSidebarCollapsedControl"] button:hover {{
        background:var(--accent) !important; color:var(--accent-ink) !important; transform:translateX(-2px);
    }}
    [data-testid="stSidebarCollapsedControl"] button:hover {{ transform:translateX(2px); }}
    [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapsedControl"] [data-testid="stIconMaterial"] {{ color:inherit !important; }}

    [data-testid="stPlotlyChart"] {{
        background:var(--card); border:1px solid var(--border); border-radius:20px; padding:14px 16px 8px;
        box-shadow:var(--shadow);
    }}
    [data-testid="stDataFrame"], [data-testid="stTable"] {{ border:1px solid var(--border) !important; border-radius:16px !important; overflow:hidden; background:var(--card) !important; }}
    [data-testid="stExpander"] {{ border:1px solid var(--border) !important; border-radius:16px !important; background:var(--card) !important; overflow:hidden; }}
    [data-testid="stExpander"] summary {{ color:var(--ink) !important; }}
    [data-testid="stAlert"] {{ border-radius:16px !important; border:1px solid var(--border) !important; }}
    [data-testid="stFileUploaderDropzone"] {{ background:var(--card-2) !important; border:1.6px dashed var(--border-hi) !important; border-radius:16px !important; }}
    .stTabs [data-baseweb="tab-list"] {{ gap:6px; border-bottom:1px solid var(--border); }}
    .stTabs [data-baseweb="tab"] {{ border-radius:10px 10px 0 0; color:var(--ink-dim) !important; }}
    .stTabs [aria-selected="true"] {{ color:var(--ink) !important; }}
    .stTabs [aria-selected="true"]::after {{ background:var(--accent) !important; }}
    code {{ background:var(--card-2) !important; color:var(--accent) !important; border:1px solid var(--border) !important; border-radius:8px !important; padding:2px 6px !important; font-family:'JetBrains Mono',monospace !important; }}
    hr {{ border-color:var(--border) !important; }}

    @keyframes rise {{ from {{ opacity:0; transform:translateY(6px); }} to {{ opacity:1; transform:translateY(0); }} }}
    @media (prefers-reduced-motion: reduce) {{ *,*::before,*::after {{ animation-duration:.01ms !important; transition-duration:.01ms !important; }} }}
    @media (max-width: 900px) {{
        [data-testid="stMainBlockContainer"] {{ padding:1.2rem 1rem 3rem !important; }}
        .topbar {{ flex-direction:column; align-items:flex-start; }}
        .tb-right {{ justify-content:flex-start; }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def format_currency(value: float | None) -> str:
    return "N/A" if value is None or pd.isna(value) else f"${value:,.2f}"


def format_percent(value: float | None) -> str:
    return "N/A" if value is None or pd.isna(value) else f"{value:,.1f}%"


def format_compact(value: float | None, prefix: str = "$") -> str:
    if value is None or pd.isna(value):
        return "N/A"
    magnitude = abs(value)
    if magnitude >= 1e9:
        return f"{prefix}{value / 1e9:.2f}B"
    if magnitude >= 1e6:
        return f"{prefix}{value / 1e6:.2f}M"
    if magnitude >= 1e3:
        return f"{prefix}{value / 1e3:.1f}K"
    return f"{prefix}{value:,.0f}"


def spark_bars(values: Iterable[float], hero: bool = False) -> str:
    clean = [float(v) for v in values if pd.notna(v)]
    if len(clean) < 2:
        return '<svg class="m-spark" viewBox="0 0 96 38"></svg>'
    clean = clean[-14:]
    low, high = min(clean), max(clean)
    spread = (high - low) or 1.0
    gap = 96 / len(clean)
    width = max(gap - 2.6, 2.0)
    accent = "var(--accent-ink)" if hero else "var(--accent)"
    faint = "rgba(18,20,13,.28)" if hero else "var(--card-2)"
    bars = []
    for index, value in enumerate(clean):
        height = 4 + ((value - low) / spread) * 30
        x = index * gap + (gap - width) / 2
        color = accent if index == len(clean) - 1 else faint
        bars.append(
            f'<rect x="{x:.1f}" y="{38 - height:.1f}" width="{width:.1f}" height="{height:.1f}" rx="1.6" fill="{color}"></rect>'
        )
    return f'<svg class="m-spark" viewBox="0 0 96 38" preserveAspectRatio="none" aria-hidden="true">{"".join(bars)}</svg>'


def metric_card(
    title: str,
    value: str,
    icon: str = "◆",
    spark: Iterable[float] | None = None,
    delta: str | None = None,
    direction: str | None = None,
    hero: bool = False,
) -> None:
    dir_class = {"up": "up", "down": "down"}.get(direction or "", "flat")
    arrow = {"up": "▲", "down": "▼"}.get(direction or "", "•")
    spark_html = spark_bars(spark or [], hero=hero)
    delta_html = (
        f'<span class="m-delta {dir_class}">{arrow} {escape(delta)}</span>' if delta else "<span></span>"
    )
    st.markdown(
        f'<div class="card{" hero" if hero else ""}">'
        f'<div class="m-head"><span class="m-ico">{icon}</span>'
        f'<span class="m-label">{escape(title)}</span></div>'
        f'<div class="m-value">{escape(value)}</div>'
        f'<div class="m-foot">{delta_html}{spark_html}</div></div>',
        unsafe_allow_html=True,
    )


def style_chart(fig: go.Figure, height: int = 340, tickprefix: str | None = None, title: str = "",
                x_category: bool = False, y_from_zero: bool = False, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        margin={"l": 10, "r": 18, "t": 50 if title else 20, "b": 62 if legend else 34},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=P["surface"],
        font={"color": P["ink"], "family": "Manrope"},
        title={"text": title, "font": {"size": 15, "color": P["ink"]}, "x": 0.012, "y": 0.98, "yanchor": "top"} if title else None,
        showlegend=legend,
        legend={"orientation": "h", "y": -0.2, "yanchor": "top", "x": 0.5, "xanchor": "center",
                "bgcolor": "rgba(0,0,0,0)", "font": {"size": 12, "color": P["ink"]},
                "itemsizing": "constant"},
        hoverlabel={"bgcolor": THEME["vars"]["--card-2"], "font": {"color": P["ink"], "family": "Manrope"}, "bordercolor": P["grid"]},
    )
    axis_common = {"gridcolor": P["grid"], "zerolinecolor": P["grid"], "linecolor": P["grid"],
                   "tickfont": {"color": P["axis"], "size": 11}, "title": None}
    fig.update_xaxes(**axis_common, **({"type": "category"} if x_category else {}))
    fig.update_yaxes(**axis_common, tickprefix=tickprefix, **({"rangemode": "tozero"} if y_from_zero else {}))
    return fig


@st.cache_data(show_spinner=False)
def weekly_metric_values(data: pd.DataFrame | None, metric: str) -> list[float]:
    if data is None or data.empty or "Date" not in data.columns:
        return []
    frame = data.copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame.dropna(subset=["Date"])
    if frame.empty:
        return []
    weekly = frame.set_index("Date").resample("W")
    if metric == "orders":
        values = weekly["Order_ID"].nunique() if "Order_ID" in frame else weekly.size()
    elif metric == "customers":
        values = weekly["Customer_ID"].nunique() if "Customer_ID" in frame else weekly.size()
    elif metric == "profit_margin":
        revenue = weekly["Revenue"].sum()
        values = weekly["Profit"].sum().div(revenue.where(revenue != 0)).fillna(0) * 100
    else:
        column = "Revenue" if metric in {"revenue", "average_order_value", "growth_rate"} else "Profit"
        values = weekly[column].sum() if column in frame else pd.Series(dtype=float)
        if metric == "average_order_value":
            orders = weekly["Order_ID"].nunique() if "Order_ID" in frame else weekly.size()
            values = values.div(orders.where(orders != 0)).fillna(0)
    return values.tail(14).tolist()


@st.cache_data(show_spinner=False)
def dimension_revenue(data: pd.DataFrame | None, dimension: str) -> pd.DataFrame:
    if data is None or data.empty or dimension not in data.columns or "Revenue" not in data.columns:
        return pd.DataFrame(columns=[dimension, "Revenue"])
    grouped = (
        data.groupby(dimension)["Revenue"].sum().sort_values(ascending=False).reset_index()
    )
    return grouped[grouped[dimension].astype("string").str.lower() != "unknown"]


@st.cache_data(show_spinner=False)
def load_and_prepare_sample_data(path: str):
    raw = pd.read_csv(path)
    cleaned, summary, column_report, actions = clean_sales_data(raw)
    return raw, cleaned, summary, column_report, actions, calculate_kpis(cleaned)


def topbar(title: str, subtitle: str) -> None:
    source = st.session_state.get("source_name") or "no dataset"
    rows = st.session_state.get("cleaned_df")
    row_count = f"{len(rows):,}" if rows is not None else "0"
    now = datetime.now().strftime("%H:%M · %d %b")
    st.markdown(
        f'<div class="topbar"><div class="tb-left">'
        f'<span class="tb-eyebrow">{escape(subtitle)}</span>'
        f'<span class="tb-title">{escape(title)}</span></div>'
        f'<div class="tb-right">'
        f'<span class="chip mono"><span class="ck">Clock</span><span class="cv">{now}</span></span>'
        f'<span class="chip"><span class="ck">Dataset</span><span class="cv">{escape(source)}</span></span>'
        f'<span class="chip"><span class="ck">Rows</span><span class="cv">{row_count}</span></span>'
        f'<span class="avatar">NS</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-mark">◈</div>'
        '<div><div class="brand-name">Northstar</div>'
        '<div class="brand-sub">KPI Intelligence</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="rail-label">Workspace</div>', unsafe_allow_html=True)
    menu = st.radio(
        "Navigation",
        list(NAV.keys()),
        key="navigation",
        format_func=lambda name: f"{NAV[name]}   {name}",
        label_visibility="collapsed",
    )

    upload_pill = "" if menu in UPLOAD_SECTIONS else '<span class="rail-hint-tag">⇪ CSV upload here</span>'
    st.markdown(
        f'<div class="rail-hint"><div class="rail-hint-desc">{escape(NAV_DESC[menu])}</div>'
        f'{upload_pill}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="rail-note">Import a dataset in <b>Upload &amp; Quality</b> (sales) '
                'or <b>Statistical Studio</b> (any CSV). Scroll for all 8 workspaces.</div>',
                unsafe_allow_html=True)

    st.markdown('<div class="rail-label">Session</div>', unsafe_allow_html=True)
    st.toggle("Light interface", key="theme_light", help="Switch between the dark and light appearance.")

    connected = st.session_state.get("active_run_id")
    status_label = "Live" if connected else "Idle"
    src = st.session_state.get("source_name") or "—"
    st.markdown(
        f'<div class="rail-stat"><div class="rs-top"><span class="rs-k">Engine</span>'
        f'<span class="dot"></span></div><div class="rs-v">{status_label}</div></div>'
        f'<div class="rail-stat"><span class="rs-k">Active source</span>'
        f'<div class="rs-v" style="font-size:.86rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{escape(src)}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="rail-label">About</div>', unsafe_allow_html=True)
    st.caption("Northstar v2 · cytric (github.com/cytric-74)")


for key in ["raw_df", "cleaned_df", "quality_summary", "column_report", "kpis"]:
    if key not in st.session_state:
        st.session_state[key] = None
st.session_state.setdefault("actions_log", [])
st.session_state.setdefault("source_name", "")
st.session_state.setdefault("active_run_id", "")
st.session_state.setdefault("uploaded_file_hash", "")
st.session_state.setdefault("stat_df", None)
st.session_state.setdefault("stat_name", "")

if st.session_state["raw_df"] is None and SAMPLE_DATA_PATH.exists():
    try:
        synth_df, cleaned, summary, col_rep, actions, kpi_res = load_and_prepare_sample_data(str(SAMPLE_DATA_PATH))
        st.session_state["raw_df"] = synth_df
        st.session_state["cleaned_df"] = cleaned
        st.session_state["quality_summary"] = summary
        st.session_state["column_report"] = col_rep
        st.session_state["actions_log"] = actions
        st.session_state["kpis"] = kpi_res
        st.session_state["source_name"] = "synthetic_sales_data.csv"
        st.session_state["active_run_id"] = save_analysis_run(cleaned, kpi_res, "synthetic_sales_data.csv")
    except Exception as exc:
        st.sidebar.error(f"Failed to auto-load sample data: {exc}")


if menu == "KPI Dashboard":
    topbar("Executive Overview", "Performance Cockpit")

    kpis = st.session_state["kpis"]
    cleaned_df = st.session_state["cleaned_df"]

    if not kpis:
        st.info("Load a dataset from **Upload & Quality** to populate the cockpit.")
    else:
        rate = kpis["growth_rate"]
        rate_dir = None if rate is None else ("up" if rate >= 0 else "down")
        rate_delta = None if rate is None else f"{abs(rate):.1f}% MoM"
        margin = kpis["profit_margin"]

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Total Revenue", format_compact(kpis["revenue"]), "◒",
                        weekly_metric_values(cleaned_df, "revenue"), rate_delta, rate_dir, hero=True)
        with c2:
            metric_card("Net Profit", format_compact(kpis["profit"]), "⊕",
                        weekly_metric_values(cleaned_df, "profit"),
                        format_percent(margin) if margin is not None else None,
                        "up" if (margin or 0) >= 15 else "down")
        with c3:
            metric_card("Avg Order Value", format_currency(kpis["average_order_value"]), "⊞",
                        weekly_metric_values(cleaned_df, "average_order_value"))
        with c4:
            metric_card("Profit Margin", format_percent(margin), "◐",
                        weekly_metric_values(cleaned_df, "profit_margin"))

        c5, c6, c7 = st.columns(3)
        with c5:
            metric_card("Total Orders", f"{kpis['orders']:,}", "▤", weekly_metric_values(cleaned_df, "orders"))
        with c6:
            metric_card("Unique Customers", f"{kpis['customers']:,}", "◇", weekly_metric_values(cleaned_df, "customers"))
        with c7:
            metric_card("Monthly Growth", format_percent(rate), "⇗",
                        weekly_metric_values(cleaned_df, "growth_rate"), rate_delta, rate_dir)

        trends = calculate_trends(cleaned_df) if cleaned_df is not None else {"monthly_trends": pd.DataFrame()}
        monthly = trends["monthly_trends"]

        left, right = st.columns([1.62, 1])
        with left:
            st.markdown('<div class="eyebrow">Trajectory</div>', unsafe_allow_html=True)
            if not monthly.empty:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=monthly["Month_Period"].astype(str), y=monthly["Revenue"], name="Revenue",
                    marker={"color": P["rev"], "line": {"width": 0}}, marker_cornerradius=6,
                    hovertemplate="%{x}<br>Revenue: $%{y:,.0f}<extra></extra>",
                ))
                fig.add_trace(go.Scatter(
                    x=monthly["Month_Period"].astype(str), y=monthly["Profit"], name="Profit", mode="lines+markers",
                    line={"color": P["profit"], "width": 3, "shape": "spline"}, marker={"size": 8},
                    hovertemplate="%{x}<br>Profit: $%{y:,.0f}<extra></extra>",
                ))
                st.plotly_chart(style_chart(fig, 380, "$", "Revenue & profit by month", x_category=True, y_from_zero=True),
                                width="stretch", config={"displayModeBar": False})
            else:
                st.info("Not enough dated history to plot the monthly trajectory.")

        with right:
            st.markdown('<div class="eyebrow">Revenue mix</div>', unsafe_allow_html=True)
            cat = dimension_revenue(cleaned_df, "Category")
            if not cat.empty:
                palette = (P["categ"] * 3)[: len(cat)]
                donut = go.Figure(go.Pie(
                    labels=cat["Category"], values=cat["Revenue"], hole=0.66, sort=False,
                    marker={"colors": palette, "line": {"color": THEME["vars"]["--card"], "width": 3}},
                    textinfo="percent", textfont={"size": 12, "color": "#12140d"},
                    hovertemplate="%{label}<br>$%{value:,.0f} (%{percent})<extra></extra>",
                ))
                donut.update_layout(annotations=[{
                    "text": f"<b>{format_compact(cat['Revenue'].sum())}</b><br><span style='font-size:11px'>total</span>",
                    "showarrow": False, "font": {"color": P["ink"], "size": 18}, "x": 0.5, "y": 0.5}])
                st.plotly_chart(style_chart(donut, 380, title="Revenue by category"),
                                width="stretch", config={"displayModeBar": False})
            else:
                st.info("No category dimension available.")

        st.markdown('<div class="eyebrow">Leaders</div>', unsafe_allow_html=True)
        lead_l, lead_r = st.columns(2)
        products = dimension_revenue(cleaned_df, "Product").head(5)
        customers = dimension_revenue(cleaned_df, "Customer_ID").head(5)

        def leaderboard(title: str, frame: pd.DataFrame, key_col: str, subtitle_fn) -> str:
            if frame.empty:
                return f'<div class="panel"><h4>{escape(title)}</h4><p>No data available.</p></div>'
            peak = float(frame["Revenue"].max()) or 1.0
            rows_html = []
            for rank, (_, row) in enumerate(frame.iterrows(), 1):
                pct = float(row["Revenue"]) / peak * 100
                rows_html.append(
                    f'<div class="list-row"><div class="lr-left">'
                    f'<span class="lr-rank">{rank}</span>'
                    f'<div class="lr-track"><div class="lr-name">{escape(str(row[key_col]))}</div>'
                    f'<div class="lr-sub">{subtitle_fn(row)}</div>'
                    f'<div class="lr-bar" style="width:{pct:.0f}%"></div></div></div>'
                    f'<span class="lr-val">{format_compact(row["Revenue"])}</span></div>'
                )
            return f'<div class="panel"><h4>{escape(title)}</h4>{"".join(rows_html)}</div>'

        with lead_l:
            st.markdown(leaderboard("Top products", products, "Product",
                                    lambda r: "revenue contribution"), unsafe_allow_html=True)
        with lead_r:
            st.markdown(leaderboard("Top customers", customers, "Customer_ID",
                                    lambda r: "lifetime revenue"), unsafe_allow_html=True)

        if rate is not None:
            st.info(
                f"Latest month revenue of {format_currency(kpis['growth_current_revenue'])} "
                f"({kpis['growth_current_period']}) vs previous month "
                f"{format_currency(kpis['growth_previous_revenue'])} ({kpis['growth_previous_period']})."
            )

        with st.expander("KPI formula reference"):
            st.dataframe(pd.DataFrame(KPI_DEFINITIONS), width="stretch", hide_index=True)


elif menu == "Upload & Quality":
    topbar("Data Upload & Quality Engine", "Ingest Pipeline")
    st.write(
        "Upload a business transactions CSV. Northstar maps standard column names, imputes missing "
        "financial records, resolves date stamps, and builds a quality health checklist."
    )

    uploaded_file = st.file_uploader("Upload sales data CSV", type=["csv"])
    if uploaded_file is not None:
        try:
            file_bytes = uploaded_file.getvalue()
            file_hash = hashlib.sha256(file_bytes).hexdigest()
            if file_hash != st.session_state["uploaded_file_hash"]:
                raw_data = pd.read_csv(BytesIO(file_bytes))
                cleaned, summary, col_rep, actions = clean_sales_data(raw_data)
                kpis = calculate_kpis(cleaned)
                st.session_state.update({
                    "raw_df": raw_data, "cleaned_df": cleaned, "quality_summary": summary,
                    "column_report": col_rep, "actions_log": actions, "kpis": kpis,
                    "source_name": uploaded_file.name,
                    "active_run_id": save_analysis_run(cleaned, kpis, uploaded_file.name),
                    "uploaded_file_hash": file_hash,
                })
                st.success("Upload processed and saved. Every dashboard view is now live.")
            else:
                st.caption("This file is already loaded. Upload a different CSV to refresh the analysis.")
        except Exception as exc:
            st.error(f"Error processing file: {exc}")
            st.stop()

    summary = st.session_state["quality_summary"]
    cleaned_df = st.session_state["cleaned_df"]

    if summary and cleaned_df is not None:
        st.markdown('<div class="eyebrow">Health snapshot</div>', unsafe_allow_html=True)
        cols = st.columns(5)
        with cols[0]:
            metric_card("Initial rows", f"{summary['rows_before']:,}", "▦")
        with cols[1]:
            metric_card("Cleaned rows", f"{summary['rows_after']:,}", "▩")
        with cols[2]:
            metric_card("Duplicates purged", f"{summary['duplicate_rows_removed']:,}", "⊗")
        with cols[3]:
            metric_card("Corrupt dates", f"{summary['invalid_dates_found']:,}", "⊘")
        with cols[4]:
            change = summary["quality_score_after"] - summary["quality_score_before"]
            metric_card("Quality index", f"{summary['quality_score_after']:.1f}%", "◉",
                        delta=f"{change:+.1f}%", direction="up" if change >= 0 else "down", hero=True)

        left, right = st.columns(2)
        with left:
            log_rows = st.session_state["actions_log"] or ["No cleaning operations were required — the CSV was pristine."]
            items = "".join(f'<div class="list-row"><div class="lr-left"><span class="lr-rank">✓</span>'
                             f'<span class="lr-name" style="white-space:normal">{escape(str(a))}</span></div></div>'
                             for a in log_rows)
            st.markdown(f'<div class="panel"><h4>Cleaning operations log</h4>{items}</div>', unsafe_allow_html=True)
        with right:
            schema_ok = not summary["missing_expected_columns"]
            schema_line = ("All expected schemas matched perfectly."
                           if schema_ok else "Missing optional columns: " + ", ".join(summary["missing_expected_columns"]))
            st.markdown(
                f'<div class="panel"><h4>Missing fields analysis</h4>'
                f'<div class="list-row"><span class="lr-name">Empty cells (raw)</span>'
                f'<span class="lr-val">{summary["missing_values_before"]:,}</span></div>'
                f'<div class="list-row"><span class="lr-name">Empty cells (after imputation)</span>'
                f'<span class="lr-val">{summary["missing_values_after"]:,}</span></div>'
                f'<div class="list-row"><span class="lr-name">Schema</span>'
                f'<span class="badge {"badge-accent" if schema_ok else "badge-ghost"}">{escape(schema_line)}</span></div></div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="eyebrow">Column-level health</div>', unsafe_allow_html=True)
        st.dataframe(st.session_state["column_report"], width="stretch", hide_index=True)

        st.markdown('<div class="eyebrow">Cleaned dataset preview</div>', unsafe_allow_html=True)
        st.dataframe(cleaned_df.head(20), width="stretch")
        st.download_button("Download cleaned dataset CSV", dataframe_to_csv_bytes(cleaned_df),
                           "cleaned_sales_dataset.csv", "text/csv")


elif menu == "Statistical Studio":
    topbar("Statistical Studio", "Exploratory Analysis")
    st.write(
        "Upload any CSV to generate a full statistical profile — distributions, correlations, outliers, "
        "and missingness. No upload? The active sales dataset is analysed by default."
    )

    stat_upload = st.file_uploader("Upload a CSV for statistical analysis", type=["csv"], key="stat_uploader")
    if stat_upload is not None:
        try:
            st.session_state["stat_df"] = pd.read_csv(BytesIO(stat_upload.getvalue()))
            st.session_state["stat_name"] = stat_upload.name
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}")

    data = st.session_state.get("stat_df")
    source_label = st.session_state.get("stat_name")
    if data is None:
        data = st.session_state.get("cleaned_df")
        source_label = st.session_state.get("source_name") or "active dataset"
    if data is None or data.empty:
        st.info("Upload a CSV above to begin statistical analysis.")
        st.stop()

    st.caption(f"Analysing **{source_label}** — {len(data):,} rows × {data.shape[1]} columns")

    def stat_number(value: float) -> str:
        if value is None or pd.isna(value):
            return "N/A"
        if abs(value) >= 10000:
            return format_compact(value, prefix="")
        return f"{value:,.2f}"

    profile = profile_dataframe(data)
    st.markdown('<div class="eyebrow">Dataset profile</div>', unsafe_allow_html=True)
    prof_cols = st.columns(6)
    with prof_cols[0]:
        metric_card("Rows", f"{profile['rows']:,}", "▦", hero=True)
    with prof_cols[1]:
        metric_card("Columns", f"{profile['cols']:,}", "▤")
    with prof_cols[2]:
        metric_card("Numeric", f"{profile['numeric']:,}", "◨")
    with prof_cols[3]:
        metric_card("Categorical", f"{profile['categorical']:,}", "◧")
    with prof_cols[4]:
        metric_card("Missing", f"{profile['missing_pct']:.1f}%", "⊘",
                    delta=f"{profile['missing']:,} cells" if profile["missing"] else "complete",
                    direction="down" if profile["missing"] else "up")
    with prof_cols[5]:
        metric_card("Duplicates", f"{profile['duplicates']:,}", "⊗",
                    delta=f"{profile['memory_kb']:.0f} KB", direction=None)

    num_summary = numeric_summary(data)
    cat_summary = categorical_summary(data)
    numeric_cols = num_summary["Column"].tolist() if not num_summary.empty else []

    if numeric_cols:
        st.markdown('<div class="eyebrow">Distribution explorer</div>', unsafe_allow_html=True)
        focus = st.selectbox("Numeric column", numeric_cols, key="stat_focus")
        focus_series = pd.to_numeric(data[focus], errors="coerce").dropna()
        ref = distribution_reference(data[focus])
        focus_row = num_summary[num_summary["Column"] == focus].iloc[0]

        read_cols = st.columns(5)
        with read_cols[0]:
            metric_card("Mean", stat_number(focus_row["Mean"]), "μ")
        with read_cols[1]:
            metric_card("Median", stat_number(focus_row["Median"]), "◑")
        with read_cols[2]:
            metric_card("Std dev", stat_number(focus_row["Std"]), "σ")
        with read_cols[3]:
            skew = focus_row["Skew"]
            metric_card("Skew", f"{skew:.2f}", "⋀",
                        delta="right" if skew > 0.2 else "left" if skew < -0.2 else "symmetric",
                        direction="up" if skew > 0.2 else "down" if skew < -0.2 else None)
        with read_cols[4]:
            outliers = int(focus_row["Outliers"])
            metric_card("Outliers", f"{outliers:,}", "◎",
                        delta="IQR rule", direction="down" if outliers else "up")

        dist_l, dist_r = st.columns([1.55, 1])
        with dist_l:
            hist = go.Figure(go.Histogram(
                x=focus_series, nbinsx=32,
                marker={"color": P["rev"], "line": {"color": THEME["vars"]["--card"], "width": 1}},
                hovertemplate="Range %{x}<br>Count %{y}<extra></extra>",
            ))
            for label, value, color in [("Mean", ref["mean"], P["profit"]), ("Median", ref["median"], P["pos"])]:
                if pd.notna(value):
                    hist.add_vline(x=value, line={"color": color, "width": 2, "dash": "dash"},
                                   annotation_text=label, annotation_position="top",
                                   annotation_font={"color": color, "size": 11})
            st.plotly_chart(style_chart(hist, 350, title=f"Distribution — {focus}"),
                            width="stretch", config={"displayModeBar": False})
        with dist_r:
            box = go.Figure(go.Box(
                y=focus_series, name=focus, boxmean="sd",
                marker={"color": P["profit"], "outliercolor": P["neg"], "size": 4},
                line={"color": P["profit"]}, fillcolor=P["band"],
                hovertemplate="%{y:,.2f}<extra></extra>",
            ))
            st.plotly_chart(style_chart(box, 350, title="Spread & outliers"),
                            width="stretch", config={"displayModeBar": False})

    corr = correlation_matrix(data)
    if not corr.empty:
        st.markdown('<div class="eyebrow">Correlation structure</div>', unsafe_allow_html=True)
        corr_l, corr_r = st.columns([1.42, 1])
        with corr_l:
            labels = corr.columns.tolist()
            show_text = len(labels) <= 12
            heat = go.Figure(go.Heatmap(
                z=corr.values, x=labels, y=labels, zmid=0, zmin=-1, zmax=1, colorscale=P["div"],
                colorbar={"title": "r", "outlinewidth": 0, "tickfont": {"color": P["axis"]}},
                text=corr.round(2).values if show_text else None,
                texttemplate="%{text}" if show_text else None,
                textfont={"size": 10, "color": P["ink"]},
                hovertemplate="%{y} ↔ %{x}<br>r = %{z:.2f}<extra></extra>",
            ))
            st.plotly_chart(style_chart(heat, 430, title="Pearson correlation matrix"),
                            width="stretch", config={"displayModeBar": False})
        with corr_r:
            tops = top_correlations(data, 8)
            if tops.empty:
                st.markdown('<div class="panel"><h4>Strongest relationships</h4><p>No pairs available.</p></div>',
                            unsafe_allow_html=True)
            else:
                rows_html = []
                for _, prow in tops.iterrows():
                    value = float(prow["Correlation"])
                    tone = "var(--good)" if value >= 0 else "var(--bad)"
                    sign = "＋" if value >= 0 else "－"
                    width = min(abs(value) * 100, 100)
                    rows_html.append(
                        f'<div class="list-row"><div class="lr-left">'
                        f'<span class="lr-rank" style="color:{tone}">{sign}</span>'
                        f'<div class="lr-track"><div class="lr-name">{escape(str(prow["Feature A"]))} ↔ {escape(str(prow["Feature B"]))}</div>'
                        f'<div class="lr-bar" style="width:{width:.0f}%; background:{tone}"></div></div></div>'
                        f'<span class="lr-val">{value:+.2f}</span></div>'
                    )
                st.markdown(f'<div class="panel"><h4>Strongest relationships</h4>{"".join(rows_html)}</div>',
                            unsafe_allow_html=True)
    else:
        st.info("At least two non-constant numeric columns are required for correlation analysis.")

    miss = missing_by_column(data)
    cat_cols = cat_summary["Column"].tolist() if not cat_summary.empty else []
    diag_l, diag_r = st.columns(2)
    with diag_l:
        st.markdown('<div class="eyebrow">Missingness</div>', unsafe_allow_html=True)
        if not miss.empty:
            mfig = go.Figure(go.Bar(
                x=miss["Missing %"], y=miss["Column"], orientation="h",
                marker={"color": P["neg"]}, marker_cornerradius=5,
                hovertemplate="%{y}<br>%{x:.1f}% missing<extra></extra>",
            ))
            mfig.update_yaxes(autorange="reversed")
            st.plotly_chart(style_chart(mfig, min(150 + len(miss) * 34, 430)),
                            width="stretch", config={"displayModeBar": False})
        else:
            st.success("No missing values detected across any column.")
    with diag_r:
        st.markdown('<div class="eyebrow">Category frequencies</div>', unsafe_allow_html=True)
        if cat_cols:
            cfocus = st.selectbox("Categorical column", cat_cols, key="stat_cat_focus")
            counts = value_counts_frame(data, cfocus, 12)
            if not counts.empty:
                cfig = go.Figure(go.Bar(
                    x=counts["Count"], y=counts[cfocus], orientation="h",
                    marker={"color": P["profit"]}, marker_cornerradius=5,
                    hovertemplate="%{y}<br>%{x:,} rows<extra></extra>",
                ))
                cfig.update_yaxes(autorange="reversed")
                st.plotly_chart(style_chart(cfig, min(150 + len(counts) * 30, 430)),
                                width="stretch", config={"displayModeBar": False})
        else:
            st.caption("No categorical columns to summarise.")

    st.markdown('<div class="eyebrow">Full statistical tables</div>', unsafe_allow_html=True)
    table_tabs = st.tabs(["Numeric summary", "Categorical summary", "Top correlations"])
    with table_tabs[0]:
        if not num_summary.empty:
            st.dataframe(num_summary.round(2), width="stretch", hide_index=True)
            st.download_button("Download numeric summary CSV", num_summary.to_csv(index=False).encode(),
                               "numeric_summary.csv", "text/csv")
        else:
            st.caption("No numeric columns detected.")
    with table_tabs[1]:
        if not cat_summary.empty:
            st.dataframe(cat_summary.round(2), width="stretch", hide_index=True)
        else:
            st.caption("No categorical columns detected.")
    with table_tabs[2]:
        all_corr = top_correlations(data, 25)
        if not all_corr.empty:
            st.dataframe(all_corr.round(3), width="stretch", hide_index=True)
        else:
            st.caption("Not enough numeric columns for pairwise correlation.")


elif menu == "SQL Playground":
    topbar("Interactive SQL Playground", "Query Console")
    st.write(
        "A relational SQLite playground over your active dataset. Run a predefined report to learn, "
        "or write custom ANSI SQL against the `sales_data` table."
    )

    run_id = st.session_state["active_run_id"]
    if not run_id:
        st.warning("No database records available. Please upload a dataset in **Upload & Quality** first.")
        st.stop()

    st.markdown('<div class="eyebrow">Predefined reports</div>', unsafe_allow_html=True)
    query_option = st.selectbox(
        "Select a report", list(PREDEFINED_QUERIES.keys()),
        format_func=lambda k: PREDEFINED_QUERIES[k]["title"],
    )
    report = PREDEFINED_QUERIES[query_option]
    st.caption(report["description"])
    st.code(report["query"].replace(":run_id", f"'{run_id}'"), language="sql")

    try:
        st.dataframe(run_predefined_query(run_id, query_option), width="stretch")
    except Exception as exc:
        st.error(f"SQL execution error: {exc}")

    with st.expander("Learn SQL — query explanation"):
        st.markdown(report["explanation"])

    st.markdown('<div class="eyebrow">Interactive console</div>', unsafe_allow_html=True)
    st.caption(
        "Table `sales_data` · columns: Date, Order_ID, Customer_ID, Product, Category, Revenue, Cost, Profit, Quantity. "
        f"Filter by run_id = '{run_id}' to isolate your dataset."
    )
    default_sql = (
        "SELECT Product, COUNT(*) as Transaction_Count, SUM(Revenue) as Total_Revenue\n"
        "FROM sales_data\n"
        f"WHERE run_id = '{run_id}'\n"
        "GROUP BY Product\n"
        "ORDER BY Total_Revenue DESC"
    )
    custom_sql = st.text_area("Write SQL SELECT statement", value=default_sql, height=180)
    if st.button("Execute query"):
        try:
            st.success("Query executed successfully.")
            st.dataframe(run_custom_query(run_id, custom_sql), width="stretch")
        except Exception as exc:
            st.error(f"SQL execution error: {exc}")


elif menu == "Trends & Root Cause":
    topbar("Trend & Root Cause Analysis", "Diagnostics")
    st.write(
        "Track trajectory across calendar metrics and automatically dissect declines. The Root Cause "
        "Engine decomposes month-over-month drops to pinpoint the exact category, product, or customer leak."
    )

    cleaned_df = st.session_state["cleaned_df"]
    if cleaned_df is None:
        st.warning("Upload a dataset in **Upload & Quality** first.")
        st.stop()

    trends = calculate_trends(cleaned_df)
    st.markdown('<div class="eyebrow">Trajectory summary</div>', unsafe_allow_html=True)
    t1, t2, t3 = st.columns(3)
    with t1:
        metric_card("Peak sales month", trends["best_month"] or "N/A", "▲",
                    delta=format_compact(trends["best_month_revenue"]), direction="up")
    with t2:
        metric_card("Lowest sales month", trends["worst_month"] or "N/A", "▼",
                    delta=format_compact(trends["worst_month_revenue"]), direction="down")
    with t3:
        rate = trends["fastest_growing_category_rate"]
        metric_card("Fastest-growing division", trends["fastest_growing_category"] or "N/A", "⇗",
                    delta=None if rate is None else f"{rate:.1f}% MoM",
                    direction=None if rate is None else ("up" if rate >= 0 else "down"), hero=True)

    st.markdown('<div class="eyebrow">Revenue & profit timelines</div>', unsafe_allow_html=True)
    mon = trends["monthly_trends"]
    if not mon.empty:
        timeline = go.Figure()
        for column, color in [("Revenue", P["rev"]), ("Profit", P["profit"])]:
            timeline.add_trace(go.Scatter(
                x=mon["Month_Period"].astype(str), y=mon[column], mode="lines+markers", name=column,
                line={"color": color, "width": 3, "shape": "spline"}, marker={"size": 8},
                hovertemplate=f"%{{x}}<br>{column}: $%{{y:,.0f}}<extra></extra>",
            ))
        st.plotly_chart(style_chart(timeline, 360, "$", x_category=True), width="stretch", config={"displayModeBar": False})
    else:
        st.info("Insufficient monthly history to build the timeline.")

    st.markdown('<div class="eyebrow">Automated root cause</div>', unsafe_allow_html=True)
    selected_metric = st.selectbox("Metric to analyze", ["Revenue", "Profit"])
    rca = analyze_root_cause(cleaned_df, selected_metric)

    report_lines = "".join(f'<p class="rec-desc" style="margin-bottom:8px">{line}</p>' for line in rca["explanations"])
    st.markdown(f'<div class="panel"><h4>RCA intelligence report</h4>{report_lines}</div>', unsafe_allow_html=True)

    if rca["drop_detected"]:
        st.markdown('<div class="eyebrow">Decomposed impact</div>', unsafe_allow_html=True)
        available = list(rca["dimension_changes"].keys())
        if available:
            grouping = st.selectbox("Waterfall grouping", available)
            changes = pd.DataFrame(rca["dimension_changes"][grouping])
            if not changes.empty:
                labels = changes[grouping].astype(str).tolist() + ["Net change"]
                values = changes["Change"].astype(float).tolist() + [float(rca["total_change"])]
                waterfall = go.Figure(go.Waterfall(
                    orientation="v", measure=["relative"] * len(changes) + ["total"], x=labels, y=values,
                    increasing={"marker": {"color": P["pos"]}}, decreasing={"marker": {"color": P["neg"]}},
                    totals={"marker": {"color": P["total"]}}, connector={"line": {"color": P["grid"]}},
                    hovertemplate="%{x}<br>Change: $%{y:,.2f}<extra></extra>",
                ))
                st.plotly_chart(
                    style_chart(waterfall, 420, "$", f"{selected_metric} change by {grouping.replace('_', ' ')}"),
                    width="stretch", config={"displayModeBar": False},
                )
        tab_labels = [("Category", "Category impact"), ("Product", "Product impact"), ("Customer_ID", "Customer impact")]
        tabs = st.tabs([label for _, label in tab_labels])
        for tab, (dim, _) in zip(tabs, tab_labels):
            with tab:
                if dim in rca["dimension_reports"]:
                    st.dataframe(pd.DataFrame(rca["dimension_reports"][dim]), width="stretch", hide_index=True)
                else:
                    st.caption("No decline recorded for this dimension.")


elif menu == "Forecasting":
    topbar("Predictive Sales Forecasting", "Projection Lab")
    st.write(
        "Project daily performance with statistical engines. Compare Moving Averages with Linear "
        "Regression across 30-day, 90-day, or 6-month horizons."
    )

    cleaned_df = st.session_state["cleaned_df"]
    if cleaned_df is None:
        st.warning("Upload a dataset in **Upload & Quality** first.")
        st.stop()

    horizon = st.selectbox("Forecast horizon", [30, 90, 180], format_func=lambda h: f"Next {h} days")
    forecast = generate_forecast(cleaned_df, horizon)
    f_df = forecast["forecast_df"]
    metrics = forecast["metrics"]

    if f_df.empty:
        st.info("Ensure at least 5 unique days of historical sales to generate forecasts.")
        st.stop()

    f1, f2, f3 = st.columns(3)
    with f1:
        metric_card("Avg daily sales", format_currency(metrics["average_historical_daily"]), "◒", hero=True)
    with f2:
        metric_card("Projected (Moving Avg)", format_compact(metrics["horizon_total_ma"]), "◇")
    with f3:
        metric_card("Projected (Linear Reg)", format_compact(metrics["horizon_total_lr"]), "⇗")

    st.markdown('<div class="eyebrow">Daily projections</div>', unsafe_allow_html=True)
    historical = f_df[f_df["Type"] == "Historical"]
    projected = f_df[f_df["Type"] == "Forecast"]
    chart = go.Figure()
    chart.add_trace(go.Scatter(x=historical["Date"], y=historical["Actual_Revenue"], mode="lines", name="Actual revenue",
                               line={"color": P["ink"], "width": 2.4}, hovertemplate="%{x|%b %d}<br>Actual: $%{y:,.2f}<extra></extra>"))
    chart.add_trace(go.Scatter(x=projected["Date"], y=projected["Forecast_LR_Upper"], mode="lines",
                               name="95% band", line={"color": "rgba(0,0,0,0)", "width": 0}, hoverinfo="skip", showlegend=False))
    chart.add_trace(go.Scatter(x=projected["Date"], y=projected["Forecast_LR_Lower"], mode="lines", name="95% confidence",
                               line={"color": "rgba(0,0,0,0)", "width": 0}, fill="tonexty", fillcolor=P["band"],
                               hovertemplate="%{x|%b %d}<br>Lower: $%{y:,.2f}<extra></extra>"))
    chart.add_trace(go.Scatter(x=projected["Date"], y=projected["Forecast_LR"], mode="lines", name="Linear regression",
                               line={"color": P["profit"], "width": 3}, hovertemplate="%{x|%b %d}<br>LR: $%{y:,.2f}<extra></extra>"))
    chart.add_trace(go.Scatter(x=projected["Date"], y=projected["Forecast_MA"], mode="lines", name="Moving average",
                               line={"color": P["rev"], "width": 2.4, "dash": "dot"}, hovertemplate="%{x|%b %d}<br>MA: $%{y:,.2f}<extra></extra>"))
    st.plotly_chart(style_chart(chart, 430, "$"), width="stretch", config={"displayModeBar": False})

    with st.expander("How the models work"):
        for explanation in forecast["explanations"]:
            st.markdown(explanation)


elif menu == "Recommendations":
    topbar("Business Recommendation Engine", "Action Center")
    st.write(
        "Heuristics cross-reference KPI ratios, negative-margin lines, seller concentration, and data "
        "sanitizers to surface prioritized actions."
    )

    cleaned_df = st.session_state["cleaned_df"]
    kpis = st.session_state["kpis"]
    summary = st.session_state["quality_summary"]

    if not (cleaned_df is not None and kpis and summary):
        st.warning("Upload a dataset in **Upload & Quality** first to run the engine.")
        st.stop()

    recs = generate_recommendations(cleaned_df, kpis, summary)
    if not recs:
        st.success("No business alerts triggered. The operational structure looks healthy.")
        st.stop()

    counts = {"High": 0, "Medium": 0, "Low": 0}
    for rec in recs:
        counts[rec["priority"]] = counts.get(rec["priority"], 0) + 1
    s1, s2, s3 = st.columns(3)
    with s1:
        metric_card("High priority", str(counts["High"]), "⚑", hero=counts["High"] > 0)
    with s2:
        metric_card("Medium priority", str(counts["Medium"]), "◮")
    with s3:
        metric_card("Low priority", str(counts["Low"]), "○")

    priority_color = {"High": "var(--bad)", "Medium": "#f6a54a", "Low": "var(--good)"}
    for index, rec in enumerate(recs, 1):
        color = priority_color.get(rec["priority"], "var(--accent)")
        st.markdown(
            f'<div class="rec" style="--rec-color:{color}">'
            f'<div class="rec-tags"><span class="rec-pri">{escape(rec["priority"])} priority</span>'
            f'<span class="rec-cat">{escape(rec["category"].upper())}</span></div>'
            f'<h4>{index}. {escape(rec["title"])}</h4>'
            f'<p class="rec-trig"><strong>Trigger:</strong> <em>{escape(rec["trigger_reason"])}</em></p>'
            f'<p class="rec-desc">{escape(rec["description"])}</p></div>',
            unsafe_allow_html=True,
        )


elif menu == "Power BI Guide":
    topbar("Power BI Development Suite", "Handoff Blueprint")
    st.write(
        "A structured roadmap to recreate this Northstar platform inside Microsoft Power BI, complete "
        "with relational modeling, metric definitions, and copy-pasteable DAX."
    )

    st.markdown(
        """
        ### 1. Relational Star Schema Model
        Deconstruct the cleaned dataset into a Star Schema with one fact table and three dimension tables:

        *   **Fact_Sales**: `Order_ID`, `Date`, `Customer_ID`, `Product_ID`, `Revenue`, `Cost`, `Profit`, `Quantity`
        *   **Dim_Products**: `Product_ID`, `Product_Name`, `Category`
        *   **Dim_Customers**: `Customer_ID`
        *   **Dim_Calendar**: `Date`, `Year`, `Quarter`, `Month`, `Month_Name`, `Day_of_Week` (Mark as Date Table)

        **Relationships**:
        *   `Dim_Calendar[Date]` 1 → * `Fact_Sales[Date]` (Active)
        *   `Dim_Products[Product_ID]` 1 → * `Fact_Sales[Product_ID]`
        *   `Dim_Customers[Customer_ID]` 1 → * `Fact_Sales[Customer_ID]`

        ---

        ### 2. Core Business Measures (DAX)
        Create a dedicated `_Measures` table and add:

        ```dax
        Total Revenue = SUM(Fact_Sales[Revenue])
        Total Cost = SUM(Fact_Sales[Cost])
        Total Profit = [Total Revenue] - [Total Cost]
        Profit Margin % = DIVIDE([Total Profit], [Total Revenue], 0)
        Total Orders = DISTINCTCOUNT(Fact_Sales[Order_ID])
        Average Order Value = DIVIDE([Total Revenue], [Total Orders], 0)
        ```

        ```dax
        MoM Revenue Growth % =
        VAR PriorMonthRevenue =
            CALCULATE([Total Revenue], DATEADD(Dim_Calendar[Date], -1, MONTH))
        RETURN
            DIVIDE([Total Revenue] - PriorMonthRevenue, PriorMonthRevenue, 0)
        ```

        ```dax
        Revenue YTD = TOTALYTD([Total Revenue], Dim_Calendar[Date])
        ```

        ---

        ### 3. Visual Layout Guidelines
        *   **Typography**: Segoe UI Semibold for numbers and headings; scale font to visual priority.
        *   **Color Theme**: Dark canvas `#0D0F0C`, visual containers `#181B16` with `20px` rounded corners and a lime `#C9F24D` accent.
        *   **Hierarchy**: KPI cards on top (Revenue, Profit, Margin %, AOV), category donut + monthly trend in the mid band, product matrix at the bottom.
        """
    )
