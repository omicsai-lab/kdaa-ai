# KDAA Paper B — KBS Claims and Evaluation Freeze

**Document ID:** KDAA-PB-KBS-001  
**Version:** 1.0  
**Status:** **FROZEN FOR IMPLEMENTATION**  
**Freeze date:** 2026-08-22  
**Research owner:** James Li, OmicsAI Lab, Georgetown University  
**Target repository:** `omicsai-lab/kdaa-ai`  
**Target manuscript:** Paper B — computational artifact and evaluation paper  
**First-submission journal:** **Knowledge-Based Systems (KBS)**  
**Fallback journal:** Expert Systems with Applications (ESWA)  
**Software line:** KDAA-AI v0.2.x, built from v0.1.0  
**Predecessor specification:** KDAA-TDE-001 v1.0, dated 2026-08-14  

---

## 0. Authority and use

This document freezes **Step 1 — scientific claims and publication boundary** and **Step 2 — evaluation protocol** for the first KDAA journal paper.

For Paper B, this document narrows and supersedes the predecessor specification’s broad claim and evaluation sections. The predecessor’s DR-01 through DR-12 remain the authoritative architecture and governance requirements unless this document explicitly narrows their role in the main manuscript.

The normative terms **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** have their usual specification meanings.

The evaluation is complete when the prespecified runs are completed and reported—not when KDAA wins. Null, adverse, and failed results SHALL remain in the record. No final-test tuning, result-dependent case replacement, or post hoc baseline weakening is permitted.

---

# Part I — Step 1: Scientific Claim Freeze

## 1. KBS positioning

Paper B is a **knowledge-based AI systems paper**. Its intellectual center is not knowledge-management theory alone, a CV-analysis application, an LLM wrapper, or a software-release description.

The KBS-facing problem is:

> **How can heterogeneous and incomplete knowledge traces be converted into bounded, auditable knowledge-asset hypotheses and opportunity-specific human–AI plans without collapsing evidence into expertise, collective contribution into individual ownership, or machine inference into human confirmation?**

The KBS-facing novelty is a **provenance-constrained knowledge inference and decision-support architecture** that combines:

1. typed multilevel knowledge representation;
2. trace-to-claim provenance constraints;
3. bounded and falsifiable hypothesis records;
4. contribution, dependency, and collective-ownership representation;
5. explicit epistemic states and legal transitions;
6. asset-level rather than person-level assessment;
7. opportunity-specific matching;
8. human–AI task allocation and verification gates; and
9. reproducible deterministic and hybrid execution modes.

The paper SHALL make the computational formalization explicit through data definitions, constraints, scoring rules, state-transition rules, and pseudocode. It SHALL NOT claim a new machine-learning algorithm when the novelty lies at the knowledge-representation, reasoning, and system-design level.

### 1.1 Working title

**KDAA: A Provenance-Constrained Knowledge-Based System for Auditable Knowledge-Asset Hypothesis Formation and Human–AI Opportunity Planning**

A shorter title MAY be chosen at final drafting, but it SHALL preserve the phrases **provenance-constrained**, **knowledge-based system**, and **hypothesis** or an equivalent term that does not imply validated discovery.

### 1.2 One-sentence thesis

> KDAA treats latent knowledge-asset discovery as a provenance-constrained knowledge-inference and opportunity-planning problem rather than as free-form profiling, and evaluates whether the resulting representation and constraints improve grounding, attribution, and opportunity matching under controlled truth while preserving auditability in public-data cases.

### 1.3 Manuscript identity

Paper B SHALL be written as:

> **formal problem definition → theory-derived design requirements → computational architecture → controlled evaluation → design knowledge and failure boundaries**

It SHALL NOT be written as:

> product description → screenshots → favorable examples → claims of real-world usefulness.

---

## 2. Formal problem statement

For a focal unit \(u\), let:

- \(E_u\) be a heterogeneous set of observable evidence traces;
- \(G_u\) be a provenance and dependency graph over the unit, traces, contributors, projects, and source relations;
- \(C_u\) be the strategic, temporal, governance, and opportunity context;
- \(O_u\) be a candidate opportunity set;
- \(H_u\) be a set of bounded knowledge-asset hypotheses;
- \(S_u\) be transparent, multidimensional assessment proxies;
- \(R_u\) be a ranking of candidate opportunities; and
- \(P_u\) be opportunity-specific human–AI task and verification plans.

KDAA implements a constrained mapping:

\[
F_\theta:(u,E_u,G_u,C_u,O_u)\rightarrow(H_u,S_u,R_u,P_u)
\]

subject to at least the following constraints:

1. **Trace–hypothesis separation:** an observable artifact is not automatically an asset.
2. **Provenance:** every active hypothesis references resolvable supporting traces.
3. **Boundedness:** every hypothesis states a mobilizable capability and a scope, exclusion, alternative, dependency, or missing-evidence condition.
4. **Attribution:** individual, shared, organizational, external, and unresolved contribution states remain distinguishable.
5. **Epistemic discipline:** AI-only output cannot transition to confirmed, narrowed, split, or rejected without an explicit calibration record.
6. **Opportunity specificity:** matching is defined over asset–opportunity–context combinations, not a unit-wide prestige or expertise score.
7. **Governed amplification:** plans identify human tasks, AI tasks, verification gates, baseline, expected gain dimensions, cost, and risk.
8. **Contestability and purpose limitation:** outputs remain auditable, correctable, and prohibited from automated high-stakes personnel decisions.

