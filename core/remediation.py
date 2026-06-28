"""
Remediation Guidance - Provides actionable advice for failed claims.
"""

def generate_remediation(result: dict) -> str:
    """Generate remediation guidance for a claim result."""
    status = result.get("status", "unknown")
    
    if status == "reproduced":
        return "✅ Claim reproduced successfully. No action needed."
    
    if status == "not_reproduced":
        return """
        ❌ Claim did not reproduce. Possible reasons:
        - Normality assumption may have been violated
        - Sample size may be insufficient
        - Check for outliers in the data
        - Consider using a non-parametric alternative
        """
    
    return "⚠️ Unable to generate remediation guidance."
