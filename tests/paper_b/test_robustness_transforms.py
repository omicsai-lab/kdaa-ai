"""Checkpoint B Section 10: R1/R2/R3 transforms actually perturb what they claim to."""

from __future__ import annotations

from kdaa.evaluation.paper_b.dev_cases import generate_development_set
from kdaa.evaluation.paper_b.robustness import (
    r1_exact_duplicate,
    r1_source_equivalent_duplicate,
    r2_substantial_irrelevant_evidence,
    r3_ontology_surface_shift,
)
from kdaa.ontology import Ontology


def test_r1_exact_duplicate_adds_one_trace_with_identical_content() -> None:
    case = next(iter(generate_development_set(1)))
    bundle = case.evidence_bundle
    perturbed = r1_exact_duplicate(bundle)
    assert len(perturbed.traces) == len(bundle.traces) + 1
    duplicate = perturbed.traces[-1]
    original = bundle.traces[0]
    assert duplicate.title == original.title
    assert duplicate.description == original.description
    assert duplicate.id != original.id


def test_r1_source_equivalent_duplicate_shares_a_strong_source_record_id() -> None:
    case = next(iter(generate_development_set(1)))
    bundle = case.evidence_bundle
    perturbed = r1_source_equivalent_duplicate(bundle)
    assert len(perturbed.traces) == len(bundle.traces) + 1
    assert perturbed.traces[0].source_record_id == perturbed.traces[-1].source_record_id
    assert perturbed.traces[0].title != perturbed.traces[-1].title


def test_r1_duplicates_are_actually_detected_as_relations_by_dedup() -> None:
    # Confirms R1's traces genuinely exercise WP2's dedup machinery, not just structurally
    # resemble a duplicate. Case index 1 (not 0): dev_cases.py itself plants a duplicate
    # on every 5th case (index % 5 == 0), so index 0 would already have one baseline
    # duplicate before R1 adds its own.
    from kdaa.ingestion import deduplicate_traces
    from kdaa.models import TraceRelationType

    case = generate_development_set(2)[1]
    baseline_duplicates = deduplicate_traces(case.evidence_bundle.traces).duplicate_count
    assert baseline_duplicates == 0, "expected a clean case with no pre-existing duplicate"

    exact = r1_exact_duplicate(case.evidence_bundle)
    result = deduplicate_traces(exact.traces)
    assert result.duplicate_count == 1
    assert result.trace_relations[0].relation_type == TraceRelationType.EXACT_DUPLICATE

    equivalent = r1_source_equivalent_duplicate(case.evidence_bundle)
    result2 = deduplicate_traces(equivalent.traces)
    assert result2.duplicate_count == 1
    assert result2.trace_relations[0].relation_type == TraceRelationType.SOURCE_RECORD_EQUIVALENT


def test_r2_adds_the_requested_number_of_noise_traces() -> None:
    case = next(iter(generate_development_set(1)))
    bundle = case.evidence_bundle
    perturbed = r2_substantial_irrelevant_evidence(bundle, n_noise=5)
    assert len(perturbed.traces) == len(bundle.traces) + 5


def test_r3_actually_changes_matchable_terms() -> None:
    """Regression test for the Checkpoint B defect: an earlier substitution list used
    phrases that never appeared in generated evidence text, silently making R3 a no-op.
    At least some development cases must show an actual text change."""
    cases = generate_development_set(15)
    changed = 0
    for case in cases:
        shifted = r3_ontology_surface_shift(case.evidence_bundle)
        if any(
            (a.title, a.description, tuple(a.keywords)) != (b.title, b.description, tuple(b.keywords))
            for a, b in zip(case.evidence_bundle.traces, shifted.traces, strict=True)
        ):
            changed += 1
    assert changed >= 5, f"expected several development cases to actually shift, got {changed}/15"


def test_r3_shift_affects_searchable_text_not_only_title_and_description() -> None:
    # The defect specifically involved keywords/topics leaking the original term through
    # EvidenceTrace.searchable_text even when title/description were shifted.
    cases = generate_development_set(15)
    for case in cases:
        shifted = r3_ontology_surface_shift(case.evidence_bundle)
        for original, mutated in zip(case.evidence_bundle.traces, shifted.traces, strict=True):
            if original.keywords:
                # If any substitution term appears in the original keywords, the shifted
                # trace's keywords must differ (not just title/description).
                original_kw_text = " ".join(original.keywords).lower()
                from kdaa.evaluation.paper_b.robustness import _SURFACE_SHIFT_SUBSTITUTIONS

                if any(term in original_kw_text for term in _SURFACE_SHIFT_SUBSTITUTIONS):
                    assert mutated.keywords != original.keywords


def test_r3_degrades_concept_recognition_on_some_cases() -> None:
    # End-to-end proof the fix actually matters: ontology.match finds fewer/different
    # concepts on at least some shifted cases than on the originals.
    ontology = Ontology.default()
    cases = generate_development_set(15)
    affected = 0
    for case in cases:
        shifted = r3_ontology_surface_shift(case.evidence_bundle)
        original_keys = {m.key for t in case.evidence_bundle.traces for m in ontology.match(t.searchable_text)}
        shifted_keys = {m.key for t in shifted.traces for m in ontology.match(t.searchable_text)}
        if original_keys != shifted_keys:
            affected += 1
    assert affected >= 5
