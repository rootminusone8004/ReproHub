"""
Statistical Test Engine - runs real statistical tests against the
uploaded dataset using SciPy/statsmodels.

Each test type expects a specific params shape (the columns it needs
from the dataset). Columns must already be resolved to real names in
the uploaded DataFrame - resolving them from a paper's prose ("cognitive
scores" -> "cognitive_score") happens upstream, in core/matcher.py or
the Review page, not here.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
import statsmodels.api as sm


class EngineError(Exception):
    """Raised when a test can't be run against the supplied data/params."""


class StatisticalTestEngine:
    """Runs real statistical tests against a pandas DataFrame."""

    SUPPORTED_TESTS = {
        "t_test_independent",
        "paired_t_test",
        "one_way_anova",
        "pearson_correlation",
        "spearman_correlation",
        "chi_square",
        "mann_whitney_u",
        "kruskal_wallis",
        "wilcoxon_signed_rank",
        "linear_regression",
        "logistic_regression",
    }

    def __init__(self, data: Optional[pd.DataFrame]):
        self.data = data

    def run_test(self, test_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a real statistical test.

        Args:
            test_type: one of SUPPORTED_TESTS.
            params: column references the test needs. Shape depends on
                test_type - see the individual _run_* methods.

        Returns:
            A result dict: {test_type, statistic, p_value, effect_size,
            n, assumptions_checked (where applicable)}, or
            {"error": "..."} if the test can't be run (missing/invalid
            columns, insufficient data, unsupported test_type). An error
            dict is returned rather than an exception raised, since a
            single bad claim shouldn't crash a batch of several - see
            core/comparator.py, which calls this per-claim in a loop.
        """
        if self.data is None:
            return {"error": "No dataset loaded."}

        if test_type not in self.SUPPORTED_TESTS:
            return {"error": f"Test {test_type} not implemented"}

        try:
            handler = getattr(self, f"_run_{test_type}")
            return handler(params)
        except EngineError as exc:
            return {"error": str(exc)}
        except Exception as exc:  # noqa: BLE001 - never let one bad claim crash the batch
            return {"error": f"Unexpected error running {test_type}: {exc}"}

    # -- helpers --------------------------------------------------------

    def _require_columns(self, *cols: str) -> None:
        missing = [c for c in cols if c not in self.data.columns]
        if missing:
            raise EngineError(f"Column(s) not found in dataset: {', '.join(missing)}")

    def _numeric_series(self, col: str) -> pd.Series:
        series = pd.to_numeric(self.data[col], errors="coerce").dropna()
        if series.empty:
            raise EngineError(f"Column '{col}' has no usable numeric values.")
        return series

    # -- test implementations --------------------------------------------

    def _run_t_test_independent(self, params: dict) -> dict:
        group_col, value_col = params.get("group_col"), params.get("value_col")
        if not group_col or not value_col:
            raise EngineError("t_test_independent requires 'group_col' and 'value_col'.")
        self._require_columns(group_col, value_col)

        sub = self.data[[group_col, value_col]].dropna()
        groups = sub[group_col].unique()
        if len(groups) != 2:
            raise EngineError(
                f"t_test_independent requires exactly 2 groups in '{group_col}', "
                f"found {len(groups)}: {list(groups)}"
            )

        a = pd.to_numeric(sub[sub[group_col] == groups[0]][value_col], errors="coerce").dropna()
        b = pd.to_numeric(sub[sub[group_col] == groups[1]][value_col], errors="coerce").dropna()
        if len(a) == 0 or len(b) == 0:
            raise EngineError(
                f"Column '{value_col}' does not contain numeric values for one or "
                f"both groups - check that 'value_col' and 'group_col' aren't swapped."
            )
        if len(a) < 2 or len(b) < 2:
            raise EngineError("Each group needs at least 2 observations for a t-test.")

        normal_a = stats.shapiro(a).pvalue > 0.05 if len(a) >= 3 else None
        normal_b = stats.shapiro(b).pvalue > 0.05 if len(b) >= 3 else None
        equal_var = stats.levene(a, b).pvalue > 0.05

        result = stats.ttest_ind(a, b, equal_var=equal_var)
        pooled_std = np.sqrt(((len(a) - 1) * a.std(ddof=1) ** 2 + (len(b) - 1) * b.std(ddof=1) ** 2)
                              / (len(a) + len(b) - 2))
        cohens_d = (a.mean() - b.mean()) / pooled_std if pooled_std > 0 else 0.0

        return {
            "test_type": "t_test_independent",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": {"type": "cohens_d", "value": float(cohens_d)},
            "n": int(len(a) + len(b)),
            "assumptions_checked": {
                "normality": bool(normal_a) and bool(normal_b) if normal_a is not None and normal_b is not None else None,
                "equal_variance": bool(equal_var),
            },
        }

    def _run_paired_t_test(self, params: dict) -> dict:
        col1, col2 = params.get("col1"), params.get("col2")
        if not col1 or not col2:
            raise EngineError("paired_t_test requires 'col1' and 'col2'.")
        self._require_columns(col1, col2)

        sub = self.data[[col1, col2]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(sub) < 2:
            raise EngineError("paired_t_test requires at least 2 paired observations.")

        result = stats.ttest_rel(sub[col1], sub[col2])
        diffs = sub[col1] - sub[col2]
        cohens_d = diffs.mean() / diffs.std(ddof=1) if diffs.std(ddof=1) > 0 else 0.0

        return {
            "test_type": "paired_t_test",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": {"type": "cohens_d", "value": float(cohens_d)},
            "n": int(len(sub)),
        }

    def _run_one_way_anova(self, params: dict) -> dict:
        group_col, value_col = params.get("group_col"), params.get("value_col")
        if not group_col or not value_col:
            raise EngineError("one_way_anova requires 'group_col' and 'value_col'.")
        self._require_columns(group_col, value_col)

        sub = self.data[[group_col, value_col]].dropna()
        sub[value_col] = pd.to_numeric(sub[value_col], errors="coerce")
        sub = sub.dropna()
        groups = [g[value_col].values for _, g in sub.groupby(group_col) if len(g) >= 2]
        if len(groups) < 2:
            raise EngineError(f"one_way_anova requires at least 2 groups with 2+ observations each.")

        result = stats.f_oneway(*groups)

        grand_mean = sub[value_col].mean()
        ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
        ss_total = ((sub[value_col] - grand_mean) ** 2).sum()
        eta_sq = ss_between / ss_total if ss_total > 0 else 0.0

        return {
            "test_type": "one_way_anova",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": {"type": "eta_squared", "value": float(eta_sq)},
            "n": int(sum(len(g) for g in groups)),
        }

    def _run_pearson_correlation(self, params: dict) -> dict:
        col1, col2 = params.get("col1"), params.get("col2")
        if not col1 or not col2:
            raise EngineError("pearson_correlation requires 'col1' and 'col2'.")
        self._require_columns(col1, col2)

        sub = self.data[[col1, col2]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(sub) < 3:
            raise EngineError("pearson_correlation requires at least 3 paired observations.")

        result = stats.pearsonr(sub[col1], sub[col2])

        return {
            "test_type": "pearson_correlation",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": {"type": "r", "value": float(result.statistic)},
            "n": int(len(sub)),
        }

    def _run_spearman_correlation(self, params: dict) -> dict:
        col1, col2 = params.get("col1"), params.get("col2")
        if not col1 or not col2:
            raise EngineError("spearman_correlation requires 'col1' and 'col2'.")
        self._require_columns(col1, col2)

        sub = self.data[[col1, col2]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(sub) < 3:
            raise EngineError("spearman_correlation requires at least 3 paired observations.")

        result = stats.spearmanr(sub[col1], sub[col2])

        return {
            "test_type": "spearman_correlation",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": {"type": "rho", "value": float(result.statistic)},
            "n": int(len(sub)),
        }

    def _run_chi_square(self, params: dict) -> dict:
        col1, col2 = params.get("col1"), params.get("col2")
        if not col1 or not col2:
            raise EngineError("chi_square requires 'col1' and 'col2'.")
        self._require_columns(col1, col2)

        sub = self.data[[col1, col2]].dropna()
        if len(sub) < 1:
            raise EngineError("chi_square requires at least 1 observation.")

        contingency = pd.crosstab(sub[col1], sub[col2])
        if contingency.shape[0] < 2 or contingency.shape[1] < 2:
            raise EngineError(
                f"chi_square requires at least 2 categories in each of '{col1}' and '{col2}'."
            )

        chi2, p, dof, expected = stats.chi2_contingency(contingency)

        n = contingency.values.sum()
        min_dim = min(contingency.shape) - 1
        cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 and n > 0 else 0.0

        return {
            "test_type": "chi_square",
            "statistic": float(chi2),
            "p_value": float(p),
            "effect_size": {"type": "cramers_v", "value": float(cramers_v)},
            "n": int(n),
            "degrees_of_freedom": int(dof),
        }

    def _run_mann_whitney_u(self, params: dict) -> dict:
        group_col, value_col = params.get("group_col"), params.get("value_col")
        if not group_col or not value_col:
            raise EngineError("mann_whitney_u requires 'group_col' and 'value_col'.")
        self._require_columns(group_col, value_col)

        sub = self.data[[group_col, value_col]].dropna()
        groups = sub[group_col].unique()
        if len(groups) != 2:
            raise EngineError(
                f"mann_whitney_u requires exactly 2 groups in '{group_col}', found {len(groups)}."
            )

        a = pd.to_numeric(sub[sub[group_col] == groups[0]][value_col], errors="coerce").dropna()
        b = pd.to_numeric(sub[sub[group_col] == groups[1]][value_col], errors="coerce").dropna()
        if len(a) == 0 or len(b) == 0:
            raise EngineError(
                f"Column '{value_col}' does not contain numeric values for one or "
                f"both groups - check that 'value_col' and 'group_col' aren't swapped."
            )
        if len(a) < 1 or len(b) < 1:
            raise EngineError("Each group needs at least 1 observation for Mann-Whitney U.")

        result = stats.mannwhitneyu(a, b, alternative="two-sided")

        # Rank-biserial correlation as effect size for Mann-Whitney U.
        n_a, n_b = len(a), len(b)
        r_rb = 1 - (2 * result.statistic) / (n_a * n_b)

        return {
            "test_type": "mann_whitney_u",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": {"type": "rank_biserial_r", "value": float(r_rb)},
            "n": int(n_a + n_b),
        }

    def _run_kruskal_wallis(self, params: dict) -> dict:
        group_col, value_col = params.get("group_col"), params.get("value_col")
        if not group_col or not value_col:
            raise EngineError("kruskal_wallis requires 'group_col' and 'value_col'.")
        self._require_columns(group_col, value_col)

        sub = self.data[[group_col, value_col]].dropna()
        sub[value_col] = pd.to_numeric(sub[value_col], errors="coerce")
        sub = sub.dropna()
        groups = [g[value_col].values for _, g in sub.groupby(group_col) if len(g) >= 2]
        if len(groups) < 2:
            raise EngineError("kruskal_wallis requires at least 2 groups with 2+ observations each.")

        result = stats.kruskal(*groups)

        # Eta-squared approximation for Kruskal-Wallis.
        n_total = sum(len(g) for g in groups)
        k = len(groups)
        eta_sq = (result.statistic - k + 1) / (n_total - k) if n_total > k else 0.0

        return {
            "test_type": "kruskal_wallis",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": {"type": "eta_squared", "value": float(max(eta_sq, 0.0))},
            "n": int(n_total),
        }

    def _run_wilcoxon_signed_rank(self, params: dict) -> dict:
        col1, col2 = params.get("col1"), params.get("col2")
        if not col1 or not col2:
            raise EngineError("wilcoxon_signed_rank requires 'col1' and 'col2'.")
        self._require_columns(col1, col2)

        sub = self.data[[col1, col2]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(sub) < 10:
            raise EngineError("wilcoxon_signed_rank requires at least 10 paired observations.")

        diffs = sub[col1] - sub[col2]
        # Drop zero differences (Wilcoxon requires non-zero differences).
        diffs = diffs[diffs != 0]
        if len(diffs) < 1:
            raise EngineError("All differences are zero — Wilcoxon test cannot be run.")

        result = stats.wilcoxon(diffs)

        # Rank-biserial correlation as effect size.
        n = len(diffs)
        r_rb = result.statistic / (n * (n + 1) / 2)

        return {
            "test_type": "wilcoxon_signed_rank",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "effect_size": {"type": "rank_biserial_r", "value": float(r_rb)},
            "n": int(n),
        }

    def _run_linear_regression(self, params: dict) -> dict:
        dependent_col = params.get("dependent_col")
        independent_cols = params.get("independent_cols")
        if not dependent_col or not independent_cols:
            raise EngineError(
                "linear_regression requires 'dependent_col' (str) and "
                "'independent_cols' (list of str)."
            )
        if isinstance(independent_cols, str):
            independent_cols = [independent_cols]

        all_cols = [dependent_col] + independent_cols
        self._require_columns(*all_cols)

        sub = self.data[all_cols].apply(pd.to_numeric, errors="coerce").dropna()
        if len(sub) < len(independent_cols) + 2:
            raise EngineError(
                f"linear_regression needs at least {len(independent_cols) + 2} "
                "complete observations."
            )

        y = sub[dependent_col]
        X = sm.add_constant(sub[independent_cols])
        model = sm.OLS(y, X).fit()

        return {
            "test_type": "linear_regression",
            "statistic": float(model.fvalue),          # F-statistic for model fit
            "p_value": float(model.f_pvalue),           # Overall model p-value
            "effect_size": {"type": "r_squared", "value": float(model.rsquared)},
            "n": int(len(sub)),
            "details": {
                "r_squared": float(model.rsquared),
                "adj_r_squared": float(model.rsquared_adj),
                "coefficients": {
                    col: float(coef)
                    for col, coef in zip(X.columns, model.params)
                },
                "coef_p_values": {
                    col: float(pv)
                    for col, pv in zip(X.columns, model.pvalues)
                },
            },
        }

    def _run_logistic_regression(self, params: dict) -> dict:
        dependent_col = params.get("dependent_col")
        independent_cols = params.get("independent_cols")
        if not dependent_col or not independent_cols:
            raise EngineError(
                "logistic_regression requires 'dependent_col' (str) and "
                "'independent_cols' (list of str)."
            )
        if isinstance(independent_cols, str):
            independent_cols = [independent_cols]

        all_cols = [dependent_col] + independent_cols
        self._require_columns(*all_cols)

        sub = self.data[all_cols].dropna().copy()
        for col in independent_cols:
            sub[col] = pd.to_numeric(sub[col], errors="coerce")
        sub = sub.dropna()

        if len(sub) < len(independent_cols) + 2:
            raise EngineError(
                f"logistic_regression needs at least {len(independent_cols) + 2} "
                "complete observations."
            )

        # Encode the outcome to 0/1 if it isn't already numeric binary.
        y_raw = sub[dependent_col]
        if not pd.api.types.is_numeric_dtype(y_raw) or set(y_raw.unique()) - {0, 1}:
            le = LabelEncoder()
            y = le.fit_transform(y_raw)
        else:
            y = y_raw.values

        X = sub[independent_cols].values

        # statsmodels Logit for p-values and pseudo-R².
        X_sm = sm.add_constant(X)
        try:
            logit_model = sm.Logit(y, X_sm).fit(disp=0, maxiter=200)
            p_value = float(logit_model.llr_pvalue)   # Likelihood-ratio test p-value
            statistic = float(logit_model.llr)         # LR chi-square statistic
            mcfadden_r2 = float(logit_model.prsquared) # McFadden pseudo-R²
            coef_pvalues = {
                independent_cols[i]: float(logit_model.pvalues[i + 1])
                for i in range(len(independent_cols))
            }
        except Exception as exc:
            raise EngineError(f"Logistic regression failed to converge: {exc}") from exc

        return {
            "test_type": "logistic_regression",
            "statistic": statistic,
            "p_value": p_value,
            "effect_size": {"type": "mcfadden_r2", "value": mcfadden_r2},
            "n": int(len(sub)),
            "details": {
                "mcfadden_r2": mcfadden_r2,
                "coef_p_values": coef_pvalues,
            },
        }
