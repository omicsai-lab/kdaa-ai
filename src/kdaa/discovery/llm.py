"""Optional LLM-assisted hypothesis generation with strict provenance gates."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from kdaa.models import (
    AssetCategory,
    AssetRecord,
    AssetState,
    EvidenceLink,
    EvidenceRole,
    UnitBundle,
)
from kdaa.providers.base import JSONProvider


class LLMSuggestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str
    bounded_claim: str
    enables: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    categories: list[AssetCategory]
    concept_tags: list[str] = Field(default_factory=list)
    supporting_trace_ids: list[str]
    contradicting_trace_ids: list[str] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


def discover_with_llm(
    bundle: UnitBundle,
    provider: JSONProvider,
    *,
    allow_sensitive: bool = False,
    max_suggestions: int = 12,
) -> list[AssetRecord]:
    traces = [trace for trace in bundle.traces if allow_sensitive or not trace.sensitive]
    trace_index = {
        trace.id: {
            "trace_type": trace.trace_type.value,
            "title": trace.title,
            "description": (trace.description or trace.abstract or trace.content)[:1600],
            "keywords": trace.keywords,
            "topics": trace.topics,
            "contribution_role": trace.contribution_role.value,
            "event_date": trace.event_date.isoformat() if trace.event_date else None,
            "source_kind": trace.source_kind.value,
        }
        for trace in traces
    }
    system = (
        "You are an evidence-constrained knowledge-asset analyst. A trace is not an asset. "
        "Return falsifiable, bounded asset hypotheses only. Every active claim must cite one or "
        "more trace IDs supplied by the user. Do not infer prestige, personality, or unsupported "
        "expertise. Distinguish codified, tacit/procedural, relational, and combinative/execution "
        "components. Preserve alternative explanations and attribution uncertainty. Return JSON "
        "with a top-level 'suggestions' array."
    )
    user = json.dumps(
        {
            "focal_unit": bundle.unit.model_dump(mode="json"),
            "traces": trace_index,
            "required_schema": {
                "label": "short label",
                "bounded_claim": "what the asset enables and under which boundary",
                "enables": ["capability"],
                "exclusions": ["what is not claimed"],
                "categories": [
                    "codified|tacit_procedural|relational|combinative_execution|bundle"
                ],
                "concept_tags": ["plain-language tags"],
                "supporting_trace_ids": ["trace-id"],
                "contradicting_trace_ids": ["trace-id"],
                "alternative_explanations": ["plausible alternative"],
                "dependencies": ["person, infrastructure, data, license, or condition"],
                "confidence": "0..1",
            },
            "max_suggestions": max_suggestions,
        },
        ensure_ascii=False,
    )
    response = provider.generate_json(system=system, user=user)
    raw_suggestions = response.get("suggestions", [])
    if not isinstance(raw_suggestions, list):
        raise ValueError("Provider response must contain a 'suggestions' array")

    valid_trace_ids = set(trace_index)
    records: list[AssetRecord] = []
    for raw in raw_suggestions[:max_suggestions]:
        try:
            suggestion = LLMSuggestion.model_validate(raw)
        except ValidationError:
            continue
        supporting = [trace_id for trace_id in suggestion.supporting_trace_ids if trace_id in valid_trace_ids]
        contradicting = [
            trace_id for trace_id in suggestion.contradicting_trace_ids if trace_id in valid_trace_ids
        ]
        if not supporting:
            continue
        payload = "|".join([bundle.unit.id, suggestion.label, *sorted(supporting)])
        asset_id = f"asset-llm-{hashlib.sha1(payload.encode('utf-8')).hexdigest()[:12]}"
        links = [
            EvidenceLink(
                trace_id=trace_id,
                role=EvidenceRole.SUPPORTING,
                relation="supports",
                rationale="LLM-selected supporting trace; requires deterministic and human review.",
                weight=0.55,
            )
            for trace_id in supporting
        ] + [
            EvidenceLink(
                trace_id=trace_id,
                role=EvidenceRole.CONTRADICTING,
                relation="contradicts",
                rationale="LLM-selected contradicting trace; requires review.",
                weight=0.55,
            )
            for trace_id in contradicting
        ]
        records.append(
            AssetRecord(
                id=asset_id,
                unit_id=bundle.unit.id,
                label=suggestion.label,
                bounded_claim=suggestion.bounded_claim,
                enables=suggestion.enables,
                exclusions=suggestion.exclusions,
                categories=suggestion.categories,
                concept_tags=suggestion.concept_tags,
                evidence_links=links,
                alternative_explanations=suggestion.alternative_explanations,
                dependencies=suggestion.dependencies,
                hypothesized_owner=bundle.unit.name,
                epistemic_state=AssetState.HYPOTHESIS,
                discovery_method=f"llm_provenance_gated:{provider.model_name}",
                discovery_confidence=suggestion.confidence,
                human_calibration_required=True,
                notes=[
                    "LLM-assisted suggestion passed a trace-ID provenance gate but is not validated.",
                ],
            )
        )
    return records
