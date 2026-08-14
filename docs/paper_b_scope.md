# Paper B scope: the artifact and system paper

## Working purpose

Paper B asks:

> How can the KDAA theoretical framework be operationalized as a provenance-aware intelligent system that produces bounded, auditable asset hypotheses and opportunity-specific amplification designs without assuming human confirmation?

This repository is the primary artifact and experimental object.

## Proposed working title

**Operationalizing AI-Amplified Knowledge Assets: Design and Evaluation of a Provenance-Aware Discovery, Assessment, and Amplification System**

Alternative ESWA-oriented title:

**A Provenance-Aware Intelligent System for Knowledge Asset Discovery, Assessment, and Amplification**

## Central contribution

Paper B should make a bounded claim:

- the theory can be translated into explicit design requirements;
- those requirements can be implemented in a reproducible artifact;
- provenance and epistemic-state constraints can reduce unsupported claims relative to simpler profile-generation approaches;
- the system can generate inspectable opportunity designs without human confirmation as a critical path;
- construct validity, usefulness, and value remain separate empirical questions.

It should **not** claim that the system has validated real knowledge assets or generated realized value.

## Recommended paper structure

1. **Introduction**
   - problem: accumulated knowledge is dispersed and profiles collapse evidence and inference;
   - artifact objective;
   - bounded contributions.
2. **Theoretical grounding and design requirements**
   - concise summary of Paper A;
   - trace–asset separation;
   - asset-level granularity;
   - opportunity-specific amplifiability;
   - no automatic confirmation;
   - provenance and governance.
3. **Artifact design**
   - domain model;
   - architecture;
   - deterministic and optional LLM modes;
   - connectors;
   - lifecycle records.
4. **Implementation**
   - package, API, app, exports, configuration, reproducibility.
5. **Evaluation design**
   - synthetic benchmark;
   - baselines;
   - ablations;
   - perturbation/robustness tests;
   - cost and latency;
   - claim audit.
6. **Results**
   - engineering metrics;
   - failure modes;
   - examples with clear synthetic/public labels.
7. **Discussion**
   - artifact as computational instantiation;
   - what implementation revealed about theory;
   - limitations and research agenda.
8. **Conclusion**

## Design requirements for the paper

| ID | Requirement | Rationale | Evidence in v0.1 |
|---|---|---|---|
| DR1 | Preserve focal-unit boundaries | unit and asset are distinct levels | `FocalUnit`, boundary/governance fields |
| DR2 | Separate traces from assets | observation is not inference | `EvidenceTrace` vs `AssetRecord` |
| DR3 | Require claim-level provenance | reduce flattering unsupported synthesis | active assets require supporting links |
| DR4 | Make claims falsifiable | enable rejection, narrowing, and split | bounded claim, exclusions, alternatives |
| DR5 | Represent attribution and dependency | collective work and ownership matter | roles, contributors, dependencies, relational records |
| DR6 | Assess at asset level | heterogeneous portfolios cannot be one score | `AssetAssessment` per record |
| DR7 | Define amplification at opportunity level | AI value is context and baseline dependent | baseline, tasks, gates, gain vector |
| DR8 | Prevent automatic confirmation | human calibration is constitutive | pipeline only emits hypothesis/provisional states |
| DR9 | Preserve revisions and outcomes | closed-loop learning needs negative evidence | append-only calibration/outcome records |
| DR10 | Support reproducible local evaluation | Paper B cannot depend on uncontrolled users | deterministic mode and synthetic benchmark |

## Evaluation that can be completed without a human loop

### Required for a solid first submission

- deterministic end-to-end artifact;
- at least one unstructured profile baseline;
- at least one LLM baseline, if API access is available;
- provenance-completeness and unsupported-claim measures;
- concept or trace-level coverage measures;
- deterministic/repeatability test;
- ablation of provenance, contribution role, and bounded-claim fields;
- perturbation tests for duplicate, stale, conflicting, and misattributed traces;
- runtime and optional token/cost reporting;
- public repository, Docker, tests, and archived release.

### Valuable but not mandatory for Paper B

- a small expert audit of example records;
- multiple public researcher/lab cases;
- direct ORCID/Crossref connectors;
- LLM model comparison;
- UI usability observations.

These additions should not turn human participation into the critical path.

## Journal positioning

### Expert Systems with Applications

Best fit when the paper emphasizes intelligent-system architecture, implementation, baselines, robustness, and applied knowledge-management use.

### Decision Support Systems

Best fit when the opportunity-ranking and decision-support contribution becomes central and the evaluation demonstrates meaningful decision improvement or transparent choice support.

### Information-systems design-science outlet

Possible later if design knowledge and theoretical contribution become much stronger than a typical applied-AI artifact paper. It should not be assumed in v0.1 planning.

## Relationship to Paper A

Paper B should cite and summarize the theory, but not reproduce the 30-page theoretical development. The artifact can reveal weak constructs and motivate revisions to Paper A.

## Relationship to Paper C

Paper B creates the research instrument for Paper C. It should preserve calibration and outcome data structures, while explicitly stating that real human validity and value have not yet been established.
