"""Interactive KDAA-AI MVP.

Run with:
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import io
import json
import tempfile
import uuid
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from kdaa.config import KDAAConfig
from kdaa.discovery.provenance import (
    add_duplicate_trace_edges,
    build_evidence_graph,
    enrich_graph_with_analysis,
)
from kdaa.ingestion import (
    GitHubConnector,
    OpenAlexConnector,
    build_demo_scenario,
    deduplicate_traces,
    load_bundle_from_dict,
    parse_cv_document,
)
from kdaa.lifecycle import apply_calibration
from kdaa.models import CalibrationAction, CalibrationRecord, UnitBundle
from kdaa.pipeline import KDAAPipeline
from kdaa.providers.openai_compatible import OpenAICompatibleProvider
from kdaa.report import render_html, render_markdown, write_run_outputs


st.set_page_config(
    page_title="KDAA-AI",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def demo_bundle_dict(scenario: str) -> dict:
    return build_demo_scenario(scenario).model_dump(mode="json")


def _load_uploaded_bundle(uploaded) -> UnitBundle:
    raw = uploaded.getvalue().decode("utf-8")
    payload = (
        yaml.safe_load(raw)
        if uploaded.name.lower().endswith((".yaml", ".yml"))
        else json.loads(raw)
    )
    return load_bundle_from_dict(payload)


def _pipeline_from_sidebar() -> KDAAPipeline:
    mode = st.session_state.get("analysis_mode", "deterministic")
    config = KDAAConfig(mode=mode)
    if mode == "deterministic":
        return KDAAPipeline(config)
    api_key = st.session_state.get("llm_api_key", "")
    model = st.session_state.get("llm_model", "")
    base_url = st.session_state.get("llm_base_url", "https://api.openai.com/v1")
    if not api_key or not model:
        raise ValueError("Remote-model mode requires both a model name and API key.")
    provider = OpenAICompatibleProvider(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=0.1,
    )
    allow_sensitive = bool(st.session_state.get("allow_sensitive_remote", False))
    config = config.model_copy(
        update={
            "llm": config.llm.model_copy(
                update={
                    "enabled": True,
                    "model": model,
                    "base_url": base_url,
                    "allow_sensitive_traces": allow_sensitive,
                }
            )
        }
    )
    return KDAAPipeline(config, provider=provider)


def _graphviz_for_run(run) -> str:
    lines = [
        "digraph KDAA {",
        'graph [rankdir="LR", bgcolor="transparent", pad="0.25", nodesep="0.35", ranksep="0.65", splines="ortho"];',
        'node [shape="box", style="rounded,filled", fontname="Helvetica", fontsize="10", margin="0.10,0.06"];',
        'edge [fontname="Helvetica", fontsize="8", color="#7b8794", arrowsize="0.65"];',
        f'unit [label={json.dumps(run.unit.name)}, fillcolor="#dcecf6", color="#39749a", penwidth="1.4"];',
    ]
    asset_nodes: dict[str, str] = {}
    for index, asset in enumerate(run.assets[:14]):
        node = f"asset_{index}"
        asset_nodes[asset.id] = node
        credibility = asset.assessment.overall_credibility.value if asset.assessment else 0.0
        label = f"{asset.label}\\ncredibility {credibility:.2f}"
        fill = "#e7f3eb" if asset.epistemic_state.value == "confirmed" else "#f4f1df"
        lines.append(
            f'{node} [label={json.dumps(label)}, fillcolor="{fill}", color="#7c7a55"];'
        )
        lines.append(f'unit -> {node} [label="hypothesis"];')
    for index, opportunity in enumerate(run.opportunities[:10]):
        node = f"opp_{index}"
        label = f"{opportunity.output_container.value}\\n{opportunity.priority_score:.2f}"
        lines.append(
            f'{node} [shape="ellipse", label={json.dumps(label)}, fillcolor="#eee6f7", color="#78559a"];'
        )
        for asset_id in opportunity.asset_ids:
            if asset_id in asset_nodes:
                lines.append(f'{asset_nodes[asset_id]} -> {node} [label="fit"];')
    lines.append("}")
    return "\n".join(lines)


def _run_to_zip(run) -> bytes:
    bundle = UnitBundle(unit=run.unit, goals=run.goals, traces=run.traces, metadata={})
    deduplication = deduplicate_traces(run.traces)
    base_graph = add_duplicate_trace_edges(
        build_evidence_graph(bundle), deduplication.duplicate_to_canonical
    )
    graph = enrich_graph_with_analysis(base_graph, run)
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp)
        write_run_outputs(run, graph, output)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(output.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(output))
        return buffer.getvalue()


st.title("KDAA-AI")
st.caption("Knowledge Asset Discovery · Assessment · Amplification")
st.info(
    "The MVP produces evidence-linked hypotheses and provisional asset records. "
    "It does not confirm expertise, ownership, or realized value without later review and outcomes."
)

with st.sidebar:
    st.header("1. Evidence source")
    source = st.radio(
        "Choose input",
        [
            "Synthetic demo",
            "Upload UnitBundle",
            "CV/PDF document",
            "OpenAlex author",
            "GitHub user",
        ],
        label_visibility="collapsed",
    )

    bundle = None
    if source == "Synthetic demo":
        scenario = st.selectbox(
            "Synthetic focal unit",
            ["researcher", "lab", "team"],
            help="All scenarios are fictional and redistributable.",
        )
        bundle = UnitBundle.model_validate(demo_bundle_dict(scenario))
        st.caption("Fully synthetic; safe for demonstration and screenshots.")
    elif source == "Upload UnitBundle":
        uploaded = st.file_uploader("JSON or YAML", type=["json", "yaml", "yml"])
        if uploaded:
            try:
                bundle = _load_uploaded_bundle(uploaded)
            except Exception as exc:
                st.error(f"Could not load bundle: {exc}")
    elif source == "CV/PDF document":
        uploaded_document = st.file_uploader(
            "PDF or text CV-like document",
            type=["pdf", "txt", "md", "rst", "tex"],
        )
        cv_unit_name = st.text_input("Focal-unit name")
        cv_unit_id = st.text_input("Stable focal-unit ID", value="unit:researcher")
        cv_institution = st.text_input("Institution (optional)")
        if st.button("Parse local document", use_container_width=True):
            if not uploaded_document or not cv_unit_name.strip() or not cv_unit_id.strip():
                st.error("A document, focal-unit name, and stable focal-unit ID are required.")
            else:
                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir) / uploaded_document.name
                        temp_path.write_bytes(uploaded_document.getvalue())
                        parsed = parse_cv_document(
                            temp_path,
                            unit_id=cv_unit_id.strip(),
                            unit_name=cv_unit_name.strip(),
                            institution=cv_institution.strip() or None,
                        )
                    st.session_state["cv_bundle"] = parsed
                except Exception as exc:
                    st.error(f"Document parsing failed: {exc}")
        bundle = st.session_state.get("cv_bundle")
        st.caption(
            "CV/PDF parsing is heuristic. Imported traces are marked sensitive and require review."
        )
    elif source == "OpenAlex author":
        identifier = st.text_input("OpenAlex ID, ORCID, or name")
        max_works = st.slider("Maximum works", 5, 100, 40, 5)
        if st.button("Fetch OpenAlex", use_container_width=True):
            try:
                with st.spinner("Fetching public scholarly metadata..."):
                    bundle = OpenAlexConnector().fetch_bundle(identifier, max_works=max_works)
                    st.session_state["openalex_bundle"] = bundle
            except Exception as exc:
                st.error(f"OpenAlex fetch failed: {exc}")
        bundle = st.session_state.get("openalex_bundle")
    elif source == "GitHub user":
        username = st.text_input("GitHub username")
        max_repos = st.slider("Maximum repositories", 5, 100, 50, 5)
        include_forks = st.checkbox("Include forks", False)
        if st.button("Fetch GitHub", use_container_width=True):
            try:
                with st.spinner("Fetching public repository metadata..."):
                    bundle = GitHubConnector().fetch_bundle(
                        username,
                        max_repos=max_repos,
                        include_forks=include_forks,
                    )
                    st.session_state["github_bundle"] = bundle
            except Exception as exc:
                st.error(f"GitHub fetch failed: {exc}")
        bundle = st.session_state.get("github_bundle")

    st.header("2. Analysis mode")
    analysis_mode = st.selectbox(
        "Mode",
        ["deterministic", "hybrid", "llm"],
        help="Deterministic is local and reproducible. Hybrid adds provenance-gated model suggestions.",
        key="analysis_mode",
    )
    if analysis_mode != "deterministic":
        with st.expander("Remote model settings", expanded=True):
            st.text_input("Base URL", value="https://api.openai.com/v1", key="llm_base_url")
            st.text_input("Model", key="llm_model")
            st.text_input("API key", type="password", key="llm_api_key")
            st.checkbox(
                "Allow sensitive traces to leave this machine",
                value=False,
                key="allow_sensitive_remote",
            )

    st.header("3. Run")
    if bundle:
        st.write(f"**{bundle.unit.name}**")
        st.caption(f"{len(bundle.traces)} traces · {bundle.unit.unit_type.value}")
    run_button = st.button("Run KDAA analysis", type="primary", use_container_width=True, disabled=bundle is None)
    if run_button and bundle:
        try:
            with st.spinner("Building evidence graph and provisional asset portfolio..."):
                pipeline = _pipeline_from_sidebar()
                run, graph = pipeline.analyze(bundle)
                st.session_state["run"] = run
                st.session_state["graph"] = graph
                st.session_state["bundle_used"] = bundle
        except Exception as exc:
            st.error(f"Analysis failed: {exc}")

run = st.session_state.get("run")
if run is None:
    st.markdown(
        """
