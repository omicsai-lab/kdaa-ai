import httpx
import pytest
from pydantic import ValidationError

from kdaa.evaluation.paper_b.adapters.fake_provider import FakeJSONProvider
from kdaa.evaluation.paper_b.adapters.llm_harness import (
    MAX_AUTOMATIC_RETRIES,
    call_llm_with_retries,
    classify_exception,
)
from kdaa.evaluation.paper_b.telemetry import AttemptStatus

_VALID_RESPONSE = {"concepts": [{"label": "X"}], "ranked_opportunity_ids": ["a", "b"]}


def test_successful_call_returns_validated_schema() -> None:
    provider = FakeJSONProvider([_VALID_RESPONSE])
    result = call_llm_with_retries(provider=provider, system_prompt="s", user_prompt="u", attempt_number=1)
    assert result.status == AttemptStatus.SUCCESS
    assert result.validated is not None
    assert result.validated.concepts[0].label == "X"
    assert result.attempts_made == 1


def test_retry_then_succeed_is_recorded_as_success_with_correct_retry_count() -> None:
    provider = FakeJSONProvider([httpx.TimeoutException("slow"), _VALID_RESPONSE])
    result = call_llm_with_retries(provider=provider, system_prompt="s", user_prompt="u", attempt_number=1)
    assert result.status == AttemptStatus.SUCCESS
    assert result.attempts_made == 2
    assert provider.call_count == 2


def test_exhausted_retries_is_recorded_as_failure_not_dropped() -> None:
    provider = FakeJSONProvider([ValueError("bad"), ValueError("bad"), ValueError("bad")])
    result = call_llm_with_retries(
        provider=provider, system_prompt="s", user_prompt="u", attempt_number=1, max_retries=2
    )
    assert result.status == AttemptStatus.INVALID_JSON
    assert result.validated is None
    # 1 initial + 2 retries = 3 calls; MAX_AUTOMATIC_RETRIES matches the Freeze cap.
    assert result.attempts_made == 3
    assert MAX_AUTOMATIC_RETRIES == 2


def test_max_two_automatic_retries_is_enforced_by_default() -> None:
    provider = FakeJSONProvider([ValueError("bad")] * 10)
    result = call_llm_with_retries(provider=provider, system_prompt="s", user_prompt="u", attempt_number=1)
    assert result.attempts_made == 1 + MAX_AUTOMATIC_RETRIES
    assert provider.call_count == 1 + MAX_AUTOMATIC_RETRIES


@pytest.mark.parametrize(
    "exception,expected_status",
    [
        (httpx.TimeoutException("t"), AttemptStatus.TIMEOUT),
        (httpx.ConnectError("c"), AttemptStatus.PROVIDER_ERROR),
        (ValueError("bad json"), AttemptStatus.INVALID_JSON),
        (RuntimeError("weird"), AttemptStatus.OTHER_FAILURE),
    ],
)
def test_classify_exception_maps_to_expected_status(exception, expected_status) -> None:
    assert classify_exception(exception) == expected_status


def test_validation_error_from_malformed_response_is_schema_validation_failure() -> None:
    provider = FakeJSONProvider([{"not_the_right_shape": True}])
    result = call_llm_with_retries(provider=provider, system_prompt="s", user_prompt="u", attempt_number=1)
    assert result.status == AttemptStatus.SCHEMA_VALIDATION_FAILURE


def test_classify_exception_direct_validation_error() -> None:
    from kdaa.evaluation.paper_b.adapters.llm_harness import LLMResponseSchema

    try:
        LLMResponseSchema.model_validate({})
    except ValidationError as exc:
        assert classify_exception(exc) == AttemptStatus.SCHEMA_VALIDATION_FAILURE
    else:
        raise AssertionError("expected ValidationError")


def test_resource_usage_records_latency_and_model_identifier() -> None:
    provider = FakeJSONProvider([_VALID_RESPONSE], model_name="my-fake-model")
    result = call_llm_with_retries(provider=provider, system_prompt="s", user_prompt="u", attempt_number=1)
    assert result.resource_usage.model_identifier == "my-fake-model"
    assert result.resource_usage.latency_seconds is not None
    assert result.resource_usage.latency_seconds >= 0.0
