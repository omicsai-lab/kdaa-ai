"""Command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from kdaa.config import load_config
from kdaa.evaluation import run_robustness_suite, run_synthetic_benchmark
from kdaa.ingestion import (
    GitHubConnector,
    OpenAlexConnector,
    build_demo_scenario,
    load_bundle,
    merge_bundles,
    parse_cv_document,
)
from kdaa.models import UnitType
from kdaa.pipeline import KDAAPipeline

app = typer.Typer(
    name="kdaa",
    help="KDAA-AI: provenance-aware knowledge asset discovery, assessment, and amplification.",
    no_args_is_help=True,
)
console = Console()


def _write_bundle(bundle, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")


def _print_run_summary(run) -> None:
    table = Table(title=f"KDAA-AI — {run.unit.name}")
    table.add_column("Measure")
    table.add_column("Value", justify="right")
    table.add_row("Evidence traces", str(len(run.traces)))
    table.add_row("Asset records", str(len(run.assets)))
    table.add_row("Confirmed assets", str(len(run.confirmed_assets)))
    table.add_row("Opportunities", str(len(run.opportunities)))
    table.add_row("Run ID", run.manifest.run_id)
    console.print(table)
    if run.assets:
        console.print("\n[bold]Top provisional assets[/bold]")
        for asset in run.assets[:5]:
            credibility = asset.assessment.overall_credibility.value if asset.assessment else 0.0
            console.print(f" • {asset.label} [dim](credibility proxy {credibility:.2f})[/dim]")
    if run.opportunities:
        console.print("\n[bold]Top opportunities[/bold]")
        for opportunity in run.opportunities[:5]:
            console.print(
                f" • {opportunity.title} [dim](priority {opportunity.priority_score:.2f})[/dim]"
            )


@app.command()
def demo(
    output: Path = typer.Option(Path("results/demo"), "--output", "-o"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    scenario: str = typer.Option(
        "researcher",
        "--scenario",
        "-s",
        help="Fully synthetic focal-unit scenario: researcher, lab, or team.",
    ),
) -> None:
    """Run a fully synthetic demonstration end to end."""

    pipeline = KDAAPipeline(load_config(config))
    try:
        bundle = build_demo_scenario(scenario)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--scenario") from exc
    run, _ = pipeline.analyze(bundle, output_dir=output)
    _print_run_summary(run)
    console.print(f"\nOutputs: [bold]{output.resolve()}[/bold]")


@app.command()
def analyze(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    output: Path = typer.Option(Path("results/run"), "--output", "-o"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Analyze a UnitBundle JSON/YAML file."""

    bundle = load_bundle(input_path)
    pipeline = KDAAPipeline(load_config(config))
    run, _ = pipeline.analyze(bundle, output_dir=output)
    _print_run_summary(run)
    console.print(f"\nOutputs: [bold]{output.resolve()}[/bold]")


@app.command("ingest-cv")
def ingest_cv(
    document: Path = typer.Argument(..., exists=True, readable=True),
    unit_id: str = typer.Option(..., "--unit-id", help="Stable focal-unit identifier"),
    unit_name: str = typer.Option(..., "--unit-name", help="Focal-unit display name"),
    institution: Optional[str] = typer.Option(None, "--institution"),
    unit_type: UnitType = typer.Option(UnitType.RESEARCHER, "--unit-type"),
    output: Path = typer.Option(Path("data/cv_bundle.json"), "--output", "-o"),
) -> None:
    """Parse a local PDF/text CV-like document into a conservative evidence bundle."""

    bundle = parse_cv_document(
        document,
        unit_id=unit_id,
        unit_name=unit_name,
        institution=institution,
        unit_type=unit_type,
    )
    _write_bundle(bundle, output)
    console.print(f"Saved {len(bundle.traces)} sensitive provisional traces to [bold]{output.resolve()}[/bold]")
    console.print(
        "[yellow]Review section segmentation, identity, attribution, and privacy before analysis or sharing.[/yellow]"
    )


@app.command("fetch-openalex")
def fetch_openalex(
    identifier: str = typer.Argument(..., help="OpenAlex author ID, ORCID, or author name"),
    output: Path = typer.Option(Path("data/openalex_bundle.json"), "--output", "-o"),
    max_works: int = typer.Option(50, min=1, max=100),
) -> None:
    """Fetch a public scholarly-evidence bundle from OpenAlex."""

    connector = OpenAlexConnector()
    bundle = connector.fetch_bundle(identifier, max_works=max_works)
    _write_bundle(bundle, output)
    console.print(f"Saved {len(bundle.traces)} traces to [bold]{output.resolve()}[/bold]")
    console.print("[yellow]Review author identity and work attribution before analysis.[/yellow]")


@app.command("fetch-github")
def fetch_github(
    username: str = typer.Argument(...),
    output: Path = typer.Option(Path("data/github_bundle.json"), "--output", "-o"),
    max_repos: int = typer.Option(100, min=1, max=100),
    include_forks: bool = typer.Option(False, help="Include forked repositories"),
) -> None:
    """Fetch a public repository-evidence bundle from GitHub."""

    connector = GitHubConnector()
    bundle = connector.fetch_bundle(
        username,
        max_repos=max_repos,
        include_forks=include_forks,
    )
    _write_bundle(bundle, output)
    console.print(f"Saved {len(bundle.traces)} traces to [bold]{output.resolve()}[/bold]")


@app.command()
def benchmark(
    n_units: int = typer.Option(50, "--n-units", min=5, max=500),
    seed: int = typer.Option(42),
    output: Path = typer.Option(Path("results/benchmark"), "--output", "-o"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Run the controlled synthetic engineering benchmark."""

    result, _ = run_synthetic_benchmark(
        n_units=n_units,
        seed=seed,
        config=load_config(config),
        output_dir=output,
    )
    console.print_json(json.dumps(result.__dict__))
    console.print(f"\nOutputs: [bold]{output.resolve()}[/bold]")


@app.command("stress-test")
def stress_test(
    output: Path = typer.Option(Path("results/robustness"), "--output", "-o"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Run deterministic duplicate, staleness, attribution, drop, and noise perturbations."""

    result, _ = run_robustness_suite(
        config=load_config(config),
        output_dir=output,
    )
    console.print_json(json.dumps(result.__dict__))
    console.print(f"\nOutputs: [bold]{output.resolve()}[/bold]")


@app.command()
def merge(
    inputs: list[Path] = typer.Argument(..., exists=True, readable=True),
    output: Path = typer.Option(Path("data/merged_bundle.json"), "--output", "-o"),
) -> None:
    """Merge multiple UnitBundle JSON/YAML files into one evidence bundle."""

    bundles = [load_bundle(path) for path in inputs]
    merged = merge_bundles(bundles)
    _write_bundle(merged, output)
    console.print(
        f"Merged {len(bundles)} bundles and {len(merged.traces)} unique traces into "
        f"[bold]{output.resolve()}[/bold]"
    )


@app.command()
def schema(output: Optional[Path] = typer.Option(None, "--output", "-o")) -> None:
    """Print or save the JSON schema for an input UnitBundle."""

    from kdaa.models import UnitBundle

    payload = UnitBundle.model_json_schema()
    text = json.dumps(payload, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        console.print(f"Saved schema to [bold]{output.resolve()}[/bold]")
    else:
        console.print_json(text)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0"),
    port: int = typer.Option(8000),
    reload: bool = typer.Option(False),
) -> None:
    """Run the FastAPI service."""

    import uvicorn

    uvicorn.run("kdaa.api:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
