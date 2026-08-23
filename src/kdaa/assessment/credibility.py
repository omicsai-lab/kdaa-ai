"""Transparent proxy scoring for provisional asset records.

Scores are engineering aids, not validated psychometric or causal measures.
Every dimension records its method, rationale, uncertainty, and proxy status.
"""

from __future__ import annotations

import math
from datetime import date
from statistics import mean

from kdaa.config import AssessmentConfig
from kdaa.discovery.features import TraceFeatures
from kdaa.models import (
    AssetAssessment,
    AssetCategory,
    AssetRecord,
    AssetState,
    EvidenceRole,
    EvidenceTrace,
    OwnershipState,
    ScoreDimension,
    TraceType,
)
from kdaa.ontology import Ontology

# Conservative dependency-intensity increment by typed ownership state (WP2 requirement
# A6). UNRESOLVED must not be treated as proof of external dependency -- it increases
# attribution uncertainty elsewhere, not this dependency proxy.
_OWNERSHIP_DEPENDENCY_INCREMENT: dict[OwnershipState, float] = {
    OwnershipState.FOCAL_UNIT: 0.00,
    OwnershipState.UNRESOLVED: 0.00,
    OwnershipState.SHARED: 0.10,
    OwnershipState.ORGANIZATIONAL: 0.10,
    OwnershipState.EXTERNAL: 0.10,
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _dimension(
    value: float,
    method: str,
    rationale: str,
    *,
    uncertainty: float = 0.25,
    is_proxy: bool = True,
) -> ScoreDimension:
    return ScoreDimension(
        value=round(_clamp(value), 4),
        method=method,
        rationale=rationale,
        uncertainty=round(_clamp(uncertainty), 4),
        is_proxy=is_proxy,
    )


def _recency_score(
    traces: list[EvidenceTrace], half_life_years: float, as_of_date: date
) -> tuple[float, str]:
    dated = [trace.event_date for trace in traces if trace.event_date]
    if not dated:
        return 0.45, "No reliable event dates; neutral-low recency proxy used."
    values = []
    for event_date in dated:
        age_years = max(0.0, (as_of_date - event_date).days / 365.25)
        values.append(math.exp(-math.log(2) * age_years / half_life_years))
    return mean(values), f"Exponential decay over {len(values)} dated traces as of {as_of_date.isoformat()}."


def assess_asset_records(
    assets: list[AssetRecord],
    traces: list[EvidenceTrace],
    features: dict[str, TraceFeatures],
    ontology: Ontology,
    config: AssessmentConfig,
    *,
    as_of_date: date,
) -> list[AssetRecord]:
    trace_by_id = {trace.id: trace for trace in traces}
    assessed: list[AssetRecord] = []

    for asset in assets:
        linked = [
            trace_by_id[link.trace_id]
            for link in asset.evidence_links
            if link.trace_id in trace_by_id and link.role == EvidenceRole.SUPPORTING
        ]
        contradicting = [
            link for link in asset.evidence_links if link.role == EvidenceRole.CONTRADICTING
        ]
        weights = [
            next(
                (link.weight for link in asset.evidence_links if link.trace_id == trace.id),
                0.5,
            )
            for trace in linked
        ]
        source_kinds = {trace.source_kind for trace in linked}
        trace_types = {trace.trace_type for trace in linked}

        evidence_strength_value = _clamp(
            0.16
            + 0.22 * math.log1p(len(linked))
            + 0.14 * math.log1p(len(source_kinds))
            + 0.11 * math.log1p(len(trace_types))
            + 0.28 * (mean(weights) if weights else 0.0)
            - 0.12 * len(contradicting)
        )
        evidence_strength = _dimension(
            evidence_strength_value,
            "weighted_evidence_count_source_and_type_diversity_v0.1",
            (
                f"{len(linked)} supporting traces from {len(source_kinds)} source kinds and "
                f"{len(trace_types)} trace types; {len(contradicting)} contradicting links."
            ),
            uncertainty=0.18 if len(linked) >= 3 else 0.35,
        )

        role_values = [
            ontology.role_weights.get(trace.contribution_role.value, 0.35) for trace in linked
        ]
        attribution_value = mean(role_values) if role_values else 0.25
        role_based_uncertainty = (
            0.15 if all(trace.contribution_role.value != "unknown" for trace in linked) else 0.42
        )
        unresolved_ownership = asset.ownership_state == OwnershipState.UNRESOLVED
        attribution_uncertainty = max(
            role_based_uncertainty,
            0.42 if unresolved_ownership else 0.0,
        )
        attribution_confidence = _dimension(
            attribution_value,
            "contribution_role_weight_average_with_ownership_uncertainty_v0.2",
            (
                "Average of explicit contribution-role weights across supporting traces. "
                "Contribution role is trace-level evidence about how a trace was produced; "
                "it is not ownership and does not by itself establish sole ownership. "
                "Unresolved typed ownership widens uncertainty to at least 0.42 regardless "
                "of role weights, since no ownership evidence has been resolved."
            ),
            uncertainty=attribution_uncertainty,
        )

        reuse_values: list[float] = []
        completion_values: list[float] = []
        for trace in linked:
            reuse = trace.outcome_signals.get("reuse_count", 0)
            reuse_values.append(min(1.0, float(reuse) / 5.0) if isinstance(reuse, (int, float)) else 0.0)
            completion_values.append(1.0 if trace.outcome_signals.get("completed", False) else 0.3)
        mature_types = len(trace_types) / 5.0
        maturity_value = _clamp(
            0.15
            + 0.22 * min(1.0, len(linked) / 4.0)
            + 0.20 * min(1.0, mature_types)
            + 0.23 * (mean(reuse_values) if reuse_values else 0.0)
            + 0.20 * (mean(completion_values) if completion_values else 0.0)
        )
        maturity = _dimension(
            maturity_value,
            "repetition_output_and_reuse_proxy_v0.1",
            "Combines repeated evidence, heterogeneous output types, completion, and reuse signals.",
            uncertainty=0.35,
        )

        label_specificity = min(1.0, len(asset.label.split()) / 11.0)
        combinative = AssetCategory.COMBINATIVE_EXECUTION in asset.categories
        tag_count = len(asset.concept_tags)
        distinctiveness_value = _clamp(
            0.25 + 0.20 * label_specificity + 0.20 * min(1.0, tag_count / 3.0) + (0.18 if combinative else 0.0)
        )
        distinctiveness = _dimension(
            distinctiveness_value,
            "within-record_specificity_and_combination_proxy_v0.1",
            (
                "Proxy based on bounded specificity and cross-concept combination. "
                "No external labor-market or peer benchmark is used."
            ),
            uncertainty=0.55,
        )

        tacit_types = sum(
            trace.trace_type in {TraceType.EMPLOYMENT, TraceType.PROJECT, TraceType.COLLABORATION}
            for trace in linked
        )
        codified_types = sum(trace.trace_type in {TraceType.SOFTWARE, TraceType.DATASET, TraceType.PROTOCOL, TraceType.PUBLICATION, TraceType.COURSE, TraceType.DOCUMENT} for trace in linked)
        tacitness_value = _clamp(
            0.15
            + 0.45 * (tacit_types / max(1, len(linked)))
            + (0.18 if AssetCategory.TACIT_PROCEDURAL in asset.categories else 0.0)
            + (0.12 if AssetCategory.RELATIONAL in asset.categories else 0.0)
            - 0.20 * (codified_types / max(1, len(linked)))
        )
        tacitness = _dimension(
            tacitness_value,
            "trace_type_and_asset_category_proxy_v0.1",
            "Higher for employment, project, and relational evidence; lower for reusable codified artifacts.",
            uncertainty=0.40,
        )

        cross_context = min(1.0, len(trace_types) / 4.0)
        codification = min(1.0, codified_types / max(1, len(linked)))
        transferability_value = _clamp(0.18 + 0.42 * cross_context + 0.40 * codification - 0.25 * tacitness_value)
        transferability = _dimension(
            transferability_value,
            "cross_context_and_codification_proxy_v0.1",
            "Rewards repeated appearance across trace types and codified representations; penalizes tacitness.",
            uncertainty=0.38,
        )

        unique_people = {
            contributor
            for trace in linked
            for contributor in trace.authors_or_contributors
            if contributor.strip()
        }
        ownership_increment = _OWNERSHIP_DEPENDENCY_INCREMENT.get(asset.ownership_state, 0.0)
        dependency_value = _clamp(
            0.10
            + 0.10 * min(1.0, len(asset.dependencies) / 4.0)
            + 0.35 * min(1.0, len(unique_people) / 6.0)
            + (0.20 if AssetCategory.RELATIONAL in asset.categories else 0.0)
            + ownership_increment
        )
        dependency_intensity = _dimension(
            dependency_value,
            "people_and_declared_dependency_proxy_typed_ownership_v0.2",
            (
                "Counts recurring people, declared dependencies, and relational/collective "
                "characteristics, plus a conservative increment from the typed ownership_state "
                f"({asset.ownership_state.value}: +{ownership_increment:.2f}). UNRESOLVED ownership "
                "is not treated as proof of external dependency; it contributes no increment here "
                "and instead widens attribution uncertainty elsewhere."
            ),
            uncertainty=0.42,
        )

        recency_value, recency_rationale = _recency_score(
            linked, config.recency_half_life_years, as_of_date
        )
        decay_risk = _dimension(
            1.0 - recency_value,
            "inverse_exponential_recency_v0.1",
            recency_rationale,
            uncertainty=0.25 if any(trace.event_date for trace in linked) else 0.50,
        )

        public_codified = sum(
            trace.trace_type in {TraceType.PUBLICATION, TraceType.SOFTWARE, TraceType.DATASET, TraceType.DOCUMENT}
            and bool(trace.source_uri)
            for trace in linked
        )
        appropriability_value = _clamp(
            0.18
            + 0.38 * (public_codified / max(1, len(linked)))
            + 0.16 * codification
            - 0.10 * dependency_value
        )
        appropriability_risk = _dimension(
            appropriability_value,
            "public_codification_and_imitation_proxy_v0.1",
            "Higher when public codified traces make imitation or attribution leakage easier.",
            uncertainty=0.45,
        )

        interface_trace_types = {
            TraceType.PUBLICATION: 0.72,
            TraceType.SOFTWARE: 0.95,
            TraceType.DATASET: 0.92,
            TraceType.PROTOCOL: 0.82,
            TraceType.COURSE: 0.78,
            TraceType.DOCUMENT: 0.86,
            TraceType.GRANT: 0.67,
            TraceType.PROJECT: 0.55,
            TraceType.EMPLOYMENT: 0.30,
            TraceType.COLLABORATION: 0.25,
            TraceType.TALK: 0.52,
        }
        interface_values = [interface_trace_types.get(trace.trace_type, 0.45) for trace in linked]
        ai_interfaceability_value = _clamp(
            (mean(interface_values) if interface_values else 0.35) - 0.18 * tacitness_value
        )
        ai_interfaceability = _dimension(
            ai_interfaceability_value,
            "trace_modality_ai_interface_proxy_v0.1",
            "Higher for text, code, data, and structured protocols; lower for relational and highly tacit evidence.",
            uncertainty=0.30,
        )

        sensitive_fraction = sum(trace.sensitive for trace in linked) / max(1, len(linked))
        privacy_risk_value = _clamp(
            0.05 + 0.70 * sensitive_fraction + (0.10 if AssetCategory.RELATIONAL in asset.categories else 0.0)
        )
        privacy_risk = _dimension(
            privacy_risk_value,
            "sensitive_trace_fraction_v0.1",
            "Derived from trace sensitivity flags and relational content.",
            uncertainty=0.25,
        )

        w = config.weights
        source_diversity = min(1.0, len(source_kinds) / 3.0)
        recency_contribution = recency_value
        contradiction_penalty = min(1.0, len(contradicting) * 0.25)
        numerator = (
            w.evidence_strength * evidence_strength.value
            + w.attribution_confidence * attribution_confidence.value
            + w.maturity * maturity.value
            + w.transferability * transferability.value
            + w.recency * recency_contribution
            + w.source_diversity * source_diversity
            - w.contradiction_penalty * contradiction_penalty
        )
        denominator = (
            w.evidence_strength
            + w.attribution_confidence
            + w.maturity
            + w.transferability
            + w.recency
            + w.source_diversity
        )
        overall_value = _clamp(numerator / max(denominator, 1e-9))
        overall_credibility = _dimension(
            overall_value,
            "transparent_weighted_proxy_v0.1",
            (
                "Weighted combination of evidence strength, attribution, maturity, transferability, "
                "recency, and source diversity; contradiction penalty applied."
            ),
            uncertainty=max(
                evidence_strength.uncertainty,
                attribution_confidence.uncertainty,
                0.22,
            ),
        )

        assessment = AssetAssessment(
            evidence_strength=evidence_strength,
            attribution_confidence=attribution_confidence,
            maturity=maturity,
            distinctiveness=distinctiveness,
            tacitness=tacitness,
            transferability=transferability,
            dependency_intensity=dependency_intensity,
            decay_risk=decay_risk,
            appropriability_risk=appropriability_risk,
            ai_interfaceability=ai_interfaceability,
            privacy_risk=privacy_risk,
            overall_credibility=overall_credibility,
            scoring_version="0.2.0",
        )
        state = (
            AssetState.PROVISIONAL
            if overall_value >= config.provisional_threshold
            else AssetState.HYPOTHESIS
        )
        needs_review = (
            overall_value < config.human_review_threshold
            or tacitness_value >= config.tacitness_review_threshold
            or attribution_value < 0.75
            or dependency_value > 0.55
            or unresolved_ownership
        )
        assessed.append(
            asset.model_copy(
                update={
                    "assessment": assessment,
                    "epistemic_state": state,
                    "human_calibration_required": needs_review,
                }
            )
        )
    return sorted(
        assessed,
        key=lambda asset: (
            -(asset.assessment.overall_credibility.value if asset.assessment else 0.0),
            asset.label,
        ),
    )
