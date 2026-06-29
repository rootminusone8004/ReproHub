"""
Comparison Engine - runs each claim's statistical test for real (via
StatisticalTestEngine) and compares claimed vs reproduced results using
a composite scoring approach that weighs p-value discrepancy, effect size
discrepancy, and test statistic discrepancy together.

Why composite scoring?
    A p-value-only classification is misleading in two common ways:
    1. Same p-value, very different effect size (e.g. d=0.2 vs d=0.8):
       the study found the same significance but a wildly different
       practical effect — should not be called "reproduced".
    2. Different p-values but negligible effect size in both (e.g.
       p=0.03 vs p=0.07 when d≈0.05 in both): arguably still reproduces
       the substantive finding even though p crossed 0.05.

Scoring model:
    composite_score = (
        w_p   * p_component        +   # p-value agreement
        w_es  * es_component       +   # effect size agreement (if available)
        w_stat * stat_component        # test statistic agreement (relative)
    )
    where each component is in [0, 1] and weights sum to 1.

    When claimed_effect_size is absent the effect size weight is
    redistributed to the p-value weight so the score stays in [0, 1].

Status thresholds on composite_score:
    reproduced       >= 0.80
    marginal         >= 0.55
    not_reproduced   < 0.55
    could_not_verify test couldn't be run at all
"""

from typing import Dict, Any, List, Optional
import math
import pandas as pd

from core.engine import StatisticalTestEngine

# --- Component weights ---------------------------------------------------
W_P_VALUE   = 0.50
W_EFFECT    = 0.30
W_STATISTIC = 0.20

# --- Status thresholds on composite_score --------------------------------
THRESHOLD_REPRODUCED = 0.80
THRESHOLD_MARGINAL   = 0.55


def _p_component(claimed_p: float, reproduced_p: float) -> float:
    diff = abs(claimed_p - reproduced_p)
    return math.exp(-30 * diff)


def _effect_component(claimed_es: Optional[float], reproduced_es: Optional[float]) -> Optional[float]:
    if claimed_es is None or reproduced_es is None:
        return None
    diff = abs(claimed_es - reproduced_es)
    return math.exp(-10 * diff)


def _stat_component(claimed_stat: Optional[float], reproduced_stat: float) -> float:
    if claimed_stat is None:
        return 0.5  # neutral: no info
    denom = max(abs(reproduced_stat), 0.001)
    rel_err = abs(claimed_stat - reproduced_stat) / denom
    return max(0.0, 1.0 - rel_err)


def _composite_score(
    claimed_p: float,
    reproduced_p: float,
    claimed_es: Optional[float],
    reproduced_es: Optional[float],
    claimed_stat: Optional[float],
    reproduced_stat: float,
) -> tuple[float, Dict[str, Any]]:
    p_comp  = _p_component(claimed_p, reproduced_p)
    es_comp = _effect_component(claimed_es, reproduced_es)
    st_comp = _stat_component(claimed_stat, reproduced_stat)

    if es_comp is None:
        w_p  = W_P_VALUE + W_EFFECT
        w_es = 0.0
    else:
        w_p  = W_P_VALUE
        w_es = W_EFFECT
    w_stat = W_STATISTIC

    score = w_p * p_comp + w_es * (es_comp or 0.0) + w_stat * st_comp

    breakdown = {
        "p_component":      round(p_comp, 4),
        "effect_component": round(es_comp, 4) if es_comp is not None else None,
        "stat_component":   round(st_comp, 4),
        "weights": {
            "p_value":     round(w_p, 2),
            "effect_size": round(w_es, 2),
            "statistic":   round(w_stat, 2),
        },
        "composite_score": round(score, 4),
    }
    return score, breakdown


def _classify(score: float) -> str:
    if score >= THRESHOLD_REPRODUCED:
        return "reproduced"
    if score >= THRESHOLD_MARGINAL:
        return "marginal"
    return "not_reproduced"


