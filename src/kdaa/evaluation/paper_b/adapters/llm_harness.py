"""Shared LLM-call harness for C1/C2/C4 (Checkpoint B Section 6: attempts, raw/parsed/
validated outputs, failures, usage).

Retains every intended attempt via the WP1 ``ExperimentAttempt``/``ResourceUsage``
contracts: at most 2 automatic retries per intended call (Freeze Section 16.6), a failed
intended run is never silently dropped or replaced, and the failure category is recorded.

Known Checkpoint B simplification: ``JSONProvider.generate_json`` (the existing production
provider protocol) already collapses raw-text parsing into its return value, so this
harness's "parsed output" is that dict and its "validated output" is the pydantic-checked
``LLMResponseSchema`` -- there is no separately retained pre-parse raw-text layer, since
the provider protocol was not extended to expose one (a live provider could be extended
later without changing this harness's contract).

Under the truth-import boundary (see ``kdaa.evaluation.paper_b.boundary``): must never
import ``kdaa.evaluation.paper_b.truth`` or ``opportunity_truth``.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from kdaa.providers.base import JSONProvider

from ..schemas import PredictionBundle
from ..telemetry import AttemptStatus, ExperimentAttempt, ResourceUsage

MAX_AUTOMATIC_RETRIES = 2


class LLMConceptSuggestion(BaseModel):
    """Minimal evaluation-neutral JSON schema for parseability only -- no KDAA design
    knowledge (ontology, provenance, epistemic states, bounded-claim rules) is encoded
    here (Freeze Section 10, C1)."""

    model_config = ConfigDict(extra="ignore")

    label: str
    ownership: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class LLMResponseSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    concepts: list[LLMConceptSuggestion]
    ranked_opportunity_ids: list[str]


@dataclass(frozen=True)
class LLMCallResult:
    status: AttemptStatus
    validated: LLMResponseSchema | None
    error_message: str
    resource_usage: ResourceUsage
    attempts_made: int


def classify_exception(exc: Exception) -> AttemptStatus:
    if isinstance(exc, httpx.TimeoutException):
        return AttemptStatus.TIMEOUT
    if isinstance(exc, httpx.HTTPError):
        return AttemptStatus.PROVIDER_ERROR
    if isinstance(exc, ValidationError):
        return AttemptStatus.SCHEMA_VALIDATION_FAILURE
    if isinstance(exc, ValueError):
        return AttemptStatus.INVALID_JSON
    return AttemptStatus.OTHER_FAILURE


def call_llm_with_retries(
    *,
    provider: JSONProvider,
    system_prompt: str,
    user_prompt: str,
    attempt_number: int,
    max_retries: int = MAX_AUTOMATIC_RETRIES,
) -> LLMCallResult:
    """One intended attempt, retried up to ``max_retries`` times on failure. Retries are
    not separate intended runs; only the final outcome (and its retry count) is recorded.
    """
    status = AttemptStatus.OTHER_FAILURE
    error_message = ""
    validated: LLMResponseSchema | None = None
    attempts_made = 0
    started = time.monotonic()

    while attempts_made <= max_retries:
        attempts_made += 1
        try:
            raw: dict[str, Any] = provider.generate_json(system=system_prompt, user=user_prompt)
            validated = LLMResponseSchema.model_validate(raw)
            status = AttemptStatus.SUCCESS
            error_message = ""
            break
        except Exception as exc:  # noqa: BLE001 -- deliberately broad, classified below
            status = classify_exception(exc)
            error_message = str(exc)
            validated = None
            continue

    latency = time.monotonic() - started
    resource_usage = ResourceUsage(
        provider="dev-provider",
        model_identifier=getattr(provider, "model_name", ""),
        attempt_number=attempt_number,
        latency_seconds=latency,
    )
    return LLMCallResult(
        status=status,
        validated=validated,
        error_message=error_message,
        resource_usage=resource_usage,
        attempts_made=attempts_made,
    )


def build_experiment_attempt(
    *,
    case_id: str,
    comparator_id: str,
    attempt_number: int,
    call_result: LLMCallResult,
    prediction: PredictionBundle | None,
) -> ExperimentAttempt:
    """Assemble the final ``ExperimentAttempt`` once the caller has (on success) built a
    ``PredictionBundle`` from ``call_result.validated`` -- the harness itself cannot do
    this, since turning validated LLM output into a ``PredictionBundle`` is
    comparator-specific (C1 vs. C2 differ in how they use ``evidence_ids``).
    """
    return ExperimentAttempt(
        attempt_id=str(uuid.uuid4()),
        case_id=case_id,
        comparator_id=comparator_id,
        attempt_number=attempt_number,
        status=call_result.status,
        prediction=prediction,
        error_message=call_result.error_message,
        resource_usage=call_result.resource_usage,
    )
