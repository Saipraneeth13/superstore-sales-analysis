"""Utilities and UI Styling Helper Module for Superstore Sales Analysis.

Provides CSS injection, custom metric cards, currency formatters,
and Plotly chart layout generators for a polished, modern blue & white enterprise dashboard.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import plotly.graph_objects as go
import streamlit as st

# Enterprise Blue & White Theme Color Palette
COLOR_BRAND_NAVY = "#0f172a"  # Deep Navy / Text Primary
COLOR_SAPPHIRE = "#1d4ed8"  # Royal Sapphire Blue
COLOR_PRIMARY = "#2563eb"  # Primary Blue
COLOR_ACCENT_BLUE = "#3b82f6"  # Bright Blue
COLOR_ICE_BLUE = "#eff6ff"  # Soft Ice Blue Background
COLOR_ICE_BORDER = "#dbeafe"  # Border Blue
COLOR_SURFACE_WHITE = "#ffffff"  # Clean Pure White
COLOR_SUCCESS = "#059669"  # Deep Emerald Green (Profits)
COLOR_SUCCESS_BG = "#ecfdf5"  # Soft Mint
COLOR_DANGER = "#dc2626"  # Crimson Red (Losses)
COLOR_DANGER_BG = "#fef2f2"  # Soft Coral
COLOR_WARNING = "#d97706"  # Amber
COLOR_MUTED = "#64748b"  # Slate Muted Text
COLOR_LIGHT_GRAY = "#f8fafc"  # Off-white Surface

CATEGORY_COLORS = {
    "Technology": "#2563eb",  # Sapphire Blue
    "Office Supplies": "#0284c7",  # Ocean Cyan
    "Furniture": "#d97706",  # Amber
}

REGION_COLORS = {
    "West": "#1d4ed8",
    "East": "#3b82f6",
    "Central": "#0284c7",
    "South": "#f59e0b",
}


def inject_custom_css() -> None:
    """Injects custom CSS for a modern, clean, unique blue-and-white enterprise UI."""
    custom_css = """
    <style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Global Typography & Background */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        color: #0f172a;
    }

    .stApp {
        background-color: #f8fafc;
    }

    code, pre, .stCodeBlock {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Top Executive Header Bar */
    .top-header-banner {
        background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 50%, #2563eb 100%);
        border-radius: 16px;
        padding: 24px 32px;
        color: #ffffff;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.25), 0 8px 10px -6px rgba(37, 99, 235, 0.2);
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .top-header-title {
        font-size: 1.75rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin: 0;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .top-header-subtitle {
        font-size: 0.95rem;
        color: #dbeafe;
        margin-top: 6px;
        font-weight: 400;
    }

    .header-badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 255, 255, 0.18);
        backdrop-filter: blur(8px);
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.25);
    }

    /* Metric Cards - Unique Blue & White Design */
    .metric-card-container {
        position: relative;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-top: 3.5px solid #2563eb;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 6px 12px -2px rgba(37, 99, 235, 0.04);
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 16px;
        min-height: 124px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .metric-card-container:hover {
        transform: translateY(-3px);
        border-color: #93c5fd;
        box-shadow: 0 10px 20px -3px rgba(37, 99, 235, 0.12), 0 4px 6px -2px rgba(37, 99, 235, 0.06);
    }

    .metric-header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }

    .metric-title {
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #64748b;
    }

    .metric-icon-box {
        width: 32px;
        height: 32px;
        border-radius: 8px;
        background: #eff6ff;
        color: #2563eb;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        border: 1px solid #dbeafe;
    }

    .metric-value {
        font-size: 1.7rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.03em;
        line-height: 1.15;
    }

    .metric-sub {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
        font-weight: 500;
    }

    /* Badges */
    .metric-badge-positive {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 6px;
        background-color: #ecfdf5;
        color: #059669;
        border: 1px solid #a7f3d0;
    }

    .metric-badge-negative {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 6px;
        background-color: #fef2f2;
        color: #dc2626;
        border: 1px solid #fecaca;
    }

    .metric-badge-neutral {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 6px;
        background-color: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
    }

    /* Card Containers */
    .white-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 20px 24px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }

    /* Blue Accent Section Callouts */
    .blue-callout {
        background: #eff6ff;
        border-left: 4px solid #2563eb;
        border-radius: 0 10px 10px 0;
        padding: 14px 18px;
        margin: 12px 0;
        color: #1e3a8a;
        font-size: 0.92rem;
        border: 1px solid #dbeafe;
        border-left-width: 4px;
    }

    .warning-callout {
        background: #fef2f2;
        border-left: 4px solid #dc2626;
        border-radius: 0 10px 10px 0;
        padding: 14px 18px;
        margin: 12px 0;
        color: #991b1b;
        font-size: 0.92rem;
        border: 1px solid #fecaca;
        border-left-width: 4px;
    }

    .success-callout {
        background: #ecfdf5;
        border-left: 4px solid #059669;
        border-radius: 0 10px 10px 0;
        padding: 14px 18px;
        margin: 12px 0;
        color: #065f46;
        font-size: 0.92rem;
        border: 1px solid #a7f3d0;
        border-left-width: 4px;
    }

    /* Streamlit Tabs Customization */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f1f5f9;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
    }

    .stTabs [data-baseweb="tab"] {
        height: 44px;
        white-space: pre-wrap;
        border-radius: 8px;
        color: #475569;
        font-size: 0.88rem;
        font-weight: 600;
        padding: 0 18px;
        transition: all 0.2s ease;
        background-color: transparent;
        border: none !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e2e8f0;
        color: #1e293b;
    }

    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #1d4ed8 !important;
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.12), 0 1px 2px rgba(0, 0, 0, 0.06);
        font-weight: 700 !important;
    }

    /* Sidebar Clean Styling */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }

    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: #1e3a8a;
    }

    /* Custom SQL Query Code Container */
    .sql-ide-container {
        background: #0f172a;
        color: #f8fafc;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #334155;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def format_currency(val: float, compact: bool = False) -> str:
    """Formats numeric value to US Dollar currency string."""
    if compact:
        if abs(val) >= 1_000_000:
            return f"${val / 1_000_000:,.2f}M"
        elif abs(val) >= 1_000:
            return f"${val / 1_000:,.1f}K"
        else:
            return f"${val:,.2f}"
    return f"${val:,.2f}"


def format_percent(val: float, decimals: int = 1) -> str:
    """Formats float value to percentage string."""
    return f"{val:.{decimals}f}%"


def format_number(val: int | float) -> str:
    """Formats number with thousands commas."""
    if isinstance(val, int) or (isinstance(val, float) and val.is_integer()):
        return f"{int(val):,}"
    return f"{val:,.2f}"


def render_kpi_card(
    title: str,
    value: str,
    subtitle: Optional[str] = None,
    badge: Optional[str] = None,
    badge_type: str = "neutral",  # 'positive', 'negative', 'neutral'
    icon: Optional[str] = None,
) -> None:
    """Renders a custom HTML KPI card in Streamlit with modern blue & white styling."""
    badge_html = ""
    if badge:
        css_class = f"metric-badge-{badge_type}"
        badge_html = f'<span class="{css_class}">{badge}</span>'

    icon_box = f'<div class="metric-icon-box">{icon}</div>' if icon else ""

    card_html = f"""
    <div class="metric-card-container">
        <div class="metric-header-row">
            <div class="metric-title">{title}</div>
            {icon_box}
        </div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">
            <span>{subtitle or ""}</span> {badge_html}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def apply_chart_layout(
    fig: go.Figure,
    title: str = "",
    height: int = 380,
    show_legend: bool = True,
    x_title: Optional[str] = None,
    y_title: Optional[str] = None,
) -> go.Figure:
    """Applies modern clean blue & white enterprise styling to Plotly charts."""
    fig.update_layout(
        title={
            "text": title,
            "font": {"size": 15, "weight": "bold", "family": "Plus Jakarta Sans, sans-serif", "color": "#0f172a"},
            "x": 0.01,
            "xanchor": "left",
        },
        height=height,
        margin={"l": 40, "r": 20, "t": 48, "b": 40},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"family": "Plus Jakarta Sans, sans-serif", "size": 12, "color": "#334155"},
        showlegend=show_legend,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"size": 11, "family": "Plus Jakarta Sans, sans-serif"},
        },
        hoverlabel={
            "bgcolor": "#0f172a",
            "font": {"family": "Plus Jakarta Sans, sans-serif", "size": 12, "color": "#ffffff"},
            "bordercolor": "#1e293b",
        },
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="#f1f5f9",
        linecolor="#cbd5e1",
        title={"text": x_title, "font": {"family": "Plus Jakarta Sans, sans-serif", "size": 12, "color": "#475569"}},
        tickfont={"family": "Plus Jakarta Sans, sans-serif", "size": 11, "color": "#64748b"},
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#f1f5f9",
        linecolor="#cbd5e1",
        title={"text": y_title, "font": {"family": "Plus Jakarta Sans, sans-serif", "size": 12, "color": "#475569"}},
        tickfont={"family": "Plus Jakarta Sans, sans-serif", "size": 11, "color": "#64748b"},
    )

    return fig
