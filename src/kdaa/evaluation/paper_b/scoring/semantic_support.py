"""E2 -- semantic unsupported-claim rate (Freeze Section 15.2, E2).

Deliberately not the legacy "does this trace ID exist" check: a claim can cite a real
trace ID and still be substantively unsupported. This is the simplest transparent
truth-atom scorer sufficient to distinguish substantive support from mere provenance
linkage (Checkpoint A instruction), covering the five required atom types using only
fields already present in the WP1/production schemas -- no new NLP or entailment model:

- **nonexistent capability**: the claim's label does not match any true concept at all
  (reuses E1's matching, so "matched" means the same thing in both endpoints).
- **materially overbroad scope**: the claim cites a trace the matched true concept does
  not list as supporting it.
- **unsupported currentness**: the matched true concept is marked not current
  (``is_current=False``). Checkpoint A treats matching a stale-only concept as an
  unsupported currentness assertion, since predicted claims here carry no temporal
  qualification to check against -- a documented development-stage simplification, not a
  claim about natural-language semantics.
- **unsupported sole ownership**: the claim asserts ``FOCAL_UNIT`` ownership while the
  matched true concept's ownership is anything else.
- **unsupported dependency**: the matched true concept has declared dependency traces and
  the claim cites none of them.

Scorer-side (reads ``TrueAssetConcept``); must never be imported by
``kdaa.evaluation.paper_b.adapters``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..schemas import OwnershipLabel, PredictedClaim
from ..truth import TrueAssetConcept


@dataclass(frozen=True)
class ClaimSupportResult:
    claim_id: str
    unsupported: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SemanticSupportResult:
    case_id: str
    unsupported_claim_rate: float
    n_active_claims: int
    n_unsupported: int
    claim_results: tuple[ClaimSupportResult, ...]


def _atoms_for_matched_claim(claim: PredictedClaim, concept: TrueAssetConcept) -> list[str]:
    reasons: list[str] = []
    cited = set(claim.cited_trace_ids)

    if concept.supporting_trace_ids and not cited.issubset(set(concept.supporting_trace_ids)):
        reasons.append("materially_overbroad_scope")

    if not concept.is_current:
        reasons.append("unsupported_currentness")

    if claim.ownership == OwnershipLabel.FOCAL_UNIT and concept.ownership_state != OwnershipLabel.FOCAL_UNIT:
        reasons.append("unsupported_sole_ownership")

    if concept.dependency_trace_ids and not (cited & set(concept.dependency_trace_ids)):
        reasons.append("unsupported_dependency")

    return reasons


def score_semantic_support(
    case_id: str,
    predicted_claims: list[PredictedClaim],
    true_concepts: list[TrueAssetConcept],
    matched_pairs: tuple[tuple[str, str], ...],
) -> SemanticSupportResult:
    concepts_by_id = {concept.concept_id: concept for concept in true_concepts}
    matched_concept_for_claim = dict(matched_pairs)

    claim_results: list[ClaimSupportResult] = []
    for claim in predicted_claims:
        concept_id = matched_concept_for_claim.get(claim.claim_id)
        concept = concepts_by_id.get(concept_id) if concept_id else None
        if concept is None:
            claim_results.append(
                ClaimSupportResult(claim_id=claim.claim_id, unsupported=True, reasons=("nonexistent_capability",))
            )
            continue
        reasons = _atoms_for_matched_claim(claim, concept)
        claim_results.append(
            ClaimSupportResult(claim_id=claim.claim_id, unsupported=bool(reasons), reasons=tuple(reasons))
        )

    n_active = len(claim_results)
    n_unsupported = sum(1 for result in claim_results if result.unsupported)
    rate = (n_unsupported / n_active) if n_active > 0 else 0.0

    return SemanticSupportResult(
        case_id=case_id,
        unsupported_claim_rate=rate,
        n_active_claims=n_active,
        n_unsupported=n_unsupported,
        claim_results=tuple(claim_results),
    )
