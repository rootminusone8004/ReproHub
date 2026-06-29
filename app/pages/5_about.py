"""
About Page — Help and Documentation
"""

import streamlit as st
from datetime import datetime
from app.config import config
from core.engine import StatisticalTestEngine

# Display names for each supported test_type. Previously this page had
# its own separate, hardcoded list of 8 tests that silently went stale
# once core/engine.py grew to support 11 (Kruskal-Wallis, Wilcoxon
# signed-rank, and logistic regression were added but never reflected
# here). Listing every key from SUPPORTED_TESTS below, rather than
# hardcoding a parallel list, means this page can't drift out of sync
# with the engine again - if a test is added or removed there, it's
# either already covered by this map or shows up as a clear KeyError
# during development rather than silently being missing from the UI.
_TEST_DISPLAY_NAMES = {
    "t_test_independent": "Independent t-test",
    "paired_t_test": "Paired t-test",
    "one_way_anova": "One-way ANOVA",
    "chi_square": "Chi-square test",
    "pearson_correlation": "Pearson correlation",
    "spearman_correlation": "Spearman correlation",
    "mann_whitney_u": "Mann-Whitney U",
    "kruskal_wallis": "Kruskal-Wallis H",
    "wilcoxon_signed_rank": "Wilcoxon signed-rank",
    "linear_regression": "Linear regression",
    "logistic_regression": "Logistic regression",
}


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
    """)

    supported = StatisticalTestEngine.SUPPORTED_TESTS
    missing_display_names = supported - _TEST_DISPLAY_NAMES.keys()
    if missing_display_names:
        # Surfaced visibly rather than silently skipped, so a newly
        # added test in the engine is impossible to forget about here.
        st.warning(
            f"⚠️ Engine supports test(s) with no display name configured: "
            f"{sorted(missing_display_names)}. Add them to _TEST_DISPLAY_NAMES "
            "in this file."
        )

    test_list_md = "\n".join(
        f"- {_TEST_DISPLAY_NAMES[t]}"
        for t in sorted(supported)
        if t in _TEST_DISPLAY_NAMES
    )
    st.markdown(test_list_md)

    st.divider()
    st.caption(f"© {datetime.now().year} Junaid Ahmed Rupok · MIT License")
