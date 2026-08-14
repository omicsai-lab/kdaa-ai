# API and CLI reference

## Command line

```bash
kdaa --help
```

### `kdaa demo`

Runs one of three fully synthetic scenarios.

```bash
kdaa demo --scenario researcher --output results/demo
kdaa demo --scenario lab --output results/demo-lab
kdaa demo --scenario team --output results/demo-team
```

### `kdaa analyze`

```bash
kdaa analyze INPUT.json --config configs/default.yaml --output results/run
```

The input must validate as `UnitBundle`.

### `kdaa ingest-cv`

```bash
kdaa ingest-cv researcher_cv.pdf \
  --unit-id unit:researcher \
  --unit-name "Researcher Name" \
  --institution "Georgetown University" \
  --output data/cv_bundle.json
```

Parses a local PDF or text CV-like document into a conservative `UnitBundle`. Imported traces are marked sensitive and contribution roles remain unknown unless explicitly available. Review segmentation, privacy, and attribution before analysis or sharing.

### `kdaa fetch-openalex`

```bash
kdaa fetch-openalex IDENTIFIER --max-works 50 --output data/openalex.json
```

`IDENTIFIER` may be an OpenAlex author ID, ORCID, or name. Review the returned identity before analysis.

### `kdaa fetch-github`

```bash
kdaa fetch-github USERNAME --max-repos 100 --output data/github.json
```

Use `--include-forks` only when forked repositories are meaningful evidence.

### `kdaa merge`

```bash
kdaa merge data/a.json data/b.yaml --output data/merged.json
```

Bundles should represent the same focal unit. Trace IDs are made unique on collision, and exact/source-record-equivalent records are conservatively de-duplicated without collapsing different segments from the same source document.

### `kdaa benchmark`

```bash
kdaa benchmark --n-units 50 --seed 42 --output results/benchmark
```

### `kdaa stress-test`

```bash
kdaa stress-test --output results/robustness
```

Runs deterministic duplicate, staleness, attribution, evidence-removal, and irrelevant-noise perturbations. Results are engineering checks, not human validation.

### `kdaa schema`

```bash
kdaa schema --output data/schema/unit_bundle.schema.json
```

### `kdaa serve`

```bash
kdaa serve --host 0.0.0.0 --port 8000
```

## FastAPI

Start with:

```bash
uvicorn kdaa.api:app --reload
```

### `GET /health`

Returns service status and version.

### `GET /v1/schema/unit-bundle`

Returns the Pydantic-generated JSON schema.

### `POST /v1/analyze`

Request body: canonical `UnitBundle` JSON.

Response: complete `AnalysisRun` JSON.

### `POST /v1/demo`

Runs a fully synthetic demonstration. Use the optional query parameter `scenario=researcher|lab|team`; the default is `researcher`.

### `POST /v1/calibrate`

Applies a list of calibration records to a supplied analysis run and returns a new versioned run.

## Python

```python
from kdaa.config import KDAAConfig
from kdaa.ingestion import build_demo_bundle
from kdaa.pipeline import KDAAPipeline

bundle = build_demo_bundle()
run, graph = KDAAPipeline(KDAAConfig()).analyze(bundle)

print(run.unit.name)
print(run.assets[0].bounded_claim)
print(run.opportunities[0].credible_baseline)
```

## Errors and validation

Domain models use `extra="forbid"`. Unknown fields, invalid enum values, duplicate trace IDs within a single input bundle, trace/unit mismatch, unsupported active asset records, and invalid calibration/outcome references raise explicit errors rather than being silently ignored. At analysis time, equivalent records under different IDs are retained in provenance and excluded from analytical support counts.
