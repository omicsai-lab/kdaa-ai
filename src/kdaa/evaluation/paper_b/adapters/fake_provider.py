"""A deterministic, local, no-network ``JSONProvider`` for tests and the development
pilot's dry-run mode (Checkpoint B Section 14: "the same command should support a dry/
fake-provider validation mode"). Never makes a live call.
"""

from __future__ import annotations

from typing import Any


class FakeJSONProvider:
    """Cycles through a fixed, caller-supplied sequence of responses (dicts) or
    exceptions to raise, so tests can exercise success, retry-then-succeed, and
    exhausted-retry failure paths without any network access.
    """

    def __init__(self, responses: list[dict[str, Any] | Exception], *, model_name: str = "fake-dev-model-v0") -> None:
        if not responses:
            raise ValueError("FakeJSONProvider requires at least one response")
        self._responses = list(responses)
        self.model_name = model_name
        self.call_count = 0

    def generate_json(self, *, system: str, user: str) -> dict[str, Any]:
        response = self._responses[self.call_count % len(self._responses)]
        self.call_count += 1
        if isinstance(response, Exception):
            raise response
        return response


def always_succeeding_provider(concepts: list[dict[str, Any]], ranked_opportunity_ids: list[str]) -> FakeJSONProvider:
    """Convenience constructor: always returns the same well-formed response."""
    return FakeJSONProvider([{"concepts": concepts, "ranked_opportunity_ids": ranked_opportunity_ids}])
