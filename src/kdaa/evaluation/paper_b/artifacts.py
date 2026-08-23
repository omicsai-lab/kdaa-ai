"""Immutable, content-addressed artifact lineage for Paper B (raw -> parsed -> validated -> scored).

``ArtifactIndex`` stores records keyed by content hash, not by a mutable slot name. This
makes silent overwriting structurally impossible rather than merely policy-forbidden: two
different byte payloads always land under two different keys (a SHA-256 property, not an
assumption this code makes), so nothing already indexed can ever be replaced by different
bytes. Re-registering byte-identical content is a no-op; attempting to register the same
content hash with contradictory lineage metadata (different producer/parents/experiment)
is treated as a data integrity error and rejected.

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
    """Raised when an artifact index operation would violate lineage or immutability."""


class ArtifactRecord(StrictEvalModel):
    schema_version: str = SCHEMA_VERSION
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    artifact_type: ArtifactType
    content_hash: str = Field(min_length=1)
    producer: str = Field(min_length=1)
    producer_version: str = Field(min_length=1)
    parent_hashes: tuple[str, ...] = ()
    experiment_id: str | None = None
    case_id: str | None = None

    @model_validator(mode="after")
    def parent_requirement_matches_type(self) -> ArtifactRecord:
        if self.artifact_type in _REQUIRES_PARENT and not self.parent_hashes:
            raise ValueError(
                f"{self.artifact_type.value} artifacts must declare at least one parent_hash"
            )
        if self.artifact_type == ArtifactType.RAW and self.parent_hashes:
            raise ValueError("raw artifacts must not declare a parent_hash")
        return self

    @classmethod
    def for_payload(
        cls,
        payload: Any,
        *,
        artifact_type: ArtifactType,
        producer: str,
        producer_version: str,
        parent_hashes: Sequence[str] = (),
        experiment_id: str | None = None,
        case_id: str | None = None,
    ) -> ArtifactRecord:
        """Build a record whose ``content_hash`` is derived from ``payload`` itself, so the
        hash can never drift from the content it claims to describe."""
        return cls(
            artifact_type=artifact_type,
            content_hash=content_hash(payload),
            producer=producer,
            producer_version=producer_version,
            parent_hashes=tuple(parent_hashes),
            experiment_id=experiment_id,
            case_id=case_id,
        )


class ArtifactIndex(StrictEvalModel):
    schema_version: str = SCHEMA_VERSION
    experiment_id: str = Field(min_length=1)
    records: dict[str, ArtifactRecord] = Field(default_factory=dict)

    def add(self, record: ArtifactRecord) -> ArtifactRecord:
        """Register ``record``. Returns the record now stored under its content hash, which
        is ``record`` itself unless byte-identical content was already indexed."""
        for parent_hash in record.parent_hashes:
            if parent_hash not in self.records:
                raise ArtifactLineageError(f"Unknown parent artifact hash: {parent_hash}")
        existing = self.records.get(record.content_hash)
        if existing is not None:
            same_metadata = existing.model_dump(exclude={"artifact_id"}) == record.model_dump(
                exclude={"artifact_id"}
            )
            if not same_metadata:
                raise ArtifactLineageError(
                    f"Artifact content hash {record.content_hash} is already registered "
                    "with different lineage metadata; artifacts are immutable once indexed"
                )
            return existing
        self.records[record.content_hash] = record
        return record

    def lineage(self, content_hash_value: str) -> list[ArtifactRecord]:
        """Return the chain from ``content_hash_value`` back through its ancestors, nearest
        first, following ``parent_hashes`` transitively."""
        chain: list[ArtifactRecord] = []
        seen: set[str] = set()
        frontier = [content_hash_value]
        while frontier:
            current = frontier.pop(0)
            if current in seen or current not in self.records:
                continue
            seen.add(current)
            record = self.records[current]
            chain.append(record)
            frontier.extend(record.parent_hashes)
        return chain

    def by_type(self, artifact_type: ArtifactType) -> list[ArtifactRecord]:
        return [record for record in self.records.values() if record.artifact_type == artifact_type]
