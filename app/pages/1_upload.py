"""
Upload Page — File Upload and Real Claim Extraction

Wires the actual pipeline together:
    utils.pdf_parser.extract_text_from_pdf   -> raw text from the PDF
    core.extractor.extract_claims_from_paper -> regex-extracted claims (params empty)
    core.matcher.match_all_claims            -> fuzzy-matches claim text to dataset columns

No mock data - everything that lands in st.session_state.claims comes from
the uploaded paper and dataset themselves.
"""

import streamlit as st
import pandas as pd

from app.config import config
from utils.pdf_parser import extract_text_from_pdf, PDFExtractionError
from core.extractor import extract_claims_from_paper
from core.matcher import match_all_claims


def render():
    st.title("📤 Upload Files")
    st.markdown("Upload your research paper and dataset to begin verification.")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📄 Research Paper")
        paper_file = st.file_uploader("Choose a PDF file", type=["pdf"], key="paper_uploader")
        if paper_file:
            if not config.check_file_size(paper_file.size):
                st.error(f"File too large. Max size: {config.MAX_FILE_SIZE_MB}MB")
                return
            st.success(f"✅ {paper_file.name} uploaded")
            st.session_state.paper_file = paper_file

    with col2:
        st.subheader("📊 Dataset")
        # Accept both extensions config.py actually declares as allowed
        # (previously only .csv was wired up here despite .xlsx being
        # listed in config.ALLOWED_DATA_EXTENSIONS) - and read each with
        # the function that actually understands its format.
        dataset_file = st.file_uploader(
            "Choose a CSV or Excel file", type=["csv", "xlsx"], key="dataset_uploader"
        )
        if dataset_file:
            # Dataset size was never checked at all before - only the
            # paper file was. config.check_file_size() already existed
            # for exactly this purpose.
            if not config.check_file_size(dataset_file.size):
                st.error(f"File too large. Max size: {config.MAX_FILE_SIZE_MB}MB")
                return
            try:
                if dataset_file.name.lower().endswith(".xlsx"):
                    df = pd.read_excel(dataset_file)
                else:
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
        if st.button("🔍 Extract Claims", type="primary"):
            with st.spinner("Reading PDF and extracting statistical claims..."):
                # 1. Pull raw text out of the uploaded PDF.
                try:
                    paper_text = extract_text_from_pdf(st.session_state.paper_file)
                except PDFExtractionError as exc:
                    st.error(f"Couldn't read the PDF: {exc}")
                    return

                st.session_state.paper_text = paper_text

                # 2. Regex-extract APA-style statistical claims from the text.
                claims = extract_claims_from_paper(paper_text)

                if not claims:
                    st.warning(
                        "No statistical claims were found in this PDF. "
                        "ReproHub looks for conventional APA-style notation "
                        "(e.g. `t(98) = 2.43, p = .03`) - papers that report "
                        "results purely in prose won't be picked up automatically."
                    )
                    return

                # 3. Fuzzy-match each claim's text against the dataset's
                # columns to propose params (group_col, value_col, etc.).
                claims = match_all_claims(claims, st.session_state.dataset_df)

                st.session_state.claims = claims
                st.session_state.extraction_complete = True

                high_conf = sum(1 for c in claims if c.get("match_confidence") == "high")
                st.success(f"✅ Extracted {len(claims)} claim(s) from the paper.")
                if high_conf < len(claims):
                    st.info(
                        f"{high_conf}/{len(claims)} claim(s) had all dataset columns "
                        "matched automatically. Review the rest on the next page before "
                        "running verification."
                    )
                st.rerun()
    else:
        st.warning("Please upload both a paper (PDF) and a dataset (CSV) to continue.")
