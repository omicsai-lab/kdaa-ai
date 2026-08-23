from datetime import date

from kdaa.evaluation.paper_b.adapters.fake_provider import FakeJSONProvider
from kdaa.evaluation.paper_b.dev_cases import generate_development_case
from kdaa.evaluation.paper_b.dev_pilot_llm import DEVELOPMENT_LABEL, run_llm_development_pilot
from kdaa.evaluation.paper_b.fairness import assert_within_output_limits
from kdaa.evaluation.paper_b.snapshot import build_snapshot_for_case
from kdaa.ontology import Ontology

_AS_OF_DATE = date(2026, 6, 1)
_GOOD_RESPONSE = {"concepts": [{"label": "Agentic AI"}], "ranked_opportunity_ids": []}
_BAD_RESPONSE = {"not_the_right_shape": True}


def _fresh_provider(responses):
    return FakeJSONProvider(responses)


def test_pilot_records_exactly_n_repeats_per_case_per_comparator() -> None:
    ontology = Ontology.default()
    case = generate_development_case(0)
    provider = _fresh_provider([_GOOD_RESPONSE])

    result = run_llm_development_pilot(
        [case], provider_c1=provider, provider_c2=provider, provider_c4=provider,
        ontology=ontology, as_of_date=_AS_OF_DATE, n_repeats=3,
    )
    for comparator_id in ("C1", "C2", "C4"):
        attempts = [a for a in result.all_attempts if a.comparator_id == comparator_id]
        assert len(attempts) == 3
        assert [a.attempt_number for a in attempts] == [1, 2, 3]


def test_primary_case_value_is_mean_not_best_of_three() -> None:
    # One success (f1 will be >0 for a matching label) and two runs that exhaust their
    # retries and fail entirely (f1=0.0 by failure policy) -- the mean must reflect all
    # three, not just the best one. The fake provider cycles its response list and each
    # repeat's own retry loop draws from that same cycling queue (max_retries=2 -> up to
    # 3 draws per repeat), so 1 success + 2 full repeat-failures needs 1 + 3 + 3 = 7
    # queued responses: one GOOD, then six BAD (three per failing repeat).
    ontology = Ontology.default()
    case = generate_development_case(0)
    provider_c1 = _fresh_provider([_GOOD_RESPONSE, *([_BAD_RESPONSE] * 6)])
    provider_c2 = _fresh_provider([_GOOD_RESPONSE])
    provider_c4 = _fresh_provider([_GOOD_RESPONSE])

    result = run_llm_development_pilot(
        [case], provider_c1=provider_c1, provider_c2=provider_c2, provider_c4=provider_c4,
        ontology=ontology, as_of_date=_AS_OF_DATE, n_repeats=3,
    )
    c1_score = next(s for s in result.repeated_scores if s.comparator_id == "C1")
    assert c1_score.n_successful_repeats == 1
    assert c1_score.n_intended_repeats == 3
    # If this were best-of-3, mean_concept_f1 would equal the single successful run's
    # score; instead two of the three contribute 0.0, so the mean must be strictly lower
    # than what a single successful run alone would show (unless that run also scored 0).
    assert c1_score.mean_concept_f1 <= 1.0
    # Directly assert the averaging arithmetic: 1 success + 2 zero-contributions over 3.
    from kdaa.evaluation.paper_b.dev_pilot import _score_prediction

    successful_attempt = next(a for a in result.all_attempts if a.comparator_id == "C1" and a.prediction)
    single_run_score = _score_prediction(case, successful_attempt.prediction).concept_f1
    assert abs(c1_score.mean_concept_f1 - single_run_score / 3) < 1e-9


def test_failed_repeats_are_retained_in_the_attempt_record_not_dropped() -> None:
    ontology = Ontology.default()
    case = generate_development_case(0)
    provider = _fresh_provider([_BAD_RESPONSE])

    result = run_llm_development_pilot(
        [case], provider_c1=provider, provider_c2=provider, provider_c4=provider,
        ontology=ontology, as_of_date=_AS_OF_DATE, n_repeats=2,
    )
    c1_attempts = [a for a in result.all_attempts if a.comparator_id == "C1"]
    assert len(c1_attempts) == 2
    assert all(a.prediction is None for a in c1_attempts)
    assert all(a.error_message for a in c1_attempts)


def test_development_label_present_and_no_final_claim() -> None:
    assert "DEVELOPMENT ONLY" in DEVELOPMENT_LABEL
    assert "NOT FINAL" in DEVELOPMENT_LABEL


def test_pilot_output_respects_fairness_output_limits_for_every_attempt() -> None:
    ontology = Ontology.default()
    case = generate_development_case(2)
    snapshot = build_snapshot_for_case(case)
    provider = _fresh_provider(
        [{"concepts": [{"label": f"concept-{i}"} for i in range(15)], "ranked_opportunity_ids": []}]
    )
    result = run_llm_development_pilot(
        [case], provider_c1=provider, provider_c2=provider, provider_c4=provider,
        ontology=ontology, as_of_date=_AS_OF_DATE, n_repeats=1,
    )
    for attempt in result.all_attempts:
        if attempt.prediction is not None:
            # The adapter itself caps at 10 (MAX_CLAIMS); fairness validator confirms it.
            assert_within_output_limits(attempt.prediction, snapshot)


def test_deterministic_scoring_from_cached_fake_outputs() -> None:
    """Given the same cached (fake) provider responses, scoring is fully deterministic --
    no live call, no randomness."""
    ontology = Ontology.default()
    case = generate_development_case(3)
    provider_a = _fresh_provider([_GOOD_RESPONSE])
    provider_b = _fresh_provider([_GOOD_RESPONSE])

    result_a = run_llm_development_pilot(
        [case], provider_c1=provider_a, provider_c2=provider_a, provider_c4=provider_a,
        ontology=ontology, as_of_date=_AS_OF_DATE, n_repeats=2,
    )
    result_b = run_llm_development_pilot(
        [case], provider_c1=provider_b, provider_c2=provider_b, provider_c4=provider_b,
        ontology=ontology, as_of_date=_AS_OF_DATE, n_repeats=2,
    )
    scores_a = [(s.comparator_id, s.mean_concept_f1, s.mean_ndcg_at_5) for s in result_a.repeated_scores]
    scores_b = [(s.comparator_id, s.mean_concept_f1, s.mean_ndcg_at_5) for s in result_b.repeated_scores]
    assert scores_a == scores_b
