import time

import pytest
from pydantic import ValidationError

from kdaa.evaluation.paper_b import (
    ArtifactIndex,
    ArtifactLineageError,
    ArtifactRecord,
    ArtifactType,
    AttemptStatus,
    ExperimentAttempt,
    PredictedClaim,
    PredictionBundle,
    ResourceUsage,
    content_hash,
)


def test_content_hash_is_stable_for_identical_content() -> None:
    a = PredictionBundle(case_id="c1", comparator_id="C0-S", claims=[PredictedClaim(claim_id="k1")])
    b = PredictionBundle(case_id="c1", comparator_id="C0-S", claims=[PredictedClaim(claim_id="k1")])
    assert content_hash(a) == content_hash(b)


def test_content_hash_differs_for_different_content() -> None:
    a = PredictionBundle(case_id="c1", comparator_id="C0-S", claims=[PredictedClaim(claim_id="k1")])
    b = PredictionBundle(case_id="c1", comparator_id="C0-S", claims=[PredictedClaim(claim_id="k2")])
    assert content_hash(a) != content_hash(b)


def test_canonical_hash_excludes_volatile_metadata() -> None:
    prediction = PredictionBundle(case_id="c1", comparator_id="C0-S")
    attempt_a = ExperimentAttempt(
        attempt_id="a1",
        case_id="c1",
        comparator_id="C0-S",
        attempt_number=1,
        status=AttemptStatus.SUCCESS,
        prediction=prediction,
        resource_usage=ResourceUsage(latency_seconds=1.23),
    )
    time.sleep(0.01)
    attempt_b = ExperimentAttempt(
        attempt_id="a1",
        case_id="c1",
        comparator_id="C0-S",
        attempt_number=1,
        status=AttemptStatus.SUCCESS,
        prediction=prediction,
        resource_usage=ResourceUsage(latency_seconds=9.87),
    )
    assert attempt_a.started_at != attempt_b.started_at
    assert attempt_a.resource_usage.latency_seconds != attempt_b.resource_usage.latency_seconds
    assert content_hash(attempt_a) == content_hash(attempt_b)


def test_resource_usage_round_trip() -> None:
    usage = ResourceUsage(
        provider="fake-provider",
        model_identifier="fake-model-0",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        estimated_cost_usd=0.01,
        attempt_number=2,
        latency_seconds=0.5,
        provider_usage_metadata={"finish_reason": "stop"},
    )
    restored = ResourceUsage.model_validate_json(usage.model_dump_json())
    assert restored == usage


def test_artifact_record_requires_parent_unless_raw() -> None:
    with pytest.raises(ValidationError):
        ArtifactRecord(
            artifact_type=ArtifactType.PARSED,
            content_hash="deadbeef",
            producer="parser",
            producer_version="0.1",
        )
    with pytest.raises(ValidationError):
        ArtifactRecord(
            artifact_type=ArtifactType.RAW,
            content_hash="deadbeef",
            producer="ingest",
            producer_version="0.1",
            parent_ids=("some-parent-id",),
        )


def test_raw_parsed_validated_lineage_chain() -> None:
    index = ArtifactIndex(experiment_id="exp-1")

    raw_payload = {"text": "hello world"}
    raw = ArtifactRecord.for_payload(
        raw_payload, artifact_type=ArtifactType.RAW, producer="ingest", producer_version="0.1"
    )
    index.add(raw)

    parsed_payload = {"text": "hello world", "tokens": ["hello", "world"]}
    parsed = ArtifactRecord.for_payload(
        parsed_payload,
        artifact_type=ArtifactType.PARSED,
        producer="parser",
        producer_version="0.1",
        parent_ids=[raw.artifact_id],
    )
    index.add(parsed)

    validated_payload = {**parsed_payload, "valid": True}
    validated = ArtifactRecord.for_payload(
        validated_payload,
        artifact_type=ArtifactType.VALIDATED,
        producer="validator",
        producer_version="0.1",
        parent_ids=[parsed.artifact_id],
    )
    index.add(validated)

    chain = index.lineage(validated.artifact_id)
    assert [record.artifact_type for record in chain] == [
        ArtifactType.VALIDATED,
        ArtifactType.PARSED,
        ArtifactType.RAW,
    ]
    assert index.by_type(ArtifactType.RAW) == [raw]


def test_artifact_index_rejects_unknown_parent_id() -> None:
    index = ArtifactIndex(experiment_id="exp-1")
    orphan = ArtifactRecord.for_payload(
        {"x": 1},
        artifact_type=ArtifactType.PARSED,
        producer="parser",
        producer_version="0.1",
        parent_ids=["does-not-exist"],
    )
    with pytest.raises(ArtifactLineageError):
        index.add(orphan)


