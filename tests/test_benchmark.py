from kdaa.evaluation import run_synthetic_benchmark


def test_small_synthetic_benchmark(tmp_path) -> None:
    result, rows = run_synthetic_benchmark(n_units=5, seed=7, output_dir=tmp_path)
    assert result.n_units == 5
    assert len(rows) == 5
    assert 0.0 <= result.kdaa_concept_f1 <= 1.0
    assert result.kdaa_provenance_completeness == 1.0
    assert result.kdaa_unsupported_claim_rate == 0.0
    assert result.kdaa_confirmed_without_human_rate == 0.0
    assert (tmp_path / "benchmark_summary.json").exists()
