import streamlit as st
import pandas as pd
from ..config import config


def render():
    st.title("📤 Upload Files")
    st.markdown("Upload your research paper and dataset to begin verification.")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📄 Research Paper")
        paper_file = st.file_uploader("Choose a PDF file", type=["pdf"], key="paper_uploader")
        if paper_file:
            if paper_file.size > config.MAX_FILE_SIZE_BYTES:
                st.error(f"File too large. Max size: {config.MAX_FILE_SIZE_MB}MB")
                return
            st.success(f"✅ {paper_file.name} uploaded")
            st.session_state.paper_file = paper_file

    with col2:
        st.subheader("📊 Dataset")
        dataset_file = st.file_uploader("Choose a CSV file", type=["csv"], key="dataset_uploader")
        if dataset_file:
            try:
                df = pd.read_csv(dataset_file)
                st.success(f"✅ {dataset_file.name} uploaded ({len(df)} rows, {len(df.columns)} columns)")
                with st.expander("📊 Dataset Preview (first 5 rows)"):
                    st.dataframe(df.head(), use_container_width=True)
                st.session_state.dataset_file = dataset_file
                st.session_state.dataset_df = df
            except Exception as e:
                st.error(f"Error: {str(e)}")

    st.divider()

    if st.session_state.paper_file and st.session_state.dataset_df is not None:
        if st.button("🔍 Extract Claims (Mock)", type="primary"):
            with st.spinner("Extracting claims (using mock data)..."):
                df = st.session_state.dataset_df
                col_names = df.columns.tolist()

                mock_claims = [
                    {
                        "id": "claim_1",
                        "test_type": "t_test_independent",
                        "claimed_p_value": 0.03,
                        "claimed_effect_size": 0.45,
                        "params": {
                            "group_col": col_names[0],
                            "value_col": col_names[1] if len(col_names) > 1 else col_names[0],
                            "group1": str(df.iloc[0, 0]) if len(df) > 0 else "A",
                            "group2": str(df.iloc[1, 0]) if len(df) > 1 else "B"
                        },
                        "claim_statement": "Treatment significantly improved scores compared to control",
                        "source": "mock_extracted",
                        "extraction_confidence": "high"
                    },
                    {
                        "id": "claim_2",
                        "test_type": "pearson_correlation",
                        "claimed_p_value": 0.01,
                        "claimed_effect_size": 0.60,
                        "params": {
                            "col1": col_names[0],
                            "col2": col_names[1] if len(col_names) > 1 else col_names[0]
                        },
                        "claim_statement": "Age is positively correlated with scores",
                        "source": "mock_extracted",
                        "extraction_confidence": "medium"
                    }
                ]

                st.session_state.claims = mock_claims
                st.session_state.extraction_complete = True
                st.success(f"✅ Extracted {len(mock_claims)} mock claims from the paper!")
                st.rerun()
    else:
        st.warning("Please upload both a paper (PDF) and a dataset (CSV) to continue.")
