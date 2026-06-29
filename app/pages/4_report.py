"""
Report Page — Real PDF Report Generation

Builds an actual PDF from the real verification results (core.comparator's
output, stored in st.session_state.results) using ReportLab. The PDF includes
an executive summary and/or a detailed per-claim results table, depending on
which sections the user selects.

Requires reportlab >= 3.6.13 (uses the `ROUNDEDCORNERS` table style command).
"""

import io
import logging
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
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

logger = logging.getLogger(__name__)

# ── Status config ────────────────────────────────────────────────────────────
STATUS_META = {
    "reproduced": {"label": "Reproduced", "symbol": "✓", "hex": "#10B981"},
    "marginal": {"label": "Marginal", "symbol": "~", "hex": "#F59E0B"},
    "not_reproduced": {"label": "Not Reproduced", "symbol": "✗", "hex": "#EF4444"},
    "could_not_verify": {"label": "Could Not Verify", "symbol": "?", "hex": "#8B95A9"},
}

STATUS_LABELS = {k: v["label"] for k, v in STATUS_META.items()}
STATUS_ORDER = list(STATUS_META.keys())

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

MAX_CLAIM_CHARS = 55
DOWNLOAD_FILENAME_FMT = "reprohub_report_%Y%m%d_%H%M%S.pdf"


# ── Small, defensive helpers ──────────────────────────────────────────────────

def _format_p(value) -> str:
    """Format a p-value (or any numeric stat) for table display. Never raises."""
    if value is None:
        return "—"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"
    if value != value:  # NaN check without importing math
        return "—"
    if value < 0.001:
        return "<.001"
    return f"{value:.4f}"


def _score_color(score) -> colors.Color:
    """Map a 0-100 score to a semantic colour. Falls back safely on bad input."""
    try:
        score = float(score)
    except (TypeError, ValueError):
        return C_MUTED
    if score >= 75:
        return C_REPRODUCED
    if score >= 40:
        return C_MARGINAL
    return C_NOT_REPRO


def _safe_text(value, fallback: str = "—") -> str:
    """
    Coerce arbitrary result-dict values into a short, XML-escaped string that's
    safe to interpolate into a ReportLab Paragraph (which parses a mini-HTML
    dialect — unescaped '<', '>' or '&' from claim text can throw or corrupt
    layout).
    """
    if value is None:
        return fallback
    text = str(value).strip()
    if not text:
        return fallback
    return xml_escape(text)


