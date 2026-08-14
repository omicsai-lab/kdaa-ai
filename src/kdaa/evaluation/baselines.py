"""Simple baselines deliberately representing flat-profile extraction."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from kdaa.discovery.features import extract_trace_features
from kdaa.models import UnitBundle
from kdaa.ontology import Ontology


@dataclass(frozen=True)
class FlatProfileResult:
    predicted_concepts: set[str]
    profile_labels: list[str]
    provenance_completeness: float
    unsupported_claim_rate: float


class FlatKeywordProfileBaseline:
    """Top concept mentions from a flattened evidence dump.

    The baseline does not retain claim-level provenance, alternative
    explanations, or epistemic state. It is intentionally representative of a
    generic profile/summarization workflow rather than a straw-man classifier.
    """

    def __init__(self, max_concepts: int = 8) -> None:
        self.max_concepts = max_concepts

    def run(self, bundle: UnitBundle, ontology: Ontology) -> FlatProfileResult:
        features = extract_trace_features(bundle.traces, ontology)
        counts: Counter[str] = Counter()
        for feature in features.values():
            counts.update(feature.concept_counts)
        ranked = [
            key
            for key, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[
                : self.max_concepts
            ]
        ]
        labels = [f"Expertise in {ontology.concepts[key].label}" for key in ranked]
        return FlatProfileResult(
            predicted_concepts=set(ranked),
            profile_labels=labels,
            provenance_completeness=0.0,
            unsupported_claim_rate=1.0 if labels else 0.0,
        )
