"""Optional human-calibration and outcome-update operations.

Calibration transitions are validated against an explicit state-transition matrix
(WP2 requirement D). No non-calibration code path in this package sets
`AssetState.CONFIRMED`; discovery and assessment only ever produce `HYPOTHESIS` or
`PROVISIONAL` (see `kdaa.discovery.rules`, `kdaa.discovery.llm`,
`kdaa.assessment.credibility`), so a CONFIRMED asset can only be produced through
`apply_calibration`'s CONFIRM action below.
"""

from __future__ import annotations

from collections import defaultdict

from kdaa.models import (
    AnalysisRun,
    AssetState,
    CalibrationAction,
    CalibrationRecord,
    OutcomeRecord,
)

# Explicit transition matrix (WP2 D1). A state with no entry (SPLIT, REJECTED, RETIRED)
# is terminal for calibration: no action is legal from it.
_TRANSITION_MATRIX: dict[AssetState, dict[CalibrationAction, AssetState]] = {
    AssetState.HYPOTHESIS: {
        CalibrationAction.CONFIRM: AssetState.CONFIRMED,
        CalibrationAction.NARROW: AssetState.NARROWED,
        CalibrationAction.SPLIT: AssetState.SPLIT,
        CalibrationAction.REJECT: AssetState.REJECTED,
        CalibrationAction.DEFER: AssetState.HYPOTHESIS,
    },
    AssetState.PROVISIONAL: {
        CalibrationAction.CONFIRM: AssetState.CONFIRMED,
        CalibrationAction.NARROW: AssetState.NARROWED,
        CalibrationAction.SPLIT: AssetState.SPLIT,
        CalibrationAction.REJECT: AssetState.REJECTED,
        CalibrationAction.DEFER: AssetState.PROVISIONAL,
    },
    AssetState.CONFIRMED: {
        CalibrationAction.NARROW: AssetState.NARROWED,
        CalibrationAction.SPLIT: AssetState.SPLIT,
        CalibrationAction.REJECT: AssetState.REJECTED,
    },
    AssetState.NARROWED: {
        CalibrationAction.CONFIRM: AssetState.CONFIRMED,
        CalibrationAction.NARROW: AssetState.NARROWED,
        CalibrationAction.SPLIT: AssetState.SPLIT,
        CalibrationAction.REJECT: AssetState.REJECTED,
        CalibrationAction.DEFER: AssetState.NARROWED,
    },
}

# Terminal for calibration in WP2: no calibration action may be applied to an asset in
# one of these states. Child-record creation for SPLIT remains outside WP2.
_TERMINAL_STATES = frozenset({AssetState.SPLIT, AssetState.REJECTED, AssetState.RETIRED})

# WP2 D4: human_calibration_required after each action. DEFER and SPLIT keep the record
# flagged for further human attention; CONFIRM/NARROW/REJECT resolve it. MERGE never
# reaches this table because it is always rejected before any state is applied.
_HUMAN_CALIBRATION_REQUIRED_AFTER: dict[CalibrationAction, bool] = {
    CalibrationAction.CONFIRM: False,
    CalibrationAction.NARROW: False,
    CalibrationAction.REJECT: False,
    CalibrationAction.DEFER: True,
    CalibrationAction.SPLIT: True,
}


class CalibrationError(ValueError):
    """An illegal calibration request: bad transition, unsupported action, or missing
    required field. Subclasses `ValueError` so existing `except (ValueError, KeyError)`
    boundaries (e.g. `kdaa.api`'s `/v1/calibrate`) keep working without modification.
    """


