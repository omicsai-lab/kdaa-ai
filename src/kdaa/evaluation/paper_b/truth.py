"""Truth-side ground-truth records for Paper B (KBS).

STRUCTURAL ISOLATION: nothing in this module may be imported by inference-side code --
comparator/adapter implementations, ``kdaa.discovery``, ``kdaa.providers``, or
``kdaa.pipeline``. That boundary is not merely a naming convention:
``kdaa.evaluation.paper_b.__init__`` deliberately does not re-export anything from this
module, and ``boundary.find_truth_leakage`` statically scans the inference-side namespaces
listed in ``boundary.INFERENCE_BOUNDARY_PREFIXES`` for any direct import of this module
(absolute, aliased, ``from ... import ...``, or relative), so a future direct-import
violation fails a test rather than depending on reviewers noticing it. This is direct
import-boundary enforcement, not transitive dependency-graph enforcement: a boundary module
that imports some other, non-boundary module which itself imports ``truth`` would not be
caught by this check today -- see ``boundary.py`` and
``tests/paper_b/test_truth_isolation.py``.

Per Freeze Section 9.4 (leakage prevention), final truth must live outside model-visible
bundles and outside inference-accessible metadata; this module is that separate location.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from .base import StrictEvalModel
from .hashing import SCHEMA_VERSION
from .schemas import ChallengeCategory, OwnershipLabel


class TrueAssetConcept(StrictEvalModel):
    """Hidden ground truth for one true asset concept in a case."""

    concept_id: str = Field(min_length=1)
    canonical_label: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    ownership_state: OwnershipLabel = OwnershipLabel.UNRESOLVED
    supporting_trace_ids: list[str] = Field(default_factory=list)
    contradicting_trace_ids: list[str] = Field(default_factory=list)
    dependency_trace_ids: list[str] = Field(default_factory=list)
    is_current: bool = True
    scope_notes: str = ""


class TrueOpportunityRelevance(StrictEvalModel):
    """Hidden graded relevance (0-3) of one opportunity-catalog entry for a case."""

    opportunity_id: str = Field(min_length=1)
    relevance_grade: int = Field(ge=0, le=3)


class TruthBundle(StrictEvalModel):
    """Complete hidden ground truth for one case.

    Never place an instance of this type, or any field extracted from it, into
    ``UnitBundle.metadata``, ``InputSnapshot``, prediction metadata, prompt metadata, or a
    filename visible to inference code (Freeze Section 9.4).
    """

    schema_version: str = SCHEMA_VERSION
    case_id: str = Field(min_length=1)
    asset_concepts: list[TrueAssetConcept] = Field(default_factory=list)
    opportunity_relevance: list[TrueOpportunityRelevance] = Field(default_factory=list)
    sensitive_trace_ids: list[str] = Field(default_factory=list)
    challenge_category: ChallengeCategory | None = None
    expected_perturbation_directions: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_identifiers(self) -> TruthBundle:
        concept_ids = [concept.concept_id for concept in self.asset_concepts]
        if len(concept_ids) != len(set(concept_ids)):
            raise ValueError("TruthBundle asset_concepts must have unique concept_id values")
        opportunity_ids = [rel.opportunity_id for rel in self.opportunity_relevance]
        if len(opportunity_ids) != len(set(opportunity_ids)):
            raise ValueError("TruthBundle opportunity_relevance must have unique opportunity_id values")
        return self
