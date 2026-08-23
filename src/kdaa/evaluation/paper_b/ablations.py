"""Essential development ablations only (Checkpoint B Section 9): A1, A4, A6.

Each ablation transforms an already-produced, evaluation-neutral ``PredictionBundle`` --
never the production ``AssetRecord`` or KDAA's internal validators, which stay untouched
(Checkpoint B: "Do not weaken production AssetRecord"; PC-05: unsafe ablations operate
only on the evaluation-neutral bundle). This makes each ablation a cheap, deterministic,
easy-to-interpret post-hoc transform rather than a second implementation of KDAA.

Deliberately not implemented (per Checkpoint B Section 9): the full A1-A9 set, an
attribution ablation (KDAA currently has no substantive ownership-inference mechanism to
remove -- see WP2), and the optional fourth ablation (no dependence/duplicate control),
skipped to keep this checkpoint's scope tight.
"""

from __future__ import annotations

from collections import Counter

from .schemas import (
    InputSnapshot,
    OwnershipLabel,
    PredictedClaim,
    PredictedOpportunity,
    PredictionBundle,
)


def apply_a1_no_provenance_gate(prediction: PredictionBundle) -> PredictionBundle:
    """A1 -- no provenance constraint. The normal system's provenance gate would reject a
    claim that cites a trace ID that does not exist or does not actually support it. This
    simulates that gate being bypassed by adding one such unvalidated citation to every
    claim, so a downstream E2 scorer sees exactly the "materially overbroad scope"
    unsupported-claim atom the gate normally prevents.

    Primary diagnostic: E2 (expected direction: higher unsupported-claim rate).
    """
    ablated_claims = [
        claim.model_copy(
            update={"cited_trace_ids": [*claim.cited_trace_ids, f"unvalidated-{claim.claim_id}"]}
        )
        for claim in prediction.claims
    ]
    return prediction.model_copy(
        update={"claims": ablated_claims, "comparator_id": f"{prediction.comparator_id}+A1"}
    )


def apply_a4_flat_unit_representation(prediction: PredictionBundle) -> PredictionBundle:
    """A4 -- no asset-level structure. Collapses every claim into one unit-level profile
    claim (one label, the union of cited evidence, majority-vote ownership), removing the
    asset-level granularity that lets one-to-one E1 matching credit multiple distinct true
    concepts and lets E4 reason about which *specific* asset an opportunity fits.

    Primary diagnostics: E1 (expected: recall drops, since one broad claim can match at
    most one true concept under one-to-one matching), E4.
    """
    if not prediction.claims:
        return prediction.model_copy(update={"comparator_id": f"{prediction.comparator_id}+A4"})

    combined_label = "; ".join(dict.fromkeys(claim.label for claim in prediction.claims if claim.label))
    combined_citations = sorted({trace_id for claim in prediction.claims for trace_id in claim.cited_trace_ids})

    ownership_counts = Counter(claim.ownership for claim in prediction.claims)
    top_ownership, top_count = ownership_counts.most_common(1)[0]
    tied_for_top = sum(1 for count in ownership_counts.values() if count == top_count)
    ownership = top_ownership if tied_for_top == 1 else OwnershipLabel.UNRESOLVED

    flat_claim = PredictedClaim(
        claim_id=f"{prediction.case_id}-a4-flat-profile",
        label=combined_label,
        cited_trace_ids=combined_citations,
        ownership=ownership,
    )
    return prediction.model_copy(
        update={"claims": [flat_claim], "comparator_id": f"{prediction.comparator_id}+A4"}
    )


def apply_a6_no_opportunity_specific_matching(
    prediction: PredictionBundle, snapshot: InputSnapshot
) -> PredictionBundle:
    """A6 -- no opportunity-specific matching. Replaces whatever case-specific ranking the
    comparator produced with the catalog's own fixed default order -- identical for every
    case, using no evidence or predicted-concept information at all.

    Primary diagnostic: E4 (expected: nDCG drops toward the catalog's unconditional
    average, since ranking no longer responds to the case).
    """
    generic_ranking = [
        PredictedOpportunity(opportunity_id=candidate.opportunity_id, rank=rank)
        for rank, candidate in enumerate(snapshot.opportunity_catalog, start=1)
    ]
    return prediction.model_copy(
        update={"ranked_opportunities": generic_ranking, "comparator_id": f"{prediction.comparator_id}+A6"}
    )
