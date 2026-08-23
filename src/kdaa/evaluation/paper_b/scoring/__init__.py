"""Case-level Paper B scorers (E1-E4). All scorer-side: these modules read truth and
must never be imported by ``kdaa.evaluation.paper_b.adapters``.
"""

from __future__ import annotations

from .attribution import AttributionResult, score_attribution
from .concept_matching import ConceptMatchResult, score_concepts
from .opportunities import NdcgResult, score_opportunities
from .semantic_support import SemanticSupportResult, score_semantic_support

__all__ = [
    "AttributionResult",
    "ConceptMatchResult",
    "NdcgResult",
    "SemanticSupportResult",
    "score_attribution",
    "score_concepts",
    "score_opportunities",
    "score_semantic_support",
]
