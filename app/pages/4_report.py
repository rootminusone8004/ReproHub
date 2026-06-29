"""
Report Page — Real PDF Report Generation

Builds an actual PDF from the real verification results (core.comparator's
output, stored in st.session_state.results) using ReportLab. The PDF includes
an executive summary and/or a detailed per-claim results table, depending on
which sections the user selects.
"""

import io
from datetime import datetime

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

from app.config import config

# ── Status config ────────────────────────────────────────────────────────────
STATUS_META = {
    "reproduced": {"label": "Reproduced", "symbol": "✓", "hex": "#10B981"},
    "marginal": {"label": "Marginal", "symbol": "~", "hex": "#F59E0B"},
    "not_reproduced": {"label": "Not Reproduced", "symbol": "✗", "hex": "#EF4444"},
    "could_not_verify": {"label": "Could Not Verify", "symbol": "?", "hex": "#8B95A9"},
}

STATUS_LABELS = {k: v["label"] for k, v in STATUS_META.items()}

# ── PDF palette ───────────────────────────────────────────────────────────────
C_INK = colors.HexColor("#0D1117")
C_SURFACE = colors.HexColor("#FFFFFF")
C_RULE = colors.HexColor("#E2E8F0")
C_MUTED = colors.HexColor("#8B95A9")
C_ACCENT = colors.HexColor("#5B4FE8")
C_HEADER_BG = colors.HexColor("#0A0F1E")
C_ALT_ROW = colors.HexColor("#F8FAFC")
C_REPRODUCED = colors.HexColor("#10B981")
C_MARGINAL = colors.HexColor("#F59E0B")
C_NOT_REPRO = colors.HexColor("#EF4444")
C_UNVERIFIED = colors.HexColor("#8B95A9")

STATUS_COLORS = {
    "reproduced": C_REPRODUCED,
    "marginal": C_MARGINAL,
    "not_reproduced": C_NOT_REPRO,
    "could_not_verify": C_UNVERIFIED,
}


def _format_p(value) -> str:
    if value is None:
        return "—"
    if value < 0.001:
        return "<.001"
    return f"{value:.4f}"


def _score_color(score: int):
    if score >= 75:
        return C_REPRODUCED
    if score >= 40:
        return C_MARGINAL
    return C_NOT_REPRO


