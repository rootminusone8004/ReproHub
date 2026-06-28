"""
Comparison Engine - runs each claim's statistical test for real (via
StatisticalTestEngine) and compares the claimed p-value against the
reproduced p-value to classify reproducibility.

Status thresholds (per README.md "Understanding Results"):
    reproduced       p-value difference < 0.01
    marginal         p-value difference 0.01 - 0.05
    not_reproduced   p-value difference >= 0.05
    could_not_verify test couldn't be run at all (missing/invalid
                     columns, unsupported test type, no dataset, etc.)
"""

from typing import Dict, Any, List, Optional
import pandas as pd

from core.engine import StatisticalTestEngine

# Status thresholds on |claimed_p - reproduced_p|, per README.md.
REPRODUCED_THRESHOLD = 0.01
MARGINAL_THRESHOLD = 0.05


def _classify(claimed_p: float, reproduced_p: float) -> str:
    """Classify reproducibility status from the p-value discrepancy."""
    discrepancy = abs(claimed_p - reproduced_p)
    if discrepancy < REPRODUCED_THRESHOLD:
        return "reproduced"
    if discrepancy < MARGINAL_THRESHOLD:
        return "marginal"
    return "not_reproduced"


class ComparisonEngine:
    """Compares claimed results with reproduced results from real tests."""

    def __init__(self, data: Optional[pd.DataFrame]):
        self.data = data
        self.engine = StatisticalTestEngine(data)

    def run_all(self, claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run verification for every claim.

        Each claim dict should already have a resolved `params` (real
        column names, not paper prose) - see core/matcher.py or the
        Review page for how that mapping happens.

        Returns one result dict per claim, in the same order, with the
        shape expected by models/result.py: claim_id, test_type, status,
        claimed_p_value, reproduced_p_value, discrepancy, explanation.
        A claim is never silently dropped - if its test can't run, it
        gets a `could_not_verify` result rather than disappearing from
        the list, so totals on the Dashboard stay consistent with the
        number of claims reviewed.
        """
        return [self.run_test(claim) for claim in claims]

    def run_test(self, claim: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run verification for a single claim.

        Args:
            claim: a claim dict (id, test_type, claimed_p_value, params, ...).

        Returns:
            A result dict: claim_id, test_type, status, claimed_p_value,
            reproduced_p_value, discrepancy, explanation.
            reproduced_p_value and discrepancy are None when status is
            "could_not_verify", since no reproduced value exists.
        """
        claim_id = claim.get("id", "unknown")
        test_type = claim.get("test_type", "unknown")
        claimed_p_value = claim.get("claimed_p_value")
        params = claim.get("params", {})

        if claimed_p_value is None:
            return {
                "claim_id": claim_id,
                "test_type": test_type,
                "status": "could_not_verify",
                "claimed_p_value": None,
                "reproduced_p_value": None,
                "discrepancy": None,
                "explanation": "Claim has no claimed p-value to compare against.",
            }

        if not params:
            return {
                "claim_id": claim_id,
                "test_type": test_type,
                "status": "could_not_verify",
                "claimed_p_value": claimed_p_value,
                "reproduced_p_value": None,
                "discrepancy": None,
                "explanation": (
                    "No dataset columns have been mapped to this claim yet. "
                    "Resolve column mappings on the Review page before running "
                    "verification."
                ),
            }

        engine_result = self.engine.run_test(test_type, params)

        if "error" in engine_result:
            return {
                "claim_id": claim_id,
                "test_type": test_type,
                "status": "could_not_verify",
                "claimed_p_value": claimed_p_value,
                "reproduced_p_value": None,
                "discrepancy": None,
                "explanation": engine_result["error"],
            }

        reproduced_p_value = engine_result["p_value"]
        discrepancy = abs(claimed_p_value - reproduced_p_value)
        status = _classify(claimed_p_value, reproduced_p_value)

        return {
            "claim_id": claim_id,
            "test_type": test_type,
            "status": status,
            "claimed_p_value": claimed_p_value,
            "reproduced_p_value": reproduced_p_value,
            "discrepancy": discrepancy,
            "explanation": None,
        }
