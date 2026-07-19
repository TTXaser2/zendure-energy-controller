import inspect
import unittest
from pathlib import Path

import controller_logic
import status_page_v2
import version
import web_ui
from config_manager import DEFAULT_CONFIG
from state import ControllerState

ROOT = Path(__file__).resolve().parents[1]


class V12112Rc3StatusV2Tests(unittest.TestCase):
    def sample(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg.update({"UI_DARK_MODE": False, "ZENDURE_BATTERY_CAPACITY_WH": 5280})
        s = ControllerState().snapshot()
        s.update({
            "current_mode": "AUTO_CHARGE",
            "raw_grid_power": -1240.0,
            "grid_power_valid": True,
            "grid_power_age_seconds": 0.4,
            "battery_soc": 82,
            "zendure_system_signed_power": 1850,
            "zendure_target_signed_power": 1900,
            "zendure_mqtt_overall_status": "ZENDURE_MQTT_OK",
            "zendure_mqtt_live_confirmed": True,
            "second_battery_soc_percent": 91,
            "second_battery_power_w": 2110,
            "second_battery_data_valid": True,
            "second_battery_data_fresh": True,
            "rest_surplus_harvest_active": True,
            "rest_surplus_harvest_reason": "HIGH_SMA_SOC",
            "raw_grid_source": "sma_energy_meter_udp",
            "sma_energy_meter_detected_device_count": 2,
            "sma_energy_meter_selected_device_matched": True,
            "sma_energy_meter_packet_rate_per_min": 120,
            "sma_energy_meter_last_update_age_seconds": 0,
            "measurement_log_status": "active",
            "measurement_log_active_target_type": "external_mount",
            "measurement_db_status": "available",
            "measurement_db_path": "/opt/zendure-controller/logs/zec_measurements.sqlite3",
        })
        return cfg, s

    def test_true_standalone_status_v2_uses_mockup_structure(self):
        cfg, s = self.sample()
        html = web_ui.build_status_page(cfg, s)
        self.assertIn('class="zec-status-v2"', html)
        self.assertIn('class="zec-main-grid"', html)
        self.assertIn('class="zec-wide-card zec-soc-day-card"', html)
        self.assertIn('class="zec-lower-grid"', html)
        self.assertIn('/static/status_v2.css', html)
        self.assertIn('/static/status_v2.js', html)
        self.assertNotIn('Live-Snapshot · Refresh ohne Seitenreload', html)
        self.assertNotIn('<h1>Status</h1>', html)
        self.assertEqual(5, html.count('data-card="'))

    def test_topbar_contains_single_system_status_and_service_dependent_analysis(self):
        cfg, s = self.sample()
        payload = web_ui.build_status_view_payload(cfg, s)
        html = status_page_v2.render_status_page_v2(cfg, payload, analysis_available=True, analysis_port=8081)
        self.assertEqual(1, html.count('id="systemStatusButton"'))
        self.assertIn('Analyse-Service', html)
        html_off = status_page_v2.render_status_page_v2(cfg, payload, analysis_available=False, analysis_port=8081)
        self.assertNotIn('class="analysis-service-link"', html_off)
        self.assertIn('Handbuch', html_off)

    def test_one_and_two_headunit_layouts_follow_approved_design(self):
        cfg, s = self.sample()
        html = web_ui.build_status_page(cfg, s)
        self.assertIn('zec-storage-layout-single', html)
        self.assertIn('Rest bis Max-SOC', html)
        s["zendure_units_json"] = [
            {"unit_id":"u1", "name":"Unit 1", "soc_percent":56, "actual_power_w":2400, "target_w":2400, "capacity_kwh":5.28},
            {"unit_id":"u2", "name":"Unit 2", "soc_percent":100, "actual_power_w":0, "target_w":0, "capacity_kwh":2.44, "execution_state":"STOP_HOLD"},
        ]
        html = web_ui.build_status_page(cfg, s)
        self.assertIn('class="zec-dual-rings"', html)
        self.assertIn('Unit 1', html)
        self.assertIn('Unit 2', html)
        self.assertIn('System-SOC', html)
        self.assertIn('STOP_HOLD', html)

    def test_primary_card_exposes_harvest_harmonisation_in_standard_mode(self):
        cfg, s = self.sample()
        payload = web_ui.build_status_view_payload(cfg, s)
        self.assertIn('Parallel-Ernte aktiv', payload['primary']['line'])
        html = web_ui.build_status_page(cfg, s)
        self.assertIn('Harmonisierung', html)
        self.assertIn('Parallel-Ernte aktiv', html)

    def test_source_shows_packets_per_minute_and_multi_device_filter(self):
        cfg, s = self.sample()
        payload = web_ui.build_status_view_payload(cfg, s)
        self.assertEqual('120/min', payload['source']['packets_text'])
        self.assertEqual('2 SMA-Geräte erkannt · korrekt gefiltert', payload['source']['device_line'])
        self.assertEqual('ok', payload['source']['tone'])
        self.assertNotIn('Hz', web_ui.build_status_page(cfg, s))

    def test_tooltips_and_canvas_hover_are_separate_and_viewport_bounded(self):
        css = (ROOT / 'static' / 'status_v2.css').read_text(encoding='utf-8')
        js = (ROOT / 'static' / 'status_v2.js').read_text(encoding='utf-8')
        self.assertIn('width:min(340px,calc(100vw - 24px))', css)
        self.assertIn('class MiniGridChart', js)
        self.assertIn("canvas.addEventListener('mousemove'", js)
        self.assertIn('this.showTooltip', js)
        self.assertIn('setupInfoPopovers', js)
        cfg, snap = self.sample()
        payload = web_ui.build_status_view_payload(cfg, snap)
        self.assertNotIn(' title=', status_page_v2.render_status_page_v2(cfg, payload, analysis_available=False, analysis_port=8081))
        self.assertNotIn('<svg title=', status_page_v2.render_status_page_v2(cfg, payload, analysis_available=False, analysis_port=8081))

    def test_full_day_navigation_and_no_marker_series(self):
        html = web_ui.build_status_page(*self.sample())
        js = (ROOT / 'static' / 'status_v2.js').read_text(encoding='utf-8')
        for ident in ('dayPrev', 'dayToday', 'dayNext', 'storageSocChart'):
            self.assertIn(f'id="{ident}"', html)
        self.assertIn('/1440', js)
        self.assertIn('[0,360,720,1080,1440]', js)
        self.assertNotIn('pointRadius', js)

    def test_ring_inner_uses_card_background_and_dark_tokens(self):
        css = (ROOT / 'static' / 'status_v2.css').read_text(encoding='utf-8')
        self.assertIn('--zec-ring-inner:var(--zec-card-bg)', css)
        self.assertIn('background:var(--zec-ring-inner)', css)
        self.assertIn('html[data-theme="dark"]', css)

    def test_mqtt_recovery_hint_is_prominent_and_actionable(self):
        cfg, s = self.sample()
        s.update({"zendure_mqtt_overall_status":"ZENDURE_MQTT_RETAINED_ONLY", "zendure_mqtt_live_confirmed":False})
        payload = web_ui.build_status_view_payload(cfg, s)
        self.assertIn('Zendure-App', payload['zendure']['command_warning'])
        self.assertTrue(any('Zendure Live-Status' in x for x in payload['system']['warnings']))

    def test_rejected_measurement_diagnostics_are_bounded_scalars_under_existing_lock(self):
        source = inspect.getsource(controller_logic.ZendureController)
        self.assertIn('grid_rejected_count_since_start', source)
        self.assertIn('grid_last_rejected_time', source)
        self.assertNotIn('sleep(', source[source.find('grid_rejected_count_since_start')-500:source.find('grid_rejected_count_since_start')+700])
        snapshot = ControllerState().snapshot()
        for key in ('grid_rejected_count_since_start','grid_last_rejected_time','grid_last_rejected_reason','grid_last_rejected_value_w'):
            self.assertIn(key, snapshot)


if __name__ == '__main__':
    unittest.main()
