# Traceability matrix

This matrix links the theory manuscript, software objects, implementation modules, tests, exports, and remaining evidence gaps.

| Theory construct / requirement | Domain object | Main module(s) | Test or artifact | Remaining gap |
|---|---|---|---|---|
| focal unit | `FocalUnit` | `models.py`, ingestion | synthetic researcher/lab/team tests | real boundary validation |
| strategic context | `StrategicGoal` | `models.py`, `opportunity_fit.py` | opportunity outputs | goal elicitation validity |
| knowledge trace | `EvidenceTrace` | ingestion connectors | connector fixtures/tests | completeness and identity errors |
| provenance-aware evidence assembly | NetworkX graph | `provenance.py` | GraphML/JSON export tests | source independence and negative evidence |
| duplicate-aware evidence control | retained traces + canonical analysis set | `ingestion/dedup.py`, `provenance.py`, `pipeline.py` | de-duplication and perturbation tests | semantic/source-dependence resolution |
| trace is not asset | separate models | `models.py`, `pipeline.py` | model and pipeline tests | user comprehension |
| asset hypothesis | `AssetRecord` | `rules.py`, `llm.py` | active evidence validation | real claim correctness |
| falsifiability | claim/exclusions/alternatives | `rules.py` | demo report | quality of disconfirming criteria |
| asset categories | enum/list | `models.py`, rules | portfolio CSV | construct discrimination |
| asset-level credibility | `AssetAssessment` | `credibility.py` | benchmark and score export | measurement validation |
| attribution | contribution role / dependencies | connectors, assessment | mocked connector tests | contributorship ground truth |
| tacitness | score/category | assessment | score output | interview/behavioral validation |
| distinctiveness | score | assessment | score output | external comparison population |
| asset–opportunity fit | `AmplificationOpportunity` | opportunity engine | five-container pipeline test | human usefulness and timing |
| AI amplifiability | baseline/tasks/gates/gain | catalog/engine | opportunity CSV/report | counterfactual outcome study |
| human calibration | `CalibrationRecord` | `lifecycle.py`, app/API | lifecycle/API tests | participant study and reliability |
| realized value | `OutcomeRecord.realized_value` | lifecycle/models | outcome test/template | observed deployments |
| captured value | `OutcomeRecord.captured_value` | lifecycle/models | outcome test/template | attribution/IP/reputation measures |
| closed-loop learning | append-only deltas | lifecycle | version preservation tests | learning algorithm and longitudinal data |
| five output containers | `OutputContainer` | catalog/engine | pipeline container test | portfolio outcome comparison |
| reproducibility | `RunManifest` | pipeline/report | digests, CI, benchmark, perturbation suite, release check | environment lock and archived DOI |
| governance | sensitivity, warnings, notes | models/pipeline/docs | warning outputs | production controls and institutional review |