---

## 3. Frozen research questions

### RQ1 — Computational operationalizability and invariants

> Can a theory-derived, provenance-constrained representation be implemented so that evidence traces, asset hypotheses, assessments, opportunities, plans, and epistemic states remain distinct, auditable, and reproducible, with no AI-only confirmation?

RQ1 is answered by architecture inspection, schemas, property tests, validators, state-transition tests, and clean-environment reproducibility. These are **system guarantees**, not empirical superiority claims.

### RQ2 — Comparative knowledge inference

> Under hidden synthetic truth, how do deterministic and hybrid KDAA configurations compare with a strong flat semantic profile, a generic single-shot LLM, and an evidence-ID/RAG LLM in asset-concept recovery, unsupported overreach, attribution, and opportunity ranking?

RQ2 is the main empirical question.

### RQ3 — Mechanism necessity, robustness, and cost

> Which KDAA constraints account for observed behavior, and how robust are those behaviors to evidence dependence, missingness, contradiction, identity ambiguity, collective production, ontology shift, opportunity-context change, and model or prompt variation, at what computational cost?

RQ3 is answered by ablation, perturbation, stability, and efficiency analyses.

### Ecological demonstration objective

Public cases answer a narrower descriptive question:

> Can the frozen system ingest real, messy public traces and preserve provenance, attribution caveats, epistemic boundaries, and governance warnings, and what failure modes become visible?

This is not a fourth validity question and SHALL NOT be reported as proof that the inferred assets are true.

---

## 4. Frozen contribution claims

Paper B may contain three principal contribution claims.

### Claim C1 — Computational formalization

KDAA provides a formal, executable representation that separates traces, hypotheses, assessments, opportunities, plans, and outcomes, and enforces provenance, attribution, epistemic-state, and governance constraints.

**Evidence class:** architecture, code, schemas, tests, and invariants.  
**Permitted strength:** unconditional if all software quality gates pass.  
**Not permitted:** “the theory is empirically validated.”

### Claim C2 — Comparative behavior

Under hidden controlled truth, the full deterministic and/or hybrid KDAA configurations exhibit measurable differences from specified practical alternatives in one or more of:

- asset-concept recovery;
- semantic unsupported-claim rate;
- false individualization;
- opportunity-ranking quality; and
- robustness under controlled perturbation.

**Evidence class:** paired benchmark comparisons with uncertainty.  
**Permitted strength:** conditional on observed effects.  
**Not permitted:** a blanket “KDAA is superior” statement unless the complete result pattern supports it.

### Claim C3 — Design knowledge

Ablations and perturbations identify which provenance, dependence, attribution, asset-level, opportunity-specific, and verification mechanisms materially affect system behavior and reveal trade-offs among breadth, grounding, stability, and cost.

**Evidence class:** prespecified component removal and stress testing.  
**Permitted strength:** conditional on observed effects, including null or adverse effects.  
**Not permitted:** claiming that every theory-derived feature is necessary.

### Supporting ecological statement

KDAA can process a prespecified set of public professional evidence bundles and produce inspectable provisional records while preserving source manifests, caveats, and non-certification language.

This is a demonstration statement, not a principal validity claim.

---

## 5. Claims explicitly prohibited in Paper B

Paper B SHALL NOT claim that:

1. KDAA discovers the “true” latent knowledge assets of a real person, team, or organization.
2. A publication, repository, grant, patent, title, coauthorship, or public profile proves personal contribution, ownership, tacit capability, or current availability.
3. The assessment dimensions are validated psychometric or organizational constructs.
4. A high proxy score certifies expertise, merit, employability, scientific quality, or future value.
5. KDAA recommendations are useful, fair, legitimate, trusted, or preferred by users.
6. KDAA creates realized or captured value.
7. the system improves hiring, tenure, promotion, admissions, compensation, grant allocation, or workforce decisions.
8. public availability creates unrestricted permission to infer, redistribute, rank, or monetize.
9. a synthetic benchmark validates real-world construct validity.
10. a held-out public self-description is complete ground truth for a person’s knowledge assets.
11. deterministic compliance with a software rule proves substantive correctness.
12. AI-only `hypothesis` or `provisional` records are confirmed knowledge assets.

The preferred manuscript phrase is:

> **evidence-grounded knowledge-asset hypothesis**

not:

> **discovered knowledge asset**

unless referring to a later human-calibrated record outside the Paper B evidence.

---

## 6. A/B/C publication firewall

| Dimension | Paper A — Define | Paper B — Build | Paper C — Test with humans |
|---|---|---|---|
| Primary object | theory of AI-amplified knowledge assets | computational representation and artifact | human calibration and downstream use |
| Main question | what the construct is and how mechanisms operate | how the construct can be operationalized and evaluated computationally | whether hypotheses are correct, novel, useful, fair, and value producing |
| Owned content | definitions, mechanisms, propositions, boundary conditions, value creation/capture | formal objects, constraints, architecture, algorithms, baselines, ablations, robustness, reproducibility | confirmation/rejection/split rates, correction burden, trust, usefulness, legitimacy, realized/captured value |
| Evidence | literature synthesis, theoretical argument, illustrative reasoning | synthetic hidden truth, system tests, public ecological cases | participants, experts, organizations, outcomes, longitudinal observations |
| Prohibited borrowing | no Paper B result tables or software-performance claims | no full reproduction of Paper A propositions or human-validity claims | no relabeling of Paper B synthetic results as human validity |
| Output status | theoretical framework | auditable hypotheses and plans | calibrated assets and observed consequences |

