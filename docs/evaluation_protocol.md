# Evaluation protocol

## Purpose and claim boundary

Version 0.1 includes two controlled evaluation layers:

1. a generated-unit benchmark for ontology recovery, provenance, determinism, and runtime; and
2. a deterministic perturbation suite for duplicate control, recency response, attribution response, evidence removal, and irrelevant-noise resistance.

Both are **software-engineering validation exercises**. They do not establish that a real focal unit possesses a latent knowledge asset, that an opportunity is useful, or that AI creates realized or captured value.

## Synthetic benchmark

### Generator

`SyntheticBenchmarkGenerator` samples two to four latent template families for each synthetic unit and creates two or more traces per family plus noise traces. Unit types include researchers, teams, and laboratories. Ground-truth concept keys remain in bundle metadata for evaluation but are not exposed to the analysis pipeline as input features.

The generator uses the same declared ontology as the system. This makes it useful for regression testing but easier than real-world language, identity resolution, attribution, and ontology shift.

### Baseline

The flat-profile baseline performs keyword/concept aggregation over the evidence bundle but does not create:

- claim-level evidence links;
- bounded claims and exclusions;
- epistemic states;
- asset-level assessments;
- opportunity-specific amplification designs.

It is intentionally simple. Stronger single-shot LLM, retrieval, expert-finder, and agentic baselines are Paper B work.

### Metrics

**Concept precision, recall, and F1.** Generated ground-truth concept keys are compared with concepts surfaced by each method. This measures ontology recovery, not asset validity.

**Provenance completeness.** Proportion of active asset claims with at least one supporting trace link resolving to an input trace.

**Unsupported claim rate.** Proportion of active claims without resolvable supporting evidence.

**Confirmed-without-human rate.** Proportion of assets in `confirmed` state when no calibration record exists. The required value is zero.

**Determinism.** Whether repeated deterministic runs produce the same ordered asset labels, bounded claims, and supporting trace IDs after excluding run IDs and timestamps.

**Runtime.** Mean wall-clock pipeline runtime per generated unit in the execution environment.

### Committed v0.1 result

For 50 generated units with seed 42:

| Metric | Flat-profile baseline | KDAA deterministic pipeline |
|---|---:|---:|
| Concept precision | 0.8171 | 0.8008 |
| Concept recall | 0.5669 | 0.6733 |
| Concept F1 | 0.6610 | 0.7257 |
| Provenance completeness | 0.0000 | 1.0000 |
| Unsupported claim rate | 1.0000 | 0.0000 |
| Confirmed without human | — | 0.0000 |
| Determinism | — | 1.0000 |
| Mean runtime per unit | — | approximately 0.013 seconds in the build environment |

![Synthetic benchmark](assets/benchmark_comparison.png)

Runtime is environment-specific and is not a portable performance guarantee.

## Deterministic perturbation suite

Run:

```bash
kdaa stress-test --output results/robustness
```

The suite starts from the fully synthetic researcher case and applies one controlled transformation at a time:

| Case | Transformation | Expected behavior |
|---|---|---|
| Exact duplicates | Duplicate the first three traces under new IDs | Retain duplicates in provenance; do not inflate analytical support or asset count |
| Stale dates | Set all evidence dates to 2010 | Preserve the asset signature while lowering the recency-dependent credibility proxy |
| Unknown roles | Replace all contribution roles with `unknown` | Preserve the asset signature while lowering attribution confidence |
| Dropped trace | Remove one input trace | Permit bounded structural change rather than forcing invariance |
| Irrelevant noise | Add five administrative traces without ontology content | Preserve the asset signature and scores |

### Committed v0.1 perturbation result

| Measure | Result |
|---|---:|
| Base assets | 32 |
| Exact-duplicate signature Jaccard | 1.0000 |
| Exact-duplicate asset-count change | 0 |
| Exact-duplicate mean-credibility change | 0.0000 |
| Stale-date signature Jaccard | 1.0000 |
| Stale-date mean-credibility change | -0.0439 |
| Unknown-role signature Jaccard | 1.0000 |
| Unknown-role mean-attribution change | -0.6076 |
| One-trace-removed signature Jaccard | 0.7647 |
| Irrelevant-noise signature Jaccard | 1.0000 |
| Provenance complete in every case | true |
| Automatically confirmed assets in every case | 0 |

![Perturbation structural stability](assets/robustness_signature.png)

![Perturbation directional response](assets/robustness_score_deltas.png)

The exact-duplicate safeguard is conservative: it uses source-record identifiers or normalized source/trace identity. It does not resolve semantic near-duplicates, derivative records, or dependence among nominally different sources.

## Required Paper B extensions

A publishable artifact paper should go beyond these smoke tests:

1. **Stronger baselines:** single-shot LLM profile, RAG profile, generic expert finder, and unstructured recommendation agent.
2. **Ablations:** provenance, exclusions, contribution roles, source diversity, ontology groups, goal alignment, and opportunity-template gates.
3. **Harder perturbations:** incorrect author resolution, conflicting evidence, collaborator-heavy records, sparse records, semantic duplicates, and ontology shift.
4. **Model robustness:** models, temperatures, source subsets, prompts, and unit types.
5. **Cost and latency:** tokens, external calls, runtime, memory, and failure/retry behavior.
6. **Reproducibility:** clean environment, container build, frozen cases, generated manifests, and archived artifacts.
7. **Claim audit:** independent review of whether every presented claim is trace-grounded and appropriately bounded.

## Later Paper C evaluation

Human-loop studies should separately assess:

- claim correctness and boundary quality;
- attribution and collective ownership;
- novelty relative to self-understanding and conventional profiles;
- actionability and opportunity fit;
- correction burden;
- perceived surveillance or power effects;
- downstream artifact creation;
- realized and captured value;
- false positives retained or eliminated over time.

Human validation should not be retrofitted as an informal anecdote into the synthetic benchmark.
