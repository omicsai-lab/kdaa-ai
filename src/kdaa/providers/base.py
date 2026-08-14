"""Provider protocol."""

from __future__ import annotations

from typing import Any, Protocol


class JSONProvider(Protocol):
    model_name: str

    def generate_json(self, *, system: str, user: str) -> dict[str, Any]: ...
