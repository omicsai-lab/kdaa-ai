"""C0-S -- strong flat semantic profile baseline (Freeze Section 10, C0-S).

Operates at unit/profile level: one aggregate embedding of all evidence text, compared
against the ontology's concept vocabulary and the case's opportunity catalog. Uses no
KDAA provenance constraints, epistemic states, ownership reasoning, or opportunity-planning
gates -- claim-level ``cited_trace_ids`` are a best-effort lexical-match convenience for
audit reading, not a validated provenance link, and ``ownership`` is always
``UNRESOLVED`` since C0-S has no ownership-reasoning mechanism at all.

This module is under the truth-import boundary (see ``kdaa.evaluation.paper_b.boundary``):
it must only ever receive an ``InputSnapshot``, never a ``TruthBundle``.
"""

from __future__ import annotations

from kdaa.ontology import Ontology

from ..schemas import (
    InputSnapshot,
    OwnershipLabel,
    PredictedClaim,
    PredictedOpportunity,
    PredictionBundle,
)
from .embeddings import EmbeddingBackend, TfidfEmbeddingBackend, cosine_similarity

COMPARATOR_ID = "C0-S"
MAX_CONCEPTS = 10


def run_c0_s(
    snapshot: InputSnapshot,
    ontology: Ontology,
    *,
    embedding_backend: EmbeddingBackend | None = None,
) -> PredictionBundle:
    backend = embedding_backend or TfidfEmbeddingBackend()
    profile_text = " ".join(trace.normalized_text for trace in snapshot.traces)

    trace_concept_keys = {
        trace.trace_id: {match.key for match in ontology.match(trace.normalized_text)}
        for trace in snapshot.traces
    }

    claims = _rank_concepts(profile_text, ontology, backend, trace_concept_keys)
    ranked_opportunities = _rank_opportunities(profile_text, snapshot, backend)

    return PredictionBundle(
        case_id=snapshot.case_id,
        comparator_id=COMPARATOR_ID,
        claims=claims,
        ranked_opportunities=ranked_opportunities,
    )


def _rank_concepts(
    profile_text: str,
    ontology: Ontology,
    backend: EmbeddingBackend,
    trace_concept_keys: dict[str, set[str]],
) -> list[PredictedClaim]:
    concept_keys = sorted(ontology.concepts)
    concept_texts = [
        f"{ontology.concepts[key].label} {' '.join(ontology.concepts[key].terms)}"
        for key in concept_keys
    ]
    vectors = backend.embed_many([profile_text, *concept_texts])
    profile_vector, concept_vectors = vectors[0], vectors[1:]

    scored = [
        (key, cosine_similarity(profile_vector, vector))
        for key, vector in zip(concept_keys, concept_vectors, strict=True)
    ]
    scored.sort(key=lambda item: (-item[1], item[0]))
    top = [item for item in scored if item[1] > 0.0][:MAX_CONCEPTS]

    claims = []
    for key, score in top:
        label = ontology.concepts[key].label
        cited = sorted(
            trace_id for trace_id, keys in trace_concept_keys.items() if key in keys
        )
        claims.append(
            PredictedClaim(
                claim_id=f"c0s-{key}",
                label=label,
                bounded_claim=(
                    f"Profile-level semantic similarity to '{label}' "
                    f"(cosine similarity={score:.3f})."
                ),
                cited_trace_ids=cited,
                ownership=OwnershipLabel.UNRESOLVED,
            )
        )
    return claims


def _rank_opportunities(
    profile_text: str, snapshot: InputSnapshot, backend: EmbeddingBackend
) -> list[PredictedOpportunity]:
    opportunity_texts = [
        f"{candidate.title} {candidate.description}" for candidate in snapshot.opportunity_catalog
    ]
    vectors = backend.embed_many([profile_text, *opportunity_texts])
    profile_vector, opportunity_vectors = vectors[0], vectors[1:]

    scored = [
        (candidate.opportunity_id, cosine_similarity(profile_vector, vector))
        for candidate, vector in zip(snapshot.opportunity_catalog, opportunity_vectors, strict=True)
    ]
    scored.sort(key=lambda item: (-item[1], item[0]))
    return [
        PredictedOpportunity(
            opportunity_id=opportunity_id,
            rank=rank,
            rationale=f"Profile-level semantic similarity (cosine similarity={score:.3f}).",
        )
        for rank, (opportunity_id, score) in enumerate(scored, start=1)
    ]
