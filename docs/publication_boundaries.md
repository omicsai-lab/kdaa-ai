# Publication firewall (Paper A / Paper B / Paper C)

**Status:** Verbatim excerpt, reproduced without paraphrase.
**Source:** Section 6, "A/B/C publication firewall," of [`paper_b_kbs_claims_evaluation_freeze.md`](paper_b_kbs_claims_evaluation_freeze.md) (`KDAA-PB-KBS-001` v1.0, FROZEN FOR IMPLEMENTATION). That document is the authoritative full text; this file exists only so the firewall is directly discoverable from the README and release checklist.

**Target journal:** Knowledge-Based Systems (KBS), first submission. **Fallback:** Expert Systems with Applications (ESWA).

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

See also [Paper B scope](paper_b_scope.md), [Paper A integration](paper_a_integration.md), and [Paper C human loop](paper_c_human_loop.md) for the repository's existing (pre-freeze) discussion of these boundaries.
