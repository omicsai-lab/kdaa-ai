"""Shared logic for adapting a production KDAA ``AnalysisRun`` into the WP1
evaluation-neutral schema. Used by both the deterministic (C3) and hybrid (C4) adapters,
since both wrap the same production pipeline and differ only in ``KDAAConfig.mode`` and
(for C4) an LLM provider.

Under the truth-import boundary: must never import ``kdaa.evaluation.paper_b.truth`` or
``kdaa.evaluation.paper_b.opportunity_truth``.
"""

from __future__ import annotations

from kdaa.models import AnalysisRun, EvidenceRole, OwnershipState
from kdaa.ontology import Ontology

from ..opportunity_catalog import rank_opportunities_by_visible_text
from ..schemas import (
    InputSnapshot,
    OwnershipLabel,
    PredictedClaim,
    PredictedOpportunity,
    PredictionBundle,
)

MAX_CLAIMS = 10

# Production OwnershipState and evaluation OwnershipLabel share identical string values
# by construction (WP2 requirement A1); mapping by value needs no translation table.
OWNERSHIP_MAP: dict[OwnershipState, OwnershipLabel] = {
    state: OwnershipLabel(state.value) for state in OwnershipState
}


def adapt_kdaa_run(
    run: AnalysisRun,
    snapshot: InputSnapshot,
    ontology: Ontology,
    *,
    comparator_id: str,
) -> PredictionBundle:
    """Map a completed KDAA ``AnalysisRun`` to a ``PredictionBundle``.

    Claims: the top ``MAX_CLAIMS`` assets (``assess_asset_records`` already sorts by
    descending overall credibility, so taking a prefix enforces the fairness cap without
    inventing a new ranking rule).

    Opportunity ranking: ``rank_opportunities_by_visible_text`` (Checkpoint B E4 fix) --
    computed from the *visible* opportunity text against C3/C4's *own* discovered concept
    labels, never from a hidden lookup table shared with truth generation.
    """
    top_assets = run.assets[:MAX_CLAIMS]

    claims: list[PredictedClaim] = []
    discovered_concept_labels: list[str] = []
    for asset in top_assets:
        cited = [
            link.trace_id for link in asset.evidence_links if link.role == EvidenceRole.SUPPORTING
        ]
        claims.append(
            PredictedClaim(
                claim_id=asset.id,
                label=", ".join(asset.concept_tags) if asset.concept_tags else asset.label,
                bounded_claim=asset.bounded_claim,
                cited_trace_ids=cited,
                ownership=OWNERSHIP_MAP.get(asset.ownership_state, OwnershipLabel.UNRESOLVED),
            )
        )
        discovered_concept_labels.extend(asset.concept_tags)

    ranked_opportunities: list[PredictedOpportunity] = rank_opportunities_by_visible_text(
        discovered_concept_labels, snapshot.opportunity_catalog, ontology
    )

    return PredictionBundle(
        case_id=snapshot.case_id,
        comparator_id=comparator_id,
        claims=claims,
        ranked_opportunities=ranked_opportunities,
    )