def _build_explanation(
    status: str,
    breakdown: Dict[str, Any],
    claimed_p: float,
    reproduced_p: float,
    claimed_es: Optional[float],
    reproduced_es_dict: Optional[Dict],
) -> str:
    score = breakdown["composite_score"]
    lines = [f"Composite score: {score:.2f} → {status.replace('_', ' ').title()}"]

    p_diff = abs(claimed_p - reproduced_p)
    lines.append(
        f"  • p-value: claimed={claimed_p:.4f}, reproduced={reproduced_p:.4f} "
        f"(|Δ|={p_diff:.4f}, component={breakdown['p_component']:.2f})"
    )

    if claimed_es is not None and breakdown["effect_component"] is not None:
        rep_es_val  = reproduced_es_dict["value"] if reproduced_es_dict else None
        rep_es_type = reproduced_es_dict["type"]  if reproduced_es_dict else "?"
        rep_es_str  = f"{rep_es_val:.3f}" if rep_es_val is not None else "N/A"
        lines.append(
            f"  • effect size ({rep_es_type}): claimed={claimed_es:.3f}, "
            f"reproduced={rep_es_str} "
            f"(component={breakdown['effect_component']:.2f})"
        )
    else:
        lines.append("  • effect size: not available in claim — weight redistributed to p-value")

    lines.append(f"  • statistic component: {breakdown['stat_component']:.2f}")

    if status == "not_reproduced":
        worst = min(
            ("p-value",    breakdown["p_component"]),
            ("effect size", breakdown["effect_component"] or 1.0),
            ("statistic",  breakdown["stat_component"]),
            key=lambda x: x[1],
        )
        lines.append(f"  ⚠ Primary driver of failure: {worst[0]} agreement ({worst[1]:.2f})")

    return "\n".join(lines)


class ComparisonEngine:
    """Compares claimed results with reproduced results from real tests."""

    def __init__(self, data: Optional[pd.DataFrame]):
        self.data = data
        self.engine = StatisticalTestEngine(data)

    def run_all(self, claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.run_test(claim) for claim in claims]

    def run_test(self, claim: Dict[str, Any]) -> Dict[str, Any]:
        claim_id     = claim.get("id", "unknown")
        test_type    = claim.get("test_type", "unknown")
        claimed_p    = claim.get("claimed_p_value")
        claimed_es   = claim.get("claimed_effect_size")
        claimed_stat = claim.get("claimed_statistic")
        params       = claim.get("params", {})

        def _cant_verify(reason: str) -> Dict[str, Any]:
            return {
                "claim_id":               claim_id,
                "test_type":              test_type,
                "status":                 "could_not_verify",
                "claimed_p_value":        claimed_p,
                "reproduced_p_value":     None,
                "discrepancy":            None,
                "composite_score":        None,
                "score_breakdown":        None,
                "claimed_effect_size":    claimed_es,
                "reproduced_effect_size": None,
                "explanation":            reason,
            }

        if claimed_p is None:
            return _cant_verify("Claim has no claimed p-value to compare against.")

        if not params:
            return _cant_verify(
                "No dataset columns have been mapped to this claim yet. "
                "Resolve column mappings on the Review page before running verification."
            )

        engine_result = self.engine.run_test(test_type, params)

        if "error" in engine_result:
            return _cant_verify(engine_result["error"])

        reproduced_p       = engine_result["p_value"]
        reproduced_stat    = engine_result["statistic"]
        reproduced_es_dict = engine_result.get("effect_size")
        reproduced_es_val  = reproduced_es_dict["value"] if reproduced_es_dict else None

        score, breakdown = _composite_score(
            claimed_p, reproduced_p,
            claimed_es, reproduced_es_val,
            claimed_stat, reproduced_stat,
        )

        status = _classify(score)
        explanation = _build_explanation(
            status, breakdown, claimed_p, reproduced_p,
            claimed_es, reproduced_es_dict,
        )

        return {
            "claim_id":               claim_id,
            "test_type":              test_type,
            "status":                 status,
            "claimed_p_value":        claimed_p,
            "reproduced_p_value":     reproduced_p,
            "discrepancy":            round(abs(claimed_p - reproduced_p), 6),
            "composite_score":        round(score, 4),
            "score_breakdown":        breakdown,
            "claimed_effect_size":    claimed_es,
            "reproduced_effect_size": reproduced_es_dict,
            "explanation":            explanation,
        }
