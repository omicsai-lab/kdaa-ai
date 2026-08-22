# Paper B (KBS) reviewer attack map

**Status:** Verbatim excerpt, reproduced without paraphrase.
**Source:** Appendix B, "Reviewer attack map," of [`paper_b_kbs_claims_evaluation_freeze.md`](paper_b_kbs_claims_evaluation_freeze.md) (`KDAA-PB-KBS-001` v1.0, FROZEN FOR IMPLEMENTATION). That document is the authoritative full text; this file exists only so the attack map is directly discoverable during drafting and review.

---

## Appendix B — Reviewer attack map

| Likely KBS criticism | Prespecified answer |
|---|---|
| "This is only a CV summarizer." | Formal trace–hypothesis separation, multilevel representation, attribution, state machine, and opportunity task/gate planning |
| "This is only an LLM prompt." | Deterministic anchor, typed schemas, validators, algorithms, C1/C2 comparisons, C4-R resource-matched sensitivity |
| "The baseline is a strawman." | Strong flat semantic baseline plus single-shot and evidence-ID/RAG LLMs |
| "Provenance completeness is true by construction." | Report it as an invariant, not an empirical endpoint; use semantic unsupported-claim rate as the substantive measure |
| "The generator uses the same ontology." | Separate truth, disjoint development/final sets, 60-case challenge benchmark, ontology shift, public anchors |
| "Synthetic cases do not prove real assets." | Explicitly agree; public cases are ecological audits, and human validity is reserved for Paper C |
| "The hybrid system simply uses more compute." | Full cost reporting plus C4-R resource-matched comparison |
| "Attribution is ignored." | Hidden ownership truth, false-individualization endpoint, A3, collective public cases |
| "Opportunity quality is subjective." | Common candidate catalog with hidden graded relevance for primary ranking; open-ended generation remains secondary |
| "The theory and system papers overlap." | Formal A/B/C firewall, one home per result, related-manuscript disclosure |
| "The system is unsafe for personnel decisions." | Purpose limitation, no ranking, no auto-confirmation, privacy and contestability requirements |
| "All results are favorable because the protocol changed." | Frozen cases, prompts, endpoints, hashes, deviations log, and retained null/adverse results |

---

See also [Protocol deviations](protocol_deviations.md) for the running deviations log referenced by the last row of this table.
