"""Execution-side telemetry: attempt outcomes and resource usage for Paper B comparator runs.

WP1 defines the contract only. No retry logic, provider integration, or model selection is
implemented here (that is WP6); the point is that every intended attempt, including every
failure mode, can already be represented without discarding it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import Field, model_validator

from .base import StrictEvalModel
from .hashing import SCHEMA_VERSION, VOLATILE_MARKER
from .schemas import PredictionBundle


def _utc_now() -> datetime:
    return datetime.now(UTC)


class AttemptStatus(str, Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    PROVIDER_ERROR = "provider_error"
    REFUSAL = "refusal"
    INVALID_JSON = "invalid_json"
    TRUNCATED = "truncated"
    PARSE_FAILURE = "parse_failure"
    SCHEMA_VALIDATION_FAILURE = "schema_validation_failure"
    OTHER_FAILURE = "other_failure"


FAILURE_STATUSES: frozenset[AttemptStatus] = frozenset(AttemptStatus) - {AttemptStatus.SUCCESS}


class ResourceUsage(StrictEvalModel):
    """Provider/token/cost telemetry for one attempt. No provider or model is chosen here."""

    schema_version: str = SCHEMA_VERSION
    provider: str = ""
    model_identifier: str = ""
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    attempt_number: int = Field(default=1, ge=1)
    latency_seconds: float | None = Field(
        default=None, ge=0.0, json_schema_extra={VOLATILE_MARKER: True}
    )
    provider_usage_metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class ExperimentAttempt(StrictEvalModel):
    """One intended run of one comparator on one case, retained regardless of outcome.

    ``status`` is the only field that determines whether ``prediction`` may be absent: a
    ``SUCCESS`` attempt must carry a prediction; every failure status may still carry a
    best-effort partial ``PredictionBundle`` (e.g. from partially parsed output) or ``None``.
    """

    schema_version: str = SCHEMA_VERSION
    attempt_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    comparator_id: str = Field(min_length=1)
    attempt_number: int = Field(ge=1)
    status: AttemptStatus
    prediction: PredictionBundle | None = None
    error_message: str = ""
    raw_output_ref: str | None = None
    resource_usage: ResourceUsage | None = None
    started_at: datetime = Field(default_factory=_utc_now, json_schema_extra={VOLATILE_MARKER: True})
    completed_at: datetime | None = Field(
        default=None, json_schema_extra={VOLATILE_MARKER: True}
    )

    @model_validator(mode="after")
    def success_requires_prediction(self) -> ExperimentAttempt:
        if self.status == AttemptStatus.SUCCESS and self.prediction is None:
            raise ValueError("A successful ExperimentAttempt must include a prediction bundle")
        return self
