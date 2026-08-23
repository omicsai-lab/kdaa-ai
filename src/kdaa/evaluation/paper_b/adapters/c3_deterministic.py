"""C3 -- KDAA deterministic adapter (Freeze Section 10, C3).

Reuses the existing production ``KDAAPipeline`` unchanged (deterministic mode) and maps
its valid output into the WP1 evaluation-neutral schema. This is a thin translation layer,
not a reimplementation: no discovery, scoring, or opportunity logic is duplicated or
redesigned here.

Opportunity ranking uses only a minimal evaluation ranking interface (concept-tag overlap
against the same fixed catalog tagging used to generate hidden relevance -- see
``kdaa.evaluation.paper_b.opportunity_catalog``), not the full production amplification
engine, per the Checkpoint A instruction not to redesign it.

This module is under the truth-import boundary (see ``kdaa.evaluation.paper_b.boundary``):
it must only ever receive a ``UnitBundle``/``InputSnapshot``, never a ``TruthBundle``.
"""

from __future__ import annotations

from datetime import date

from kdaa.config import KDAAConfig
from kdaa.models import EvidenceRole, OwnershipState, UnitBundle
from kdaa.ontology import Ontology
from kdaa.pipeline import KDAAPipeline

from ..opportunity_catalog import relevance_grade
from ..schemas import (
    InputSnapshot,
    OwnershipLabel,
    PredictedClaim,
    PredictedOpportunity,
    PredictionBundle,
)

COMPARATOR_ID = "C3"
MAX_CLAIMS = 10

# Production OwnershipState and evaluation OwnershipLabel share identical string values
# by construction (WP2 requirement A1); mapping by value needs no translation table.
_OWNERSHIP_MAP: dict[OwnershipState, OwnershipLabel] = {
    state: OwnershipLabel(state.value) for state in OwnershipState
}


def run_c3(
    bundle: UnitBundle,
    snapshot: InputSnapshot,
    ontology: Ontology,
    *,
    as_of_date: date,
) -> PredictionBundle:
    """Run the unmodified production deterministic pipeline and adapt its output.

    ``snapshot`` is used only for its opportunity catalog (the exact 10 IDs to rank) and
    to confirm the case_id; the evidence itself comes from ``bundle`` because the
    production pipeline requires a real ``UnitBundle``, not the evaluation-neutral
    ``InputSnapshot``.
    """
    config = KDAAConfig(mode="deterministic", as_of_date=as_of_date)
    pipeline = KDAAPipeline(config, ontology=ontology)
    run, _ = pipeline.analyze(bundle)

    # assess_asset_records already returns assets sorted by descending overall
    # credibility; taking the first MAX_CLAIMS enforces the fairness cap without
    # inventing a new ranking rule.
    top_assets = run.assets[:MAX_CLAIMS]

    claims = []
    discovered_concept_keys: set[str] = set()
    label_to_key = {
        definition.label.strip().lower(): key for key, definition in ontology.concepts.items()
    }
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
                ownership=_OWNERSHIP_MAP.get(asset.ownership_state, OwnershipLabel.UNRESOLVED),
            )
        )
        for tag in asset.concept_tags:
            key = label_to_key.get(tag.strip().lower())
            if key:
                discovered_concept_keys.add(key)

    ranked_opportunities = _rank_opportunities(discovered_concept_keys, snapshot)

    return PredictionBundle(
        case_id=snapshot.case_id,
        comparator_id=COMPARATOR_ID,
        claims=claims,
        ranked_opportunities=ranked_opportunities,
    )


def _rank_opportunities(
    discovered_concept_keys: set[str], snapshot: InputSnapshot
) -> list[PredictedOpportunity]:
    """Minimal evaluation ranking interface: rank the fixed catalog by overlap between
    C3's own discovered concept keys and each opportunity's concept tags. Deterministic
    ties broken by opportunity_id.
    """
    scored = [
        (candidate.opportunity_id, relevance_grade(discovered_concept_keys, candidate.opportunity_id))
        for candidate in snapshot.opportunity_catalog
    ]
    scored.sort(key=lambda item: (-item[1], item[0]))
    return [
        PredictedOpportunity(
            opportunity_id=opportunity_id,
            rank=rank,
            rationale=f"Discovered-concept-tag overlap score={score}.",
        )
        for rank, (opportunity_id, score) in enumerate(scored, start=1)
    ]
