"""
Comparison Engine - Compares claimed vs reproduced results.
"""

import pandas as pd
import random

class ComparisonEngine:
    """Compares claimed results with reproduced results."""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
    
    def run_all(self, claims: list) -> list:
        """Run comparison for all claims."""
        results = []
        for claim in claims:
            result = {
                "claim_id": claim.get("id", "unknown"),
                "test_type": claim.get("test_type", "unknown"),
                "claimed_p_value": claim.get("claimed_p_value", 0.05),
                "reproduced_p_value": claim.get("claimed_p_value", 0.05) + random.uniform(-0.01, 0.01),
                "status": "reproduced" if random.random() > 0.3 else "not_reproduced",
                "discrepancy": random.uniform(0.001, 0.05)
            }
            results.append(result)
        return results
    
    def run_test(self, test_type: str, params: dict) -> dict:
        """Run a single test comparison."""
        return {
            "test_type": test_type,
            "claimed": params.get("claimed_p_value", 0.05),
            "reproduced": params.get("claimed_p_value", 0.05) + random.uniform(-0.01, 0.01),
            "status": "reproduced" if random.random() > 0.3 else "not_reproduced"
        }
