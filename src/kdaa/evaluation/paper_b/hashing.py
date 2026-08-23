"""Canonical serialization and content hashing for Paper B evaluation artifacts.

Per protocol clarification PC-01, "deterministic exact reproducibility" applies to the
canonical *scientific* payload and explicitly excludes volatile execution metadata: run
UUIDs, wall-clock timestamps, filesystem paths, and machine-specific timing. Rather than
re-implementing that exclusion list wherever hashing happens, a field is marked volatile
once, at the point it is declared, via ``Field(json_schema_extra={VOLATILE_MARKER: True})``.
``canonical_payload`` walks the live object graph (not an already-dumped dict, so nested
volatile fields are still visible as such) and drops every field so marked before hashing.

Identical scientific content always produces an identical canonical hash; volatile fields
never affect it.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

SCHEMA_VERSION = "0.1.0-wp1"
VOLATILE_MARKER = "paper_b_volatile"


def _is_volatile_field(model_cls: type[BaseModel], field_name: str) -> bool:
    field_info = model_cls.model_fields.get(field_name)
    if field_info is None:
        return False
    extra = field_info.json_schema_extra
    if not isinstance(extra, dict):
        return False
    return bool(extra.get(VOLATILE_MARKER))


def canonical_payload(value: Any) -> Any:
    """Recursively reduce ``value`` to a JSON-safe structure with volatile fields removed.

    Operates on live objects rather than a pre-dumped dict: a ``BaseModel`` field is only
    converted to a plain dict after its own volatile fields have been stripped, so nesting
    a volatile-marked model inside another model still excludes it correctly.
    """
    if isinstance(value, BaseModel):
        cls = type(value)
        return {
            field_name: canonical_payload(getattr(value, field_name))
            for field_name in cls.model_fields
            if not _is_volatile_field(cls, field_name)
        }
    if isinstance(value, dict):
        return {str(key): canonical_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [canonical_payload(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def canonical_json_bytes(value: Any) -> bytes:
    payload = canonical_payload(value)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
