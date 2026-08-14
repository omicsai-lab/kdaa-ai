# Design decisions

## Why deterministic mode is the default

The first repo must be runnable, inspectable, and testable without model access, token cost, provider drift, or human recruitment. Deterministic mode also creates a stable reference point for LLM comparisons.

## Why a trace is not an asset

Profiles and LLM summaries often convert every visible accomplishment directly into a capability claim. KDAA requires a separate inferential object so that evidence, attribution, exclusions, dependencies, and uncertainty can be inspected.

## Why no global person score

A focal unit can have a heterogeneous portfolio. One asset can be well evidenced and codified, another highly tacit and collaborator-dependent, and a third merely adjacent. A single expertise or potential score destroys these distinctions and invites high-stakes misuse.

## Why `confirmed` is inaccessible to the pipeline

If a model can mark its own claims confirmed, the human-calibration construct becomes cosmetic. Only an explicit calibration record can create a confirmed state.

## Why opportunity templates are explicit

Templates make hidden assumptions visible: preferred asset forms, beneficiary, output container, human/AI allocation, baseline, verification gates, expected gains, effort, and caveats. A free-form recommender would be more fluent but less auditable.

## Why five output containers

The five containers reflect the project's practical asset strategy:

1. repository;
2. living document;
3. structured knowledge base;
4. deployable product;
5. public content.

They are not claimed to exhaust all forms of value. Journal, grant, course, book, software, consulting, and public-engagement pathways are represented separately.

## Why synthetic data are first-class

The first artifact must not depend on delayed or uncontrolled participant confirmation. Synthetic cases permit complete reproducibility, negative/noise traces, known concept labels, unit-type variation, and open redistribution. They cannot replace human validation.

## Why public connectors are bounded

OpenAlex and GitHub provide useful public traces and demonstrate source heterogeneity. They are not treated as comprehensive identity or contribution systems. The connector outputs remain reviewable `UnitBundle` files before analysis.

## Why calibration and outcomes are already modeled

The first version does not need the human loop to run, but Paper C must not require a schema redesign. Calibration and outcome objects make the theoretical closed loop explicit while preserving the boundary between implemented artifact and uncollected evidence.

## Duplicate retention without support inflation

**Decision:** retain every supplied trace in `AnalysisRun` and the provenance graph, but exclude exact/source-record-equivalent duplicates from discovery, assessment, and LLM input. Add a `possible_duplicate_of` edge from each excluded record to its canonical record.

**Reason:** silently deleting evidence harms auditability, while counting repeated ingestion as independent support inflates confidence. The identity rule therefore uses source-record IDs when available, otherwise source URI plus trace type and normalized title, and finally a normalized content fingerprint. A source URI alone is never sufficient because one CV/PDF can legitimately yield multiple trace segments.

**Known boundary:** semantic duplicates, derivative publications, mirrored repositories, and correlated sources require later source-dependence models.
