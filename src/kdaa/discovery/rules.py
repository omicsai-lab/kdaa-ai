"""Deterministic, provenance-first asset-hypothesis discovery."""

from __future__ import annotations

import hashlib
import itertools
from collections import Counter, defaultdict
from collections.abc import Iterable

from kdaa.config import DiscoveryConfig
from kdaa.discovery.features import TraceFeatures
from kdaa.models import (
    AssetCategory,
    AssetRecord,
    AssetState,
    EvidenceLink,
    EvidenceRole,
    EvidenceTrace,
    OwnershipState,
    TraceType,
    UnitBundle,
)
from kdaa.ontology import Ontology

CODIFIED_TRACE_TYPES = {
    TraceType.PUBLICATION,
    TraceType.SOFTWARE,
    TraceType.DATASET,
    TraceType.PROTOCOL,
    TraceType.COURSE,
    TraceType.PATENT,
    TraceType.DOCUMENT,
}

EXECUTION_TRACE_TYPES = {
    TraceType.SOFTWARE,
    TraceType.PROJECT,
    TraceType.GRANT,
    TraceType.PROTOCOL,
    TraceType.OUTCOME,
}


def _stable_id(unit_id: str, namespace: str, tokens: Iterable[str]) -> str:
    payload = "|".join([unit_id, namespace, *sorted(tokens)])
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"asset-{namespace}-{digest}"


def _trace_weight(trace: EvidenceTrace, feature: TraceFeatures) -> float:
    completion = 1.0 if trace.outcome_signals.get("completed", True) else 0.75
    reuse = trace.outcome_signals.get("reuse_count", 0)
    reuse_bonus = min(0.15, float(reuse) * 0.02) if isinstance(reuse, (int, float)) else 0.0
    return min(1.0, feature.source_weight * 0.55 + feature.role_weight * 0.35 + completion * 0.1 + reuse_bonus)


def _categories_for(
    concept_keys: set[str],
    evidence: list[EvidenceTrace],
    ontology: Ontology,
    *,
    combinative: bool = False,
    relational: bool = False,
) -> list[AssetCategory]:
    categories: list[AssetCategory] = []
    groups = {ontology.concepts[key].group for key in concept_keys if key in ontology.concepts}
    if any(trace.trace_type in CODIFIED_TRACE_TYPES for trace in evidence):
        categories.append(AssetCategory.CODIFIED)
    if any(trace.trace_type in {TraceType.EMPLOYMENT, TraceType.PROJECT, TraceType.COLLABORATION} for trace in evidence):
        categories.append(AssetCategory.TACIT_PROCEDURAL)
    if relational or "relational" in groups:
        categories.append(AssetCategory.RELATIONAL)
    if combinative or "execution" in groups or len({trace.trace_type for trace in evidence}) >= 3:
        categories.append(AssetCategory.COMBINATIVE_EXECUTION)
    if len(set(categories)) >= 3:
        categories.append(AssetCategory.BUNDLE)
    if not categories:
        categories = [AssetCategory.TACIT_PROCEDURAL]
    return list(dict.fromkeys(categories))


def _standard_alternatives(evidence: list[EvidenceTrace]) -> list[str]:
    alternatives = [
        "The observed outputs may reflect collaborator-led work rather than a capability owned by the focal unit.",
        "The evidence may represent a one-time activity rather than a repeatable capability.",
    ]
    if any(trace.contribution_role.value == "unknown" for trace in evidence):
        alternatives.append("Contribution attribution is incomplete in one or more supporting traces.")
    if len({trace.source_kind for trace in evidence}) == 1:
        alternatives.append("All support comes from one evidence source and may share the same bias.")
    return alternatives


