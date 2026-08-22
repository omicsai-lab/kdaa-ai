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

Full normative text: [`paper_b_protocol_clarifications_v1.0.1.md`](paper_b_protocol_clarifications_v1.0.1.md).

## Deviations

| Date | Description | Reason | Affected runs/comparators | Rerun status | Recorded by |
|---|---|---|---|---|---|
| — | None recorded as of audit baseline `main@80df46c` (WP0). | — | — | — | — |

No case replacement, result-dependent tuning, or selective rerun is ever a valid entry in this table; those actions are prohibited outright, not deviations to be logged.
