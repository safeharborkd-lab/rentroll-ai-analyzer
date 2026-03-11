"""
RentRoll AI Analyzer
Private Equity & Real Estate Investor Tool
Built for programmatic JV acquisition workflows.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from io import BytesIO
from datetime import datetime, timedelta
import re
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# PAGE CONFIG & STYLING
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="RentRoll AI Analyzer",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

BRAND = {
    "primary": "#1B2A4A",
    "accent": "#2D8CFF",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "bg_dark": "#0F1724",
    "bg_card": "#1A2332",
    "bg_surface": "#F8FAFC",
    "text_primary": "#F1F5F9",
    "text_secondary": "#94A3B8",
    "border": "#334155",
}

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global */
    .stApp {{
        background: linear-gradient(135deg, {BRAND["bg_dark"]} 0%, #1a1f2e 100%);
        font-family: 'DM Sans', sans-serif;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: {BRAND["primary"]};
        border-right: 1px solid {BRAND["border"]};
    }}
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown label,
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiSelect label {{
        color: {BRAND["text_primary"]} !important;
        font-family: 'DM Sans', sans-serif;
    }}

    /* Header */
    .app-header {{
        background: linear-gradient(90deg, {BRAND["primary"]}, #243B5C);
        border-radius: 12px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        border: 1px solid {BRAND["border"]};
    }}
    .app-header h1 {{
        color: white;
        font-family: 'DM Sans', sans-serif;
        font-weight: 700;
        font-size: 1.8rem;
        margin: 0;
    }}
    .app-header p {{
        color: {BRAND["text_secondary"]};
        font-size: 0.95rem;
        margin: 0.25rem 0 0 0;
    }}

    /* KPI Cards */
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }}
    .kpi-card {{
        background: {BRAND["bg_card"]};
        border: 1px solid {BRAND["border"]};
        border-radius: 10px;
        padding: 1.1rem 1.2rem;
        transition: transform 0.15s, box-shadow 0.15s;
    }}
    .kpi-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }}
    .kpi-label {{
        color: {BRAND["text_secondary"]};
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 0.35rem;
    }}
    .kpi-value {{
        color: white;
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.45rem;
        font-weight: 700;
        line-height: 1.2;
    }}
    .kpi-sub {{
        color: {BRAND["text_secondary"]};
        font-size: 0.72rem;
        margin-top: 0.25rem;
    }}
    .kpi-accent {{ border-left: 3px solid {BRAND["accent"]}; }}
    .kpi-success {{ border-left: 3px solid {BRAND["success"]}; }}
    .kpi-warning {{ border-left: 3px solid {BRAND["warning"]}; }}
    .kpi-danger {{ border-left: 3px solid {BRAND["danger"]}; }}

    /* Section Headers */
    .section-header {{
        color: {BRAND["text_primary"]};
        font-family: 'DM Sans', sans-serif;
        font-weight: 700;
        font-size: 1.15rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid {BRAND["accent"]};
        margin: 1.5rem 0 1rem 0;
    }}

    /* Risk Badges */
    .risk-high {{ background: #FEE2E2; color: #991B1B; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; }}
    .risk-med {{ background: #FEF3C7; color: #92400E; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; }}
    .risk-low {{ background: #D1FAE5; color: #065F46; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; }}

    /* AI Insight Box */
    .ai-insight {{
        background: linear-gradient(135deg, {BRAND["bg_card"]}, #1E293B);
        border: 1px solid {BRAND["accent"]};
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: {BRAND["text_primary"]};
        line-height: 1.7;
    }}
    .ai-insight h4 {{
        color: {BRAND["accent"]};
        margin-bottom: 0.75rem;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0;
        background: {BRAND["bg_card"]};
        border-radius: 10px;
        padding: 4px;
        border: 1px solid {BRAND["border"]};
    }}
    .stTabs [data-baseweb="tab"] {{
        color: {BRAND["text_secondary"]};
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        font-size: 0.85rem;
        border-radius: 8px;
        padding: 0.5rem 1.2rem;
    }}
    .stTabs [aria-selected="true"] {{
        background: {BRAND["accent"]} !important;
        color: white !important;
    }}

    /* Download Buttons */
    .stDownloadButton > button {{
        background: {BRAND["accent"]} !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-family: 'DM Sans', sans-serif !important;
        padding: 0.4rem 1.2rem !important;
        font-size: 0.82rem !important;
    }}

    /* Upload Area */
    [data-testid="stFileUploader"] {{
        background: {BRAND["bg_card"]};
        border: 2px dashed {BRAND["border"]};
        border-radius: 12px;
        padding: 1rem;
    }}
    [data-testid="stFileUploader"] label {{
        color: {BRAND["text_primary"]} !important;
    }}

    /* Plotly Chart Containers */
    .stPlotlyChart {{
        background: {BRAND["bg_card"]};
        border: 1px solid {BRAND["border"]};
        border-radius: 10px;
        padding: 0.5rem;
    }}

    /* Hide streamlit branding */
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}

    /* Tab content text */
    .stTabs [data-testid="stMarkdownContainer"] p {{
        color: {BRAND["text_primary"]};
    }}
    .stTabs [data-testid="stMarkdownContainer"] h1,
    .stTabs [data-testid="stMarkdownContainer"] h2,
    .stTabs [data-testid="stMarkdownContainer"] h3 {{
        color: {BRAND["text_primary"]};
    }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# COLUMN MAPPING ENGINE
# ─────────────────────────────────────────────

COLUMN_MAP = {
    "unit": {
        "patterns": [
            r"unit\s*#?", r"unit\s*num", r"unit\s*id", r"slip\s*#?",
            r"slip\s*num", r"space\s*#?", r"suite\s*#?", r"lot\s*#?",
            r"berth", r"dock\s*#?", r"bay\s*#?",
        ],
        "required": True,
    },
    "tenant": {
        "patterns": [
            r"tenant\s*name", r"tenant", r"lessee", r"occupant",
            r"renter", r"customer", r"vessel\s*name", r"boat\s*name",
            r"owner\s*name", r"name",
        ],
        "required": False,
    },
    "monthly_rent": {
        "patterns": [
            r"monthly\s*rent", r"mr\b", r"rent\s*\/?\s*mo", r"mo\s*rent",
            r"monthly\s*rate", r"base\s*rent", r"contract\s*rent",
            r"current\s*rent", r"actual\s*rent", r"rent\s*amount",
            r"rent$", r"rate$", r"monthly\s*fee", r"slip\s*fee",
            r"storage\s*fee", r"dock\s*fee",
        ],
        "required": True,
    },
    "market_rent": {
        "patterns": [
            r"market\s*rent", r"market\s*rate", r"asking\s*rent",
            r"proforma\s*rent", r"pro\s*forma", r"comparable\s*rent",
            r"comp\s*rent", r"target\s*rent",
        ],
        "required": False,
    },
    "sqft": {
        "patterns": [
            r"sq\s*ft", r"sqft", r"square\s*f", r"sf\b", r"rsf\b",
            r"area", r"size", r"loa\b", r"length\s*overall",
            r"slip\s*length", r"boat\s*length",
        ],
        "required": False,
    },
    "status": {
        "patterns": [
            r"status", r"occupancy\s*status", r"occ\s*status",
            r"vacant", r"occupied", r"lease\s*status", r"availability",
        ],
        "required": False,
    },
    "lease_start": {
        "patterns": [
            r"lease\s*start", r"start\s*date", r"commence",
            r"move\s*in", r"eff\s*date", r"effective\s*date",
        ],
        "required": False,
    },
    "lease_end": {
        "patterns": [
            r"lease\s*end", r"end\s*date", r"expir", r"expiry",
            r"maturity", r"term\s*end", r"move\s*out",
        ],
        "required": False,
    },
    "unit_type": {
        "patterns": [
            r"unit\s*type", r"type", r"category", r"class",
            r"bed\s*room", r"br\b", r"floorplan", r"floor\s*plan",
            r"slip\s*type", r"storage\s*type", r"wet\s*slip",
            r"dry\s*storage", r"covered",
        ],
        "required": False,
    },
    "property": {
        "patterns": [
            r"property", r"asset", r"building", r"location",
            r"site", r"marina\s*name", r"facility",
        ],
        "required": False,
    },
    "annual_rent": {
        "patterns": [
            r"annual\s*rent", r"yearly\s*rent", r"ar\b",
            r"rent\s*\/?\s*yr", r"yr\s*rent", r"annual\s*rate",
        ],
        "required": False,
    },
}


def map_columns(df: pd.DataFrame) -> dict:
    """Auto-map raw column names to standardized fields.

    Uses two passes: first tries full-string matches (higher confidence),
    then falls back to substring/regex matches. This prevents 'Market Rent'
    from incorrectly matching the monthly_rent field's 'rent$' pattern
    when 'MR' is available.
    """
    mapping = {}
    used_cols = set()

    for field, cfg in COLUMN_MAP.items():
        best_match = None
        best_score = 0
        for col in df.columns:
            if col in used_cols:
                continue
            col_clean = str(col).strip().lower()
            for pattern in cfg["patterns"]:
                match = re.search(pattern, col_clean)
                if match:
                    # Prefer matches that cover the entire column name (exact)
                    coverage = (match.end() - match.start()) / max(len(col_clean), 1)
                    # Score: coverage (0-1) * 1000 + pattern specificity
                    score = coverage * 1000 + len(pattern)
                    if score > best_score:
                        best_score = score
                        best_match = col
        if best_match:
            mapping[field] = best_match
            used_cols.add(best_match)

    return mapping


def clean_currency(series: pd.Series) -> pd.Series:
    """Clean currency strings to float."""
    if series.dtype in [np.float64, np.int64, float, int]:
        return series.astype(float)
    return (
        series.astype(str)
        .str.replace(r"[\$,\s]", "", regex=True)
        .str.replace(r"[()]", "-", regex=True)
        .str.strip()
        .replace(["", "-", "nan", "None", "N/A", "n/a"], np.nan)
        .astype(float)
    )


def clean_dataframe(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Standardize and clean the rent roll."""
    clean = pd.DataFrame()

    # Unit
    if "unit" in mapping:
        clean["unit"] = df[mapping["unit"]].astype(str).str.strip()
    else:
        clean["unit"] = [f"Unit-{i+1}" for i in range(len(df))]

    # Tenant
    if "tenant" in mapping:
        clean["tenant"] = df[mapping["tenant"]].astype(str).str.strip()
        clean["tenant"] = clean["tenant"].replace(["nan", "None", "", "N/A"], "Vacant")
    else:
        clean["tenant"] = "Unknown"

    # Monthly Rent
    if "monthly_rent" in mapping:
        clean["monthly_rent"] = clean_currency(df[mapping["monthly_rent"]])
    elif "annual_rent" in mapping:
        clean["monthly_rent"] = clean_currency(df[mapping["annual_rent"]]) / 12
    else:
        clean["monthly_rent"] = 0.0

    # Market Rent
    if "market_rent" in mapping:
        clean["market_rent"] = clean_currency(df[mapping["market_rent"]])
    else:
        clean["market_rent"] = np.nan

    # SqFt / Size
    if "sqft" in mapping:
        clean["sqft"] = clean_currency(df[mapping["sqft"]])
    else:
        clean["sqft"] = np.nan

    # Status
    if "status" in mapping:
        raw_status = df[mapping["status"]].astype(str).str.strip().str.lower()
        clean["status"] = raw_status.apply(
            lambda x: "Vacant" if any(v in x for v in ["vacant", "empty", "available", "open", "unoccupied"])
            else "Occupied"
        )
    else:
        clean["status"] = clean["tenant"].apply(
            lambda x: "Vacant" if x in ["Vacant", "Unknown", "nan", ""] else "Occupied"
        )

    # Lease Start / End
    for date_field in ["lease_start", "lease_end"]:
        if date_field in mapping:
            clean[date_field] = pd.to_datetime(df[mapping[date_field]], errors="coerce", dayfirst=False)
        else:
            clean[date_field] = pd.NaT

    # Unit Type
    if "unit_type" in mapping:
        clean["unit_type"] = df[mapping["unit_type"]].astype(str).str.strip()
        clean["unit_type"] = clean["unit_type"].replace(["nan", "None", ""], "Standard")
    else:
        clean["unit_type"] = "Standard"

    # Property
    if "property" in mapping:
        clean["property"] = df[mapping["property"]].astype(str).str.strip()
        clean["property"] = clean["property"].replace(["nan", "None", ""], "Portfolio")
    else:
        clean["property"] = "Portfolio"

    # Derived fields
    clean["annual_rent"] = clean["monthly_rent"] * 12
    clean["rent_per_sqft"] = np.where(
        clean["sqft"] > 0,
        clean["annual_rent"] / clean["sqft"],
        np.nan,
    )

    # Loss-to-Lease per unit
    if clean["market_rent"].notna().any():
        clean["loss_to_lease"] = np.where(
            (clean["market_rent"] > 0) & (clean["status"] == "Occupied"),
            clean["market_rent"] - clean["monthly_rent"],
            0,
        )
    else:
        clean["loss_to_lease"] = 0.0

    # Lease term remaining (months)
    today = pd.Timestamp.today().normalize()
    clean["months_remaining"] = np.where(
        clean["lease_end"].notna(),
        ((clean["lease_end"] - today).dt.days / 30.44).clip(lower=0),
        np.nan,
    )

    # Expiration bucket
    def expiration_bucket(end_date):
        if pd.isna(end_date):
            return "No End Date"
        months = (end_date - today).days / 30.44
        if months < 0:
            return "Expired"
        elif months <= 12:
            return "0-12 Mo"
        elif months <= 24:
            return "12-24 Mo"
        elif months <= 36:
            return "24-36 Mo"
        else:
            return "36+ Mo"

    clean["exp_bucket"] = clean["lease_end"].apply(expiration_bucket)

    return clean


