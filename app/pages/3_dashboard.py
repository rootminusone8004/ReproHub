"""
Dashboard Page — Results Visualization

Renders a rich, scannable verification dashboard. The page's job:
give a researcher an at-a-glance read of every claim's outcome and
let them drill into the numbers without leaving the page.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List, Any

# ── Status config ─────────────────────────────────────────────────────────────
_STATUS = {
    "reproduced": {
        "label": "Reproduced",
        "color": "#10B981",
        "bg": "rgba(16,185,129,0.15)",
        "icon": "✓",
    },
    "marginal": {
        "label": "Marginal",
        "color": "#F59E0B",
        "bg": "rgba(245,158,11,0.15)",
        "icon": "~",
    },
    "not_reproduced": {
        "label": "Not Reproduced",
        "color": "#EF4444",
        "bg": "rgba(239,68,68,0.15)",
        "icon": "✗",
    },
    "could_not_verify": {
        "label": "Could Not Verify",
        "color": "#8B95A9",
        "bg": "rgba(139,149,169,0.15)",
        "icon": "?",
    },
}

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif !important;
}

.stApp {
    background: #0B0F19;
    color: #E2E8F0;
}

/* ── Glassmorphism Utility ── */
.glass-panel {
    background: rgba(255, 255, 255, 0.03) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 20px !important;
    padding: 20px !important;
}

/* ── KPI Card Component ── */
.kpi-card {
    padding: 20px !important;
    position: relative !important;
    overflow: hidden !important;
    transition: all 0.2s ease !important;
}
.kpi-card:hover {
    border-color: rgba(255, 255, 255, 0.12) !important;
    transform: translateY(-3px) !important;
}
.kpi-accent {
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: 4px !important;
    border-radius: 20px 20px 0 0 !important;
}
.kpi-num {
    font-size: 34px !important;
    font-weight: 700 !important;
    line-height: 1 !important;
    margin-top: 8px !important;
    letter-spacing: -0.02em !important;
}
.kpi-label {
    font-size: 11px !important;
    color: #64748B !important;
    margin-top: 6px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    font-weight: 500 !important;
}
.kpi-bar {
    height: 4px !important;
    border-radius: 4px !important;
    margin-top: 14px !important;
    background: rgba(255, 255, 255, 0.06) !important;
}
.kpi-bar-fill {
    height: 100% !important;
    border-radius: 4px !important;
    transition: width 0.8s cubic-bezier(0.22, 1, 0.36, 1) !important;
}

/* ── Score Hero ── */
.score-hero {
    background: linear-gradient(135deg, rgba(91, 79, 232, 0.12) 0%, rgba(124, 58, 237, 0.05) 100%) !important;
    border: 1px solid rgba(91, 79, 232, 0.2) !important;
    border-radius: 24px !important;
    padding: 32px 36px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    margin-bottom: 24px !important;
    position: relative !important;
    overflow: hidden !important;
}
.score-hero::before {
    content: '' !important;
    position: absolute !important;
    top: -60px !important;
    right: -60px !important;
    width: 240px !important;
    height: 240px !important;
    background: radial-gradient(circle, rgba(91, 79, 232, 0.15) 0%, transparent 70%) !important;
    pointer-events: none !important;
}
.score-number {
    font-size: 58px !important;
    font-weight: 700 !important;
    line-height: 1 !important;
    color: #F8FAFC !important;
    letter-spacing: -0.03em !important;
}
.score-pct {
    font-size: 28px !important;
    font-weight: 300 !important;
    color: #7C3AED !important;
}
.score-label {
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #64748B !important;
    margin-top: 6px !important;
}
.score-note {
    font-size: 13px !important;
    color: #94A3B8 !important;
    max-width: 340px !important;
    line-height: 1.6 !important;
}

/* ── Section Label ── */
.section-label {
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: #475569 !important;
    margin: 32px 0 16px !important;
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
}
.section-label::after {
    content: '' !important;
    flex: 1 !important;
    height: 1px !important;
    background: rgba(255, 255, 255, 0.06) !important;
}

/* ── Table Styling ── */
[data-testid="stDataFrame"] {
    background: transparent !important;
}
[data-testid="stDataFrame"] table {
    border-collapse: separate !important;
    border-spacing: 0 6px !important;
}
[data-testid="stDataFrame"] thead tr th {
    background: rgba(255, 255, 255, 0.04) !important;
    color: #94A3B8 !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
    padding: 12px 16px !important;
}
[data-testid="stDataFrame"] tbody tr td {
    background: rgba(255, 255, 255, 0.02) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
    padding: 12px 16px !important;
    color: #E2E8F0 !important;
    font-size: 13px !important;
}
[data-testid="stDataFrame"] tbody tr:hover td {
    background: rgba(255, 255, 255, 0.05) !important;
    transition: background 0.2s ease !important;
}

/* ── Download Button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #5B4FE8, #7C3AED) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 10px 28px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 16px rgba(91, 79, 232, 0.3) !important;
}
.stDownloadButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(91, 79, 232, 0.4) !important;
}

/* ── Empty State ── */
.empty-state {
    text-align: center !important;
    padding: 80px 24px !important;
}
.empty-icon {
    font-size: 56px !important;
    margin-bottom: 20px !important;
    opacity: 0.6 !important;
}
.empty-title {
    font-size: 20px !important;
    font-weight: 600 !important;
    color: #CBD5E1 !important;
    margin-bottom: 8px !important;
}
.empty-sub {
    font-size: 14px !important;
    color: #64748B !important;
}

/* ── Callout ── */
.callout-box {
    background: rgba(245, 158, 11, 0.08) !important;
    border: 1px solid rgba(245, 158, 11, 0.15) !important;
    border-radius: 14px !important;
    padding: 16px 20px !important;
    font-size: 13px !important;
    color: #FCD34D !important;
    line-height: 1.6 !important;
    margin-bottom: 24px !important;
}
.callout-box b {
    font-weight: 600 !important;
}

/* ── Plotly override ── */
.js-plotly-plot .plotly {
    background: transparent !important;
}
</style>
"""


