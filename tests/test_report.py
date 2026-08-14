from pathlib import Path

from kdaa.config import KDAAConfig
from kdaa.ingestion.synthetic import build_demo_bundle
from kdaa.pipeline import KDAAPipeline
from kdaa.report import render_html, render_markdown, write_run_outputs


def test_reports_render_and_export(tmp_path: Path) -> None:
    run, graph = KDAAPipeline(KDAAConfig()).analyze(build_demo_bundle())
    markdown = render_markdown(run)
    html = render_html(run)
    assert "Epistemic status" in markdown
    assert "KDAA-AI Knowledge Asset Portfolio" in html
    paths = write_run_outputs(run, graph, tmp_path)
    assert paths["analysis_run"].exists()
    assert paths["graphml"].exists()
    assert paths["assets_csv"].read_text(encoding="utf-8").startswith("asset_id")