def _truncate(text: str, max_chars: int = MAX_CLAIM_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ── PDF construction ──────────────────────────────────────────────────────────

def _build_styles(score: int) -> dict:
    """Build the named ParagraphStyle set used throughout the document."""
    base = getSampleStyleSheet()

    def s(name, **kw):
        parent = kw.pop("parent", base["Normal"])
        return ParagraphStyle(name, parent=parent, **kw)

    return {
        "cover_brand": s(
            "CoverBrand", fontName="Helvetica-Bold", fontSize=9,
            textColor=C_ACCENT, spaceAfter=6,
        ),
        "cover_title": s(
            "CoverTitle", fontName="Helvetica-Bold", fontSize=26,
            textColor=C_INK, leading=30, spaceAfter=4,
        ),
        "cover_sub": s(
            "CoverSub", fontName="Helvetica", fontSize=10,
            textColor=C_MUTED, spaceAfter=24,
        ),
        "section": s(
            "Section", fontName="Helvetica-Bold", fontSize=13,
            textColor=C_INK, spaceBefore=18, spaceAfter=6,
        ),
        "body": s(
            "Body", fontName="Helvetica", fontSize=9,
            textColor=C_INK, leading=14, spaceAfter=6,
        ),
        "note_label": s(
            "NoteLabel", fontName="Helvetica-Bold", fontSize=8.5,
            textColor=C_INK, leading=13,
        ),
        "note_body": s(
            "NoteBody", fontName="Helvetica", fontSize=8.5,
            textColor=colors.HexColor("#475569"), leading=13, spaceAfter=6,
        ),
        "score_big": s(
            "ScoreBig", fontName="Helvetica-Bold", fontSize=36, leading=40,
            textColor=_score_color(score), alignment=TA_CENTER, spaceAfter=2,
        ),
        "score_label": s(
            "ScoreLabel", fontName="Helvetica", fontSize=8, leading=11,
            textColor=C_MUTED, alignment=TA_CENTER, spaceBefore=4, spaceAfter=14,
        ),
        "stat_num": s(
            "StatNum", fontName="Helvetica-Bold", fontSize=18,
            textColor=C_INK, alignment=TA_CENTER, spaceAfter=0,
        ),
        "stat_lbl": s(
            "StatLbl", fontName="Helvetica", fontSize=7.5,
            textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=0,
        ),
        "footer": s(
            "Footer", fontName="Helvetica", fontSize=7.5,
            textColor=C_MUTED, alignment=TA_CENTER,
        ),
        "cell_claim": s(
            "CellClaim", fontName="Helvetica", fontSize=8,
            textColor=C_INK, leading=11,
        ),
        "cell_center": s(
            "CellCenter", fontName="Helvetica", fontSize=8,
            textColor=C_INK, leading=11, alignment=TA_CENTER,
        ),
        "empty_note": s(
            "EmptyNote", fontName="Helvetica-Oblique", fontSize=9.5,
            textColor=C_MUTED, alignment=TA_CENTER, spaceBefore=20, spaceAfter=10,
        ),
    }


def _rule(color=C_RULE, thickness=0.5, space=8) -> HRFlowable:
    return HRFlowable(width="100%", thickness=thickness, color=color,
                       spaceAfter=space, spaceBefore=space)


def _build_summary_section(sty: dict, results: list, score: int, counts: dict, total: int) -> list:
    elements = [Paragraph("Executive Summary", sty["section"])]

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
        TableStyle([
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
        ])
    )
    elements.append(stat_table)
    elements.append(Spacer(1, 10))

    if total:
        pct_reproduced = round(counts["reproduced"] / total * 100)
        elements.append(
            Paragraph(
                f"Of <b>{total}</b> statistical claim(s) examined, ReproHub successfully "
                f"reproduced <b>{counts['reproduced']}</b> ({pct_reproduced}%), "
                f"found <b>{counts['marginal']}</b> marginal result(s) within tolerance, "
                f"could not reproduce <b>{counts['not_reproduced']}</b>, and was unable "
                f"to verify <b>{counts['could_not_verify']}</b> due to insufficient data.",
                sty["body"],
            )
        )
    else:
        elements.append(Paragraph("No claims were examined in this run.", sty["body"]))

    elements.append(_rule())
    return elements


def _build_details_section(sty: dict, results: list, claim_lookup: dict) -> list:
    elements = [Paragraph("Detailed Results", sty["section"]), Spacer(1, 4)]

    if not results:
        elements.append(Paragraph("No per-claim results are available for this run.", sty["empty_note"]))
        return elements

    col_w = [2.15 * inch, 0.95 * inch, 1.05 * inch, 0.8 * inch, 0.9 * inch, 0.65 * inch]
    header = ["Claim", "Test", "Status", "Claimed p", "Repro. p", "Δ"]
    table_data = [header]
    status_per_row = []

    for r in results:
        cid = r.get("claim_id")
        # claim_lookup keys come from confirmed_claims / claims; cid may be
        # missing or unmatched, so always fall back to a safe placeholder.
        raw_claim_text = claim_lookup.get(cid) or cid or "Unlabeled claim"
        claim_text = _safe_text(raw_claim_text, "Unlabeled claim")

        status = r.get("status")
        label = STATUS_META.get(status, {}).get("label", _safe_text(status, "Unknown"))

        # Claim and Test are wrapped in real Paragraphs so long text wraps
        # within its own column instead of overflowing into the next one
        # (a bare string falls back to a default style that doesn't respect
        # the column width reliably).
        table_data.append([
            Paragraph(claim_text, sty["cell_claim"]),
            Paragraph(_safe_text(r.get("test_type")), sty["cell_center"]),
            label,
            _format_p(r.get("claimed_p_value")),
            _format_p(r.get("reproduced_p_value")),
            _format_p(r.get("discrepancy")),
        ])
        status_per_row.append(status)

    ts = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
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
    ])

    for i, status in enumerate(status_per_row, start=1):
        c = STATUS_COLORS.get(status, C_MUTED)
        ts.add("TEXTCOLOR", (2, i), (2, i), c)
        ts.add("FONTNAME", (2, i), (2, i), "Helvetica-Bold")

    table = Table(table_data, repeatRows=1, colWidths=col_w)
    table.setStyle(ts)
    elements.append(table)

    notes = [r for r in results if r.get("explanation")]
    if notes:
        elements.append(Spacer(1, 14))
        elements.append(_rule())
        elements.append(Paragraph("Verification Notes", sty["section"]))
        for r in notes:
            cid = _safe_text(r.get("claim_id"), "Unlabeled claim")
            ttype = _safe_text(r.get("test_type"), "")
            expl = _safe_text(r.get("explanation"), "")
            header_line = f"{cid} &nbsp;·&nbsp; {ttype}" if ttype else cid
            elements.append(
                KeepTogether([
                    Paragraph(header_line, sty["note_label"]),
                    Paragraph(expl, sty["note_body"]),
                ])
            )

    return elements