# ─────────────────────────────────────────────
# KPI COMPUTATION ENGINE
# ─────────────────────────────────────────────

def compute_kpis(df: pd.DataFrame) -> dict:
    """Compute all rent roll KPIs."""
    total_units = len(df)
    occupied = df[df["status"] == "Occupied"]
    vacant = df[df["status"] == "Vacant"]
    occupied_count = len(occupied)
    vacant_count = len(vacant)

    # Occupancy
    occupancy_pct = (occupied_count / total_units * 100) if total_units > 0 else 0

    # GPR (Gross Potential Rent) = all units at market or actual, monthly
    if df["market_rent"].notna().any():
        gpr_monthly = df["market_rent"].fillna(df["monthly_rent"]).sum()
    else:
        gpr_monthly = df["monthly_rent"].sum()  # fallback: assume current = market

    # Effective Gross Revenue (actual collections from occupied)
    egr_monthly = occupied["monthly_rent"].sum()

    # Economic Occupancy
    economic_occ = (egr_monthly / gpr_monthly * 100) if gpr_monthly > 0 else 0

    # Avg Rent per Unit (occupied only)
    avg_rent_unit = occupied["monthly_rent"].mean() if occupied_count > 0 else 0

    # Avg Rent per SqFt (occupied, annual basis)
    occ_with_sqft = occupied[occupied["sqft"] > 0]
    if len(occ_with_sqft) > 0:
        avg_rent_sqft = (occ_with_sqft["annual_rent"].sum() / occ_with_sqft["sqft"].sum())
    else:
        avg_rent_sqft = None

    # WALE (Weighted Average Lease Expiry in months, weighted by rent)
    occ_with_end = occupied[occupied["months_remaining"].notna() & (occupied["monthly_rent"] > 0)]
    if len(occ_with_end) > 0:
        wale = np.average(occ_with_end["months_remaining"], weights=occ_with_end["monthly_rent"])
    else:
        wale = None

    # Expiration counts
    today = pd.Timestamp.today().normalize()
    has_end = occupied[occupied["lease_end"].notna()]
    exp_12 = len(has_end[has_end["lease_end"] <= today + timedelta(days=365)])
    exp_24 = len(has_end[has_end["lease_end"] <= today + timedelta(days=730)])
    exp_36 = len(has_end[has_end["lease_end"] <= today + timedelta(days=1095)])

    # Loss-to-Lease %
    if df["market_rent"].notna().any():
        total_market = occupied[occupied["market_rent"] > 0]["market_rent"].sum()
        total_actual = occupied[occupied["market_rent"] > 0]["monthly_rent"].sum()
        ltl_pct = ((total_market - total_actual) / total_market * 100) if total_market > 0 else 0
    else:
        ltl_pct = None

    # Total monthly / annual
    total_monthly = occupied["monthly_rent"].sum()
    total_annual = total_monthly * 12

    return {
        "total_units": total_units,
        "occupied": occupied_count,
        "vacant": vacant_count,
        "occupancy_pct": occupancy_pct,
        "gpr_monthly": gpr_monthly,
        "gpr_annual": gpr_monthly * 12,
        "egr_monthly": egr_monthly,
        "economic_occ": economic_occ,
        "avg_rent_unit": avg_rent_unit,
        "avg_rent_sqft": avg_rent_sqft,
        "wale_months": wale,
        "exp_12": exp_12,
        "exp_24": exp_24,
        "exp_36": exp_36,
        "ltl_pct": ltl_pct,
        "total_monthly": total_monthly,
        "total_annual": total_annual,
    }


