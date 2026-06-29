"""
Tests for core/engine.py - the statistical test engine.

Reference values are computed independently via scipy/statsmodels
called directly in these tests (not by re-importing engine internals),
so they verify the engine's wrapper logic actually matches the
underlying library, not just that it runs without crashing.
"""
import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats as scipy_stats

from core.engine import StatisticalTestEngine


@pytest.fixture
def two_group_df():
    return pd.DataFrame({
        "group": ["control"] * 10 + ["treatment"] * 10,
        "score": [70, 72, 68, 71, 69, 73, 70, 71, 69, 72,
                   80, 82, 78, 81, 79, 83, 80, 81, 79, 82],
    })


class TestTTestIndependent:
    def test_matches_scipy_reference(self, two_group_df):
        a = two_group_df[two_group_df["group"] == "control"]["score"]
        b = two_group_df[two_group_df["group"] == "treatment"]["score"]
        expected = scipy_stats.ttest_ind(a, b, equal_var=True)

        engine = StatisticalTestEngine(two_group_df)
        result = engine.run_test("t_test_independent", {"group_col": "group", "value_col": "score"})

        assert "error" not in result
        if result["assumptions_checked"]["equal_variance"]:
            assert math.isclose(result["statistic"], expected.statistic, rel_tol=1e-6)
            assert math.isclose(result["p_value"], expected.pvalue, rel_tol=1e-6)
        assert result["n"] == 20

    def test_wrong_number_of_groups_errors(self, two_group_df):
        df = two_group_df.copy()
        df.loc[0, "group"] = "third_group"
        engine = StatisticalTestEngine(df)
        result = engine.run_test("t_test_independent", {"group_col": "group", "value_col": "score"})
        assert "error" in result
        assert "exactly 2 groups" in result["error"]

    def test_missing_columns_errors(self, two_group_df):
        engine = StatisticalTestEngine(two_group_df)
        result = engine.run_test("t_test_independent", {"group_col": "nope", "value_col": "also_nope"})
        assert "error" in result
        assert "not found in dataset" in result["error"]

    def test_missing_params_errors(self, two_group_df):
        engine = StatisticalTestEngine(two_group_df)
        result = engine.run_test("t_test_independent", {"group_col": "group"})
        assert "error" in result


class TestPairedTTest:
    def test_matches_scipy_reference(self):
        before = [80, 85, 78, 90, 82, 88, 75, 92]
        after = [85, 90, 80, 95, 89, 92, 79, 96]
        expected = scipy_stats.ttest_rel(before, after)

        df = pd.DataFrame({"before": before, "after": after})
        engine = StatisticalTestEngine(df)
        result = engine.run_test("paired_t_test", {"col1": "before", "col2": "after"})

        assert math.isclose(result["statistic"], expected.statistic, rel_tol=1e-6)
        assert math.isclose(result["p_value"], expected.pvalue, rel_tol=1e-6)

    def test_insufficient_data_errors(self):
        df = pd.DataFrame({"a": [1], "b": [2]})
        engine = StatisticalTestEngine(df)
        result = engine.run_test("paired_t_test", {"col1": "a", "col2": "b"})
        assert "error" in result


class TestOneWayAnova:
    def test_matches_scipy_reference(self):
        control = [12, 14, 11, 13, 15]
        treat_a = [18, 20, 17, 19, 21]
        treat_b = [25, 27, 24, 26, 28]
        expected = scipy_stats.f_oneway(control, treat_a, treat_b)

        df = pd.DataFrame({
            "group": ["control"] * 5 + ["a"] * 5 + ["b"] * 5,
            "value": control + treat_a + treat_b,
        })
        engine = StatisticalTestEngine(df)
        result = engine.run_test("one_way_anova", {"group_col": "group", "value_col": "value"})

        assert math.isclose(result["statistic"], expected.statistic, rel_tol=1e-6)
        assert math.isclose(result["p_value"], expected.pvalue, rel_tol=1e-6)

    def test_single_group_errors(self):
        df = pd.DataFrame({"group": ["a"] * 5, "value": [1, 2, 3, 4, 5]})
        engine = StatisticalTestEngine(df)
        result = engine.run_test("one_way_anova", {"group_col": "group", "value_col": "value"})
        assert "error" in result


