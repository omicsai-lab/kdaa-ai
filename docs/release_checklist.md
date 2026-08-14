# Release checklist

## Scientific integrity

- [ ] The focal unit is clearly bounded.
- [ ] Every active asset record has supporting trace-level provenance.
- [ ] No AI-only run marks an asset as confirmed.
- [ ] Alternative explanations, exclusions, dependencies, and attribution caveats are retained.
- [ ] Synthetic, public, and private evidence are labeled distinctly.
- [ ] Benchmark and perturbation statements are described as engineering results, not construct validation.
- [ ] Exact duplicates do not inflate analytical support; retained duplicate traces remain auditable in provenance.
- [ ] Paper A, Paper B, and Paper C claims remain separated.

## Privacy, licensing, and governance

- [ ] No private or confidential source data are committed.
- [ ] No credentials, tokens, or model keys are committed.
- [ ] Public-data licenses and redistribution terms have been reviewed.
- [ ] Sensitive inferences are not used for automated high-stakes decisions.
- [ ] AI assistance is disclosed materially and accurately.

## Software quality

- [ ] `python scripts/check_release.py` passes.
- [ ] `pytest --cov=kdaa --cov-report=term-missing` passes the configured threshold.
- [ ] `ruff check .` passes in CI.
- [ ] `python -m compileall -q src app scripts tests` passes.
- [ ] `kdaa demo --scenario researcher --output /tmp/kdaa-demo` succeeds.
- [ ] `kdaa stress-test --output /tmp/kdaa-robustness` succeeds with expected directional invariants.
- [ ] Package wheel builds and includes ontology/report resources.
- [ ] Docker image/Compose configuration is tested in an environment with Docker.
- [ ] Streamlit and FastAPI are smoke-tested in an environment with optional runtime dependencies.

## GitHub and archival metadata

- [ ] Version matches `pyproject.toml`, `src/kdaa/__init__.py`, `CITATION.cff`, and release notes.
- [ ] `CHANGELOG.md` and `RELEASE_NOTES.md` are updated.
- [ ] `CITATION.cff` and `.zenodo.json` identify Georgetown University correctly.
- [ ] README links, figures, and committed result paths resolve.
- [ ] A tagged GitHub release and, when ready, a Zenodo software archive are created.
