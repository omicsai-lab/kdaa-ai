# Reproducibility

## Supported environment

- Python 3.11 or 3.12;
- Linux, macOS, or Windows for the Python package;
- Graphviz for rebuilding documentation diagrams;
- Docker/Compose optional.

## Clean installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[app,dev]"
```

## Deterministic demonstration

```bash
rm -rf results/demo
kdaa demo --scenario researcher --output results/demo
```

The analysis run ID and timestamps will differ. Ordered asset labels, bounded claims, and evidence links should remain stable under the same code, configuration, and input.

## Synthetic benchmark

```bash
rm -rf results/benchmark
kdaa benchmark --n-units 50 --seed 42 --output results/benchmark
```

Expected committed metrics are listed in `results/benchmark/benchmark_summary.json` and [Evaluation protocol](evaluation_protocol.md).

## Perturbation suite

```bash
rm -rf results/robustness
kdaa stress-test --output results/robustness
```

The committed suite checks exact-duplicate control, stale-date response, unknown-role response, evidence removal, irrelevant-noise resistance, provenance completeness, and zero automatic confirmation. Expected results are listed in `results/robustness/robustness_summary.json` and [Evaluation protocol](evaluation_protocol.md).

Rebuild documentation figures after changing committed results:

```bash
python scripts/build_figures.py
```

## Tests

```bash
pytest
pytest --cov=kdaa --cov-report=term-missing
```

The test suite covers:

- strict models and epistemic constraints;
- end-to-end deterministic pipeline and determinism;
- exact/source-record-equivalent trace de-duplication while retaining provenance;
- multi-segment CV/document merging;
- local CV/text parsing and CLI ingestion;
- OpenAlex and GitHub connector normalization with mocked HTTP responses;
- lifecycle calibration and outcomes;
- report generation and GraphML export;
- FastAPI endpoints;
- benchmark and perturbation invariants;
- synthetic researcher, laboratory, and team scenarios.

## Lint and compile

```bash
ruff check .
ruff format --check src tests app scripts
python -m compileall -q src app scripts tests examples
```

GitHub Actions is the independent lint/test environment for a pushed release.

## Release check

```bash
python scripts/check_release.py
```

The release check validates required files, structured data, version consistency, local Markdown links, committed demo/benchmark/robustness invariants, common secret patterns, compilation, tests, and temporary clean runs. It does not make live external API calls or launch Streamlit/Docker.

## Package artifacts

```bash
make package
```

This builds:

- a Python wheel;
- a clean source ZIP rooted at `kdaa-ai-v<version>/`;
- an internal file manifest with per-file SHA-256 hashes;
- a SHA-256 checksum for the source ZIP.

## Docker

```bash
cp .env.example .env
docker compose build

docker compose run --rm api kdaa demo --output /tmp/demo
docker compose up api
```

Docker availability and live container testing are environment-dependent and should be reported explicitly.

## Run manifest

Every exported run includes:

- software version;
- execution timestamp;
- execution mode;
- random seed;
- configuration digest;
- input digest;
- optional model name;
- warnings and method notes.

## External APIs

Connector tests use local fixtures and mocked responses. A release should not claim live connector validation unless real calls were performed in the documented environment. External schemas, authentication, rate limits, and terms can change independently of the repository.

## LLM experiments

For a reproducible LLM experiment, record:

- provider and endpoint type;
- exact model identifier and date;
- temperature and other sampling settings;
- prompt/template version;
- input trace subset and sensitivity policy;
- token counts, latency, and cost;
- rejected outputs and validation errors;
- repeated-run variation.

Do not place API keys or private traces in the repository.
