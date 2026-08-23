import copy

import pytest
import yaml
from pydantic import ValidationError

from kdaa.evaluation.paper_b import (
    ChallengeCategory,
    ExperimentRegistry,
    RegistryState,
    RegistryTransitionError,
)
from kdaa.evaluation.paper_b.config import (
    DEFAULT_EXPERIMENT_LOCK_PATH,
    ExperimentLock,
    load_experiment_lock,
)


def test_default_experiment_lock_loads_and_matches_committed_yaml() -> None:
    lock = load_experiment_lock()
    with DEFAULT_EXPERIMENT_LOCK_PATH.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    assert lock.document_id == raw["document_id"]
    assert lock.target_journal == "Knowledge-Based Systems"
    assert lock.fallback_journal == "Expert Systems with Applications"
    assert lock.data.final_synthetic.total_n == 240
    assert lock.data.final_synthetic.core_n == 180
    assert lock.data.final_synthetic.challenge_n == 60
    assert [list(pair) for pair in lock.primary_contrasts] == [
        ["C3", "C0_S"],
        ["C4", "C1"],
        ["C4", "C2"],
    ]
    assert lock.statistics.bootstrap_resamples == 10000
    assert lock.statistics.best_of_n_selection_allowed is False


def test_challenge_category_enum_matches_frozen_lock_exactly() -> None:
    lock = load_experiment_lock()
    assert {c.value for c in ChallengeCategory} == set(lock.data.final_synthetic.challenge_categories)


def test_load_experiment_lock_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_experiment_lock("/nonexistent/path/experiment_lock.yaml")


def _valid_payload() -> dict:
    with DEFAULT_EXPERIMENT_LOCK_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_experiment_lock_rejects_missing_required_field(tmp_path) -> None:
    payload = copy.deepcopy(_valid_payload())
    del payload["target_journal"]
    broken = tmp_path / "broken_lock.yaml"
    broken.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_experiment_lock(broken)


def test_experiment_lock_rejects_unknown_field(tmp_path) -> None:
    payload = copy.deepcopy(_valid_payload())
    payload["an_unexpected_new_key"] = True
    broken = tmp_path / "broken_lock.yaml"
    broken.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_experiment_lock(broken)


def test_experiment_lock_rejects_wrong_type(tmp_path) -> None:
    payload = copy.deepcopy(_valid_payload())
    payload["data"]["final_synthetic"]["total_n"] = "two hundred forty"
    broken = tmp_path / "broken_lock.yaml"
    broken.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_experiment_lock(broken)


def test_experiment_lock_canonical_hash_is_stable_and_content_sensitive() -> None:
    lock_a = load_experiment_lock()
    lock_b = ExperimentLock.model_validate(_valid_payload())
    assert lock_a.canonical_hash() == lock_b.canonical_hash()

    payload = copy.deepcopy(_valid_payload())
    payload["statistics"]["bootstrap_resamples"] = 5000
    mutated = ExperimentLock.model_validate(payload)
    assert mutated.canonical_hash() != lock_a.canonical_hash()


def test_registry_rejects_illegal_state_regression() -> None:
    lock = load_experiment_lock()
    registry = ExperimentRegistry.open_development(experiment_id="exp-1", experiment_lock=lock)
    assert registry.state == RegistryState.DEVELOPMENT

    with pytest.raises(RegistryTransitionError):
        registry.mark_executed()

    registry.freeze(experiment_lock=lock)
    assert registry.state == RegistryState.FROZEN

    with pytest.raises(RegistryTransitionError):
        registry.freeze(experiment_lock=lock)

    registry.mark_executed()
    assert registry.state == RegistryState.EXECUTED

    with pytest.raises(RegistryTransitionError):
        registry.mark_executed()
    with pytest.raises(RegistryTransitionError):
        registry.freeze(experiment_lock=lock)


def test_registry_rejects_case_registration_after_freeze() -> None:
    lock = load_experiment_lock()
    registry = ExperimentRegistry.open_development(experiment_id="exp-1", experiment_lock=lock)
    registry.register_case("hash-1")
    registry.freeze(experiment_lock=lock)
    with pytest.raises(RegistryTransitionError):
        registry.register_case("hash-2")
    assert registry.case_manifest_hashes == ("hash-1",)


def test_registry_refuses_to_freeze_against_a_changed_lock() -> None:
    lock = load_experiment_lock()
    registry = ExperimentRegistry.open_development(experiment_id="exp-1", experiment_lock=lock)

    payload = copy.deepcopy(_valid_payload())
    payload["statistics"]["bootstrap_resamples"] = 1
    changed_lock = ExperimentLock.model_validate(payload)

    with pytest.raises(RegistryTransitionError):
        registry.freeze(experiment_lock=changed_lock)
    assert registry.state == RegistryState.DEVELOPMENT