def _build_asset(
    *,
    bundle: UnitBundle,
    namespace: str,
    label: str,
    claim: str,
    enables: list[str],
    exclusions: list[str],
    concept_keys: set[str],
    evidence: list[EvidenceTrace],
    features: dict[str, TraceFeatures],
    ontology: Ontology,
    combinative: bool = False,
    relational: bool = False,
    dependencies: list[str] | None = None,
) -> AssetRecord:
    weighted = [_trace_weight(trace, features[trace.id]) for trace in evidence]
    discovery_confidence = min(
        0.92,
        0.25
        + 0.12 * len(evidence)
        + 0.08 * len({trace.source_kind for trace in evidence})
        + 0.05 * len({trace.trace_type for trace in evidence})
        + 0.12 * (sum(weighted) / max(1, len(weighted))),
    )
    evidence_links = [
        EvidenceLink(
            trace_id=trace.id,
            role=EvidenceRole.SUPPORTING,
            relation="supports",
            rationale=f"{trace.trace_type.value} trace matching the bounded claim",
            weight=round(_trace_weight(trace, features[trace.id]), 4),
        )
        for trace in evidence
    ]
    concept_labels = ontology.labels(sorted(concept_keys))
    return AssetRecord(
        id=_stable_id(bundle.unit.id, namespace, [label, *concept_keys, *[t.id for t in evidence]]),
        unit_id=bundle.unit.id,
        label=label,
        bounded_claim=claim,
        enables=enables,
        exclusions=exclusions,
        categories=_categories_for(
            concept_keys, evidence, ontology, combinative=combinative, relational=relational
        ),
        concept_tags=concept_labels,
        evidence_links=evidence_links,
        alternative_explanations=_standard_alternatives(evidence),
        dependencies=dependencies or [],
        hypothesized_owner=bundle.unit.name,
        ownership_state=OwnershipState.UNRESOLVED,
        ownership_rationale=(
            "Deterministic discovery rules identify supporting traces but do not resolve "
            "individual, shared, organizational, or external ownership; ownership state "
            "defaults to unresolved pending human calibration."
        ),
        epistemic_state=AssetState.HYPOTHESIS,
        discovery_method="deterministic_provenance_rules_v0.1",
        discovery_confidence=round(discovery_confidence, 4),
        human_calibration_required=True,
        notes=[
            "System-generated asset hypothesis; not a confirmed expertise claim.",
            "Supporting evidence must be reviewed for attribution, boundary, and tacit dependencies.",
        ],
    )


