"""Minimal programmatic KDAA-AI example using only synthetic evidence."""

from pathlib import Path

from kdaa.config import KDAAConfig
from kdaa.ingestion import build_demo_scenario
from kdaa.pipeline import KDAAPipeline


def main() -> None:
    bundle = build_demo_scenario("researcher")
    run, _ = KDAAPipeline(KDAAConfig()).analyze(
        bundle,
        output_dir=Path("results/example-basic"),
    )

    print(f"Focal unit: {run.unit.name}")
    print(f"Evidence traces: {len(run.traces)}")
    print(f"Asset hypotheses: {len(run.assets)}")
    print(f"Automatically confirmed assets: {len(run.confirmed_assets)}")
    print(f"Amplification opportunities: {len(run.opportunities)}")
    if run.opportunities:
        top = run.opportunities[0]
        print(f"Top opportunity: {top.title} ({top.priority_score:.3f})")


if __name__ == "__main__":
    main()
