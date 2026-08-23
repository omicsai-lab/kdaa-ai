"""Development-stage synthetic case generation for Paper B Checkpoint A.

Reuses ``kdaa.ingestion.synthetic``'s asset templates and noise blueprints as shared
*content* (the same accepted pattern already used by the v0.1 benchmark generator), but
produces case evidence and hidden truth as two separate objects instead of embedding
truth in ``UnitBundle.metadata``, per Freeze Section 9.4 (leakage prevention) and the
WP1 truth-side isolation architecture (``kdaa.evaluation.paper_b.truth``).

DEVELOPMENT ONLY. This generator exists to debug and calibrate the evaluation machinery
(Freeze Section 9.1: development set). It is not the frozen final N=240 dataset, does not
attempt disjoint seeds/templates from a not-yet-defined final set, and must never be
reported as final evidence. It deliberately reuses the same declared ontology the
production system uses -- acceptable at development stage (Freeze Section 9.1: development
data may be used "to debug", "tune the strong flat semantic baseline", and "validate the
scorer"), but not a substitute for the final challenge-set's held-out surface forms.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from kdaa.ingestion.synthetic import ASSET_TEMPLATES, NOISE_BLUEPRINTS, SyntheticAssetTemplate
from kdaa.models import (
    ContributionRole,
    EvidenceTrace,
    FocalUnit,
    SourceKind,
    UnitBundle,
    UnitType,
)
from kdaa.ontology import Ontology

from .opportunity_catalog import DEV_OPPORTUNITY_CATALOG
from .opportunity_truth import compute_relevance_grade
from .schemas import (
    AttributionRegime,
    CaseManifest,
    DomainBreadth,
    EvidenceDensity,
    ExperimentUnitType,
    OpportunityCandidate,
    OwnershipLabel,
)
from .truth import TrueAssetConcept, TrueOpportunityRelevance, TruthBundle

_TEMPLATE_KEYS: tuple[str, ...] = tuple(sorted(ASSET_TEMPLATES))
_UNIT_TYPE_CYCLE: tuple[ExperimentUnitType, ...] = (
    ExperimentUnitType.INDIVIDUAL_RESEARCHER,
    ExperimentUnitType.TEAM,
    ExperimentUnitType.LABORATORY,
)
_OWNERSHIP_CYCLE: tuple[OwnershipLabel, ...] = (
    OwnershipLabel.FOCAL_UNIT,
    OwnershipLabel.SHARED,
    OwnershipLabel.ORGANIZATIONAL,
    OwnershipLabel.EXTERNAL,
    OwnershipLabel.UNRESOLVED,
)

# ExperimentUnitType (evaluation-neutral) and production UnitType do not share the same
# string values (e.g. "individual_researcher" vs "researcher"), so an explicit map is
# required rather than passing .value straight through.
_EVAL_TO_PRODUCTION_UNIT_TYPE: dict[ExperimentUnitType, UnitType] = {
    ExperimentUnitType.INDIVIDUAL_RESEARCHER: UnitType.RESEARCHER,
    ExperimentUnitType.TEAM: UnitType.TEAM,
    ExperimentUnitType.LABORATORY: UnitType.LAB,
}

_COLLABORATORS = ("Alex Rivera", "Jordan Patel", "Morgan Lee", "Taylor Kim", "Sam Osei")


def _trace_from_blueprint(
    blueprint: dict, unit_id: str, index: int, year: int, role: ContributionRole | None = None
) -> EvidenceTrace:
    return EvidenceTrace(
        id=f"trace-dev-{unit_id.split(':')[-1]}-{index:03d}",
        unit_id=unit_id,
        trace_type=blueprint["trace_type"],
        title=str(blueprint["title"]),
        description=str(blueprint.get("description", "")),
        source_kind=SourceKind.SYNTHETIC,
        source_name="KDAA Paper B development generator",
        source_uri=f"synthetic-dev://{unit_id}/{index}",
        event_date=date(year, ((index * 3) % 12) + 1, 1),
        authors_or_contributors=[_COLLABORATORS[index % len(_COLLABORATORS)]],
        affiliations=["Synthetic Research Institute"],
        keywords=list(blueprint.get("keywords", [])),
        contribution_role=role if role is not None else blueprint.get("role", ContributionRole.UNKNOWN),
        outcome_signals={"synthetic": True, "completed": True, "reuse_count": index % 4},
        license="CC0-1.0",
        raw={},
    )


def _select_templates(case_index: int, domain_breadth: DomainBreadth) -> list[SyntheticAssetTemplate]:
    n = len(_TEMPLATE_KEYS)
    primary_key = _TEMPLATE_KEYS[case_index % n]
    keys = [primary_key]
    if domain_breadth == DomainBreadth.INTERDISCIPLINARY:
        keys.append(_TEMPLATE_KEYS[(case_index + n // 2 + 1) % n])
    return [ASSET_TEMPLATES[key] for key in keys]


@dataclass(frozen=True)
class DevelopmentCase:
    """One development-stage case: inference-safe evidence, opportunity catalog, and
    physically separate hidden truth. Only ``evidence_bundle`` and ``opportunity_catalog``
    may ever be handed to a comparator; ``truth`` is scorer-only.
    """

    manifest: CaseManifest
    evidence_bundle: UnitBundle
    truth: TruthBundle
    opportunity_catalog: tuple[OpportunityCandidate, ...]


def generate_development_case(case_index: int, *, ontology: Ontology | None = None) -> DevelopmentCase:
    """Deterministically generate one development case from its integer index.

    Design cell (unit_type, evidence_density, domain_breadth, attribution_regime,
    ownership) cycles through the available values by index so a development run of
    N>=60 covers every combination at least once, without claiming this is the frozen
    final factorial design (Freeze Section 9.2).
    """
    ontology = ontology or Ontology.default()

    unit_type = _UNIT_TYPE_CYCLE[case_index % len(_UNIT_TYPE_CYCLE)]
    evidence_density = EvidenceDensity.DENSE if case_index % 2 == 0 else EvidenceDensity.SPARSE
    domain_breadth = (
        DomainBreadth.INTERDISCIPLINARY if case_index % 3 == 0 else DomainBreadth.SINGLE_DOMAIN
    )
    attribution_regime = (
        AttributionRegime.CLEAR_INDIVIDUAL
        if case_index % 3 == 0
        else AttributionRegime.SHARED_COLLECTIVE
        if case_index % 3 == 1
        else AttributionRegime.UNKNOWN_AMBIGUOUS
    )
    ownership = _OWNERSHIP_CYCLE[case_index % len(_OWNERSHIP_CYCLE)]
    is_stale = case_index % 4 == 0  # ~1/4 of cases exercise a stale/current truth atom
    has_duplicate = case_index % 5 == 0  # ~1/5 of cases include a duplicate trace

    case_id = f"dev-{case_index:04d}"
    unit_id = f"synthetic-dev:{case_id}"
    unit = FocalUnit(
        id=unit_id,
        name=f"Development Unit {case_index:04d}",
        unit_type=_EVAL_TO_PRODUCTION_UNIT_TYPE[unit_type],
        institution="Synthetic Research Institute",
        description="Development-stage synthetic focal unit for Paper B Checkpoint A.",
        boundary_notes="Generated for development-stage evaluation-machinery calibration only.",
        is_synthetic=True,
    )

    templates = _select_templates(case_index, domain_breadth)
    true_concept_keys: set[str] = set()
    traces: list[EvidenceTrace] = []
    concept_supporting_traces: dict[str, list[str]] = {}
    trace_idx = 1
    stale_applied = False
    base_year = 2019 + (case_index % 6)

    for template_idx, template in enumerate(templates):
        primary_keys = list(template.concepts[: 3 if evidence_density == EvidenceDensity.SPARSE else 4])
        for key in primary_keys:
            true_concept_keys.add(key)
            concept_supporting_traces.setdefault(key, [])

        blueprints = list(template.trace_blueprints)
        if evidence_density == EvidenceDensity.SPARSE:
            blueprints = blueprints[:1]
        for blueprint in blueprints:
            year = base_year + template_idx
            if is_stale and not stale_applied:
                year = base_year - 9  # far enough before as_of_date to be unambiguously stale
                stale_applied = True
            role = (
                ContributionRole.LEAD
                if attribution_regime == AttributionRegime.CLEAR_INDIVIDUAL
                else ContributionRole.CONTRIBUTOR
                if attribution_regime == AttributionRegime.SHARED_COLLECTIVE
                else ContributionRole.UNKNOWN
            )
            trace = _trace_from_blueprint(blueprint, unit_id, trace_idx, year, role=role)
            traces.append(trace)
            for key in template.concepts:
                if key in true_concept_keys:
                    concept_supporting_traces[key].append(trace.id)
            trace_idx += 1

    if has_duplicate and traces:
        duplicate = traces[0].model_copy(update={"id": f"{traces[0].id}-dup"})
        traces.append(duplicate)

    # Always add one irrelevant/noise trace (evidence_density does not remove this --
    # every case exercises "irrelevant traces" per the Checkpoint A requirements).
    noise_blueprint = NOISE_BLUEPRINTS[case_index % len(NOISE_BLUEPRINTS)]
    traces.append(_trace_from_blueprint(noise_blueprint, unit_id, trace_idx, base_year, role=ContributionRole.PARTICIPANT))

    evidence_bundle = UnitBundle(unit=unit, traces=traces)

    stale_key = None
    if is_stale and true_concept_keys:
        stale_key = sorted(true_concept_keys)[0]

    asset_concepts = []
    for key in sorted(true_concept_keys):
        definition = ontology.concepts.get(key)
        label = definition.label if definition else key.replace("_", " ").title()
        aliases = list(definition.terms[:2]) if definition else []
        asset_concepts.append(
            TrueAssetConcept(
                concept_id=key,
                canonical_label=label,
                aliases=aliases,
                ownership_state=ownership,
                supporting_trace_ids=concept_supporting_traces.get(key, []),
                is_current=key != stale_key,
            )
        )

    opportunity_relevance = [
        TrueOpportunityRelevance(
            opportunity_id=candidate.opportunity_id,
            relevance_grade=compute_relevance_grade(true_concept_keys, candidate.opportunity_id),
        )
        for candidate in DEV_OPPORTUNITY_CATALOG
    ]

    truth = TruthBundle(
        case_id=case_id,
        asset_concepts=asset_concepts,
        opportunity_relevance=opportunity_relevance,
    )

    manifest = CaseManifest(
        case_id=case_id,
        is_challenge_case=False,
        unit_type=unit_type,
        evidence_density=evidence_density,
        domain_breadth=domain_breadth,
        attribution_regime=attribution_regime,
        seed=case_index,
        development_case=True,
        notes=(
            f"has_duplicate={has_duplicate}; is_stale={is_stale}; "
            f"templates={[t.key for t in templates]}"
        ),
    )
    return DevelopmentCase(
        manifest=manifest,
        evidence_bundle=evidence_bundle,
        truth=truth,
        opportunity_catalog=DEV_OPPORTUNITY_CATALOG,
    )


def generate_development_set(n_cases: int = 60, *, ontology: Ontology | None = None) -> list[DevelopmentCase]:
    """Generate ``n_cases`` development cases deterministically (index-driven, no RNG)."""
    ontology = ontology or Ontology.default()
    return [generate_development_case(i, ontology=ontology) for i in range(n_cases)]
