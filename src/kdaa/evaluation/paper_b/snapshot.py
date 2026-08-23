"""Build the immutable, fairness-locked ``InputSnapshot`` every comparator receives.

Deriving the snapshot from the same ``UnitBundle`` in the bundle's own trace order (not a
re-sorted or re-filtered order) is what guarantees C0-S and C3 see identical evidence
content and order (Freeze Section 12: fair-comparison rules). Building the snapshot here,
once, and handing the *same* object to both adapters is what makes that guarantee
structural rather than a convention each adapter has to separately honor.
"""

from __future__ import annotations

from kdaa.models import EvidenceTrace, UnitBundle

from .dev_cases import DevelopmentCase
from .schemas import EvidenceSnapshotTrace, InputSnapshot, OpportunityCandidate


def _normalized_text(trace: EvidenceTrace) -> str:
    return trace.searchable_text


def build_input_snapshot(
    case_id: str,
    bundle: UnitBundle,
    opportunity_catalog: tuple[OpportunityCandidate, ...],
) -> InputSnapshot:
    """Build an ``InputSnapshot`` from ``bundle.traces`` in their existing order.

    Only fields already safe for inference are copied across (trace_id, trace type,
    normalized searchable text, sensitivity flag, and order) -- ownership, contribution
    role, and other trace fields are deliberately not included, since they are not part
    of the fairness-locked evaluation input every comparator receives identically.
    """
    traces = tuple(
        EvidenceSnapshotTrace(
            trace_id=trace.id,
            order_index=index,
            trace_type=trace.trace_type.value,
            normalized_text=_normalized_text(trace),
            sensitive=trace.sensitive,
        )
        for index, trace in enumerate(bundle.traces)
    )
    return InputSnapshot(case_id=case_id, traces=traces, opportunity_catalog=opportunity_catalog)


def build_snapshot_for_case(case: DevelopmentCase) -> InputSnapshot:
    return build_input_snapshot(case.manifest.case_id, case.evidence_bundle, case.opportunity_catalog)
