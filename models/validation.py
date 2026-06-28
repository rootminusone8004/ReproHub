"""Validation schemas for input data."""

from pydantic import BaseModel, validator
from typing import List, Dict, Any

class ClaimInput(BaseModel):
    id: str
    test_type: str
    claimed_p_value: float
    claimed_effect_size: float = 0.0
    params: Dict[str, Any]
    claim_statement: str = ""
    
    @validator("claimed_p_value")
    def validate_p_value(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("p-value must be between 0 and 1")
        return v
