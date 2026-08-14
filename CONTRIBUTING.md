# Contributing

Contributions are welcome when they preserve the central epistemic rule: **a trace is not an asset, and a generated hypothesis is not a confirmed asset**.

Before submitting a pull request:

1. Add or update tests for behavior changes.
2. Keep deterministic mode fully functional without an API key.
3. Preserve provenance for every active claim.
4. Document new proxy scores and their limitations.
5. Avoid adding public fixtures that identify a person without a clear lawful and ethical basis.
6. Run `pytest`, `ruff check`, and the synthetic demo.

Large ontology or evaluation changes should include a short design note in `docs/`.