class TestPearsonCorrelation:
    def test_matches_scipy_reference(self):
        x = [1, 2, 3, 4, 5, 6, 7, 8]
        y = [2, 4, 5, 4, 5, 7, 8, 9]
        expected = scipy_stats.pearsonr(x, y)

        df = pd.DataFrame({"x": x, "y": y})
        engine = StatisticalTestEngine(df)
        result = engine.run_test("pearson_correlation", {"col1": "x", "col2": "y"})

        assert math.isclose(result["statistic"], expected.statistic, rel_tol=1e-6)
        assert math.isclose(result["p_value"], expected.pvalue, rel_tol=1e-6)

    def test_too_few_points_errors(self):
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        engine = StatisticalTestEngine(df)
        result = engine.run_test("pearson_correlation", {"col1": "x", "col2": "y"})
        assert "error" in result


class TestSpearmanCorrelation:
    def test_matches_scipy_reference(self):
        x = [1, 2, 3, 4, 5, 6]
        y = [2, 1, 4, 3, 6, 5]
        expected = scipy_stats.spearmanr(x, y)

        df = pd.DataFrame({"x": x, "y": y})
        engine = StatisticalTestEngine(df)
        result = engine.run_test("spearman_correlation", {"col1": "x", "col2": "y"})

        assert math.isclose(result["statistic"], expected.statistic, rel_tol=1e-6)
        assert math.isclose(result["p_value"], expected.pvalue, rel_tol=1e-6)


class TestChiSquare:
    def test_matches_scipy_reference(self):
        df = pd.DataFrame({
            "smoker": ["yes"] * 30 + ["no"] * 30,
            "disease": ["yes"] * 20 + ["no"] * 10 + ["yes"] * 10 + ["no"] * 20,
        })
        contingency = pd.crosstab(df["smoker"], df["disease"])
        expected_chi2, expected_p, expected_dof, _ = scipy_stats.chi2_contingency(contingency)

        engine = StatisticalTestEngine(df)
        result = engine.run_test("chi_square", {"col1": "smoker", "col2": "disease"})

        assert math.isclose(result["statistic"], expected_chi2, rel_tol=1e-6)
        assert math.isclose(result["p_value"], expected_p, rel_tol=1e-6)
        assert result["degrees_of_freedom"] == expected_dof

    def test_table_too_small_errors(self):
        df = pd.DataFrame({"a": ["x"] * 4, "b": ["y"] * 4})
        engine = StatisticalTestEngine(df)
        result = engine.run_test("chi_square", {"col1": "a", "col2": "b"})
        assert "error" in result
        assert "at least 2 categories" in result["error"]


class TestMannWhitneyU:
    def test_matches_scipy_reference(self):
        a = [1, 2, 3, 4, 5]
        b = [6, 7, 8, 9, 10]
        expected = scipy_stats.mannwhitneyu(a, b, alternative="two-sided")

        df = pd.DataFrame({"group": ["a"] * 5 + ["b"] * 5, "value": a + b})
        engine = StatisticalTestEngine(df)
        result = engine.run_test("mann_whitney_u", {"group_col": "group", "value_col": "value"})

        assert math.isclose(result["statistic"], expected.statistic, rel_tol=1e-6)
        assert math.isclose(result["p_value"], expected.pvalue, rel_tol=1e-6)


class TestKruskalWallis:
    def test_matches_scipy_reference(self):
        a, b, c = [1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]
        expected = scipy_stats.kruskal(a, b, c)

        df = pd.DataFrame({
            "group": ["a"] * 4 + ["b"] * 4 + ["c"] * 4,
            "value": a + b + c,
        })
        engine = StatisticalTestEngine(df)
        result = engine.run_test("kruskal_wallis", {"group_col": "group", "value_col": "value"})

        assert math.isclose(result["statistic"], expected.statistic, rel_tol=1e-6)
        assert math.isclose(result["p_value"], expected.pvalue, rel_tol=1e-6)


class TestWilcoxonSignedRank:
    def test_matches_scipy_reference(self):
        col1 = [10, 12, 14, 9, 11, 13, 15, 8, 10, 12]
        col2 = [12, 11, 16, 10, 13, 12, 14, 9, 13, 14]
        diffs = np.array(col1) - np.array(col2)
        diffs_nonzero = diffs[diffs != 0]
        expected = scipy_stats.wilcoxon(diffs_nonzero)

        df = pd.DataFrame({"col1": col1, "col2": col2})
        engine = StatisticalTestEngine(df)
        result = engine.run_test("wilcoxon_signed_rank", {"col1": "col1", "col2": "col2"})

        assert math.isclose(result["statistic"], expected.statistic, rel_tol=1e-6)
        assert math.isclose(result["p_value"], expected.pvalue, rel_tol=1e-6)

    def test_too_few_pairs_errors(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [2, 3, 4]})
        engine = StatisticalTestEngine(df)
        result = engine.run_test("wilcoxon_signed_rank", {"col1": "a", "col2": "b"})
        assert "error" in result


