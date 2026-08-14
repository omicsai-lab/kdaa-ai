"""Configurable concept ontology and text matching utilities."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ConceptDefinition:
    key: str
    label: str
    group: str
    terms: tuple[str, ...]


@dataclass(frozen=True)
class ConceptMatch:
    key: str
    label: str
    group: str
    matched_terms: tuple[str, ...]
    count: int


class Ontology:
    def __init__(
        self,
        concepts: dict[str, ConceptDefinition],
        trace_type_weights: dict[str, float],
        role_weights: dict[str, float],
        version: str = "0.1.0",
    ) -> None:
        self.concepts = concepts
        self.trace_type_weights = trace_type_weights
        self.role_weights = role_weights
        self.version = version
        self._patterns: dict[str, list[tuple[str, re.Pattern[str]]]] = {}
        for key, definition in concepts.items():
            patterns: list[tuple[str, re.Pattern[str]]] = []
            for term in sorted(definition.terms, key=len, reverse=True):
                escaped = re.escape(term.lower())
                pattern = re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.I)
                patterns.append((term, pattern))
            self._patterns[key] = patterns

    @classmethod
    def default(cls) -> "Ontology":
        resource = files("kdaa.resources").joinpath("ontology.yaml")
        with resource.open(encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)
        return cls.from_dict(payload)

    @classmethod
    def from_path(cls, path: str | Path) -> "Ontology":
        with Path(path).open(encoding="utf-8") as handle:
            return cls.from_dict(yaml.safe_load(handle))

    @classmethod
    def from_dict(cls, payload: dict) -> "Ontology":
        concepts = {
            key: ConceptDefinition(
                key=key,
                label=value["label"],
                group=value["group"],
                terms=tuple(value.get("terms", [])),
            )
            for key, value in payload.get("concepts", {}).items()
        }
        return cls(
            concepts=concepts,
            trace_type_weights={
                str(k): float(v) for k, v in payload.get("trace_type_weights", {}).items()
            },
            role_weights={str(k): float(v) for k, v in payload.get("role_weights", {}).items()},
            version=str(payload.get("version", "0.1.0")),
        )

    def match(self, text: str) -> list[ConceptMatch]:
        normalized = normalize_text(text)
        matches: list[ConceptMatch] = []
        for key, definition in self.concepts.items():
            matched_terms: list[str] = []
            count = 0
            for term, pattern in self._patterns[key]:
                found = pattern.findall(normalized)
                if found:
                    matched_terms.append(term)
                    count += len(found)
            if count:
                matches.append(
                    ConceptMatch(
                        key=key,
                        label=definition.label,
                        group=definition.group,
                        matched_terms=tuple(matched_terms),
                        count=count,
                    )
                )
        return sorted(matches, key=lambda item: (-item.count, item.label))

    def labels(self, keys: Iterable[str]) -> list[str]:
        return [self.concepts[k].label for k in keys if k in self.concepts]


def normalize_text(text: str) -> str:
    text = text.lower().replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()
