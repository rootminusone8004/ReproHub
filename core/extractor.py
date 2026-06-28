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
}

# Effect-size patterns, checked against a small window of text following
# each statistic match (effect sizes are conventionally reported right
# after the p-value, e.g. "..., p = 0.03, Cohen's d = 0.45").
_EFFECT_PATTERNS: Dict[str, "re.Pattern[str]"] = {
    # Matches both "Cohen's d = 0.45" and the common abbreviated form
    # "d = 0.92" used once "Cohen's d" has already been introduced
    # earlier in the same sentence. \b before "d" avoids false-matching
    # "df = 5" or other words ending in "d".
    "cohens_d": re.compile(r"(?:Cohen'?s\s+)?\bd\s*=\s*(-?\d*\.?\d+)", re.IGNORECASE),
    "eta_squared": re.compile(r"(?:partial\s+)?(?:eta squared|η²|η2)\s*=\s*(-?\d*\.?\d+)", re.IGNORECASE),
    "r_effect": re.compile(r"\br\s*=\s*(-?\d*\.?\d+)", re.IGNORECASE),
}

# How far past the end of a statistic match to look for its effect size,
# in characters. Wide enough to catch "..., d = 0.45." but not so wide
# it picks up an unrelated effect size from the next sentence.
_EFFECT_SIZE_WINDOW = 60


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
    """
    Extract statistical claims from paper text using regex pattern
    matching against conventional APA-style result reporting.

    Args:
        paper_text: Full text of the paper (e.g. from
            utils.pdf_parser.extract_text_from_pdf).

    Returns:
        A list of claim dicts, each matching the shape expected by
        core.schema.Claim:
            - id, test_type, claimed_p_value, claimed_effect_size,
              params (always {} - see module docstring), claim_statement,
              source ("regex_extracted"), extraction_confidence.
        Returns an empty list if no recognizable statistics are found,
        e.g. for blank input or papers that report results purely in
        prose without inline notation.
    """
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
                continue  # Shouldn't happen given the pattern, but don't crash on a bad match.

            effect_size = _find_effect_size(paper_text, match.end())

            # Use a short surrounding window of the original text as the
            # human-readable claim statement, so a person reviewing this
            # on the Review page can see where it came from. Trimmed and
            # collapsed to single-line for readability in the UI.
            context_start = max(0, match.start() - 80)
            context_end = min(len(paper_text), match.end() + 20)
            raw_context = paper_text[context_start:context_end]
            claim_statement = " ".join(raw_context.split())

            claims.append({
                "id": f"claim_{claim_counter}",
                "test_type": test_type,
                "claimed_p_value": claimed_p_value,
                "claimed_effect_size": effect_size,
                # Left empty intentionally - see module docstring. Must be
                # filled in by core.matcher's fuzzy matching against the
                # uploaded dataset's columns, or manually on the Review page.
                "params": {},
                "claim_statement": claim_statement,
                "source": "regex_extracted",
                # Confidence reflects pattern-match certainty, not whether
                # the claim will actually be verifiable - a match with a
                # clean, unambiguous df/stat/p triplet is "high"; matches
                # missing an effect size or df are downgraded since they're
                # more likely to be partial/malformed matches.
                "extraction_confidence": (
                    "high" if effect_size is not None or "df" not in groups
                    else "medium"
                ),
            })

    return claims
