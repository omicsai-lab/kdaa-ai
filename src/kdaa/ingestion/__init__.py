"""Input connectors and normalization helpers."""

from .dedup import (
    TraceDeduplicationResult,
    deduplicate_traces,
    independent_support_groups,
    trace_identity_key,
)
from .github import GitHubConnector
from .local import load_bundle, load_bundle_from_dict, merge_bundles, parse_cv_document
from .openalex import OpenAlexConnector
from .synthetic import (
    SyntheticBenchmarkGenerator,
    build_demo_bundle,
    build_demo_scenario,
    build_lab_demo_bundle,
    build_team_demo_bundle,
)

__all__ = [
    "GitHubConnector",
    "TraceDeduplicationResult",
    "OpenAlexConnector",
    "SyntheticBenchmarkGenerator",
    "build_demo_bundle",
    "build_demo_scenario",
    "build_lab_demo_bundle",
    "build_team_demo_bundle",
    "deduplicate_traces",
    "independent_support_groups",
    "load_bundle",
    "load_bundle_from_dict",
    "merge_bundles",
    "parse_cv_document",
    "trace_identity_key",
]
