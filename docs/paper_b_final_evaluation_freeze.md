# KDAA Paper B — Final Evaluation Freeze

**Document ID:** KDAA-PB-FINAL-FREEZE-001
**Version:** 1.0
**Status:** **FINAL PROTOCOL FROZEN BEFORE FINAL DATA GENERATION**
**Freeze date:** 2026-08-23
**Branch:** `paper-b/evaluation`

---

## 0. Purpose and authority

This document freezes the exact final-study configuration for KDAA Paper B so that the
final N=240 dataset and final experiment runs can be generated **afterward**, from a
committed, auditable protocol state. It does not narrow, contradict, or supersede the
scientific claim/evaluation freeze in
[`paper_b_kbs_claims_evaluation_freeze.md`](paper_b_kbs_claims_evaluation_freeze.md) or the
existing [`configs/paper_b/experiment_lock.yaml`](../configs/paper_b/experiment_lock.yaml);
it operationalizes them into exact, hashed parameters, and records the small number of
places where this freeze checkpoint deliberately narrows scope for the final primary
result package (all logged in
[`protocol_deviations.md`](protocol_deviations.md) as clarifications PC-06 through PC-08).

**As of this freeze: no final case has been generated, and no live experiment run has
occurred against final data.** `python scripts/validate_paper_b_final_freeze.py` confirms
this and is re-runnable at any time to re-verify the frozen state has not drifted.

---

## 1. Intended parent state

| | |
|---|---|
| Branch | `paper-b/evaluation` |
| Intended parent commit (working tree HEAD at freeze time) | `c3859697f7fed3abf417277539a3bac33a327b19` — "Add Paper B LLM evaluation and mechanism tests" |
| This freeze's files | committed together as the next commit on top of the above, for human review |

The final case generator and final run scripts (not yet implemented) must be built and
executed only after this freeze commit — including this document, the three new
`configs/paper_b/final_*.yaml` files, and the `docs/protocol_deviations.md` update — is
reviewed, committed, and pushed by a human.

---

## 2. Final model lock

See [`configs/paper_b/final_model_lock.yaml`](../configs/paper_b/final_model_lock.yaml)
for the full record. Summary:

| | |
|---|---|
| Provider | OpenAI-compatible OpenAI API |
| Base URL | `https://api.openai.com/v1` |
| Model | `gpt-5.4-2026-03-05` |
| Temperature | 0.1 |
| Applies to | C1, C2, C4 — one shared provider instance/configuration, no per-comparator variation |
| Model-shopping | prohibited, before and after final results |
| Retry policy | max 2 automatic retries per intended run (unchanged from Checkpoint B) |
| Credential handling | sourced only from repo-root `.env`; never printed, logged, or copied |

This exact provider/model combination was operationally verified during the **Live
Checkpoint B Development Run** on this branch (270/270 calls succeeded). That run is
development-only precedent, not final evidence, and licenses no further model comparison.

### 2.1 Token/cost telemetry — small isolated change made at this freeze

Item 12 asked me to inspect whether token usage could be captured with a small, isolated
change, since the live Checkpoint B run showed usage was visible in the OpenAI dashboard
but not locally. It could:

- [`src/kdaa/providers/openai_compatible.py`](../src/kdaa/providers/openai_compatible.py):
  `OpenAICompatibleProvider` now records the chat-completions response's top-level
  `"usage"` object as `self.last_usage` after every call.
- [`src/kdaa/evaluation/paper_b/adapters/llm_harness.py`](../src/kdaa/evaluation/paper_b/adapters/llm_harness.py):
  a new `_usage_fields(provider)` helper reads `getattr(provider, "last_usage", None)` and,
  when present, populates `ResourceUsage.input_tokens` / `output_tokens` / `total_tokens` /
  `provider_usage_metadata`. Wired into both the C1/C2 harness path and C4's adapter
  (`c4_hybrid.py`).
- For any provider that does not expose `last_usage` (e.g. the dry-run `FakeJSONProvider`),
  this is a true no-op — token fields stay `None`, exactly as before. No value is ever
  invented.
- **Not done, as out of scope for "small, isolated":** estimated-cost computation. No price
  schedule is locked. `estimated_cost_usd` remains unavailable locally; aggregate
  provider-side usage/cost remains separately available in the OpenAI dashboard, as
  observed during the live Checkpoint B run.