# ─────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────

CHART_TEMPLATE = "plotly_dark"
CHART_COLORS = ["#2D8CFF", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"]

CHART_LAYOUT = dict(
    template=CHART_TEMPLATE,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#CBD5E1"),
    margin=dict(l=40, r=20, t=50, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)


def make_lease_expiration_chart(df: pd.DataFrame) -> go.Figure:
    """Lease expiration waterfall chart."""
    occupied = df[df["status"] == "Occupied"]
    bucket_order = ["Expired", "0-12 Mo", "12-24 Mo", "24-36 Mo", "36+ Mo", "No End Date"]
    counts = occupied.groupby("exp_bucket").agg(
        units=("unit", "count"),
        rent=("monthly_rent", "sum"),
    ).reindex(bucket_order).fillna(0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=counts.index,
        y=counts["units"],
        marker_color=["#EF4444", "#F59E0B", "#2D8CFF", "#10B981", "#8B5CF6", "#64748B"],
        text=counts["units"].astype(int),
        textposition="outside",
        name="Units",
        hovertemplate="<b>%{x}</b><br>Units: %{y}<br>Monthly Rent: $%{customdata:,.0f}<extra></extra>",
        customdata=counts["rent"],
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Lease Expiration Schedule", font=dict(size=15)),
        yaxis_title="Units",
        showlegend=False,
        height=380,
    )
    return fig


def make_rent_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Monthly rent distribution histogram."""
    occupied = df[(df["status"] == "Occupied") & (df["monthly_rent"] > 0)]
    fig = px.histogram(
        occupied, x="monthly_rent", nbins=20,
        color_discrete_sequence=[BRAND["accent"]],
        labels={"monthly_rent": "Monthly Rent ($)"},
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Rent Distribution", font=dict(size=15)),
        yaxis_title="Count",
        showlegend=False,
        height=380,
    )
    return fig


def make_occupancy_pie(df: pd.DataFrame) -> go.Figure:
    """Occupancy donut chart."""
    counts = df["status"].value_counts()
    fig = go.Figure(go.Pie(
        labels=counts.index,
        values=counts.values,
        hole=0.6,
        marker=dict(colors=[BRAND["success"], BRAND["danger"]]),
        textinfo="label+percent",
        textfont=dict(size=13),
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Occupancy Split", font=dict(size=15)),
        showlegend=False,
        height=380,
    )
    return fig


def make_rent_vs_sqft_scatter(df: pd.DataFrame) -> go.Figure:
    """Rent vs SqFt scatter."""
    plot_df = df[(df["status"] == "Occupied") & (df["sqft"] > 0) & (df["monthly_rent"] > 0)].copy()
    if len(plot_df) == 0:
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT, title="Rent vs Size (No SqFt Data)", height=380)
        return fig

    fig = px.scatter(
        plot_df, x="sqft", y="monthly_rent",
        color="unit_type",
        hover_data=["unit", "tenant"],
        color_discrete_sequence=CHART_COLORS,
        labels={"sqft": "Size (SqFt / LOA)", "monthly_rent": "Monthly Rent ($)"},
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Rent vs Size", font=dict(size=15)),
        height=380,
    )
    return fig


def make_revenue_by_type_chart(df: pd.DataFrame) -> go.Figure:
    """Revenue contribution by unit type."""
    occupied = df[df["status"] == "Occupied"]
    by_type = occupied.groupby("unit_type")["monthly_rent"].sum().sort_values(ascending=True)
    fig = go.Figure(go.Bar(
        x=by_type.values,
        y=by_type.index,
        orientation="h",
        marker_color=CHART_COLORS[:len(by_type)],
        text=[f"${v:,.0f}" for v in by_type.values],
        textposition="outside",
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Monthly Revenue by Unit Type", font=dict(size=15)),
        xaxis_title="Monthly Rent ($)",
        showlegend=False,
        height=380,
    )
    return fig


# ─────────────────────────────────────────────
# AI INSIGHTS ENGINE
# ─────────────────────────────────────────────

def generate_insights(df: pd.DataFrame, kpis: dict) -> list[str]:
    """Generate rules-based natural language insights."""
    insights = []
    occupied = df[df["status"] == "Occupied"]

    # 1. Occupancy assessment
    occ = kpis["occupancy_pct"]
    if occ >= 95:
        insights.append(
            f"**Occupancy Strength:** Physical occupancy sits at {occ:.1f}%, indicating strong demand "
            f"and limited near-term lease-up risk. Evaluate whether current rents have room to move to market."
        )
    elif occ >= 85:
        insights.append(
            f"**Occupancy Assessment:** Physical occupancy is {occ:.1f}%, within the stabilized band for most "
            f"operating assets. Focus on converting the {kpis['vacant']} vacant unit(s) to stabilize above 90%."
        )
    else:
        insights.append(
            f"**Occupancy Concern:** Physical occupancy at {occ:.1f}% is below stabilized levels. "
            f"The {kpis['vacant']} vacant unit(s) represent a {100-occ:.1f}% vacancy drag on revenue. "
            f"Underwrite lease-up timing and concession costs carefully."
        )

    # 2. Economic occupancy gap
    if kpis["economic_occ"] < kpis["occupancy_pct"] - 3:
        gap = kpis["occupancy_pct"] - kpis["economic_occ"]
        insights.append(
            f"**Economic Occupancy Gap:** Economic occupancy ({kpis['economic_occ']:.1f}%) trails physical "
            f"({occ:.1f}%) by {gap:.1f} pts, signaling concessions, free rent, or below-market leases "
            f"are compressing effective revenue."
        )

    # 3. Loss-to-Lease opportunity
    if kpis["ltl_pct"] is not None:
        if kpis["ltl_pct"] > 10:
            ltl_monthly = occupied["loss_to_lease"].sum()
            insights.append(
                f"**Loss-to-Lease Upside:** At {kpis['ltl_pct']:.1f}%, there is approximately "
                f"${ltl_monthly:,.0f}/mo (${ltl_monthly*12:,.0f}/yr) in mark-to-market upside. "
                f"This is a core value-add lever, prioritize units furthest below market on next renewal."
            )
        elif kpis["ltl_pct"] > 5:
            insights.append(
                f"**Moderate Loss-to-Lease:** {kpis['ltl_pct']:.1f}% LTL suggests moderate rent growth "
                f"opportunity. Target below-market units at renewal to capture incremental NOI."
            )
        else:
            insights.append(
                f"**Rents Near Market:** Loss-to-lease is only {kpis['ltl_pct']:.1f}%, indicating "
                f"limited organic rent growth from mark-to-market. NOI growth will depend on ancillary "
                f"revenue or expense optimization."
            )

    # 4. Rollover risk
    if kpis["exp_12"] > 0:
        pct_12 = kpis["exp_12"] / kpis["occupied"] * 100 if kpis["occupied"] > 0 else 0
        rent_at_risk = occupied[
            occupied["lease_end"].notna()
            & (occupied["lease_end"] <= pd.Timestamp.today() + timedelta(days=365))
        ]["monthly_rent"].sum()
        insights.append(
            f"**Near-Term Rollover:** {kpis['exp_12']} lease(s) ({pct_12:.0f}% of occupied) expire within "
            f"12 months, representing ${rent_at_risk:,.0f}/mo in at-risk revenue. "
            f"Model renewal probability and downtime assumptions for underwriting."
        )

    # 5. Tenant concentration
    if len(occupied) > 0:
        by_tenant = occupied.groupby("tenant")["monthly_rent"].sum().sort_values(ascending=False)
        total_rev = by_tenant.sum()
        if total_rev > 0:
            top_tenant_pct = by_tenant.iloc[0] / total_rev * 100
            if top_tenant_pct > 25:
                insights.append(
                    f"**Concentration Risk:** The largest tenant (\"{by_tenant.index[0]}\") accounts for "
                    f"{top_tenant_pct:.1f}% of total occupied revenue. Single-tenant exposure above 25% "
                    f"warrants credit analysis and renewal probability assessment."
                )
            top5_pct = by_tenant.head(5).sum() / total_rev * 100
            if top5_pct > 50 and len(by_tenant) > 5:
                insights.append(
                    f"**Top 5 Concentration:** The top 5 tenants represent {top5_pct:.1f}% of revenue. "
                    f"In a downside scenario, loss of any one creates outsized NOI impact."
                )

    # 6. WALE
    if kpis["wale_months"] is not None:
        wale_yrs = kpis["wale_months"] / 12
        if wale_yrs < 2:
            insights.append(
                f"**Short WALE:** Weighted average lease expiry is {wale_yrs:.1f} years. "
                f"This creates near-term re-leasing risk but also an opportunity to mark rents "
                f"to market quickly if demand supports it."
            )
        elif wale_yrs > 5:
            insights.append(
                f"**Strong WALE:** At {wale_yrs:.1f} years, the weighted lease term provides "
                f"revenue visibility and limits near-term vacancy risk."
            )

    # 7. Rent dispersion
    if len(occupied) > 5:
        cv = occupied["monthly_rent"].std() / occupied["monthly_rent"].mean() if occupied["monthly_rent"].mean() > 0 else 0
        if cv > 0.5:
            insights.append(
                f"**Rent Dispersion:** High coefficient of variation ({cv:.2f}) in rents across units "
                f"may indicate legacy pricing, mixed unit types, or inconsistent rate management. "
                f"Audit the rent roll for below-market outliers."
            )

    return insights


# ─────────────────────────────────────────────
# EXPORT HELPERS
# ─────────────────────────────────────────────

def to_excel_download(df: pd.DataFrame, sheet_name: str = "Data") -> bytes:
    """Convert DataFrame to downloadable Excel bytes."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        header_fmt = workbook.add_format({
            "bold": True,
            "bg_color": "#1B2A4A",
            "font_color": "white",
            "border": 1,
        })
        for col_num, col_name in enumerate(df.columns):
            worksheet.write(0, col_num, col_name, header_fmt)
            max_len = max(df[col_name].astype(str).str.len().max(), len(col_name)) + 2
            worksheet.set_column(col_num, col_num, min(max_len, 30))

    return output.getvalue()


