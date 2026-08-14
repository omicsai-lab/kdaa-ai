"""Feature extraction for evidence traces."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from kdaa.models import EvidenceTrace
from kdaa.ontology import Ontology


@dataclass(frozen=True)
class TraceFeatures:
    trace_id: str
    concept_counts: dict[str, int]
    concept_groups: dict[str, str]
    concept_labels: dict[str, str]
    source_weight: float
    role_weight: float
    text_length: int

    @property
    def concept_keys(self) -> set[str]:
        return set(self.concept_counts)


def extract_trace_features(
    traces: list[EvidenceTrace], ontology: Ontology
) -> dict[str, TraceFeatures]:
    result: dict[str, TraceFeatures] = {}
    for trace in traces:
        matches = ontology.match(trace.searchable_text)
        counts = Counter({match.key: match.count for match in matches})
        groups = {match.key: match.group for match in matches}
        labels = {match.key: match.label for match in matches}
        source_weight = ontology.trace_type_weights.get(trace.trace_type.value, 0.35)
        role_weight = ontology.role_weights.get(trace.contribution_role.value, 0.35)
        result[trace.id] = TraceFeatures(
            trace_id=trace.id,
            concept_counts=dict(counts),
            concept_groups=groups,
            concept_labels=labels,
            source_weight=source_weight,
            role_weight=role_weight,
            text_length=len(trace.searchable_text),
        )
    return result
