"""
Column Matching - resolves a claim's required parameters (e.g.
'group_col', 'value_col') to real dataset column names, using fuzzy
text matching between the claim's surrounding statement and the
dataset's column names.

This exists because core/extractor.py's regex-based extraction can
identify *which statistical test was run* and *what its reported
numbers were*, but cannot identify *which dataset columns the claim
refers to* - that requires matching prose like "cognitive scores"
against a column literally named "cognitive_score", which is a
language-understanding task. Per project decision, no AI API is used,
so this module does that matching with fuzzy string similarity instead
(via utils/fuzzy_matcher.py's fuzzywuzzy wrapper) plus a column-type
constraint (numeric vs categorical) to narrow candidates sensibly.

This is inherently an approximation. It will sometimes pick the wrong
column when a statement mentions multiple equally-plausible variables,
or fail to find any column when the paper's wording doesn't resemble
the column name at all (e.g. "performance index" vs a column named
"perf_idx"). Every match is returned with the matched param so it can
be shown to the user on the Review page for confirmation - this module
never silently asserts certainty it doesn't have.
"""

from typing import Dict, Any, List, Optional, Set

import pandas as pd
from fuzzywuzzy import fuzz, process

# Param shape required by each test type, per core/engine.py.
# "group" params need a low-cardinality categorical column; "value"/
# "col" params need a numeric column, EXCEPT chi_square, where both
# col1 and col2 are categorical (it operates on a contingency table).
_GROUP_VALUE_TESTS = {"t_test_independent", "one_way_anova", "mann_whitney_u"}
_NUMERIC_PAIR_TESTS = {"paired_t_test", "pearson_correlation", "spearman_correlation"}
_CATEGORICAL_PAIR_TESTS = {"chi_square"}

# Below this fuzzy-match score (0-100), treat it as "no real match" rather
# than guessing. Calibrated empirically: snake_case-to-prose matches for
# the right column typically score well above this; unrelated columns
# typically score well below it.
DEFAULT_THRESHOLD = 60

# Columns with more than this many unique values are treated as
# numeric/continuous rather than categorical/group-like, even if their
# dtype happens to be object/string (e.g. free-text columns), and
# conversely a numeric dtype column with very few unique values (e.g.
# a 0/1 flag) is still usable as a categorical grouping column.
_MAX_CATEGORICAL_UNIQUE = 20


def _normalize(text: str) -> str:
    """Normalize column names / text for comparison: snake_case and
    hyphens become spaces, lowercased, so 'cognitive_score' compares
    sensibly against prose like 'cognitive score'."""
    return text.replace("_", " ").replace("-", " ").lower().strip()


def classify_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Split dataset columns into 'numeric' and 'categorical' pools for
    matching purposes.

    A column counts as categorical if it's non-numeric, OR numeric with
    few enough distinct values to plausibly be a group label (e.g. a
    0/1 condition flag). Everything else numeric counts as a value
    column. This dual check matters because group_col in a real dataset
    is sometimes coded as 0/1 rather than text labels.
    """
    numeric: List[str] = []
    categorical: List[str] = []

    for col in df.columns:
        series = df[col]
        is_numeric_dtype = pd.api.types.is_numeric_dtype(series)
        n_unique = series.nunique(dropna=True)

        if is_numeric_dtype and n_unique > _MAX_CATEGORICAL_UNIQUE:
            numeric.append(col)
        else:
            categorical.append(col)
            if is_numeric_dtype:
                # A low-cardinality numeric column can plausibly serve as
                # a value column too (e.g. a 1-10 rating scale used as
                # both a group label and a measured value elsewhere).
                numeric.append(col)

    return {"numeric": numeric, "categorical": categorical}


def _best_match(
    text: str,
    candidate_columns: List[str],
    exclude: Optional[Set[str]] = None,
    threshold: int = DEFAULT_THRESHOLD,
) -> Optional[str]:
    """Find the single best-matching column name for a piece of text,
    restricted to a candidate pool and excluding already-used columns."""
    exclude = exclude or set()
    pool = [c for c in candidate_columns if c not in exclude]
    if not pool or not text or not text.strip():
        return None

    normalized_map = {_normalize(c): c for c in pool}
    match = process.extractOne(
        _normalize(text), list(normalized_map.keys()), scorer=fuzz.partial_ratio
    )
    if match and match[1] >= threshold:
        return normalized_map[match[0]]
    return None


def match_columns(claim: Dict[str, Any], dataset: pd.DataFrame) -> Dict[str, Any]:
    """
    Propose a `params` dict for a single claim by fuzzy-matching its
    claim_statement text against the dataset's column names.

    Args:
        claim: a claim dict from core/extractor.py (test_type and
            claim_statement are used; any existing params are ignored
            and replaced with proposed matches).
        dataset: the uploaded dataset.

    Returns:
        A dict with two keys:
            "params": the proposed column mapping (e.g.
                {"group_col": "treatment_group", "value_col":
                "cognitive_score"}). Any slot that couldn't be
                confidently matched is omitted, not guessed - the
                caller (e.g. the Review page) should treat a missing
                key as "needs manual selection", not '"
            "match_confidence": "high" if every required slot was
                filled, "partial" if some were, "none" if no slots
                could be matched at all.
        Never raises - an unmatchable claim simply gets an empty/partial
        params dict, which core/comparator.py already handles by
        returning a `could_not_verify` result.
    """
    test_type = claim.get("test_type", "")
    statement = claim.get("claim_statement", "") or ""
    pools = classify_columns(dataset)

    params: Dict[str, str] = {}

    if test_type in _GROUP_VALUE_TESTS:
        group_col = _best_match(statement, pools["categorical"])
        value_col = _best_match(statement, pools["numeric"], exclude={group_col} if group_col else None)
        if group_col:
            params["group_col"] = group_col
        if value_col:
            params["value_col"] = value_col
        required = {"group_col", "value_col"}

    elif test_type in _NUMERIC_PAIR_TESTS:
        col1 = _best_match(statement, pools["numeric"])
        col2 = _best_match(statement, pools["numeric"], exclude={col1} if col1 else None)
        if col1:
            params["col1"] = col1
        if col2:
            params["col2"] = col2
        required = {"col1", "col2"}

    elif test_type in _CATEGORICAL_PAIR_TESTS:
        col1 = _best_match(statement, pools["categorical"])
        col2 = _best_match(statement, pools["categorical"], exclude={col1} if col1 else None)
        if col1:
            params["col1"] = col1
        if col2:
            params["col2"] = col2
        required = {"col1", "col2"}

    else:
        # Unknown test type - nothing we can confidently propose.
        return {"params": {}, "match_confidence": "none"}

    filled = set(params.keys())
    if filled == required:
        confidence = "high"
    elif filled:
        confidence = "partial"
    else:
        confidence = "none"

    return {"params": params, "match_confidence": confidence}


def match_all_claims(claims: List[Dict[str, Any]], dataset: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Run match_columns for every claim and return updated claim dicts
    (each claim's `params` replaced with the proposed mapping, plus a
    new `match_confidence` field). Original claim fields are preserved.
    """
    updated = []
    for claim in claims:
        match_result = match_columns(claim, dataset)
        new_claim = dict(claim)
        new_claim["params"] = match_result["params"]
        new_claim["match_confidence"] = match_result["match_confidence"]
        updated.append(new_claim)
    return updated