def _validate_and_plan(
    run: AnalysisRun, records: list[CalibrationRecord]
) -> dict[str, list[tuple[CalibrationRecord, AssetState]]]:
    """Validate every record in the batch against the transition matrix without mutating
    anything, and return the planned (record, next_state) sequence per asset. Raises on
    the first invalid record found; nothing in the batch is ever partially applied
    (WP2 D3): this function either returns a fully valid plan for every record, or raises.
    """
    asset_by_id = {asset.id: asset for asset in run.assets}

    by_asset: dict[str, list[CalibrationRecord]] = defaultdict(list)
    for record in records:
        if record.run_id != run.manifest.run_id:
            raise ValueError(f"Calibration {record.id} belongs to another run")
        by_asset[record.asset_id].append(record)

    missing = set(by_asset) - set(asset_by_id)
    if missing:
        raise KeyError(f"Unknown asset IDs in calibration records: {sorted(missing)}")

    planned: dict[str, list[tuple[CalibrationRecord, AssetState]]] = {}
    for asset_id, asset_records in by_asset.items():
        current_state = asset_by_id[asset_id].epistemic_state
        plan: list[tuple[CalibrationRecord, AssetState]] = []
        for record in asset_records:
            if record.action == CalibrationAction.MERGE:
                raise CalibrationError(
                    f"Calibration {record.id}: MERGE is unsupported -- there is no "
                    "target-asset/child-record schema defined for a valid merge yet. "
                    "Reject explicitly rather than fabricating merge semantics."
                )
            if current_state in _TERMINAL_STATES:
                raise CalibrationError(
                    f"Calibration {record.id}: {current_state.value} is terminal for "
                    "calibration; no further action is permitted."
                )
            allowed = _TRANSITION_MATRIX.get(current_state, {})
            if record.action not in allowed:
                raise CalibrationError(
                    f"Calibration {record.id}: {record.action.value} is not a legal "
                    f"transition from {current_state.value}"
                )
            if record.action == CalibrationAction.NARROW and not (record.revised_claim or "").strip():
                raise CalibrationError(
                    f"Calibration {record.id}: NARROW requires a non-empty revised_claim"
                )
            next_state = allowed[record.action]
            plan.append((record, next_state))
            current_state = next_state
        planned[asset_id] = plan

    return planned


def apply_calibration(
    run: AnalysisRun,
    records: list[CalibrationRecord],
) -> AnalysisRun:
    """Apply versioned calibration records without overwriting the AI-only map.

    The full batch is validated against the explicit transition matrix before any asset
    is updated (WP2 D3): a single invalid record anywhere in the batch -- an unknown
    asset, a wrong run ID, an unsupported MERGE, an illegal transition, a terminal-state
    violation, or a NARROW missing `revised_claim` -- prevents every record in the batch
    from being applied, including otherwise-valid records for other assets.
    """

    planned_updates = _validate_and_plan(run, records)

    updated_assets = []
    for asset in run.assets:
        current = asset
        for record, next_state in planned_updates.get(asset.id, []):
            update: dict = {
                "version": current.version + 1,
                "epistemic_state": next_state,
                "human_calibration_required": _HUMAN_CALIBRATION_REQUIRED_AFTER[record.action],
                "notes": [*current.notes, f"Calibration {record.action.value}: {record.notes}"],
            }
            if record.revised_claim:
                update["bounded_claim"] = record.revised_claim
            if record.revised_categories:
                update["categories"] = record.revised_categories
            current = current.model_copy(update=update)
        updated_assets.append(current)

    return run.model_copy(
        update={
            "assets": updated_assets,
            "calibration_records": [*run.calibration_records, *records],
        }
    )


def append_outcomes(run: AnalysisRun, outcomes: list[OutcomeRecord]) -> AnalysisRun:
    valid_opportunities = {opportunity.id for opportunity in run.opportunities}
    for outcome in outcomes:
        if outcome.run_id != run.manifest.run_id:
            raise ValueError(f"Outcome {outcome.id} belongs to another run")
        if outcome.opportunity_id not in valid_opportunities:
            raise KeyError(f"Unknown opportunity: {outcome.opportunity_id}")
    return run.model_copy(update={"outcome_records": [*run.outcome_records, *outcomes]})
