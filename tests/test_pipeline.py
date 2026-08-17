from kdaa.config import KDAAConfig
from kdaa.ingestion.synthetic import build_demo_bundle
from kdaa.pipeline import KDAAPipeline


def test_pipeline_end_to_end() -> None:
    run, graph = KDAAPipeline(KDAAConfig()).analyze(build_demo_bundle())
    assert len(run.traces) >= 15
    assert len(run.assets) >= 8
    assert len(run.opportunities) >= 5
    assert graph.number_of_nodes() > len(run.traces)
    assert all(asset.epistemic_state.value != "confirmed" for asset in run.assets)
    trace_ids = {trace.id for trace in run.traces}
    for asset in run.assets:
        support = [link.trace_id for link in asset.evidence_links if link.role.value == "supporting"]
        assert support
        assert set(support) <= trace_ids
    containers = {item.output_container.value for item in run.opportunities}
    assert "repository" in containers
    assert "living_document" in containers
    assert "structured_knowledge_base" in containers
    assert "deployable_product" in containers
    assert "public_content" in containers


def test_pipeline_is_deterministic_except_run_id() -> None:
    bundle = build_demo_bundle()
    pipeline = KDAAPipeline(KDAAConfig())
    first, _ = pipeline.analyze(bundle)
    second, _ = pipeline.analyze(bundle)
    first_assets = [(a.label, a.bounded_claim, [link.trace_id for link in a.evidence_links]) for a in first.assets]
    second_assets = [(a.label, a.bounded_claim, [link.trace_id for link in a.evidence_links]) for a in second.assets]
    assert first_assets == second_assets
