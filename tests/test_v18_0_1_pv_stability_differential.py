"""Bounded care-on/off command-volume differential; synthetic inputs, not field effect."""
import unittest
from tests.test_battery_care_pv_live_dispatch import BatteryCarePvLiveDispatch
from tests.test_battery_care_discharge_floor import care_cfg

class CarePvDifferentialTests(unittest.TestCase):
    def test_no_independent_pv_observation_matches_care_disabled_commands(self):
        tester=BatteryCarePvLiveDispatch()
        cases=[]
        for enabled in (False,True):
            cfg=care_cfg(BATTERY_CARE_ENABLED=enabled, REST_SURPLUS_HARVEST_ENABLED=False,
                         HARVEST_FAST_CAPTURE_MODE='off')
            ctrl,cfg,state,mqtt=tester.make(cfg=cfg,soc=55,grid=0)
            tester.proposal(ctrl,state,0,0,'NO_DISTINCT_SOURCE')
            for grid in (0,12,-12,20,-20,8,-8)*5:
                ctrl.shelly.value=grid
                ctrl.run_once(cfg)
            cases.append((list(mqtt.commands),state.last_input_power,state.last_output_power))
        self.assertEqual(cases[0],cases[1], 'care-on must not add commands without PV evidence')

    def test_care_pv_shadow_flap_has_no_unsolicited_discharge(self):
        tester=BatteryCarePvLiveDispatch()
        ctrl,cfg,state,mqtt=tester.make(soc=39,grid=0)
        for candidate in (220,0,250,0,200,0):
            tester.proposal(ctrl,state,candidate,candidate)
            ctrl.run_once(cfg)
        self.assertFalse(any(c[0]=='output' and c[1]>0 for c in mqtt.commands))
        self.assertLessEqual(sum(c[0]=='ac' for c in mqtt.commands),3)

if __name__=='__main__':unittest.main()
