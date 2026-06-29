"""
Dashboard Page — Results Visualization

Renders a rich, scannable verification dashboard. The page's job:
give a researcher an at-a-glance read of every claim's outcome and
let them drill into the numbers without leaving the page.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional

# ── Status configuration dictionary ──────────────────────────────────────────
# This dictionary maps internal status keys to their display labels, colors,
# background colors, and icons for the entire application.
_STATUS: Dict[str, Dict[str, str]] = {
    "reproduced": {
        "label": "Reproduced",
        "color": "#10B981",
        "bg": "rgba(16, 185, 129, 0.12)",
        "icon": "✓",
    },
    "marginal": {
        "label": "Marginal",
        "color": "#F59E0B",
        "bg": "rgba(245, 158, 11, 0.12)",
        "icon": "~",
    },
    "not_reproduced": {
        "label": "Not Reproduced",
        "color": "#EF4444",
        "bg": "rgba(239, 68, 68, 0.12)",
        "icon": "✗",
    },
    "could_not_verify": {
        "label": "Could Not Verify",
        "color": "#8B95A9",
        "bg": "rgba(139, 149, 169, 0.12)",
        "icon": "?",
    },
}

# ── Comprehensive Custom CSS for a 10/10 Aesthetic ──────────────────────────
_CSS: str = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* Global Reset and Typography */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: #0B0F19 !important;
    color: #E2E8F0 !important;
}

/* Main App Background */
.stApp {
    background: #0B0F19;
}

/* ── Glassmorphism Utility Classes ── */
.glass-panel {
    background: rgba(255, 255, 255, 0.03) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 20px !important;
    padding: 20px !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.glass-panel:hover {
    border-color: rgba(255, 255, 255, 0.15) !important;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.6) !important;
}

/* ── Page Header ── */
.page-header {
    display: flex !important;
    align-items: center !important;
    gap: 20px !important;
    margin-bottom: 32px !important;
    padding-bottom: 24px !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
}

.header-icon-wrapper {
    width: 56px !important;
    height: 56px !important;
    flex-shrink: 0 !important;
    background: linear-gradient(135deg, #7C3AED, #5B4FE8) !important;
    border-radius: 16px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 26px !important;
    box-shadow: 0 8px 32px rgba(91, 79, 232, 0.3) !important;
}

.header-title {
    font-size: 28px !important;
    font-weight: 800 !important;
    color: #F8FAFC !important;
    margin: 0 !important;
    line-height: 1.1 !important;
    letter-spacing: -0.03em !important;
}

.header-subtitle {
    font-size: 13px !important;
    color: #94A3B8 !important;
    margin-top: 4px !important;
    font-weight: 400 !important;
}

/* ── Score Hero Card ── */
.score-hero {
    background: linear-gradient(135deg, rgba(91, 79, 232, 0.15) 0%, rgba(124, 58, 237, 0.08) 100%) !important;
    border: 1px solid rgba(91, 79, 232, 0.25) !important;
    border-radius: 24px !important;
    padding: 32px 36px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    margin-bottom: 28px !important;
    position: relative !important;
    overflow: hidden !important;
}

.score-hero::before {
    content: '' !important;
    position: absolute !important;
    top: -80px !important;
    right: -80px !important;
    width: 300px !important;
    height: 300px !important;
    background: radial-gradient(circle, rgba(91, 79, 232, 0.2) 0%, transparent 70%) !important;
    pointer-events: none !important;
}

.score-number {
    font-size: 64px !important;
    font-weight: 800 !important;
    line-height: 1 !important;
    color: #F8FAFC !important;
    letter-spacing: -0.04em !important;
}

.score-pct {
    font-size: 32px !important;
    font-weight: 300 !important;
    color: #7C3AED !important;
}

.score-label {
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: #64748B !important;
    margin-top: 8px !important;
}

.score-note {
    font-size: 13px !important;
    color: #CBD5E1 !important;
    max-width: 360px !important;
    line-height: 1.7 !important;
    text-align: right !important;
}

/* ── KPI Strip ── */
.kpi-grid {
    display: grid !important;
    grid-template-columns: repeat(4, 1fr) !important;
    gap: 16px !important;
    margin-bottom: 32px !important;
}

.kpi-card {
    padding: 24px !important;
    position: relative !important;
    overflow: hidden !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.kpi-card:hover {
    transform: translateY(-4px) !important;
}

.kpi-accent {
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: 4px !important;
    border-radius: 20px 20px 0 0 !important;
}

.kpi-title {
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}

.kpi-number {
    font-size: 36px !important;
    font-weight: 700 !important;
    line-height: 1 !important;
    margin-top: 10px !important;
    letter-spacing: -0.02em !important;
}

.kpi-subtitle {
    font-size: 11px !important;
    color: #64748B !important;
    margin-top: 6px !important;
    font-weight: 500 !important;
}

.kpi-progress-bar {
    height: 4px !important;
    border-radius: 4px !important;
    margin-top: 16px !important;
    background: rgba(255, 255, 255, 0.06) !important;
    overflow: hidden !important;
}

.kpi-progress-fill {
    height: 100% !important;
    border-radius: 4px !important;
    transition: width 1s cubic-bezier(0.22, 1, 0.36, 1) !important;
}

/* ── Section Divider ── */
.section-divider {
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    color: #475569 !important;
    margin: 36px 0 18px !important;
    display: flex !important;
    align-items: center !important;
    gap: 14px !important;
}

.section-divider::after {
    content: '' !important;
    flex: 1 !important;
    height: 1px !important;
    background: rgba(255, 255, 255, 0.06) !important;
}

/* ── Callout / Notification Box ── */
.callout-box {
    background: rgba(245, 158, 11, 0.08) !important;
    border: 1px solid rgba(245, 158, 11, 0.15) !important;
    border-radius: 14px !important;
    padding: 16px 22px !important;
    font-size: 13px !important;
    color: #FCD34D !important;
    line-height: 1.7 !important;
    margin-bottom: 28px !important;
}

.callout-box b {
    font-weight: 700 !important;
}

/* ── Native Streamlit Dataframe Override ── */
[data-testid="stDataFrame"] {
    background: transparent !important;
}

[data-testid="stDataFrame"] table {
    border-collapse: separate !important;
    border-spacing: 0 8px !important;
}

[data-testid="stDataFrame"] thead tr th {
    background: rgba(255, 255, 255, 0.04) !important;
    color: #94A3B8 !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
    padding: 14px 18px !important;
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stDataFrame"] tbody tr td {
    background: rgba(255, 255, 255, 0.02) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
    padding: 14px 18px !important;
    color: #E2E8F0 !important;
    font-size: 13px !important;
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stDataFrame"] tbody tr:hover td {
    background: rgba(255, 255, 255, 0.05) !important;
    transition: background 0.2s ease !important;
}

[data-testid="stDataFrame"] tbody tr td:first-child {
    border-top-left-radius: 12px !important;
    border-bottom-left-radius: 12px !important;
}

[data-testid="stDataFrame"] tbody tr td:last-child {
    border-top-right-radius: 12px !important;
    border-bottom-right-radius: 12px !important;
}

/* ── Download Button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #5B4FE8, #7C3AED) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 32px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 20px rgba(91, 79, 232, 0.35) !important;
}

.stDownloadButton > button:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 32px rgba(91, 79, 232, 0.5) !important;
}

.stDownloadButton > button:active {
    transform: translateY(0) !important;
}

/* ── Empty State ── */
.empty-state {
    text-align: center !important;
    padding: 100px 24px !important;
}

.empty-icon {
    font-size: 64px !important;
    margin-bottom: 24px !important;
    opacity: 0.5 !important;
}

.empty-title {
    font-size: 22px !important;
    font-weight: 700 !important;
    color: #CBD5E1 !important;
    margin-bottom: 8px !important;
}

.empty-subtitle {
    font-size: 14px !important;
    color: #64748B !important;
    max-width: 400px !important;
    margin: 0 auto !important;
    line-height: 1.6 !important;
}

/* ── Plotly Override ── */
.js-plotly-plot .plotly {
    background: transparent !important;
}

/* ── Responsive Tweaks ── */
@media (max-width: 768px) {
    .score-hero {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 16px !important;
    }
    .score-note {
        text-align: left !important;
        max-width: 100% !important;
    }
}
</style>
"""


