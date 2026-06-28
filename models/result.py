"""Result data model."""

from pydantic import BaseModel
from typing import Optional

class Result(BaseModel):
    claim_id: str
    test_type: str
    status: str  # reproduced, not_reproduced, marginal, could_not_verify
    claimed_p_value: float
    reproduced_p_value: float
    discrepancy: float
    explanation: Optional[str] = None
