# Architecture

KDAA-AI is organized around one rule: **an observable trace is not automatically a knowledge asset**. The software therefore preserves separate representations for focal units, traces, asset hypotheses, assessments, opportunities, calibration deltas, and outcomes.

![System architecture](assets/system_architecture.png)

## Design objectives

The v0.1 architecture is intended to satisfy seven requirements derived from the theory paper:

1. **Multilevel scope.** The focal unit can be an individual or collective, while the principal analytical object remains a bounded asset claim.
2. **Provenance before synthesis.** Every active asset record must contain at least one supporting `EvidenceLink` to a trace in the input bundle.
3. **Falsifiability.** Asset records include bounded claims, exclusions, alternative explanations, dependencies, and a provisional epistemic state.
4. **Duplicate-aware evidence control.** Exact/source-record-equivalent traces remain visible in provenance but do not inflate analytical support.
5. **Opportunity-specific amplification.** AI amplifiability is represented on an asset–opportunity configuration with a stated baseline, not as a global score attached to a person.
6. **No hidden confirmation.** The deterministic or LLM pipeline cannot mark an asset `confirmed`; only a calibration record can do so.
7. **Versioned learning.** Human calibration and outcome records are appended as deltas, preserving the original AI-only run.

## End-to-end flow

### 1. Evidence acquisition and normalization

`UnitBundle` is the canonical input contract. Connectors normalize source-specific records into:

- `FocalUnit`;
- `StrategicGoal`;
- `EvidenceTrace`.

Before discovery, conservative trace identity keys select canonical analytical records while retaining all supplied records and adding `possible_duplicate_of` edges to the provenance graph. A shared source URI alone is not sufficient for duplication because one CV/PDF can yield multiple legitimate trace segments.

Implemented inputs:

- local JSON/YAML;
- local PDF or text CV-like documents;
- OpenAlex author and work records;
- GitHub profile and repository records;
- synthetic researcher, team, laboratory, and benchmark cases.

Module: `src/kdaa/ingestion/`.

### 2. Feature extraction and provenance graph

The ontology matcher identifies declared concepts in trace text. The graph builder creates explicit unit, trace, contributor, and analysis nodes and edges. Graph exports preserve trace IDs and relations for later audit.

Modules:

- `ingestion/dedup.py`;
- `discovery/features.py`;
- `discovery/provenance.py`;
- `resources/ontology.yaml`.

### 3. Asset-hypothesis discovery

The deterministic engine currently proposes five hypothesis families:

- single codified artifacts;
- repeated concept-level capabilities;
- recurring cross-concept combinations;
- recurring relational linkages;
- end-to-end execution capabilities.

Every hypothesis contains supporting trace links, non-claims, alternative explanations, and dependencies. An optional LLM generator can add hypotheses, but it must cite valid trace IDs from the supplied bundle.

Modules:

- `discovery/rules.py`;
- `discovery/llm.py`;
- `providers/openai_compatible.py`.

### 4. Asset-level assessment

The assessment layer generates transparent engineering proxies. Each dimension records:

- a value in `[0, 1]`;
- a named method/version;
- a rationale;
- uncertainty;
- an `is_proxy` flag.

The scores are prioritization aids, not validated latent-variable measurements.

Module: `assessment/credibility.py`.

### 5. Opportunity matching and amplification design

The opportunity engine matches one or two assets to theory-aligned templates. Each opportunity defines:

- a concrete problem and beneficiary;
- one of the five output containers;
- scholarly or operational value pathways;
- a credible human-only baseline;
- AI tasks, human tasks, and verification gates;
- expected gain vector;
- fit, amplifiability, readiness, governance risk, and priority proxies;
- dependencies, effort, time horizon, and caveats.

Modules:

- `amplification/catalog.py`;
- `amplification/engine.py`;
- `assessment/opportunity_fit.py`.

### 6. Reporting and graph export

A run is emitted as a complete `AnalysisRun` and multiple projections:

- JSON record;
- run manifest with configuration/input digests;
- asset and opportunity CSV files;
- Markdown and standalone HTML reports;
- GraphML and node-link JSON provenance graphs.

Modules:

- `report.py`;
- `storage.py`;
- `resources/report.*.j2`.

### 7. Optional human and outcome lifecycle

The MVP runs without this stage. When available, calibration records can confirm, narrow, split, reject, or defer an asset. Outcome records distinguish observed gains, realized value, captured value, and causal caveats.

Module: `lifecycle.py`.

## Interface layers

| Interface | Entry point | Intended use |
|---|---|---|
| Python | `KDAAPipeline.analyze()` | notebooks, experiments, integration |
| CLI | `kdaa` | reproducible scripts and batch runs |
| FastAPI | `kdaa.api:app` | service integration and programmatic testing |
| Streamlit | `app/streamlit_app.py` | interactive research inspection and calibration |

## Local-first and optional remote inference

The deterministic mode is the reference implementation and benchmark target. It requires no remote model, which makes it suitable for reproducible software evaluation and sensitive-data prototyping. Hybrid and LLM modes are optional and use an OpenAI-compatible JSON endpoint. Sensitive traces are not sent unless explicitly enabled.

## Dependency direction

```text
models/config/ontology
        ↓
ingestion → discovery → assessment → amplification
        ↓                         ↓
  provenance graph         opportunities
        └──────────────┬──────────┘
                       ↓
                pipeline/reporting
                       ↓
           API / CLI / Streamlit / lifecycle
```

No connector or user interface defines the scientific constructs. The domain models and theory-derived requirements sit below all interfaces.