Additional firewall rules:

1. Every primary table, figure, endpoint, and result SHALL have one home paper.
2. Paper B may summarize only the minimum theory required to justify its design requirements.
3. Paper B SHALL be self-contained even if Paper A is unpublished or pending.
4. If Paper A or C is under review when B is submitted, the related manuscript SHALL be disclosed to the editor and supplied if requested.
5. No substantial paragraph, figure, table, or result shall be duplicated across manuscripts.
6. Paper C should evaluate a frozen, versioned Paper B system rather than an evolving prototype.
7. Paper A may cite Paper B as a computational instantiation after B is public; B may cite a public Paper A preprint, but B shall not depend on inaccessible theory.

---

## 7. Terminology lock

| Term | Paper B meaning |
|---|---|
| Evidence trace | observable artifact, event, relation, or metadata record |
| Asset hypothesis | bounded, falsifiable, evidence-linked proposition about a mobilizable capability |
| Knowledge asset | human-calibrated or otherwise independently validated asset record; not produced automatically in Paper B |
| Assessment proxy | transparent engineering measure with uncertainty; not a validated scale |
| Opportunity | concrete beneficiary–problem–output–timing–channel configuration |
| AI amplifiability | opportunity-specific counterfactual change under a governed human–AI configuration; represented but not causally validated |
| Realized value | observed downstream benefit; outside Paper B |
| Captured value | portion of realized value retained by or legitimately attributable to the focal unit; outside Paper B |
| Confirmation | explicit human calibration state transition; never generated by score threshold |

---

# Part II — Step 2: Evaluation Protocol Freeze

## 8. Evidence architecture

Paper B SHALL keep four evidence layers separate.

### Layer 0 — System invariants

Schema, validator, state-machine, privacy, and reproducibility tests. These establish that the software behaves as specified.

### Layer 1 — Controlled empirical comparison

A frozen synthetic benchmark with hidden truth evaluates recovery, unsupported overreach, attribution, and opportunity ranking.

### Layer 2 — Mechanism and robustness evaluation

Ablations and perturbations evaluate which design elements matter and where behavior fails.

### Layer 3 — Public ecological demonstration

Prespecified public cases evaluate ingestion, provenance, auditability, identity ambiguity, attribution caveats, and operational failure modes. They do not establish asset truth or usefulness.

Engineering efficiency and reliability are reported across all applicable layers.

---

## 9. Data and case design

### 9.1 Development set

A separate **development set of at least 60 synthetic units** SHALL be created using seeds and templates disjoint from the final evaluation set.

The development set MAY be used for:

- debugging;
- choosing fixed matching thresholds;
- tuning the strong flat semantic baseline;
- finalizing prompts and output schemas;
- validating the scorer; and
- estimating run cost.

Development results SHALL NOT be reported as final evidence.

### 9.2 Frozen synthetic evaluation set

The final synthetic evaluation set SHALL contain **240 focal units**:

#### Core factorial set: \(N=180\)

Balanced over:

- unit type: individual researcher, team, laboratory;
- evidence density: sparse, dense;
- domain breadth: single-domain, interdisciplinary;
- attribution regime: clear/individual, shared/collective, unknown/ambiguous; and
- five independently seeded replicates per cell.

This yields:

\[
3 \times 2 \times 2 \times 3 \times 5 = 180
\]

Each case SHOULD contain:

- 2–5 true asset concepts;
- 12–40 evidence traces depending on density;
- supporting, contextual, contradictory, dependent, stale, and irrelevant traces as appropriate;
- explicit hidden ownership and dependency states; and
- a candidate catalog of 10 opportunities with hidden graded relevance \(0,1,2,3\).

#### Challenge set: \(N=60\)

Ten prespecified categories, six cases per category:

1. ontology shift, paraphrases, and unseen synonyms;
2. interdisciplinary or composite assets;
3. trace-as-asset decoys and prestige distractors;
4. semantic near-duplicates and cross-source dependence;
5. stale/current conflict and contradictory evidence;
6. collaborator-heavy production and unknown roles;
7. identity collision or incorrect entity resolution;
8. sparse evidence and missing support;
9. irrelevant administrative noise and sensitive traces; and
10. opportunity-context reversal, infeasible opportunities, or unsafe delegation.

The challenge set SHALL use surface forms, combinations, and distractors not available to the inference code or prompts as direct truth labels.

### 9.3 Ground-truth structure

Ground truth SHALL include, at minimum:

- canonical asset concepts and hidden aliases;
- trace-to-concept support relations;
- contradiction and context relations;
- scope and temporal validity;
- contribution and ownership state;
- external and infrastructure dependencies;
- candidate-opportunity relevance grades;
- expected direction under applicable perturbations;
- sensitive-data flags; and
- challenge-category labels.

### 9.4 Leakage prevention

1. Final truth SHALL be stored outside model-visible bundles and outside inference-accessible metadata.
2. Truth files SHALL be hashed and frozen before final runs.
3. Inference code SHALL write prediction files before scoring code can read truth.
4. Final seeds, case IDs, and LLM subsets SHALL be frozen before model execution.
5. Prompt payloads, filenames, trace text, and metadata SHALL be scanned for truth-only labels.
6. No final case may be replaced after results are seen.
7. No threshold, ontology alias, or baseline parameter may be tuned on final outcomes.
8. Any protocol amendment after freeze SHALL be versioned, justified, and labeled exploratory unless caused by a documented software defect.

