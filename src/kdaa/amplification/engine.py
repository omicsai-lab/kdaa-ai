"""Asset--opportunity matching and opportunity-specific amplifiability."""

from __future__ import annotations

import hashlib
import itertools
import re

from kdaa.amplification.catalog import TEMPLATES, OpportunityTemplate
from kdaa.assessment.opportunity_fit import goal_alignment_score
from kdaa.config import OpportunityConfig
from kdaa.models import (
    AmplificationOpportunity,
    AssetRecord,
    GainVector,
    OutputContainer,
    StrategicGoal,
)


def _stable_id(unit_id: str, template_key: str, asset_ids: list[str]) -> str:
    payload = "|".join([unit_id, template_key, *sorted(asset_ids)])
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"opp-{template_key}-{digest}"


def _text_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9+\-]{2,}", text.lower())
        if token not in {"the", "and", "for", "with", "from", "into", "that", "this"}
    }


def _asset_namespace(asset: AssetRecord) -> str:
    parts = asset.id.split("-")
    return parts[1] if len(parts) > 2 else "unknown"


def _short_label(label: str) -> str:
    replacements = (
        ("Repeatable capability in ", ""),
        ("End-to-end execution capability in ", "end-to-end "),
        ("Combinative capability linking ", "integration of "),
        ("Reusable software artifact: ", "software artifact "),
        ("Reusable data resource: ", "data resource "),
        ("Reusable protocol: ", "protocol "),
        ("Reusable curriculum asset: ", "curriculum "),
    )
    for prefix, replacement in replacements:
        if label.startswith(prefix):
            return replacement + label[len(prefix):]
    return label


def _template_affinity(template: OpportunityTemplate, assets: list[AssetRecord]) -> float:
    categories = {category.value for asset in assets for category in asset.categories}
    asset_tokens = _text_tokens(
        " ".join(
            [
                *(asset.label for asset in assets),
                *(asset.bounded_claim for asset in assets),
                *(" ".join(asset.concept_tags) for asset in assets),
            ]
        )
    )
    category_score = (
        len(categories & set(template.preferred_categories))
        / max(1, len(set(template.preferred_categories)))
        if template.preferred_categories
        else 0.5
    )
    term_tokens = _text_tokens(" ".join(template.preferred_terms))
    term_score = len(asset_tokens & term_tokens) / max(1, len(term_tokens))
    namespaces = {_asset_namespace(asset) for asset in assets}
    namespace_score = (
        len(namespaces & set(template.preferred_namespaces))
        / max(1, len(namespaces))
        if template.preferred_namespaces
        else 0.5
    )
    return min(1.0, 0.18 + 0.27 * category_score + 0.37 * term_score + 0.34 * namespace_score)


def _asset_set_allowed(template: OpportunityTemplate, assets: list[AssetRecord]) -> bool:
    namespaces = {_asset_namespace(asset) for asset in assets}
    has_relational = "relational" in namespaces
    if has_relational and template.key != "grant_program":
        return False
    if (
        template.key in {"research_repository", "deployable_copilot", "methods_paper"}
        and not namespaces & {"artifact", "execution", "pair"}
    ):
        return False
    return not (len(assets) == 2 and len({asset.id for asset in assets}) < 2)


def _aggregate_asset_score(assets: list[AssetRecord], field: str, default: float = 0.4) -> float:
    values: list[float] = []
    for asset in assets:
        assessment = asset.assessment
        if not assessment:
            continue
        dimension = getattr(assessment, field)
        values.append(float(dimension.value))
    return sum(values) / len(values) if values else default


def _combine_gain(base: GainVector, interfaceability: float, governance_risk: float) -> GainVector:
    factor = 0.65 + 0.55 * interfaceability
    risk_drag = 0.20 * governance_risk
    payload = base.model_dump()
    for key, value in payload.items():
        adjusted = (
            float(value) - governance_risk * 0.25
            if key == "risk"
            else float(value) * factor - risk_drag * 0.10
        )
        payload[key] = max(-1.0, min(1.0, adjusted))
    return GainVector(**payload)


def _candidate_asset_sets(assets: list[AssetRecord]) -> list[list[AssetRecord]]:
    ranked = sorted(
        assets,
        key=lambda asset: (
            -(asset.assessment.overall_credibility.value if asset.assessment else 0.0),
            -asset.discovery_confidence,
        ),
    )
    candidates: list[list[AssetRecord]] = [[asset] for asset in ranked[:10]]
    for first, second in itertools.combinations(ranked[:8], 2):
        tags_a, tags_b = set(first.concept_tags), set(second.concept_tags)
        overlap = len(tags_a & tags_b) / max(1, len(tags_a | tags_b))
        # Prefer complementary rather than duplicate pairs.
        if overlap < 0.75:
            candidates.append([first, second])
    return candidates


