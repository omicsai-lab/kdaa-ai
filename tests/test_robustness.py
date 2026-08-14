from kdaa.evaluation import run_robustness_suite


def test_robustness_suite_has_expected_directional_behavior(tmp_path) -> None:
    result, rows = run_robustness_suite(output_dir=tmp_path)
    assert len(rows) == 6
    assert result.all_cases_provenance_complete is True
    assert result.all_cases_zero_auto_confirmation is True
    assert result.duplicate_signature_jaccard == 1.0
    assert result.duplicate_asset_count_delta == 0
    assert result.duplicate_mean_credibility_delta == 0.0
    assert result.stale_mean_credibility_delta < 0
    assert result.unknown_role_attribution_delta < 0
    assert result.irrelevant_noise_signature_jaccard >= 0.95
    assert (tmp_path / "robustness_summary.json").exists()
    assert (tmp_path / "robustness_cases.csv").exists()
