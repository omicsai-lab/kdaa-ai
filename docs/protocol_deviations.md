# Protocol deviations log

Per Section 23 ("Change control") of [`paper_b_kbs_claims_evaluation_freeze.md`](paper_b_kbs_claims_evaluation_freeze.md): "the final manuscript must include a deviations table, even if it states 'none.'" This file is that table, kept current from WP0 onward. It is append-only; entries are never edited or removed after the fact, only superseded by a new dated entry.

## How to use this log

- **Protocol clarifications** (prospective, pre-freeze-implementation, do not change endpoints/contrasts/case counts) are recorded in the "Clarifications" section below, per the change-control instruction in [`paper_b_protocol_clarifications_v1.0.1.md`](paper_b_protocol_clarifications_v1.0.1.md#change-control-effect).
- **Deviations** (any departure from the frozen protocol discovered after implementation begins, including software-defect corrections that invalidate and require rerunning affected comparators per Section 23) go in the "Deviations" table. A deviation entry is required even for defects that are fixed cleanly before any final run is affected.

## Clarifications (pre-implementation, not post hoc deviations)

| ID | Title | Effect |
|---|---|---|
| PC-01 | Exact reproducibility | Scopes "deterministic exact reproducibility" to the canonical scientific payload; requires a frozen `as_of_date` from the experiment lock; prohibits `date.today()` in final runs. |
| PC-02 | C2 comparator | Names the primary C2 comparator "Generic evidence-linked LLM"; defines C2-RAG as a secondary, non-primary variant. |
| PC-03 | Attribution output contract | Fixes the neutral ownership-field vocabulary (`focal_unit`, `shared`, `organizational`, `external`, `unresolved`) shared by all comparators for E3 scoring. |
| PC-04 | Resource matching | Defines C4-R's prospective match to C2 on call count, token ceilings, retry policy, and model snapshot. |
| PC-05 | Unsafe ablations | Confines A1/A9 to the evaluation-neutral `PredictionBundle`; prohibits weakening the production `AssetRecord` validator, lifecycle state machine, API, CLI, or public application. |
| PC-06 | `as_of_date` freeze location | Records the frozen `as_of_date` (`2026-06-01`, inherited unchanged from development) authoritatively in `configs/paper_b/final_experiment_lock.yaml`, closing a gap where PC-01 required a frozen `as_of_date` "from the experiment lock" but `configs/paper_b/experiment_lock.yaml` never actually carried the field. |
| PC-07 | E3 reinterpretation | Freezes E3 as an attribution *safety* profile (false-individualization rate, attribution coverage, unresolved/abstention rate), not ownership-attribution *accuracy*. Requires the final manuscript to read "low false-individualization with zero coverage" as conservative abstention, not successful inference — generalizing the live Checkpoint B development finding (C4: 0.0/0.0; C1/C2: ≈1.0/≈1.0) prospectively to the final study. No new ownership classifier before final evaluation. |
| PC-08 | Final ablation/robustness scope | Narrows the FINAL primary result package to three ablations (A1, A4, A6 — excluding A2, A3, A7) and three robustness families (R1, R2, R3, plus optional secondary R4 — excluding the remaining perturbation families in Freeze §14). Does not remove A2/A3/A7 or the other perturbation families from the broader scientific protocol; narrows only what the final primary Paper B result package reports, per explicit instruction at the Final Evaluation Freeze checkpoint. A human should confirm this narrowing is acceptable against the KBS-readiness gate (Freeze §22) before final case generation begins. |

Full normative text: [`paper_b_protocol_clarifications_v1.0.1.md`](paper_b_protocol_clarifications_v1.0.1.md) for PC-01 through PC-05; PC-06 through PC-08 are defined in full in [`paper_b_final_evaluation_freeze.md`](paper_b_final_evaluation_freeze.md).

## Deviations

| Date | Description | Reason | Affected runs/comparators | Rerun status | Recorded by |
|---|---|---|---|---|---|
| — | None recorded as of audit baseline `main@80df46c` (WP0). | — | — | — | — |

No case replacement, result-dependent tuning, or selective rerun is ever a valid entry in this table; those actions are prohibited outright, not deviations to be logged.
