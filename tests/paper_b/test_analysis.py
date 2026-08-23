import math

from kdaa.evaluation.paper_b.analysis import paired_bootstrap_ci, summarize_paired


def test_paired_bootstrap_ci_empty_input_does_not_crash() -> None:
    assert paired_bootstrap_ci([]) == (0.0, 0.0)


def test_paired_bootstrap_ci_single_case_returns_that_value_both_bounds() -> None:
    assert paired_bootstrap_ci([0.4]) == (0.4, 0.4)


def test_paired_bootstrap_ci_is_deterministic_for_fixed_seed() -> None:
    differences = [0.1, -0.2, 0.3, 0.05, -0.1]
    first = paired_bootstrap_ci(differences, seed=7)
    second = paired_bootstrap_ci(differences, seed=7)
    assert first == second


def test_summarize_paired_empty_lists_returns_zeroed_summary() -> None:
    summary = summarize_paired("metric", [], [])
    assert summary.n_cases == 0
    assert summary.mean_paired_difference == 0.0


def test_summarize_paired_matches_hand_calculated_mean_and_median() -> None:
    values_a = [0.8, 0.6, 0.4]
    values_b = [0.5, 0.5, 0.5]
    summary = summarize_paired("metric", values_a, values_b, seed=1)
    assert math.isclose(summary.mean_a, (0.8 + 0.6 + 0.4) / 3)
    assert summary.mean_b == 0.5
    for actual, expected in zip(summary.per_case_differences, (0.3, 0.1, -0.1), strict=True):
        assert math.isclose(actual, expected, abs_tol=1e-9)
    assert math.isclose(summary.mean_paired_difference, (0.3 + 0.1 - 0.1) / 3)
    assert math.isclose(summary.median_paired_difference, 0.1, abs_tol=1e-9)


def test_summarize_paired_rejects_mismatched_lengths() -> None:
    import pytest

    with pytest.raises(ValueError, match="same length"):
        summarize_paired("metric", [0.1, 0.2], [0.1])
