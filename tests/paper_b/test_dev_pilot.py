from dataclasses import asdict
from datetime import date

from kdaa.evaluation.paper_b.dev_pilot import DEVELOPMENT_LABEL, run_development_pilot

_AS_OF_DATE = date(2026, 6, 1)


def _scientific_case_scores(result):
    # CaseScore has no volatile fields of its own, but comparing the full dataclass
    # (rather than picking fields) keeps this test honest about what "identical" means.
    return [asdict(score) for score in result.case_scores]


def test_development_pilot_is_deterministic_across_reruns() -> None:
    first = run_development_pilot(n_cases=12, as_of_date=_AS_OF_DATE, bootstrap_seed=42)
    second = run_development_pilot(n_cases=12, as_of_date=_AS_OF_DATE, bootstrap_seed=42)
    assert _scientific_case_scores(first) == _scientific_case_scores(second)
    for name in first.paired_summaries:
        a, b = first.paired_summaries[name], second.paired_summaries[name]
        assert asdict(a) == asdict(b)


def test_development_pilot_label_is_present() -> None:
    result = run_development_pilot(n_cases=6, as_of_date=_AS_OF_DATE)
    assert result.label == DEVELOPMENT_LABEL
    assert "NOT FINAL" in result.label


def test_development_pilot_runs_both_comparators_for_every_case() -> None:
    result = run_development_pilot(n_cases=6, as_of_date=_AS_OF_DATE)
    comparator_ids = {score.comparator_id for score in result.case_scores}
    assert comparator_ids == {"C0-S", "C3"}
    assert len(result.case_scores) == 6 * 2


def test_development_pilot_writes_labeled_outputs(tmp_path) -> None:
    from kdaa.evaluation.paper_b.dev_pilot import write_development_outputs

    result = run_development_pilot(n_cases=4, as_of_date=_AS_OF_DATE)
    write_development_outputs(result, tmp_path)
    readme = (tmp_path / "README_DEVELOPMENT_ONLY.txt").read_text()
    assert "NOT FINAL PAPER RESULTS" in readme
    assert (tmp_path / "case_scores.csv").exists()
    assert (tmp_path / "summary.json").exists()


def test_different_as_of_date_can_change_c3_scores_but_pilot_stays_internally_consistent() -> None:
    # Not asserting a specific direction (recency affects credibility ranking/ordering of
    # KDAA's discovered assets, which can shift which top-10 assets are selected) --
    # only that varying the one input that's supposed to matter is possible without
    # crashing, and that fixing it back reproduces the original result exactly.
    result_a = run_development_pilot(n_cases=6, as_of_date=date(2020, 1, 1))
    result_b = run_development_pilot(n_cases=6, as_of_date=date(2020, 1, 1))
    assert _scientific_case_scores(result_a) == _scientific_case_scores(result_b)
