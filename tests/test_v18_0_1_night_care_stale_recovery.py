"""V18.0.1: evidence-gated recovery from historical night-SOC SAFE_STATE."""
import time
import unittest
from tests.test_battery_care_discharge_floor import care_cfg
from tests.test_operation_priority import make_controller, fresh_state, OkShelly


class NightCareStaleRecoveryTests(unittest.TestCase):
    def prepare(self, *, readback=True, neutral=True, soc=39, power_valid=True):
        cfg = care_cfg(NIGHT_DISCHARGE_ENABLED=True,
                       NIGHT_DISCHARGE_STOP_SOC_PERCENT=35)
        state = fresh_state(soc)
        ctrl, state, mqtt, _ = make_controller(cfg, state=state, shelly=OkShelly(400))
        ctrl.is_night_discharge_active = lambda _cfg: True
        with state.lock:
            state.current_mode = 'SAFE_STATE'
            state.control_reason = 'Nachtmodus blockiert: Zendure SOC fehlt oder ist veraltet'
            state.last_output_power = 0
            state.last_input_power = 0
            state.command_desired_signed_target_w = 0
            state.command_readback_matches_desired = readback
            state.command_neutralization_active = not neutral
            state.actual_zendure_power_valid = power_valid
            state.actual_zendure_system_signed_power = 0
        return ctrl,cfg,state,mqtt

    def test_fresh_soc_and_confirmed_neutral_recover_without_publish(self):
        ctrl,cfg,state,mqtt = self.prepare()
        ctrl.run_once(cfg)
        self.assertEqual(state.current_mode, 'HOLD')
        self.assertIn('BATTERY_CARE_RESERVE', state.active_limiters)
        self.assertEqual(state.last_output_power, 0)
        self.assertEqual(mqtt.commands, [])
        self.assertNotIn('veraltet', state.control_reason)
        ctrl.run_once(cfg)
        self.assertEqual(mqtt.commands, [])

    def test_missing_confirmation_fails_closed(self):
        for kwargs in ({'readback':False},{'neutral':False},{'power_valid':False}):
            with self.subTest(kwargs=kwargs):
                ctrl,cfg,state,mqtt=self.prepare(**kwargs)
                ctrl.run_once(cfg)
                self.assertEqual(state.current_mode, 'SAFE_STATE')
                self.assertEqual(mqtt.commands, [])

    def test_soc_stale_keeps_safe_state(self):
        ctrl,cfg,state,_=self.prepare()
        with state.lock:
            state.last_soc_update_epoch = time.time() - 150
        ctrl.run_once(cfg)
        self.assertEqual(state.current_mode, 'SAFE_STATE')

    def test_unrelated_safe_state_cannot_be_silently_recovered(self):
        ctrl,cfg,state,_=self.prepare()
        with state.lock:
            state.control_reason = 'Fehlender Commandpfad'
        ctrl.run_once(cfg)
        self.assertEqual(state.current_mode, 'SAFE_STATE')

    def test_above_care_floor_falls_through_normal_rule(self):
        ctrl,cfg,state,_=self.prepare(soc=41)
        ctrl.run_once(cfg)
        self.assertNotEqual(state.control_reason, 'Battery Care: Schutzreserve erreicht; Nachtentladung bleibt gesperrt')


if __name__=='__main__':
    unittest.main()