def _build_pdf(
    results: list,
    score: int,
    claim_lookup: dict,
    include_summary: bool,
    include_details: bool,
) -> bytes:
    """Render the verification results into a production-quality PDF."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.65 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # ── Custom style sheet ────────────────────────────────────────────────────
    def s(name, **kw):
        base = kw.pop("parent", styles["Normal"])
        return ParagraphStyle(name, parent=base, **kw)

    sty = {
        "cover_brand": s(
            "CoverBrand",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=C_ACCENT,
            spaceAfter=6,
            tracking=2,
        ),
        "cover_title": s(
            "CoverTitle",
            fontName="Helvetica-Bold",
            fontSize=26,
            textColor=C_INK,
            leading=30,
            spaceAfter=4,
        ),
        "cover_sub": s(
            "CoverSub",
            fontName="Helvetica",
            fontSize=10,
            textColor=C_MUTED,
            spaceAfter=24,
        ),
        "section": s(
            "Section",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=C_INK,
            spaceBefore=18,
            spaceAfter=6,
        ),
        "body": s(
            "Body",
            fontName="Helvetica",
            fontSize=9,
            textColor=C_INK,
            leading=14,
            spaceAfter=6,
        ),
        "note_label": s(
            "NoteLabel",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            textColor=C_INK,
            leading=13,
        ),
        "note_body": s(
            "NoteBody",
            fontName="Helvetica",
            fontSize=8.5,
            textColor=colors.HexColor("#475569"),
            leading=13,
            spaceAfter=6,
        ),
        "score_big": s(
            "ScoreBig",
            fontName="Helvetica-Bold",
            fontSize=36,
            textColor=_score_color(score),
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "score_label": s(
            "ScoreLabel",
            fontName="Helvetica",
            fontSize=8,
            textColor=C_MUTED,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "stat_num": s(
            "StatNum",
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=C_INK,
            alignment=TA_CENTER,
            spaceAfter=0,
        ),
        "stat_lbl": s(
            "StatLbl",
            fontName="Helvetica",
            fontSize=7.5,
            textColor=C_MUTED,
            alignment=TA_CENTER,
            spaceAfter=0,
        ),
        "footer": s(
            "Footer",
            fontName="Helvetica",
            fontSize=7.5,
            textColor=C_MUTED,
            alignment=TA_CENTER,
        ),
    }

    total = len(results)
    counts = {
        k: sum(1 for r in results if r.get("status") == k) for k in STATUS_META
    }

    def rule(color=C_RULE, thickness=0.5, space=8):
        return HRFlowable(
            width="100%",
            thickness=thickness,
            color=color,
            spaceAfter=space,
            spaceBefore=space,
        )

    elements = []

    # ── Cover block ───────────────────────────────────────────────────────────
    elements.append(Paragraph("REPROHUB", sty["cover_brand"]))
    elements.append(Paragraph("Verification Report", sty["cover_title"]))
    elements.append(
        Paragraph(
            f"Generated {datetime.now().strftime('%B %d, %Y at %H:%M')} &nbsp;·&nbsp; "
            f"{config.APP_NAME} v{config.APP_VERSION}",
            sty["cover_sub"],
        )
    )
    elements.append(rule(C_ACCENT, thickness=2, space=20))

    # ── Executive Summary ─────────────────────────────────────────────────────
    if include_summary:
        elements.append(Paragraph("Executive Summary", sty["section"]))

        # Score + stat grid as a table for precise layout
        stat_rows = [
            [
                Paragraph(f"{score}%", sty["score_big"]),
                Paragraph(str(counts["reproduced"]), sty["stat_num"]),
                Paragraph(str(counts["marginal"]), sty["stat_num"]),
                Paragraph(str(counts["not_reproduced"]), sty["stat_num"]),
                Paragraph(str(counts["could_not_verify"]), sty["stat_num"]),
            ],
            [
                Paragraph("Reproducibility Score", sty["score_label"]),
                Paragraph("Reproduced", sty["stat_lbl"]),
                Paragraph("Marginal", sty["stat_lbl"]),
                Paragraph("Not Reproduced", sty["stat_lbl"]),
                Paragraph("Could Not Verify", sty["stat_lbl"]),
            ],
        ]
        stat_col_w = [1.7 * inch, 1.2 * inch, 1.1 * inch, 1.3 * inch, 1.3 * inch]
        stat_table = Table(stat_rows, colWidths=stat_col_w)
        stat_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BACKGROUND", (0, 0), (0, 1), colors.HexColor("#EEF2FF")),
                    ("LINEAFTER", (0, 0), (0, 1), 0.75, C_RULE),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROUNDEDCORNERS", [4]),
                    ("BOX", (0, 0), (-1, -1), 0.5, C_RULE),
                ]
            )
        )
        elements.append(stat_table)
        elements.append(Spacer(1, 10))

        elements.append(
            Paragraph(
                f"Of <b>{total}</b> statistical claim(s) examined, ReproHub successfully "
                f"reproduced <b>{counts['reproduced']}</b> "
                f"({round(counts['reproduced']/total*100) if total else 0}%), "
                f"found <b>{counts['marginal']}</b> marginal results within tolerance, "
                f"could not reproduce <b>{counts['not_reproduced']}</b>, and was unable "
                f"to verify <b>{counts['could_not_verify']}</b> due to insufficient data.",
                sty["body"],
            )
        )
        elements.append(rule())

    # ── Detailed Results ──────────────────────────────────────────────────────
    if include_details:
        elements.append(Paragraph("Detailed Results", sty["section"]))
        elements.append(Spacer(1, 4))

        col_w = [2.15 * inch, 0.95 * inch, 1.05 * inch, 0.8 * inch, 0.9 * inch, 0.65 * inch]
        header = ["Claim", "Test", "Status", "Claimed p", "Repro. p", "Δ"]
        table_data = [header]
        status_per_row = []

        for r in results:
            cid = r.get("claim_id", "—")
            claim_text = claim_lookup.get(cid, cid)
            if len(claim_text) > 55:
                claim_text = claim_text[:52] + "…"
            status = r.get("status", "")
            label = STATUS_META.get(status, {}).get("label", status)
            table_data.append(
                [
                    claim_text,
                    r.get("test_type", "—"),
                    label,
                    _format_p(r.get("claimed_p_value")),
                    _format_p(r.get("reproduced_p_value")),
                    _format_p(r.get("discrepancy")),
                ]
            )
            status_per_row.append(status)

        # Base table style
        ts = TableStyle(
            [
                # Header
                ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
                # Body
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("TOPPADDING", (0, 1), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.4, C_RULE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_SURFACE, C_ALT_ROW]),
            ]
        )

        # Per-row status colour on the Status column (col 2)
        for i, status in enumerate(status_per_row, start=1):
            c = STATUS_COLORS.get(status, C_MUTED)
            ts.add("TEXTCOLOR", (2, i), (2, i), c)
            ts.add("FONTNAME", (2, i), (2, i), "Helvetica-Bold")

        table = Table(table_data, repeatRows=1, colWidths=col_w)
        table.setStyle(ts)
        elements.append(table)

        # Notes section (for could_not_verify explanations)
        notes = [r for r in results if r.get("explanation")]
        if notes:
            elements.append(Spacer(1, 14))
            elements.append(rule())
            elements.append(Paragraph("Verification Notes", sty["section"]))
            for r in notes:
                cid = r.get("claim_id", "—")
                ttype = r.get("test_type", "")
                expl = r.get("explanation", "")
                elements.append(
                    KeepTogether(
                        [
                            Paragraph(f"{cid} &nbsp;·&nbsp; {ttype}", sty["note_label"]),
                            Paragraph(expl, sty["note_body"]),
                        ]
                    )
                )

    # ── Footer ────────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 20))
    elements.append(rule(C_RULE, space=6))
    elements.append(
        Paragraph(
            f"Confidential · {config.APP_NAME} v{config.APP_VERSION} · "
            f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            sty["footer"],
        )
    )

    doc.build(elements)
    return buffer.getvalue()


# ── Streamlit UI ──────────────────────────────────────────────────────────────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: #0B0F19 !important;
    color: #E2E8F0 !important;
}

.stApp { background: #0B0F19; }

/* ── Page Header ── */
.report-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 32px;
    padding-bottom: 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.report-icon-wrapper {
    width: 48px;
    height: 48px;
    background: linear-gradient(135deg, #7C3AED, #5B4FE8);
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    box-shadow: 0 8px 24px rgba(91, 79, 232, 0.3);
}
.report-title {
    font-size: 24px;
    font-weight: 700;
    color: #F8FAFC;
    margin: 0;
    line-height: 1.2;
    letter-spacing: -0.02em;
}
.report-subtitle {
    font-size: 13px;
    color: #94A3B8;
    margin-top: 2px;
    font-weight: 400;
}

/* ── Glass Panels ── */
.glass-panel {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 20px;
    transition: all 0.2s ease;
}

/* ── Config Panel ── */
.config-panel {
    padding: 24px;
    height: 100%;
}
.config-title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #64748B;
    margin-bottom: 20px;
}

/* ── Options ── */
.option-card {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 16px 18px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 14px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
}
.option-card:hover {
    border-color: rgba(91, 79, 232, 0.3);
}
.option-icon {
    font-size: 20px;
    flex-shrink: 0;
    margin-top: 1px;
}
.option-content-title {
    font-size: 14px;
    font-weight: 600;
    color: #E2E8F0;
}
.option-content-desc {
    font-size: 12px;
    color: #64748B;
    margin-top: 2px;
    line-height: 1.4;
}

/* ── Checkbox override ── */
[data-testid="stCheckbox"] { margin: 0 !important; }
[data-testid="stCheckbox"] label { cursor: pointer !important; }

/* ── Score Preview ── */
.score-preview-panel {
    padding: 28px 24px 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
}

.ring-container {
    position: relative;
    width: 140px;
    height: 140px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.ring-svg {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    filter: drop-shadow(0 0 20px rgba(91, 79, 232, 0.25));
}
.ring-score-text {
    position: relative;
    z-index: 10;
    font-size: 36px;
    font-weight: 700;
    color: #F8FAFC;
    letter-spacing: -0.02em;
}

.score-label-text {
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748B;
    margin-top: 4px;
}

/* ── Stat Grid ── */
.stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    width: 100%;
    margin-top: 24px;
}
.stat-pill {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 14px 10px;
    text-align: center;
}
.stat-pill-num {
    font-size: 24px;
    font-weight: 700;
    line-height: 1;
}
.stat-pill-lbl {
    font-size: 10px;
    color: #64748B;
    margin-top: 3px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 500;
}

/* ── Legend ── */
.legend-container {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 10px 16px;
    margin-top: 18px;
    padding: 14px 16px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 12px;
    width: 100%;
}
.legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #94A3B8;
}
.legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}
.legend-val {
    color: #CBD5E1;
    font-weight: 600;
}

/* ── Footer Meta ── */
.meta-text {
    font-size: 11px;
    color: #475569;
    text-align: center;
    margin-top: 16px;
}

/* ── Generate Button ── */
.generate-wrapper .stButton > button {
    width: 100%;
    background: linear-gradient(135deg, #5B4FE8, #7C3AED) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 14px 24px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 4px 20px rgba(91, 79, 232, 0.35) !important;
    transition: all 0.2s ease !important;
}
.generate-wrapper .stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 32px rgba(91, 79, 232, 0.5) !important;
}

/* ── Download Button ── */
.download-wrapper .stDownloadButton > button {
    width: 100%;
    background: transparent !important;
    color: #5B4FE8 !important;
    border: 1.5px solid #5B4FE8 !important;
    border-radius: 14px !important;
    padding: 12px 24px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.2s ease !important;
}
.download-wrapper .stDownloadButton > button:hover {
    background: rgba(91, 79, 232, 0.08) !important;
    border-color: #7C6FF0 !important;
}

/* ── Success / Warning ── */
.success-banner {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 14px;
    padding: 14px 18px;
    margin-top: 16px;
    font-size: 13px;
    color: #6EE7B7;
    font-weight: 500;
}
.warning-banner {
    background: rgba(245, 158, 11, 0.08);
    border: 1px solid rgba(245, 158, 11, 0.2);
    border-radius: 14px;
    padding: 14px 18px;
    font-size: 13px;
    color: #FCD34D;
}

/* ── Empty State ── */
.empty-state {
    text-align: center;
    padding: 80px 24px;
}
.empty-icon {
    font-size: 52px;
    margin-bottom: 18px;
    opacity: 0.6;
}
.empty-title {
    font-size: 20px;
    font-weight: 600;
    color: #CBD5E1;
    margin-bottom: 6px;
}
.empty-sub {
    font-size: 13px;
    color: #64748B;
}

/* ── Divider ── */
.rh-divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.06);
    margin: 28px 0;
}

/* ── Spinner Override ── */
.stSpinner { color: #7C3AED !important; }
</style>
"""


