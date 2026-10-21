"""Next release S3: truthfulness of diagnostic applicability and V4 schema."""
from unittest.mock import patch

from measurement_v4 import build_v4_row
from measurement_v4_contract import (
    RC17_STANDARD_HEADER, STANDARD_HEADER, EXTENDED_HEADER,
    V17_S3_DIAGNOSTIC_FIELDS,
)
from tests.test_v12_11_2_rc17_harvest_zero_grid_target import Rc17HarvestZeroGridTargetTests


def _case(reason, *, sma=2500, zendure=500, export=0, **changes):
    harness=Rc17HarvestZeroGridTargetTests()
    controller,state,_,cfg,epoch=harness.make_case(
        reason,sma_w=sma,zendure_w=zendure,export_w=export,share=.5,**changes
    )
    with patch('controller_logic.time.time',return_value=epoch):
        result=controller._rest_surplus_charge_pressure_target(cfg,-export,int(state.last_input_power or 0))
    return result,state,cfg


def test_high_soc_share_calc_applied_without_claiming_physical_effect():
    result,state,_=_case('HIGH_SMA_SOC')
    assert result['target']==1500
    assert state.harvest_s3_applicability=='APPLIED'
    assert state.harvest_s3_override_reason==''
    assert state.harvest_target_selected_by=='STRATEGIC_SHARE'


def test_export_capture_priority_is_reported_as_override():
    result,state,_=_case('HIGH_SMA_SOC',sma=1000,zendure=1500,export=500)
    assert result['target']==2000
    assert state.harvest_s3_applicability=='OVERRIDDEN'
    assert state.harvest_s3_override_reason=='EXPORT_CAPTURE_PRIORITY'


def test_opted_in_sma_priority_suppresses_strategy_not_export_capture():
    result,state,_=_case('HIGH_SMA_SOC',HARVEST_SEASON_POLICY_ENABLED=True,HARVEST_SEASON_MODE='sma_priority')
    assert result['target']==500
    assert state.harvest_s3_applicability=='OVERRIDDEN'
    assert state.harvest_s3_override_reason=='SEASON_SMA_PRIORITY_EXPORT_CAPTURE_ONLY'


def test_ineligible_branches_are_not_claimed_applied():
    result,state,_=_case('SMA_FULL_OR_IDLE',sma=10,zendure=300,export=600)
    assert result['target']==900
    assert state.harvest_s3_applicability=='NOT_APPLICABLE'
    assert state.harvest_s3_override_reason=='OUTSIDE_HIGH_SOC_BRANCH'


def test_missing_independent_physical_reference_not_applied():
    result,state,_=_case('HIGH_SMA_SOC',reference_direction='UNKNOWN',reference_confidence='NONE')
    assert state.harvest_s3_applicability=='NOT_APPLICABLE'
    assert state.harvest_s3_override_reason


def test_v4_additive_s3_evidence_and_exact_legacy_rc_headers():
    assert len(STANDARD_HEADER)==278 and len(EXTENDED_HEADER)==281
    assert len(RC17_STANDARD_HEADER)==238
    assert V17_S3_DIAGNOSTIC_FIELDS.isdisjoint(RC17_STANDARD_HEADER)
    assert V17_S3_DIAGNOSTIC_FIELDS.issubset(STANDARD_HEADER)
    row=build_v4_row({}, {'epoch_s':1800000000.0,'cycle_id':1,
                            'harvest_season_requested':'calendar',
                            'harvest_season_effective':'sma_priority',
                            'harvest_profile_confirm_s':42,
                            'harvest_s3_applicability':'OVERRIDDEN',
                            'harvest_s3_override_reason':'EXPORT_CAPTURE_PRIORITY'})
    assert row['harvest_season_requested']=='calendar'
    assert row['harvest_profile_confirm_s']==42.0
    assert row['harvest_s3_override_reason']=='EXPORT_CAPTURE_PRIORITY'
