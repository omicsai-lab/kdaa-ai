# Theory-to-system mapping

The repository is not intended as a generic résumé summarizer. Its architecture is a computational instantiation of the KDAA theoretical framework.

![Theory to artifact](assets/theory_to_artifact.png)

## Core constructs

### Focal unit

**Theory:** a bounded individual or collective social actor whose traces, capabilities, governance, and outcomes can be linked.

**Software:** `FocalUnit` supports researchers, teams, laboratories, departments, firms, nonprofits, public institutions, and other units. Boundary and governance notes are first-class fields.

**Safeguard:** the software does not assign one global “expert score” to the focal unit.

### Knowledge trace

**Theory:** an observable artifact, event, relation, or outcome that bears on an asset claim but is not itself the asset.

**Software:** `EvidenceTrace` supports publications, software, datasets, grants, projects, protocols, courses, talks, patents, employment, awards, collaborations, documents, outcomes, and other traces.

**Safeguard:** trace type, source, contribution role, event date, contributors, sensitivity, license, and raw source metadata remain available for audit. Exact/source-record-equivalent duplicates remain in the run and graph but are excluded from discovery, assessment, and remote-model input.

### Asset hypothesis

**Theory:** a falsifiable, evidence-linked proposition that the focal unit possesses or can access a bounded knowledge asset.

**Software:** `AssetRecord` requires a bounded claim and at least one supporting `EvidenceLink`. It also stores what the asset enables, exclusions, alternative explanations, dependencies, hypothesized ownership, discovery method, uncertainty, and epistemic state.

**Safeguard:** non-rejected active records without supporting evidence fail Pydantic validation.

### Knowledge asset

**Theory:** a validated bundle of know-how, artifacts, routines, relationships, and problem-solving capacity that can be mobilized for future value.

**Software:** v0.1 never creates a validated asset automatically. It creates `hypothesis` or `provisional` records. A `CalibrationRecord` can later move an asset to `confirmed` or another reviewed state.

### Asset-level credibility

**Theory:** degree to which evidence and calibration support a bounded asset claim.

**Software:** `AssetAssessment` exposes separate dimensions and uncertainty. Overall credibility is a transparent weighted proxy, not an opaque classifier.

### Asset distinctiveness

**Theory:** scarcity, differentiation, difficulty of imitation, or unusual combination relative to alternatives.

**Software:** v0.1 uses only within-record specificity and combination proxies. It explicitly does **not** benchmark the external labor market, peer population, or competitive field. This is a known limitation.

### Asset–opportunity fit

**Theory:** compatibility between an asset and a concrete problem, audience, timing, resources, and deployment path.

**Software:** `AmplificationOpportunity` binds assets to a beneficiary, problem, output container, value pathway, dependencies, effort, time horizon, and strategic goals.

### AI amplifiability

**Theory:** counterfactual incremental value of a governed human–AI configuration relative to a credible human-only baseline.

**Software:** each opportunity states a baseline, AI tasks, human tasks, verification gates, an expected gain vector, and an opportunity-specific amplifiability proxy.

**Safeguard:** the proxy is not attached to the focal unit or asset in isolation.

### Realized and captured value

**Theory:** realized benefit can differ from the value retained by or legitimately attributable to the focal unit.

**Software:** `OutcomeRecord` has separate dictionaries for `realized_value` and `captured_value`, plus attribution notes and causal caveats.

### Closed-loop learning

**Theory:** calibration and outcome evidence revise asset boundaries, confidence, opportunities, and governance rules.

**Software:** lifecycle functions append records and preserve earlier versions. Full automatic learning is not implemented in v0.1; the data contract is present for Paper C and later releases.

## Six operational stages

| Theory stage | v0.1 implementation | Status |
|---|---|---|
| 1. Provenance-aware evidence assembly | typed connectors, trace normalization, duplicate-aware canonical analysis set, NetworkX evidence graph | implemented |
| 2. Asset-hypothesis formation | deterministic rules and optional provenance-gated LLM | implemented |
| 3. Asset-level assessment | transparent proxy dimensions with uncertainty | implemented, unvalidated |
| 4. Human calibration and opportunity matching | opportunity engine implemented; human calibration optional | partially implemented |
| 5. AI-enabled mobilization and externalization | task maps, baselines, gates, gain vectors, five containers | design representation implemented |
| 6. Outcome evaluation and closed-loop learning | outcome schema and append-only lifecycle | data layer implemented; empirical learning future |

## Four ideal asset categories

The data model allows multiple categories per asset:

- `codified`;
- `tacit_procedural`;
- `relational`;
- `combinative_execution`;
- `bundle` when several components are inseparable.

The categories are analytical aids, not mutually exclusive taxonomic truth.

## Theoretical claims the artifact can and cannot support

The repository can currently demonstrate that the KDAA ontology is operationalizable, that provenance and zero automatic confirmation can be enforced in software, that exact duplicate evidence need not inflate support, and that a bounded deterministic pipeline can generate reproducible asset/opportunity records with expected directional responses to controlled perturbations.

It cannot establish that:

- the constructs are psychometrically valid;
- the discovered assets are true in real units;
- the opportunities are novel or useful to humans;
- AI creates incremental value;
- value is causally attributable to the artifact;
- captured value follows realized value.

Those claims belong to later empirical work.