def kpi_to_dataframe(kpis: dict) -> pd.DataFrame:
    """Convert KPI dict to a nice dataframe for export."""
    rows = [
        ("Total Units", kpis["total_units"]),
        ("Occupied Units", kpis["occupied"]),
        ("Vacant Units", kpis["vacant"]),
        ("Physical Occupancy %", f"{kpis['occupancy_pct']:.1f}%"),
        ("Economic Occupancy %", f"{kpis['economic_occ']:.1f}%"),
        ("GPR (Monthly)", f"${kpis['gpr_monthly']:,.0f}"),
        ("GPR (Annual)", f"${kpis['gpr_annual']:,.0f}"),
        ("EGR (Monthly)", f"${kpis['egr_monthly']:,.0f}"),
        ("Avg Rent / Unit", f"${kpis['avg_rent_unit']:,.0f}"),
    ]
    if kpis["avg_rent_sqft"] is not None:
        rows.append(("Avg Rent / SqFt (Annual)", f"${kpis['avg_rent_sqft']:.2f}"))
    if kpis["wale_months"] is not None:
        rows.append(("WALE (Months)", f"{kpis['wale_months']:.1f}"))
        rows.append(("WALE (Years)", f"{kpis['wale_months']/12:.1f}"))
    rows.append(("Leases Expiring 12 Mo", kpis["exp_12"]))
    rows.append(("Leases Expiring 24 Mo", kpis["exp_24"]))
    rows.append(("Leases Expiring 36 Mo", kpis["exp_36"]))
    if kpis["ltl_pct"] is not None:
        rows.append(("Loss-to-Lease %", f"{kpis['ltl_pct']:.1f}%"))

    return pd.DataFrame(rows, columns=["Metric", "Value"])


# ─────────────────────────────────────────────
# APP HEADER
# ─────────────────────────────────────────────

st.markdown("""
<div class="app-header">
    <h1>🏢 RentRoll AI Analyzer</h1>
    <p>Private equity-grade rent roll analysis. Upload CSV or Excel to begin.</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# FILE UPLOAD
# ─────────────────────────────────────────────

uploaded = st.file_uploader(
    "Upload Rent Roll (CSV, XLSX, XLS)",
    type=["csv", "xlsx", "xls"],
    help="Supports most rent roll formats. The analyzer will auto-detect column mappings.",
)

if uploaded is None:
    st.markdown(f"""
    <div style="
        background: {BRAND['bg_card']};
        border: 1px solid {BRAND['border']};
        border-radius: 12px;
        padding: 2.5rem;
        text-align: center;
        margin-top: 2rem;
    ">
        <h3 style="color: {BRAND['text_primary']}; margin-bottom: 1rem;">Getting Started</h3>
        <p style="color: {BRAND['text_secondary']}; max-width: 500px; margin: 0 auto; line-height: 1.7;">
            Upload a rent roll in CSV or Excel format. The analyzer will auto-detect columns
            like Unit #, Tenant Name, Monthly Rent (MR), Lease Dates, SqFt, and more.
        </p>
        <div style="margin-top: 1.5rem; display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
            <span style="background: {BRAND['primary']}; color: {BRAND['accent']}; padding: 6px 14px; border-radius: 6px; font-size: 0.8rem; font-weight: 600;">
                Multi-property supported
            </span>
            <span style="background: {BRAND['primary']}; color: {BRAND['success']}; padding: 6px 14px; border-radius: 6px; font-size: 0.8rem; font-weight: 600;">
                Marina &amp; MF formats
            </span>
            <span style="background: {BRAND['primary']}; color: {BRAND['warning']}; padding: 6px 14px; border-radius: 6px; font-size: 0.8rem; font-weight: 600;">
                Auto column mapping
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────────
# LOAD & PROCESS DATA
# ─────────────────────────────────────────────

@st.cache_data
def load_file(file_bytes, file_name):
    if file_name.endswith(".csv"):
        return pd.read_csv(BytesIO(file_bytes))
    else:
        return pd.read_excel(BytesIO(file_bytes))


raw_df = load_file(uploaded.getvalue(), uploaded.name)

# Drop fully empty rows
raw_df = raw_df.dropna(how="all").reset_index(drop=True)

# Auto-map columns
mapping = map_columns(raw_df)

if "monthly_rent" not in mapping and "annual_rent" not in mapping:
    st.error("Could not auto-detect a rent column. Please ensure your file has a column like 'Monthly Rent', 'MR', 'Rent', or 'Annual Rent'.")
    st.write("**Detected columns:**", list(raw_df.columns))
    st.stop()

# Show mapping in sidebar expander
with st.sidebar:
    st.markdown(f"<h3 style='color: white; font-family: DM Sans;'>⚙️ Column Mapping</h3>", unsafe_allow_html=True)
    with st.expander("View detected mappings", expanded=False):
        for field, col in mapping.items():
            st.text(f"{field:16s} → {col}")
        unmapped = [c for c in raw_df.columns if c not in mapping.values()]
        if unmapped:
            st.text(f"\nUnmapped: {', '.join(unmapped)}")

# Clean
df = clean_dataframe(raw_df, mapping)

# ─────────────────────────────────────────────
# SIDEBAR FILTERS
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"<h3 style='color: white; font-family: DM Sans;'>🔍 Filters</h3>", unsafe_allow_html=True)

    # Property
    properties = sorted(df["property"].unique())
    if len(properties) > 1:
        sel_properties = st.multiselect("Property", properties, default=properties)
    else:
        sel_properties = properties

    # Unit Type
    unit_types = sorted(df["unit_type"].unique())
    if len(unit_types) > 1:
        sel_types = st.multiselect("Unit Type", unit_types, default=unit_types)
    else:
        sel_types = unit_types

    # Status
    sel_status = st.multiselect("Status", ["Occupied", "Vacant"], default=["Occupied", "Vacant"])

    # Expiration Bucket
    buckets = ["Expired", "0-12 Mo", "12-24 Mo", "24-36 Mo", "36+ Mo", "No End Date"]
    available_buckets = [b for b in buckets if b in df["exp_bucket"].unique()]
    sel_buckets = st.multiselect("Expiration Bucket", available_buckets, default=available_buckets)

    st.markdown("---")
    st.markdown(f"<p style='color: {BRAND['text_secondary']}; font-size: 0.75rem;'>RentRoll AI Analyzer v1.0</p>", unsafe_allow_html=True)

