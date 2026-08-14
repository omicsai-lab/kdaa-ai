"""Provenance-aware asset-hypothesis discovery."""

from .features import TraceFeatures, extract_trace_features
from .provenance import (
    add_duplicate_trace_edges,
    build_evidence_graph,
    enrich_graph_with_analysis,
)
from .rules import discover_asset_hypotheses

__all__ = [
    "TraceFeatures",
    "add_duplicate_trace_edges",
    "build_evidence_graph",
    "discover_asset_hypotheses",
    "enrich_graph_with_analysis",
    "extract_trace_features",
]
