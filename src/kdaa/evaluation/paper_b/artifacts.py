"""Immutable, content-addressed artifact lineage for Paper B (raw -> parsed -> validated -> scored).

Occurrence identity and content identity are kept separate. ``artifact_id`` identifies one
occurrence -- one specific attempt's raw output, one specific parse of it, and so on -- and
is unique per record. ``content_hash`` identifies the bytes/content itself and is derived
from the payload, so it is immutable for a given occurrence but is *not* required to be
unique across occurrences: identical raw output (an empty ``{}``, a repeated refusal or
error) can legitimately recur across different attempts/cases, and each such recurrence is
still its own occurrence with its own lineage.

``ArtifactIndex`` is therefore keyed by ``artifact_id``, and ``parent_ids``/lineage
traversal reference ``artifact_id`` values, not content hashes -- following a content hash
would be ambiguous whenever more than one occurrence shares it. ``find_by_content_hash``
provides the optional reverse lookup from content to the occurrence(s) that produced it.

Registering the same ``artifact_id`` twice with identical metadata is a no-op (idempotent
re-registration of the same occurrence); registering it twice with different metadata is
rejected as a data-integrity error. Different ``artifact_id`` values sharing the same
``content_hash`` are always allowed and both remain independently retrievable.

Scoring itself is out of scope for WP1; ``ArtifactType.SCORED`` exists so the lineage chain
already has a place for it once WP5 exists.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from enum import Enum
from typing import Any

from pydantic import Field, model_validator

from .base import StrictEvalModel
from .hashing import SCHEMA_VERSION, content_hash


class ArtifactType(str, Enum):
    RAW = "raw"
    PARSED = "parsed"
    VALIDATED = "validated"
    SCORED = "scored"


_REQUIRES_PARENT = frozenset({ArtifactType.PARSED, ArtifactType.VALIDATED, ArtifactType.SCORED})


class ArtifactLineageError(RuntimeError):
    """Raised when an artifact index operation would violate lineage or occurrence identity."""


class ArtifactRecord(StrictEvalModel):
    schema_version: str = SCHEMA_VERSION
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    artifact_type: ArtifactType
    content_hash: str = Field(min_length=1)
    producer: str = Field(min_length=1)
    producer_version: str = Field(min_length=1)
    parent_ids: tuple[str, ...] = ()
    experiment_id: str | None = None
    case_id: str | None = None

    @model_validator(mode="after")
    def parent_requirement_matches_type(self) -> ArtifactRecord:
        if self.artifact_type in _REQUIRES_PARENT and not self.parent_ids:
            raise ValueError(
                f"{self.artifact_type.value} artifacts must declare at least one parent_id"
            )
        if self.artifact_type == ArtifactType.RAW and self.parent_ids:
            raise ValueError("raw artifacts must not declare a parent_id")
        return self

    @classmethod
    def for_payload(
        cls,
        payload: Any,
        *,
        artifact_type: ArtifactType,
        producer: str,
        producer_version: str,
        parent_ids: Sequence[str] = (),
        experiment_id: str | None = None,
        case_id: str | None = None,
        artifact_id: str | None = None,
    ) -> ArtifactRecord:
        """Build a record whose ``content_hash`` is derived from ``payload`` itself, so the
        hash can never drift from the content it claims to describe. ``artifact_id`` may be
        supplied explicitly (e.g. to pre-generate it before hashing); otherwise a fresh one
        is generated, so calling this twice for identical ``payload`` yields two distinct
        occurrences that both carry the same ``content_hash``.
        """
        kwargs: dict[str, Any] = dict(
            artifact_type=artifact_type,
            content_hash=content_hash(payload),
            producer=producer,
            producer_version=producer_version,
            parent_ids=tuple(parent_ids),
            experiment_id=experiment_id,
            case_id=case_id,
        )
        if artifact_id is not None:
            kwargs["artifact_id"] = artifact_id
        return cls(**kwargs)


class ArtifactIndex(StrictEvalModel):
    schema_version: str = SCHEMA_VERSION
    experiment_id: str = Field(min_length=1)
    records: dict[str, ArtifactRecord] = Field(default_factory=dict)

    def add(self, record: ArtifactRecord) -> ArtifactRecord:
        """Register ``record`` under its ``artifact_id``. Returns the record now stored,
        which is ``record`` itself unless an identical occurrence was already indexed."""
        for parent_id in record.parent_ids:
            if parent_id not in self.records:
                raise ArtifactLineageError(f"Unknown parent artifact_id: {parent_id}")
        existing = self.records.get(record.artifact_id)
        if existing is not None:
            if existing != record:
                raise ArtifactLineageError(
                    f"artifact_id {record.artifact_id} is already registered with "
                    "different metadata; artifact occurrences are immutable once indexed"
                )
            return existing
        self.records[record.artifact_id] = record
        return record

    def lineage(self, artifact_id: str) -> list[ArtifactRecord]:
        """Return the chain from the occurrence ``artifact_id`` back through its ancestors,
        nearest first, following ``parent_ids`` transitively."""
        chain: list[ArtifactRecord] = []
        seen: set[str] = set()
        frontier = [artifact_id]
        while frontier:
            current = frontier.pop(0)
            if current in seen or current not in self.records:
                continue
            seen.add(current)
            record = self.records[current]
            chain.append(record)
            frontier.extend(record.parent_ids)
        return chain

    def by_type(self, artifact_type: ArtifactType) -> list[ArtifactRecord]:
        return [record for record in self.records.values() if record.artifact_type == artifact_type]

    def find_by_content_hash(self, content_hash_value: str) -> list[ArtifactRecord]:
        """Reverse lookup: every indexed occurrence sharing this content hash. Multiple
        occurrences legitimately sharing content (e.g. repeated identical refusals across
        attempts) are all returned, distinguished by their own ``artifact_id``."""
        return [
            record for record in self.records.values() if record.content_hash == content_hash_value
        ]
