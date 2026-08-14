"""Synthetic focal units and benchmark generator.

Synthetic records are intentionally marked and are suitable only for software
validation, demonstrations, and controlled engineering benchmarks. They are not
empirical evidence for the KDAA theory.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from typing import Any

from kdaa.models import (
    ContributionRole,
    EvidenceTrace,
    FocalUnit,
    SourceKind,
    StrategicGoal,
    TraceType,
    UnitBundle,
    UnitType,
)


@dataclass(frozen=True)
class SyntheticAssetTemplate:
    key: str
    label: str
    concepts: tuple[str, ...]
    trace_blueprints: tuple[dict[str, Any], ...]


ASSET_TEMPLATES: dict[str, SyntheticAssetTemplate] = {
    "agentic_omics_workflows": SyntheticAssetTemplate(
        key="agentic_omics_workflows",
        label="Agentic AI workflows for reproducible omics analysis",
        concepts=(
            "agentic_ai",
            "generative_ai",
            "bioinformatics",
            "transcriptomics",
            "software_engineering",
            "reproducible_research",
        ),
        trace_blueprints=(
            {
                "trace_type": TraceType.PUBLICATION,
                "title": "An agentic framework for reproducible transcriptomic analysis",
                "description": "A peer-reviewed methods paper on multi-agent planning, evidence retrieval, and RNA-seq interpretation.",
                "keywords": ["agentic AI", "RNA-seq", "reproducibility", "bioinformatics"],
                "role": ContributionRole.LEAD,
            },
            {
                "trace_type": TraceType.SOFTWARE,
                "title": "omics-agent-workbench",
                "description": "Dockerized Python application with planner, executor, evidence review, and report generation modules.",
                "keywords": ["Python", "Docker", "LLM", "multi-agent", "bioinformatics"],
                "role": ContributionRole.ORIGINATOR,
            },
            {
                "trace_type": TraceType.PROJECT,
                "title": "Reproducible AI-assisted secondary analysis pilot",
                "description": "Integrated public gene-expression data, pathway analysis, and evidence-grounded synthesis into a repeatable workflow.",
                "keywords": ["gene expression", "workflow automation", "agentic AI"],
                "role": ContributionRole.LEAD,
            },
        ),
    ),
    "causal_clinical_methods": SyntheticAssetTemplate(
        key="causal_clinical_methods",
        label="Causal and statistical methods for clinical studies",
        concepts=("causal_inference", "clinical_trials", "statistical_modeling", "survival_analysis"),
        trace_blueprints=(
            {
                "trace_type": TraceType.PUBLICATION,
                "title": "Causal estimands for heterogeneous treatment effects in clinical studies",
                "description": "Methodological work linking estimands, treatment-effect heterogeneity, and survival outcomes.",
                "keywords": ["causal inference", "clinical trials", "survival analysis", "estimand"],
                "role": ContributionRole.LEAD,
            },
            {
                "trace_type": TraceType.COURSE,
                "title": "AI and causal reasoning for clinical trials",
                "description": "Graduate module covering estimands, audit trails, simulation, and human oversight.",
                "keywords": ["clinical trial", "causal inference", "teaching"],
                "role": ContributionRole.ORIGINATOR,
            },
            {
                "trace_type": TraceType.GRANT,
                "title": "Trustworthy causal AI for secondary clinical-data analysis",
                "description": "Proposal integrating causal models, validation, and governed AI assistance.",
                "keywords": ["causal model", "clinical data", "AI system"],
                "role": ContributionRole.LEAD,
            },
        ),
    ),
    "multiomics_integration": SyntheticAssetTemplate(
        key="multiomics_integration",
        label="Multimodal and multi-omics integration",
        concepts=(
            "multi_omics",
            "genomics",
            "transcriptomics",
            "machine_learning",
            "precision_medicine",
        ),
        trace_blueprints=(
            {
                "trace_type": TraceType.PUBLICATION,
                "title": "Integrating clinical and multi-omics data with attention-based models",
                "description": "Repeated cross-validation and external validation of multimodal prediction models.",
                "keywords": ["multi-omics", "transformer", "precision medicine", "clinical data"],
                "role": ContributionRole.LEAD,
            },
            {
                "trace_type": TraceType.DATASET,
                "title": "Harmonized multi-cohort omics benchmark",
                "description": "Versioned public benchmark with clinical, genomic, and transcriptomic features.",
                "keywords": ["genomics", "transcriptomics", "data harmonization"],
                "role": ContributionRole.ORIGINATOR,
            },
            {
                "trace_type": TraceType.PROTOCOL,
                "title": "Multimodal validation and leakage-control protocol",
                "description": "Reusable protocol for grouped splitting, tuning, and repeated evaluation.",
                "keywords": ["reproducibility", "cross-validation", "multiomics"],
                "role": ContributionRole.ORIGINATOR,
            },
        ),
    ),
    "research_computing_support": SyntheticAssetTemplate(
        key="research_computing_support",
        label="Research computing and productionization capability",
        concepts=("research_computing", "software_engineering", "data_engineering", "reproducible_research"),
        trace_blueprints=(
            {
                "trace_type": TraceType.EMPLOYMENT,
                "title": "Director of research computing support",
                "description": "Led scientific-computing support, cloud deployment, and reproducible workflow design for research groups.",
                "keywords": ["research computing", "cloud computing", "scientific computing"],
                "role": ContributionRole.LEAD,
            },
            {
                "trace_type": TraceType.SOFTWARE,
                "title": "research-workflow-template",
                "description": "Reusable Docker, CI, data-path, and audit-trail template for scientific repositories.",
                "keywords": ["Docker", "continuous integration", "data pipeline", "reproducibility"],
                "role": ContributionRole.ORIGINATOR,
            },
            {
                "trace_type": TraceType.PROJECT,
                "title": "Laboratory workflow modernization program",
                "description": "Converted fragmented analyses into versioned, containerized, and testable pipelines.",
                "keywords": ["software engineering", "workflow automation", "data engineering"],
                "role": ContributionRole.LEAD,
            },
        ),
    ),
    "ai_curriculum_design": SyntheticAssetTemplate(
        key="ai_curriculum_design",
        label="AI-assisted curriculum and reusable teaching assets",
        concepts=("teaching_curriculum", "generative_ai", "machine_learning", "scientific_writing"),
        trace_blueprints=(
            {
                "trace_type": TraceType.COURSE,
                "title": "Statistical programming with AI assistance",
                "description": "Graduate course combining R, Python, software practice, and governed use of generative AI.",
                "keywords": ["teaching", "curriculum", "generative AI", "statistical programming"],
                "role": ContributionRole.ORIGINATOR,
            },
            {
                "trace_type": TraceType.DOCUMENT,
                "title": "Reusable AI-assisted programming textbook",
                "description": "A living document with exercises, code, and teaching notes for repeated course delivery.",
                "keywords": ["textbook", "course", "R", "Python", "AI"],
                "role": ContributionRole.ORIGINATOR,
            },
            {
                "trace_type": TraceType.TALK,
                "title": "Teaching software and data science in the generative-AI era",
                "description": "Invited presentation on assessment, verification, and curriculum redesign.",
                "keywords": ["teaching", "AI", "scientific writing"],
                "role": ContributionRole.LEAD,
            },
        ),
    ),
    "knowledge_asset_systems": SyntheticAssetTemplate(
        key="knowledge_asset_systems",
        label="AI-amplified knowledge-asset systems",
        concepts=(
            "knowledge_management",
            "information_systems",
            "generative_ai",
            "product_development",
            "software_engineering",
        ),
        trace_blueprints=(
            {
                "trace_type": TraceType.DOCUMENT,
                "title": "AI-amplified knowledge assets: conceptual framework",
                "description": "Theory manuscript defining trace, asset hypothesis, credibility, opportunity fit, amplification, and value capture.",
                "keywords": ["knowledge assets", "information systems", "generative AI"],
                "role": ContributionRole.ORIGINATOR,
            },
            {
                "trace_type": TraceType.SOFTWARE,
                "title": "kdaa-ai prototype",
                "description": "Provenance-aware application for discovery, assessment, opportunity matching, and portfolio export.",
                "keywords": ["knowledge management", "MVP", "AI system", "evidence graph"],
                "role": ContributionRole.ORIGINATOR,
            },
            {
                "trace_type": TraceType.TALK,
                "title": "From accumulated knowledge to deployable knowledge assets",
                "description": "Research seminar on AI, knowledge work, and value realization.",
                "keywords": ["knowledge asset", "AI", "information systems"],
                "role": ContributionRole.LEAD,
            },
        ),
    ),
}

NOISE_BLUEPRINTS: tuple[dict[str, Any], ...] = (
    {
        "trace_type": TraceType.TALK,
        "title": "General introduction to data science",
        "description": "A broad introductory talk with limited evidence of a distinct reusable capability.",
        "keywords": ["data science"],
        "role": ContributionRole.PARTICIPANT,
    },
    {
        "trace_type": TraceType.COLLABORATION,
        "title": "Participant in an interdisciplinary working group",
        "description": "Membership record without documented deliverables or clear contribution attribution.",
        "keywords": ["collaboration", "interdisciplinary"],
        "role": ContributionRole.PARTICIPANT,
    },
    {
        "trace_type": TraceType.AWARD,
        "title": "Travel support award",
        "description": "Recognition of participation; limited direct evidence for a bounded knowledge asset.",
        "keywords": ["award"],
        "role": ContributionRole.PARTICIPANT,
    },
)


def _trace_from_blueprint(
    blueprint: dict[str, Any],
    unit_id: str,
    index: int,
    year: int,
    rng: random.Random,
) -> EvidenceTrace:
    title = str(blueprint["title"])
    collaborators = [
        rng.choice(["Alex Rivera", "Jordan Patel", "Morgan Lee", "Taylor Kim"])
        for _ in range(rng.randint(1, 3))
    ]
    return EvidenceTrace(
        id=f"trace-syn-{unit_id.split(':')[-1]}-{index:03d}",
        unit_id=unit_id,
        trace_type=blueprint["trace_type"],
        title=title,
        description=str(blueprint.get("description", "")),
        source_kind=SourceKind.SYNTHETIC,
        source_name="KDAA synthetic generator",
        source_uri=f"synthetic://{unit_id}/{index}",
        event_date=date(year, rng.randint(1, 12), 1),
        authors_or_contributors=collaborators,
        affiliations=["Synthetic Research Institute"],
        keywords=list(blueprint.get("keywords", [])),
        topics=list(blueprint.get("topics", [])),
        contribution_role=blueprint.get("role", ContributionRole.UNKNOWN),
        outcome_signals={
            "synthetic": True,
            "completed": rng.random() > 0.1,
            "reuse_count": rng.randint(0, 8),
        },
        license="CC0-1.0",
        raw={"synthetic_asset_key": blueprint.get("asset_key")},
    )


def build_demo_bundle() -> UnitBundle:
    """A rich but fully synthetic researcher case used by the app and tests."""

    rng = random.Random(42)
    unit_id = "synthetic:maya-chen"
    unit = FocalUnit(
        id=unit_id,
        name="Dr. Maya Chen",
        unit_type=UnitType.RESEARCHER,
        institution="Synthetic Research Institute",
        description=(
            "Synthetic computational biomedical researcher used to demonstrate KDAA-AI. "
            "No person or career record is represented."
        ),
        homepage="https://example.org/synthetic/maya-chen",
        boundary_notes="All evidence and outcomes are synthetic and may be freely redistributed.",
        governance_notes="Demo data only; do not interpret scores as claims about a real person.",
        is_synthetic=True,
    )
    selected = [
        ASSET_TEMPLATES["agentic_omics_workflows"],
        ASSET_TEMPLATES["causal_clinical_methods"],
        ASSET_TEMPLATES["multiomics_integration"],
        ASSET_TEMPLATES["research_computing_support"],
        ASSET_TEMPLATES["ai_curriculum_design"],
        ASSET_TEMPLATES["knowledge_asset_systems"],
    ]
    traces: list[EvidenceTrace] = []
    idx = 1
    for asset_index, template in enumerate(selected):
        for blueprint in template.trace_blueprints:
            enriched = dict(blueprint)
            enriched["asset_key"] = template.key
            trace = _trace_from_blueprint(
                enriched,
                unit_id,
                idx,
                2019 + asset_index + rng.randint(0, 2),
                rng,
            )
            traces.append(trace)
            idx += 1
    for blueprint in NOISE_BLUEPRINTS:
        traces.append(_trace_from_blueprint(blueprint, unit_id, idx, 2024, rng))
        idx += 1

    goals = [
        StrategicGoal(
            id="goal-independent-program",
            label="Build an independent AI research program",
            description="Create theory, software, and empirical work that form a coherent research trajectory.",
            keywords=["AI", "knowledge assets", "research program", "software", "paper"],
            weight=1.4,
            horizon_months=24,
        ),
        StrategicGoal(
            id="goal-reusable-assets",
            label="Maximize reusable scholarly assets",
            description="Prefer repositories, living documents, structured knowledge bases, deployable products, and public content.",
            keywords=["repository", "reproducibility", "course", "software", "knowledge base"],
            weight=1.2,
            horizon_months=12,
        ),
        StrategicGoal(
            id="goal-scientific-impact",
            label="Increase scientific and educational impact",
            description="Translate methods into reliable tools, training, and publishable evidence.",
            keywords=["scientific", "education", "clinical", "bioinformatics"],
            weight=1.0,
            horizon_months=36,
        ),
    ]
    return UnitBundle(
        unit=unit,
        goals=goals,
        traces=traces,
        metadata={
            "synthetic": True,
            "ground_truth_asset_keys": [template.key for template in selected],
            "ground_truth_concepts": sorted({c for template in selected for c in template.concepts}),
            "generator_version": "0.1.0",
        },
    )


class SyntheticBenchmarkGenerator:
    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_bundle(
        self,
        index: int,
        *,
        min_assets: int = 2,
        max_assets: int = 4,
        noise_traces: int = 2,
    ) -> UnitBundle:
        rng = random.Random(self.seed + index * 7919)
        unit_type = rng.choice([UnitType.RESEARCHER, UnitType.TEAM, UnitType.LAB])
        unit_id = f"synthetic:benchmark-{index:04d}"
        unit = FocalUnit(
            id=unit_id,
            name=f"Synthetic Unit {index:04d}",
            unit_type=unit_type,
            institution="Synthetic Research Institute",
            description="Synthetic benchmark focal unit.",
            boundary_notes="Generated for controlled software evaluation only.",
            is_synthetic=True,
        )
        n_assets = rng.randint(min_assets, max_assets)
        selected = rng.sample(list(ASSET_TEMPLATES.values()), n_assets)
        traces: list[EvidenceTrace] = []
        trace_index = 1
        for asset_template in selected:
            n_blueprints = rng.randint(2, len(asset_template.trace_blueprints))
            for blueprint in rng.sample(list(asset_template.trace_blueprints), n_blueprints):
                enriched = dict(blueprint)
                enriched["asset_key"] = asset_template.key
                year = rng.randint(2018, 2026)
                traces.append(
                    _trace_from_blueprint(enriched, unit_id, trace_index, year, rng)
                )
                trace_index += 1
        for _ in range(noise_traces):
            blueprint = rng.choice(NOISE_BLUEPRINTS)
            traces.append(_trace_from_blueprint(blueprint, unit_id, trace_index, 2024, rng))
            trace_index += 1

        goals = [
            StrategicGoal(
                id="goal-output",
                label="Create reusable high-value outputs",
                keywords=["software", "paper", "course", "repository"],
                weight=1.0,
            )
        ]
        return UnitBundle(
            unit=unit,
            goals=goals,
            traces=traces,
            metadata={
                "synthetic": True,
                "benchmark_index": index,
                "ground_truth_asset_keys": [item.key for item in selected],
                "ground_truth_concepts": sorted({c for item in selected for c in item.concepts}),
                "generator_seed": self.seed,
            },
        )

    def generate(self, n_units: int = 50, **kwargs: Any) -> list[UnitBundle]:
        return [self.generate_bundle(i, **kwargs) for i in range(n_units)]


def _rebind_demo_bundle(
    base: UnitBundle,
    *,
    unit: FocalUnit,
    allowed_asset_keys: set[str],
    goals: list[StrategicGoal],
) -> UnitBundle:
    """Create a distinct synthetic focal-unit scenario from vetted trace blueprints."""

    traces: list[EvidenceTrace] = []
    for index, trace in enumerate(
        [
            item
            for item in base.traces
            if item.raw.get("synthetic_asset_key") in allowed_asset_keys
            or item.raw.get("synthetic_asset_key") is None
        ],
        start=1,
    ):
        traces.append(
            trace.model_copy(
                deep=True,
                update={
                    "id": f"trace-syn-{unit.id.split(':')[-1]}-{index:03d}",
                    "unit_id": unit.id,
                    "source_uri": f"synthetic://{unit.id}/{index}",
                    "affiliations": [unit.institution or "Synthetic Research Institute"],
                },
            )
        )
    ground_truth_concepts = sorted(
        {
            concept
            for key in allowed_asset_keys
            for concept in ASSET_TEMPLATES[key].concepts
        }
    )
    return UnitBundle(
        unit=unit,
        goals=goals,
        traces=traces,
        metadata={
            "synthetic": True,
            "scenario": unit.unit_type.value,
            "ground_truth_asset_keys": sorted(allowed_asset_keys),
            "ground_truth_concepts": ground_truth_concepts,
            "generator_version": "0.1.0",
        },
    )


def build_lab_demo_bundle() -> UnitBundle:
    """Synthetic laboratory case demonstrating a collective focal unit."""

    base = build_demo_bundle()
    unit = FocalUnit(
        id="synthetic:sage-translational-ai-lab",
        name="Sage Translational AI Laboratory",
        unit_type=UnitType.LAB,
        institution="Synthetic Research Institute",
        members=["Maya Chen", "Alex Rivera", "Jordan Patel", "Morgan Lee"],
        description=(
            "Synthetic laboratory combining omics, causal methods, research computing, "
            "and reusable AI systems. No real laboratory or personnel are represented."
        ),
        homepage="https://example.org/synthetic/sage-lab",
        boundary_notes=(
            "The laboratory is the focal unit. Asset ownership and contribution attribution "
            "remain provisional because traces may reflect member-specific or collective work."
        ),
        governance_notes="Synthetic demonstration only; all records are CC0.",
        is_synthetic=True,
    )
    goals = [
        StrategicGoal(
            id="goal-lab-platform",
            label="Build a reusable translational AI platform",
            description="Convert repeated scientific workflows into governed shared infrastructure.",
            keywords=["platform", "omics", "software", "reproducibility", "knowledge base"],
            weight=1.4,
            horizon_months=18,
        ),
        StrategicGoal(
            id="goal-lab-grants",
            label="Develop a coherent multi-project grant program",
            keywords=["grant", "clinical", "causal", "AI", "multi-omics"],
            weight=1.2,
            horizon_months=24,
        ),
    ]
    return _rebind_demo_bundle(
        base,
        unit=unit,
        allowed_asset_keys={
            "agentic_omics_workflows",
            "causal_clinical_methods",
            "multiomics_integration",
            "research_computing_support",
            "knowledge_asset_systems",
        },
        goals=goals,
    )


def build_team_demo_bundle() -> UnitBundle:
    """Synthetic project-team case demonstrating a bounded temporary collective."""

    base = build_demo_bundle()
    unit = FocalUnit(
        id="synthetic:precision-evidence-team",
        name="Precision Evidence Project Team",
        unit_type=UnitType.TEAM,
        institution="Synthetic Research Institute",
        members=["Maya Chen", "Taylor Kim", "Jordan Patel"],
        description=(
            "Synthetic cross-functional project team translating causal, multi-omics, and "
            "software-engineering capabilities into reproducible decision support."
        ),
        homepage="https://example.org/synthetic/precision-evidence-team",
        boundary_notes=(
            "The project team is treated as a temporary focal unit; dependencies on home "
            "laboratories and individual members must be retained in later calibration."
        ),
        governance_notes="Synthetic demonstration only; all records are CC0.",
        is_synthetic=True,
    )
    goals = [
        StrategicGoal(
            id="goal-team-pilot",
            label="Deliver a reproducible pilot and methods paper",
            keywords=["pilot", "methods paper", "causal", "multi-omics", "repository"],
            weight=1.5,
            horizon_months=9,
        ),
        StrategicGoal(
            id="goal-team-transfer",
            label="Transfer the workflow to additional research groups",
            keywords=["transfer", "training", "workflow", "course", "documentation"],
            weight=1.0,
            horizon_months=12,
        ),
    ]
    return _rebind_demo_bundle(
        base,
        unit=unit,
        allowed_asset_keys={
            "causal_clinical_methods",
            "multiomics_integration",
            "research_computing_support",
            "ai_curriculum_design",
        },
        goals=goals,
    )


def build_demo_scenario(scenario: str = "researcher") -> UnitBundle:
    """Return one of the documented, fully synthetic demonstration scenarios."""

    normalized = scenario.strip().lower().replace("-", "_")
    builders = {
        "researcher": build_demo_bundle,
        "lab": build_lab_demo_bundle,
        "laboratory": build_lab_demo_bundle,
        "team": build_team_demo_bundle,
    }
    try:
        return builders[normalized]()
    except KeyError as exc:
        allowed = ", ".join(sorted({"researcher", "lab", "team"}))
        raise ValueError(f"Unknown demo scenario '{scenario}'. Choose one of: {allowed}.") from exc