### 9.5 LLM comparison subset

A prespecified **60-case subset** SHALL be selected before any final LLM run:

- 30 core cases;
- 30 challenge cases;
- balanced as far as possible over unit type, density, domain breadth, and attribution regime.

C1, C2, and C4 SHALL each be run **three times per case**. The primary LLM summary is the within-case mean across all three intended runs. Best-of-three selection is prohibited.

### 9.6 Ablation subset

A prespecified **48-case subset** SHALL be selected:

- 24 core cases;
- 24 challenge cases;
- enriched for cases where the ablated mechanism is relevant.

Full C4 and each principal ablation SHALL be run three times per case when stochastic generation is involved.

### 9.7 Public ecological set

A prespecified set of **12 independent public focal units** SHALL be selected before KDAA outputs are inspected:

- approximately eight individuals and four collective units;
- at least three substantive domains;
- at least two sparse cases;
- at least two collaborator-heavy or collective-production cases;
- stable public identifiers where available; and
- at least two public source classes per standard case when feasible.

A separate **author-controlled illustrative case** MAY be included for richer contextual discussion but SHALL NOT enter aggregate public-case metrics.

Allowed sources include public scholarly identifiers, publication metadata, repository metadata, official institutional pages, public CVs where use is permitted, and public grant or patent metadata where appropriate. Full raw content SHALL be redistributed only when source terms allow it.

---

## 10. Comparator lock

All systems receive the same focal-unit boundary, normalized evidence content, fixed evidence order for that case, candidate opportunity catalog for the ranking task, and output-count limits.

### C0-L — Legacy flat lexical profile

The current keyword/concept aggregation baseline is retained as a smoke-test and continuity comparator. It is not the principal baseline for KBS claims.

### C0-S — Strong flat semantic profile

The primary deterministic baseline SHALL:

- use a frozen local lexical plus sentence-embedding representation;
- map traces to a controlled concept vocabulary;
- aggregate concept support at the unit level;
- return at most 10 ranked concepts;
- rank the common opportunity catalog using semantic fit; and
- avoid KDAA asset records, claim-level provenance validation, attribution modeling, epistemic states, multidimensional assessment, and task/gate planning.

Its model, revision hash, thresholds, and weights SHALL be selected only on development data.

### C1 — Generic single-shot LLM

One generic prompt asks a fixed model to identify up to 10 candidate knowledge capabilities and rank the common opportunity catalog. It receives the same evidence text but no KDAA definitions, provenance requirement, state machine, attribution schema, or planning gates.

A minimal evaluation-neutral JSON schema MAY be required for parseability. That schema shall not introduce KDAA design knowledge.

### C2 — Generic evidence-ID/RAG LLM

C2 receives the same evidence content with stable trace IDs and retrieval context. It is asked to cite evidence IDs for its candidate claims and rank the common opportunity catalog, but it does not receive the KDAA ontology, assessment dimensions, epistemic state machine, attribution rules, bounded-claim requirements, or task/gate planning structure.

### C3 — KDAA deterministic

The transparent rule-, ontology-, provenance-, assessment-, and opportunity-based pipeline. It is the reproducible knowledge-based system anchor.

### C4 — KDAA hybrid

The full KDAA pipeline with the same base model used by C1 and C2 plus:

- typed KDAA output schema;
- trace-level provenance;
- claim validation;
- boundedness fields;
- attribution and dependency representation;
- epistemic constraints;
- asset-level assessment;
- opportunity-specific matching; and
- human–AI task and verification plans.

### C4-R — Resource-matched KDAA sensitivity configuration

On a frozen 30-case subset, a compact one-call KDAA schema plus deterministic validation SHALL operate under the same total model-call count and approximately the same token ceiling as C2. This separates the effect of KDAA design knowledge from the extra computation of the full multi-stage system.

---

## 11. Primary comparisons

### P1 — Deterministic architecture comparison

\[
C3 \; \text{versus} \; C0\text{-}S
\]

Run on all 240 synthetic cases.

### P2 — Full hybrid versus generic LLM

\[
C4 \; \text{versus} \; C1
\]

Run on the 60-case LLM subset with three intended repeats.

### P3 — Full hybrid versus evidence-ID/RAG LLM

\[
C4 \; \text{versus} \; C2
\]

Run on the same 60 cases and repeats.

### Prespecified secondary comparisons

- C2 versus C1: incremental effect of evidence IDs/retrieval context;
- C4 versus C3: breadth–stability–cost trade-off, not a required superiority test;
- C4-R versus C2: design-knowledge effect under resource matching;
- C0-S versus C0-L: strength gained by a non-strawman semantic baseline.

No other comparison is primary.

---

## 12. Fair-comparison rules

1. C1, C2, C4, and C4-R SHALL use the same exact base-model snapshot within a controlled comparison.
2. The primary model SHALL be locked before final runs; post hoc model shopping is prohibited.
3. All systems SHALL receive semantically identical evidence content. IDs may differ only where the comparator definition requires them.
4. Each system may output no more than 10 asset/capability candidates and must rank the same 10 opportunity candidates.
5. Input order SHALL be fixed per case and shared across systems. An order-randomization sensitivity analysis MAY be performed separately.
6. Prompt templates, schemas, model settings, decoding settings, and hashes SHALL be committed.
7. Output adapters may parse, normalize labels, and map fields to the evaluation schema; they SHALL NOT add claims, evidence, attribution, or opportunities.
8. Invalid JSON, refusal, timeout, truncation, and validation failure SHALL be retained and counted.
9. The primary practical comparison need not equalize total calls because architecture is part of the system; calls, tokens, latency, and cost SHALL be reported.
10. C4-R provides the prespecified resource-matched sensitivity.
11. No baseline may receive less evidence merely to make KDAA appear better.
12. No KDAA-only postprocessing may be silently applied to baseline outputs.