def test_artifact_index_reregistering_same_occurrence_is_a_no_op() -> None:
    index = ArtifactIndex(experiment_id="exp-1")
    record = ArtifactRecord.for_payload(
        {"x": 1},
        artifact_type=ArtifactType.RAW,
        producer="ingest",
        producer_version="0.1",
        artifact_id="occurrence-1",
    )
    stored_first = index.add(record)
    stored_second = index.add(record.model_copy())
    assert stored_first.artifact_id == stored_second.artifact_id
    assert len(index.records) == 1


def test_same_artifact_id_with_contradictory_metadata_is_rejected() -> None:
    index = ArtifactIndex(experiment_id="exp-1")
    first = ArtifactRecord.for_payload(
        {"x": 1},
        artifact_type=ArtifactType.RAW,
        producer="ingest",
        producer_version="0.1",
        artifact_id="occurrence-1",
    )
    index.add(first)
    # Same artifact_id, different producer -- corrupted bookkeeping, not a legitimate
    # re-run, and must not silently overwrite the original occurrence.
    conflicting = first.model_copy(update={"producer": "different-producer"})
    with pytest.raises(ArtifactLineageError):
        index.add(conflicting)


def test_same_content_different_cases_or_runs_is_allowed() -> None:
    # An empty {} raw output, or a repeated identical refusal, may legitimately recur
    # across different attempts/cases; each occurrence must be independently retrievable.
    index = ArtifactIndex(experiment_id="exp-1")
    empty_payload: dict = {}
    occurrence_case_a = ArtifactRecord.for_payload(
        empty_payload,
        artifact_type=ArtifactType.RAW,
        producer="c1-provider",
        producer_version="0.1",
        case_id="case-a",
    )
    occurrence_case_b = ArtifactRecord.for_payload(
        empty_payload,
        artifact_type=ArtifactType.RAW,
        producer="c1-provider",
        producer_version="0.1",
        case_id="case-b",
    )
    index.add(occurrence_case_a)
    index.add(occurrence_case_b)
    assert occurrence_case_a.content_hash == occurrence_case_b.content_hash
    assert occurrence_case_a.artifact_id != occurrence_case_b.artifact_id
    assert len(index.records) == 2


def test_same_content_different_artifact_ids_are_both_retrievable() -> None:
    index = ArtifactIndex(experiment_id="exp-1")
    payload = {"refusal": True}
    first = ArtifactRecord.for_payload(
        payload, artifact_type=ArtifactType.RAW, producer="c1-provider", producer_version="0.1"
    )
    second = ArtifactRecord.for_payload(
        payload, artifact_type=ArtifactType.RAW, producer="c1-provider", producer_version="0.1"
    )
    index.add(first)
    index.add(second)

    matches = index.find_by_content_hash(first.content_hash)
    assert {record.artifact_id for record in matches} == {first.artifact_id, second.artifact_id}
    assert index.records[first.artifact_id] is not index.records[second.artifact_id]


def test_content_mutation_changes_content_hash_but_not_artifact_id_identity() -> None:
    first = ArtifactRecord.for_payload(
        {"x": 1}, artifact_type=ArtifactType.RAW, producer="ingest", producer_version="0.1"
    )
    second = ArtifactRecord.for_payload(
        {"x": 2}, artifact_type=ArtifactType.RAW, producer="ingest", producer_version="0.1"
    )
    assert first.content_hash != second.content_hash
    assert first.artifact_id != second.artifact_id


def test_duplicate_content_does_not_collapse_distinct_attempts() -> None:
    # Three separate attempts that all happen to fail with an identical error payload
    # must all be retained as three distinct occurrences, not merged into one.
    index = ArtifactIndex(experiment_id="exp-1")
    error_payload = {"error": "rate_limited"}
    occurrences = [
        ArtifactRecord.for_payload(
            error_payload,
            artifact_type=ArtifactType.RAW,
            producer="c2-provider",
            producer_version="0.1",
            case_id="case-x",
        )
        for _ in range(3)
    ]
    for occurrence in occurrences:
        index.add(occurrence)
    assert len({o.artifact_id for o in occurrences}) == 3
    assert len(index.records) == 3
    assert len(index.find_by_content_hash(occurrences[0].content_hash)) == 3


