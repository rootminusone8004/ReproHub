"""
Dashboard Page — Results Visualization
"""

import streamlit as st
import pandas as pd
import plotly.express as px


def render():
    st.title("📊 Verification Dashboard")

    if not st.session_state.analysis_complete:
        st.info("🔬 No analysis results found. Please upload and verify claims first.")
        return

    results = st.session_state.results
    score = st.session_state.reproducibility_score

    st.subheader("📈 Summary")

    total = len(results)
    reproduced = sum(1 for r in results if r.get("status") == "reproduced")
    not_reproduced = sum(1 for r in results if r.get("status") == "not_reproduced")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("🎯 Score", f"{score}%")
    with col2:
        st.metric("✅ Reproduced", reproduced)
    with col3:
        st.metric("❌ Not Reproduced", not_reproduced)

    st.divider()

    results_df = pd.DataFrame(results)
    st.dataframe(results_df, use_container_width=True)

    # Visualization
    if results:
        fig = px.pie(
            values=[reproduced, not_reproduced],
            names=["Reproduced", "Not Reproduced"],
            title="Reproducibility Status",
            color_discrete_sequence=["#28a745", "#dc3545"]
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("📥 Export Options")

    if st.button("📄 Download Results (CSV)"):
        results_df.to_csv("reprohub_results.csv", index=False)
        st.success("✅ Results downloaded!")
