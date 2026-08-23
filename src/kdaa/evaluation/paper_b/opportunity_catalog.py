"""The fixed, development-stage opportunity catalog shared by every case (Freeze Section
9.2: "candidate catalog of 10 opportunities"; Checkpoint A simplification: one fixed
catalog reused across all development cases rather than a per-case catalog).

Deliberately truth-free (imports only ``.schemas``) so it can be imported both by
``dev_cases.py`` (truth-authorized, to compute hidden relevance grades) and by inference
-side adapters under ``kdaa.evaluation.paper_b.adapters`` (which must never import
``kdaa.evaluation.paper_b.truth`` -- see ``boundary.py``) for opportunity ranking.
"""

from __future__ import annotations

from .schemas import OpportunityCandidate

DEV_OPPORTUNITY_CATALOG: tuple[OpportunityCandidate, ...] = (
    OpportunityCandidate(
        opportunity_id="opp-repository",
        title="Publish a maintained reusable repository",
        description="Package the documented capability as an installable, tested repository.",
    ),
    OpportunityCandidate(
        opportunity_id="opp-living-document",
        title="Create a living methods document",
        description="Turn the documented protocol or workflow into a maintained reference document.",
    ),
    OpportunityCandidate(
        opportunity_id="opp-knowledge-base",
        title="Build a structured internal knowledge base",
        description="Consolidate the evidence into a queryable internal knowledge resource.",
    ),
    OpportunityCandidate(
        opportunity_id="opp-deployable-product",
        title="Ship a deployable product or tool",
        description="Turn the software or workflow evidence into a deployable, user-facing product.",
    ),
    OpportunityCandidate(
        opportunity_id="opp-public-content",
        title="Produce public educational content",
        description="Translate the documented expertise into an accessible public explainer.",
    ),
    OpportunityCandidate(
        opportunity_id="opp-grant-proposal",
        title="Draft a grant proposal built on this capability",
        description="Use the documented track record as preliminary evidence for a funding proposal.",
    ),
    OpportunityCandidate(
        opportunity_id="opp-benchmark-dataset",
        title="Release a benchmark dataset",
        description="Package the underlying data as a versioned, reusable benchmark resource.",
    ),
    OpportunityCandidate(
        opportunity_id="opp-training-course",
        title="Develop a training course",
        description="Turn the documented curriculum or teaching evidence into a structured course.",
    ),
    OpportunityCandidate(
        opportunity_id="opp-consulting-service",
        title="Offer a consulting or advisory service",
        description="Formalize the documented expertise as an advisory or consulting offering.",
    ),
    OpportunityCandidate(
        opportunity_id="opp-methods-paper",
        title="Write a methods paper generalizing the approach",
        description="Generalize the documented method into a standalone methodological publication.",
    ),
)

# Ontology concept keys each opportunity is relevant to. Used by dev_cases.py to compute
# hidden relevance grades from true concepts, and by the C3 adapter to rank the catalog
# from its own discovered concept tags -- the same mapping, applied to two different
# (predicted vs. true) concept sets, which is what makes the two rankings comparable
# without either side seeing the other's data.
OPPORTUNITY_CONCEPT_TAGS: dict[str, frozenset[str]] = {
    "opp-repository": frozenset({"software_engineering", "agentic_ai", "data_engineering"}),
    "opp-living-document": frozenset({"reproducible_research", "research_computing"}),
    "opp-knowledge-base": frozenset({"research_computing", "data_engineering", "knowledge_management"}),
    "opp-deployable-product": frozenset({"software_engineering", "agentic_ai", "generative_ai"}),
    "opp-public-content": frozenset({"ai_curriculum", "teaching", "science_communication"}),
    "opp-grant-proposal": frozenset({"clinical_trials", "causal_inference", "statistical_modeling"}),
    "opp-benchmark-dataset": frozenset({"multi_omics", "genomics", "transcriptomics"}),
    "opp-training-course": frozenset({"ai_curriculum", "teaching"}),
    "opp-consulting-service": frozenset({"research_computing", "knowledge_management"}),
    "opp-methods-paper": frozenset({"causal_inference", "statistical_modeling", "survival_analysis"}),
}


def relevance_grade(concept_keys: set[str], opportunity_id: str) -> int:
    """Shared 0-3 grading rule (min(3, overlap)) used for both hidden relevance (truth
    side) and predicted relevance signals (inference side, if a comparator wants one)."""
    tags = OPPORTUNITY_CONCEPT_TAGS.get(opportunity_id, frozenset())
    return min(3, len(concept_keys & tags))
