import tempfile
import unittest
from unittest.mock import patch

from config_manager import DEFAULT_CONFIG
from controller_logic import ZendureController
from state import ControllerState
from web_ui import build_nav_bar, build_soc_day_payload


class DummyMqtt:
    def connect(self, cfg):
        pass
    def start(self):
        pass
    def stop(self):
        pass
    def refresh_subscriptions(self, cfg):
        pass


class DummyShelly:
    def __init__(self, value):
        self.value = value
    def read_grid_power(self, cfg):
        return self.value


class DummySma:
    def ensure_started(self, cfg):
        pass
    def stop(self):
        pass
    def snapshot(self):
        class Snap:
            enabled=False; running=False; age_s=None
        return Snap()
    def read_grid_power(self, cfg):
        return 0.0


class TestRC8Hotfix(unittest.TestCase):
    def test_navbar_keeps_analysis_link_and_uses_browser_host_script_target(self):
        html = build_nav_bar(dict(DEFAULT_CONFIG, REPLAY_WEB_PORT=8090))
        self.assertIn('Analyse-Service', html)
        self.assertIn('analysis-service-link', html)
        self.assertIn('data-replay-port="8090"', html)
        self.assertNotIn('http://127.0.0.1:8090', html)

    def test_soc_day_payload_advertises_full_day_axis_and_uses_cache(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = dict(DEFAULT_CONFIG)
            cfg['MEASUREMENT_LOG_DIR'] = td
            cfg['SOC_DAY_GRAPH_BOOTSTRAP_CACHE_SECONDS'] = 300
            state = ControllerState()
            state.battery_soc = 61
            state.soc_valid = True
            payload1 = build_soc_day_payload(cfg, state.snapshot())
            self.assertEqual(0, payload1['axis_minute_start'])
            self.assertEqual(1440, payload1['axis_minute_end'])
            self.assertGreaterEqual(len(payload1['points']), 1)
            state.battery_soc = 62
            with patch('web_ui._graph_points_from_measurements', side_effect=AssertionError('must use cache')):
                payload2 = build_soc_day_payload(cfg, state.snapshot())
            self.assertEqual(0, payload2['axis_minute_start'])
            self.assertEqual(1440, payload2['axis_minute_end'])

    def test_grid_power_outlier_is_rejected_before_smoothing(self):
        state = ControllerState()
        
        class CfgMgr:
            def get(self):
                return dict(DEFAULT_CONFIG)
        logic = ZendureController(CfgMgr(), state, DummyMqtt(), DummyShelly(-173000.0), None, None, sma_energy_meter_client=DummySma())
        cfg = dict(DEFAULT_CONFIG)
        cfg['GRID_METER_SOURCE'] = 'shelly_http'
        cfg['GRID_POWER_PLAUSIBILITY_MAX_ABS_W'] = 30000
        cfg['SAFE_STATE_ON_SHELLY_ERROR'] = False
        with self.assertRaises(RuntimeError):
            logic.read_grid_power(cfg, for_control=True)
        self.assertFalse(state.grid_power_valid)
        self.assertIn('unplausibel', state.grid_power_validity_reason)

    def test_rest_surplus_harvest_parameters_are_not_added_in_rc8(self):
        self.assertNotIn('PRIMARY_CHARGE_WINDOW_HARVEST_ENABLED', DEFAULT_CONFIG)
        self.assertNotIn('PV_SHARE_HARVEST_ALLOWED_START', DEFAULT_CONFIG)


if __name__ == '__main__':
    unittest.main()
