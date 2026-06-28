"""Fuzzy string matching utilities."""

from fuzzywuzzy import fuzz, process

def find_best_match(query: str, candidates: list, threshold: int = 80) -> str:
    """Find the best fuzzy match for a string."""
    if not candidates:
        return query
    
    match, score = process.extractOne(query, candidates, scorer=fuzz.ratio)
    if score >= threshold:
        return match
    return query