def _fmt_p(v: Any) -> str:
    if v is None or pd.isna(v):
        return "—"
    try:
        v = float(v)
        if v < 0.001:
            return "<.001"
        return f"{v:.4f}"
    except (ValueError, TypeError):
        return "—"


def _score_color(score: int) -> str:
    if score >= 75:
        return "#10B981"
    if score >= 40:
        return "#F59E0B"
    return "#EF4444"


def _donut_chart(counts: Dict[str, int], total: int):
    """Render a clean donut chart via Plotly go."""
    present = {k: v for k, v in counts.items() if v > 0}
    labels = [_STATUS[k]["label"] for k in present]
    values = list(present.values())
    colors = [_STATUS[k]["color"] for k in present]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.60,
        marker=dict(
            colors=colors,
            line=dict(color="#0B0F19", width=3),
        ),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value} claim(s) — %{percent}<extra></extra>",
        direction="clockwise",
        sort=False,
    ))

    fig.add_annotation(
        text=f"<b style='font-size:32px; color:#F8FAFC;'>{total}</b>",
        x=0.5, y=0.58, showarrow=False,
        font=dict(family="Inter", size=32, color="#F8FAFC"),
    )
    fig.add_annotation(
        text="claims",
        x=0.5, y=0.42, showarrow=False,
        font=dict(family="Inter", size=12, color="#64748B"),
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=16, b=16, l=16, r=16),
        height=300,
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


def _bar_chart(results: List[Dict]):
    """Horizontal bar: p-value claimed vs reproduced per claim."""
    rows = [
        r for r in results
        if r.get("claimed_p_value") is not None and not pd.isna(r.get("claimed_p_value"))
        and r.get("reproduced_p_value") is not None and not pd.isna(r.get("reproduced_p_value"))
    ]
    if not rows:
        return None

    ids = [r.get("claim_id", f"C{i+1}") for i, r in enumerate(rows)]
    claimed = [float(r["claimed_p_value"]) for r in rows]
    reproduced = [float(r["reproduced_p_value"]) for r in rows]
    statuses = [r.get("status", "could_not_verify") for r in rows]
    bar_cols = [_STATUS[s]["color"] for s in statuses]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="Claimed p",
        y=ids, x=claimed,
        orientation="h",
        marker=dict(color="rgba(91, 79, 232, 0.4)", line=dict(color="#5B4FE8", width=1.5)),
        hovertemplate="<b>%{y}</b><br>Claimed p = %{x:.4f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Reproduced p",
        y=ids, x=reproduced,
        orientation="h",
        marker=dict(color=bar_cols, opacity=0.85),
        hovertemplate="<b>%{y}</b><br>Reproduced p = %{x:.4f}<extra></extra>",
    ))

    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=16, b=8, l=8, r=16),
        height=max(240, 48 * len(rows)),
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