def _score_ring_svg(score: int) -> str:
    """
    Generate an SVG score ring with a smooth CSS draw animation.
    Score must be 0-100.
    """
    radius = 54
    cx = cy = 68
    circumference = 2 * 3.14159 * radius
    offset = circumference * (100 - score) / 100

    if score >= 75:
        stroke_color = "#10B981"
    elif score >= 40:
        stroke_color = "#F59E0B"
    else:
        stroke_color = "#EF4444"

    return f"""
    <svg class="ring-svg" viewBox="0 0 136 136" xmlns="http://www.w3.org/2000/svg">
      <style>
        .ring-bg {{ stroke: rgba(255,255,255,0.08); }}
        .ring-progress {{
          stroke: {stroke_color};
          stroke-dasharray: {circumference:.2f};
          stroke-dashoffset: {offset:.2f};
          transition: stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1);
        }}
      </style>
      <circle class="ring-bg" cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke-width="8"/>
      <circle class="ring-progress" cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke-width="8" stroke-linecap="round" transform="rotate(-90 {cx} {cy})"/>
    </svg>
    """


def render():
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Page Header ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="report-header">
      <div class="report-icon-wrapper">📄</div>
      <div>
        <div class="report-title">Generate Report</div>
        <div class="report-subtitle">Export a professional PDF summarising your verification results</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Guard: No results yet ─────────────────────────────────────────────────
    if not st.session_state.get("analysis_complete"):
        st.markdown("""
        <div class="empty-state">
          <div class="empty-icon">🔬</div>
          <div class="empty-title">No analysis results yet</div>
          <div class="empty-sub">Upload a paper and verify its claims first,<br>then return here to generate your report.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    results = st.session_state.results
    score = st.session_state.reproducibility_score
    total = len(results)

    claims = st.session_state.get("confirmed_claims") or st.session_state.get("claims") or []
    claim_lookup = {c.get("id"): c.get("claim_statement") or c.get("id") for c in claims}

    counts = {k: sum(1 for r in results if r.get("status") == k) for k in STATUS_META}

    # ── Two-column layout ─────────────────────────────────────────────────────
    col_config, col_preview = st.columns([1.05, 0.95], gap="large")

    # ── LEFT: Configuration ──────────────────────────────────────────────────
    with col_config:
        st.markdown('<div class="glass-panel config-panel">', unsafe_allow_html=True)
        st.markdown('<div class="config-title">Report Sections</div>', unsafe_allow_html=True)

        # Summary Option
        st.markdown("""
        <div class="option-card">
          <div class="option-icon">📋</div>
          <div>
            <div class="option-content-title">Executive Summary</div>
            <div class="option-content-desc">Score overview and per-status breakdown</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        include_summary = st.checkbox("Include executive summary", value=True, key="cb_summary", label_visibility="collapsed")

        # Details Option
        st.markdown("""
        <div class="option-card">
          <div class="option-icon">📊</div>
          <div>
            <div class="option-content-title">Detailed Results</div>
            <div class="option-content-desc">Per-claim table with p-values and discrepancy</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        include_details = st.checkbox("Include detailed results", value=True, key="cb_details", label_visibility="collapsed")

        st.markdown('<div class="rh-divider"></div>', unsafe_allow_html=True)

        # Status Legend
        legend_html = '<div class="legend-container">'
        for key, meta in STATUS_META.items():
            legend_html += (
                f'<div class="legend-item">'
                f'<div class="legend-dot" style="background:{meta["hex"]};"></div>'
                f'{meta["label"]}: <span class="legend-val">{counts[key]}</span>'
                f'</div>'
            )
        legend_html += '</div>'
        st.markdown(legend_html, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # Close panel

    # ── RIGHT: Score Preview ──────────────────────────────────────────────────
    with col_preview:
        with st.container():
            st.markdown('<div class="glass-panel score-preview-panel">', unsafe_allow_html=True)
            
            # Ring Chart
            ring_svg = _score_ring_svg(score)
            st.markdown(f"""
            <div class="ring-container">
                {ring_svg}
                <div class="ring-score-text">{score}%</div>
            </div>
            <div class="score-label-text">Reproducibility Score</div>
            """, unsafe_allow_html=True)

            # Stats Grid (Using Native Streamlit Metrics to avoid HTML escaping)
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Reproduced", value=counts['reproduced'], label_visibility="visible")
            with col2:
                st.metric(label="Marginal", value=counts['marginal'], label_visibility="visible")
            
            col3, col4 = st.columns(2)
            with col3:
                st.metric(label="Not Reproduced", value=counts['not_reproduced'], label_visibility="visible")
            with col4:
                st.metric(label="Unverifiable", value=counts['could_not_verify'], label_visibility="visible")

            # Footer Meta
            st.markdown(f"""
            <div class="meta-text">
                {total} claim{"s" if total != 1 else ""} examined &nbsp;·&nbsp;
                {datetime.now().strftime('%Y-%m-%d %H:%M')}
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Footer Action Buttons ─────────────────────────────────────────────────
    st.markdown('<div class="rh-divider"></div>', unsafe_allow_html=True)

    if not include_summary and not include_details:
        st.markdown('<div class="warning-banner">⚠️ Select at least one section to include in the report.</div>', unsafe_allow_html=True)
        return

    st.markdown('<div class="generate-wrapper">', unsafe_allow_html=True)
    generate = st.button("Generate PDF Report", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if generate:
        with st.spinner("Building your professional report…"):
            try:
                pdf_bytes = _build_pdf(
                    results, score, claim_lookup,
                    include_summary, include_details,
                )
            except Exception as exc:
                st.error(f"Report generation failed: {exc}")
                if config.DEBUG:
                    st.exception(exc)
                return

        st.session_state.report_generated = True
        st.session_state.report_data = pdf_bytes

        st.markdown('<div class="success-banner">✅ &nbsp; Report generated successfully — ready to download.</div>', unsafe_allow_html=True)

    if st.session_state.get("report_generated") and st.session_state.get("report_data"):
        fname = f"reprohub_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        st.markdown('<div class="download-wrapper">', unsafe_allow_html=True)
        st.download_button(
            label="⬇ Download PDF",
            data=st.session_state.report_data,
            file_name=fname,
            mime="application/pdf",
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
