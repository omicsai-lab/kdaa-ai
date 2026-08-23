import math

from kdaa.evaluation.paper_b.schemas import OwnershipLabel, PredictedClaim, PredictedOpportunity
from kdaa.evaluation.paper_b.scoring.attribution import score_attribution
from kdaa.evaluation.paper_b.scoring.concept_matching import score_concepts
from kdaa.evaluation.paper_b.scoring.opportunities import dcg_at_k, score_opportunities
from kdaa.evaluation.paper_b.scoring.semantic_support import score_semantic_support
from kdaa.evaluation.paper_b.truth import TrueAssetConcept, TrueOpportunityRelevance

# --- E1: concept matching --------------------------------------------------------------


def test_e1_exact_match() -> None:
    predicted = [PredictedClaim(claim_id="k1", label="Agentic AI")]
    true = [TrueAssetConcept(concept_id="agentic_ai", canonical_label="Agentic AI")]
    result = score_concepts("c1", predicted, true)
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1 == 1.0
    assert result.exact_or_alias_matches == 1
    assert result.matched_pairs == (("k1", "agentic_ai"),)


def test_e1_alias_match() -> None:
    # Checkpoint A's matcher does exact/alias word-boundary containment, not stemming;
    # the predicted label matches via the declared alias, not the canonical label.
    predicted = [PredictedClaim(claim_id="k1", label="Our GenAI capability")]
    true = [
        TrueAssetConcept(concept_id="generative_ai", canonical_label="Generative AI", aliases=["genai"])
    ]
    result = score_concepts("c1", predicted, true)
    assert result.recall == 1.0
    assert result.exact_or_alias_matches == 1


def test_e1_one_to_one_matching_prevents_double_counting() -> None:
    # One broad prediction that textually contains both true labels must match at most
    # one of them, not both.
    predicted = [PredictedClaim(claim_id="k1", label="Agentic AI and Bioinformatics")]
    true = [
        TrueAssetConcept(concept_id="agentic_ai", canonical_label="Agentic AI"),
        TrueAssetConcept(concept_id="bioinformatics", canonical_label="Bioinformatics"),
    ]
    result = score_concepts("c1", predicted, true)
    assert len(result.matched_pairs) == 1
    assert result.recall == 0.5  # only one of the two true concepts is credited
    assert result.precision == 1.0


def test_e1_precision_recall_hand_calculation() -> None:
    # 3 predicted, 2 true: one correct, one wrong, one extra false positive.
    predicted = [
        PredictedClaim(claim_id="k1", label="Agentic AI"),
        PredictedClaim(claim_id="k2", label="Completely unrelated capability"),
        PredictedClaim(claim_id="k3", label="Also unrelated"),
    ]
    true = [
        TrueAssetConcept(concept_id="agentic_ai", canonical_label="Agentic AI"),
        TrueAssetConcept(concept_id="bioinformatics", canonical_label="Bioinformatics"),
    ]
    result = score_concepts("c1", predicted, true)
    assert result.precision == 1 / 3
    assert result.recall == 1 / 2
    expected_f1 = 2 * (1 / 3) * (1 / 2) / ((1 / 3) + (1 / 2))
    assert math.isclose(result.f1, expected_f1)


def test_e1_no_predictions_and_no_truth_is_trivially_perfect() -> None:
    result = score_concepts("c1", [], [])
    assert result.f1 == 1.0


def test_e1_no_predictions_with_truth_present_scores_zero() -> None:
    true = [TrueAssetConcept(concept_id="agentic_ai", canonical_label="Agentic AI")]
    result = score_concepts("c1", [], true)
    assert result.precision == 0.0
    assert result.recall == 0.0
    assert result.f1 == 0.0


def test_e1_semantic_evaluator_is_used_only_when_no_exact_or_alias_match() -> None:
    class AlwaysMatchEvaluator:
        def similarity(self, text_a: str, text_b: str) -> float:
            return 0.9

    predicted = [PredictedClaim(claim_id="k1", label="Something else entirely")]
    true = [TrueAssetConcept(concept_id="agentic_ai", canonical_label="Agentic AI")]
    result = score_concepts("c1", predicted, true, semantic_evaluator=AlwaysMatchEvaluator())
    assert result.semantic_only_matches == 1
    assert result.exact_or_alias_matches == 0


