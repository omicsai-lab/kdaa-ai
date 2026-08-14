import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = r"""
import json
from kdaa.ingestion import build_demo_bundle
from kdaa.pipeline import KDAAPipeline

run, _ = KDAAPipeline().analyze(build_demo_bundle())
payload = [
    {
        "label": asset.label,
        "claim": asset.bounded_claim,
        "concept_tags": asset.concept_tags,
        "evidence": sorted(link.trace_id for link in asset.evidence_links),
        "state": asset.epistemic_state.value,
    }
    for asset in run.assets
]
print(json.dumps(payload, sort_keys=True))
"""


def _signature(hash_seed: str) -> object:
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = hash_seed
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_asset_signature_is_stable_across_python_hash_seeds() -> None:
    assert _signature("1") == _signature("777")
