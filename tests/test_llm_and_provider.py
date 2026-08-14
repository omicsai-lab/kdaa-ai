import pytest

from kdaa.config import KDAAConfig
from kdaa.discovery.llm import discover_with_llm
from kdaa.ingestion.synthetic import build_demo_bundle
from kdaa.pipeline import KDAAPipeline
from kdaa.providers.openai_compatible import _parse_json_object


class FakeProvider:
    model_name = "fake-json-model"

    def generate_json(self, *, system: str, user: str) -> dict:
        assert "trace is not an asset" in system.lower()
        assert "max_suggestions" in user
        return {
            "suggestions": [
                {
                    "label": "Evidence-grounded synthetic capability",
                    "bounded_claim": "The unit appears able to externalize a documented workflow in the supplied context.",
                    "enables": ["bounded workflow reuse"],
                    "exclusions": ["general expertise outside the supplied evidence"],
                    "categories": ["codified"],
                    "concept_tags": ["Reproducible research"],
                    "supporting_trace_ids": ["trace-syn-maya-chen-001"],
                    "contradicting_trace_ids": ["does-not-exist"],
                    "alternative_explanations": ["The trace may reflect collaborator-led work."],
                    "dependencies": ["attribution review"],
                    "confidence": 0.62,
                },
                {
                    "label": "Unsupported suggestion",
                    "bounded_claim": "This must be discarded.",
                    "categories": ["codified"],
                    "supporting_trace_ids": ["does-not-exist"],
                },
                {"not": "valid"},
            ]
        }


def test_provenance_gated_llm_discovery() -> None:
    bundle = build_demo_bundle()
    records = discover_with_llm(bundle, FakeProvider())
    assert len(records) == 1
    assert records[0].discovery_method.endswith("fake-json-model")
    assert [link.trace_id for link in records[0].evidence_links] == [
        "trace-syn-maya-chen-001"
    ]
    assert records[0].epistemic_state.value == "hypothesis"


def test_hybrid_pipeline_with_fake_provider() -> None:
    config = KDAAConfig.model_validate(
        {
            "mode": "hybrid",
            "llm": {"enabled": True, "model": "fake-json-model"},
        }
    )
    run, _ = KDAAPipeline(config, provider=FakeProvider()).analyze(build_demo_bundle())
    assert any(asset.id.startswith("asset-llm") for asset in run.assets)
    assert run.manifest.mode == "hybrid"
    assert run.manifest.llm_model == "fake-json-model"


def test_provider_json_parser() -> None:
    assert _parse_json_object('{"a": 1}') == {"a": 1}
    assert _parse_json_object('```json\n{"b": 2}\n```') == {"b": 2}
    assert _parse_json_object('prefix {"c": 3} suffix') == {"c": 3}
    with pytest.raises(ValueError):
        _parse_json_object("no object")
    with pytest.raises(ValueError):
        _parse_json_object("[1, 2, 3]")