# --- E2: semantic unsupported-claim rate ------------------------------------------------


def test_e2_nonexistent_capability_is_unsupported() -> None:
    predicted = [PredictedClaim(claim_id="k1", label="Nonexistent capability")]
    true = [TrueAssetConcept(concept_id="agentic_ai", canonical_label="Agentic AI")]
    matches = score_concepts("c1", predicted, true).matched_pairs
    result = score_semantic_support("c1", predicted, true, matches)
    assert result.unsupported_claim_rate == 1.0
    assert result.claim_results[0].reasons == ("nonexistent_capability",)


def test_e2_overbroad_scope_cites_trace_outside_true_support() -> None:
    predicted = [PredictedClaim(claim_id="k1", label="Agentic AI", cited_trace_ids=["t1", "t99"])]
    true = [
        TrueAssetConcept(concept_id="agentic_ai", canonical_label="Agentic AI", supporting_trace_ids=["t1"])
    ]
    matches = score_concepts("c1", predicted, true).matched_pairs
    result = score_semantic_support("c1", predicted, true, matches)
    assert result.claim_results[0].unsupported is True
    assert "materially_overbroad_scope" in result.claim_results[0].reasons


def test_e2_citing_only_true_supporting_traces_is_not_overbroad() -> None:
    predicted = [PredictedClaim(claim_id="k1", label="Agentic AI", cited_trace_ids=["t1"])]
    true = [
        TrueAssetConcept(concept_id="agentic_ai", canonical_label="Agentic AI", supporting_trace_ids=["t1", "t2"])
    ]
    matches = score_concepts("c1", predicted, true).matched_pairs
    result = score_semantic_support("c1", predicted, true, matches)
    assert "materially_overbroad_scope" not in result.claim_results[0].reasons


def test_e2_unsupported_currentness_for_stale_concept() -> None:
    predicted = [PredictedClaim(claim_id="k1", label="Agentic AI")]
    true = [TrueAssetConcept(concept_id="agentic_ai", canonical_label="Agentic AI", is_current=False)]
    matches = score_concepts("c1", predicted, true).matched_pairs
    result = score_semantic_support("c1", predicted, true, matches)
    assert "unsupported_currentness" in result.claim_results[0].reasons


def test_e2_unsupported_sole_ownership() -> None:
    predicted = [PredictedClaim(claim_id="k1", label="Agentic AI", ownership=OwnershipLabel.FOCAL_UNIT)]
    true = [
        TrueAssetConcept(
            concept_id="agentic_ai", canonical_label="Agentic AI", ownership_state=OwnershipLabel.SHARED
        )
    ]
    matches = score_concepts("c1", predicted, true).matched_pairs
    result = score_semantic_support("c1", predicted, true, matches)
    assert "unsupported_sole_ownership" in result.claim_results[0].reasons


def test_e2_focal_unit_claim_matching_focal_unit_truth_is_not_flagged() -> None:
    predicted = [PredictedClaim(claim_id="k1", label="Agentic AI", ownership=OwnershipLabel.FOCAL_UNIT)]
    true = [
        TrueAssetConcept(
            concept_id="agentic_ai", canonical_label="Agentic AI", ownership_state=OwnershipLabel.FOCAL_UNIT
        )
    ]
    matches = score_concepts("c1", predicted, true).matched_pairs
    result = score_semantic_support("c1", predicted, true, matches)
    assert "unsupported_sole_ownership" not in result.claim_results[0].reasons


def test_e2_unsupported_dependency_when_not_cited() -> None:
    predicted = [PredictedClaim(claim_id="k1", label="Agentic AI", cited_trace_ids=["t1"])]
    true = [
        TrueAssetConcept(
            concept_id="agentic_ai",
            canonical_label="Agentic AI",
            supporting_trace_ids=["t1"],
            dependency_trace_ids=["t2"],
        )
    ]
    matches = score_concepts("c1", predicted, true).matched_pairs
    result = score_semantic_support("c1", predicted, true, matches)
    assert "unsupported_dependency" in result.claim_results[0].reasons