- Tests added: `tests/paper_b/test_llm_harness.py` (three new cases — no-op when absent,
  populated when present, malformed usage ignored not invented) and
  `tests/test_llm_and_provider.py` (two new cases exercising the real
  `OpenAICompatibleProvider` against a mocked HTTP response). All pass; see §13.

---

## 3. Final N=240 dataset design

Unchanged from
[`paper_b_kbs_claims_evaluation_freeze.md` §9.2](paper_b_kbs_claims_evaluation_freeze.md)
and [`configs/paper_b/experiment_lock.yaml`](../configs/paper_b/experiment_lock.yaml)
`data.final_synthetic` — reaffirmed, not altered:

- **180 core factorial cases:** 3 unit types × 2 evidence densities × 2 domain breadths ×
  3 attribution regimes × 5 replicates.
- **60 challenge cases:** 10 categories × 6 cases each.
- Truth and evidence remain physically separate (WP1 `kdaa.evaluation.paper_b.truth`
  module + `boundary.find_truth_leakage()` direct-import-boundary enforcement — the same
  architecture already validated for development, unchanged for final).
- Truth is **not** visible to C0-S, C1, C2, C3, C4, prompts, inference adapters, or any
  visible filename/metadata.
- The final case-generation code does not exist yet and is explicitly out of scope for
  this freeze; this document and `configs/paper_b/final_experiment_lock.yaml` are what a
  future implementation checkpoint must read.

`as_of_date` is frozen at **2026-06-01**, inherited unchanged from development for
continuity (see PC-06 in `protocol_deviations.md` — the master `experiment_lock.yaml` did
not previously carry this field even though PC-01 requires one; it is now recorded
authoritatively in `final_experiment_lock.yaml`).

---

## 4. Final LLM subset, repeats, and call count

| | |
|---|---|
| N | 60 |
| Core | 30 |
| Challenge | 30 |
| Comparators | C1, C2, C4 |
| Intended repeats per case | 3 |
| **Intended primary live LLM calls** | **60 × 3 × 3 = 540** |
| Selection algorithm | first 30 core-set + first 30 challenge-set cases, each by canonical generation index within its own stratum — direct extension of the proven `dev_llm_subset.select_development_llm_subset` design (Checkpoint B) to two independent strata |
| Best-of-N | prohibited |
| Primary case value | mean across all intended repeats |
| Failed attempts | retained per the existing WP1 failure policy (never dropped, never replaced) |

The subset must be selected and its case IDs recorded **before** any live model result is
observed, exactly as the Checkpoint B development subset was.

---

## 5. Comparator set

**Primary:** C3 vs C0-S · C4 vs C1 · C4 vs C2

**Important secondary:** C4 vs C3 — interpreted as a breadth/flexibility/grounding/latency
trade-off, not a required superiority test.

**C2 retained despite no development advantage.** The live Checkpoint B run (N=30,
gpt-5.4-2026-03-05) found C2 did **not** outperform C1 on concept F1 (paired diff −0.0002,
95% CI crosses 0) or nDCG@5 (paired diff −0.006, 95% CI crosses 0), and had a marginally
*higher* unsupported-claim rate (paired diff +0.023, 95% CI [0.005, 0.045] — excludes 0).
C2 stays in the final study anyway: its role is to test whether simple evidence-
linking/citation prompting alone reproduces provenance-constrained reasoning, independent
of whether it wins.

---

## 6. Endpoint interpretation (final lock)

- **E1 — concept recovery:** precision/recall/F1, one-to-one bipartite matching, unchanged.
- **E2 — semantic unsupported-claim rate:** primary Paper B endpoint; measures substantive
  unsupported inference (nonexistent capability, overbroad scope, unsupported currentness,
  unsupported sole ownership, unsupported dependency) — **not** merely "cites a valid
  evidence ID."
- **E3 — attribution safety profile** (reinterpreted; see PC-07): **not** described as
  ownership-attribution accuracy. Composed of false-individualization rate, attribution
  coverage, and unresolved/abstention rate. **Locked interpretation:** low
  false-individualization combined with zero attribution coverage represents conservative
  abstention, not successful ownership inference. This reading is required in the final
  manuscript. It generalizes directly from the live Checkpoint B finding: C4 showed 0.0
  false-individualization and 0.0 attribution coverage in every applicable case (because it
  always predicts `UNRESOLVED` — WP2's deliberate conservative default), while C1/C2 showed
  ≈1.0 attribution coverage and ≈1.0 false-individualization (confidently wrong in nearly
  every case where they attributed at all). No new ownership classifier will be added
  before the final study.
- **E4 — opportunity ranking:** nDCG@5, but final cases use **case-specific** opportunity
  catalogs (see §7), not development's single shared catalog. Truth-side grading remains
  architecturally independent of any comparator's ranking mechanism (the Checkpoint B
  E4-circularity fix, generalized).

