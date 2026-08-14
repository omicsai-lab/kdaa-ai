"""Theory-aligned opportunity template catalog."""

from __future__ import annotations

from dataclasses import dataclass

from kdaa.models import GainVector, OutputContainer, ValuePathway


@dataclass(frozen=True)
class OpportunityTemplate:
    key: str
    title_prefix: str
    output_container: OutputContainer
    value_pathways: tuple[ValuePathway, ...]
    problem: str
    beneficiary: str
    ai_tasks: tuple[str, ...]
    human_tasks: tuple[str, ...]
    verification_gates: tuple[str, ...]
    credible_baseline: str
    expected_gain: GainVector
    effort: str
    horizon: str
    preferred_categories: tuple[str, ...] = ()
    preferred_terms: tuple[str, ...] = ()
    preferred_namespaces: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()


TEMPLATES: tuple[OpportunityTemplate, ...] = (
    OpportunityTemplate(
        key="research_repository",
        title_prefix="Build a reproducible repository around",
        output_container=OutputContainer.REPOSITORY,
        value_pathways=(ValuePathway.SOFTWARE, ValuePathway.JOURNAL_PAPER),
        problem="Methods and implementation knowledge are dispersed across outputs and difficult to reuse or evaluate.",
        beneficiary="Researchers, collaborators, reviewers, and future project teams",
        ai_tasks=(
            "scaffold a tested package or workflow",
            "standardize documentation and examples",
            "generate unit tests and reproducibility checks",
            "convert repeated procedures into configuration-driven code",
        ),
        human_tasks=(
            "define scientific and operational boundaries",
            "validate algorithms, assumptions, and examples",
            "decide licensing, attribution, and release scope",
        ),
        verification_gates=(
            "all example runs reproduce from a clean environment",
            "claims are linked to evidence or tests",
            "licenses and contributor attribution are reviewed",
        ),
        credible_baseline="A manually assembled repository built from existing files without AI-assisted refactoring.",
        expected_gain=GainVector(time=0.70, quality=0.35, scale=0.65, reuse=0.85, recombination=0.45, execution_span=0.60, learning=0.25, cost=0.45, risk=-0.05),
        effort="medium",
        horizon="2-6 weeks",
        preferred_categories=("codified", "combinative_execution"),
        preferred_terms=("software", "reproducible", "method", "data", "workflow"),
        preferred_namespaces=("artifact", "execution", "pair"),
    ),
    OpportunityTemplate(
        key="living_playbook",
        title_prefix="Create a versioned living playbook for",
        output_container=OutputContainer.LIVING_DOCUMENT,
        value_pathways=(ValuePathway.BOOK, ValuePathway.COURSE, ValuePathway.INTERNAL_CAPABILITY),
        problem="Tacit sequencing, exceptions, and repeated judgment are not captured in reusable form.",
        beneficiary="The focal unit, trainees, collaborators, and future users",
        ai_tasks=(
            "organize evidence into a modular outline",
            "draft examples, checklists, and cross-references",
            "translate the same knowledge into multiple levels of detail",
            "maintain change logs and detect stale sections",
        ),
        human_tasks=(
            "supply tacit exceptions and boundary conditions",
            "approve examples and normative guidance",
            "remove sensitive or non-transferable details",
        ),
        verification_gates=(
            "every operational recommendation has an owner and evidence basis",
            "tacit exceptions are explicitly flagged",
            "the document is versioned and has a review cadence",
        ),
        credible_baseline="A static document assembled manually from existing notes.",
        expected_gain=GainVector(time=0.65, quality=0.30, accessibility=0.75, reuse=0.80, learning=0.45, cost=0.35, risk=-0.05),
        effort="small",
        horizon="1-4 weeks",
        preferred_categories=("tacit_procedural", "codified"),
        preferred_terms=("teaching", "protocol", "workflow", "method", "writing"),
        preferred_namespaces=("concept", "execution", "artifact"),
    ),
    OpportunityTemplate(
        key="structured_knowledge_base",
        title_prefix="Build a provenance-aware knowledge base for",
        output_container=OutputContainer.KNOWLEDGE_BASE,
        value_pathways=(ValuePathway.DATA_RESOURCE, ValuePathway.INTERNAL_CAPABILITY, ValuePathway.JOURNAL_PAPER),
        problem="Evidence, claims, dependencies, and lessons are difficult to query as a portfolio rather than a flat profile.",
        beneficiary="The focal unit, research managers, collaborators, and evaluators",
        ai_tasks=(
            "normalize evidence and entity names",
            "link claims to supporting and contradicting traces",
            "generate versioned asset records",
            "surface missing evidence and stale assumptions",
        ),
        human_tasks=(
            "define unit boundaries and access rights",
            "adjudicate attribution and ownership",
            "approve high-impact asset claims",
        ),
        verification_gates=(
            "no active asset claim lacks provenance",
            "contradicting evidence is retained",
            "sensitive traces are separated from public exports",
        ),
        credible_baseline="A CV, profile page, or unstructured document collection searched manually.",
        expected_gain=GainVector(time=0.55, quality=0.45, scale=0.75, accessibility=0.80, reuse=0.70, recombination=0.55, learning=0.60, cost=0.30, risk=-0.10),
        effort="medium",
        horizon="3-8 weeks",
        preferred_categories=("bundle", "codified", "relational"),
        preferred_terms=("knowledge", "evidence", "research", "data", "portfolio"),
        preferred_namespaces=("execution", "pair", "concept", "relational"),
    ),
    OpportunityTemplate(
        key="deployable_copilot",
        title_prefix="Develop a deployable AI-assisted workflow for",
        output_container=OutputContainer.DEPLOYABLE_PRODUCT,
        value_pathways=(ValuePathway.SOFTWARE, ValuePathway.CONSULTING, ValuePathway.INTERNAL_CAPABILITY),
        problem="A credible capability remains bottlenecked by repetitive search, synthesis, translation, or production tasks.",
        beneficiary="Practitioners who face the same recurring workflow and verification problem",
        ai_tasks=(
            "execute bounded search, extraction, synthesis, and drafting tasks",
            "orchestrate repeatable tool calls and data transformations",
            "produce auditable intermediate outputs",
            "route uncertain cases to explicit verification gates",
        ),
        human_tasks=(
            "define goals and acceptable failure modes",
            "validate frontier-sensitive judgments",
            "accept accountability for deployment decisions",
        ),
        verification_gates=(
            "performance is compared with a credible human-only baseline",
            "high-risk outputs require human approval",
            "failure logs and provenance are retained",
        ),
        credible_baseline="The same workflow performed manually with conventional search, documents, and scripts.",
        expected_gain=GainVector(time=0.75, quality=0.30, scale=0.80, accessibility=0.50, reuse=0.65, recombination=0.55, execution_span=0.75, learning=0.35, cost=0.50, risk=-0.20),
        effort="large",
        horizon="4-12 weeks",
        preferred_categories=("combinative_execution", "codified"),
        preferred_terms=("AI", "software", "workflow", "product", "analysis"),
        preferred_namespaces=("execution", "pair", "artifact"),
        caveats=("Do not infer deployment safety from a successful demonstration alone.",),
    ),
    OpportunityTemplate(
        key="public_content",
        title_prefix="Publish a public tutorial or research talk on",
        output_container=OutputContainer.PUBLIC_CONTENT,
        value_pathways=(ValuePathway.PUBLIC_ENGAGEMENT, ValuePathway.CONFERENCE_OUTPUT, ValuePathway.COURSE),
        problem="A differentiated capability is not visible or legible to the audiences who could use, cite, or extend it.",
        beneficiary="Scholarly and professional audiences",
        ai_tasks=(
            "adapt the asset to multiple audience levels",
            "create examples, diagrams, and companion material",
            "convert one validated core into slides, tutorial, and web content",
        ),
        human_tasks=(
            "choose the intellectual claim and narrative",
            "verify facts, examples, and attribution",
            "deliver and defend the content publicly",
        ),
        verification_gates=(
            "the public claim is narrower than or equal to the evidence",
            "all borrowed material is attributed",
            "sensitive and proprietary content is excluded",
        ),
        credible_baseline="A one-off manually prepared presentation with no reusable companion asset.",
        expected_gain=GainVector(time=0.60, quality=0.25, scale=0.70, accessibility=0.85, reuse=0.65, learning=0.20, cost=0.35, risk=-0.05),
        effort="small",
        horizon="1-3 weeks",
        preferred_categories=("codified", "combinative_execution"),
        preferred_terms=("teaching", "research", "AI", "method", "framework"),
        preferred_namespaces=("concept", "pair", "execution"),
    ),
    OpportunityTemplate(
        key="methods_paper",
        title_prefix="Develop a methods or design-science paper from",
        output_container=OutputContainer.LIVING_DOCUMENT,
        value_pathways=(ValuePathway.JOURNAL_PAPER, ValuePathway.CONFERENCE_OUTPUT),
        problem="A recurring method or artifact lacks a bounded scholarly claim, transparent evaluation, and reusable research record.",
        beneficiary="Researchers and reviewers in the relevant scholarly community",
        ai_tasks=(
            "organize literature and evidence matrices",
            "generate experiment scaffolding and reproducibility tables",
            "maintain consistency across manuscript, code, and supplement",
        ),
        human_tasks=(
            "define the research question and contribution",
            "select defensible baselines and evaluation criteria",
            "interpret results and own all scholarly claims",
        ),
        verification_gates=(
            "evaluation can falsify the central claim",
            "all citations and quantitative results are independently checked",
            "the paper clearly separates hypothesis, artifact, and empirical validation",
        ),
        credible_baseline="A manuscript assembled after implementation without a theory-to-evidence traceability plan.",
        expected_gain=GainVector(time=0.50, quality=0.35, reuse=0.55, recombination=0.35, learning=0.40, cost=0.25, risk=-0.05),
        effort="medium",
        horizon="4-10 weeks",
        preferred_categories=("codified", "combinative_execution", "bundle"),
        preferred_terms=("method", "framework", "system", "analysis", "research"),
        preferred_namespaces=("pair", "execution", "artifact"),
    ),
    OpportunityTemplate(
        key="grant_program",
        title_prefix="Form a grant-ready research program around",
        output_container=OutputContainer.LIVING_DOCUMENT,
        value_pathways=(ValuePathway.GRANT, ValuePathway.INTERNAL_CAPABILITY),
        problem="Complementary capabilities exist but are not organized into a fundable problem, milestones, and evidence plan.",
        beneficiary="The focal unit, collaborators, funders, and target beneficiaries",
        ai_tasks=(
            "map preliminary evidence to aims and milestones",
            "identify reusable components and missing complementary assets",
            "maintain an evidence-to-claim matrix across proposal sections",
        ),
        human_tasks=(
            "choose the fundable problem and scientific stakes",
            "secure collaborators, access, and institutional commitments",
            "validate feasibility, budget, and ethical obligations",
        ),
        verification_gates=(
            "each aim has preliminary evidence or a credible feasibility plan",
            "ownership and collaborator roles are explicit",
            "claims are aligned with the funding mechanism and beneficiary need",
        ),
        credible_baseline="A proposal drafted from a general idea without an asset portfolio or dependency map.",
        expected_gain=GainVector(time=0.45, quality=0.30, recombination=0.65, execution_span=0.45, learning=0.30, cost=0.20, risk=-0.05),
        effort="large",
        horizon="6-16 weeks",
        preferred_categories=("combinative_execution", "relational", "bundle"),
        preferred_terms=("grant", "clinical", "research", "AI", "program"),
        preferred_namespaces=("execution", "pair", "relational"),
    ),
)
