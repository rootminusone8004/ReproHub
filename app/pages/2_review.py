"""
Review Page — Review and Confirm Claims
"""

import streamlit as st
import json
from app.config import config


def render():
    st.title("📋 Review Claims")

    if not st.session_state.claims:
        st.info("📤 No claims found. Please upload a paper and extract claims first.")
        return

    if st.session_state.dataset_df is None:
        st.warning("📊 No dataset found.")
        return

    st.markdown(f"**{len(st.session_state.claims)}** claims extracted from the paper.")
    st.markdown("Review each claim before running verification.")
    st.divider()

    claims = st.session_state.claims
    all_confirmed = True

    for idx, claim in enumerate(claims):
        with st.expander(f"Claim {idx + 1}: {claim.get('claim_statement', 'Untitled')}", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Test Type**")
                st.code(claim.get("test_type", "Unknown"))
                st.markdown("**Claimed P-Value**")
                st.metric("p-value", f"{claim.get('claimed_p_value', 'N/A')}")
                st.markdown("**Claimed Effect Size**")
                st.metric("effect size", f"{claim.get('claimed_effect_size', 'N/A')}")

            with col2:
                st.markdown("**Claim Statement**")
                st.info(claim.get("claim_statement", "No statement provided"))
                confidence = claim.get("extraction_confidence", "unknown")
                if confidence == "high":
                    st.success("✅ High confidence")
                elif confidence == "medium":
                    st.warning("⚠️ Medium confidence")
                else:
                    st.error("❌ Low confidence")

            st.divider()
            st.markdown("**Column Mapping**")

            params = claim.get("params", {})
            for key, value in params.items():
                if isinstance(value, str) and st.session_state.dataset_df is not None:
                    if value in st.session_state.dataset_df.columns:
                        st.success(f"✅ `{key}` → `{value}` (found)")
                    else:
                        st.warning(f"⚠️ `{key}` → `{value}` (column not found)")

            confirm_key = f"confirm_{idx}"
            confirmed = st.checkbox(f"✅ Confirm Claim {idx + 1}", key=confirm_key)
            if not confirmed:
                all_confirmed = False

    st.divider()

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        confirmed_count = sum(1 for i in range(len(claims)) if st.session_state.get(f"confirm_{i}", False))
        st.metric("Confirmed", f"{confirmed_count}/{len(claims)}")

    with col3:
        if all_confirmed:
            if st.button("🔬 Run Verification", type="primary", use_container_width=True):
                with st.spinner("Running verification..."):
                    # Mock results
                    results = []
                    for claim in claims:
                        results.append({
                            "claim_id": claim.get("id", "unknown"),
                            "test_type": claim.get("test_type", "unknown"),
                            "status": "reproduced" if len(results) % 2 == 0 else "not_reproduced",
                            "claimed_p_value": claim.get("claimed_p_value", 0.05),
                            "reproduced_p_value": claim.get("claimed_p_value", 0.05) + 0.01,
                            "discrepancy": 0.01
                        })
                    st.session_state.results = results
                    st.session_state.reproducibility_score = 67
                    st.session_state.analysis_complete = True
                    st.session_state.review_complete = True
                    st.success("✅ Verification complete!")
                    st.rerun()
        else:
            st.warning("Please confirm all claims before running verification")
