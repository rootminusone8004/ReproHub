"""
Report Page — Real PDF Report Generation

Builds an actual PDF from the real verification results (core.comparator's
output, stored in st.session_state.results) using ReportLab - no more
placeholder bytes. The PDF includes an executive summary and/or a detailed
per-claim results table, depending on which sections the user selects.
"""

import io
from datetime import datetime

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.config import config

STATUS_LABELS = {
    "reproduced": "✅ Reproduced",
    "marginal": "⚠️ Marginal",
    "not_reproduced": "❌ Not Reproduced",
    "could_not_verify": "❓ Could Not Verify",
}


def _format_p(value) -> str:
    return f"{value:.4f}" if value is not None else "—"


def _build_pdf(results: list, score: int, claim_lookup: dict,
                include_summary: bool, include_details: bool) -> bytes:
    """Render the verification results into a PDF and return its bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], spaceAfter=4)
    subtitle_style = ParagraphStyle(
        "ReportSubtitle", parent=styles["Normal"], textColor=colors.grey, spaceAfter=20
    )

    elements = [
        Paragraph("ReproHub Verification Report", title_style),
        Paragraph(
            f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} "
            f"&middot; {config.APP_NAME} v{config.APP_VERSION}",
            subtitle_style,
        ),
    ]

    total = len(results)
    counts = {key: sum(1 for r in results if r.get("status") == key) for key in STATUS_LABELS}

    if include_summary:
        elements.append(Paragraph("Executive Summary", styles["Heading2"]))
        elements.append(Paragraph(
            f"Of <b>{total}</b> statistical claim(s) checked, ReproHub reproduced "
            f"<b>{counts['reproduced']}</b>, found <b>{counts['marginal']}</b> marginal, "
            f"could not reproduce <b>{counts['not_reproduced']}</b>, and could not verify "
            f"<b>{counts['could_not_verify']}</b>.",
            styles["Normal"],
        ))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"Reproducibility Score: <b>{score}%</b>", styles["Heading3"]))
        elements.append(Spacer(1, 16))

    if include_details:
        elements.append(Paragraph("Detailed Results", styles["Heading2"]))
        elements.append(Spacer(1, 8))

        table_data = [["Claim", "Test", "Status", "Claimed p", "Reproduced p", "\u0394"]]
        for r in results:
            claim_text = claim_lookup.get(r.get("claim_id"), r.get("claim_id", "—"))
            if len(claim_text) > 50:
                claim_text = claim_text[:47] + "..."
            table_data.append([
                claim_text,
                r.get("test_type", "—"),
                STATUS_LABELS.get(r.get("status"), r.get("status", "—")),
                _format_p(r.get("claimed_p_value")),
                _format_p(r.get("reproduced_p_value")),
                _format_p(r.get("discrepancy")),
            ])

        table = Table(
            table_data,
            repeatRows=1,
            colWidths=[1.9 * inch, 1.0 * inch, 1.1 * inch, 0.8 * inch, 0.9 * inch, 0.7 * inch],
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e2327")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
        ]))
        elements.append(table)

        # Explanations are only populated for could_not_verify results
        # (see core/comparator.py) - surface them so the report explains
        # *why*, not just *that*, a claim couldn't be checked.
        notes = [r for r in results if r.get("explanation")]
        if notes:
            elements.append(Spacer(1, 16))
            elements.append(Paragraph("Notes", styles["Heading3"]))
            for r in notes:
                elements.append(Paragraph(
                    f"<b>{r.get('claim_id')}</b> ({r.get('test_type')}): {r['explanation']}",
                    styles["Normal"],
                ))
                elements.append(Spacer(1, 4))

    doc.build(elements)
    return buffer.getvalue()


def render():
    st.title("📄 Generate Report")

    if not st.session_state.analysis_complete:
        st.info("🔬 No analysis results found. Please upload and verify claims first.")
        return

    st.markdown("Generate a professional report summarizing the verification results.")
    st.divider()

    results = st.session_state.results
    score = st.session_state.reproducibility_score

    # confirmed_claims (set by the Review page after verification) gives
    # the full claim_statement text for the report; fall back to claims
    # if verification was somehow run without going through Review.
    claims = st.session_state.get("confirmed_claims") or st.session_state.get("claims") or []
    claim_lookup = {c.get("id"): c.get("claim_statement") or c.get("id") for c in claims}

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📋 Report Options")
        include_summary = st.checkbox("Include executive summary", value=True)
        include_details = st.checkbox("Include detailed results", value=True)

    with col2:
        st.subheader("📊 Summary")
        st.metric("Reproducibility Score", f"{score}%")
        st.caption(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    st.divider()

    if not include_summary and not include_details:
        st.warning("Select at least one section to include in the report.")
        return

    if st.button("📄 Generate Report", type="primary"):
        with st.spinner("Generating report..."):
            try:
                pdf_bytes = _build_pdf(results, score, claim_lookup, include_summary, include_details)
            except Exception as exc:
                st.error(f"Couldn't generate the report: {exc}")
                if config.DEBUG:
                    st.exception(exc)
                return

            st.session_state.report_generated = True
            st.session_state.report_data = pdf_bytes

        st.success("✅ Report generated successfully!")

    if st.session_state.get("report_generated") and st.session_state.get("report_data"):
        st.download_button(
            label="📥 Download PDF",
            data=st.session_state.report_data,
            file_name=f"reprohub_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
        )
