"""
Claim Extraction - Regex-based pattern matching.

Scans extracted paper text for statistical results reported in standard
APA-style notation (e.g. "t(98) = 2.43, p = 0.03") and turns each match
into a claim dict matching the schema in core/schema.py.

IMPORTANT LIMITATION: this is pattern matching over text, not language
understanding. It can reliably pull out *which test was run* and *what
the reported statistic/p-value/effect size were*, because those have a
fixed, conventional notation. It CANNOT tell which dataset columns a
claim refers to (e.g. mapping "cognitive scores" -> a CSV column named
"score_t1") - that requires understanding the surrounding prose, which
is exactly what an LLM would normally be used for. Per project decision,
no AI API is used here, so every claim's `params` dict is returned empty
and must be filled in either by core/matcher.py's fuzzy column matching
or by the user on the Review page.

Consequences of the regex-only approach worth knowing about:
- Only catches results reported in conventional notation. A paper that
  writes results out in prose without inline statistics (e.g. "the
  groups did not differ significantly") will not be picked up.
- Cannot resolve which specific test variant produced a generic stat.
  For example r(df) is reported identically for Pearson and sometimes
  loosely for other correlation types - this module assumes Pearson
  unless the surrounding text says otherwise.
- No claim deduplication across paraphrased restatements of the same
  result (e.g. the same t-test appearing in both an abstract and the
  Results section) - each textual occurrence becomes a separate claim.
"""

import re
from typing import List, Dict, Any, Optional

# Shared p-value fragment: handles both "0.03" and ".03" styles, and
# both "=" and "<" comparators (papers often write p < .05 for
# significance thresholds rather than the exact computed value).
_P = r"[=<]\s*(?P<p>0?\.\d+|\d\.\d+)"
_NUM = r"-?\d*\.?\d+"

# One compiled pattern per supported test type. Each must capture at
# least a `stat` and `p` group; df groups are test-specific.
_TEST_PATTERNS: Dict[str, "re.Pattern[str]"] = {
    "t_test_independent": re.compile(
        rf"\bt\(\s*(?P<df>\d+\.?\d*)\s*\)\s*=\s*(?P<stat>{_NUM})\s*,\s*p\s*{_P}",
        re.IGNORECASE,
    ),
    "one_way_anova": re.compile(
        rf"\bF\(\s*(?P<df1>\d+\.?\d*)\s*,\s*(?P<df2>\d+\.?\d*)\s*\)\s*=\s*(?P<stat>{_NUM})\s*,\s*p\s*{_P}",
        re.IGNORECASE,
    ),
    "pearson_correlation": re.compile(
        rf"(?:Pearson'?s?\s+)?\br\(?\s*(?P<df>\d*)\s*\)?\s*=\s*(?P<stat>{_NUM})\s*,\s*p\s*{_P}",
        re.IGNORECASE,
    ),
    "chi_square": re.compile(
        rf"(?:χ2|χ²|\bchi-square\b)\s*\(\s*(?P<df>\d+)(?:\s*,\s*N\s*=\s*\d+)?\s*\)\s*=\s*(?P<stat>{_NUM})\s*,\s*p\s*{_P}",
        re.IGNORECASE,
    ),
    "mann_whitney_u": re.compile(
        rf"\b(?:Mann-Whitney\s+U|U)\s*=\s*(?P<stat>{_NUM})\s*,\s*p\s*{_P}",
        re.IGNORECASE,
    ),
    "kruskal_wallis": re.compile(
        rf"\b(?:Kruskal[–-]Wallis|H)\s*\(?\s*(?P<df>\d*)?\s*\)?\s*=\s*(?P<stat>{_NUM})\s*,\s*p\s*{_P}",
        re.IGNORECASE,
    ),
    "wilcoxon_signed_rank": re.compile(
        rf"\b(?:Wilcoxon(?:\s+signed[–-]rank)?|W)\s*=\s*(?P<stat>{_NUM})\s*,\s*p\s*{_P}",
        re.IGNORECASE,
    ),
    "linear_regression": re.compile(
        rf"\bF\s*\(\s*(?P<df1>\d+\.?\d*)\s*,\s*(?P<df2>\d+\.?\d*)\s*\)\s*=\s*(?P<stat>{_NUM})\s*,\s*p\s*{_P}[^,]*,\s*R[²2]\s*=\s*(?P<r2>{_NUM})",
        re.IGNORECASE,
    ),
    "logistic_regression": re.compile(
        rf"\b(?:logistic\s+regression|Wald\s+χ2|LR\s+χ2)\b[^,]*,?\s*(?:χ2|chi.?square)?\s*[=(]\s*(?P<stat>{_NUM})[^,]*,\s*p\s*{_P}",
        re.IGNORECASE,
    ),
}