### What the first version does

1. Ingests heterogeneous traces from a structured bundle, a CV/PDF, OpenAlex, GitHub, or a synthetic case.
2. Separates observable traces from falsifiable asset hypotheses.
3. Attaches claim-level provenance and transparent proxy assessments.
4. Matches assets to opportunity-specific human–AI workflows and credible baselines.
5. Exports a portfolio, reports, CSVs, JSON, and a provenance graph.

The human loop is implemented but is not required to run the system or reproduce the synthetic benchmark.
"""
    )
    st.stop()

metric_cols = st.columns(5)
metric_cols[0].metric("Evidence traces", len(run.traces))
metric_cols[1].metric("Asset records", len(run.assets))
metric_cols[2].metric("Confirmed", len(run.confirmed_assets))
metric_cols[3].metric("Opportunities", len(run.opportunities))
metric_cols[4].metric("Graph edges", run.graph_summary.get("edges", 0))

(
    overview_tab,
    evidence_tab,
    assets_tab,
    opportunities_tab,
    graph_tab,
    calibration_tab,
    export_tab,
) = st.tabs(
    [
        "Overview",
        "Evidence",
        "Assets",
        "Opportunities",
        "Provenance",
        "Calibration",
        "Export",
    ]
)

with overview_tab:
    st.subheader(run.unit.name)
    st.write(run.unit.description)
    if run.goals:
        st.markdown("**Strategic goals**")
        for goal in run.goals:
            st.write(f"- {goal.label}: {goal.description}")
    st.markdown("**Scope warnings**")
    for warning in run.warnings:
        st.warning(warning, icon="⚠️")

with evidence_tab:
    evidence_rows = [
        {
            "id": trace.id,
            "type": trace.trace_type.value,
            "title": trace.title,
            "source": trace.source_kind.value,
            "date": trace.event_date,
            "role": trace.contribution_role.value,
            "sensitive": trace.sensitive,
        }
        for trace in run.traces
    ]
    st.dataframe(pd.DataFrame(evidence_rows), use_container_width=True, hide_index=True)

with assets_tab:
    asset_rows = []
    for asset in run.assets:
        a = asset.assessment
        asset_rows.append(
            {
                "asset": asset.label,
                "state": asset.epistemic_state.value,
                "categories": ", ".join(category.value for category in asset.categories),
                "credibility": a.overall_credibility.value if a else None,
                "evidence_strength": a.evidence_strength.value if a else None,
                "attribution": a.attribution_confidence.value if a else None,
                "tacitness": a.tacitness.value if a else None,
                "transferability": a.transferability.value if a else None,
                "AI interfaceability": a.ai_interfaceability.value if a else None,
                "human review": asset.human_calibration_required,
            }
        )
    frame = pd.DataFrame(asset_rows)
    st.dataframe(frame, use_container_width=True, hide_index=True)
    if not run.assets:
        st.info("No asset hypotheses were generated for the supplied evidence and configuration.")
    else:
        selected_label = st.selectbox("Inspect asset", [asset.label for asset in run.assets])
        selected = next(asset for asset in run.assets if asset.label == selected_label)
        st.markdown(f"**Bounded claim:** {selected.bounded_claim}")
        st.markdown("**Non-claims / exclusions**")
        for item in selected.exclusions:
            st.write(f"- {item}")
        st.markdown("**Evidence links**")
        st.json([link.model_dump(mode="json") for link in selected.evidence_links], expanded=False)

with opportunities_tab:
    rows = [
        {
            "opportunity": item.title,
            "container": item.output_container.value,
            "pathways": ", ".join(path.value for path in item.value_pathways),
            "fit": item.fit_score,
            "amplifiability": item.amplifiability_score,
            "readiness": item.readiness_score,
            "risk": item.governance_risk,
            "priority": item.priority_score,
            "effort": item.estimated_effort,
        }
        for item in run.opportunities
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if not run.opportunities:
        st.info("No opportunities passed the configured fit threshold.")
    else:
        selected_title = st.selectbox("Inspect opportunity", [item.title for item in run.opportunities])
        selected_opp = next(item for item in run.opportunities if item.title == selected_title)
        st.markdown(f"**Credible baseline:** {selected_opp.credible_baseline}")
        left, right = st.columns(2)
        with left:
            st.markdown("**AI tasks**")
            for item in selected_opp.ai_tasks:
                st.write(f"- {item}")
        with right:
            st.markdown("**Human tasks and verification**")
            for item in selected_opp.human_tasks:
                st.write(f"- {item}")
            for item in selected_opp.verification_gates:
                st.write(f"- Gate: {item}")

with graph_tab:
    st.graphviz_chart(_graphviz_for_run(run), use_container_width=True)
    st.caption("Simplified view. Full trace-level provenance is available in GraphML and JSON exports.")

with calibration_tab:
    st.info("Calibration is optional for the MVP and is preserved as a delta from the AI-only map.")
    if not run.assets:
        st.info("There are no asset records to calibrate.")
    else:
        asset = st.selectbox("Asset to review", run.assets, format_func=lambda item: item.label)
        action = st.selectbox("Action", list(CalibrationAction), format_func=lambda item: item.value)
        revised_claim = st.text_area("Revised bounded claim", value=asset.bounded_claim)
        notes = st.text_area("Review notes")
        if st.button("Apply calibration record"):
            record = CalibrationRecord(
                id=f"cal-{uuid.uuid4().hex[:10]}",
                run_id=run.manifest.run_id,
                asset_id=asset.id,
                action=action,
                notes=notes,
                revised_claim=revised_claim if revised_claim != asset.bounded_claim else None,
            )
            run = apply_calibration(run, [record])
            st.session_state["run"] = run
            st.success("Calibration recorded without overwriting the original hypothesis.")
            st.rerun()

with export_tab:
    st.download_button(
        "Download complete run package (.zip)",
        data=_run_to_zip(run),
        file_name=f"kdaa-{run.unit.id.replace(':', '-')}-{run.manifest.run_id}.zip",
        mime="application/zip",
        use_container_width=True,
    )
    st.download_button(
        "Download analysis JSON",
        data=run.model_dump_json(indent=2),
        file_name="analysis_run.json",
        mime="application/json",
    )
    st.download_button(
        "Download Markdown report",
        data=render_markdown(run),
        file_name="portfolio_report.md",
        mime="text/markdown",
    )
    st.download_button(
        "Download HTML report",
        data=render_html(run),
        file_name="portfolio_report.html",
        mime="text/html",
    )
