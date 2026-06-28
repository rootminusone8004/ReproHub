"""
Shared claim schema for the application.
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel

class Claim(BaseModel):
    """A statistical claim extracted from a paper."""
    id: str
    test_type: str
    claimed_p_value: float
    claimed_effect_size: Optional[float] = None
    params: Dict[str, Any]
    claim_statement: Optional[str] = None
    source: Optional[str] = "manual"
    extraction_confidence: Optional[str] = "unknown"

class ClaimValidator:
    """Validate claims before processing."""
    
    @staticmethod
    def validate(claim: dict) -> tuple[bool, str]:
        """Validate a claim dictionary."""
        required_fields = ["id", "test_type", "claimed_p_value", "params"]
        for field in required_fields:
            if field not in claim:
                return False, f"Missing required field: {field}"
        
        if not isinstance(claim["claimed_p_value"], (int, float)):
            return False, "claimed_p_value must be a number"
        
        if claim["claimed_p_value"] < 0 or claim["claimed_p_value"] > 1:
            return False, "claimed_p_value must be between 0 and 1"
        
        return True, "Valid"