# Effect-size patterns, checked against a small window of text following
# each statistic match (effect sizes are conventionally reported right
# after the p-value, e.g. "..., p = 0.03, Cohen's d = 0.45").
_EFFECT_PATTERNS: Dict[str, "re.Pattern[str]"] = {
    "cohens_d": re.compile(r"(?:Cohen'?s\s+)?\bd\s*=\s*(-?\d*\.?\d+)", re.IGNORECASE),
    "eta_squared": re.compile(r"(?:partial\s+)?(?:eta squared|η²|η2)\s*=\s*(-?\d*\.?\d+)", re.IGNORECASE),
    "r_effect": re.compile(r"\br\s*=\s*(-?\d*\.?\d+)", re.IGNORECASE),
}

_EFFECT_SIZE_WINDOW = 60
_CONTEXT_SEARCH_RADIUS = 300
_LOOKBACK_SENTENCES = 1


def _extract_sentence_context(text: str, match_start: int, match_end: int) -> str:
    search_start = max(0, match_start - _CONTEXT_SEARCH_RADIUS)
    preceding = text[search_start:match_start]
    boundary_matches = list(re.finditer(r"[.!?]\s+", preceding))

    if len(boundary_matches) > _LOOKBACK_SENTENCES:
        sentence_start = search_start + boundary_matches[-(_LOOKBACK_SENTENCES + 1)].end()
    else:
        sentence_start = search_start

    search_end = min(len(text), match_end + _CONTEXT_SEARCH_RADIUS)
    following = text[match_end:search_end]
    boundary_match = re.search(r"[.!?](?:\s|$)", following)
    sentence_end = match_end + boundary_match.end() if boundary_match else search_end

    raw_context = text[sentence_start:sentence_end]
    return " ".join(raw_context.split())


def _find_effect_size(text: str, search_start: int) -> Optional[float]:
    """Look for an effect-size value shortly after a statistic match."""
    window = text[search_start:search_start + _EFFECT_SIZE_WINDOW]
    for pattern in _EFFECT_PATTERNS.values():
        match = pattern.search(window)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


def extract_claims_from_paper(paper_text: str) -> List[Dict[str, Any]]:
    if not paper_text or not paper_text.strip():
        return []

    claims: List[Dict[str, Any]] = []
    claim_counter = 0

    for test_type, pattern in _TEST_PATTERNS.items():
        for match in pattern.finditer(paper_text):
            claim_counter += 1
            groups = match.groupdict()

            try:
                claimed_p_value = float(groups["p"])
            except (KeyError, ValueError):
                continue

            effect_size = _find_effect_size(paper_text, match.end())
            claim_statement = _extract_sentence_context(paper_text, match.start(), match.end())

            claims.append({
                "id": f"claim_{claim_counter}",
                "test_type": test_type,
                "claimed_p_value": claimed_p_value,
                "claimed_effect_size": effect_size,
                "params": {},
                "claim_statement": claim_statement,
                "source": "regex_extracted",
                "extraction_confidence": (
                    "high" if effect_size is not None or "df" not in groups
                    else "medium"
                ),
            })

    return claims