class TestLinearRegression:
    def test_simple_perfect_fit(self):
        x = list(range(1, 11))
        y = [3 * v + 7 for v in x]
        df = pd.DataFrame({"x": x, "y": y})
        engine = StatisticalTestEngine(df)
        result = engine.run_test("linear_regression", {"dependent_col": "y", "independent_cols": ["x"]})

        assert math.isclose(result["effect_size"]["value"], 1.0, rel_tol=1e-6)
        assert math.isclose(result["details"]["coefficients"]["x"], 3.0, rel_tol=1e-6)

    def test_collinear_predictors_rejected(self):
        # Bug found earlier in this project: perfectly collinear
        # predictors made OLS silently return a meaningless F-statistic
        # (~1e+32) and p-value (~1e-279) via pseudo-inverse, instead of
        # failing. The engine now checks model.condition_number and
        # raises a clean error - this guards against regressing back to
        # the old silent-garbage behavior.
        rng = np.random.RandomState(0)
        df = pd.DataFrame({
            "x1": list(range(20)),
            "x2": [v * 2 for v in range(20)],  # perfectly collinear with x1
            "y": [v + rng.randn() * 0.01 for v in range(20)],
        })
        engine = StatisticalTestEngine(df)
        result = engine.run_test(
            "linear_regression", {"dependent_col": "y", "independent_cols": ["x1", "x2"]}
        )
        assert "error" in result
        assert "correlated" in result["error"]

    def test_well_conditioned_multiple_regression_succeeds(self):
        rng = np.random.RandomState(0)
        n = 30
        x1 = rng.normal(0, 1, n)
        x2 = rng.normal(0, 1, n)
        y = 2 * x1 - 1.5 * x2 + 3 + rng.normal(0, 0.3, n)
        df = pd.DataFrame({"x1": x1, "x2": x2, "y": y})
        engine = StatisticalTestEngine(df)
        result = engine.run_test(
            "linear_regression", {"dependent_col": "y", "independent_cols": ["x1", "x2"]}
        )
        assert "error" not in result
        assert result["details"]["condition_number"] < 100

    def test_insufficient_observations_errors(self):
        # Engine requires len(independent_cols) + 2 complete rows; for 1
        # predictor that's 3. Using only 2 rows genuinely falls short.
        df = pd.DataFrame({"x": [1, 2], "y": [1, 2]})
        engine = StatisticalTestEngine(df)
        result = engine.run_test("linear_regression", {"dependent_col": "y", "independent_cols": ["x"]})
        assert "error" in result


class TestLogisticRegression:
    def test_runs_and_returns_expected_shape(self):
        rng = np.random.RandomState(0)
        n = 60
        x = rng.normal(0, 1, n)
        outcome = (x + rng.normal(0, 0.5, n) > 0).astype(int)
        df = pd.DataFrame({"x": x, "outcome": outcome})
        engine = StatisticalTestEngine(df)
        result = engine.run_test(
            "logistic_regression", {"dependent_col": "outcome", "independent_cols": ["x"]}
        )
        assert "error" not in result
        assert result["effect_size"]["type"] == "mcfadden_r2"
        assert 0.0 <= result["effect_size"]["value"] <= 1.0

    def test_collinear_predictors_fail_to_converge(self):
        df = pd.DataFrame({
            "x1": list(range(20)),
            "x2": [v * 2 for v in range(20)],
            "outcome": [0] * 10 + [1] * 10,
        })
        engine = StatisticalTestEngine(df)
        result = engine.run_test(
            "logistic_regression", {"dependent_col": "outcome", "independent_cols": ["x1", "x2"]}
        )
        assert "error" in result


class TestEngineGeneral:
    def test_unsupported_test_type_errors(self, two_group_df):
        engine = StatisticalTestEngine(two_group_df)
        result = engine.run_test("not_a_real_test", {})
        assert "error" in result
        assert "not implemented" in result["error"]

    def test_no_data_loaded_errors(self):
        engine = StatisticalTestEngine(None)
        result = engine.run_test("t_test_independent", {"group_col": "a", "value_col": "b"})
        assert "error" in result
        assert "No dataset loaded" in result["error"]

    def test_all_supported_tests_have_handlers(self, two_group_df):
        engine = StatisticalTestEngine(two_group_df)
        for test_type in StatisticalTestEngine.SUPPORTED_TESTS:
            assert hasattr(engine, f"_run_{test_type}"), f"missing handler for {test_type}"