# ── Helper Formatting Functions ─────────────────────────────────────────────

def _fmt_p(v: Any) -> str:
    """
    Safely formats a p-value into a human-readable string.
    
    Handles None, NaN, and edge cases gracefully. Returns '—' for invalid data.
    """
    if v is None:
        return "—"
    try:
        # Convert to float if it's a string or pandas numeric
        v_float = float(v)
        if pd.isna(v_float):
            return "—"
        if v_float < 0.001:
            return "<.001"
        return f"{v_float:.4f}"
    except (ValueError, TypeError):
        return "—"


def _score_color(score: int) -> str:
    """
    Determines the CSS color for the reproducibility score based on its value.
    
    Args:
        score: An integer between 0 and 100.
    
    Returns:
        A hex color string.
    """
    if score >= 75:
        return "#10B981"  # Green
    if score >= 40:
        return "#F59E0B"  # Amber
    return "#EF4444"      # Red


def _truncate_text(text: Any, max_length: int = 75) -> str:
    """
    Truncates a text string to a specific length and appends an ellipsis.
    
    Args:
        text: The input text to truncate.
        max_length: Maximum allowed length.
    
    Returns:
        The truncated string.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "…"


# ── Chart Generation Functions ──────────────────────────────────────────────

def _create_donut_chart(counts: Dict[str, int], total: int) -> go.Figure:
    """
    Generates a clean, glassmorphism-styled donut chart for outcome distribution.
    
    Args:
        counts: Dictionary of status keys to integer counts.
        total: The total number of claims.
    
    Returns:
        A Plotly Figure object.
    """
    # Filter out zero counts for cleaner visual
    present = {k: v for k, v in counts.items() if v > 0}
    labels = [_STATUS[k]["label"] for k in present]
    values = list(present.values())
    colors = [_STATUS[k]["color"] for k in present]

    # Initialize the Pie chart
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.60,
        marker=dict(
            colors=colors,
            line=dict(color="#0B0F19", width=4),
        ),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value} claim(s) — %{percent}<extra></extra>",
        direction="clockwise",
        sort=False,
    ))

    # Add central annotations
    fig.add_annotation(
        text=f"<b style='font-size:34px; color:#F8FAFC;'>{total}</b>",
        x=0.5, y=0.58, showarrow=False,
        font=dict(family="Inter", size=34, color="#F8FAFC"),
    )
    fig.add_annotation(
        text="claims",
        x=0.5, y=0.42, showarrow=False,
        font=dict(family="Inter", size=13, color="#64748B"),
    )

    # Clean layout configuration
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=16, b=16, l=16, r=16),
        height=320,
        showlegend=True,
        legend=dict(
            font=dict(family="Inter", size=12, color="#94A3B8"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            orientation="v",
            x=0.72, y=0.5,
            xanchor="left", yanchor="middle",
        ),
    )
    return fig


def _create_comparison_chart(results: List[Dict]) -> Optional[go.Figure]:
    """
    Generates a grouped horizontal bar chart comparing claimed vs reproduced p-values.
    
    Args:
        results: A list of claim result dictionaries.
    
    Returns:
        A Plotly Figure object, or None if insufficient data exists.
    """
    # Filter for claims that contain BOTH p-values
    valid_rows = []
    for r in results:
        claimed = r.get("claimed_p_value")
        reproduced = r.get("reproduced_p_value")
        try:
            if claimed is not None and not pd.isna(float(claimed)) and \
               reproduced is not None and not pd.isna(float(reproduced)):
                valid_rows.append(r)
        except (ValueError, TypeError):
            continue

    if not valid_rows:
        return None

    # Prepare data arrays
    ids = [r.get("claim_id", f"C{i+1}") for i, r in enumerate(valid_rows)]
    claimed = [float(r["claimed_p_value"]) for r in valid_rows]
    reproduced = [float(r["reproduced_p_value"]) for r in valid_rows]
    statuses = [r.get("status", "could_not_verify") for r in valid_rows]
    bar_colors = [_STATUS[s]["color"] for s in statuses]

    # Initialize Figure
    fig = go.Figure()

    # Claimed P-Value Trace
    fig.add_trace(go.Bar(
        name="Claimed p",
        y=ids, x=claimed,
        orientation="h",
        marker=dict(color="rgba(91, 79, 232, 0.4)", line=dict(color="#5B4FE8", width=1.5)),
        hovertemplate="<b>%{y}</b><br>Claimed p = %{x:.4f}<extra></extra>",
    ))

    # Reproduced P-Value Trace (colored by status)
    fig.add_trace(go.Bar(
        name="Reproduced p",
        y=ids, x=reproduced,
        orientation="h",
        marker=dict(color=bar_colors, opacity=0.85),
        hovertemplate="<b>%{y}</b><br>Reproduced p = %{x:.4f}<extra></extra>",
    ))

    # Clean Layout
    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=16, b=8, l=8, r=16),
        height=max(260, 52 * len(valid_rows)),
        font=dict(family="Inter", color="#94A3B8", size=11),
        legend=dict(
            font=dict(family="Inter", size=11, color="#94A3B8"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            orientation="h", x=0, y=1.08,
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.04)",
            zerolinecolor="rgba(255,255,255,0.08)",
            tickfont=dict(family="JetBrains Mono", size=10),
            title=dict(text="p-value", font=dict(size=10, color="#64748B")),
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(family="JetBrains Mono", size=10),
        ),
    )
    return fig


# ── Dataframe Preparation Function ──────────────────────────────────────────

def _prepare_dataframe(df: pd.DataFrame, claim_lookup: Dict[str, str]) -> pd.DataFrame:
    """
    Cleans, formats, and prepares the raw results dataframe for display.
    
    Args:
        df: Raw pandas DataFrame of results.
        claim_lookup: Dictionary mapping claim IDs to their full text statements.
    
    Returns:
        A fully formatted pandas DataFrame ready for styling.
    """
    df_display = df.copy()

    # 1. Safely map Claim ID to Claim Statement
    df_display["Claim"] = df_display["claim_id"].map(claim_lookup).fillna(df_display["claim_id"])
    df_display["Claim"] = df_display["Claim"].astype(str).apply(_truncate_text)

    # 2. Map Status to Labels and Colors for frontend rendering
    df_display["Status_Label"] = df_display["status"].map(
        lambda x: _STATUS.get(x, _STATUS["could_not_verify"])["label"]
    )
    df_display["Status_Color"] = df_display["status"].map(
        lambda x: _STATUS.get(x, _STATUS["could_not_verify"])["color"]
    )
    df_display["Status_BG"] = df_display["status"].map(
        lambda x: _STATUS.get(x, _STATUS["could_not_verify"])["bg"]
    )

    # 3. Format P-Values using the robust helper
    df_display["Claimed p"] = df_display["claimed_p_value"].apply(_fmt_p)
    df_display["Repro. p"] = df_display["reproduced_p_value"].apply(_fmt_p)

    # 4. Calculate and Format Delta (Discrepancy)
    def format_delta(val: Any) -> str:
        if val is None or pd.isna(val):
            return "—"
        try:
            v = float(val)
            if v < 0.001:
                return f"+{v:.4f}"
            return f"{v:.4f}"
        except (ValueError, TypeError):
            return "—"
            
    df_display["Δ"] = df_display["discrepancy"].apply(format_delta)

    # 5. Clean Test Type
    df_display["Test"] = df_display["test_type"].fillna("—").astype(str)

    # 6. Drop internal columns and reorder for display
    df_display = df_display[[
        "Claim", "Test", "Status_Label", "Status_Color", "Status_BG", 
        "Claimed p", "Repro. p", "Δ"
    ]]
    return df_display


def _apply_table_styling(df: pd.DataFrame) -> pd.DataFrame.style:
    """
    Applies pandas Styler formatting to the dataframe for color-coded status chips.
    
    Args:
        df: The formatted pandas DataFrame.
    
    Returns:
        A styled pandas Styler object.
    """
    def highlight_status(row):
        # If the column is 'Status_Label', return the specific CSS background/color
        # Otherwise, return an empty string to leave it unstyled.
        return [
            f'background-color: {row["Status_BG"]}; color: {row["Status_Color"]}; border-radius: 12px; padding: 3px 12px; font-weight: 600; font-size: 11px; display: inline-block;'
            if col == "Status_Label" else ''
            for col in row.index
        ]
    
    return df.style.apply(highlight_status, axis=1)


# ── Main Render Function ─────────────────────────────────────────────────────

def render() -> None:
    """
    Main entry point for the Dashboard page. 
    Orchestrates all UI components, data processing, and rendering logic.
    """
    # 1. Inject global CSS
    st.markdown(_CSS, unsafe_allow_html=True)

    # 2. Render Page Header
    st.markdown("""
    <div class="page-header">
      <div class="header-icon-wrapper">📊</div>
      <div>
        <div class="header-title">Verification Dashboard</div>
        <div class="header-subtitle">Statistical reproducibility results at a glance</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 3. Guard Clause: Check if analysis has been completed
    if not st.session_state.get("analysis_complete"):
        st.markdown("""
        <div class="empty-state">
          <div class="empty-icon">🔬</div>
          <div class="empty-title">No results yet</div>
          <div class="empty-subtitle">Upload a paper and verify its claims first,<br>then return here to explore the results in-depth.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # 4. Extract and compute core metrics from session state
    results = st.session_state.get("results", [])
    score = st.session_state.get("reproducibility_score", 0)
    total = len(results)
    
    # Safely calculate status counts
    counts = {k: sum(1 for r in results if r.get("status") == k) for k in _STATUS}

    # Extract claim mappings safely
    claims = st.session_state.get("confirmed_claims") or st.session_state.get("claims") or []
    claim_lookup = {c.get("id"): c.get("claim_statement") or c.get("id") for c in claims}

    # Determine score color
    score_color = _score_color(score)

    # 5. Render the Score Hero
    repro_rate = round(counts.get("reproduced", 0) / total * 100) if total else 0
    st.markdown(f"""
    <div class="score-hero">
      <div>
        <div class="score-number" style="color:{score_color};">{score}<span class="score-pct">%</span></div>
        <div class="score-label">Reproducibility Score</div>
      </div>
      <div class="score-note">
        <b style="color:{_STATUS['reproduced']['color']};">{counts.get('reproduced', 0)} reproduced</b>, 
        <b style="color:{_STATUS['marginal']['color']};">{counts.get('marginal', 0)} marginal</b>, 
        <b style="color:{_STATUS['not_reproduced']['color']};">{counts.get('not_reproduced', 0)} failed</b>, 
        <b style="color:{_STATUS['could_not_verify']['color']};">{counts.get('could_not_verify', 0)} unverifiable</b>.
        <br>Overall success rate: <b>{repro_rate}%</b> of <b>{total}</b> claims.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 6. Render the KPI Strip
    st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
    for key, meta in _STATUS.items():
        n = counts.get(key, 0)
        pct = round(n / total * 100) if total else 0
        st.markdown(f"""
        <div class="glass-panel kpi-card">
          <div class="kpi-accent" style="background:{meta['color']};"></div>
          <div class="kpi-title" style="color:{meta['color']};">{meta['label']}</div>
          <div class="kpi-number" style="color:{meta['color']};">{n}</div>
          <div class="kpi-subtitle">of {total} claims</div>
          <div class="kpi-progress-bar">
            <div class="kpi-progress-fill" style="width:{pct}%;background:{meta['color']};"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 7. Render the Callout Box if there are unverifiable claims
    if counts.get("could_not_verify", 0) > 0:
        st.markdown(f"""
        <div class="callout-box">
          <b>ℹ️ {counts['could_not_verify']} claim(s) could not be verified</b> —
          this means ReproHub was unable to run the test (e.g., an unmapped column or
          unsupported test type), not that the finding is incorrect.
          See the Review page for per-claim explanations.
        </div>
        """, unsafe_allow_html=True)

    # 8. Render Charts Section
    st.markdown('<div class="section-divider">Outcome breakdown</div>', unsafe_allow_html=True)

    col_donut, col_bar = st.columns([1, 1.6], gap="medium")

    with col_donut:
        with st.container():
            st.markdown('<div class="glass-panel" style="padding:12px 12px 4px;">', unsafe_allow_html=True)
            fig_donut = _create_donut_chart(counts, total)
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

    with col_bar:
        with st.container():
            fig_bar = _create_comparison_chart(results)
            if fig_bar:
                st.markdown('<div class="glass-panel" style="padding:12px 12px 4px;">', unsafe_allow_html=True)
                st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="glass-panel" style="display:flex; align-items:center; justify-content:center; height:260px; color:#64748B; font-size:13px;">
                  No comparable p-value data available for this chart
                </div>
                """, unsafe_allow_html=True)

    # 9. Render Claims Data Table
    st.markdown('<div class="section-divider">Claim-level results</div>', unsafe_allow_html=True)

    # Process the dataframe
    df_raw = pd.DataFrame(results)
    df_prepared = _prepare_dataframe(df_raw, claim_lookup)
    styled_df = _apply_table_styling(df_prepared)

    # Display the dataframe safely, hiding internal helper columns via column_order
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Claim": st.column_config.TextColumn("Claim", width="large"),
            "Test": st.column_config.TextColumn("Test", width="small"),
            "Status_Label": st.column_config.TextColumn("Status", width="medium"),
            "Claimed p": st.column_config.TextColumn("Claimed p", width="small"),
            "Repro. p": st.column_config.TextColumn("Repro. p", width="small"),
            "Δ": st.column_config.TextColumn("Δ", width="small"),
        },
        column_order=["Claim", "Test", "Status_Label", "Claimed p", "Repro. p", "Δ"]
    )

    # 10. Render Export Section
    st.markdown('<div class="section-divider">Export</div>', unsafe_allow_html=True)

    # Safely convert to CSV
    export_df = pd.DataFrame(results)
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇ Download Results (CSV)",
        data=csv_bytes,
        file_name="reprohub_results.csv",
        mime="text/csv",
    )
