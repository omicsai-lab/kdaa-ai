"""Final Paper B N=240 case generation: core factorial set (180) and challenge set (60).

Implements, and only implements, the machinery frozen in
``configs/paper_b/final_experiment_lock.yaml`` (``final_dataset``) and
``docs/paper_b_kbs_claims_evaluation_freeze.md`` Section 9.2. Importing this module never
creates a file or directory -- generation is pure, deterministic, in-memory case
construction. ``scripts/generate_paper_b_final_cases.py`` is the separate, human-run CLI
that writes the frozen dataset to disk; nothing in this module calls it.

Deliberately does not import or reuse ``dev_cases.py``: keeping final and development
generation fully independent means a future change to one cannot silently affect the
other's already-validated behavior (development results are frozen record, per
``docs/protocol_deviations.md`` DD-06). The two modules share the same *content* source
(``kdaa.ingestion.synthetic.ASSET_TEMPLATES``/``NOISE_BLUEPRINTS``) -- an already-accepted
pattern per ``dev_cases.py``'s own docstring -- but never share code.

Truth/evidence separation follows the same WP1 architecture ``dev_cases.py`` established:
every ``FinalCase.truth`` is a physically separate object from ``evidence_bundle``, never
embedded in ``UnitBundle.metadata``, and this module is truth-authorized (like
``dev_cases.py``, it may import ``opportunity_truth``) but is not itself an inference
boundary module -- see ``boundary.INFERENCE_BOUNDARY_PREFIXES``, which this module's
namespace (``kdaa.evaluation.paper_b``, not ``...paper_b.adapters``) is outside of.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from itertools import product

from kdaa.ingestion.synthetic import ASSET_TEMPLATES, NOISE_BLUEPRINTS, SyntheticAssetTemplate
from kdaa.models import (
    ContributionRole,
    EvidenceTrace,
    FocalUnit,
    SourceKind,
    TraceType,
    UnitBundle,
    UnitType,
)
from kdaa.ontology import Ontology

from .final_opportunities import _ARCHETYPE_TEMPLATES, build_case_opportunity_catalog
from .opportunity_truth import compute_relevance_grade
from .schemas import (
    AttributionRegime,
    CaseManifest,
    ChallengeCategory,
    DomainBreadth,
    EvidenceDensity,
    ExperimentUnitType,
    OpportunityCandidate,
    OwnershipLabel,
)
from .truth import TrueAssetConcept, TrueOpportunityRelevance, TruthBundle

_TEMPLATE_KEYS: tuple[str, ...] = tuple(sorted(ASSET_TEMPLATES))
_OPPORTUNITY_IDS: tuple[str, ...] = tuple(opportunity_id for opportunity_id, _, _ in _ARCHETYPE_TEMPLATES)

_EVAL_TO_PRODUCTION_UNIT_TYPE: dict[ExperimentUnitType, UnitType] = {
    ExperimentUnitType.INDIVIDUAL_RESEARCHER: UnitType.RESEARCHER,
    ExperimentUnitType.TEAM: UnitType.TEAM,
    ExperimentUnitType.LABORATORY: UnitType.LAB,
}

# Attribution regime (visible manifest coordinate, Freeze Section 9.2) determines hidden
# ownership truth and the contribution role recorded on primary-template traces by direct
# semantic correspondence -- clear/individual attribution IS focal-unit ownership with a
# lead role, etc. -- rather than an invented, separately-seeded mapping.
_ATTRIBUTION_TO_OWNERSHIP: dict[AttributionRegime, OwnershipLabel] = {
    AttributionRegime.CLEAR_INDIVIDUAL: OwnershipLabel.FOCAL_UNIT,
    AttributionRegime.SHARED_COLLECTIVE: OwnershipLabel.SHARED,
    AttributionRegime.UNKNOWN_AMBIGUOUS: OwnershipLabel.UNRESOLVED,
}
_ATTRIBUTION_TO_ROLE: dict[AttributionRegime, ContributionRole] = {
    AttributionRegime.CLEAR_INDIVIDUAL: ContributionRole.LEAD,
    AttributionRegime.SHARED_COLLECTIVE: ContributionRole.CONTRIBUTOR,
    AttributionRegime.UNKNOWN_AMBIGUOUS: ContributionRole.UNKNOWN,
}

_COLLABORATORS = ("Alex Rivera", "Jordan Patel", "Morgan Lee", "Taylor Kim", "Sam Osei", "Riley Chen", "Casey Nguyen")

# EvidenceTrace.observed_at defaults to a wall-clock datetime.now() factory (kdaa.models
# utc_now), which would make every regeneration of "the same" case non-deterministic
# (discovered while validating this checkpoint's determinism requirement -- see
# tests/paper_b/test_final_cases.py::test_generation_is_byte_for_byte_deterministic).
# Every final-case trace pins it to this fixed constant instead of the default factory.
_GENERATION_OBSERVED_AT = datetime(2026, 6, 1, tzinfo=UTC)

# Challenge Category 1 (ontology shift / unseen synonyms): held-out phrases that never
# occur in any registered kdaa.resources.ontology.yaml `terms` entry for ANY concept
# (verified by tests/paper_b/test_final_cases.py::test_unseen_synonyms_are_genuinely_unseen).
# A comparator must generalize past memorized ontology vocabulary to recover these concepts.
_UNSEEN_SYNONYMS: dict[str, str] = {
    "agentic_ai": "self-directing orchestration of specialized software helpers",
    "bioinformatics": "computational analysis of biological sequence archives",
    "software_engineering": "disciplined production-grade code craftsmanship",
    "genomics": "large-scale hereditary-code profiling",
    "reproducible_research": "fully repeatable analytical workflow discipline",
    "teaching_curriculum": "structured learner-enablement program design",
}
_SYNONYM_SHIFT_TEMPLATE_CYCLE: tuple[str, ...] = (
    "agentic_omics_workflows",
    "research_computing_support",
    "ai_curriculum_design",
    "multiomics_integration",
)


@dataclass(frozen=True)
class FinalCase:
    """One final-study case: inference-safe evidence, case-specific visible opportunity
    catalog, and physically separate hidden truth. Only ``evidence_bundle`` and
    ``opportunity_catalog`` may ever be handed to a comparator; ``truth`` is scorer-only."""

    manifest: CaseManifest
    evidence_bundle: UnitBundle
    truth: TruthBundle
    opportunity_catalog: tuple[OpportunityCandidate, ...]


@dataclass(frozen=True)
class FinalDataset:
    core_cases: tuple[FinalCase, ...]
    challenge_cases: tuple[FinalCase, ...]

    @property
    def total_n(self) -> int:
        return len(self.core_cases) + len(self.challenge_cases)


# --------------------------------------------------------------------------------------
# Shared trace-construction helpers (final-only; never imported by dev_cases.py)
# --------------------------------------------------------------------------------------


def _blueprint_to_trace(
    blueprint: dict, unit_id: str, index: int, year: int, *, role: ContributionRole, id_namespace: str, sensitive: bool = False
) -> EvidenceTrace:
    return EvidenceTrace(
        id=f"trace-final-{id_namespace}-{unit_id.split(':')[-1]}-{index:03d}",
        unit_id=unit_id,
        trace_type=blueprint["trace_type"],
        title=str(blueprint["title"]),
        description=str(blueprint.get("description", "")),
        source_kind=SourceKind.SYNTHETIC,
        source_name="KDAA Paper B final generator",
        source_uri=f"synthetic-final-{id_namespace}://{unit_id}/{index}",
        source_record_id=blueprint.get("source_record_id"),
        observed_at=_GENERATION_OBSERVED_AT,
        event_date=date(year, ((index * 3) % 12) + 1, 1),
        authors_or_contributors=blueprint.get("authors_or_contributors") or [_COLLABORATORS[index % len(_COLLABORATORS)]],
        affiliations=blueprint.get("affiliations") or ["Synthetic Research Institute"],
        keywords=list(blueprint.get("keywords", [])),
        contribution_role=blueprint.get("role", role),
        outcome_signals={"synthetic": True, "completed": True, "reuse_count": index % 4},
        license="CC0-1.0",
        sensitive=sensitive,
        raw={},
    )


def _apply_synonym_shift(blueprint: dict, concept_keys: tuple[str, ...], ontology: Ontology) -> dict:
    """Replace every registered-term mention of a shiftable concept in ``blueprint`` with
    its held-out synonym. Only touches concepts that both appear in ``concept_keys`` and
    have an entry in ``_UNSEEN_SYNONYMS``; every other concept's vocabulary is untouched."""
    title = str(blueprint["title"])
    description = str(blueprint.get("description", ""))
    keywords = list(blueprint.get("keywords", []))
    for key in concept_keys:
        synonym = _UNSEEN_SYNONYMS.get(key)
        definition = ontology.concepts.get(key)
        if synonym is None or definition is None:
            continue
        for term in definition.terms:
            pattern = re.compile(rf"(?<![a-zA-Z0-9]){re.escape(term)}(?![a-zA-Z0-9])", re.I)
            title = pattern.sub(synonym, title)
            description = pattern.sub(synonym, description)
        term_set = {t.lower() for t in definition.terms}
        keywords = [kw for kw in keywords if kw.lower() not in term_set]
        keywords.append(synonym)
    result = dict(blueprint)
    result["title"] = title
    result["description"] = description
    result["keywords"] = keywords
    return result


