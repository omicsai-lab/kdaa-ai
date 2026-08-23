"""Core domain models for KDAA-AI.

The models intentionally preserve the distinction made in the theory paper:
observable traces are not assets; system outputs are falsifiable asset hypotheses;
and a hypothesis does not become a confirmed knowledge asset without calibration.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class UnitType(str, Enum):
    RESEARCHER = "researcher"
    TEAM = "team"
    LAB = "laboratory"
    DEPARTMENT = "department"
    FIRM = "firm"
    NONPROFIT = "nonprofit"
    PUBLIC_INSTITUTION = "public_institution"
    OTHER = "other"


class TraceType(str, Enum):
    PUBLICATION = "publication"
    SOFTWARE = "software_repository"
    DATASET = "dataset"
    GRANT = "grant"
    PROJECT = "project"
    PROTOCOL = "protocol"
    COURSE = "course"
    TALK = "talk"
    PATENT = "patent"
    EMPLOYMENT = "employment"
    AWARD = "award"
    COLLABORATION = "collaboration"
    DOCUMENT = "document"
    OUTCOME = "outcome"
    OTHER = "other"


class SourceKind(str, Enum):
    OPENALEX = "openalex"
    ORCID = "orcid"
    GITHUB = "github"
    CV = "cv"
    LOCAL_FILE = "local_file"
    MANUAL = "manual"
    SYNTHETIC = "synthetic"
    OTHER = "other"


class ContributionRole(str, Enum):
    ORIGINATOR = "originator"
    LEAD = "lead"
    IMPLEMENTER = "implementer"
    SUPERVISOR = "supervisor"
    ADVISOR = "advisor"
    CONTRIBUTOR = "contributor"
    PARTICIPANT = "participant"
    UNKNOWN = "unknown"


class OwnershipState(str, Enum):
    """Typed, evaluation-neutral ownership state for an asset hypothesis.

    Trace-level ``ContributionRole`` is evidence that may inform ownership; it is not
    ownership itself, and the two remain independent fields (see ``AssetRecord``). Values
    are chosen to match ``kdaa.evaluation.paper_b.OwnershipLabel`` (WP1, protocol
    clarification PC-03) so a later adapter can map by value with no semantic translation;
    see ``test_ownership_state_matches_paper_b_ownership_label_value_set`` in
    ``tests/test_models.py``. This module must not import ``kdaa.evaluation.paper_b`` --
    the dependency direction runs the other way (evaluation/adapters may import production).
    """

    FOCAL_UNIT = "focal_unit"
    SHARED = "shared"
    ORGANIZATIONAL = "organizational"
    EXTERNAL = "external"
    UNRESOLVED = "unresolved"


_LEGACY_OWNERSHIP_TOKENS = frozenset(member.value for member in OwnershipState)


class TraceRelationType(str, Enum):
    EXACT_DUPLICATE = "exact_duplicate"
    SOURCE_RECORD_EQUIVALENT = "source_record_equivalent"
    DERIVATIVE = "derivative"
    SEMANTIC_NEAR_DUPLICATE = "semantic_near_duplicate"
    CONTRADICTS = "contradicts"
    CONTEXTUALIZES = "contextualizes"
    INDEPENDENT_SUPPORT = "independent_support"
    OTHER = "other"


class AssetCategory(str, Enum):
    CODIFIED = "codified"
    TACIT_PROCEDURAL = "tacit_procedural"
    RELATIONAL = "relational"
    COMBINATIVE_EXECUTION = "combinative_execution"
    BUNDLE = "bundle"


class AssetState(str, Enum):
    HYPOTHESIS = "hypothesis"
    PROVISIONAL = "provisional"
    CONFIRMED = "confirmed"
    NARROWED = "narrowed"
    SPLIT = "split"
    REJECTED = "rejected"
    RETIRED = "retired"


class EvidenceRole(str, Enum):
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    CONTEXT = "context"
    MISSING = "missing"


class OutputContainer(str, Enum):
    REPOSITORY = "repository"
    LIVING_DOCUMENT = "living_document"
    KNOWLEDGE_BASE = "structured_knowledge_base"
    DEPLOYABLE_PRODUCT = "deployable_product"
    PUBLIC_CONTENT = "public_content"


class ValuePathway(str, Enum):
    JOURNAL_PAPER = "journal_paper"
    CONFERENCE_OUTPUT = "conference_output"
    GRANT = "grant"
    SOFTWARE = "software"
    DATA_RESOURCE = "data_resource"
    COURSE = "course"
    BOOK = "book"
    CONSULTING = "consulting"
    INTERNAL_CAPABILITY = "internal_capability"
    PUBLIC_ENGAGEMENT = "public_engagement"
    OTHER = "other"


class FocalUnit(StrictModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    unit_type: UnitType
    description: str = ""
    institution: str | None = None
    homepage: str | None = None
    identifiers: dict[str, str] = Field(default_factory=dict)
    members: list[str] = Field(default_factory=list)
    boundary_notes: str = ""
    governance_notes: str = ""
    is_synthetic: bool = False


class StrategicGoal(StrictModel):
    id: str
    label: str
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    weight: float = Field(default=1.0, ge=0.0, le=5.0)
    horizon_months: int | None = Field(default=None, ge=1)


class EvidenceTrace(StrictModel):
    id: str = Field(min_length=1)
    unit_id: str = Field(min_length=1)
    trace_type: TraceType
    title: str = Field(min_length=1)
    description: str = ""
    abstract: str = ""
    content: str = ""
    source_kind: SourceKind = SourceKind.MANUAL
    source_name: str = ""
    source_uri: str | None = None
    source_record_id: str | None = None
    observed_at: datetime = Field(default_factory=utc_now)
    event_date: date | None = None
    authors_or_contributors: list[str] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    contribution_role: ContributionRole = ContributionRole.UNKNOWN
    outcome_signals: dict[str, float | int | str | bool] = Field(default_factory=dict)
    related_trace_ids: list[str] = Field(default_factory=list)
    sensitive: bool = False
    license: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("keywords", "topics", "authors_or_contributors", "affiliations")
    @classmethod
    def strip_list_values(cls, values: list[str]) -> list[str]:
        return [v.strip() for v in values if isinstance(v, str) and v.strip()]

    @property
    def searchable_text(self) -> str:
        parts = [
            self.title,
            self.description,
            self.abstract,
            self.content,
            " ".join(self.keywords),
            " ".join(self.topics),
        ]
        return "\n".join(part for part in parts if part).strip()


class EvidenceLink(StrictModel):
    trace_id: str
    role: EvidenceRole = EvidenceRole.SUPPORTING
    relation: str = "supports"
    rationale: str = ""
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class TraceRelation(StrictModel):
    """A typed relationship between two evidence traces within the same bundle.

    WP2 provides this representation plus exact/source-record-equivalence detection only
    (see ``kdaa.ingestion.dedup``). Semantic near-duplicate, derivative, contradiction, and
    independent-support detection are represented here but not automatically populated
    until later work packages implement that policy.
    """

    id: str = Field(min_length=1)
    source_trace_id: str = Field(min_length=1)
    target_trace_id: str = Field(min_length=1)
    relation_type: TraceRelationType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: str = ""
    detection_method: str = "unspecified"

    @model_validator(mode="after")
    def source_and_target_differ(self) -> TraceRelation:
        if self.source_trace_id == self.target_trace_id:
            raise ValueError("TraceRelation source_trace_id and target_trace_id must differ")
        return self


class ScoreDimension(StrictModel):
    value: float = Field(ge=0.0, le=1.0)
    method: str
    rationale: str = ""
    uncertainty: float = Field(default=0.0, ge=0.0, le=1.0)
    is_proxy: bool = True


class AssetAssessment(StrictModel):
    evidence_strength: ScoreDimension
    attribution_confidence: ScoreDimension
    maturity: ScoreDimension
    distinctiveness: ScoreDimension
    tacitness: ScoreDimension
    transferability: ScoreDimension
    dependency_intensity: ScoreDimension
    decay_risk: ScoreDimension
    appropriability_risk: ScoreDimension
    ai_interfaceability: ScoreDimension
    privacy_risk: ScoreDimension
    overall_credibility: ScoreDimension
    assessed_at: datetime = Field(default_factory=utc_now)
    scoring_version: str = "0.1.0"


class AssetRecord(StrictModel):
    id: str
    version: int = Field(default=1, ge=1)
    unit_id: str
    label: str
    bounded_claim: str
    enables: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    categories: list[AssetCategory]
    concept_tags: list[str] = Field(default_factory=list)
    evidence_links: list[EvidenceLink]
    alternative_explanations: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    # Deprecated legacy free-text display field. Not authoritative for Paper B scoring or
    # dependency calculations; use `ownership_state` instead. Retained only so pre-WP2
    # serialized records continue to load and display.
    hypothesized_owner: str = "focal_unit"
    ownership_state: OwnershipState = OwnershipState.UNRESOLVED
    ownership_rationale: str = ""
    attribution_trace_ids: list[str] = Field(default_factory=list)
    attributed_contributors: list[str] = Field(default_factory=list)
    epistemic_state: AssetState = AssetState.HYPOTHESIS
    discovery_method: str = "deterministic"
    discovery_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    assessment: AssetAssessment | None = None
    human_calibration_required: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    parent_asset_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _migrate_ownership_state(cls, data: Any) -> Any:
        """Deterministic legacy migration (WP2 requirement A3).

        If ``ownership_state`` is already present (and not None) in the input, it is
        authoritative and this validator does nothing. Otherwise, if the legacy
        ``hypothesized_owner`` field is present and its value is *exactly* one of the five
        recognized typed tokens, that token is mapped across. Any other case -- an arbitrary
        person/unit/institution/repository-owner display name, or both fields simply absent
        -- is left unset, so the field default (``UNRESOLVED``) applies. This never infers
        ``FOCAL_UNIT`` merely because a record belongs to a focal-unit analysis.
        """
        if not isinstance(data, dict) or data.get("ownership_state") is not None:
            return data
        legacy_value = data.get("hypothesized_owner")
        if isinstance(legacy_value, str) and legacy_value in _LEGACY_OWNERSHIP_TOKENS:
            data = dict(data)
            data["ownership_state"] = OwnershipState(legacy_value)
        return data

    @model_validator(mode="after")
    def hypothesis_requires_evidence(self) -> AssetRecord:
        if (
            self.epistemic_state not in {AssetState.REJECTED, AssetState.RETIRED}
            and not any(link.role == EvidenceRole.SUPPORTING for link in self.evidence_links)
        ):
            raise ValueError("An active asset record must have at least one supporting trace")
        return self


class GainVector(StrictModel):
    time: float = Field(default=0.0, ge=-1.0, le=1.0)
    quality: float = Field(default=0.0, ge=-1.0, le=1.0)
    scale: float = Field(default=0.0, ge=-1.0, le=1.0)
    accessibility: float = Field(default=0.0, ge=-1.0, le=1.0)
    reuse: float = Field(default=0.0, ge=-1.0, le=1.0)
    recombination: float = Field(default=0.0, ge=-1.0, le=1.0)
    execution_span: float = Field(default=0.0, ge=-1.0, le=1.0)
    learning: float = Field(default=0.0, ge=-1.0, le=1.0)
    cost: float = Field(default=0.0, ge=-1.0, le=1.0)
    risk: float = Field(default=0.0, ge=-1.0, le=1.0)


class AmplificationOpportunity(StrictModel):
    id: str
    unit_id: str
    title: str
    problem: str
    beneficiary: str
    output_container: OutputContainer
    value_pathways: list[ValuePathway]
    asset_ids: list[str]
    complementary_asset_ids: list[str] = Field(default_factory=list)
    rationale: str
    ai_tasks: list[str]
    human_tasks: list[str]
    verification_gates: list[str]
    credible_baseline: str
    expected_gain: GainVector
    fit_score: float = Field(ge=0.0, le=1.0)
    amplifiability_score: float = Field(ge=0.0, le=1.0)
    readiness_score: float = Field(ge=0.0, le=1.0)
    governance_risk: float = Field(ge=0.0, le=1.0)
    priority_score: float = Field(ge=0.0, le=1.0)
    estimated_effort: Literal["small", "medium", "large"] = "medium"
    time_horizon: str = ""
    dependencies: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class CalibrationAction(str, Enum):
    CONFIRM = "confirm"
    NARROW = "narrow"
    SPLIT = "split"
    MERGE = "merge"
    REJECT = "reject"
    DEFER = "defer"


class CalibrationRecord(StrictModel):
    id: str
    run_id: str
    asset_id: str
    action: CalibrationAction
    reviewer_role: str = "focal_unit_representative"
    reviewer_id: str | None = None
    notes: str = ""
    revised_claim: str | None = None
    revised_categories: list[AssetCategory] | None = None
    additional_supporting_trace_ids: list[str] = Field(default_factory=list)
    missing_or_contradicting_evidence: list[str] = Field(default_factory=list)
    calibrated_at: datetime = Field(default_factory=utc_now)


class OutcomeRecord(StrictModel):
    id: str
    run_id: str
    opportunity_id: str
    baseline_description: str
    intervention_description: str
    observed_gain: GainVector
    quality_notes: str = ""
    attribution_notes: str = ""
    realized_value: dict[str, float | int | str | bool] = Field(default_factory=dict)
    captured_value: dict[str, float | int | str | bool] = Field(default_factory=dict)
    causal_caveats: list[str] = Field(default_factory=list)
    observed_at: datetime = Field(default_factory=utc_now)


class UnitBundle(StrictModel):
    unit: FocalUnit
    goals: list[StrategicGoal] = Field(default_factory=list)
    traces: list[EvidenceTrace]
    # Backward-compatible: absent in pre-WP2 bundles, defaults to empty. Legacy
    # `EvidenceTrace.related_trace_ids` is preserved separately and is not automatically
    # converted into typed relations here (see kdaa.ingestion.dedup for what WP2 does
    # populate: typed exact/source-record-equivalent relations from deduplication).
    trace_relations: list[TraceRelation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def all_traces_belong_to_unit(self) -> UnitBundle:
        wrong = [trace.id for trace in self.traces if trace.unit_id != self.unit.id]
        if wrong:
            raise ValueError(f"Trace unit_id mismatch for: {wrong}")
        ids = [trace.id for trace in self.traces]
        if len(ids) != len(set(ids)):
            raise ValueError("Trace IDs must be unique within a bundle")
        return self

    @model_validator(mode="after")
    def trace_relations_are_well_formed(self) -> UnitBundle:
        relation_ids = [relation.id for relation in self.trace_relations]
        if len(relation_ids) != len(set(relation_ids)):
            raise ValueError("Trace relation IDs must be unique within a bundle")
        trace_ids = {trace.id for trace in self.traces}
        unknown = [
            relation.id
            for relation in self.trace_relations
            if relation.source_trace_id not in trace_ids or relation.target_trace_id not in trace_ids
        ]
        if unknown:
            raise ValueError(f"Trace relations reference unknown trace IDs: {unknown}")
        return self


class RunManifest(StrictModel):
    run_id: str
    created_at: datetime = Field(default_factory=utc_now)
    kdaa_version: str = "0.1.0"
    config_digest: str
    input_digest: str
    random_seed: int = 42
    mode: Literal["deterministic", "hybrid", "llm"] = "deterministic"
    llm_model: str | None = None
    # Backward-compatible: absent in pre-WP2 manifests. The resolved as_of_date every
    # recency-dependent calculation in this run actually used (explicit config value, or
    # the convenience current-date fallback -- see kdaa.pipeline.KDAAPipeline.analyze).
    analysis_as_of_date: date | None = None
    notes: list[str] = Field(default_factory=list)


class AnalysisRun(StrictModel):
    manifest: RunManifest
    unit: FocalUnit
    goals: list[StrategicGoal]
    traces: list[EvidenceTrace]
    assets: list[AssetRecord]
    opportunities: list[AmplificationOpportunity]
    graph_summary: dict[str, int | float | str]
    calibration_records: list[CalibrationRecord] = Field(default_factory=list)
    outcome_records: list[OutcomeRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def confirmed_assets(self) -> list[AssetRecord]:
        return [a for a in self.assets if a.epistemic_state == AssetState.CONFIRMED]

    @property
    def provisional_assets(self) -> list[AssetRecord]:
        return [
            a
            for a in self.assets
            if a.epistemic_state in {AssetState.HYPOTHESIS, AssetState.PROVISIONAL}
        ]