def _style_dataframe(df: pd.DataFrame, claim_lookup: Dict[str, str]) -> pd.DataFrame:
    """Prepare and style the dataframe for display."""
    df_display = df.copy()

    # 1. Map Claim ID to Claim Text
    df_display["Claim"] = df_display["claim_id"].map(claim_lookup).fillna(df_display["claim_id"])
    df_display["Claim"] = df_display["Claim"].astype(str).apply(lambda x: x[:75] + "…" if len(x) > 75 else x)

    # 2. Map Status to plain text (for sorting) and prepare color mapping
    df_display["Status_Label"] = df_display["status"].map(lambda x: _STATUS.get(x, _STATUS["could_not_verify"])["label"])
    df_display["Status_Color"] = df_display["status"].map(lambda x: _STATUS.get(x, _STATUS["could_not_verify"])["color"])
    df_display["Status_BG"] = df_display["status"].map(lambda x: _STATUS.get(x, _STATUS["could_not_verify"])["bg"])

    # 3. Format P-Values
    df_display["Claimed p"] = df_display["claimed_p_value"].apply(_fmt_p)
    df_display["Repro. p"] = df_display["reproduced_p_value"].apply(_fmt_p)

    # 4. Format Delta
    def fmt_delta(val):
        if val is None or pd.isna(val):
            return "—"
        try:
            val = float(val)
            if val < 0.001:
                return f"+{val:.4f}"
            else:
                return f"{val:.4f}"
        except (ValueError, TypeError):
            return "—"
    df_display["Δ"] = df_display["discrepancy"].apply(fmt_delta)

    # 5. Test Type
    df_display["Test"] = df_display["test_type"].fillna("—").astype(str)

    # 6. Select final columns
    df_display = df_display[["Claim", "Test", "Status_Label", "Status_Color", "Status_BG", "Claimed p", "Repro. p", "Δ"]]
    return df_display


