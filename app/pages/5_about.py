"""
About Page — Help and Documentation
"""

import streamlit as st
from datetime import datetime
from app.config import config


def render():
    st.title("ℹ️ About ReproHub")

    st.markdown(f"""
    ### 🔬 {config.APP_NAME}

    **{config.APP_DESCRIPTION}**

    Version: {config.APP_VERSION}
    Author: Junaid Ahmed Rupok

    ### How It Works

    1. 📄 Upload paper (PDF) and dataset (CSV)
    2. 📋 Review extracted claims
    3. 🔬 Run verification
    4. 📊 View dashboard
    5. 📄 Download report

    ### Supported Tests

    - Independent t-test
    - Paired t-test
    - One-way ANOVA
    - Chi-square test
    - Pearson correlation
    - Spearman correlation
    - Linear regression
    - Mann-Whitney U
    """)

    st.divider()
    st.caption(f"© {datetime.now().year} Junaid Ahmed Rupok · MIT License")