def _generate_template_traces(
    *,
    templates: list[SyntheticAssetTemplate],
    evidence_density: EvidenceDensity,
    id_namespace: str,
    unit_id: str,
    role: ContributionRole,
    base_year: int,
    is_stale: bool,
    ontology: Ontology,
    synonym_shift: bool = False,
    max_primary_keys_override: int | None = None,
    max_blueprints_override: int | None = None,
) -> tuple[list[EvidenceTrace], set[str], dict[str, list[str]], str | None]:
    """Core per-template trace-and-truth loop shared by the core and challenge generators.
    Mirrors the proven structure of ``dev_cases.generate_development_case``'s inner loop,
    reimplemented independently here (see module docstring for why)."""
    true_concept_keys: set[str] = set()
    concept_supporting_traces: dict[str, list[str]] = {}
    traces: list[EvidenceTrace] = []
    trace_idx = 1
    stale_applied = False

    for template_idx, template in enumerate(templates):
        n_primary = 3 if evidence_density == EvidenceDensity.SPARSE else 4
        if max_primary_keys_override is not None:
            n_primary = max_primary_keys_override
        primary_keys = list(template.concepts[:n_primary])
        for key in primary_keys:
            true_concept_keys.add(key)
            concept_supporting_traces.setdefault(key, [])

        blueprints = list(template.trace_blueprints)
        if evidence_density == EvidenceDensity.SPARSE:
            blueprints = blueprints[:1]
        if max_blueprints_override is not None:
            blueprints = blueprints[:max_blueprints_override]

        for blueprint in blueprints:
            year = base_year + template_idx
            if is_stale and not stale_applied:
                year = base_year - 9
                stale_applied = True
            effective_blueprint = (
                _apply_synonym_shift(blueprint, template.concepts, ontology) if synonym_shift else blueprint
            )
            trace = _blueprint_to_trace(effective_blueprint, unit_id, trace_idx, year, role=role, id_namespace=id_namespace)
            traces.append(trace)
            for key in template.concepts:
                if key in true_concept_keys:
                    concept_supporting_traces[key].append(trace.id)
            trace_idx += 1

    stale_key = sorted(true_concept_keys)[0] if (is_stale and true_concept_keys) else None
    return traces, true_concept_keys, concept_supporting_traces, stale_key