# Apply filters
mask = (
    df["property"].isin(sel_properties)
    & df["unit_type"].isin(sel_types)
    & df["status"].isin(sel_status)
    & df["exp_bucket"].isin(sel_buckets)
)
fdf = df[mask].copy()

if len(fdf) == 0:
    st.warning("No data matches the current filters. Adjust sidebar selections.")
    st.stop()

# Compute KPIs
kpis = compute_kpis(fdf)


# ─────────────────────────────────────────────
# KPI DASHBOARD CARDS
# ─────────────────────────────────────────────

def kpi_card(label, value, sub="", css_class="kpi-accent"):
    return f"""
    <div class="kpi-card {css_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>
    """


wale_display = f"{kpis['wale_months']:.1f} mo" if kpis["wale_months"] else "N/A"
wale_sub = f"({kpis['wale_months']/12:.1f} yrs)" if kpis["wale_months"] else ""
sqft_display = f"${kpis['avg_rent_sqft']:.2f}" if kpis["avg_rent_sqft"] else "N/A"
ltl_display = f"{kpis['ltl_pct']:.1f}%" if kpis["ltl_pct"] is not None else "N/A"

occ_class = "kpi-success" if kpis["occupancy_pct"] >= 90 else ("kpi-warning" if kpis["occupancy_pct"] >= 80 else "kpi-danger")

cards_html = f"""
<div class="kpi-grid">
    {kpi_card("Physical Occupancy", f"{kpis['occupancy_pct']:.1f}%", f"{kpis['occupied']}/{kpis['total_units']} units", occ_class)}
    {kpi_card("Economic Occupancy", f"{kpis['economic_occ']:.1f}%", f"EGR / GPR", "kpi-accent")}
    {kpi_card("GPR (Annual)", f"${kpis['gpr_annual']:,.0f}", f"${kpis['gpr_monthly']:,.0f}/mo", "kpi-accent")}
    {kpi_card("EGR (Monthly)", f"${kpis['egr_monthly']:,.0f}", f"${kpis['egr_monthly']*12:,.0f}/yr", "kpi-accent")}
    {kpi_card("Avg Rent / Unit", f"${kpis['avg_rent_unit']:,.0f}", "occupied units", "kpi-accent")}
    {kpi_card("Avg Rent / SqFt", sqft_display, "annual basis", "kpi-accent")}
    {kpi_card("WALE", wale_display, wale_sub, "kpi-warning" if kpis['wale_months'] and kpis['wale_months'] < 24 else "kpi-success")}
    {kpi_card("Loss-to-Lease", ltl_display, "mark-to-market gap", "kpi-warning" if kpis['ltl_pct'] and kpis['ltl_pct'] > 5 else "kpi-success")}
    {kpi_card("Expiring 12 Mo", str(kpis['exp_12']), f"of {kpis['occupied']} occupied", "kpi-danger" if kpis['exp_12'] > kpis['occupied'] * 0.25 else "kpi-warning")}
    {kpi_card("Expiring 24 Mo", str(kpis['exp_24']), "", "kpi-warning")}
    {kpi_card("Expiring 36 Mo", str(kpis['exp_36']), "", "kpi-accent")}
    {kpi_card("Vacant Units", str(kpis['vacant']), f"of {kpis['total_units']} total", "kpi-danger" if kpis['vacant'] > 0 else "kpi-success")}
</div>
"""
st.markdown(cards_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Summary & Charts",
    "📋 Rent Roll Table",
    "⚠️ Concentration & Risk",
    "🤖 AI Insights",
    "🚤 Seasonal Timing",
])


# ── TAB 1: Summary & Charts ─────────────────

