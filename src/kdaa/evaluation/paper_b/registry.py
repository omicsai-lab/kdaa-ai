"""Minimal experiment registry state machine for Paper B.

WP1 provides only the state contract -- ``development -> frozen -> executed`` -- and
illegal-transition rejection. It does not implement final-case generation (WP3), the
development pilot (WP11), or execution (WP12); those later work packages drive this
registry rather than being implemented by it.
"""

from __future__ import annotations

from enum import Enum

from pydantic import PrivateAttr

from .base import StrictEvalModel
from .config import ExperimentLock
from .hashing import content_hash


class RegistryState(str, Enum):
    DEVELOPMENT = "development"
    FROZEN = "frozen"
    EXECUTED = "executed"


_ALLOWED_TRANSITIONS: dict[RegistryState, frozenset[RegistryState]] = {
    RegistryState.DEVELOPMENT: frozenset({RegistryState.FROZEN}),
    RegistryState.FROZEN: frozenset({RegistryState.EXECUTED}),
    RegistryState.EXECUTED: frozenset(),
}


class RegistryTransitionError(RuntimeError):
    """Raised on an illegal state regression, re-freeze, or mutation-after-freeze attempt."""


class ExperimentRegistry(StrictEvalModel):
    """Tracks one experiment's lifecycle state and which case manifests it has admitted.

    ``case_manifest_hashes`` is exposed only as a read-only tuple via a property; the
    backing list is a private attribute so external code cannot append to it directly and
    bypass the state check in ``register_case``.
    """

    experiment_id: str
    state: RegistryState = RegistryState.DEVELOPMENT
    experiment_lock_hash: str
    frozen_at_lock_hash: str | None = None

    _case_manifest_hashes: list[str] = PrivateAttr(default_factory=list)

    @classmethod
    def open_development(
        cls, *, experiment_id: str, experiment_lock: ExperimentLock
    ) -> ExperimentRegistry:
        return cls(experiment_id=experiment_id, experiment_lock_hash=content_hash(experiment_lock))

    @property
    def case_manifest_hashes(self) -> tuple[str, ...]:
        return tuple(self._case_manifest_hashes)

    def register_case(self, case_manifest_hash: str) -> None:
        if self.state != RegistryState.DEVELOPMENT:
            raise RegistryTransitionError(
                f"Cannot register a new case manifest once registry state is {self.state.value}"
            )
        if case_manifest_hash not in self._case_manifest_hashes:
            self._case_manifest_hashes.append(case_manifest_hash)

    def freeze(self, *, experiment_lock: ExperimentLock) -> None:
        if content_hash(experiment_lock) != self.experiment_lock_hash:
            raise RegistryTransitionError(
                "Experiment lock content differs from the lock this registry was opened "
                "against; refusing to freeze against a changed scientific configuration"
            )
        self._transition(RegistryState.FROZEN)
        self.frozen_at_lock_hash = self.experiment_lock_hash

    def mark_executed(self) -> None:
        self._transition(RegistryState.EXECUTED)

    def _transition(self, target: RegistryState) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(self.state, frozenset())
        if target not in allowed:
            raise RegistryTransitionError(
                f"Illegal registry state transition: {self.state.value} -> {target.value}"
            )
        self.state = target