def _build_pdf(
    results: list,
    score: int,
    claim_lookup: dict,
    include_summary: bool,
    include_details: bool,
) -> bytes:
    """
    Render the verification results into a production-quality PDF.

    Raises ValueError if neither section is selected (caller is expected to
    have already validated this, but we don't trust that blindly).
    """
    if not include_summary and not include_details:
        raise ValueError("At least one report section must be selected.")

    results = results or []
    score = _safe_int(score, default=0)
    score = max(0, min(100, score))  # clamp into a sane display range
    claim_lookup = claim_lookup or {}

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.65 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        title="ReproHub Verification Report",
        author=config.APP_NAME,
    )

    sty = _build_styles(score)
    total = len(results)
    counts = {k: sum(1 for r in results if r.get("status") == k) for k in STATUS_ORDER}

    elements = []

    # ── Cover block ───────────────────────────────────────────────────────────
    elements.append(Paragraph("REPROHUB", sty["cover_brand"]))
    elements.append(Paragraph("Verification Report", sty["cover_title"]))
    elements.append(
        Paragraph(
            f"Generated {datetime.now().strftime('%B %d, %Y at %H:%M')} &nbsp;·&nbsp; "
            f"{xml_escape(str(config.APP_NAME))} v{xml_escape(str(config.APP_VERSION))}",
            sty["cover_sub"],
        )
    )
    elements.append(_rule(C_ACCENT, thickness=2, space=20))

    if include_summary:
        elements.extend(_build_summary_section(sty, results, score, counts, total))

    if include_details:
        elements.extend(_build_details_section(sty, results, claim_lookup))

    # ── Footer ────────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 20))
    elements.append(_rule(C_RULE, space=6))
    elements.append(
        Paragraph(
            f"Confidential · {xml_escape(str(config.APP_NAME))} v{xml_escape(str(config.APP_VERSION))} · "
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

/* ── Score Preview Panel ── */
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
    margin-bottom: 12px;
}
.ring-svg {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    filter: drop-shadow(0 0 20px rgba(91, 79, 232, 0.25));
}

/* ── Native Metric Override ── */
[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 12px !important;
    padding: 18px 10px !important;
    text-align: center !important;
    backdrop-filter: blur(4px) !important;
    transition: all 0.2s ease !important;
}
[data-testid="stMetric"]:hover {
    background: rgba(255, 255, 255, 0.06) !important;
    border-color: rgba(255, 255, 255, 0.12) !important;
}
[data-testid="stMetric"] .stMetricValue {
    font-size: 28px !important;
    font-weight: 700 !important;
    line-height: 1 !important;
    padding: 0 !important;
    margin-top: 4px !important;
}
[data-testid="stMetric"] .stMetricLabel {
    font-size: 11px !important;
    color: #94A3B8 !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* ── Legend ── */
.legend-container {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 12px 20px;
    margin-top: 20px;
    padding: 14px 20px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 12px;
    width: 100%;
    border: 1px solid rgba(255, 255, 255, 0.05);
}
.legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
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
    font-weight: 700;
}

/* ── Footer Meta ── */
.meta-text {
    font-size: 11px;
    color: #475569;
    text-align: center;
    margin-top: 18px;
}

/* ── Divider ── */
.rh-divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.06);
    margin: 28px 0;
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
.generate-wrapper .stButton > button:disabled {
    opacity: 0.45 !important;
    cursor: not-allowed !important;
    transform: none !important;
    box-shadow: none !important;
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

/* ── Success / Warning / Error ── */
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
.error-banner {
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 14px;
    padding: 14px 18px;
    margin-top: 16px;
    font-size: 13px;
    color: #FCA5A5;
}
.stale-banner {
    background: rgba(91, 79, 232, 0.08);
    border: 1px solid rgba(91, 79, 232, 0.25);
    border-radius: 14px;
    padding: 12px 18px;
    margin-top: 14px;
    font-size: 12.5px;
    color: #C4B5FD;
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

/* ── Spinner Override ── */
.stSpinner { color: #7C3AED !important; }
</style>
"""


def _score_ring_svg(score: int) -> str:
    """
    Generate an SVG score ring with a smooth CSS draw animation.
    `score` is clamped to 0-100 so malformed upstream data can't produce a
    negative dash-offset or an oversized/invalid stroke.
    """
    score = max(0, min(100, _safe_int(score, default=0)))

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
    <svg class="ring-svg" viewBox="0 0 136 136" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Reproducibility score {score} percent">
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


def _render_header():
    st.markdown("""
    <div class="report-header">
      <div class="report-icon-wrapper">📄</div>
      <div>
        <div class="report-title">Generate Report</div>
        <div class="report-subtitle">Export a professional PDF summarising your verification results</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _render_empty_state():
    st.markdown("""
    <div class="empty-state">
      <div class="empty-icon">🔬</div>
      <div class="empty-title">No analysis results yet</div>
      <div class="empty-sub">Upload a paper and verify its claims first,<br>then return here to generate your report.</div>
    </div>
    """, unsafe_allow_html=True)


def _render_config_panel(counts: dict) -> tuple:
    st.markdown('<div class="glass-panel config-panel">', unsafe_allow_html=True)
    st.markdown('<div class="config-title">Report Sections</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="option-card">
      <div class="option-icon">📋</div>
      <div>
        <div class="option-content-title">Executive Summary</div>
        <div class="option-content-desc">Score overview and per-status breakdown</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    include_summary = st.checkbox(
        "Include executive summary", value=True, key="cb_summary",
        label_visibility="collapsed",
    )

    st.markdown("""
    <div class="option-card">
      <div class="option-icon">📊</div>
      <div>
        <div class="option-content-title">Detailed Results</div>
        <div class="option-content-desc">Per-claim table with p-values and discrepancy</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    include_details = st.checkbox(
        "Include detailed results", value=True, key="cb_details",
        label_visibility="collapsed",
    )

    st.markdown('<div class="rh-divider"></div>', unsafe_allow_html=True)

    legend_html = '<div class="legend-container">'
    for key in STATUS_ORDER:
        meta = STATUS_META[key]
        legend_html += (
            f'<div class="legend-item">'
            f'<div class="legend-dot" style="background:{meta["hex"]};"></div>'
            f'{meta["label"]}: <span class="legend-val">{counts.get(key, 0)}</span>'
            f'</div>'
        )
    legend_html += '</div>'
    st.markdown(legend_html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    return include_summary, include_details


def _render_score_preview(score: int, counts: dict, total: int):
    st.markdown('<div class="glass-panel score-preview-panel">', unsafe_allow_html=True)

    ring_svg = _score_ring_svg(score)
    st.markdown(f'<div class="ring-container">{ring_svg}</div>', unsafe_allow_html=True)

    display_score = max(0, min(100, _safe_int(score, default=0)))
    st.markdown(f"""
    <div style="text-align:center; margin-bottom: 20px;">
        <div style="font-size: 36px; font-weight: 700; color: #F8FAFC; line-height: 1.2; letter-spacing: -0.02em;">{display_score}%</div>
        <div style="font-size: 11px; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; color: #64748B; margin-top: 2px;">Reproducibility Score</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Reproduced", value=counts.get("reproduced", 0))
    with col2:
        st.metric(label="Marginal", value=counts.get("marginal", 0))

    col3, col4 = st.columns(2)
    with col3:
        st.metric(label="Not Reproduced", value=counts.get("not_reproduced", 0))
    with col4:
        st.metric(label="Unverifiable", value=counts.get("could_not_verify", 0))

    st.markdown(f"""
    <div class="meta-text">
        {total} claim{"s" if total != 1 else ""} examined &nbsp;·&nbsp;
        {datetime.now().strftime('%Y-%m-%d %H:%M')}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render():
    st.markdown(_CSS, unsafe_allow_html=True)
    _render_header()

    if not st.session_state.get("analysis_complete"):
        _render_empty_state()
        return

    results = st.session_state.get("results") or []
    score = _safe_int(st.session_state.get("reproducibility_score"), default=0)
    total = len(results)

    if not results:
        st.markdown(
            '<div class="warning-banner">⚠️ Analysis is marked complete, but no claim '
            'results were found. Try re-running verification.</div>',
            unsafe_allow_html=True,
        )
        return

    claims = st.session_state.get("confirmed_claims") or st.session_state.get("claims") or []
    claim_lookup = {
        c.get("id"): c.get("claim_statement") or c.get("id")
        for c in claims
        if isinstance(c, dict) and c.get("id") is not None
    }

    counts = {k: sum(1 for r in results if r.get("status") == k) for k in STATUS_ORDER}

    # If results have changed since the last PDF was generated (different
    # claim count or score), the cached PDF is stale — surface that instead
    # of silently letting the user download an outdated report.
    fingerprint = (total, score, tuple(counts[k] for k in STATUS_ORDER))
    is_stale = (
        st.session_state.get("report_generated")
        and st.session_state.get("report_fingerprint") != fingerprint
    )

    col_config, col_preview = st.columns([1.05, 0.95], gap="large")

    with col_config:
        include_summary, include_details = _render_config_panel(counts)

    with col_preview:
        _render_score_preview(score, counts, total)

    st.markdown('<div class="rh-divider"></div>', unsafe_allow_html=True)

    if not include_summary and not include_details:
        st.markdown(
            '<div class="warning-banner">⚠️ Select at least one section to include in the report.</div>',
            unsafe_allow_html=True,
        )
        return

    if is_stale:
        st.markdown(
            '<div class="stale-banner">ℹ️ Your verification results have changed since '
            'this report was generated. Regenerate to capture the latest results.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="generate-wrapper">', unsafe_allow_html=True)
    generate = st.button("Generate PDF Report", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if generate:
        with st.spinner("Building your professional report…"):
            try:
                pdf_bytes = _build_pdf(
                    results, score, claim_lookup, include_summary, include_details,
                )
            except Exception:
                logger.exception("PDF report generation failed")
                st.markdown(
                    '<div class="error-banner">✕ Something went wrong while building the '
                    'report. Please try again, or contact support if this persists.</div>',
                    unsafe_allow_html=True,
                )
                if config.DEBUG:
                    st.exception(__import__("sys").exc_info()[1])
                return

        st.session_state.report_generated = True
        st.session_state.report_data = pdf_bytes
        st.session_state.report_fingerprint = fingerprint
        st.session_state.report_generated_at = datetime.now()

        st.markdown(
            '<div class="success-banner">✅ &nbsp; Report generated successfully — ready to download.</div>',
            unsafe_allow_html=True,
        )

    if st.session_state.get("report_generated") and st.session_state.get("report_data"):
        generated_at = st.session_state.get("report_generated_at") or datetime.now()
        fname = generated_at.strftime(DOWNLOAD_FILENAME_FMT)
        st.markdown('<div class="download-wrapper">', unsafe_allow_html=True)
        st.download_button(
            label="⬇ Download PDF",
            data=st.session_state.report_data,
            file_name=fname,
            mime="application/pdf",
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