def discover_asset_hypotheses(
    bundle: UnitBundle,
    features: dict[str, TraceFeatures],
    ontology: Ontology,
    config: DiscoveryConfig,
) -> list[AssetRecord]:
    trace_by_id = {trace.id: trace for trace in bundle.traces}
    concept_to_trace_ids: dict[str, list[str]] = defaultdict(list)
    for trace_id, feature in features.items():
        for concept_key in feature.concept_keys:
            concept_to_trace_ids[concept_key].append(trace_id)

    assets: list[AssetRecord] = []

    # 1. Codified single-artifact hypotheses. These are bounded by the artifact
    # and therefore can be useful even before cross-trace aggregation.
    if config.include_single_artifact_assets:
        artifact_types = {
            TraceType.SOFTWARE: "Reusable software artifact",
            TraceType.DATASET: "Reusable data resource",
            TraceType.PROTOCOL: "Reusable protocol",
            TraceType.COURSE: "Reusable curriculum asset",
            TraceType.PATENT: "Codified intellectual-property asset",
        }
        for trace in bundle.traces:
            if trace.trace_type not in artifact_types:
                continue
            concept_keys = features[trace.id].concept_keys
            asset_kind = artifact_types[trace.trace_type]
            label = f"{asset_kind}: {trace.title}"
            artifact_kind_text = trace.trace_type.value.replace("_", " ")
            if trace.contribution_role.value == "unknown":
                # No explicit independent contribution evidence: do not claim control or
                # material contribution (e.g. GitHub repository ownership alone does not
                # establish authorship -- see kdaa.ingestion.github).
                claim = (
                    f"The evidence documents a reusable {artifact_kind_text} publicly "
                    f"associated with the focal unit, represented by '{trace.title}'; "
                    "independent contribution has not been established."
                )
            else:
                claim = (
                    f"The focal unit appears to control or materially contribute to a reusable "
                    f"{artifact_kind_text} represented by '{trace.title}'."
                )
            assets.append(
                _build_asset(
                    bundle=bundle,
                    namespace="artifact",
                    label=label,
                    claim=claim,
                    enables=[
                        "reuse or adaptation of the documented artifact",
                        "future externalization into one or more output containers",
                    ],
                    exclusions=[
                        "ownership of all underlying components",
                        "evidence that the artifact is effective outside its documented context",
                    ],
                    concept_keys=set(concept_keys),
                    evidence=[trace],
                    features=features,
                    ontology=ontology,
                    dependencies=["license and contribution review"],
                )
            )

    # 2. Repeated concept-level capability hypotheses.
    ranked_concepts = sorted(
        concept_to_trace_ids.items(),
        key=lambda item: (
            -len(set(item[1])),
            -sum(features[trace_id].concept_counts.get(item[0], 0) for trace_id in item[1]),
            item[0],
        ),
    )
    for concept_key, trace_ids in ranked_concepts[: config.max_topic_assets * 2]:
        unique_ids = list(dict.fromkeys(trace_ids))
        if len(unique_ids) < config.min_trace_support:
            continue
        evidence = [trace_by_id[trace_id] for trace_id in unique_ids]
        concept = ontology.concepts[concept_key]
        contexts = sorted({trace.trace_type.value.replace("_", " ") for trace in evidence})
        label = f"Repeatable capability in {concept.label}"
        assets.append(
            _build_asset(
                bundle=bundle,
                namespace="concept",
                label=label,
                claim=(
                    f"Across {len(evidence)} traces, the focal unit appears able to apply "
                    f"{concept.label.lower()} in more than one documented activity or output."
                ),
                enables=[
                    f"application of {concept.label.lower()} to adjacent problems",
                    "reuse of accumulated methods, examples, and judgment",
                ],
                exclusions=[
                    f"mastery of every subfield adjacent to {concept.label.lower()}",
                    "independent ownership of all cited outputs",
                ],
                concept_keys={concept_key},
                evidence=evidence,
                features=features,
                ontology=ontology,
                dependencies=[f"documented contexts: {', '.join(contexts[:5])}"],
            )
        )
        if sum(1 for asset in assets if asset.id.startswith("asset-concept")) >= config.max_topic_assets:
            break

    # 3. Pairwise combinative hypotheses require recurring co-occurrence.
    pair_counts: Counter[tuple[str, str]] = Counter()
    pair_trace_ids: dict[tuple[str, str], list[str]] = defaultdict(list)
    for trace_id, feature in features.items():
        concepts = sorted(feature.concept_keys)
        for pair in itertools.combinations(concepts, 2):
            pair_counts[pair] += 1
            pair_trace_ids[pair].append(trace_id)
    ranked_pairs = sorted(pair_counts.items(), key=lambda item: (-item[1], item[0]))
    for pair, support in ranked_pairs:
        if support < config.min_pair_support:
            continue
        evidence = [trace_by_id[trace_id] for trace_id in dict.fromkeys(pair_trace_ids[pair])]
        a, b = pair
        a_def, b_def = ontology.concepts[a], ontology.concepts[b]
        # Pairs within a single narrow group are less informative than cross-boundary combinations.
        cross_group = a_def.group != b_def.group
        if not cross_group and support < config.min_pair_support + 1:
            continue
        label = f"Combinative capability linking {a_def.label} and {b_def.label}"
        assets.append(
            _build_asset(
                bundle=bundle,
                namespace="pair",
                label=label,
                claim=(
                    f"The focal unit appears able to combine {a_def.label.lower()} and "
                    f"{b_def.label.lower()} within a recurring problem-solving workflow."
                ),
                enables=[
                    "cross-boundary translation between the two knowledge areas",
                    "generation of opportunities that require both components",
                ],
                exclusions=[
                    "proof of superadditive value",
                    "transfer to contexts with substantially different data, stakeholders, or governance",
                ],
                concept_keys={a, b},
                evidence=evidence,
                features=features,
                ontology=ontology,
                combinative=True,
                dependencies=["boundary-translation capacity", "ownership and integration review"],
            )
        )
        if sum(1 for asset in assets if asset.id.startswith("asset-pair")) >= config.max_pair_assets:
            break

    # 4. Relational hypotheses based on repeated co-participation, deliberately
    # bounded to access/coordination rather than claiming collaborators' expertise.
    contributor_to_trace_ids: dict[str, list[str]] = defaultdict(list)
    for trace in bundle.traces:
        for contributor in trace.authors_or_contributors:
            normalized = contributor.strip()
            if normalized and normalized.lower() != bundle.unit.name.lower():
                contributor_to_trace_ids[normalized].append(trace.id)
    ranked_contributors = sorted(
        contributor_to_trace_ids.items(), key=lambda item: (-len(set(item[1])), item[0])
    )
    for contributor, trace_ids in ranked_contributors[: config.max_relational_assets]:
        unique_ids = list(dict.fromkeys(trace_ids))
        if len(unique_ids) < 2:
            continue
        evidence = [trace_by_id[trace_id] for trace_id in unique_ids]
        # A relationship should not inherit the union of every domain ever seen
        # around that collaborator. Keep only the most recurrent contexts so the
        # relational claim does not masquerade as broad substantive expertise.
        relationship_concepts: Counter[str] = Counter(
            concept_key
            for trace in evidence
            for concept_key in sorted(features[trace.id].concept_keys)
        )
        ranked_relationship_concepts = sorted(
            relationship_concepts.items(),
            key=lambda item: (-item[1], item[0]),
        )
        concept_keys = {concept_key for concept_key, _ in ranked_relationship_concepts[:4]}
        assets.append(
            _build_asset(
                bundle=bundle,
                namespace="relational",
                label=f"Recurring collaborative linkage with {contributor}",
                claim=(
                    f"The focal unit has a recurring documented working relationship with {contributor} "
                    f"across {len(evidence)} traces, potentially enabling access, coordination, or "
                    "boundary-spanning knowledge."
                ),
                enables=["repeated coordination", "access to complementary expertise"],
                exclusions=[
                    f"ownership of {contributor}'s knowledge or contributions",
                    "evidence that the relationship is currently active or available for every opportunity",
                ],
                concept_keys=concept_keys,
                evidence=evidence,
                features=features,
                ontology=ontology,
                relational=True,
                dependencies=[contributor, "relationship continuity and consent"],
            )
        )

    # 5. End-to-end execution hypotheses require heterogeneous trace types and
    # at least one implementation or outcome-oriented trace.
    execution_candidates: list[tuple[str, list[EvidenceTrace]]] = []
    for concept_key, trace_ids in concept_to_trace_ids.items():
        evidence = [trace_by_id[trace_id] for trace_id in dict.fromkeys(trace_ids)]
        type_count = len({trace.trace_type for trace in evidence})
        has_execution = any(trace.trace_type in EXECUTION_TRACE_TYPES for trace in evidence)
        if type_count >= 3 and has_execution:
            execution_candidates.append((concept_key, evidence))
    execution_candidates.sort(key=lambda item: (-len(item[1]), item[0]))
    for concept_key, evidence in execution_candidates[: config.max_execution_assets]:
        concept = ontology.concepts[concept_key]
        assets.append(
            _build_asset(
                bundle=bundle,
                namespace="execution",
                label=f"End-to-end execution capability in {concept.label}",
                claim=(
                    f"The focal unit appears able to carry {concept.label.lower()} from planning or "
                    "funding through implementation and a reusable or externally visible output."
                ),
                enables=[
                    "translation from idea to implemented output",
                    "repeatable orchestration of complementary tasks and artifacts",
                ],
                exclusions=[
                    "evidence that every stage is performed without collaborators",
                    "proof that the workflow is equally effective across all settings",
                ],
                concept_keys={concept_key},
                evidence=evidence,
                features=features,
                ontology=ontology,
                combinative=True,
                dependencies=["complementary people and infrastructure", "execution context"],
            )
        )

    return _deduplicate_assets(assets)


def _deduplicate_assets(assets: list[AssetRecord]) -> list[AssetRecord]:
    """Remove near-identical hypotheses while retaining different theoretical levels."""

    kept: list[AssetRecord] = []
    for asset in sorted(assets, key=lambda a: (-a.discovery_confidence, a.label)):
        evidence_set = {link.trace_id for link in asset.evidence_links}
        tag_set = set(asset.concept_tags)
        duplicate = False
        for existing in kept:
            existing_evidence = {link.trace_id for link in existing.evidence_links}
            existing_tags = set(existing.concept_tags)
            evidence_union = evidence_set | existing_evidence
            tag_union = tag_set | existing_tags
            evidence_jaccard = (
                len(evidence_set & existing_evidence) / len(evidence_union) if evidence_union else 0.0
            )
            tag_jaccard = len(tag_set & existing_tags) / len(tag_union) if tag_union else 0.0
            if evidence_jaccard > 0.88 and tag_jaccard > 0.88 and asset.label == existing.label:
                duplicate = True
                break
        if not duplicate:
            kept.append(asset)
    return sorted(kept, key=lambda a: (-a.discovery_confidence, a.label))
