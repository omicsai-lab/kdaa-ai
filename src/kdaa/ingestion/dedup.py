"""Conservative trace de-duplication for analysis-time evidence control.

The system retains every supplied trace in the exported run and provenance graph,
but exact or source-record-equivalent duplicates can be excluded from discovery and
assessment so repeated ingestion does not inflate apparent support.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from kdaa.models import EvidenceTrace, TraceRelation, TraceRelationType

_DETECTION_METHOD = "trace_identity_key_v0.1"

# Only these relation types represent the same underlying evidence occurring more than
# once; they are the only ones that merge two traces into one independent-support group.
# DERIVATIVE and SEMANTIC_NEAR_DUPLICATE relations may be represented in `TraceRelation`
# but intentionally do not merge groups here -- that policy belongs to a later work
# package. The absence of a relation between two traces is never treated as proof of
# independence; it only means no grouping relation has been detected yet.
_SUPPORT_MERGING_RELATION_TYPES = frozenset(
    {TraceRelationType.EXACT_DUPLICATE, TraceRelationType.SOURCE_RECORD_EQUIVALENT}
)


@dataclass(frozen=True)
class TraceDeduplicationResult:
    """Canonical traces plus duplicate-to-canonical trace mappings."""

    canonical_traces: list[EvidenceTrace]
    duplicate_to_canonical: dict[str, str]
    trace_relations: list[TraceRelation] = field(default_factory=list)

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


def _relation_type_for_key(key: str) -> TraceRelationType:
    """A strong source-record identifier (``record|...``) reflects the same underlying
    source record or an equivalent source identity; any other match reflects merely
    identical normalized content without stronger source identity evidence."""
    if key.startswith("record|"):
        return TraceRelationType.SOURCE_RECORD_EQUIVALENT
    return TraceRelationType.EXACT_DUPLICATE


def deduplicate_traces(traces: list[EvidenceTrace]) -> TraceDeduplicationResult:
    """Select canonical traces without deleting the original evidence records."""

    canonical: list[EvidenceTrace] = []
    duplicate_to_canonical: dict[str, str] = {}
    trace_relations: list[TraceRelation] = []
    key_to_canonical_id: dict[str, str] = {}

    for trace in traces:
        key = trace_identity_key(trace)
        canonical_id = key_to_canonical_id.get(key)
        if canonical_id is None:
            key_to_canonical_id[key] = trace.id
            canonical.append(trace)
        else:
            duplicate_to_canonical[trace.id] = canonical_id
            relation_type = _relation_type_for_key(key)
            trace_relations.append(
                TraceRelation(
                    id=f"relation-dedup-{trace.id}",
                    source_trace_id=trace.id,
                    target_trace_id=canonical_id,
                    relation_type=relation_type,
                    confidence=1.0,
                    rationale=(
                        "Same strong source record identity."
                        if relation_type == TraceRelationType.SOURCE_RECORD_EQUIVALENT
                        else "Same normalized content without a stronger source identifier."
                    ),
                    detection_method=_DETECTION_METHOD,
                )
            )

    return TraceDeduplicationResult(
        canonical_traces=canonical,
        duplicate_to_canonical=duplicate_to_canonical,
        trace_relations=trace_relations,
    )


def independent_support_groups(
    trace_ids: Iterable[str], relations: list[TraceRelation]
) -> list[list[str]]:
    """Group trace IDs into independent-analytical-support clusters.

    Only ``EXACT_DUPLICATE`` and ``SOURCE_RECORD_EQUIVALENT`` relations merge two traces
    into the same support group, reflecting that they represent one occurrence of evidence
    counted once. Every other trace -- including those connected only by a ``DERIVATIVE`` or
    ``SEMANTIC_NEAR_DUPLICATE`` relation, or by no relation at all -- remains its own
    singleton group: WP2 provides representation and exact/source-equivalence grouping
    only, not semantic-dependence policy, and absence of a relation is never treated as
    proof of independence.

    Returns groups as sorted lists of trace IDs, themselves sorted by their first member,
    so the result is fully deterministic regardless of input or relation order.
    """
    parent: dict[str, str] = {trace_id: trace_id for trace_id in trace_ids}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        if left not in parent or right not in parent:
            return
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for relation in relations:
        if relation.relation_type in _SUPPORT_MERGING_RELATION_TYPES:
            union(relation.source_trace_id, relation.target_trace_id)

    groups: dict[str, list[str]] = defaultdict(list)
    for trace_id in parent:
        groups[find(trace_id)].append(trace_id)

    return sorted((sorted(members) for members in groups.values()), key=lambda members: members[0])
