"""
Review Page — Review Claims, Fix Column Mappings, Run Real Verification

core.matcher's fuzzy matching (run on the Upload page) only gets a claim's
params right some of the time - this page is where the user checks its
work and fixes anything wrong before core.comparator actually runs the
tests. Verification is run for real via core.comparator.ComparisonEngine;
there is no mock result generation here anymore.
"""

import streamlit as st

from core.matcher import classify_columns
from core.comparator import ComparisonEngine

# Param slots each test type needs, and which column pool (numeric vs
# categorical) each slot should be picked from. Mirrors core/engine.py's
# _run_* signatures and core/matcher.py's test groupings.
REQUIRED_PARAMS = {
    "t_test_independent": [("group_col", "categorical"), ("value_col", "numeric")],
    "paired_t_test": [("col1", "numeric"), ("col2", "numeric")],
    "one_way_anova": [("group_col", "categorical"), ("value_col", "numeric")],
    "pearson_correlation": [("col1", "numeric"), ("col2", "numeric")],
    "spearman_correlation": [("col1", "numeric"), ("col2", "numeric")],
    "chi_square": [("col1", "categorical"), ("col2", "categorical")],
    "mann_whitney_u": [("group_col", "categorical"), ("value_col", "numeric")],
}

_PLACEHOLDER = "— select a column —"


def _render_column_mapping(idx: int, claim: dict, pools: dict) -> bool:
    """
    Render editable column-mapping selectboxes for one claim, writing any
    changes straight back into st.session_state.claims[idx]['params'].

    Returns True if every required param slot for this claim's test_type
    is filled with a real column, False otherwise.
    """
    test_type = claim.get("test_type", "")
    slots = REQUIRED_PARAMS.get(test_type)
    params = claim.get("params", {}) or {}

    if slots is None:
        st.error(f"Unsupported test type `{test_type}` — cannot map columns or run this test.")
        return False

    all_filled = True
    for param_key, pool_name in slots:
        options = pools[pool_name]
        current = params.get(param_key)

        # Offer the proposed match first (even if it came from a different
        # pool, e.g. matcher guessed wrong) so the user's existing pick
        # isn't silently dropped from the dropdown.
        choices = [_PLACEHOLDER] + options
        if current and current not in choices:
            choices.insert(1, current)

        default_index = choices.index(current) if current in choices else 0

        selected = st.selectbox(
            f"`{param_key}` ({pool_name} column)",
            choices,
            index=default_index,
            key=f"param_{idx}_{param_key}",
        )

        if selected == _PLACEHOLDER:
            all_filled = False
        else:
            params[param_key] = selected

    claim["params"] = params
    return all_filled


def render():
    st.title("📋 Review Claims")

    if not st.session_state.claims:
        st.info("📤 No claims found. Please upload a paper and extract claims first.")
        return

    if st.session_state.dataset_df is None:
        st.warning("📊 No dataset found.")
        return

    dataset_df = st.session_state.dataset_df
    pools = classify_columns(dataset_df)

    st.markdown(f"**{len(st.session_state.claims)}** claims extracted from the paper.")
    st.markdown("Review each claim, fix any column mapping the automatic matcher got wrong, then confirm it.")
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
            match_confidence = claim.get("match_confidence")
            if match_confidence and match_confidence != "high":
                st.caption(
                    "The automatic matcher couldn't confidently fill in every column for "
                    "this claim — double-check the selections below."
                )

            mapping_complete = _render_column_mapping(idx, claim, pools)

            confirm_key = f"confirm_{idx}"
            confirm_disabled = not mapping_complete
            if confirm_disabled:
                st.warning("Select a real column for every field above before confirming this claim.")

            confirmed = st.checkbox(
                f"✅ Confirm Claim {idx + 1}",
                key=confirm_key,
                disabled=confirm_disabled,
                value=st.session_state.get(confirm_key, False) and mapping_complete,
            )
            if not confirmed:
                all_confirmed = False

    st.session_state.claims = claims

    st.divider()

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        confirmed_count = sum(1 for i in range(len(claims)) if st.session_state.get(f"confirm_{i}", False))
        st.metric("Confirmed", f"{confirmed_count}/{len(claims)}")

    with col3:
        if all_confirmed:
            if st.button("🔬 Run Verification", type="primary", use_container_width=True):
                with st.spinner("Running statistical tests against the dataset..."):
                    engine = ComparisonEngine(dataset_df)
                    results = engine.run_all(claims)

                    verifiable = [r for r in results if r["status"] != "could_not_verify"]
                    reproduced = sum(1 for r in verifiable if r["status"] == "reproduced")
                    score = round(100 * reproduced / len(verifiable)) if verifiable else 0

                    st.session_state.confirmed_claims = claims
                    st.session_state.results = results
                    st.session_state.reproducibility_score = score
                    st.session_state.analysis_complete = True
                    st.session_state.review_complete = True

                    could_not_verify = len(results) - len(verifiable)
                    st.success("✅ Verification complete!")
                    if could_not_verify:
                        st.info(
                            f"{could_not_verify} claim(s) could not be verified and were "
                            "excluded from the score — see the Dashboard for details."
                        )
                    st.rerun()
        else:
            st.warning("Please confirm all claims before running verification")
