"""WP2 final correction 2: no unsupported contribution overclaim for unknown-role
software/repository evidence.
"""

from __future__ import annotations

from kdaa.config import KDAAConfig
from kdaa.discovery.features import extract_trace_features
from kdaa.discovery.rules import discover_asset_hypotheses
from kdaa.models import (
    ContributionRole,
    EvidenceTrace,
    FocalUnit,
    SourceKind,
    TraceType,
    UnitBundle,
    UnitType,
)
from kdaa.ontology import Ontology

_OVERCLAIM_PHRASE = "control or materially contribute"


def _artifact_asset_for(trace: EvidenceTrace):
    unit = FocalUnit(id="u1", name="Test Developer", unit_type=UnitType.RESEARCHER)
    bundle = UnitBundle(unit=unit, traces=[trace])
    ontology = Ontology.default()
    config = KDAAConfig()
    features = extract_trace_features(bundle.traces, ontology)
    assets = discover_asset_hypotheses(bundle, features, ontology, config.discovery)
    artifact_assets = [asset for asset in assets if asset.id.startswith("asset-artifact")]
    assert len(artifact_assets) == 1, "expected exactly one single-artifact hypothesis"
    return artifact_assets[0]


def test_unknown_role_github_style_software_evidence_does_not_overclaim_contribution() -> None:
    trace = EvidenceTrace(
        id="trace-github-1",
        unit_id="u1",
        trace_type=TraceType.SOFTWARE,
        title="omics-agent",
        source_kind=SourceKind.GITHUB,
        source_uri="https://github.com/example/omics-agent",
        source_record_id="12345",
        # Matches kdaa.ingestion.github's conservative default for owned/forked repos.
        contribution_role=ContributionRole.UNKNOWN,
    )
    asset = _artifact_asset_for(trace)
    assert _OVERCLAIM_PHRASE not in asset.bounded_claim
    assert "independent contribution has not been established" in asset.bounded_claim
    assert "publicly associated with the focal unit" in asset.bounded_claim


def test_unknown_role_repository_evidence_does_not_overclaim_for_other_artifact_types() -> None:
    # Same defect, same shared claim-generation code path, for a non-software codified
    # artifact (dataset) with unknown role -- confirms the fix is not a software-only
    # special case bolted onto an otherwise-shared template.
    trace = EvidenceTrace(
        id="trace-dataset-1",
        unit_id="u1",
        trace_type=TraceType.DATASET,
        title="genomics-benchmark-set",
        source_kind=SourceKind.MANUAL,
        contribution_role=ContributionRole.UNKNOWN,
    )
    asset = _artifact_asset_for(trace)
    assert _OVERCLAIM_PHRASE not in asset.bounded_claim
    assert "independent contribution has not been established" in asset.bounded_claim


def test_known_contribution_role_still_uses_stronger_claim_wording() -> None:
    # Explicit independent contribution evidence (a known role) is the one case where the
    # stronger wording remains appropriate.
    trace = EvidenceTrace(
        id="trace-github-2",
        unit_id="u1",
        trace_type=TraceType.SOFTWARE,
        title="known-lead-repo",
        source_kind=SourceKind.MANUAL,
        contribution_role=ContributionRole.LEAD,
    )
    asset = _artifact_asset_for(trace)
    assert _OVERCLAIM_PHRASE in asset.bounded_claim


def test_neutral_claim_still_names_the_artifact_and_trace_type() -> None:
    trace = EvidenceTrace(
        id="trace-github-3",
        unit_id="u1",
        trace_type=TraceType.SOFTWARE,
        title="my-repo",
        source_kind=SourceKind.GITHUB,
        contribution_role=ContributionRole.UNKNOWN,
    )
    asset = _artifact_asset_for(trace)
    assert "my-repo" in asset.bounded_claim
    assert "software repository" in asset.bounded_claim
