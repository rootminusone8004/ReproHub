"""Report generation utilities."""

def generate_report(results: list, score: int) -> str:
    """Generate a report from results."""
    report = f"""
    REPROHUB VERIFICATION REPORT
    ============================
    Reproducibility Score: {score}%
    
    Results Summary:
    - Total Claims: {len(results)}
    """
    return report
