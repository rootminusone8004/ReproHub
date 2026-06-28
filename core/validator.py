"""
Claim Validation - Ensures claims are properly formatted.
"""

from core.schema import ClaimValidator

def validate_claim(claim: dict) -> tuple[bool, str]:
    """Validate a single claim."""
    return ClaimValidator.validate(claim)

def validate_all_claims(claims: list) -> list:
    """Validate all claims and return valid ones."""
    valid_claims = []
    for claim in claims:
        is_valid, message = validate_claim(claim)
        if is_valid:
            valid_claims.append(claim)
    return valid_claims
