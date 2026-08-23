from kdaa.evaluation.paper_b.dev_cases import generate_development_case, generate_development_set
from kdaa.evaluation.paper_b.opportunity_catalog import DEV_OPPORTUNITY_CATALOG
from kdaa.models import UnitBundle
from kdaa.ontology import Ontology


def test_development_set_minimum_size() -> None:
    cases = generate_development_set(60)
    assert len(cases) == 60


def test_case_manifest_marks_development_and_not_challenge() -> None:
    case = generate_development_case(0)
    assert case.manifest.development_case is True
    assert case.manifest.is_challenge_case is False


def test_opportunity_catalog_has_exactly_ten_candidates() -> None:
    assert len(DEV_OPPORTUNITY_CATALOG) == 10
    ids = [candidate.opportunity_id for candidate in DEV_OPPORTUNITY_CATALOG]
    assert len(set(ids)) == 10


def test_every_case_shares_the_same_ten_opportunity_ids() -> None:
    cases = generate_development_set(10)
    catalog_ids = {c.opportunity_id for c in DEV_OPPORTUNITY_CATALOG}
    for case in cases:
        assert len(case.opportunity_catalog) == 10
        assert {c.opportunity_id for c in case.opportunity_catalog} == catalog_ids
        true_ids = {r.opportunity_id for r in case.truth.opportunity_relevance}
        assert true_ids == catalog_ids


def test_truth_opportunity_relevance_grades_are_bounded() -> None:
    cases = generate_development_set(20)
    for case in cases:
        for relevance in case.truth.opportunity_relevance:
            assert 0 <= relevance.relevance_grade <= 3


def test_development_set_covers_unit_types_densities_and_domains() -> None:
    cases = generate_development_set(60)
    unit_types = {case.manifest.unit_type.value for case in cases}
    densities = {case.manifest.evidence_density.value for case in cases}
    domains = {case.manifest.domain_breadth.value for case in cases}
    ownerships = {case.truth.asset_concepts[0].ownership_state.value for case in cases if case.truth.asset_concepts}
    assert unit_types == {"individual_researcher", "team", "laboratory"}
    assert densities == {"sparse", "dense"}
    assert domains == {"single_domain", "interdisciplinary"}
    assert ownerships == {"focal_unit", "shared", "organizational", "external", "unresolved"}


def _bundle_content(bundle) -> dict:
    # EvidenceTrace.observed_at defaults to a wall-clock timestamp (default_factory=
    # utc_now), the same kind of volatile execution metadata WP1/WP2 already exclude
    # from canonical scientific payloads elsewhere -- it is not part of a case's actual
    # generated content, so it is excluded here rather than asserted identical.
    dumped = bundle.model_dump()
    for trace in dumped["traces"]:
        trace.pop("observed_at", None)
    return dumped


def test_case_generation_is_deterministic() -> None:
    ontology = Ontology.default()
    case_a = generate_development_case(5, ontology=ontology)
    case_b = generate_development_case(5, ontology=ontology)
    assert _bundle_content(case_a.evidence_bundle) == _bundle_content(case_b.evidence_bundle)
    assert case_a.truth.model_dump() == case_b.truth.model_dump()


# --- evidence/truth separation -------------------------------------------------------------


def test_evidence_bundle_is_a_plain_production_unit_bundle_with_no_truth_fields() -> None:
    case = generate_development_case(0)
    assert isinstance(case.evidence_bundle, UnitBundle)
    # UnitBundle is extra="forbid" -- there is no field it could carry truth in beyond
    # the ones already reviewed for leakage (metadata is checked separately).
    assert case.evidence_bundle.metadata == {}


def test_true_concept_ids_do_not_appear_as_unit_bundle_metadata_keys() -> None:
    case = generate_development_case(0)
    true_ids = {concept.concept_id for concept in case.truth.asset_concepts}
    assert not (true_ids & set(case.evidence_bundle.metadata))


def test_evidence_bundle_traces_carry_no_ownership_or_relevance_fields() -> None:
    # EvidenceTrace has no ownership_state or relevance_grade field at all (checked via
    # model_fields, not just "did generation forget to set one") -- the production
    # schema itself is what makes this impossible, not generator discipline alone.
    from kdaa.models import EvidenceTrace

    assert "ownership_state" not in EvidenceTrace.model_fields
    assert "relevance_grade" not in EvidenceTrace.model_fields
