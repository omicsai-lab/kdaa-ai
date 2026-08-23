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
            parent_hashes=("someparent",),
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
        parent_hashes=[raw.content_hash],
    )
    index.add(parsed)

    validated_payload = {**parsed_payload, "valid": True}
    validated = ArtifactRecord.for_payload(
        validated_payload,
        artifact_type=ArtifactType.VALIDATED,
        producer="validator",
        producer_version="0.1",
        parent_hashes=[parsed.content_hash],
    )
    index.add(validated)

    chain = index.lineage(validated.content_hash)
    assert [record.artifact_type for record in chain] == [
        ArtifactType.VALIDATED,
        ArtifactType.PARSED,
        ArtifactType.RAW,
    ]
    assert index.by_type(ArtifactType.RAW) == [raw]


def test_artifact_index_rejects_unknown_parent_hash() -> None:
    index = ArtifactIndex(experiment_id="exp-1")
    orphan = ArtifactRecord.for_payload(
        {"x": 1},
        artifact_type=ArtifactType.PARSED,
        producer="parser",
        producer_version="0.1",
        parent_hashes=["does-not-exist"],
    )
    with pytest.raises(ArtifactLineageError):
        index.add(orphan)


def test_artifact_index_reindexing_identical_content_is_a_no_op() -> None:
    index = ArtifactIndex(experiment_id="exp-1")
    record = ArtifactRecord.for_payload(
        {"x": 1}, artifact_type=ArtifactType.RAW, producer="ingest", producer_version="0.1"
    )
    stored_first = index.add(record)
    duplicate = ArtifactRecord.for_payload(
        {"x": 1}, artifact_type=ArtifactType.RAW, producer="ingest", producer_version="0.1"
    )
    stored_second = index.add(duplicate)
    assert stored_first.content_hash == stored_second.content_hash
    assert len(index.records) == 1


def test_artifact_index_rejects_hash_collision_with_different_metadata() -> None:
    # Two records that happen to share a content_hash but disagree on lineage metadata
    # indicate corrupted bookkeeping, not a legitimate re-run, and must not overwrite
    # each other silently.
    index = ArtifactIndex(experiment_id="exp-1")
    first = ArtifactRecord.for_payload(
        {"x": 1}, artifact_type=ArtifactType.RAW, producer="ingest", producer_version="0.1"
    )
    index.add(first)
    conflicting = first.model_copy(update={"producer": "different-producer"})
    with pytest.raises(ArtifactLineageError):
        index.add(conflicting)


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
    # WP1 has no providers or generators yet, so the only way to be sure no live call can
    # happen is structural: none of its source files import an HTTP/provider dependency.
    import ast
    from pathlib import Path

    import kdaa.evaluation.paper_b as paper_b_pkg

    network_modules = {"requests", "httpx", "urllib.request", "openai", "anthropic"}
    package_dir = Path(paper_b_pkg.__file__).resolve().parent
    for source_path in package_dir.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = {node.module.split(".")[0]}
            else:
                continue
            offending = imported & {m.split(".")[0] for m in network_modules}
            assert not offending, f"{source_path.name} imports network dependency {offending}"
