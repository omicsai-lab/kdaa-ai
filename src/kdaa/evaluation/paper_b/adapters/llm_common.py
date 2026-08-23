"""Shared LLM-response-to-``PredictionBundle`` conversion for C1/C2 (they differ only in
whether ``evidence_ids`` are requested/used -- see each adapter's own prompt).
"""

from __future__ import annotations

from ..schemas import OwnershipLabel, PredictedClaim, PredictedOpportunity, PredictionBundle
from .llm_harness import (  # noqa: F401  (re-export for callers)
    MAX_AUTOMATIC_RETRIES,
    LLMResponseSchema,
)

MAX_CLAIMS = 10

_VALID_OWNERSHIP_VALUES = {member.value for member in OwnershipLabel}


def _parse_ownership(value: str | None) -> OwnershipLabel:
    if value and value.strip().lower() in _VALID_OWNERSHIP_VALUES:
        return OwnershipLabel(value.strip().lower())
    return OwnershipLabel.UNRESOLVED


def prediction_from_llm_response(
    validated: LLMResponseSchema,
    *,
    case_id: str,
    comparator_id: str,
    valid_trace_ids: set[str] | None = None,
) -> PredictionBundle:
    """Adapt a validated LLM response into the evaluation-neutral schema.

    ``valid_trace_ids``: when given (C2), any cited evidence ID not in this set is
    dropped -- an output adapter may parse and normalize, but per the fairness rules
    (Freeze Section 12.7) must not *add* evidence a comparator did not actually cite.
    When ``None`` (C1), no evidence citation is requested at all, so claims carry no
    ``cited_trace_ids``.
    """
    claims: list[PredictedClaim] = []
    seen_ids: set[str] = set()
    for index, concept in enumerate(validated.concepts[:MAX_CLAIMS]):
        claim_id = f"{comparator_id.lower()}-{case_id}-{index}"
        while claim_id in seen_ids:
            claim_id = f"{claim_id}-dup"
        seen_ids.add(claim_id)
        cited = (
            sorted(set(concept.evidence_ids) & valid_trace_ids) if valid_trace_ids is not None else []
        )
        claims.append(
            PredictedClaim(
                claim_id=claim_id,
                label=concept.label,
                cited_trace_ids=cited,
                ownership=_parse_ownership(concept.ownership),
            )
        )

    ranked_opportunities: list[PredictedOpportunity] = []
    ranked_ids = validated.ranked_opportunity_ids
    if len(ranked_ids) == len(set(ranked_ids)) and ranked_ids:
        ranked_opportunities = [
            PredictedOpportunity(opportunity_id=opportunity_id, rank=rank)
            for rank, opportunity_id in enumerate(ranked_ids, start=1)
        ]
    # An empty or duplicate-containing ranking is left as [] (explicit abstention/failure
    # per E4's "represented explicitly, not silently filled" rule) rather than repaired.

    return PredictionBundle(
        case_id=case_id,
        comparator_id=comparator_id,
        claims=claims,
        ranked_opportunities=ranked_opportunities,
    )
