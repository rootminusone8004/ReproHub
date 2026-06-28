"""General helper functions."""

import json
from datetime import datetime

def format_timestamp() -> str:
    """Return formatted timestamp."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def safe_json_loads(text: str) -> dict:
    """Safely load JSON from string."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}
