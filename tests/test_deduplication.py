from kdaa.ingestion import deduplicate_traces, merge_bundles
from kdaa.ingestion.synthetic import build_demo_bundle
from kdaa.pipeline import KDAAPipeline


def _asset_signature(run) -> set[tuple[str, tuple[str, ...]]]:
    return {(asset.label, tuple(sorted(asset.concept_tags))) for asset in run.assets}


def test_exact_duplicate_is_retained_but_not_counted_twice() -> None:
    bundle = build_demo_bundle()
    original = bundle.traces[0]
    duplicate = original.model_copy(update={"id": f"{original.id}-copy"})
    duplicated_bundle = bundle.model_copy(update={"traces": [*bundle.traces, duplicate]})

    result = deduplicate_traces(duplicated_bundle.traces)
    assert result.duplicate_to_canonical[duplicate.id] == original.id
    assert len(result.canonical_traces) == len(bundle.traces)

    base_run, _ = KDAAPipeline().analyze(bundle)
    duplicate_run, graph = KDAAPipeline().analyze(duplicated_bundle)
    assert _asset_signature(duplicate_run) == _asset_signature(base_run)
    assert len(duplicate_run.assets) == len(base_run.assets)
    assert graph.has_edge(duplicate.id, original.id)
    assert any("duplicate trace" in warning for warning in duplicate_run.warnings)


def test_merge_preserves_multiple_segments_from_one_document() -> None:
    bundle = build_demo_bundle()
    first = bundle.traces[0].model_copy(
        update={
            "id": "trace-doc-segment-a",
            "source_uri": "file:///tmp/example-cv.pdf",
            "title": "Publication segment",
        }
    )
    second = bundle.traces[1].model_copy(
        update={
            "id": "trace-doc-segment-b",
            "source_uri": "file:///tmp/example-cv.pdf",
            "title": "Software segment",
        }
    )
    one = bundle.model_copy(update={"traces": [first, second]})
    two = bundle.model_copy(
        update={"traces": [first.model_copy(update={"id": "trace-doc-segment-a-copy"})]}
    )

    merged = merge_bundles([one, two])
    assert {trace.title for trace in merged.traces} == {
        "Publication segment",
        "Software segment",
    }
