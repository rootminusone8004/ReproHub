"""
Column Matching - Mock version.
Returns mock column mappings.
"""

def match_columns(params: dict, column_names: list) -> dict:
    """Match paper variables to dataset columns."""
    mappings = {}
    for key, value in params.items():
        if isinstance(value, str) and value in column_names:
            mappings[key] = value
        elif isinstance(value, str):
            # Suggest first available column as match
            mappings[key] = column_names[0] if column_names else value
    return mappings