def test_e2_fully_supported_claim_has_no_reasons() -> None:
    predicted = [
        PredictedClaim(
            claim_id="k1", label="Agentic AI", cited_trace_ids=["t1"], ownership=OwnershipLabel.UNRESOLVED
        )
    ]
    true = [
        TrueAssetConcept(
            concept_id="agentic_ai",
            canonical_label="Agentic AI",
            supporting_trace_ids=["t1"],
            is_current=True,
            ownership_state=OwnershipLabel.UNRESOLVED,
        )
    ]
    matches = score_concepts("c1", predicted, true).matched_pairs
    result = score_semantic_support("c1", predicted, true, matches)
    assert result.claim_results[0].unsupported is False
    assert result.unsupported_claim_rate == 0.0


def test_e2_rate_is_zero_for_no_active_claims() -> None:
    result = score_semantic_support("c1", [], [], ())
    assert result.unsupported_claim_rate == 0.0
    assert result.n_active_claims == 0


# --- E3: false individualization rate ----------------------------------------------------


def test_e3_false_individualization_counted_correctly() -> None:
    predicted = [PredictedClaim(claim_id="k1", label="Agentic AI", ownership=OwnershipLabel.FOCAL_UNIT)]
    true = [
        TrueAssetConcept(
            concept_id="agentic_ai", canonical_label="Agentic AI", ownership_state=OwnershipLabel.SHARED
        )
    ]
    matches = (("k1", "agentic_ai"),)
    result = score_attribution("c1", predicted, true, matches)
    assert result.n_non_focal_recovered == 1
    assert result.n_false_individualized == 1
    assert result.false_individualization_rate == 1.0


def test_e3_denominator_excludes_all_focal_unit_case() -> None:
    predicted = [PredictedClaim(claim_id="k1", label="Agentic AI", ownership=OwnershipLabel.FOCAL_UNIT)]
    true = [
        TrueAssetConcept(
            concept_id="agentic_ai", canonical_label="Agentic AI", ownership_state=OwnershipLabel.FOCAL_UNIT
        )
    ]
    matches = (("k1", "agentic_ai"),)
    result = score_attribution("c1", predicted, true, matches)
    assert result.n_non_focal_recovered == 0
    assert result.false_individualization_rate is None


def test_e3_unresolved_everywhere_has_zero_false_individualization_but_zero_coverage() -> None:
    # The "abstention should not look artificially superior" guardrail: an
    # always-UNRESOLVED comparator gets a perfect (0.0) false-individualization rate,
    # but attribution_coverage=0.0 must reveal it never actually attributed anything.
    predicted = [
        PredictedClaim(claim_id="k1", label="Agentic AI", ownership=OwnershipLabel.UNRESOLVED),
        PredictedClaim(claim_id="k2", label="Bioinformatics", ownership=OwnershipLabel.UNRESOLVED),
    ]
    true = [
        TrueAssetConcept(
            concept_id="agentic_ai", canonical_label="Agentic AI", ownership_state=OwnershipLabel.SHARED
        ),
        TrueAssetConcept(
            concept_id="bioinformatics", canonical_label="Bioinformatics", ownership_state=OwnershipLabel.EXTERNAL
        ),
    ]
    matches = (("k1", "agentic_ai"), ("k2", "bioinformatics"))
    result = score_attribution("c1", predicted, true, matches)
    assert result.false_individualization_rate == 0.0
    assert result.attribution_coverage == 0.0
    assert result.unresolved_rate == 1.0


def test_e3_no_matched_pairs_gives_none_for_all_rates() -> None:
    result = score_attribution("c1", [], [], ())
    assert result.false_individualization_rate is None
    assert result.attribution_coverage is None
    assert result.unresolved_rate is None


# --- E4: opportunity nDCG@5 ---------------------------------------------------------------


