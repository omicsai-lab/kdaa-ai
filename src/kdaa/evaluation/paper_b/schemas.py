"""Evaluation-neutral, inference-visible Paper B contracts.

Every type in this module is safe for inference/comparator code to import: nothing here
carries hidden ground truth. Truth-only content (hidden asset concepts, ownership grades,
opportunity relevance) lives in ``kdaa.evaluation.paper_b.truth`` and must never be imported
by this module or by any future inference/adapter namespace -- see ``boundary.py``.

``PredictionBundle``, ``PredictedClaim``, and ``PredictedOpportunity`` deliberately do not
subclass or reuse production ``kdaa.models.AssetRecord`` validators. They must be able to
represent generic baselines with no provenance, malformed or partially valid output,
abstention (an empty ``claims`` list), and evaluation-only unsafe stress variants (future
A1/A9) -- none of which a strict production asset record can express. Field-count limits
implied by the frozen fairness rule (at most 10 candidates, exactly 10 ranked opportunities)
are deliberately *not* enforced here: WP7's A8 ("unconstrained recombination") ablation must
be able to represent candidate explosion beyond that limit for diagnostic purposes, so the
cap belongs in a WP4 fairness validator that inspects a bundle, not in the data model itself.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import ConfigDict, Field, model_validator

from .base import StrictEvalModel
from .hashing import SCHEMA_VERSION


class OwnershipLabel(str, Enum):
    """Evaluation-neutral ownership field shared by every comparator (PC-03)."""

    FOCAL_UNIT = "focal_unit"
    SHARED = "shared"
    ORGANIZATIONAL = "organizational"
    EXTERNAL = "external"
    UNRESOLVED = "unresolved"


class ExperimentUnitType(str, Enum):
    INDIVIDUAL_RESEARCHER = "individual_researcher"
    TEAM = "team"
    LABORATORY = "laboratory"


class EvidenceDensity(str, Enum):
    SPARSE = "sparse"
    DENSE = "dense"


class DomainBreadth(str, Enum):
    SINGLE_DOMAIN = "single_domain"
    INTERDISCIPLINARY = "interdisciplinary"


class AttributionRegime(str, Enum):
    CLEAR_INDIVIDUAL = "clear_individual"
    SHARED_COLLECTIVE = "shared_collective"
    UNKNOWN_AMBIGUOUS = "unknown_ambiguous"


class ChallengeCategory(str, Enum):
    """The ten frozen challenge categories (experiment_lock.yaml: data.final_synthetic.challenge_categories)."""

    ONTOLOGY_SHIFT_AND_UNSEEN_SYNONYMS = "ontology_shift_and_unseen_synonyms"
    INTERDISCIPLINARY_COMPOSITE_ASSETS = "interdisciplinary_composite_assets"
    TRACE_AS_ASSET_AND_PRESTIGE_DECOYS = "trace_as_asset_and_prestige_decoys"
    SEMANTIC_DUPLICATES_AND_SOURCE_DEPENDENCE = "semantic_duplicates_and_source_dependence"
    STALE_CURRENT_CONFLICT_AND_CONTRADICTION = "stale_current_conflict_and_contradiction"
    COLLABORATOR_HEAVY_AND_UNKNOWN_ROLES = "collaborator_heavy_and_unknown_roles"
    IDENTITY_COLLISION_AND_RESOLUTION_ERROR = "identity_collision_and_resolution_error"
    SPARSE_AND_MISSING_SUPPORT = "sparse_and_missing_support"
    IRRELEVANT_NOISE_AND_SENSITIVE_TRACES = "irrelevant_noise_and_sensitive_traces"
    OPPORTUNITY_CONTEXT_REVERSAL_AND_UNSAFE_DELEGATION = (
        "opportunity_context_reversal_and_unsafe_delegation"
    )


class CaseManifest(StrictEvalModel):
    """Descriptive, inference-safe metadata identifying a case's experimental design cell.

    Unlike ``TruthBundle``, this does not carry hidden ground truth -- only the factorial
    design coordinates a case was constructed from, which the frozen protocol treats as
    prespecified experimental structure rather than a scoring secret.
    """

    schema_version: str = SCHEMA_VERSION
    case_id: str = Field(min_length=1)
    is_challenge_case: bool = False
    challenge_category: ChallengeCategory | None = None
    unit_type: ExperimentUnitType
    evidence_density: EvidenceDensity
    domain_breadth: DomainBreadth
    attribution_regime: AttributionRegime
    seed: int | None = None
    development_case: bool = True
    notes: str = ""

    @model_validator(mode="after")
    def challenge_category_matches_flag(self) -> CaseManifest:
        if self.is_challenge_case and self.challenge_category is None:
            raise ValueError("A challenge case must declare its challenge_category")
        if not self.is_challenge_case and self.challenge_category is not None:
            raise ValueError("A core (non-challenge) case must not declare a challenge_category")
        return self


class OpportunityCandidate(StrictEvalModel):
    """One entry in the common, fixed opportunity catalog shared by every comparator."""

    model_config = ConfigDict(frozen=True)

    opportunity_id: str = Field(min_length=1)
    title: str = ""
    description: str = ""


class EvidenceSnapshotTrace(StrictEvalModel):
    """One normalized evidence trace as presented identically to every comparator."""

    model_config = ConfigDict(frozen=True)

    trace_id: str = Field(min_length=1)
    order_index: int = Field(ge=0)
    trace_type: str = ""
    normalized_text: str = ""
    sensitive: bool = False


class InputSnapshot(StrictEvalModel):
    """The immutable, fairness-locked input every comparator receives for one case.

    Immutability is real, not superficial: pydantic's ``frozen=True`` only blocks attribute
    *reassignment* (``snapshot.traces = other``), not in-place mutation of a mutable field
    value, so both collection fields use ``tuple`` rather than ``list``. Combined with
    ``EvidenceSnapshotTrace``/``OpportunityCandidate`` also being frozen, no part of a
    constructed ``InputSnapshot`` can be altered after the fact.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = SCHEMA_VERSION
    case_id: str = Field(min_length=1)
    traces: tuple[EvidenceSnapshotTrace, ...] = ()
    opportunity_catalog: tuple[OpportunityCandidate, ...] = ()

    @model_validator(mode="after")
    def fixed_order_and_unique_ids(self) -> InputSnapshot:
        indices = [trace.order_index for trace in self.traces]
        if indices != sorted(indices) or len(set(indices)) != len(indices):
            raise ValueError(
                "InputSnapshot traces must have unique, already-sorted order_index values"
            )
        trace_ids = [trace.trace_id for trace in self.traces]
        if len(trace_ids) != len(set(trace_ids)):
            raise ValueError("InputSnapshot trace_id values must be unique")
        opportunity_ids = [candidate.opportunity_id for candidate in self.opportunity_catalog]
        if len(opportunity_ids) != len(set(opportunity_ids)):
            raise ValueError("InputSnapshot opportunity_id values must be unique")
        return self