---

## 13. Ablation lock

### Main-text ablations

| ID | Ablation | Removed mechanism | Primary diagnostic outcome |
|---|---|---|---|
| A1 | No provenance gate | accept claims without valid trace-linked validation | semantic unsupported claims; invalid evidence links |
| A2 | No duplicate/dependence control | count exact, equivalent, and dependent traces as independent support | support, credibility, count, and rank inflation |
| A3 | No attribution/dependency adjustment | ignore roles, collaborators, shared production, and external dependencies | false individualization; attribution confidence |
| A4 | Unit-level profile | collapse asset-level representation into one unit/topic profile | concept resolution and opportunity nDCG@5 |
| A6 | No opportunity-specific matching | use generic recommendations based on unit topics | opportunity nDCG@5; context sensitivity |
| A7 | No human/AI tasks or verification gates | produce plans without role allocation or accountability gates | unsafe/ungated plan rate; plan completeness |

### Supplementary ablations

| ID | Ablation | Role |
|---|---|---|
| A5 | Replace multidimensional assessment with raw support count or one flat score | tests whether decomposed assessment changes ranking and perturbation response |
| A8 | Unconstrained recombination | tests candidate explosion and unsupported combinations |
| A9 | Collapse provisional and confirmed epistemic states | governance failure demonstration only; never a normal operating mode |

A9 SHALL NOT be described as a viable system configuration.

Ablations must remove a genuine mechanism while holding evidence, model, output limits, and unrelated components constant. Deliberately weak prompts are prohibited.

---

## 14. Perturbation lock

The perturbation suite SHALL cover the following families.

| Family | Controlled change | Expected full-system direction |
|---|---|---|
| Redundancy and dependence | exact duplicates, source-equivalent duplicates, semantic near-duplicates, derivative sources | no inflation for exact/equivalent duplicates; semantic-dependence limitations explicitly measured |
| Recency and missingness | stale dates, dropped support, sparse records | lower recency/credibility; possible lower recovery; no unsupported new asset |
| Attribution and collectivity | unknown roles, collaborator-heavy records, collective ownership | lower attribution confidence; no increase in sole ownership |
| Contradiction | contradictory evidence or incompatible claims | contradiction flag and/or lower confidence; bounded claim or abstention |
| Identity | name collision, incorrect author merge, ambiguous entity | quarantine, split, or warning rather than confident merged attribution |
| Noise and sensitivity | administrative noise, irrelevant traces, sensitive traces | stable concept signature where irrelevant; no remote sensitive-data transmission by default |
| Ontology shift | unseen synonyms, paraphrases, new combinations | measured graceful degradation and alias-recovery limits |
| Opportunity context | same asset with changed beneficiary, timing, baseline, resources, or risk | opportunity rank or task plan changes when context materially changes |
| Model and prompt | second model family, prompt paraphrase, supported decoding variation | variation quantified; no hidden selection of favorable run |

Deterministic perturbations SHOULD run on all applicable final cases. LLM-sensitive perturbations SHALL run on a frozen challenge subset of at least 30 cases.

---

## 15. Outcome hierarchy

### 15.1 Hard system invariants

These are quality gates, not comparative empirical endpoints.

For the full KDAA configurations:

1. claim-level provenance completeness after validation = 1.00;
2. invalid trace-reference rate after validation = 0.00;
3. automatic-confirmation rate without calibration = 0.00;
4. illegal state-transition acceptance rate = 0.00;
5. sensitive-trace transmission in default remote mode = 0.00;
6. deterministic exact reproducibility for fixed input/configuration = 1.00;
7. every active opportunity references at least one asset hypothesis;
8. every public report includes non-certification and confirmation-required language.

Any failed invariant is a software defect that must be corrected before final evaluation is considered valid. The original failure record SHALL be preserved.

### 15.2 Four primary empirical endpoints

#### E1 — Macro asset-concept F1

For case \(i\), predicted top-10 concepts \(P_i\) are matched one-to-one to hidden true concepts \(T_i\) using a frozen evaluation mapper:

1. normalized exact/alias match;
2. frozen embedding similarity with threshold chosen on development data; and
3. unresolved predictions remain unmatched.

Maximum-weight bipartite matching prevents one broad prediction from matching multiple truths.

\[
F1_i = \frac{2\,Precision_i\,Recall_i}{Precision_i+Recall_i}
\]

The primary summary is macro mean \(F1_i\) over cases. Exact-only, hierarchical, and threshold-sensitivity scores are secondary.

#### E2 — Semantic unsupported-claim rate

Each predicted claim is evaluated against hidden truth and trace-to-truth relations. A claim is unsupported if it asserts at least one positive atom not supported by the evidence/truth structure, including:

- nonexistent capability concept;
- materially overbroad scope;
- unsupported currentness;
- contradicted dependency;
- unsupported sole ownership; or
- capability inference with no compatible supporting trace.