def _build_true_asset_concepts(
    true_concept_keys: set[str],
    concept_supporting_traces: dict[str, list[str]],
    *,
    ontology: Ontology,
    ownership: OwnershipLabel,
    stale_key: str | None,
    contradicting_by_key: dict[str, list[str]] | None = None,
) -> list[TrueAssetConcept]:
    contradicting_by_key = contradicting_by_key or {}
    result = []
    for key in sorted(true_concept_keys):
        definition = ontology.concepts.get(key)
        label = definition.label if definition else key.replace("_", " ").title()
        aliases = list(definition.terms[:2]) if definition else []
        result.append(
            TrueAssetConcept(
                concept_id=key,
                canonical_label=label,
                aliases=aliases,
                ownership_state=ownership,
                supporting_trace_ids=concept_supporting_traces.get(key, []),
                contradicting_trace_ids=contradicting_by_key.get(key, []),
                is_current=key != stale_key,
            )
        )
    return result


def _opportunity_relevance(true_concept_keys: set[str]) -> list[TrueOpportunityRelevance]:
    return [
        TrueOpportunityRelevance(opportunity_id=opp_id, relevance_grade=compute_relevance_grade(true_concept_keys, opp_id))
        for opp_id in _OPPORTUNITY_IDS
    ]


# --------------------------------------------------------------------------------------
# Core factorial set: N=180 (3 unit_type x 2 evidence_density x 2 domain_breadth x
# 3 attribution_regime x 5 replicates)
# --------------------------------------------------------------------------------------

_CORE_REPLICATES = 5


def _core_factorial_cells() -> list[tuple[ExperimentUnitType, EvidenceDensity, DomainBreadth, AttributionRegime, int]]:
    """Exact, exhaustive enumeration of the frozen factorial design -- 3*2*2*3*5=180 cells,
    in a fixed, deterministic order. Never sampled or cycled: every combination appears
    exactly once per replicate."""
    cells = []
    for unit_type, density, domain, regime in product(
        tuple(ExperimentUnitType), tuple(EvidenceDensity), tuple(DomainBreadth), tuple(AttributionRegime)
    ):
        for replicate in range(_CORE_REPLICATES):
            cells.append((unit_type, density, domain, regime, replicate))
    return cells


_CORE_CELLS = _core_factorial_cells()
CORE_N = len(_CORE_CELLS)


