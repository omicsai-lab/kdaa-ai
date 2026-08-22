# KDAA Paper B — Protocol Implementation Clarifications

**Document ID:** KDAA-PB-KBS-001-A1  
**Version:** 1.0.1  
**Status:** Recommended minor amendment  
**Date:** 2026-08-22  
**Parent:** KDAA Paper B — KBS Claims and Evaluation Freeze v1.0

These clarifications do not change the scientific thesis, research questions, primary contrasts, primary endpoints, case counts, or publication firewall. They make five implementation details explicit so that the code cannot interpret the frozen protocol inconsistently.

## PC-01 — Exact reproducibility

“Deterministic exact reproducibility” applies to the **canonical scientific payload**, not volatile execution metadata.

The canonical payload includes ordered traces after canonicalization, hypotheses, assessments, opportunity rankings, evidence links, scores, warnings, and configuration-derived analytical fields. It excludes run UUIDs, wall-clock timestamps, filesystem paths, and machine-specific timing.

All recency-dependent calculations SHALL receive a frozen `as_of_date` from the experiment lock. Use of `date.today()` or an equivalent implicit clock is prohibited in final Paper B runs.

## PC-02 — C2 comparator

The primary C2 comparator SHALL be named:

> **C2 — Generic evidence-linked LLM**

It receives the same complete normalized evidence content as C1/C4, with stable trace IDs and retrieval-style chunk formatting, and may cite those IDs. It receives no KDAA ontology, bounded-claim rules, attribution rules, epistemic state machine, assessment dimensions, or task/gate planning structure.

A genuine selective top-k retrieval variant MAY be implemented as a secondary comparator named **C2-RAG**. It is not one of the three primary contrasts unless the protocol is amended before final case execution.

This clarification preserves evidence-content fairness while eliminating ambiguity over whether the primary C2 may silently discard traces.

## PC-03 — Attribution output contract

All comparators SHALL serialize predictions into the same evaluation-neutral ownership field with these states:

- `focal_unit`;
- `shared`;
- `organizational`;
- `external`;
- `unresolved`.

Providing this neutral output field does not give C1/C2 the KDAA attribution mechanism. It merely makes E3 scoreable and gives baselines a fair opportunity to abstain.

The production `AssetRecord` SHALL receive a backward-compatible typed field. Free-text `hypothesized_owner` may remain during migration but SHALL NOT be the Paper B scoring source.

## PC-04 — Resource matching

The current C4 architecture uses one principal LLM discovery call plus deterministic processing. Therefore C4-R matches C2 prospectively on:

- intended model-call count;
- maximum input tokens;
- maximum output tokens;
- retry policy; and
- model snapshot.

C4-R is not described as “removing multi-stage calls” unless a later implementation actually introduces such calls.

## PC-05 — Unsafe ablations

A1 (no provenance gate) and A9 (collapsed epistemic states) are **evaluation-only stress variants**.

They SHALL operate on the evaluation-neutral `PredictionBundle` before production validation or after safe production output transformation. They SHALL NOT weaken the normal `AssetRecord` validator, normal lifecycle state machine, API, CLI, or public application.

## Change-control effect

These clarifications should be committed before implementation starts and referenced in `docs/protocol_deviations.md`. Because they are prospective and precede final case generation, they are protocol clarifications rather than post hoc deviations.