def test_e4_dcg_hand_calculation() -> None:
    grades = [3, 2, 0, 1]
    expected = 3 / math.log2(2) + 2 / math.log2(3) + 0 / math.log2(4) + 1 / math.log2(5)
    assert math.isclose(dcg_at_k(grades, 4), expected)


def test_e4_perfect_ranking_scores_one() -> None:
    true_relevance = [
        TrueOpportunityRelevance(opportunity_id="a", relevance_grade=3),
        TrueOpportunityRelevance(opportunity_id="b", relevance_grade=2),
        TrueOpportunityRelevance(opportunity_id="c", relevance_grade=1),
        TrueOpportunityRelevance(opportunity_id="d", relevance_grade=0),
    ]
    ranked = [
        PredictedOpportunity(opportunity_id="a", rank=1),
        PredictedOpportunity(opportunity_id="b", rank=2),
        PredictedOpportunity(opportunity_id="c", rank=3),
        PredictedOpportunity(opportunity_id="d", rank=4),
    ]
    result = score_opportunities("c1", ranked, true_relevance)
    assert result.is_valid_ranking is True
    assert math.isclose(result.ndcg_at_5, 1.0)


def test_e4_hand_calculated_ndcg_worked_example() -> None:
    # 4 opportunities, grades [3,2,1,0]; predicted order deliberately reversed.
    true_relevance = [
        TrueOpportunityRelevance(opportunity_id="a", relevance_grade=3),
        TrueOpportunityRelevance(opportunity_id="b", relevance_grade=2),
        TrueOpportunityRelevance(opportunity_id="c", relevance_grade=1),
        TrueOpportunityRelevance(opportunity_id="d", relevance_grade=0),
    ]
    ranked = [
        PredictedOpportunity(opportunity_id="d", rank=1),
        PredictedOpportunity(opportunity_id="c", rank=2),
        PredictedOpportunity(opportunity_id="b", rank=3),
        PredictedOpportunity(opportunity_id="a", rank=4),
    ]
    result = score_opportunities("c1", ranked, true_relevance)
    dcg = 0 / math.log2(2) + 1 / math.log2(3) + 2 / math.log2(4) + 3 / math.log2(5)
    idcg = 3 / math.log2(2) + 2 / math.log2(3) + 1 / math.log2(4) + 0 / math.log2(5)
    assert math.isclose(result.dcg_at_5, dcg)
    assert math.isclose(result.idcg_at_5, idcg)
    assert math.isclose(result.ndcg_at_5, dcg / idcg)


def test_e4_all_zero_relevance_scores_zero_not_undefined_error() -> None:
    true_relevance = [TrueOpportunityRelevance(opportunity_id="a", relevance_grade=0)]
    ranked = [PredictedOpportunity(opportunity_id="a", rank=1)]
    result = score_opportunities("c1", ranked, true_relevance)
    assert result.ndcg_at_5 == 0.0


def test_e4_missing_or_incomplete_ranking_is_explicit_failure_not_backfilled() -> None:
    true_relevance = [
        TrueOpportunityRelevance(opportunity_id="a", relevance_grade=3),
        TrueOpportunityRelevance(opportunity_id="b", relevance_grade=1),
    ]
    partial_ranking = [PredictedOpportunity(opportunity_id="a", rank=1)]  # missing "b"
    result = score_opportunities("c1", partial_ranking, true_relevance)
    assert result.is_valid_ranking is False
    assert result.ndcg_at_5 == 0.0


def test_e4_empty_ranking_is_explicit_failure() -> None:
    true_relevance = [TrueOpportunityRelevance(opportunity_id="a", relevance_grade=3)]
    result = score_opportunities("c1", [], true_relevance)
    assert result.is_valid_ranking is False
    assert result.ndcg_at_5 == 0.0


def test_e4_ranking_naming_unknown_id_is_explicit_failure() -> None:
    true_relevance = [TrueOpportunityRelevance(opportunity_id="a", relevance_grade=3)]
    bad_ranking = [PredictedOpportunity(opportunity_id="not-a-real-id", rank=1)]
    result = score_opportunities("c1", bad_ranking, true_relevance)
    assert result.is_valid_ranking is False