class PredictedClaim(StrictEvalModel):
    """One evaluation-neutral candidate capability/asset claim from any comparator.

    Every field beyond ``claim_id`` is optional-with-default so that malformed or minimal
    baseline output (e.g. a bare label with no citations) remains representable rather than
    rejected outright; adapters may set ``raw_text`` for content that could not be parsed
    further.
    """

    claim_id: str = Field(min_length=1)
    label: str = ""
    bounded_claim: str = ""
    cited_trace_ids: list[str] = Field(default_factory=list)
    ownership: OwnershipLabel = OwnershipLabel.UNRESOLVED
    raw_text: str = ""


class PredictedOpportunity(StrictEvalModel):
    """One ranked opportunity from the common catalog, as ranked by a comparator."""

    opportunity_id: str = Field(min_length=1)
    rank: int = Field(ge=1)
    supporting_claim_ids: list[str] = Field(default_factory=list)
    rationale: str = ""


class PredictionBundle(StrictEvalModel):
    """A single comparator's complete, evaluation-neutral output for one attempt.

    ``claims=[]`` represents abstention. ``is_valid_output=False`` plus ``validation_notes``
    preserves a malformed/unparseable attempt without inventing content to make it valid.
    """

    schema_version: str = SCHEMA_VERSION
    case_id: str = Field(min_length=1)
    comparator_id: str = Field(min_length=1)
    attempt_number: int = Field(default=1, ge=1)
    claims: list[PredictedClaim] = Field(default_factory=list)
    ranked_opportunities: list[PredictedOpportunity] = Field(default_factory=list)
    is_valid_output: bool = True
    validation_notes: list[str] = Field(default_factory=list)
    raw_output_ref: str | None = None

    @model_validator(mode="after")
    def unique_identifiers(self) -> PredictionBundle:
        claim_ids = [claim.claim_id for claim in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("PredictionBundle claim_id values must be unique")
        ranks = [opportunity.rank for opportunity in self.ranked_opportunities]
        if len(ranks) != len(set(ranks)):
            raise ValueError("PredictionBundle ranked_opportunities must have unique rank values")
        return self


class ModelLock(StrictEvalModel):
    """Prospective model lock. WP1 defines the contract only; no model is chosen here."""

    schema_version: str = SCHEMA_VERSION
    locked: bool = False
    provider: str = ""
    model_identifier: str = ""
    snapshot_or_revision: str = ""
    decoding_settings: dict[str, Any] = Field(default_factory=dict)
    context_window_tokens: int | None = Field(default=None, ge=0)
    max_output_tokens: int | None = Field(default=None, ge=0)
    notes: str = ""


class PromptLock(StrictEvalModel):
    """Prospective prompt/schema lock. Populated by WP6 once prompts exist."""

    schema_version: str = SCHEMA_VERSION
    locked: bool = False
    prompt_id: str = ""
    prompt_version: str = ""
    prompt_hash: str = ""
    schema_hash: str = ""
    notes: str = ""


class ScorerLock(StrictEvalModel):
    """Prospective scorer lock. Thresholds are chosen at the WP11 development pilot."""

    schema_version: str = SCHEMA_VERSION
    locked: bool = False
    matching_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    embedding_model_for_matching: str = ""
    notes: str = ""
