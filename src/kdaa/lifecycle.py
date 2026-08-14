"""Optional human-calibration and outcome-update operations."""

from __future__ import annotations

from collections import defaultdict

from kdaa.models import (
    AnalysisRun,
    AssetState,
    CalibrationAction,
    CalibrationRecord,
    OutcomeRecord,
)


def apply_calibration(
    run: AnalysisRun,
    records: list[CalibrationRecord],
) -> AnalysisRun:
    """Apply versioned calibration records without overwriting the AI-only map."""

    by_asset: dict[str, list[CalibrationRecord]] = defaultdict(list)
    for record in records:
        if record.run_id != run.manifest.run_id:
            raise ValueError(f"Calibration {record.id} belongs to another run")
        by_asset[record.asset_id].append(record)

    updated_assets = []
    for asset in run.assets:
        current = asset
        for record in by_asset.get(asset.id, []):
            update: dict = {
                "version": current.version + 1,
                "human_calibration_required": record.action == CalibrationAction.DEFER,
                "notes": [*current.notes, f"Calibration {record.action.value}: {record.notes}"],
            }
            if record.revised_claim:
                update["bounded_claim"] = record.revised_claim
            if record.revised_categories:
                update["categories"] = record.revised_categories
            if record.action == CalibrationAction.CONFIRM:
                update["epistemic_state"] = AssetState.CONFIRMED
                update["human_calibration_required"] = False
            elif record.action == CalibrationAction.NARROW:
                update["epistemic_state"] = AssetState.NARROWED
                update["human_calibration_required"] = False
            elif record.action == CalibrationAction.SPLIT:
                update["epistemic_state"] = AssetState.SPLIT
            elif record.action == CalibrationAction.REJECT:
                update["epistemic_state"] = AssetState.REJECTED
                update["human_calibration_required"] = False
            elif record.action == CalibrationAction.DEFER:
                update["epistemic_state"] = AssetState.HYPOTHESIS
            current = current.model_copy(update=update)
        updated_assets.append(current)

    missing = set(by_asset) - {asset.id for asset in run.assets}
    if missing:
        raise KeyError(f"Unknown asset IDs in calibration records: {sorted(missing)}")

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
