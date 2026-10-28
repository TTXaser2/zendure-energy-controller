"""Read-only stage 1 telemetry adapter: cannot command Zendure."""
import unittest
from unittest.mock import patch
from tests.test_operation_priority import make_controller, fresh_state, OkShelly
from tests.test_battery_care_discharge_floor import care_cfg
from battery_care_pv_allocation import PvMemory


class CarePvShadowRuntimeTests(unittest.TestCase):
    def test_off_never_populates_or_changes_command_path(self):
        cfg=care_cfg(BATTERY_CARE_ENABLED=False)
        ctrl,state,mqtt,_=make_controller(cfg,state=fresh_state(39),shelly=OkShelly(0))
        ctrl._battery_care_pv_shadow_step(cfg)
        self.assertEqual(0,state.care_pv_shadow_candidate_w)
        self.assertEqual('CARE_NOT_ELIGIBLE',state.care_pv_shadow_reason)
        self.assertEqual([],mqtt.commands)

    def test_enabled_with_missing_observation_fails_closed_without_publish(self):
        cfg=care_cfg()
        ctrl,state,mqtt,_=make_controller(cfg,state=fresh_state(39),shelly=OkShelly(0))
        ctrl._battery_care_pv_shadow_step(cfg)
        self.assertEqual(0,state.care_pv_shadow_extra_w)
        self.assertNotEqual('CARE_PV_ATTACK',state.care_pv_shadow_reason)
        self.assertEqual([],mqtt.commands)

    def test_reentering_inactive_resets_old_shadow_state(self):
        cfg=care_cfg()
        ctrl,state,mqtt,_=make_controller(cfg,state=fresh_state(39),shelly=OkShelly(0))
        ctrl._care_pv_shadow_memory=PvMemory(extra_target_w=900)
        cfg['BATTERY_CARE_ENABLED']=False
        ctrl._battery_care_pv_shadow_step(cfg)
        self.assertEqual(PvMemory(),ctrl._care_pv_shadow_memory)
        self.assertEqual([],mqtt.commands)

    def test_integrated_primary_age_must_be_fresh_not_just_valid_flag(self):
        import time
        cfg=care_cfg(SECOND_BATTERY_INTEGRATION_ENABLED=True)
        ctrl,state,mqtt,_=make_controller(cfg,state=fresh_state(39),shelly=OkShelly(0))
        now=time.time()
        with state.lock:
            state.raw_grid_power=0
            state.grid_power_valid=True
            state.grid_power_sample_epoch=now
            state.actual_zendure_power_valid=True
            state.zendure_power_observation_direction='NEUTRAL'
            state.zendure_power_observation_signed_w=0
            state.zendure_power_observation_updated_epoch=now
            state.second_battery_data_valid=True
            state.last_sma_battery_update_epoch=now-100
            state.sma_battery_display_power=900
        with patch('primary_storage_source.primary_storage_integration_enabled',return_value=True), \
             patch.object(ctrl,'_fast_capture_command_ready',return_value=(True,'ready')):
            ctrl._battery_care_pv_shadow_step(cfg)
        self.assertEqual('SOURCE_STALE',state.care_pv_shadow_reason)
        self.assertEqual(0,state.care_pv_shadow_extra_w)
        self.assertEqual([],mqtt.commands)

    def test_auto_dispatch_remains_baseline_when_care_observations_missing(self):
        cfg=care_cfg(CROSS_CHARGE_ENABLED=False, REST_SURPLUS_HARVEST_ENABLED=False)
        ctrl,state,mqtt,_=make_controller(cfg,state=fresh_state(39),shelly=OkShelly(-500))
        ctrl.is_night_discharge_active=lambda _:False
        ctrl.run_once(cfg)
        self.assertGreater(state.last_input_power,0)
        self.assertEqual(0,state.care_pv_shadow_extra_w)
        self.assertNotEqual('CARE_PV_ATTACK',state.care_pv_shadow_reason)

if __name__=='__main__':unittest.main()