\[
SUCR_i = \frac{\#\text{unsupported active claims in case }i}
{\#\text{active claims in case }i}
\]

A severity-weighted version is secondary. This endpoint is distinct from the software invariant “has a valid trace ID”: a claim may cite an existing trace and still be substantively unsupported.

#### E3 — False individualization rate

Among recovered truth assets whose ownership is shared, organizational, external, or unresolved:

\[
FIR_i =
\frac{\#\text{recovered non-individual assets represented as sole individual ownership}}
{\#\text{recovered truth assets with non-individual or unresolved ownership}}
\]

Cases without an applicable denominator are excluded only from this endpoint and remain in all others. Attribution coverage and abstention are reported to prevent a no-attribution strategy from appearing artificially safe.

#### E4 — Opportunity-ranking nDCG@5

Each case supplies the same 10 candidate opportunities to every system. Hidden relevance grades are \(0\)–\(3\).

\[
nDCG@5 = \frac{DCG@5}{IDCG@5}
\]

The ranking task is primary because it permits fair comparison. Open-ended opportunity generation is secondary and is evaluated for specificity, completeness, provenance, and safety rather than against an artificial single “correct” text.

### 15.3 Secondary outcomes

Secondary outcomes include:

- concept precision, recall, micro F1, and top-k recall;
- evidence-link precision and recall;
- boundedness/falsifiability-field completeness;
- attribution coverage and dependency completeness;
- MRR and top-k opportunity recall;
- plan beneficiary/problem/output/baseline completeness;
- human-task, AI-task, and verification-gate coverage;
- unsafe or ungated plan rate;
- duplicate inflation in support, score, asset count, and opportunity rank;
- contradiction response;
- asset-signature Jaccard similarity;
- opportunity-rank Spearman correlation;
- held-out public-anchor recall;
- runtime, calls, tokens, estimated cost, failures, retries, and peak memory;
- exact and semantic repeated-run stability; and
- candidate explosion and unsupported-combination rate.

No arbitrary composite “overall KDAA score” shall be the primary conclusion.

---

## 16. Statistical analysis lock

### 16.1 Unit of analysis

The primary unit is the focal unit/case. Claim-level observations are nested and SHALL NOT be treated as independent cases.

### 16.2 Repeated LLM runs

For C1, C2, C4, and applicable ablations:

- three intended runs per case;
- primary case value = arithmetic mean across all intended runs;
- no best-run, successful-run-only, or majority-selected result as the primary analysis;
- run-level variability reported separately.

### 16.3 Effect reporting

For each primary contrast and applicable primary endpoint, report:

- paired case-level difference;
- mean and median difference;
- 95% confidence interval;
- standardized or interpretable effect size; and
- the full distribution or case-level plot where practical.

Use **10,000 paired bootstrap resamples at the case level**. For repeated LLM outputs, retain all runs within the resampled case. A paired permutation test MAY provide a sensitivity p-value.

If inferential p-values are reported, use Holm adjustment across the prespecified 12 primary contrast–endpoint combinations:

- 3 primary contrasts;
- 4 primary endpoints.

Secondary families use Benjamini–Hochberg FDR control when formal p-values are shown. Interpretation SHALL emphasize effect sizes and uncertainty, not thresholded significance alone.

### 16.4 Practical-effect reference values

The following are interpretation aids, not publication or suppression criteria:

- concept F1 or nDCG@5 absolute difference: 0.05;
- unsupported-claim or false-individualization absolute rate difference: 0.10.

Smaller effects may still be informative if consistent and inexpensive; larger effects may be unimportant if obtained through excessive cost or failure.

### 16.5 Subgroup analyses

Prespecified subgroup summaries:

- core versus challenge;
- individual versus collective unit;
- sparse versus dense evidence;
- single-domain versus interdisciplinary;
- clear versus shared/unknown attribution.

Subgroup analyses are descriptive unless a formal interaction model is explicitly prespecified before final runs.

### 16.6 Failures and missingness

- No failed call may be silently replaced without preserving the failed attempt.
- Retry policy SHALL be fixed in advance, with no more than two automatic retries per intended run unless a provider-wide outage is documented.
- For concept F1 and nDCG@5, final failed runs receive zero in the intent-to-evaluate primary analysis.
- For SUCR and FIR, report successful-output estimates plus a worst-case sensitivity assigning failed runs the maximum adverse rate.
- Report intent-to-run, successful-run, parse-valid, and validator-valid denominators.
- Complete-case results may appear only as secondary sensitivity analyses.

---

## 17. Public-case protocol

### 17.1 Selection

The 12 cases SHALL be selected from a written manifest before outputs are viewed. The manifest records:

- case ID and unit type;
- stable identifiers;
- domain;
- inclusion rationale;
- expected source classes;
- retrieval date;
- source/license notes;
- identity ambiguity;
- known exclusions;
- sparse or collaborator-heavy status; and
- whether a suitable held-out self-description anchor exists.

Selection shall avoid a sample composed only of famous, unusually prolific, or exceptionally well-documented researchers.

### 17.2 Held-out anchor analysis

Where an official self-description or lab mission statement exists:

1. it SHALL be excluded from system input;
2. broad anchor concepts SHALL be coded and frozen before viewing KDAA output;
3. the source text need not be redistributed; identifiers, hashes, and coded concepts are sufficient;
4. top-k concordance/recall may be reported as a secondary ecological measure.

The anchor is evidence of public self-description, not complete truth and not proof of a latent asset.

### 17.3 Public-case audit

Each case SHALL receive a structured audit covering:

1. identity resolution;
2. source coverage;
3. source and retrieval manifest;
4. trace–hypothesis separation;
5. valid provenance;
6. attribution and ownership caveats;
7. boundedness and falsifiability;
8. sensitive-data handling;
9. opportunity and plan completeness;
10. statements requiring human confirmation;
11. failure modes; and
12. explicit non-validation language.

### 17.4 Worked cases

Two worked cases SHALL be presented:

- one independent difficult public case; and
- one separate author-controlled case, if used.

The author-controlled case may illustrate contextual interpretation but SHALL be labeled as such and excluded from aggregate performance claims.

### 17.5 Ethical and governance constraints

- Use only public professional traces with a legitimate research purpose.
- Do not infer protected, intimate, medical, political, religious, or other sensitive personal attributes.
- Do not rank public individuals against one another.
- Do not issue high-stakes recommendations.
- Review source terms, redistribution rights, and institutional requirements before release.
- Use case IDs in aggregate tables; name a case in the manuscript only when ethically and analytically justified.
- Preserve correction, removal, and contestability procedures in the repository.

---

## 18. Model, prompt, and robustness lock

Before final LLM execution, the experiment manifest SHALL record:

- provider;
- exact model identifier and snapshot/revision;
- access date;
- decoding settings;
- context and output limits;
- tool/retrieval settings;
- prompt and schema hashes;
- retry policy; and
- price schedule used for cost estimation.

The primary model is selected for stable structured output and reproducible availability—not after comparing final benchmark performance.

A secondary model-family robustness block SHALL use at least 24 challenge cases. Prompt robustness SHALL use at least two meaning-preserving prompt variants on the same frozen cases. These are secondary analyses and shall not redefine the primary system.

---

## 19. Engineering and reproducibility requirements

The evidence package SHALL record:

- Git commit and software version;
- Python and dependency environment;
- OS/hardware/runtime notes;
- configuration and input digests;
- random seeds;
- model and prompt metadata;
- raw, parsed, and validated outputs;
- failures and retries;
- stage-level latency;
- tokens and estimated cost;
- all case manifests; and
- figure/table generation provenance.

Required top-level workflow:

```bash
make paper-b-eval
```

External retrieval and paid LLM calls MAY be separate cacheable stages, but frozen normalized inputs and raw outputs SHALL permit complete local rescoring and figure regeneration.

All manuscript tables and figures SHALL be generated programmatically from committed result files. A clean environment SHALL reproduce all non-paid analyses. CI SHALL cover supported Python versions and core research invariants.

---

## 20. Experiment matrix

| Block | Cases | Configurations | Repeats | Primary role |
|---|---:|---|---:|---|
| Deterministic main | 240 | C0-S, C3; C0-L secondary | deterministic repeats for exactness | RQ2 full benchmark |
| LLM main | 60 | C1, C2, C4 | 3 | RQ2 practical LLM comparison |
| Resource matched | 30 | C2, C4-R | 3 | compute-controlled sensitivity |
| Main ablations | 48 | C4 + A1, A2, A3, A4, A6, A7 | 3 when stochastic | RQ3 mechanism diagnosis |
| Supplementary ablations | 24–48 | A5, A8, A9 | as specified | secondary design/governance evidence |
| Deterministic perturbations | all applicable final cases | C3 and relevant ablations | deterministic | robustness and expected direction |
| LLM perturbations | at least 30 challenge cases | C4, selected baselines | 3 where primary-model variation is assessed | robustness |
| Model/prompt block | at least 24 challenge cases | primary model, second model family, prompt variants | fixed in manifest | transfer/stability |
| Public ecological | 12 independent + optional author case | C3 and/or frozen C4 | fixed | operational audit, not truth |
| Reproducibility | representative full workflow | frozen release | clean rerun | artifact integrity |

---

## 21. Main manuscript result architecture

### Main tables

1. Theory-derived requirements, computational mechanisms, and evidence role.
2. Dataset, comparator, output, and resource summary.
3. Primary paired results for C3 versus C0-S and C4 versus C1/C2.
4. Main ablation effects.
5. Robustness, stability, efficiency, and failure summary.

### Main figures

1. Formal KDAA architecture and constrained data flow.
2. Evaluation design and evidence-layer separation.
3. Primary comparative effects with 95% confidence intervals.
4. Ablation effect plot.
5. Robustness and quality–cost trade-off.
6. One worked provenance graph or trace-to-hypothesis-to-opportunity case.

Detailed metrics, full prompts, all secondary ablations, per-stratum tables, and public-case audits SHOULD move to the supplement or repository.

---

## 22. KBS-readiness and claim-escalation gate

The result package is technically ready for a KBS manuscript only when:

1. every hard invariant passes in the final release;
2. the strong flat semantic and two LLM baselines are implemented fairly;
3. final truth is leakage-separated and frozen;
4. all three primary contrasts and four primary endpoints are complete;
5. at least the six main ablations are complete;
6. challenge and public-case failure analyses are retained;
7. every main number is reproducible from committed files; and
8. claims are rewritten to match the observed evidence.

KBS remains a defensible first target when the final evidence shows at least one of the following:

- a meaningful comparative advantage on grounding, attribution, recovery, or opportunity ranking without a severe compensating failure;
- a clear and useful breadth–stability–cost trade-off;
- strong ablation evidence that the proposed knowledge-based constraints materially change behavior; or
- novel, well-supported design knowledge about when provenance-constrained knowledge inference succeeds or fails.

If full KDAA is indistinguishable from practical baselines and its ablations have no meaningful effects, the correct response is to narrow the contribution and reconsider venue or design—not to tune on the final benchmark or suppress results.

---

## 23. Change control

After this freeze:

- changes to final case counts, seeds, primary endpoints, main contrasts, or ablations require a versioned amendment;
- software-defect corrections are permitted, but affected runs must be invalidated and rerun for every comparator under the same conditions;
- provider deprecation or model unavailability must be documented before replacement;
- exploratory analyses must be labeled as such;
- unfavorable findings remain reportable; and
- the final manuscript must include a deviations table, even if it states “none.”

---

## 24. Definition of done for Step 1 + Step 2

Step 1 is complete when:

- [x] KBS is frozen as first-submission journal.
- [x] the problem, thesis, three claims, and three RQs are frozen.
- [x] permitted and prohibited claims are explicit.
- [x] A/B/C intellectual and empirical boundaries are explicit.
- [x] terminology is locked around evidence-grounded hypotheses rather than validated assets.

Step 2 is complete when:

- [x] development, final synthetic, challenge, LLM, ablation, and public-case sets are specified.
- [x] practical baselines and fairness rules are frozen.
- [x] six main and three supplementary ablations are specified.
- [x] perturbation families and expected directions are specified.
- [x] four primary empirical endpoints are defined.
- [x] hard invariants are separated from empirical outcomes.
- [x] statistical, failure, cost, and reproducibility rules are frozen.
- [x] KBS-readiness and change-control rules are defined.

Implementation is not complete until the repository contains the corresponding code, manifests, frozen data, outputs, and tests.

---

## 25. Immediate repository deliverables

The implementation sprint SHALL create or update:

```text
docs/
  paper_b_kbs_claims_evaluation_freeze.md
  paper_b_claims_and_limitations.md
  theory_revision_log.md
  public_case_protocol.md
  protocol_deviations.md

configs/paper_b/
  experiment_lock.yaml
  model_lock.yaml
  comparator_configs/
  ablation_configs/
  perturbation_configs/

data/
  development/
  synthetic/
    final_evidence/
    final_truth/
    challenge/
  public_cases/
    manifest.csv
    normalized/
    retrieval_manifests/
    held_out_anchors/

prompts/
  baselines/
  kdaa/
  versions.json

results/paper_b/
  manifests/
  raw/
  parsed/
  validated/
  metrics/
  audits/
  tables/
  figures/

scripts/
  freeze_paper_b_cases.py
  validate_truth_leakage.py
  run_paper_b_experiments.py
  run_paper_b_ablations.py
  run_paper_b_perturbations.py
  score_paper_b_outputs.py
  audit_public_cases.py
  build_paper_b_tables.py
  build_paper_b_figures.py

tests/
  test_paper_b_invariants.py
  test_truth_separation.py
  test_comparator_fairness.py
  test_ablation_switches.py
  test_public_case_manifests.py
  test_paper_b_reproducibility.py
```

---

## Appendix A — Frozen contribution paragraph

Subject to completed results, the manuscript contribution paragraph should take this form:

> We formulate knowledge-asset hypothesis formation as a provenance-constrained knowledge-inference problem and implement KDAA, a knowledge-based system that separates observable traces from bounded capability hypotheses, represents uncertainty, attribution, dependencies, and epistemic state, and links hypotheses to opportunity-specific human–AI plans. We evaluate the deterministic and hybrid system against a strong flat semantic profile, a generic single-shot language model, and an evidence-ID/RAG language model using leakage-separated synthetic truth, prespecified challenge cases, component ablations, robustness tests, and public-data audits. The study establishes computational operationalizability and identifies the behavioral effects and limitations of theory-derived constraints; human correctness, usefulness, legitimacy, and realized or captured value remain separate empirical questions.

This paragraph SHALL be narrowed wherever final evidence does not support a clause.

---

## Appendix B — Reviewer attack map

| Likely KBS criticism | Prespecified answer |
|---|---|
| “This is only a CV summarizer.” | Formal trace–hypothesis separation, multilevel representation, attribution, state machine, and opportunity task/gate planning |
| “This is only an LLM prompt.” | Deterministic anchor, typed schemas, validators, algorithms, C1/C2 comparisons, C4-R resource-matched sensitivity |
| “The baseline is a strawman.” | Strong flat semantic baseline plus single-shot and evidence-ID/RAG LLMs |
| “Provenance completeness is true by construction.” | Report it as an invariant, not an empirical endpoint; use semantic unsupported-claim rate as the substantive measure |
| “The generator uses the same ontology.” | Separate truth, disjoint development/final sets, 60-case challenge benchmark, ontology shift, public anchors |
| “Synthetic cases do not prove real assets.” | Explicitly agree; public cases are ecological audits, and human validity is reserved for Paper C |
| “The hybrid system simply uses more compute.” | Full cost reporting plus C4-R resource-matched comparison |
| “Attribution is ignored.” | Hidden ownership truth, false-individualization endpoint, A3, collective public cases |
| “Opportunity quality is subjective.” | Common candidate catalog with hidden graded relevance for primary ranking; open-ended generation remains secondary |
| “The theory and system papers overlap.” | Formal A/B/C firewall, one home per result, related-manuscript disclosure |
| “The system is unsafe for personnel decisions.” | Purpose limitation, no ranking, no auto-confirmation, privacy and contestability requirements |
| “All results are favorable because the protocol changed.” | Frozen cases, prompts, endpoints, hashes, deviations log, and retained null/adverse results |