with tab1:
    # Download KPI summary
    kpi_df = kpi_to_dataframe(kpis)
    col_dl1, col_dl2, _ = st.columns([1, 1, 3])
    with col_dl1:
        st.download_button(
            "📥 Download KPIs (Excel)",
            data=to_excel_download(kpi_df, "KPI Summary"),
            file_name=f"kpi_summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # Chart grid
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(make_lease_expiration_chart(fdf), use_container_width=True)
    with c2:
        st.plotly_chart(make_rent_distribution_chart(fdf), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(make_occupancy_pie(fdf), use_container_width=True)
    with c4:
        st.plotly_chart(make_rent_vs_sqft_scatter(fdf), use_container_width=True)

    # Revenue by type
    if len(fdf["unit_type"].unique()) > 1:
        st.plotly_chart(make_revenue_by_type_chart(fdf), use_container_width=True)


# ── TAB 2: Rent Roll Table ──────────────────

with tab2:
    st.markdown('<div class="section-header">Full Rent Roll — Interactive Table</div>', unsafe_allow_html=True)

    # Prep display dataframe
    display_df = fdf.copy()
    display_df["monthly_rent"] = display_df["monthly_rent"].round(2)
    display_df["annual_rent"] = display_df["annual_rent"].round(2)
    display_df["market_rent"] = display_df["market_rent"].round(2)
    display_df["loss_to_lease"] = display_df["loss_to_lease"].round(2)
    if display_df["rent_per_sqft"].notna().any():
        display_df["rent_per_sqft"] = display_df["rent_per_sqft"].round(2)
    if display_df["months_remaining"].notna().any():
        display_df["months_remaining"] = display_df["months_remaining"].round(1)

    # Format dates as strings for display
    for dc in ["lease_start", "lease_end"]:
        display_df[dc] = display_df[dc].dt.strftime("%Y-%m-%d").fillna("")

    col_order = [
        "property", "unit", "tenant", "unit_type", "status",
        "monthly_rent", "annual_rent", "market_rent", "loss_to_lease",
        "sqft", "rent_per_sqft",
        "lease_start", "lease_end", "months_remaining", "exp_bucket",
    ]
    col_order = [c for c in col_order if c in display_df.columns]
    display_df = display_df[col_order]

    # Column name prettify
    pretty_names = {
        "property": "Property",
        "unit": "Unit",
        "tenant": "Tenant",
        "unit_type": "Type",
        "status": "Status",
        "monthly_rent": "Monthly Rent",
        "annual_rent": "Annual Rent",
        "market_rent": "Market Rent",
        "loss_to_lease": "Loss-to-Lease",
        "sqft": "SqFt",
        "rent_per_sqft": "Rent/SqFt",
        "lease_start": "Lease Start",
        "lease_end": "Lease End",
        "months_remaining": "Mo. Remaining",
        "exp_bucket": "Exp. Bucket",
    }
    display_df = display_df.rename(columns=pretty_names)

    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_default_column(
        filterable=True,
        sortable=True,
        resizable=True,
        wrapText=False,
    )
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=25)
    gb.configure_side_bar()

    # Currency formatting
    for col in ["Monthly Rent", "Annual Rent", "Market Rent", "Loss-to-Lease", "Rent/SqFt"]:
        if col in display_df.columns:
            gb.configure_column(col, type=["numericColumn", "numberColumnFilter"],
                                valueFormatter="'$' + (x !== null && x !== undefined ? Number(x).toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0}) : '')")

    grid_options = gb.build()
    grid_options["domLayout"] = "normal"

    AgGrid(
        display_df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.NO_UPDATE,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        theme="alpine",
        height=520,
        allow_unsafe_jscode=True,
    )

    # Download
    c_dl1, c_dl2, _ = st.columns([1, 1, 3])
    with c_dl1:
        st.download_button(
            "📥 Download Rent Roll (Excel)",
            data=to_excel_download(display_df, "Rent Roll"),
            file_name=f"rent_roll_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with c_dl2:
        csv_bytes = display_df.to_csv(index=False).encode()
        st.download_button(
            "📥 Download Rent Roll (CSV)",
            data=csv_bytes,
            file_name=f"rent_roll_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )


# ── TAB 3: Tenant Concentration & Risk ──────

with tab3:
    occupied = fdf[fdf["status"] == "Occupied"]
    total_rev = occupied["monthly_rent"].sum()

    if total_rev > 0:
        st.markdown('<div class="section-header">Top Tenants by Revenue Share</div>', unsafe_allow_html=True)

        by_tenant = (
            occupied.groupby("tenant")
            .agg(
                units=("unit", "count"),
                monthly_rent=("monthly_rent", "sum"),
                avg_rent=("monthly_rent", "mean"),
                total_sqft=("sqft", lambda x: x.sum() if x.notna().any() else 0),
            )
            .sort_values("monthly_rent", ascending=False)
        )
        by_tenant["pct_revenue"] = by_tenant["monthly_rent"] / total_rev * 100
        by_tenant["cumulative_pct"] = by_tenant["pct_revenue"].cumsum()

        # Top 10 table
        top_n = min(10, len(by_tenant))
        top_df = by_tenant.head(top_n).reset_index()
        top_df.columns = ["Tenant", "Units", "Monthly Rent", "Avg Rent/Unit", "Total SqFt", "% of Revenue", "Cumulative %"]
        top_df["Monthly Rent"] = top_df["Monthly Rent"].apply(lambda x: f"${x:,.0f}")
        top_df["Avg Rent/Unit"] = top_df["Avg Rent/Unit"].apply(lambda x: f"${x:,.0f}")
        top_df["Total SqFt"] = top_df["Total SqFt"].apply(lambda x: f"{x:,.0f}" if x > 0 else "—")
        top_df["% of Revenue"] = top_df["% of Revenue"].apply(lambda x: f"{x:.1f}%")
        top_df["Cumulative %"] = top_df["Cumulative %"].apply(lambda x: f"{x:.1f}%")

        st.dataframe(top_df, use_container_width=True, hide_index=True)

        # Concentration chart
        chart_data = by_tenant.head(top_n).reset_index()
        fig_conc = go.Figure()
        fig_conc.add_trace(go.Bar(
            x=chart_data["tenant"],
            y=chart_data["pct_revenue"],
            marker_color=CHART_COLORS[:top_n],
            text=chart_data["pct_revenue"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside",
        ))
        fig_conc.update_layout(
            **CHART_LAYOUT,
            title=dict(text=f"Top {top_n} Tenants — Revenue Concentration", font=dict(size=15)),
            yaxis_title="% of Total Revenue",
            xaxis_tickangle=-30,
            height=400,
            showlegend=False,
        )
        st.plotly_chart(fig_conc, use_container_width=True)

        # Below-market flags
        if fdf["market_rent"].notna().any():
            st.markdown('<div class="section-header">Below-Market Flags</div>', unsafe_allow_html=True)

            below_market = occupied[
                (occupied["market_rent"] > 0)
                & (occupied["monthly_rent"] < occupied["market_rent"] * 0.90)
            ].copy()

            if len(below_market) > 0:
                below_market["gap_pct"] = (
                    (below_market["market_rent"] - below_market["monthly_rent"])
                    / below_market["market_rent"] * 100
                )
                below_market = below_market.sort_values("gap_pct", ascending=False)

                bm_display = below_market[["unit", "tenant", "monthly_rent", "market_rent", "gap_pct", "lease_end"]].copy()
                bm_display.columns = ["Unit", "Tenant", "Current Rent", "Market Rent", "Gap %", "Lease End"]
                bm_display["Current Rent"] = bm_display["Current Rent"].apply(lambda x: f"${x:,.0f}")
                bm_display["Market Rent"] = bm_display["Market Rent"].apply(lambda x: f"${x:,.0f}")
                bm_display["Gap %"] = bm_display["Gap %"].apply(lambda x: f"{x:.1f}%")
                bm_display["Lease End"] = bm_display["Lease End"].dt.strftime("%Y-%m-%d").fillna("—")

                st.dataframe(bm_display, use_container_width=True, hide_index=True)

                total_gap = below_market["loss_to_lease"].sum()
                st.markdown(
                    f"<p style='color: {BRAND['warning']}; font-weight: 600;'>"
                    f"Total Below-Market Gap: ${total_gap:,.0f}/mo (${total_gap*12:,.0f}/yr) across {len(below_market)} units</p>",
                    unsafe_allow_html=True,
                )
            else:
                st.success("No units are significantly below market (>10% gap).")
        else:
            st.info("No market rent data provided. Add a 'Market Rent' column to enable below-market analysis.")

        # Download
        st.download_button(
            "📥 Download Concentration Report (Excel)",
            data=to_excel_download(by_tenant.reset_index(), "Tenant Concentration"),
            file_name=f"tenant_concentration_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("No occupied units with revenue data to analyze.")


# ── TAB 4: AI Insights ──────────────────────

with tab4:
    st.markdown('<div class="section-header">AI-Generated Investment Insights</div>', unsafe_allow_html=True)

    insights = generate_insights(fdf, kpis)

    if insights:
        for i, insight in enumerate(insights):
            st.markdown(
                f'<div class="ai-insight">{insight}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("Upload a more detailed rent roll (with lease dates and market rents) for richer AI insights.")

    # Summary box
    st.markdown(f"""
    <div style="
        background: {BRAND['bg_card']};
        border: 1px solid {BRAND['border']};
        border-radius: 10px;
        padding: 1.5rem;
        margin-top: 1rem;
    ">
        <h4 style="color: {BRAND['accent']}; margin-bottom: 0.75rem;">Executive Summary</h4>
        <p style="color: {BRAND['text_primary']}; line-height: 1.7;">
            This rent roll contains <strong>{kpis['total_units']}</strong> units across
            <strong>{len(fdf['property'].unique())}</strong> property/properties,
            with <strong>{kpis['occupancy_pct']:.1f}%</strong> physical occupancy
            and <strong>${kpis['egr_monthly']:,.0f}/mo</strong> in effective gross revenue.
            {"WALE is " + f"{kpis['wale_months']:.1f} months ({kpis['wale_months']/12:.1f} yrs)." if kpis['wale_months'] else "Lease expiration data not fully available."}
            {f"Loss-to-lease stands at {kpis['ltl_pct']:.1f}%, representing mark-to-market upside." if kpis['ltl_pct'] and kpis['ltl_pct'] > 2 else ""}
            {f"There are {kpis['exp_12']} leases expiring in the next 12 months requiring renewal attention." if kpis['exp_12'] > 0 else ""}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Download insights as text
    insights_text = "RentRoll AI Analyzer — Investment Insights\n"
    insights_text += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    insights_text += "=" * 60 + "\n\n"
    for insight in insights:
        clean = insight.replace("**", "")
        insights_text += clean + "\n\n"

    st.download_button(
        "📥 Download Insights (TXT)",
        data=insights_text.encode(),
        file_name=f"ai_insights_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
    )


# ── TAB 5: Seasonal Timing (Marina) ─────────

with tab5:
    st.markdown('<div class="section-header">Marina Seasonal Revenue Timing</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <p style="color: {BRAND['text_secondary']}; font-size: 0.9rem; margin-bottom: 1rem;">
        Analyzes lease start/end dates to model monthly revenue recognition, occupancy curves, and
        seasonal rollover exposure. Essential for marina underwriting where leases cluster around
        spring launch and fall haul-out cycles.
    </p>
    """, unsafe_allow_html=True)

    occupied = fdf[fdf["status"] == "Occupied"].copy()
    has_dates = occupied[occupied["lease_start"].notna() & occupied["lease_end"].notna()].copy()

    if len(has_dates) < 3:
        st.warning(
            "Not enough lease date data to build seasonal analysis. "
            "Ensure your rent roll includes Lease Start and Lease End columns."
        )
    else:
        # ── Monthly revenue recognition model ──
        # For each occupied unit with dates, determine which months of the year
        # the lease is active and allocate monthly rent to those months.
        # This shows the "cash curve" across a calendar year.

        MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        def lease_active_months(row):
            """Return set of month numbers (1-12) the lease covers in any year."""
            start = row["lease_start"]
            end = row["lease_end"]
            if pd.isna(start) or pd.isna(end):
                return set(range(1, 13))  # assume year-round if no dates
            months = set()
            current = start.replace(day=1)
            end_ceil = end.replace(day=1)
            while current <= end_ceil:
                months.add(current.month)
                # advance one month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
            return months

        has_dates["active_months"] = has_dates.apply(lease_active_months, axis=1)

        # Build month-by-month revenue and unit count
        monthly_data = []
        for mo in range(1, 13):
            active = has_dates[has_dates["active_months"].apply(lambda s: mo in s)]
            monthly_data.append({
                "month_num": mo,
                "month": MONTH_NAMES[mo - 1],
                "units": len(active),
                "revenue": active["monthly_rent"].sum(),
                "avg_rent": active["monthly_rent"].mean() if len(active) > 0 else 0,
            })

        month_df = pd.DataFrame(monthly_data)
        peak_rev = month_df["revenue"].max()
        month_df["pct_of_peak"] = (month_df["revenue"] / peak_rev * 100) if peak_rev > 0 else 0
        total_units_with_dates = len(has_dates)
        month_df["occupancy_pct"] = month_df["units"] / total_units_with_dates * 100

        # ── Seasonal KPI cards ──
        peak_month = month_df.loc[month_df["revenue"].idxmax()]
        trough_month = month_df.loc[month_df["revenue"].idxmin()]
        seasonality_ratio = (trough_month["revenue"] / peak_month["revenue"] * 100) if peak_month["revenue"] > 0 else 100
        annual_modeled = month_df["revenue"].sum()

        # Identify peak season (consecutive months above 80% of peak)
        above_80 = month_df[month_df["pct_of_peak"] >= 80]["month"].tolist()
        peak_season_str = f"{above_80[0]}–{above_80[-1]}" if len(above_80) >= 2 else "Year-round"

        # Lease start clustering
        start_months = has_dates["lease_start"].dt.month.value_counts().sort_index()
        top_start_mo = start_months.idxmax() if len(start_months) > 0 else None
        top_start_count = start_months.max() if len(start_months) > 0 else 0

        # Lease end clustering
        end_months = has_dates["lease_end"].dt.month.value_counts().sort_index()
        top_end_mo = end_months.idxmax() if len(end_months) > 0 else None
        top_end_count = end_months.max() if len(end_months) > 0 else 0

        seasonal_cards = f"""
        <div class="kpi-grid">
            {kpi_card("Peak Month", peak_month['month'], f"${peak_month['revenue']:,.0f} / {int(peak_month['units'])} units", "kpi-success")}
            {kpi_card("Trough Month", trough_month['month'], f"${trough_month['revenue']:,.0f} / {int(trough_month['units'])} units", "kpi-danger")}
            {kpi_card("Trough/Peak Ratio", f"{seasonality_ratio:.0f}%", "100% = no seasonality", "kpi-warning" if seasonality_ratio < 70 else "kpi-success")}
            {kpi_card("Peak Season", peak_season_str, "months ≥80% of peak rev", "kpi-accent")}
            {kpi_card("Modeled Annual Rev", f"${annual_modeled:,.0f}", "sum of monthly model", "kpi-accent")}
            {kpi_card("Top Start Month", f"{MONTH_NAMES[top_start_mo - 1] if top_start_mo else 'N/A'}", f"{top_start_count} leases start", "kpi-accent")}
            {kpi_card("Top End Month", f"{MONTH_NAMES[top_end_mo - 1] if top_end_mo else 'N/A'}", f"{top_end_count} leases end", "kpi-warning")}
            {kpi_card("Year-Round Leases", str(len(has_dates[has_dates['active_months'].apply(lambda s: len(s) >= 12)])), f"of {total_units_with_dates} w/ dates", "kpi-success")}
        </div>
        """
        st.markdown(seasonal_cards, unsafe_allow_html=True)

        # ── Chart 1: Monthly Revenue Curve ──
        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(
            x=month_df["month"],
            y=month_df["revenue"],
            marker_color=[
                BRAND["success"] if row["pct_of_peak"] >= 80
                else BRAND["warning"] if row["pct_of_peak"] >= 50
                else BRAND["danger"]
                for _, row in month_df.iterrows()
            ],
            text=month_df["revenue"].apply(lambda x: f"${x:,.0f}"),
            textposition="outside",
            name="Revenue",
            yaxis="y",
        ))
        fig_rev.add_trace(go.Scatter(
            x=month_df["month"],
            y=month_df["occupancy_pct"],
            mode="lines+markers",
            line=dict(color=BRAND["accent"], width=2.5),
            marker=dict(size=7),
            name="Occupancy %",
            yaxis="y2",
        ))
        fig_rev.update_layout(
            **CHART_LAYOUT,
            title=dict(text="Monthly Revenue Curve & Occupancy", font=dict(size=15)),
            yaxis=dict(title="Monthly Revenue ($)", side="left", showgrid=False),
            yaxis2=dict(
                title="Occupancy %", side="right", overlaying="y",
                range=[0, 110], showgrid=False,
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=420,
            barmode="group",
        )
        st.plotly_chart(fig_rev, use_container_width=True)

        # ── Chart 2: Lease Start & End Clustering ──
        start_fill = start_months.reindex(range(1, 13), fill_value=0)
        end_fill = end_months.reindex(range(1, 13), fill_value=0)

        fig_cluster = go.Figure()
        fig_cluster.add_trace(go.Bar(
            x=MONTH_NAMES,
            y=start_fill.values,
            name="Lease Starts",
            marker_color=BRAND["success"],
            opacity=0.85,
        ))
        fig_cluster.add_trace(go.Bar(
            x=MONTH_NAMES,
            y=end_fill.values,
            name="Lease Ends",
            marker_color=BRAND["danger"],
            opacity=0.85,
        ))
        fig_cluster.update_layout(
            **CHART_LAYOUT,
            title=dict(text="Lease Start & End Clustering by Month", font=dict(size=15)),
            yaxis_title="# of Leases",
            barmode="group",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=380,
        )
        st.plotly_chart(fig_cluster, use_container_width=True)

        # ── Chart 3: Revenue at Risk by Expiration Month ──
        # Show the next 18 months of lease expirations with dollars at risk
        today = pd.Timestamp.today().normalize()
        future_exp = has_dates[
            (has_dates["lease_end"] >= today)
            & (has_dates["lease_end"] <= today + timedelta(days=548))
        ].copy()

        if len(future_exp) > 0:
            future_exp["exp_month"] = future_exp["lease_end"].dt.to_period("M")
            exp_by_month = future_exp.groupby("exp_month").agg(
                units=("unit", "count"),
                revenue_at_risk=("monthly_rent", "sum"),
            ).sort_index()

            # Create continuous 18-month index
            all_months = pd.period_range(
                start=today.to_period("M"),
                periods=18,
                freq="M",
            )
            exp_by_month = exp_by_month.reindex(all_months, fill_value=0)
            exp_by_month["cumulative_rev"] = exp_by_month["revenue_at_risk"].cumsum()
            exp_by_month["label"] = exp_by_month.index.strftime("%b %Y")

            fig_risk = make_subplots(specs=[[{"secondary_y": True}]])
            fig_risk.add_trace(
                go.Bar(
                    x=exp_by_month["label"],
                    y=exp_by_month["revenue_at_risk"],
                    marker_color=[
                        BRAND["danger"] if i < 6
                        else BRAND["warning"] if i < 12
                        else BRAND["accent"]
                        for i in range(len(exp_by_month))
                    ],
                    text=exp_by_month["units"].apply(lambda x: f"{int(x)} units" if x > 0 else ""),
                    textposition="outside",
                    name="Monthly Rev at Risk",
                ),
                secondary_y=False,
            )
            fig_risk.add_trace(
                go.Scatter(
                    x=exp_by_month["label"],
                    y=exp_by_month["cumulative_rev"],
                    mode="lines+markers",
                    line=dict(color="#EC4899", width=2.5, dash="dot"),
                    marker=dict(size=6),
                    name="Cumulative Exposure",
                ),
                secondary_y=True,
            )
            fig_risk.update_layout(
                **CHART_LAYOUT,
                title=dict(text="18-Month Rolling Expiration Exposure", font=dict(size=15)),
                height=420,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            fig_risk.update_yaxes(title_text="Monthly Revenue at Risk ($)", secondary_y=False, showgrid=False)
            fig_risk.update_yaxes(title_text="Cumulative ($)", secondary_y=True, showgrid=False)
            st.plotly_chart(fig_risk, use_container_width=True)
        else:
            st.info("No lease expirations in the next 18 months.")

        # ── Chart 4: Heatmap by Property x Month (if multi-property) ──
        if len(has_dates["property"].unique()) > 1:
            st.markdown('<div class="section-header">Revenue Heatmap — Property × Month</div>', unsafe_allow_html=True)

            heatmap_data = []
            for prop in sorted(has_dates["property"].unique()):
                prop_df = has_dates[has_dates["property"] == prop]
                for mo in range(1, 13):
                    active = prop_df[prop_df["active_months"].apply(lambda s: mo in s)]
                    heatmap_data.append({
                        "property": prop,
                        "month": MONTH_NAMES[mo - 1],
                        "month_num": mo,
                        "revenue": active["monthly_rent"].sum(),
                    })
            heat_df = pd.DataFrame(heatmap_data)
            heat_pivot = heat_df.pivot(index="property", columns="month_num", values="revenue").fillna(0)
            heat_pivot.columns = MONTH_NAMES

            fig_heat = go.Figure(go.Heatmap(
                z=heat_pivot.values,
                x=heat_pivot.columns.tolist(),
                y=heat_pivot.index.tolist(),
                colorscale=[
                    [0, "#1A2332"],
                    [0.3, "#1E3A5F"],
                    [0.6, "#2D8CFF"],
                    [0.8, "#10B981"],
                    [1.0, "#F59E0B"],
                ],
                text=[[f"${v:,.0f}" for v in row] for row in heat_pivot.values],
                texttemplate="%{text}",
                textfont=dict(size=10),
                hovertemplate="<b>%{y}</b><br>%{x}: $%{z:,.0f}<extra></extra>",
                colorbar=dict(title="Revenue"),
            ))
            fig_heat.update_layout(
                **CHART_LAYOUT,
                title=dict(text="Revenue by Property & Month", font=dict(size=15)),
                height=50 + 60 * len(heat_pivot),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_heat, use_container_width=True)

        # ── Seasonal Insights ──
        st.markdown('<div class="section-header">Seasonal Timing Insights</div>', unsafe_allow_html=True)

        seasonal_insights = []

        # Seasonality severity
        if seasonality_ratio < 50:
            seasonal_insights.append(
                f"**Heavy Seasonality:** Trough-to-peak ratio is {seasonality_ratio:.0f}%, meaning "
                f"off-season revenue drops by more than half. Underwrite with seasonal cash flow "
                f"assumptions, not straight-line annualization. Model debt service coverage at "
                f"trough months ({trough_month['month']}) to stress test loan covenants."
            )
        elif seasonality_ratio < 75:
            seasonal_insights.append(
                f"**Moderate Seasonality:** {seasonality_ratio:.0f}% trough-to-peak ratio indicates "
                f"meaningful seasonal swing. Operating expense timing (insurance renewals, seasonal "
                f"staffing) should be mapped against the revenue curve to identify cash pinch months."
            )
        else:
            seasonal_insights.append(
                f"**Low Seasonality:** {seasonality_ratio:.0f}% trough-to-peak ratio suggests relatively "
                f"stable year-round revenue. This supports straight-line underwriting and reduces "
                f"working capital reserve requirements."
            )

        # Lease clustering risk
        if top_end_mo and top_end_count > total_units_with_dates * 0.25:
            seasonal_insights.append(
                f"**Lease End Clustering:** {top_end_count} leases ({top_end_count/total_units_with_dates*100:.0f}%) "
                f"expire in {MONTH_NAMES[top_end_mo - 1]}, creating concentrated renewal risk. "
                f"If renewal rates drop below assumption, the revenue hit is front-loaded into a "
                f"single month. Consider staggering lease terms on renewal to de-risk the roll."
            )

        if top_start_mo and top_start_count > total_units_with_dates * 0.25:
            seasonal_insights.append(
                f"**Lease Start Clustering:** {top_start_count} leases begin in "
                f"{MONTH_NAMES[top_start_mo - 1]}, likely aligned with spring launch season. "
                f"This is typical for seasonal marinas but means marketing and slip prep must "
                f"be completed 60-90 days prior to capture demand."
            )

        # Off-season vacancy
        off_season_months = month_df[month_df["pct_of_peak"] < 60]
        if len(off_season_months) >= 3:
            off_rev_lost = peak_rev * len(off_season_months) - off_season_months["revenue"].sum()
            off_names = ", ".join(off_season_months["month"].tolist())
            seasonal_insights.append(
                f"**Off-Season Gap:** {len(off_season_months)} months ({off_names}) operate below "
                f"60% of peak revenue. The annualized gap vs. peak-rate operation is approximately "
                f"${off_rev_lost:,.0f}. Evaluate dry storage conversions, winter liveaboard programs, "
                f"or event rental income to backfill off-season revenue."
            )

        # Year-round vs seasonal mix
        yr_round = len(has_dates[has_dates["active_months"].apply(lambda s: len(s) >= 12)])
        seasonal_only = total_units_with_dates - yr_round
        if yr_round > 0 and seasonal_only > 0:
            seasonal_insights.append(
                f"**Lease Mix:** {yr_round} year-round leases provide a ${has_dates[has_dates['active_months'].apply(lambda s: len(s) >= 12)]['monthly_rent'].sum():,.0f}/mo "
                f"base layer, while {seasonal_only} seasonal leases add incremental peak-season revenue. "
                f"The year-round base covers {has_dates[has_dates['active_months'].apply(lambda s: len(s) >= 12)]['monthly_rent'].sum() / peak_rev * 100:.0f}% "
                f"of peak month revenue."
            )

        # 18-month cumulative exposure
        if len(future_exp) > 0:
            total_exposure = future_exp["monthly_rent"].sum()
            pct_of_egr = total_exposure / kpis["egr_monthly"] * 100 if kpis["egr_monthly"] > 0 else 0
            seasonal_insights.append(
                f"**18-Month Rollover Exposure:** ${total_exposure:,.0f}/mo in lease revenue "
                f"({pct_of_egr:.0f}% of current EGR) expires within 18 months. Map each expiration "
                f"against local boating season timing to estimate realistic renewal windows."
            )

        for insight in seasonal_insights:
            st.markdown(
                f'<div class="ai-insight">{insight}</div>',
                unsafe_allow_html=True,
            )

        # ── Monthly detail table ──
        st.markdown('<div class="section-header">Monthly Revenue Detail</div>', unsafe_allow_html=True)

        month_display = month_df.copy()
        month_display["revenue"] = month_display["revenue"].apply(lambda x: f"${x:,.0f}")
        month_display["avg_rent"] = month_display["avg_rent"].apply(lambda x: f"${x:,.0f}")
        month_display["pct_of_peak"] = month_display["pct_of_peak"].apply(lambda x: f"{x:.0f}%")
        month_display["occupancy_pct"] = month_display["occupancy_pct"].apply(lambda x: f"{x:.1f}%")
        month_display = month_display.rename(columns={
            "month": "Month",
            "units": "Active Units",
            "revenue": "Monthly Revenue",
            "avg_rent": "Avg Rent",
            "pct_of_peak": "% of Peak",
            "occupancy_pct": "Occupancy %",
        })
        month_display = month_display[["Month", "Active Units", "Monthly Revenue", "Avg Rent", "% of Peak", "Occupancy %"]]

        st.dataframe(month_display, use_container_width=True, hide_index=True)

        # Download
        export_month = month_df.copy()
        export_month = export_month.rename(columns={
            "month": "Month", "units": "Active Units", "revenue": "Monthly Revenue",
            "avg_rent": "Avg Rent/Unit", "pct_of_peak": "% of Peak Revenue",
            "occupancy_pct": "Seasonal Occupancy %",
        })
        export_month = export_month[["Month", "Active Units", "Monthly Revenue", "Avg Rent/Unit", "% of Peak Revenue", "Seasonal Occupancy %"]]

        st.download_button(
            "📥 Download Seasonal Analysis (Excel)",
            data=to_excel_download(export_month, "Seasonal Timing"),
            file_name=f"seasonal_timing_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
