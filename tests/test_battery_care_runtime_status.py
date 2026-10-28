"""CP10: Care card boundary must be grounded in real ControllerState, not settings."""
import time
import unittest
from tests.test_battery_care_discharge_floor import care_cfg
from tests.test_operation_priority import make_controller, fresh_state, OkShelly


class BatteryCareRuntimeStatusTests(unittest.TestCase):
    def make(self, cfg=None, soc=39, grid=0):
        cfg=cfg or care_cfg()
        ctrl,state,mqtt,shelly=make_controller(cfg,state=fresh_state(soc),shelly=OkShelly(grid))
        ctrl.is_night_discharge_active=lambda _: False
        return ctrl,cfg,state

    def test_current_auto_reports_effective_reserve(self):
        ctrl,cfg,state=self.make()
        ctrl.run_once(cfg)
        snap=state.snapshot()
        self.assertTrue(snap['care_policy_valid'])
        self.assertTrue(snap['care_in_season'])
        self.assertEqual(40,snap['care_effective_discharge_floor_soc'])

    def test_higher_legacy_min_is_not_reduced_in_status(self):
        ctrl,cfg,state=self.make(cfg=care_cfg(MIN_SOC_PERCENT=50))
        ctrl.run_once(cfg)
        self.assertEqual(50,state.snapshot()['care_effective_discharge_floor_soc'])

    def test_no_unproven_limit_when_disabled_or_outside_season(self):
        cases=(care_cfg(BATTERY_CARE_ENABLED=False),
               care_cfg(BATTERY_CARE_SEASON_START_MM_DD='01-01',
                        BATTERY_CARE_SEASON_END_MM_DD='01-01'))
        for cfg in cases:
            with self.subTest(cfg=cfg):
                ctrl,cfg,state=self.make(cfg=cfg)
                ctrl.run_once(cfg)
                snap=state.snapshot()
                self.assertIsNone(snap['care_effective_discharge_floor_soc'])
                self.assertFalse(snap['care_policy_valid'])
                self.assertFalse(snap['care_in_season'])

    def test_manual_stop_drops_previously_effective_status(self):
        ctrl,cfg,state=self.make()
        ctrl.run_once(cfg)
        self.assertTrue(state.snapshot()['care_in_season'])
        cfg['MANUAL_MODE']='STOP_HOLD'
        ctrl.run_once(cfg)
        snap=state.snapshot()
        self.assertFalse(snap['care_policy_valid'])
        self.assertIsNone(snap['care_effective_discharge_floor_soc'])

    def test_stale_soc_invalidates_status_in_same_cycle(self):
        ctrl,cfg,state=self.make()
        ctrl.run_once(cfg)
        with state.lock:
            state.last_soc_update_epoch=time.time()-99999
        ctrl.run_once(cfg)
        self.assertFalse(state.snapshot()['care_in_season'])
        self.assertIsNone(state.snapshot()['care_effective_discharge_floor_soc'])

    def test_safe_state_invalidates_previously_live_care_status(self):
        ctrl,cfg,state=self.make()
        ctrl.run_once(cfg)
        self.assertTrue(state.snapshot()['care_in_season'])
        ctrl.safe_state('synthetic device-state failure')
        self.assertFalse(state.snapshot()['care_in_season'])
        self.assertIsNone(state.snapshot()['care_effective_discharge_floor_soc'])

    def test_fixed_manual_discharge_never_claims_care_protection(self):
        ctrl,cfg,state=self.make(cfg=care_cfg(MANUAL_MODE='FIXED_DISCHARGE'))
        ctrl.run_once(cfg)
        self.assertEqual('MANUAL_FIXED_DISCHARGE',state.current_mode)
        self.assertFalse(state.snapshot()['care_policy_valid'])


if __name__=='__main__':
    unittest.main()
