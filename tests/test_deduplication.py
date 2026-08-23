from kdaa.discovery.provenance import (
    add_duplicate_trace_edges,
    add_trace_relation_edges,
    build_evidence_graph,
)
from kdaa.ingestion import deduplicate_traces, independent_support_groups, merge_bundles
from kdaa.ingestion.synthetic import build_demo_bundle
from kdaa.models import TraceRelation, TraceRelationType
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


# --- B3: typed relations distinguish exact-duplicate vs source-record-equivalent ---------


def test_exact_duplicate_emits_typed_relation() -> None:
    bundle = build_demo_bundle()
    original = bundle.traces[0]
    duplicate = original.model_copy(update={"id": f"{original.id}-copy"})

    result = deduplicate_traces([original, duplicate])
    assert len(result.trace_relations) == 1
    relation = result.trace_relations[0]
    assert relation.source_trace_id == duplicate.id
    assert relation.target_trace_id == original.id
    assert relation.relation_type == TraceRelationType.EXACT_DUPLICATE
    assert relation.confidence == 1.0
    assert relation.rationale
    assert relation.detection_method


def test_source_record_equivalent_emits_distinct_typed_relation() -> None:
    bundle = build_demo_bundle()
    original = bundle.traces[0].model_copy(
        update={"source_record_id": "strong-source-id-123"}
    )
    # Different title/description (not the same normalized content) but the same strong
    # source record identifier -- this is source-record equivalence, not exact duplication.
    equivalent = original.model_copy(
        update={"id": f"{original.id}-alt-segment", "title": "A differently worded title"}
    )

    result = deduplicate_traces([original, equivalent])
    assert len(result.trace_relations) == 1
    relation = result.trace_relations[0]
    assert relation.relation_type == TraceRelationType.SOURCE_RECORD_EQUIVALENT
    assert relation.source_trace_id == equivalent.id
    assert relation.target_trace_id == original.id


def test_deduplication_does_not_detect_semantic_near_duplicates() -> None:
    # WP2 provides exact/source-equivalence machinery only; two traces with genuinely
    # different content and no strong source identity are not merged, even if a human
    # reader might judge them semantically related.
    bundle = build_demo_bundle()
    first = bundle.traces[0].model_copy(
        update={"id": "trace-semantic-a", "title": "Deep learning for protein folding"}
    )
    second = bundle.traces[0].model_copy(
        update={"id": "trace-semantic-b", "title": "Neural networks applied to protein structure"}
    )
    result = deduplicate_traces([first, second])
    assert result.duplicate_count == 0
    assert result.trace_relations == []


def test_duplicate_to_canonical_and_canonical_traces_remain_backward_compatible() -> None:
    bundle = build_demo_bundle()
    original = bundle.traces[0]
    duplicate = original.model_copy(update={"id": f"{original.id}-copy"})
    result = deduplicate_traces([original, duplicate])
    assert result.duplicate_to_canonical == {duplicate.id: original.id}
    assert result.canonical_traces == [original]
    assert result.duplicate_count == 1


# --- B5: provenance graph carries typed relation edges ------------------------------------


def test_provenance_graph_edge_carries_typed_relation_metadata() -> None:
    bundle = build_demo_bundle()
    original = bundle.traces[0]
    duplicate = original.model_copy(update={"id": f"{original.id}-copy"})
    duplicated_bundle = bundle.model_copy(update={"traces": [*bundle.traces, duplicate]})

    _, graph = KDAAPipeline().analyze(duplicated_bundle)
    assert graph.nodes[duplicate.id]["analysis_excluded"] is True
    assert graph.nodes[duplicate.id]["exclusion_reason"] == "exact_duplicate"
    edge_data = graph.get_edge_data(duplicate.id, original.id)
    assert edge_data is not None
    edge_attrs = next(iter(edge_data.values()))
    assert edge_attrs["relation"] == "exact_duplicate"
    assert edge_attrs["confidence"] == 1.0
    assert edge_attrs["rationale"]
    assert edge_attrs["detection_method"]


# --- B4: independent-support grouping -------------------------------------------------------


def test_independent_support_groups_merges_exact_duplicates() -> None:
    bundle = build_demo_bundle()
    original = bundle.traces[0]
    duplicate = original.model_copy(update={"id": f"{original.id}-copy"})
    result = deduplicate_traces([original, duplicate])

    groups = independent_support_groups(
        [t.id for t in [original, duplicate]], result.trace_relations
    )
    assert groups == [sorted([original.id, duplicate.id])]


def test_independent_support_groups_keeps_unrelated_traces_singleton() -> None:
    trace_ids = ["a", "b", "c"]
    groups = independent_support_groups(trace_ids, [])
    assert groups == [["a"], ["b"], ["c"]]


def test_independent_support_groups_does_not_merge_derivative_or_semantic_relations() -> None:
    trace_ids = ["a", "b", "c"]
    relations = [
        TraceRelation(
            id="r1", source_trace_id="a", target_trace_id="b",
            relation_type=TraceRelationType.SEMANTIC_NEAR_DUPLICATE,
        ),
        TraceRelation(
            id="r2", source_trace_id="b", target_trace_id="c",
            relation_type=TraceRelationType.DERIVATIVE,
        ),
    ]
    groups = independent_support_groups(trace_ids, relations)
    # Absence of exact/source-equivalence relations means every trace remains its own
    # group -- representable relations do not imply merged support until a later policy.
    assert groups == [["a"], ["b"], ["c"]]


def test_independent_support_groups_is_deterministic_regardless_of_relation_order() -> None:
    trace_ids = ["a", "b", "c", "d"]
    relation_ab = TraceRelation(
        id="r1", source_trace_id="a", target_trace_id="b",
        relation_type=TraceRelationType.EXACT_DUPLICATE,
    )
    relation_cd = TraceRelation(
        id="r2", source_trace_id="c", target_trace_id="d",
        relation_type=TraceRelationType.SOURCE_RECORD_EQUIVALENT,
    )
    forward = independent_support_groups(trace_ids, [relation_ab, relation_cd])
    backward = independent_support_groups(trace_ids, [relation_cd, relation_ab])
    assert forward == backward == [["a", "b"], ["c", "d"]]


# --- add_duplicate_trace_edges is retained, unchanged, for existing callers (WP2 B5) -----


def test_add_duplicate_trace_edges_backward_compatible_behavior_unchanged() -> None:
    bundle = build_demo_bundle()
    original = bundle.traces[0]
    duplicate = original.model_copy(update={"id": f"{original.id}-copy"})
    duplicated_bundle = bundle.model_copy(update={"traces": [*bundle.traces, duplicate]})

    graph = add_duplicate_trace_edges(
        build_evidence_graph(duplicated_bundle), {duplicate.id: original.id}
    )
    assert graph.nodes[duplicate.id]["analysis_excluded"] is True
    assert graph.nodes[duplicate.id]["exclusion_reason"] == "duplicate_trace"
    assert graph.has_edge(duplicate.id, original.id)


def test_add_trace_relation_edges_skips_relations_referencing_missing_graph_nodes() -> None:
    bundle = build_demo_bundle()
    graph = build_evidence_graph(bundle)
    relation = TraceRelation(
        id="r1",
        source_trace_id="not-in-graph",
        target_trace_id=bundle.traces[0].id,
        relation_type=TraceRelationType.EXACT_DUPLICATE,
    )
    result = add_trace_relation_edges(graph, [relation])
    assert not result.has_edge("not-in-graph", bundle.traces[0].id)
