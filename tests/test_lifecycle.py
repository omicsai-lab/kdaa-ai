import itertools

import pytest

from kdaa.config import KDAAConfig
from kdaa.ingestion.synthetic import build_demo_bundle
from kdaa.lifecycle import CalibrationError, apply_calibration
from kdaa.models import AssetState, CalibrationAction, CalibrationRecord
from kdaa.pipeline import KDAAPipeline

# Mirrors kdaa.lifecycle._TRANSITION_MATRIX exactly (WP2 D1), duplicated here so this test
# file documents the frozen matrix independently of the implementation's internal constant.
_EXPECTED_TRANSITIONS: dict[AssetState, dict[CalibrationAction, AssetState]] = {
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
_TERMINAL_STATES = {AssetState.SPLIT, AssetState.REJECTED, AssetState.RETIRED}


@pytest.fixture
def run():
    result, _ = KDAAPipeline(KDAAConfig()).analyze(build_demo_bundle())
    return result


def _run_with_asset_in_state(run, state: AssetState):
    """Return (run, asset) with run.assets[0] forced into `state`, bypassing calibration
    (direct model_copy) so transition tests can start from any state, including ones that
    normal calibration alone could not reach in one step."""
    asset = run.assets[0].model_copy(update={"epistemic_state": state})
    other_assets = run.assets[1:]
    forced_run = run.model_copy(update={"assets": [asset, *other_assets]})
    return forced_run, asset


def _calibrate(run, asset_id: str, action: CalibrationAction, **kwargs):
    record = CalibrationRecord(
        id=f"cal-{action.value}-{asset_id}",
        run_id=run.manifest.run_id,
        asset_id=asset_id,
        action=action,
        notes="unit test",
        **kwargs,
    )
    return apply_calibration(run, [record])


def test_calibration_preserves_delta_and_can_confirm(run) -> None:
    asset = run.assets[0]
    updated = _calibrate(run, asset.id, CalibrationAction.CONFIRM)
    updated_asset = next(item for item in updated.assets if item.id == asset.id)
    assert updated_asset.epistemic_state.value == "confirmed"
    assert updated_asset.version == asset.version + 1
    assert len(updated.calibration_records) == 1
    original_asset = next(item for item in run.assets if item.id == asset.id)
    assert original_asset.epistemic_state.value != "confirmed"


# --- D5: full Cartesian product of AssetState x CalibrationAction -----------------------


@pytest.mark.parametrize(
    "state,action", list(itertools.product(AssetState, CalibrationAction))
)
def test_transition_matrix_cartesian_product(run, state: AssetState, action: CalibrationAction) -> None:
    forced_run, asset = _run_with_asset_in_state(run, state)
    kwargs = {"revised_claim": "A narrower, bounded claim."} if action == CalibrationAction.NARROW else {}

    if action == CalibrationAction.MERGE:
        with pytest.raises(CalibrationError):
            _calibrate(forced_run, asset.id, action, **kwargs)
        return

    if state in _TERMINAL_STATES:
        with pytest.raises(CalibrationError):
            _calibrate(forced_run, asset.id, action, **kwargs)
        return

    expected = _EXPECTED_TRANSITIONS[state].get(action)
    if expected is None:
        with pytest.raises(CalibrationError):
            _calibrate(forced_run, asset.id, action, **kwargs)
        return

    updated = _calibrate(forced_run, asset.id, action, **kwargs)
    updated_asset = next(item for item in updated.assets if item.id == asset.id)
    assert updated_asset.epistemic_state == expected


# --- D2: MERGE is always rejected, before any mutation -----------------------------------


def test_merge_is_rejected_for_every_starting_state(run) -> None:
    for state in AssetState:
        forced_run, asset = _run_with_asset_in_state(run, state)
        with pytest.raises(CalibrationError, match="MERGE"):
            _calibrate(forced_run, asset.id, CalibrationAction.MERGE)


# --- D3: atomic validation -----------------------------------------------------------------


def test_unknown_asset_raises_key_error(run) -> None:
    record = CalibrationRecord(
        id="cal-unknown",
        run_id=run.manifest.run_id,
        asset_id="does-not-exist",
        action=CalibrationAction.CONFIRM,
        notes="unit test",
    )
    with pytest.raises(KeyError):
        apply_calibration(run, [record])


def test_wrong_run_id_raises_value_error(run) -> None:
    record = CalibrationRecord(
        id="cal-wrong-run",
        run_id="some-other-run",
        asset_id=run.assets[0].id,
        action=CalibrationAction.CONFIRM,
        notes="unit test",
    )
    with pytest.raises(ValueError):
        apply_calibration(run, [record])


def test_atomic_rejection_of_mixed_validity_batch(run) -> None:
    valid_asset = run.assets[0]
    invalid_asset = run.assets[1]
    valid_record = CalibrationRecord(
        id="cal-valid",
        run_id=run.manifest.run_id,
        asset_id=valid_asset.id,
        action=CalibrationAction.CONFIRM,
        notes="unit test",
    )
    invalid_record = CalibrationRecord(
        id="cal-invalid",
        run_id=run.manifest.run_id,
        asset_id=invalid_asset.id,
        action=CalibrationAction.MERGE,
        notes="unit test",
    )
    with pytest.raises(CalibrationError):
        apply_calibration(run, [valid_record, invalid_record])
    # The valid record must not have been applied either: re-running only the valid
    # record from the same original run must still succeed and behave as a first
    # application (proves nothing was silently half-applied).
    updated = apply_calibration(run, [valid_record])
    updated_asset = next(item for item in updated.assets if item.id == valid_asset.id)
    assert updated_asset.epistemic_state == AssetState.CONFIRMED
    assert updated_asset.version == valid_asset.version + 1


def test_atomic_rejection_when_invalid_record_targets_same_asset_later(run) -> None:
    asset = run.assets[0]
    confirm = CalibrationRecord(
        id="cal-confirm",
        run_id=run.manifest.run_id,
        asset_id=asset.id,
        action=CalibrationAction.CONFIRM,
        notes="first",
    )
    # CONFIRM is illegal from CONFIRMED (no entry for that pair), so the second record in
    # this same-asset sequence is invalid.
    confirm_again = CalibrationRecord(
        id="cal-confirm-again",
        run_id=run.manifest.run_id,
        asset_id=asset.id,
        action=CalibrationAction.CONFIRM,
        notes="second",
    )
    with pytest.raises(CalibrationError):
        apply_calibration(run, [confirm, confirm_again])


# --- specific named scenarios from D5 -----------------------------------------------------


def test_repeated_narrowing(run) -> None:
    forced_run, asset = _run_with_asset_in_state(run, AssetState.NARROWED)
    updated = _calibrate(
        forced_run, asset.id, CalibrationAction.NARROW, revised_claim="Even narrower claim."
    )
    updated_asset = next(item for item in updated.assets if item.id == asset.id)
    assert updated_asset.epistemic_state == AssetState.NARROWED


def test_confirmation_of_a_narrowed_record(run) -> None:
    forced_run, asset = _run_with_asset_in_state(run, AssetState.NARROWED)
    updated = _calibrate(forced_run, asset.id, CalibrationAction.CONFIRM)
    updated_asset = next(item for item in updated.assets if item.id == asset.id)
    assert updated_asset.epistemic_state == AssetState.CONFIRMED


def test_rejection_of_confirmed_record(run) -> None:
    forced_run, asset = _run_with_asset_in_state(run, AssetState.CONFIRMED)
    updated = _calibrate(forced_run, asset.id, CalibrationAction.REJECT)
    updated_asset = next(item for item in updated.assets if item.id == asset.id)
    assert updated_asset.epistemic_state == AssetState.REJECTED


@pytest.mark.parametrize("state", sorted(_TERMINAL_STATES, key=lambda s: s.value))
def test_terminal_state_rejects_every_action(run, state: AssetState) -> None:
    forced_run, asset = _run_with_asset_in_state(run, state)
    for action in CalibrationAction:
        kwargs = (
            {"revised_claim": "x"} if action == CalibrationAction.NARROW else {}
        )
        with pytest.raises(CalibrationError):
            _calibrate(forced_run, asset.id, action, **kwargs)


@pytest.mark.parametrize(
    "state", [AssetState.HYPOTHESIS, AssetState.PROVISIONAL, AssetState.NARROWED]
)
def test_defer_preserves_current_source_state(run, state: AssetState) -> None:
    forced_run, asset = _run_with_asset_in_state(run, state)
    updated = _calibrate(forced_run, asset.id, CalibrationAction.DEFER)
    updated_asset = next(item for item in updated.assets if item.id == asset.id)
    assert updated_asset.epistemic_state == state
    assert updated_asset.human_calibration_required is True


def test_defer_is_illegal_from_confirmed(run) -> None:
    forced_run, asset = _run_with_asset_in_state(run, AssetState.CONFIRMED)
    with pytest.raises(CalibrationError):
        _calibrate(forced_run, asset.id, CalibrationAction.DEFER)


def test_narrow_requires_non_empty_revised_claim(run) -> None:
    asset = run.assets[0]
    with pytest.raises(CalibrationError):
        _calibrate(run, asset.id, CalibrationAction.NARROW)
    with pytest.raises(CalibrationError):
        _calibrate(run, asset.id, CalibrationAction.NARROW, revised_claim="   ")


def test_calibration_can_revise_categories(run) -> None:
    from kdaa.models import AssetCategory

    asset = run.assets[0]
    updated = _calibrate(
        run, asset.id, CalibrationAction.NARROW,
        revised_claim="A narrower claim.",
        revised_categories=[AssetCategory.CODIFIED],
    )
    updated_asset = next(item for item in updated.assets if item.id == asset.id)
    assert updated_asset.categories == [AssetCategory.CODIFIED]


def test_split_preserves_parent_as_split_state(run) -> None:
    asset = run.assets[0]
    updated = _calibrate(run, asset.id, CalibrationAction.SPLIT)
    updated_asset = next(item for item in updated.assets if item.id == asset.id)
    assert updated_asset.epistemic_state == AssetState.SPLIT
    assert updated_asset.human_calibration_required is True


def test_human_calibration_required_flags_match_spec(run) -> None:
    expectations = {
        CalibrationAction.CONFIRM: False,
        CalibrationAction.NARROW: False,
        CalibrationAction.REJECT: False,
        CalibrationAction.DEFER: True,
        CalibrationAction.SPLIT: True,
    }
    for action, expected_flag in expectations.items():
        forced_run, asset = _run_with_asset_in_state(run, AssetState.HYPOTHESIS)
        kwargs = {"revised_claim": "x"} if action == CalibrationAction.NARROW else {}
        updated = _calibrate(forced_run, asset.id, action, **kwargs)
        updated_asset = next(item for item in updated.assets if item.id == asset.id)
        assert updated_asset.human_calibration_required is expected_flag, action


# --- no non-calibration route to CONFIRMED ------------------------------------------------


def test_pipeline_never_produces_confirmed_assets_outside_calibration(run) -> None:
    assert all(asset.epistemic_state != AssetState.CONFIRMED for asset in run.assets)


def test_no_non_calibration_module_references_confirmed_state() -> None:
    # Structural guarantee: the modules that actually produce AssetRecord instances outside
    # calibration (discovery and assessment) never reference AssetState.CONFIRMED at all, so
    # there is no code path in them that could construct one.
    import ast
    import inspect

    import kdaa.assessment.credibility as credibility_module
    import kdaa.discovery.llm as llm_module
    import kdaa.discovery.rules as rules_module

    for module in (rules_module, llm_module, credibility_module):
        tree = ast.parse(inspect.getsource(module))
        confirmed_references = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and node.attr == "CONFIRMED"
            and isinstance(node.value, ast.Name)
            and node.value.id == "AssetState"
        ]
        assert confirmed_references == [], f"{module.__name__} references AssetState.CONFIRMED"
