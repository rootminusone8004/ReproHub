"""
PDF text extraction utilities.

Extracts raw text from uploaded research-paper PDFs so downstream code
(core/extractor.py) can run pattern matching over it to find statistical
claims (t-tests, ANOVA, correlations, etc.).
"""

from io import BytesIO
from typing import Union

import pdfplumber


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be opened or contains no extractable text."""


def extract_text_from_pdf(pdf_file: Union[BytesIO, str, bytes]) -> str:
    """
    Extract all text from a PDF file, page by page.

    Args:
        pdf_file: A file-like object (e.g. a Streamlit UploadedFile or an
            open binary stream), a path to a PDF on disk, or raw PDF bytes.

    Returns:
        The full extracted text, with each page's text separated by a
        blank line so multi-page claims/sections don't visually run
        together.

    Raises:
        PDFExtractionError: if the file can't be opened/parsed (e.g. it's
            corrupted, password-protected, or not actually a PDF), or if
            no text could be extracted at all (e.g. a purely scanned/
            image-only PDF with no OCR layer).
    """
    # Streamlit's UploadedFile is a BytesIO-like stream but its read
    # position may have already been consumed by a previous read (e.g.
    # st.file_uploader preview, file-size check). Reset it defensively
    # so we always read from the start.
    if hasattr(pdf_file, "seek"):
        pdf_file.seek(0)

    if isinstance(pdf_file, bytes):
        pdf_file = BytesIO(pdf_file)

    try:
        with pdfplumber.open(pdf_file) as pdf:
            if len(pdf.pages) == 0:
                raise PDFExtractionError("The PDF has no pages.")

            page_texts = []
            for page in pdf.pages:
                # x_tolerance/y_tolerance defaults are fine for normal
                # academic paper layouts (single or two-column text).
                text = page.extract_text() or ""
                page_texts.append(text)
    except PDFExtractionError:
        raise
    except Exception as exc:
        # pdfplumber/pypdfium2 can raise a variety of exception types for
        # malformed, encrypted, or non-PDF input. Normalize all of them
        # into one clear, catchable error type for callers (e.g. the
        # Upload page) instead of leaking library-specific exceptions.
        raise PDFExtractionError(f"Could not read PDF: {exc}") from exc

    full_text = "\n\n".join(page_texts).strip()

    if not full_text:
        raise PDFExtractionError(
            "No text could be extracted from this PDF. It may be a "
            "scanned/image-only document with no selectable text layer."
        )

    return full_text
