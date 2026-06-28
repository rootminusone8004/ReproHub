
"""File upload and download utilities."""

import pandas as pd
import streamlit as st

def read_csv_file(file) -> pd.DataFrame:
    """Read a CSV file and return a DataFrame."""
    return pd.read_csv(file)

def download_results(results: list, filename: str = "results.csv"):
    """Download results as CSV."""
    df = pd.DataFrame(results)
    return df.to_csv(index=False)