def _select_core_templates(flat_index: int, domain_breadth: DomainBreadth) -> list[str]:
    n = len(_TEMPLATE_KEYS)
    primary = _TEMPLATE_KEYS[flat_index % n]
    keys = [primary]
    if domain_breadth == DomainBreadth.INTERDISCIPLINARY:
        keys.append(_TEMPLATE_KEYS[(flat_index + n // 2 + 1) % n])
    return keys


def generate_final_core_case(flat_index: int, *, ontology: Ontology | None = None) -> FinalCase:
    """Deterministically generate final core-set case ``flat_index`` (0..179). The four
    factorial fields come exactly from the cell at ``flat_index`` in the frozen enumeration
    order (``_core_factorial_cells``); template/stale/duplicate content variety is driven
    by ``flat_index`` itself, so every one of the 180 cases is distinct."""
    ontology = ontology or Ontology.default()
    if not 0 <= flat_index < CORE_N:
        raise ValueError(f"flat_index must be in [0, {CORE_N}); got {flat_index}")
    unit_type, evidence_density, domain_breadth, attribution_regime, replicate = _CORE_CELLS[flat_index]

    case_id = f"final-core-{flat_index:04d}"
    unit_id = f"synthetic-final-core:{case_id}"
    ownership = _ATTRIBUTION_TO_OWNERSHIP[attribution_regime]
    role = _ATTRIBUTION_TO_ROLE[attribution_regime]

    template_keys = _select_core_templates(flat_index, domain_breadth)
    templates = [ASSET_TEMPLATES[key] for key in template_keys]
    is_stale = flat_index % 4 == 0
    has_duplicate = flat_index % 5 == 0
    base_year = 2015 + (flat_index % 9)

    traces, true_concept_keys, concept_supporting_traces, stale_key = _generate_template_traces(
        templates=templates,
        evidence_density=evidence_density,
        id_namespace="core",
        unit_id=unit_id,
        role=role,
        base_year=base_year,
        is_stale=is_stale,
        ontology=ontology,
    )
    if has_duplicate and traces:
        traces.append(traces[0].model_copy(update={"id": f"{traces[0].id}-dup"}))

    noise_blueprint = NOISE_BLUEPRINTS[flat_index % len(NOISE_BLUEPRINTS)]
    traces.append(
        _blueprint_to_trace(noise_blueprint, unit_id, len(traces) + 1, base_year, role=ContributionRole.PARTICIPANT, id_namespace="core")
    )

    unit = FocalUnit(
        id=unit_id,
        name=f"Final Core Unit {flat_index:04d}",
        unit_type=_EVAL_TO_PRODUCTION_UNIT_TYPE[unit_type],
        institution="Synthetic Research Institute",
        description="Final-study synthetic focal unit (core factorial set). Synthetic only.",
        boundary_notes="Generated for the frozen final Paper B evaluation.",
        is_synthetic=True,
    )
    evidence_bundle = UnitBundle(unit=unit, traces=traces)

    asset_concepts = _build_true_asset_concepts(
        true_concept_keys, concept_supporting_traces, ontology=ontology, ownership=ownership, stale_key=stale_key
    )
    truth = TruthBundle(
        case_id=case_id, asset_concepts=asset_concepts, opportunity_relevance=_opportunity_relevance(true_concept_keys)
    )
    manifest = CaseManifest(
        case_id=case_id,
        is_challenge_case=False,
        unit_type=unit_type,
        evidence_density=evidence_density,
        domain_breadth=domain_breadth,
        attribution_regime=attribution_regime,
        seed=flat_index,
        development_case=False,
        notes=f"core factorial cell replicate={replicate}; templates={template_keys}; has_duplicate={has_duplicate}; is_stale={is_stale}",
    )
    return FinalCase(
        manifest=manifest,
        evidence_bundle=evidence_bundle,
        truth=truth,
        opportunity_catalog=build_case_opportunity_catalog(evidence_bundle, ontology=ontology),
    )


def generate_final_core_set(*, ontology: Ontology | None = None) -> list[FinalCase]:
    ontology = ontology or Ontology.default()
    return [generate_final_core_case(i, ontology=ontology) for i in range(CORE_N)]


# --------------------------------------------------------------------------------------
# Challenge set: N=60 (10 categories x 6 cases)
# --------------------------------------------------------------------------------------

_CHALLENGE_CATEGORIES: tuple[ChallengeCategory, ...] = tuple(ChallengeCategory)
_CHALLENGE_REPLICATES = 6
CHALLENGE_N = len(_CHALLENGE_CATEGORIES) * _CHALLENGE_REPLICATES


def _build_challenge_case(
    *,
    case_id: str,
    category: ChallengeCategory,
    template_keys: list[str],
    unit_type: ExperimentUnitType,
    evidence_density: EvidenceDensity,
    domain_breadth: DomainBreadth,
    attribution_regime: AttributionRegime,
    replicate: int,
    ontology: Ontology,
    synonym_shift: bool = False,
    max_primary_keys_override: int | None = None,
    max_blueprints_override: int | None = None,
    force_stale: bool = False,
    extra_trace_specs: list[dict] | None = None,
    contradicting_concept_key: str | None = None,
    sensitive_extra_trace_index: int | None = None,
    primary_trace_source_record_id: str | None = None,
) -> FinalCase:
    """Shared builder for all 10 challenge categories -- see the ten
    ``generate_final_challenge_case`` dispatch entries below for what each category passes."""
    unit_id = f"synthetic-final-challenge:{case_id}"
    ownership = _ATTRIBUTION_TO_OWNERSHIP[attribution_regime]
    role = _ATTRIBUTION_TO_ROLE[attribution_regime]
    templates = [ASSET_TEMPLATES[key] for key in template_keys]
    base_year = 2015 + (replicate % 9)

    traces, true_concept_keys, concept_supporting_traces, stale_key = _generate_template_traces(
        templates=templates,
        evidence_density=evidence_density,
        id_namespace="challenge",
        unit_id=unit_id,
        role=role,
        base_year=base_year,
        is_stale=force_stale,
        ontology=ontology,
        synonym_shift=synonym_shift,
        max_primary_keys_override=max_primary_keys_override,
        max_blueprints_override=max_blueprints_override,
    )

    if primary_trace_source_record_id and traces:
        traces[0] = traces[0].model_copy(update={"source_record_id": primary_trace_source_record_id})

    extra_ids: list[str] = []
    if extra_trace_specs:
        offset = len(traces) + 1
        for i, spec in enumerate(extra_trace_specs):
            sensitive = sensitive_extra_trace_index == i
            extra_trace = _blueprint_to_trace(
                spec, unit_id, offset + i, base_year, role=spec.get("role", ContributionRole.PARTICIPANT), id_namespace="challenge", sensitive=sensitive
            )
            traces.append(extra_trace)
            extra_ids.append(extra_trace.id)

    contradicting_by_key: dict[str, list[str]] = {}
    if contradicting_concept_key and extra_ids:
        contradicting_by_key[contradicting_concept_key] = [extra_ids[-1]]

    sensitive_trace_ids = (
        [extra_ids[sensitive_extra_trace_index]]
        if sensitive_extra_trace_index is not None and sensitive_extra_trace_index < len(extra_ids)
        else []
    )

    unit = FocalUnit(
        id=unit_id,
        name=f"Final Challenge Unit {case_id}",
        unit_type=_EVAL_TO_PRODUCTION_UNIT_TYPE[unit_type],
        institution="Synthetic Research Institute",
        description=f"Final-study synthetic focal unit (challenge category: {category.value}). Synthetic only.",
        boundary_notes="Generated for the frozen final Paper B evaluation.",
        is_synthetic=True,
    )
    evidence_bundle = UnitBundle(unit=unit, traces=traces)

    asset_concepts = _build_true_asset_concepts(
        true_concept_keys,
        concept_supporting_traces,
        ontology=ontology,
        ownership=ownership,
        stale_key=stale_key,
        contradicting_by_key=contradicting_by_key,
    )
    truth = TruthBundle(
        case_id=case_id,
        asset_concepts=asset_concepts,
        opportunity_relevance=_opportunity_relevance(true_concept_keys),
        sensitive_trace_ids=sensitive_trace_ids,
        challenge_category=category,
    )
    manifest = CaseManifest(
        case_id=case_id,
        is_challenge_case=True,
        challenge_category=category,
        unit_type=unit_type,
        evidence_density=evidence_density,
        domain_breadth=domain_breadth,
        attribution_regime=attribution_regime,
        seed=replicate,
        development_case=False,
        notes=f"challenge category={category.value}; templates={template_keys}",
    )
    return FinalCase(
        manifest=manifest,
        evidence_bundle=evidence_bundle,
        truth=truth,
        opportunity_catalog=build_case_opportunity_catalog(evidence_bundle, ontology=ontology),
    )


_UNIT_TYPE_CYCLE = tuple(ExperimentUnitType)


def _build_ontology_shift(case_id: str, replicate: int, ontology: Ontology) -> FinalCase:
    template_key = _SYNONYM_SHIFT_TEMPLATE_CYCLE[replicate % len(_SYNONYM_SHIFT_TEMPLATE_CYCLE)]
    return _build_challenge_case(
        case_id=case_id,
        category=ChallengeCategory.ONTOLOGY_SHIFT_AND_UNSEEN_SYNONYMS,
        template_keys=[template_key],
        unit_type=_UNIT_TYPE_CYCLE[replicate % 3],
        evidence_density=EvidenceDensity.DENSE,
        domain_breadth=DomainBreadth.SINGLE_DOMAIN,
        attribution_regime=AttributionRegime.CLEAR_INDIVIDUAL,
        replicate=replicate,
        ontology=ontology,
        synonym_shift=True,
    )


def _build_interdisciplinary_composite(case_id: str, replicate: int, ontology: Ontology) -> FinalCase:
    n = len(_TEMPLATE_KEYS)
    keys = [_TEMPLATE_KEYS[replicate % n], _TEMPLATE_KEYS[(replicate + 2) % n], _TEMPLATE_KEYS[(replicate + 4) % n]]
    return _build_challenge_case(
        case_id=case_id,
        category=ChallengeCategory.INTERDISCIPLINARY_COMPOSITE_ASSETS,
        template_keys=keys,
        unit_type=_UNIT_TYPE_CYCLE[replicate % 3],
        evidence_density=EvidenceDensity.DENSE,
        domain_breadth=DomainBreadth.INTERDISCIPLINARY,
        attribution_regime=AttributionRegime.SHARED_COLLECTIVE,
        replicate=replicate,
        ontology=ontology,
    )


_PRESTIGE_DECOYS: tuple[dict, ...] = (
    {
        "trace_type": TraceType.AWARD,
        "title": "Named to a global \"40 under 40\" innovators list",
        "description": "Public recognition based on nomination; no independently verifiable deliverable.",
        "keywords": [],
        "role": ContributionRole.PARTICIPANT,
    },
    {
        "trace_type": TraceType.TALK,
        "title": "Keynote speaker at a flagship industry summit",
        "description": "High-visibility speaking slot; the talk description contains no documented capability.",
        "keywords": [],
        "role": ContributionRole.PARTICIPANT,
    },
)


def _build_prestige_decoys(case_id: str, replicate: int, ontology: Ontology) -> FinalCase:
    return _build_challenge_case(
        case_id=case_id,
        category=ChallengeCategory.TRACE_AS_ASSET_AND_PRESTIGE_DECOYS,
        template_keys=[_TEMPLATE_KEYS[replicate % len(_TEMPLATE_KEYS)]],
        unit_type=_UNIT_TYPE_CYCLE[replicate % 3],
        evidence_density=EvidenceDensity.DENSE,
        domain_breadth=DomainBreadth.SINGLE_DOMAIN,
        attribution_regime=AttributionRegime.CLEAR_INDIVIDUAL,
        replicate=replicate,
        ontology=ontology,
        extra_trace_specs=[_PRESTIGE_DECOYS[replicate % len(_PRESTIGE_DECOYS)]],
    )


def _build_semantic_duplicates(case_id: str, replicate: int, ontology: Ontology) -> FinalCase:
    template_key = _TEMPLATE_KEYS[replicate % len(_TEMPLATE_KEYS)]
    primary_blueprint = ASSET_TEMPLATES[template_key].trace_blueprints[0]
    shared_source_id = f"src-{case_id}"
    paraphrase = {
        "trace_type": primary_blueprint["trace_type"],
        "title": f"Companion writeup: {primary_blueprint['title']}",
        "description": f"A differently-worded account of the same underlying record. {primary_blueprint.get('description', '')}",
        "keywords": list(primary_blueprint.get("keywords", [])),
        "role": primary_blueprint.get("role", ContributionRole.CONTRIBUTOR),
        "source_record_id": shared_source_id,
    }
    return _build_challenge_case(
        case_id=case_id,
        category=ChallengeCategory.SEMANTIC_DUPLICATES_AND_SOURCE_DEPENDENCE,
        template_keys=[template_key],
        unit_type=_UNIT_TYPE_CYCLE[replicate % 3],
        evidence_density=EvidenceDensity.DENSE,
        domain_breadth=DomainBreadth.SINGLE_DOMAIN,
        attribution_regime=AttributionRegime.CLEAR_INDIVIDUAL,
        replicate=replicate,
        ontology=ontology,
        extra_trace_specs=[paraphrase],
        primary_trace_source_record_id=shared_source_id,
    )


def _build_stale_contradiction(case_id: str, replicate: int, ontology: Ontology) -> FinalCase:
    template_key = _TEMPLATE_KEYS[replicate % len(_TEMPLATE_KEYS)]
    primary_concept = sorted(ASSET_TEMPLATES[template_key].concepts[:4])[0]
    contradiction = {
        "trace_type": TraceType.PUBLICATION,
        "title": "Follow-up analysis revises the earlier finding",
        "description": "A later record reports that the earlier approach was superseded and should not be treated as current.",
        "keywords": [],
        "role": ContributionRole.CONTRIBUTOR,
    }
    return _build_challenge_case(
        case_id=case_id,
        category=ChallengeCategory.STALE_CURRENT_CONFLICT_AND_CONTRADICTION,
        template_keys=[template_key],
        unit_type=_UNIT_TYPE_CYCLE[replicate % 3],
        evidence_density=EvidenceDensity.DENSE,
        domain_breadth=DomainBreadth.SINGLE_DOMAIN,
        attribution_regime=AttributionRegime.CLEAR_INDIVIDUAL,
        replicate=replicate,
        ontology=ontology,
        force_stale=True,
        extra_trace_specs=[contradiction],
        contradicting_concept_key=primary_concept,
    )


def _build_collaborator_heavy(case_id: str, replicate: int, ontology: Ontology) -> FinalCase:
    n = len(_TEMPLATE_KEYS)
    keys = [_TEMPLATE_KEYS[replicate % n], _TEMPLATE_KEYS[(replicate + 3) % n]]
    extras = [
        {
            "trace_type": TraceType.COLLABORATION,
            "title": f"Collective working session #{i + 1}",
            "description": "Membership record without documented individual deliverable or clear attribution.",
            "keywords": [],
            "role": ContributionRole.UNKNOWN,
            "authors_or_contributors": [_COLLABORATORS[(replicate + i) % len(_COLLABORATORS)], _COLLABORATORS[(replicate + i + 1) % len(_COLLABORATORS)]],
        }
        for i in range(3)
    ]
    return _build_challenge_case(
        case_id=case_id,
        category=ChallengeCategory.COLLABORATOR_HEAVY_AND_UNKNOWN_ROLES,
        template_keys=keys,
        unit_type=ExperimentUnitType.TEAM,
        evidence_density=EvidenceDensity.DENSE,
        domain_breadth=DomainBreadth.INTERDISCIPLINARY,
        attribution_regime=AttributionRegime.UNKNOWN_AMBIGUOUS,
        replicate=replicate,
        ontology=ontology,
        extra_trace_specs=extras,
    )


def _build_identity_collision(case_id: str, replicate: int, ontology: Ontology) -> FinalCase:
    # Every ASSET_TEMPLATES entry has exactly 3 trace_blueprints, and
    # _generate_template_traces assigns authors by position (trace_idx 1, 2, 3) via
    # _COLLABORATORS[trace_idx % len(_COLLABORATORS)] regardless of which template or
    # replicate is used -- so indices 1-3 are the names that actually appear on this
    # case's primary traces. The colliding name must be one of those for the decoy to be a
    # genuine collision (the same name legitimately used elsewhere in the case), not an
    # unrelated name that happens not to collide with anything.
    colliding_name = _COLLABORATORS[1 + (replicate % 3)]
    unrelated_template = ASSET_TEMPLATES[_TEMPLATE_KEYS[(replicate + 3) % len(_TEMPLATE_KEYS)]]
    decoy = {
        "trace_type": TraceType.PUBLICATION,
        "title": f"Unrelated prior work sharing a name with {colliding_name}",
        "description": f"{unrelated_template.trace_blueprints[0].get('description', '')} A different individual at an unrelated institution, sharing the same name only.",
        "keywords": [],
        "role": ContributionRole.LEAD,
        "authors_or_contributors": [colliding_name],
        "affiliations": ["Unrelated External Institute"],
    }
    return _build_challenge_case(
        case_id=case_id,
        category=ChallengeCategory.IDENTITY_COLLISION_AND_RESOLUTION_ERROR,
        template_keys=[_TEMPLATE_KEYS[replicate % len(_TEMPLATE_KEYS)]],
        unit_type=_UNIT_TYPE_CYCLE[replicate % 3],
        evidence_density=EvidenceDensity.DENSE,
        domain_breadth=DomainBreadth.SINGLE_DOMAIN,
        attribution_regime=AttributionRegime.CLEAR_INDIVIDUAL,
        replicate=replicate,
        ontology=ontology,
        extra_trace_specs=[decoy],
    )


def _build_sparse_missing(case_id: str, replicate: int, ontology: Ontology) -> FinalCase:
    return _build_challenge_case(
        case_id=case_id,
        category=ChallengeCategory.SPARSE_AND_MISSING_SUPPORT,
        template_keys=[_TEMPLATE_KEYS[replicate % len(_TEMPLATE_KEYS)]],
        unit_type=_UNIT_TYPE_CYCLE[replicate % 3],
        evidence_density=EvidenceDensity.SPARSE,
        domain_breadth=DomainBreadth.SINGLE_DOMAIN,
        attribution_regime=AttributionRegime.UNKNOWN_AMBIGUOUS,
        replicate=replicate,
        ontology=ontology,
        max_primary_keys_override=1,
        max_blueprints_override=1,
    )


def _build_noise_and_sensitive(case_id: str, replicate: int, ontology: Ontology) -> FinalCase:
    extras = [dict(NOISE_BLUEPRINTS[i % len(NOISE_BLUEPRINTS)]) for i in range(replicate, replicate + 3)]
    return _build_challenge_case(
        case_id=case_id,
        category=ChallengeCategory.IRRELEVANT_NOISE_AND_SENSITIVE_TRACES,
        template_keys=[_TEMPLATE_KEYS[replicate % len(_TEMPLATE_KEYS)]],
        unit_type=_UNIT_TYPE_CYCLE[replicate % 3],
        evidence_density=EvidenceDensity.DENSE,
        domain_breadth=DomainBreadth.SINGLE_DOMAIN,
        attribution_regime=AttributionRegime.CLEAR_INDIVIDUAL,
        replicate=replicate,
        ontology=ontology,
        extra_trace_specs=extras,
        sensitive_extra_trace_index=0,
    )


def _build_opportunity_reversal(case_id: str, replicate: int, ontology: Ontology) -> FinalCase:
    # research_computing_support carries software_engineering (opp-repository's required
    # concept); ai_curriculum_design carries teaching_curriculum (opp-repository's only
    # disqualifying concept in the frozen, unchanged OPPORTUNITY_REQUIREMENTS table) -- a
    # case that naively looks like a strong repository candidate but is truth-side
    # disqualified. This exercises the existing, frozen disqualifying-concept mechanism; it
    # does not add a new one.
    return _build_challenge_case(
        case_id=case_id,
        category=ChallengeCategory.OPPORTUNITY_CONTEXT_REVERSAL_AND_UNSAFE_DELEGATION,
        template_keys=["research_computing_support", "ai_curriculum_design"],
        unit_type=_UNIT_TYPE_CYCLE[replicate % 3],
        evidence_density=EvidenceDensity.DENSE,
        domain_breadth=DomainBreadth.INTERDISCIPLINARY,
        attribution_regime=AttributionRegime.SHARED_COLLECTIVE,
        replicate=replicate,
        ontology=ontology,
    )


_CHALLENGE_BUILDERS = {
    ChallengeCategory.ONTOLOGY_SHIFT_AND_UNSEEN_SYNONYMS: _build_ontology_shift,
    ChallengeCategory.INTERDISCIPLINARY_COMPOSITE_ASSETS: _build_interdisciplinary_composite,
    ChallengeCategory.TRACE_AS_ASSET_AND_PRESTIGE_DECOYS: _build_prestige_decoys,
    ChallengeCategory.SEMANTIC_DUPLICATES_AND_SOURCE_DEPENDENCE: _build_semantic_duplicates,
    ChallengeCategory.STALE_CURRENT_CONFLICT_AND_CONTRADICTION: _build_stale_contradiction,
    ChallengeCategory.COLLABORATOR_HEAVY_AND_UNKNOWN_ROLES: _build_collaborator_heavy,
    ChallengeCategory.IDENTITY_COLLISION_AND_RESOLUTION_ERROR: _build_identity_collision,
    ChallengeCategory.SPARSE_AND_MISSING_SUPPORT: _build_sparse_missing,
    ChallengeCategory.IRRELEVANT_NOISE_AND_SENSITIVE_TRACES: _build_noise_and_sensitive,
    ChallengeCategory.OPPORTUNITY_CONTEXT_REVERSAL_AND_UNSAFE_DELEGATION: _build_opportunity_reversal,
}


def generate_final_challenge_case(flat_index: int, *, ontology: Ontology | None = None) -> FinalCase:
    """Deterministically generate final challenge-set case ``flat_index`` (0..59): category
    = ``flat_index // 6`` (in ``ChallengeCategory`` declaration order, matching
    ``experiment_lock.yaml``'s ``challenge_categories`` list), replicate = ``flat_index % 6``."""
    ontology = ontology or Ontology.default()
    if not 0 <= flat_index < CHALLENGE_N:
        raise ValueError(f"flat_index must be in [0, {CHALLENGE_N}); got {flat_index}")
    category_index, replicate = divmod(flat_index, _CHALLENGE_REPLICATES)
    category = _CHALLENGE_CATEGORIES[category_index]
    case_id = f"final-challenge-{category_index:02d}-{replicate:02d}"
    builder = _CHALLENGE_BUILDERS[category]
    return builder(case_id, replicate, ontology)


def generate_final_challenge_set(*, ontology: Ontology | None = None) -> list[FinalCase]:
    ontology = ontology or Ontology.default()
    return [generate_final_challenge_case(i, ontology=ontology) for i in range(CHALLENGE_N)]


def generate_final_dataset(*, ontology: Ontology | None = None) -> FinalDataset:
    ontology = ontology or Ontology.default()
    return FinalDataset(
        core_cases=tuple(generate_final_core_set(ontology=ontology)),
        challenge_cases=tuple(generate_final_challenge_set(ontology=ontology)),
    )
