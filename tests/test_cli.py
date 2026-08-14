from pathlib import Path

from typer.testing import CliRunner

from kdaa.cli import app

runner = CliRunner()


def test_cli_schema_demo_and_bad_scenario(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.json"
    result = runner.invoke(app, ["schema", "--output", str(schema_path)])
    assert result.exit_code == 0
    assert schema_path.exists()

    output = tmp_path / "demo-team"
    result = runner.invoke(
        app,
        ["demo", "--scenario", "team", "--output", str(output)],
    )
    assert result.exit_code == 0
    assert (output / "analysis_run.json").exists()

    result = runner.invoke(app, ["demo", "--scenario", "invalid"])
    assert result.exit_code != 0


def test_cli_ingest_cv(tmp_path: Path) -> None:
    document = tmp_path / "cv.txt"
    document.write_text(
        "Publications\n\n2026. A provenance-aware AI methods paper with reusable software.",
        encoding="utf-8",
    )
    output = tmp_path / "cv-bundle.json"
    result = runner.invoke(
        app,
        [
            "ingest-cv",
            str(document),
            "--unit-id",
            "unit:cv-cli",
            "--unit-name",
            "Synthetic CV Researcher",
            "--institution",
            "Synthetic University",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0
    assert output.exists()
