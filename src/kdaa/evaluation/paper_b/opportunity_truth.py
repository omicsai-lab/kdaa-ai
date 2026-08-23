"""Independent, truth-side opportunity-relevance grading (Checkpoint B correction).

Checkpoint A had a real circularity: C3's opportunity-ranking function and the hidden
-relevance generator both read the exact same ``OPPORTUNITY_CONCEPT_TAGS`` dictionary, so
C3's E4 score was largely a replay of a lookup table rather than a genuine measurement of
opportunity-matching ability. This module replaces that shared table with two decoupled
mechanisms:

1. **Hidden grading (here)**: each opportunity has an authored, hidden
   ``OpportunityRequirement`` (required/optional/disqualifying concepts). A grade is
   computed only from a case's *true* concepts against this record. Never exposed to any
   comparator.
2. **Comparator ranking** (``opportunity_catalog.rank_opportunities_by_visible_text``):
   computed live from each opportunity's own *visible* title/description text, matched
   against a comparator's *own predicted* concepts. This mechanism never reads this
   module and has no access to the requirement records at all -- a comparator cannot
   reconstruct hidden grades even if it correctly predicts every true concept, because it
   would still need the opportunity's description to actually use a matchable phrase.

The two mechanisms deliberately use different code paths and different (true vs.
predicted) concept sets, so a comparator's E4 score now depends on genuinely predicting
opportunity relevance from public information, not on replaying an authored lookup.

This module is truth-authorized tooling and must never be imported by
``kdaa.evaluation.paper_b.adapters`` -- see ``boundary.py`` and
``tests/paper_b/test_e4_independence.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OpportunityRequirement:
    opportunity_id: str
    required_concepts: frozenset[str] = field(default_factory=frozenset)
    optional_concepts: frozenset[str] = field(default_factory=frozenset)
    disqualifying_concepts: frozenset[str] = field(default_factory=frozenset)


# Authored against the real kdaa.resources.ontology.yaml concept keys. Deliberately not
# the same association used to write the visible catalog descriptions in
# opportunity_catalog.py -- see that module's docstring for why that matters.
OPPORTUNITY_REQUIREMENTS: dict[str, OpportunityRequirement] = {
    "opp-repository": OpportunityRequirement(
        opportunity_id="opp-repository",
        required_concepts=frozenset({"software_engineering"}),
        optional_concepts=frozenset({"research_computing", "data_engineering"}),
        disqualifying_concepts=frozenset({"teaching_curriculum"}),
    ),
    "opp-living-document": OpportunityRequirement(
        opportunity_id="opp-living-document",
        required_concepts=frozenset({"reproducible_research"}),
        optional_concepts=frozenset({"research_computing", "scientific_writing"}),
    ),
    "opp-knowledge-base": OpportunityRequirement(
        opportunity_id="opp-knowledge-base",
        required_concepts=frozenset({"knowledge_management"}),
        optional_concepts=frozenset({"information_systems", "data_engineering"}),
    ),
    "opp-deployable-product": OpportunityRequirement(
        opportunity_id="opp-deployable-product",
        required_concepts=frozenset({"product_development"}),
        optional_concepts=frozenset({"software_engineering", "generative_ai"}),
    ),
    "opp-public-content": OpportunityRequirement(
        opportunity_id="opp-public-content",
        required_concepts=frozenset({"teaching_curriculum"}),
        optional_concepts=frozenset({"scientific_writing"}),
    ),
    "opp-grant-proposal": OpportunityRequirement(
        opportunity_id="opp-grant-proposal",
        required_concepts=frozenset({"clinical_trials"}),
        optional_concepts=frozenset({"causal_inference", "statistical_modeling"}),
    ),
    "opp-benchmark-dataset": OpportunityRequirement(
        opportunity_id="opp-benchmark-dataset",
        required_concepts=frozenset({"genomics"}),
        optional_concepts=frozenset({"multi_omics", "transcriptomics"}),
    ),
    "opp-training-course": OpportunityRequirement(
        opportunity_id="opp-training-course",
        required_concepts=frozenset({"teaching_curriculum"}),
        optional_concepts=frozenset({"machine_learning"}),
    ),
    "opp-consulting-service": OpportunityRequirement(
        opportunity_id="opp-consulting-service",
        required_concepts=frozenset({"knowledge_management"}),
        optional_concepts=frozenset({"research_computing"}),
    ),
    "opp-methods-paper": OpportunityRequirement(
        opportunity_id="opp-methods-paper",
        required_concepts=frozenset({"causal_inference"}),
        optional_concepts=frozenset({"statistical_modeling", "survival_analysis"}),
    ),
}


def compute_relevance_grade(true_concept_keys: set[str], opportunity_id: str) -> int:
    """0-3 hidden relevance grade from truth-side data only.

    - Any disqualifying concept present -> 0, regardless of anything else.
    - No required concepts satisfied (when required concepts exist) -> 0.
    - All required concepts satisfied -> base 3; some (but not all) -> base 2; only an
      optional concept present when there are no required concepts -> base 1.
    - An additional optional-concept hit nudges the grade up by 1 (capped at 3).
    """
    requirement = OPPORTUNITY_REQUIREMENTS.get(opportunity_id)
    if requirement is None:
        return 0
    if requirement.disqualifying_concepts & true_concept_keys:
        return 0

    optional_hit = bool(requirement.optional_concepts & true_concept_keys)

    if requirement.required_concepts:
        required_hits = len(requirement.required_concepts & true_concept_keys)
        if required_hits == 0:
            return 0
        base = 3 if required_hits == len(requirement.required_concepts) else 2
    else:
        base = 1 if optional_hit else 0

    grade = base + 1 if (optional_hit and base < 3) else base
    return max(0, min(3, grade))