def _make_opportunity(
    *,
    unit_id: str,
    goals: list[StrategicGoal],
    template: OpportunityTemplate,
    assets: list[AssetRecord],
) -> AmplificationOpportunity:
    credibility = _aggregate_asset_score(assets, "overall_credibility", 0.45)
    maturity = _aggregate_asset_score(assets, "maturity", 0.40)
    distinctiveness = _aggregate_asset_score(assets, "distinctiveness", 0.45)
    interfaceability = _aggregate_asset_score(assets, "ai_interfaceability", 0.45)
    privacy = _aggregate_asset_score(assets, "privacy_risk", 0.10)
    appropriability = _aggregate_asset_score(assets, "appropriability_risk", 0.30)
    dependency = _aggregate_asset_score(assets, "dependency_intensity", 0.35)
    affinity = _template_affinity(template, assets)
    specificity_map = {"artifact": 0.95, "pair": 0.90, "execution": 0.86, "concept": 0.66, "relational": 0.55, "llm": 0.60}
    specificity = sum(specificity_map.get(_asset_namespace(asset), 0.55) for asset in assets) / len(assets)
    asset_phrase = " + ".join(_short_label(asset.label) for asset in assets)
    title = f"{template.title_prefix} {asset_phrase}"
    goal_alignment = goal_alignment_score(assets, goals, title + " " + template.problem)
    fit = min(1.0, 0.29 * affinity + 0.27 * credibility + 0.18 * goal_alignment + 0.14 * distinctiveness + 0.12 * specificity)
    governance_risk = min(1.0, 0.36 * privacy + 0.36 * appropriability + 0.28 * dependency)
    amplifiability = min(1.0, max(0.0, 0.25 + 0.55 * interfaceability + 0.20 * affinity - 0.25 * governance_risk))
    readiness = min(1.0, 0.42 * maturity + 0.36 * credibility + 0.22 * interfaceability)
    priority = min(
        1.0,
        max(
            0.0,
            0.34 * fit
            + 0.24 * amplifiability
            + 0.22 * readiness
            + 0.10 * distinctiveness
            + 0.10 * (1.0 - governance_risk),
        ),
    )
    expected_gain = _combine_gain(template.expected_gain, interfaceability, governance_risk)
    dependencies = sorted({dep for asset in assets for dep in asset.dependencies})
    caveats = list(template.caveats)
    if any(asset.human_calibration_required for asset in assets):
        caveats.append(
            "At least one matched asset still requires human calibration; treat this as a provisional opportunity."
        )
    caveats.append(
        "AI amplifiability is an opportunity-specific proxy and must be tested against the stated baseline."
    )
    return AmplificationOpportunity(
        id=_stable_id(unit_id, template.key, [asset.id for asset in assets]),
        unit_id=unit_id,
        title=title,
        problem=template.problem,
        beneficiary=template.beneficiary,
        output_container=template.output_container,
        value_pathways=list(template.value_pathways),
        asset_ids=[asset.id for asset in assets],
        complementary_asset_ids=[asset.id for asset in assets[1:]],
        rationale=(
            f"Template affinity={affinity:.2f}, asset credibility={credibility:.2f}, "
            f"goal alignment={goal_alignment:.2f}, distinctiveness proxy={distinctiveness:.2f}, "
            f"and artifact specificity={specificity:.2f}."
        ),
        ai_tasks=list(template.ai_tasks),
        human_tasks=list(template.human_tasks),
        verification_gates=list(template.verification_gates),
        credible_baseline=template.credible_baseline,
        expected_gain=expected_gain,
        fit_score=round(fit, 4),
        amplifiability_score=round(amplifiability, 4),
        readiness_score=round(readiness, 4),
        governance_risk=round(governance_risk, 4),
        priority_score=round(priority, 4),
        estimated_effort=template.effort,  # type: ignore[arg-type]
        time_horizon=template.horizon,
        dependencies=dependencies,
        caveats=caveats,
    )


def generate_opportunities(
    unit_id: str,
    assets: list[AssetRecord],
    goals: list[StrategicGoal],
    config: OpportunityConfig,
) -> list[AmplificationOpportunity]:
    if not assets:
        return []
    candidates: list[AmplificationOpportunity] = []
    asset_sets = _candidate_asset_sets(assets)
    for template in TEMPLATES:
        template_candidates = [
            _make_opportunity(unit_id=unit_id, goals=goals, template=template, assets=asset_set)
            for asset_set in asset_sets
            if _asset_set_allowed(template, asset_set)
        ]
        template_candidates = [
            item for item in template_candidates if item.fit_score >= config.min_fit_score
        ]
        if template_candidates:
            candidates.append(max(template_candidates, key=lambda item: item.priority_score))

    # De-duplicate by template/container and highly overlapping asset sets.
    selected: list[AmplificationOpportunity] = []
    for opportunity in sorted(candidates, key=lambda item: (-item.priority_score, item.title)):
        ids = set(opportunity.asset_ids)
        too_similar = False
        for existing in selected:
            existing_ids = set(existing.asset_ids)
            overlap = len(ids & existing_ids) / max(1, len(ids | existing_ids))
            same_prefix = opportunity.id.split("-")[1] == existing.id.split("-")[1]
            if same_prefix and overlap >= 0.75:
                too_similar = True
                break
        if not too_similar:
            selected.append(opportunity)

    if config.include_all_five_containers:
        mandatory: list[AmplificationOpportunity] = []
        for container in OutputContainer:
            options = [item for item in selected if item.output_container == container]
            if options:
                mandatory.append(max(options, key=lambda item: item.priority_score))
        mandatory_ids = {item.id for item in mandatory}
        remainder = [item for item in selected if item.id not in mandatory_ids]
        selected = mandatory + sorted(remainder, key=lambda item: -item.priority_score)

    return sorted(selected[: config.max_opportunities], key=lambda item: -item.priority_score)
