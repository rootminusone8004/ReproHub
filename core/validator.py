"""
Claim Validation - Ensures claims are properly formatted.
"""

from typing import Any, Dict, List, Tuple

from core.schema import ClaimValidator


def validate_claim(claim: dict) -> Tuple[bool, str]:
    """Validate a single claim."""
    return ClaimValidator.validate(claim)


def validate_all_claims(claims: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Validate every claim and split them into valid and invalid groups.

    Previously this silently dropped invalid claims and returned only the
    valid ones, discarding the specific reason each one failed. That
    contradicts the project's own design principle (see core/comparator.py
    and the original project plan): a claim that fails validation should
    become a visible, explained result - never disappear with no trace.
    If 5 of 10 claims are malformed, the caller needs to know that, and
    why, not just see a report with 5 results.

    Returns:
        {
            "valid": [claim, ...],
            "invalid": [claim_with_validation_error, ...],
        }
        Each claim in "invalid" has the original claim dict plus a
        "validation_error" key set to the specific failure reason, so a
        caller (e.g. a future comparator/Review-page integration) can
        surface it as a could_not_verify result with that exact reason,
        consistent with how core/comparator.py already handles claims
        that fail downstream (missing columns, engine errors, etc.).
    """
    valid_claims: List[Dict[str, Any]] = []
    invalid_claims: List[Dict[str, Any]] = []

    for claim in claims:
        is_valid, message = validate_claim(claim)
        if is_valid:
            valid_claims.append(claim)
        else:
            invalid_claim = dict(claim)
            invalid_claim["validation_error"] = message
            invalid_claims.append(invalid_claim)

    return {"valid": valid_claims, "invalid": invalid_claims}