---

## 7. Final opportunity design (per case)

Each of the 240 final cases receives:

- Exactly **10 visible candidate opportunities** — title + description, the description
  packing beneficiary/problem/expected-output/context as plain text inside the existing
  `description` field (no WP1 schema change — the same convention Checkpoint B used).
- Independent, hidden, truth-side relevance **requirements** (required/optional/
  disqualifying concepts) authored per case, producing grades 0–3 — the same
  required/optional/disqualifying mechanism `opportunity_truth.py` already uses, generalized
  from one shared development catalog to per-case authoring.
- All comparators for that case rank the same 10 opportunities.
- **No general opportunity ontology is built.** The design stays simple and auditable:
  a fixed set of opportunity *archetypes* (the same 10 types already used in development —
  repository, living document, deployable product, benchmark dataset, consulting service,
  grant proposal, knowledge base, etc.) instantiated with case-specific visible text and
  case-specific hidden requirements, not 240 × 10 bespoke, unrelated opportunities.
- **Implementation status: design frozen here; generator not yet implemented.** Building it
  is out of scope for this freeze (`final_experiment_lock.yaml` records this explicitly as
  `implementation_status: design_frozen_generator_not_yet_implemented`).

---

## 8. Final ablations

| ID | Ablation | Primary diagnostic |
|---|---|---|
| A1 | No provenance gate | E2 |
| A4 | No asset-level structure (flat unit representation) | E1 |
| A6 | No opportunity-specific matching | E4 |

No ownership-attribution ablation (A3) in the final primary set. No additional ablations
without a genuine defect justification. This narrows the six main-text ablations listed in
`paper_b_kbs_claims_evaluation_freeze.md` §13 (A1, A2, A3, A4, A6, A7) to three for the
final primary result package — logged as PC-08.

---

## 9. Final robustness tests

| ID | Family |
|---|---|
| R1 | Duplicate / dependence |
| R2 | Irrelevant noise and/or simple contradiction |
| R3 | Ontology / surface shift |
| R4 (opportunity-context reversal) | secondary only, if already implemented cleanly |

Narrows the nine perturbation families in `paper_b_kbs_claims_evaluation_freeze.md` §14 to
three primary families (plus optional secondary R4) for the final primary result package —
logged as PC-08 alongside the ablation narrowing.

---

## 10. Development-derived prospective decisions

Recorded in `configs/paper_b/final_experiment_lock.yaml`
(`development_derived_prospective_decisions`), reproduced here:

1. **DD-01** — The E4 circularity discovered in development was removed before final freeze.
2. **DD-02** — E3 was reinterpreted as attribution safety rather than attribution accuracy.
3. **DD-03** — C2 is retained because evidence linking alone is scientifically informative
   even when it does not improve performance.
4. **DD-04** — No ownership classifier will be added before final evaluation.
5. **DD-05** — No additional model/prompt shopping will occur.
6. **DD-06** — Development data/results are not final-paper evidence.

These are prospective final-design decisions recorded before any final data exist — not
post hoc adjustments made in response to final results, since final results do not yet
exist to adjust to.

---

## 11. Final analysis policy

- Unit of analysis: focal case.
- Per primary contrast/endpoint: comparator means, paired mean difference, paired median
  difference, 95% paired case-level bootstrap CI — via the existing, already-approved
  `kdaa.evaluation.paper_b.analysis.summarize_paired` framework (unchanged since
  Checkpoint A/B: seed=42, 2000-resample percentile method).
- No composite "overall KDAA score."
- Formal p-values optional; effect sizes and CIs are primary.
- Unfavorable, null, and adverse results are retained.

---

## 12. Locked hashes (recorded at freeze time)

Computed by `scripts/validate_paper_b_final_freeze.py` (sha256, whole-file content except
the `scoring/` package, which is a path-sorted concatenated hash over every `.py` file in
that directory):

