# KDAA-AI v0.1.0 release notes

**Release date:** 2026-08-11  
**Status:** research alpha  
**Intended repository:** `omicsai-lab/kdaa-ai`

## Purpose of this release

Version 0.1.0 is the first executable instantiation of the Knowledge Asset Discovery, Assessment, and Amplification framework. It is designed to serve two purposes at once:

1. a usable research MVP that converts heterogeneous traces into auditable asset hypotheses and opportunity designs; and
2. the primary software artifact for the planned Paper B on system design and controlled evaluation.

The release does **not** claim that its provisional assets are true, that its opportunity rankings are useful to real focal units, or that AI has produced realized or captured value. Those questions require later human and longitudinal work.

## Included

- strict focal-unit, evidence-trace, asset, assessment, opportunity, calibration, outcome, and run-manifest models;
- deterministic, provenance-first discovery and an optional provenance-gated LLM mode;
- transparent asset-level proxy assessment;
- opportunity matching across five reusable output containers plus paper and grant pathways;
- local JSON/YAML and CV-like PDF/text ingestion, including a CLI and Streamlit path;
- conservative exact/source-record-equivalent duplicate control that retains original traces and adds duplicate-to-canonical provenance edges;
- OpenAlex and GitHub public-data connectors;
- synthetic researcher, laboratory, and team scenarios;
- command-line, FastAPI, and Streamlit interfaces;
- JSON, CSV, Markdown, HTML, GraphML, and graph-JSON exports;
- synthetic benchmark and flat-profile baseline;
- deterministic perturbation suite for duplicates, staleness, attribution, evidence removal, and irrelevant noise;
- unit tests, coverage threshold, GitHub Actions, Docker assets, governance documents, and release audit;
- theory-to-system, Paper A/B/C boundary, evaluation, scoring, governance, and reproducibility documentation.

## Reproducibility snapshot

The committed researcher demonstration contains:

- 21 synthetic evidence traces;
- 32 hypothesis/provisional asset records;
- 7 amplification opportunities;
- 0 automatically confirmed assets.

The committed 50-unit synthetic benchmark records complete claim-level provenance and zero unsupported active claims in the KDAA pipeline. The perturbation suite leaves the asset signature unchanged under exact duplicates and irrelevant administrative noise, lowers declared score components under stale dates and unknown roles, preserves provenance, and never auto-confirms an asset. Both are engineering tests on generated data, not real-world construct validation.

## Known boundaries

- public identity resolution is basic and must be reviewed;
- contribution and collective ownership are represented but not fully inferred;
- semantic/cross-source duplication and source dependence are not fully resolved;
- distinctiveness is not benchmarked against a real peer population;
- assessment and opportunity scores are transparent design proxies, not validated scales;
- live external services, remote LLM providers, Docker deployment, and the Streamlit runtime depend on the user's environment;
- human calibration and outcome learning are data-model/lifecycle capabilities, not completed empirical validation.

## Suggested GitHub release text

> First public research alpha of KDAA-AI, a provenance-aware platform for turning heterogeneous knowledge traces into falsifiable asset hypotheses, transparent assessment proxies, and opportunity-specific human–AI amplification plans. Includes a deterministic local pipeline, conservative duplicate control, optional LLM augmentation, CV/OpenAlex/GitHub ingestion, synthetic benchmark and perturbation suite, CLI/API/Streamlit interfaces, Docker assets, tests, and full theory-to-artifact documentation. No asset is automatically confirmed.
