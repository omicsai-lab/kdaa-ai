"""Paper B (KBS) evaluation-layer contracts.

This namespace implements WP1 only: experiment configuration, canonical hashing, artifact
lineage, evaluation-neutral prediction/attempt/telemetry records, and a minimal experiment
registry. It does not implement generators, comparators, scoring, or LLM providers -- those
are later work packages (WP2 onward). See ``docs/paper_b_kbs_claims_evaluation_freeze.md``
and ``configs/paper_b/experiment_lock.yaml`` for the frozen scientific specification this
namespace implements against.

Truth-side content (``kdaa.evaluation.paper_b.truth``) is intentionally not re-exported
here: importing this package must not make truth-side types trivially reachable from
inference code. Import ``kdaa.evaluation.paper_b.truth`` explicitly, and only from
truth-authorized tooling (case generation, scoring). See ``boundary.py``.
"""

from __future__ import annotations

from .artifacts import ArtifactIndex, ArtifactLineageError, ArtifactRecord, ArtifactType
from .config import ExperimentLock, load_experiment_lock
from .hashing import SCHEMA_VERSION, canonical_json_bytes, canonical_payload, content_hash
from .registry import ExperimentRegistry, RegistryState, RegistryTransitionError
from .schemas import (
    AttributionRegime,
    CaseManifest,
    ChallengeCategory,
    DomainBreadth,
    EvidenceDensity,
    EvidenceSnapshotTrace,
    ExperimentUnitType,
    InputSnapshot,
    ModelLock,
    OpportunityCandidate,
    OwnershipLabel,
    PredictedClaim,
    PredictedOpportunity,
    PredictionBundle,
    PromptLock,
    ScorerLock,
)
from .telemetry import AttemptStatus, ExperimentAttempt, ResourceUsage

__all__ = [
    "SCHEMA_VERSION",
    "ArtifactIndex",
    "ArtifactLineageError",
    "ArtifactRecord",
    "ArtifactType",
    "AttemptStatus",
    "AttributionRegime",
    "CaseManifest",
    "ChallengeCategory",
    "DomainBreadth",
    "EvidenceDensity",
    "EvidenceSnapshotTrace",
    "ExperimentAttempt",
    "ExperimentLock",
    "ExperimentRegistry",
    "ExperimentUnitType",
    "InputSnapshot",
    "ModelLock",
    "OpportunityCandidate",
    "OwnershipLabel",
    "PredictedClaim",
    "PredictedOpportunity",
    "PredictionBundle",
    "PromptLock",
    "RegistryState",
    "RegistryTransitionError",
    "ResourceUsage",
    "ScorerLock",
    "canonical_json_bytes",
    "canonical_payload",
    "content_hash",
    "load_experiment_lock",
]