```
dac052c2cf500b0c68cdf178306ce7319d62e7bfb918513e1edd1e2d8628e66b  final_model_lock.yaml
8922e4e4e4ea891fcd8bc83d1d6b9134121353c7afe68e401b0f04781d84705f  final_experiment_lock.yaml
749997302d778b08683e6c8943ceeb0953217eb528ea7485effcaafa764e70dd  final_scorer_lock.yaml
411668256fbfe080a278495ba3a8dad1f0f201ff6c8b870bd34824c60858d5df  experiment_lock.yaml (WP0 baseline)
2d2b46656cdb14847d416daf58356e2b23f38bf290c2f259016d965132b1fad0  C1 prompt (c1_generic_llm.py)
71792334ae10ae7d788243269254295a72567ed2625afa3242fc1dd9293b0e02  C2 prompt (c2_evidence_linked.py)
4e3a9dd23b251d9db776745c5fa9c2daabba817815f134b8ca8203724f954b2d  C4 production LLM prompt (discovery/llm.py)
7e8fcaa8801b770d86212853d5a6d4eca3334a523a661c901c77cd64fe6af4be  C4 adapter wrapper (c4_hybrid.py)
36d706f1360524a05ec57eb25e08757455d3e516316367eaf41ca42e0e46cbc7  shared LLM harness/schema/retry policy (llm_harness.py)
1ed1f322d18429bc1da838ad7c92d73db53644b9b226ad40137ef3ac310ed983  ontology (ontology.yaml)
4f8f2aaf1d89fffecfdd9a8d69129af9458db34de1ac500955937de9838fb8d6  subset-selection algorithm (dev_llm_subset.py)
bed7012701358cdafe1b26f373893171b99a8f46f4c68548fdb59beab9ddd909  paired bootstrap analysis (analysis.py)
a964a07a14ef8ec3265aa1e0a837da49ce0f1f64396748a61fb27a088f56cd0c  scorer package (scoring/, all files)
```

`as_of_date` is locked as a literal value (not a file): `2026-06-01`.

**After this freeze commit:** none of the hashed files may be edited in response to final
results without a documented software-defect entry in `protocol_deviations.md` that
invalidates and requires rerunning affected comparators (Freeze §23). Re-run
`scripts/validate_paper_b_final_freeze.py` at any time to confirm these hashes still match.

---

## 13. Validation performed at this freeze

```
ruff check .                                          -> all checks passed
pytest --cov=kdaa --cov-report=term-missing            -> 368 passed, 92.05% coverage
python -m compileall -q src app scripts tests          -> exit 0
python scripts/validate_paper_b_final_freeze.py        -> all dry-validation checks passed
```

(368 vs. Checkpoint B's 363: +5 new tests covering the token/cost telemetry change in §2.1
— three in `tests/paper_b/test_llm_harness.py`, two in `tests/test_llm_and_provider.py`.)

The dry-validation script confirmed: all three new lock files parse; final dataset counts
are 180 + 60 = 240; final LLM subset is 30 + 30 = 60; intended live calls compute to
540; all 13 hash targets hashed successfully; `boundary.find_truth_leakage()` reports zero
violations; no `data/synthetic/final_evidence` or `data/synthetic/final_truth` directory
exists. **No live API call was made. No final case was generated.**

---

## 14. Unresolved issues for human review

1. **Final opportunity-catalog generator does not exist yet.** §7 freezes the design; a
   future checkpoint must implement it and verify (the same way
   `tests/paper_b/test_e4_independence.py` verifies development's version) that the
   generator's truth-side and inference-side code paths remain genuinely independent at
   N=240 scale.
2. **`as_of_date` continuity vs. re-freshness.** 2026-06-01 is inherited from development
   for continuity; nothing found it broken, but it has not been re-justified specifically
   for a 240-case final dataset with its own timeline requirements (e.g. whether any
   challenge-category case needs a different simulated "current" date to be meaningful).
3. **Estimated cost telemetry remains unavailable locally** (§2.1) — only aggregate,
   provider-side dashboard figures exist. If per-attempt cost is needed for the final
   manuscript's cost table, a price-schedule lock would need to be added as a separate,
   explicitly-scoped change, not silently folded into a future checkpoint.
4. **Ablation/robustness scope narrowing (A2/A3/A7 excluded; six of nine perturbation
   families excluded) is a real reduction from the broader scientific freeze document.**
   It is logged as PC-08, but a human should confirm this narrowing is acceptable for the
   Paper B primary result package before final case generation begins, since it affects
   what the manuscript can claim under §22 (KBS-readiness gate) of the scientific freeze.