def render():
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex; align-items:center; gap:18px; margin-bottom:32px; padding-bottom:24px; border-bottom:1px solid rgba(255,255,255,0.06);">
      <div style="width:52px; height:52px; flex-shrink:0; background:linear-gradient(135deg, #7C3AED, #5B4FE8); border-radius:16px; display:flex; align-items:center; justify-content:center; font-size:24px; box-shadow:0 8px 24px rgba(91,79,232,0.25);">📊</div>
      <div>
        <div style="font-size:26px; font-weight:700; color:#F8FAFC; margin:0; line-height:1.2; letter-spacing:-0.02em;">Verification Dashboard</div>
        <div style="font-size:13px; color:#94A3B8; margin-top:2px; font-weight:400;">Statistical reproducibility results at a glance</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Guard ─────────────────────────────────────────────────────────────────
    if not st.session_state.get("analysis_complete"):
        st.markdown("""
        <div class="empty-state">
          <div class="empty-icon">🔬</div>
          <div class="empty-title">No results yet</div>
          <div class="empty-sub">Upload a paper and verify its claims first,<br>then return here to explore the results.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    results = st.session_state.results
    score = st.session_state.reproducibility_score
    total = len(results)
    counts = {k: sum(1 for r in results if r.get("status") == k) for k in _STATUS}

    claims = st.session_state.get("confirmed_claims") or st.session_state.get("claims") or []
    claim_lookup = {c.get("id"): c.get("claim_statement") or c.get("id") for c in claims}

    score_c = _score_color(score)

    # ── Score hero ────────────────────────────────────────────────────────────
    repro_rate = round(counts["reproduced"] / total * 100) if total else 0
    st.markdown(f"""
    <div class="score-hero">
      <div>
        <div class="score-number" style="color:{score_c};">{score}<span class="score-pct">%</span></div>
        <div class="score-label">Reproducibility Score</div>
      </div>
      <div class="score-note">
        <b style="color:{_STATUS['reproduced']['color']};">{counts['reproduced']} reproduced</b>, 
        <b style="color:{_STATUS['marginal']['color']};">{counts['marginal']} marginal</b>, 
        <b style="color:{_STATUS['not_reproduced']['color']};">{counts['not_reproduced']} failed</b>, 
        <b style="color:{_STATUS['could_not_verify']['color']};">{counts['could_not_verify']} unverifiable</b>.
        <br>Overall success rate: {repro_rate}% of {total} claims.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI strip ─────────────────────────────────────────────────────────────
    cols = st.columns(4)
    for idx, (key, meta) in enumerate(_STATUS.items()):
        n = counts[key]
        pct = round(n / total * 100) if total else 0
        with cols[idx]:
            st.markdown(f"""
            <div class="glass-panel kpi-card">
              <div class="kpi-accent" style="background:{meta['color']};"></div>
              <div style="font-size:11px;color:{meta['color']};font-weight:600;letter-spacing:.07em;text-transform:uppercase;">{meta['label']}</div>
              <div class="kpi-num" style="color:{meta['color']};">{n}</div>
              <div class="kpi-label">of {total} claims</div>
              <div class="kpi-bar">
                <div class="kpi-bar-fill" style="width:{pct}%;background:{meta['color']};"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Unverifiable callout ──────────────────────────────────────────────────
    if counts["could_not_verify"] > 0:
        st.markdown(f"""
        <div class="callout-box">
          <b>ℹ️ {counts['could_not_verify']} claim(s) could not be verified</b> —
          this means ReproHub was unable to run the test (e.g. an unmapped column or
          unsupported test type), not that the finding is incorrect.
          See the Review page for per-claim explanations.
        </div>
        """, unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Outcome breakdown</div>', unsafe_allow_html=True)

    col_donut, col_bar = st.columns([1, 1.6], gap="medium")

    with col_donut:
        with st.container():
            st.markdown('<div class="glass-panel" style="padding:12px 12px 4px;">', unsafe_allow_html=True)
            fig_donut = _donut_chart(counts, total)
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

    with col_bar:
        with st.container():
            fig_bar = _bar_chart(results)
            if fig_bar:
                st.markdown('<div class="glass-panel" style="padding:12px 12px 4px;">', unsafe_allow_html=True)
                st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="glass-panel" style="display:flex;align-items:center;justify-content:center;height:200px;color:#64748B;font-size:13px;">
                  No comparable p-value data available for chart
                </div>
                """, unsafe_allow_html=True)

    # ── Claims table ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Claim-level results</div>', unsafe_allow_html=True)

    # Process dataframe
    df_raw = pd.DataFrame(results)
    df_display = _style_dataframe(df_raw, claim_lookup)

    # Apply custom styling to the dataframe for color-coded status chips
    def highlight_status(row):
        return [
            f'background-color: {row["Status_BG"]}; color: {row["Status_Color"]}; border-radius: 12px; padding: 2px 10px; font-weight: 600; font-size: 11px; display: inline-block;'
            if col == "Status_Label" else ''
            for col in row.index
        ]

    styled_df = df_display.style.apply(highlight_status, axis=1)

    # Display using st.dataframe with clean configurations
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Claim": st.column_config.TextColumn("Claim", width="large"),
            "Test": st.column_config.TextColumn("Test", width="small"),
            "Status_Label": st.column_config.TextColumn("Status", width="medium"),
            "Status_Color": st.column_config.TextColumn("_", width="small", visible=False),
            "Status_BG": st.column_config.TextColumn("_", width="small", visible=False),
            "Claimed p": st.column_config.TextColumn("Claimed p", width="small"),
            "Repro. p": st.column_config.TextColumn("Repro. p", width="small"),
            "Δ": st.column_config.TextColumn("Δ", width="small"),
        }
    )

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Export</div>', unsafe_allow_html=True)

    results_df = pd.DataFrame(results)
    csv_bytes = results_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇ Download Results (CSV)",
        data=csv_bytes,
        file_name="reprohub_results.csv",
        mime="text/csv",
    )
