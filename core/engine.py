"""
Statistical Test Engine - Mock version for deployment.
Returns mock results without running actual statistics.
"""

import pandas as pd
import random

class StatisticalTestEngine:
    """Mock statistical engine that returns predefined results."""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        
    def run_test(self, test_type: str, params: dict) -> dict:
        """Run a mock statistical test."""
        # Return mock results based on test type
        mock_results = {
            "t_test_independent": {
                "test_type": "t_test_independent",
                "statistic": 2.31,
                "p_value": 0.024,
                "effect_size": {"type": "cohens_d", "value": 0.45},
                "n": len(self.data) if self.data is not None else 100,
                "assumptions_checked": {"normality": True, "equal_variance": True}
            },
            "pearson_correlation": {
                "test_type": "pearson_correlation",
                "statistic": 0.45,
                "p_value": 0.01,
                "effect_size": {"type": "r", "value": 0.45},
                "n": len(self.data) if self.data is not None else 100
            }
        }
        return mock_results.get(test_type, {"error": f"Test {test_type} not implemented"})
