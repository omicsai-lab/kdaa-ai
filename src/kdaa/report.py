"""Research-grade export of an analysis run."""

from __future__ import annotations

import csv
import json
from collections import Counter
from importlib.resources import files
from pathlib import Path
from typing import Any

import networkx as nx
from jinja2 import Environment, select_autoescape

from kdaa.discovery.provenance import write_graphml
from kdaa.models import AnalysisRun


def _json_default(value: Any) -> str:
    return str(value)


def render_markdown(run: AnalysisRun) -> str:
    resource = files("kdaa.resources").joinpath("report.md.j2")
    template_text = resource.read_text(encoding="utf-8")
    environment = Environment(autoescape=False, trim_blocks=True, lstrip_blocks=True)
    template = environment.from_string(template_text)
    trace_counts = dict(sorted(Counter(trace.trace_type.value for trace in run.traces).items()))
    return template.render(run=run, trace_counts=trace_counts).strip() + "\n"


def render_html(run: AnalysisRun) -> str:
    resource = files("kdaa.resources").joinpath("report.html.j2")
    template_text = resource.read_text(encoding="utf-8")
    environment = Environment(
        autoescape=select_autoescape(default_for_string=True, default=True),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.from_string(template_text)
    return template.render(run=run)


def write_run_outputs(
    run: AnalysisRun,
    graph: nx.MultiDiGraph,
    output_dir: str | Path,
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    run_json = output / "analysis_run.json"
    run_json.write_text(
        json.dumps(run.model_dump(mode="json"), indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    paths["analysis_run"] = run_json

    manifest_json = output / "run_manifest.json"
    manifest_json.write_text(
        json.dumps(run.manifest.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    paths["manifest"] = manifest_json

    assets_csv = output / "asset_portfolio.csv"
    with assets_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "asset_id",
                "label",
                "state",
                "categories",
                "concept_tags",
                "credibility",
                "tacitness",
                "transferability",
                "ai_interfaceability",
                "human_calibration_required",
                "supporting_trace_ids",
            ],
        )
        writer.writeheader()
        for asset in run.assets:
            assessment = asset.assessment
            writer.writerow(
                {
                    "asset_id": asset.id,
                    "label": asset.label,
                    "state": asset.epistemic_state.value,
                    "categories": "|".join(category.value for category in asset.categories),
                    "concept_tags": "|".join(asset.concept_tags),
                    "credibility": assessment.overall_credibility.value if assessment else "",
                    "tacitness": assessment.tacitness.value if assessment else "",
                    "transferability": assessment.transferability.value if assessment else "",
                    "ai_interfaceability": assessment.ai_interfaceability.value if assessment else "",
                    "human_calibration_required": asset.human_calibration_required,
                    "supporting_trace_ids": "|".join(
                        link.trace_id for link in asset.evidence_links if link.role.value == "supporting"
                    ),
                }
            )
    paths["assets_csv"] = assets_csv

    opportunities_csv = output / "opportunities.csv"
    with opportunities_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "opportunity_id",
                "title",
                "container",
                "value_pathways",
                "asset_ids",
                "fit",
                "amplifiability",
                "readiness",
                "governance_risk",
                "priority",
                "effort",
                "horizon",
            ],
        )
        writer.writeheader()
        for item in run.opportunities:
            writer.writerow(
                {
                    "opportunity_id": item.id,
                    "title": item.title,
                    "container": item.output_container.value,
                    "value_pathways": "|".join(pathway.value for pathway in item.value_pathways),
                    "asset_ids": "|".join(item.asset_ids),
                    "fit": item.fit_score,
                    "amplifiability": item.amplifiability_score,
                    "readiness": item.readiness_score,
                    "governance_risk": item.governance_risk,
                    "priority": item.priority_score,
                    "effort": item.estimated_effort,
                    "horizon": item.time_horizon,
                }
            )
    paths["opportunities_csv"] = opportunities_csv

    markdown = output / "portfolio_report.md"
    markdown.write_text(render_markdown(run), encoding="utf-8")
    paths["report_markdown"] = markdown

    html = output / "portfolio_report.html"
    html.write_text(render_html(run), encoding="utf-8")
    paths["report_html"] = html

    graphml = output / "provenance_graph.graphml"
    write_graphml(graph, graphml)
    paths["graphml"] = graphml

    graph_json = output / "provenance_graph.json"
    graph_json.write_text(
        json.dumps(nx.node_link_data(graph, edges="edges"), indent=2, default=_json_default),
        encoding="utf-8",
    )
    paths["graph_json"] = graph_json
    return paths
