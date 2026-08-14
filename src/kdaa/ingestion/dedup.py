"""Conservative trace de-duplication for analysis-time evidence control.

The system retains every supplied trace in the exported run and provenance graph,
but exact or source-record-equivalent duplicates can be excluded from discovery and
assessment so repeated ingestion does not inflate apparent support.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from kdaa.models import EvidenceTrace


@dataclass(frozen=True)
class TraceDeduplicationResult:
    """Canonical traces plus duplicate-to-canonical trace mappings."""

    canonical_traces: list[EvidenceTrace]
    duplicate_to_canonical: dict[str, str]

    @property
    def duplicate_count(self) -> int:
        return len(self.duplicate_to_canonical)


def _normalize(value: str | None) -> str:
    text = (value or "").casefold().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def trace_identity_key(trace: EvidenceTrace) -> str:
    """Return a conservative identity key for exact/source-record duplicates.

    Strong source record identifiers take precedence. A source URI is not used
    alone because one CV/PDF can produce multiple legitimate trace segments.
    """

    source_scope = trace.source_kind.value
    record_id = _normalize(trace.source_record_id)
    if record_id:
        return f"record|{source_scope}|{trace.trace_type.value}|{record_id}"

    uri = _normalize(trace.source_uri)
    title = _normalize(trace.title)
    if uri and title:
        return f"uri-title|{source_scope}|{trace.trace_type.value}|{uri}|{title}"

    content_payload = "|".join(
        [
            source_scope,
            trace.trace_type.value,
            title,
            _normalize(trace.description),
            _normalize(trace.abstract),
            _normalize(trace.content),
            trace.event_date.isoformat() if trace.event_date else "",
        ]
    )
    digest = hashlib.sha256(content_payload.encode("utf-8")).hexdigest()
    return f"content|{digest}"


def deduplicate_traces(traces: list[EvidenceTrace]) -> TraceDeduplicationResult:
    """Select canonical traces without deleting the original evidence records."""

    canonical: list[EvidenceTrace] = []
    duplicate_to_canonical: dict[str, str] = {}
    key_to_canonical_id: dict[str, str] = {}

    for trace in traces:
        key = trace_identity_key(trace)
        canonical_id = key_to_canonical_id.get(key)
        if canonical_id is None:
            key_to_canonical_id[key] = trace.id
            canonical.append(trace)
        else:
            duplicate_to_canonical[trace.id] = canonical_id

    return TraceDeduplicationResult(
        canonical_traces=canonical,
        duplicate_to_canonical=duplicate_to_canonical,
    )
