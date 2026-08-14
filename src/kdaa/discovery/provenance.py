"""Evidence graph construction and export helpers."""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from kdaa.models import AnalysisRun, UnitBundle


def build_evidence_graph(bundle: UnitBundle) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    unit = bundle.unit
    graph.add_node(
        unit.id,
        node_type="focal_unit",
        label=unit.name,
        unit_type=unit.unit_type.value,
        institution=unit.institution or "",
        synthetic=unit.is_synthetic,
    )
    for trace in bundle.traces:
        graph.add_node(
            trace.id,
            node_type="trace",
            label=trace.title,
            trace_type=trace.trace_type.value,
            source_kind=trace.source_kind.value,
            event_date=trace.event_date.isoformat() if trace.event_date else "",
            role=trace.contribution_role.value,
            sensitive=trace.sensitive,
        )
        graph.add_edge(unit.id, trace.id, relation="has_trace")
        for contributor in trace.authors_or_contributors:
            contributor_id = f"person:{contributor.strip().lower()}"
            graph.add_node(
                contributor_id,
                node_type="contributor",
                label=contributor,
            )
            graph.add_edge(trace.id, contributor_id, relation="has_contributor")
        for affiliation in trace.affiliations:
            affiliation_id = f"institution:{affiliation.strip().lower()}"
            graph.add_node(
                affiliation_id,
                node_type="institution",
                label=affiliation,
            )
            graph.add_edge(trace.id, affiliation_id, relation="affiliated_with")
        for related_id in trace.related_trace_ids:
            if related_id:
                graph.add_edge(trace.id, related_id, relation="related_to")
    return graph


def add_duplicate_trace_edges(
    graph: nx.MultiDiGraph, duplicate_to_canonical: dict[str, str]
) -> nx.MultiDiGraph:
    """Annotate retained input traces that were excluded as duplicate evidence."""

    for duplicate_id, canonical_id in duplicate_to_canonical.items():
        if duplicate_id in graph and canonical_id in graph:
            graph.nodes[duplicate_id]["analysis_excluded"] = True
            graph.nodes[duplicate_id]["exclusion_reason"] = "duplicate_trace"
            graph.add_edge(
                duplicate_id,
                canonical_id,
                relation="possible_duplicate_of",
            )
    return graph


def enrich_graph_with_analysis(graph: nx.MultiDiGraph, run: AnalysisRun) -> nx.MultiDiGraph:
    graph = graph.copy()
    for asset in run.assets:
        graph.add_node(
            asset.id,
            node_type="asset",
            label=asset.label,
            epistemic_state=asset.epistemic_state.value,
            credibility=(
                asset.assessment.overall_credibility.value if asset.assessment else 0.0
            ),
            categories="|".join(category.value for category in asset.categories),
        )
        graph.add_edge(run.unit.id, asset.id, relation="has_asset_hypothesis")
        for evidence_link in asset.evidence_links:
            graph.add_edge(
                evidence_link.trace_id,
                asset.id,
                relation=evidence_link.relation,
                evidence_role=evidence_link.role.value,
                weight=evidence_link.weight,
            )
    for opportunity in run.opportunities:
        graph.add_node(
            opportunity.id,
            node_type="opportunity",
            label=opportunity.title,
            container=opportunity.output_container.value,
            priority=opportunity.priority_score,
        )
        graph.add_edge(run.unit.id, opportunity.id, relation="has_opportunity")
        for asset_id in opportunity.asset_ids:
            graph.add_edge(asset_id, opportunity.id, relation="matched_to")
    for calibration in run.calibration_records:
        calibration_id = f"calibration:{calibration.id}"
        graph.add_node(
            calibration_id,
            node_type="calibration",
            label=calibration.action.value,
        )
        graph.add_edge(calibration_id, calibration.asset_id, relation="calibrates")
    for outcome in run.outcome_records:
        outcome_id = f"outcome:{outcome.id}"
        graph.add_node(outcome_id, node_type="outcome", label=outcome.id)
        graph.add_edge(outcome.opportunity_id, outcome_id, relation="produces")
    return graph


def graph_summary(graph: nx.MultiDiGraph) -> dict[str, int | float | str]:
    node_types: dict[str, int] = {}
    for _, data in graph.nodes(data=True):
        key = str(data.get("node_type", "unknown"))
        node_types[key] = node_types.get(key, 0) + 1
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "density": round(nx.density(nx.DiGraph(graph)), 6) if graph.number_of_nodes() > 1 else 0.0,
        "node_types": json.dumps(node_types, sort_keys=True),
    }


def write_graphml(graph: nx.MultiDiGraph, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    # GraphML supports scalar values only.
    sanitized = nx.MultiDiGraph()
    for node, data in graph.nodes(data=True):
        sanitized.add_node(node, **{k: _scalar(v) for k, v in data.items()})
    for u, v, key, data in graph.edges(keys=True, data=True):
        sanitized.add_edge(u, v, key=key, **{k: _scalar(val) for k, val in data.items()})
    nx.write_graphml(sanitized, output)


def _scalar(value: object) -> str | int | float | bool:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, sort_keys=True, default=str)
