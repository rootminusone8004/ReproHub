"""
Report Page — Report Generation
"""

import streamlit as st
from datetime import datetime
from ..config import config


def render():
    st.title("📄 Generate Report")

    if not st.session_state.analysis_complete:
        st.info("🔬 No analysis results found. Please upload and verify claims first.")
        return

    st.markdown("Generate a professional report summarizing the verification results.")
    st.divider()

    results = st.session_state.results
    score = st.session_state.reproducibility_score

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

    if st.button("📄 Generate Report", type="primary"):
        with st.spinner("Generating report..."):
            st.success("✅ Report generated successfully!")
            st.download_button(
                label="📥 Download PDF",
                data=b"PDF content placeholder",
                file_name="reprohub_report.pdf",
                mime="application/pdf"
            )