def test_lineage_still_resolves_with_shared_content_hash_among_parents() -> None:
    # Two RAW occurrences share content; a PARSED record derived from one of them must
    # resolve lineage to exactly that occurrence, not be confused by the shared hash.
    index = ArtifactIndex(experiment_id="exp-1")
    shared_payload = {"text": "same raw text"}
    raw_a = ArtifactRecord.for_payload(
        shared_payload, artifact_type=ArtifactType.RAW, producer="ingest", producer_version="0.1"
    )
    raw_b = ArtifactRecord.for_payload(
        shared_payload, artifact_type=ArtifactType.RAW, producer="ingest", producer_version="0.1"
    )
    index.add(raw_a)
    index.add(raw_b)

    parsed_from_b = ArtifactRecord.for_payload(
        {**shared_payload, "tokens": ["same", "raw", "text"]},
        artifact_type=ArtifactType.PARSED,
        producer="parser",
        producer_version="0.1",
        parent_ids=[raw_b.artifact_id],
    )
    index.add(parsed_from_b)

    chain = index.lineage(parsed_from_b.artifact_id)
    assert [record.artifact_id for record in chain] == [parsed_from_b.artifact_id, raw_b.artifact_id]
    assert raw_a.artifact_id not in [record.artifact_id for record in chain]


def test_failed_and_successful_attempts_are_both_representable() -> None:
    success = ExperimentAttempt(
        attempt_id="a1",
        case_id="c1",
        comparator_id="C1",
        attempt_number=1,
        status=AttemptStatus.SUCCESS,
        prediction=PredictionBundle(case_id="c1", comparator_id="C1"),
    )
    assert success.prediction is not None

    for status in (
        AttemptStatus.TIMEOUT,
        AttemptStatus.PROVIDER_ERROR,
        AttemptStatus.REFUSAL,
        AttemptStatus.INVALID_JSON,
        AttemptStatus.TRUNCATED,
        AttemptStatus.PARSE_FAILURE,
        AttemptStatus.SCHEMA_VALIDATION_FAILURE,
        AttemptStatus.OTHER_FAILURE,
    ):
        failed = ExperimentAttempt(
            attempt_id="a-fail",
            case_id="c1",
            comparator_id="C1",
            attempt_number=1,
            status=status,
            error_message=f"simulated {status.value}",
        )
        assert failed.prediction is None
        assert failed.status == status


def test_success_status_requires_prediction() -> None:
    with pytest.raises(ValidationError):
        ExperimentAttempt(
            attempt_id="a1",
            case_id="c1",
            comparator_id="C1",
            attempt_number=1,
            status=AttemptStatus.SUCCESS,
            prediction=None,
        )


def test_no_external_api_or_paid_model_call_occurs() -> None:
    # Checkpoint B added kdaa.evaluation.paper_b.adapters.llm_harness, which legitimately
    # imports httpx -- but only to classify exception *types* raised by a provider
    # (isinstance(exc, httpx.TimeoutException), etc.), never to construct an httpx.Client
    # or make a request itself. The actual network-capable client only ever exists in
    # kdaa.providers.openai_compatible.OpenAICompatibleProvider (outside this package,
    # gated behind an explicit live-credential check in the pilot script -- see
    # scripts/run_paper_b_dev_llm.py). So a blanket "no httpx import" ban (WP1's original
    # form of this check, before any LLM code existed) is no longer the right test; the
    # precise, still-meaningful guarantee is that no file under kdaa.evaluation.paper_b
    # itself constructs an httpx.Client or calls a request method.
    import ast
    from pathlib import Path

    import kdaa.evaluation.paper_b as paper_b_pkg

    disallowed_network_modules = {"requests", "urllib.request", "openai", "anthropic"}
    network_call_attrs = {"post", "get", "put", "delete", "request", "stream"}
    package_dir = Path(paper_b_pkg.__file__).resolve().parent
    for source_path in package_dir.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = {node.module.split(".")[0]}
            else:
                imported = set()
            offending = imported & disallowed_network_modules
            assert not offending, f"{source_path.name} imports network dependency {offending}"

            if isinstance(node, ast.Call):
                func = node.func
                is_httpx_client = (
                    isinstance(func, ast.Attribute)
                    and func.attr == "Client"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "httpx"
                )
                if is_httpx_client:
                    raise AssertionError(f"{source_path.name} constructs an httpx.Client")
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr in network_call_attrs
                    and isinstance(func.value, ast.Name)
                    and func.value.id in {"client", "session"}
                ):
                    raise AssertionError(f"{source_path.name} appears to make an HTTP call: {func.attr}(...)")
