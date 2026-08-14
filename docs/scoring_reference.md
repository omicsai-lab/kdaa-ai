# Scoring reference

All scores in v0.1 are **transparent engineering proxies**. They are intended to support inspection, prioritization, ablation, and future construct development. They are not validated psychometric scales, causal estimators, or universal rankings.

## General representation

Every `ScoreDimension` contains:

- `value` in `[0, 1]`;
- `method`, including a versioned method name;
- `rationale` for the current record;
- `uncertainty` in `[0, 1]`;
- `is_proxy=true` by default.

## Asset-level dimensions

### Evidence strength

Combines:

- number of supporting traces;
- number of source kinds;
- number of trace types;
- average trace weight;
- contradicting-link penalty.

The implementation uses logarithmic count terms to limit runaway effects from large trace volumes.

### Attribution confidence

Average configured weight for the contribution roles on supporting traces. This is not a full contributorship model. It does not resolve honorary authorship, collective work, repository commits, PI oversight, or undocumented labor.

### Maturity

Proxy based on repetition, heterogeneity of output types, completion signals, and declared reuse counts.

### Distinctiveness

Proxy based only on record specificity, number of concepts, and combinative/execution category. No external peer, market, or rarity benchmark is included. This dimension has deliberately high uncertainty.

### Tacitness

Higher when support comes from employment, projects, collaborations, or relational categories; lower when support is codified in software, data, protocols, publications, courses, or documents.

### Transferability

Rewards cross-trace-type recurrence and codification; penalizes inferred tacitness.

### Dependency intensity

Uses declared dependencies, number of recurring contributors, relational category, and non-unit ownership indicators.

### Decay risk

Inverse of exponential recency with configurable half-life:

```text
recency = exp(-ln(2) × age_years / half_life_years)
decay_risk = 1 - recency
```

Default half-life: five years.

### Appropriability risk

Higher when evidence is publicly codified and therefore potentially easier to imitate or detach from the focal unit; adjusted for dependency intensity.

### AI interfaceability

Uses trace-modality defaults. Code, data, and structured protocols receive higher interfaceability proxies than employment or relational evidence. Tacitness reduces the value.

### Privacy risk

Uses the fraction of linked traces flagged sensitive and a relational-content increment.

### Overall credibility

Configured weighted combination of:

- evidence strength;
- attribution confidence;
- maturity;
- transferability;
- recency;
- source diversity;
- contradiction penalty.

Default weights are in `configs/default.yaml`.

## Epistemic-state thresholds

Default configuration:

- overall credibility at or above `0.58` → `provisional`;
- below `0.58` → `hypothesis`;
- no threshold can produce `confirmed`;
- calibration is recommended when credibility is below `0.75`, tacitness is high, attribution is weak, or dependency is high.

## Opportunity scores

### Template affinity

Uses overlap among:

- asset categories and template-preferred categories;
- asset text/concepts and template-preferred terms;
- asset discovery namespaces and preferred namespaces.

### Fit

Weighted proxy incorporating template affinity, asset credibility, strategic-goal alignment, distinctiveness, and asset specificity.

### Governance risk

Combination of privacy, appropriability, and dependency proxies.

### AI amplifiability

Opportunity-specific proxy based on AI interfaceability and template affinity, reduced by governance risk. It is not an estimate of Equation 1 in the theory paper and should not be interpreted as realized incremental value.

### Readiness

Combination of maturity, credibility, and AI interfaceability.

### Priority

Combination of fit, amplifiability, readiness, distinctiveness, and inverse governance risk.

## Expected gain vector

Templates define a qualitative vector with dimensions:

- time;
- quality;
- scale;
- accessibility;
- reuse;
- recombination;
- execution span;
- learning;
- cost;
- risk.

Values are template priors adjusted by interfaceability and governance risk. They are hypotheses to be tested, not forecasted outcomes.

## Appropriate use

Use scores to:

- inspect why an asset or opportunity was surfaced;
- compare system variants on the same controlled input;
- select records for human review;
- design ablations and measurement studies;
- identify data needed for stronger assessment.

Do not use scores to:

- rank employees, faculty, students, applicants, or organizations;
- make hiring, promotion, funding, tenure, admission, or compensation decisions;
- claim validated expertise or market value;
- infer causality or future performance;
- compare units with different evidence coverage without a formal study design.
