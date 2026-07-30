import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import status_page_v2
import version
import web_ui
from state import ControllerState
from tools.status_preview import create_preview_app
from tools.status_preview_scenarios import (
    build_preview_grid_payload,
    build_preview_soc_payload,
    build_preview_status_payload,
)


_METRICS = {
    "disk_free_bytes": 80.0,
    "disk_total_bytes": 100.0,
    "cpu_percent": 1.0,
    "ram_used_percent": 20.0,
    "ram_available_bytes": 80,
    "ram_total_bytes": 100,
    "swap_used_bytes": 0,
    "swap_total_bytes": 0,
    "swap_in_bytes_per_s": 0,
    "swap_out_bytes_per_s": 0,
    "temperature_c": 40.0,
    "load": [0.0, 0.0, 0.0],
    "system_uptime_s": 100,
    "throttling": {"available": True, "current": [], "historic": []},
}


def _snapshot():
    snap = ControllerState().snapshot()
    snap.update({
        "grid_power_valid": True,
        "raw_grid_power": -400,
        "battery_soc": 61,
        "zendure_system_signed_power": 380,
        "last_cycle_total_ms": 10.0,
        "last_cycle_completed_epoch": time.time(),
        "last_cycle_timing_json": json.dumps({
            "cycle_total_without_sleep_ms": 10.0,
            "other_cycle_work_ms": 10.0,
        }),
    })
    return snap


class V12112Rc10TopologyTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual("12.11.2-rc17", version.APP_VERSION)
        self.assertEqual("V12.11.2-RC17", version.APP_VERSION_LABEL)

    def test_existing_primary_storage_topology_remains_present(self):
        snap = _snapshot()
        snap.update({
            "second_battery_data_valid": True,
            "second_battery_data_fresh": True,
            "second_battery_soc_percent": 82,
            "second_battery_power_w": 900,
        })
        cfg = {
            "CROSS_CHARGE_ENABLED": True,
            "REST_SURPLUS_HARVEST_ENABLED": False,
            "INTERVAL_SECONDS": 3,
            "ZENDURE_LOCAL_API_ENABLED": False,
        }
        with patch("web_ui.get_system_metrics", return_value=_METRICS), patch("web_ui.replay_service_available", return_value=True):
            payload = web_ui.build_status_view_payload(cfg, snap, events=[])
        self.assertTrue(payload["topology"]["primary_storage_present"])
        self.assertTrue(payload["primary"]["present"])
        html = status_page_v2.render_status_page_v2(cfg, payload, analysis_available=True, analysis_port=8090)
        self.assertIn('data-card="primary"', html)
        self.assertNotIn("is-no-primary", html)

    def test_zendure_only_topology_hides_primary_without_stale_warning(self):
        snap = _snapshot()
        snap.update({
            "second_battery_data_valid": False,
            "second_battery_data_available": False,
        })
        cfg = {
            "STATUS_PRIMARY_STORAGE_PRESENT": False,
            "CROSS_CHARGE_ENABLED": False,
            "REST_SURPLUS_HARVEST_ENABLED": False,
            "INTERVAL_SECONDS": 3,
            "ZENDURE_LOCAL_API_ENABLED": False,
        }
        with patch("web_ui.get_system_metrics", return_value=_METRICS), patch("web_ui.replay_service_available", return_value=True):
            payload = web_ui.build_status_view_payload(cfg, snap, events=[])
        self.assertFalse(payload["topology"]["primary_storage_present"])
        self.assertFalse(payload["primary"]["present"])
        self.assertNotIn("Primärspeicher-Daten nicht vollständig", payload["system"]["warnings"])
        html = status_page_v2.render_status_page_v2(cfg, payload, analysis_available=True, analysis_port=8090)
        self.assertNotIn('data-card="primary"', html)
        self.assertIn("is-no-primary", html)
        self.assertIn('data-primary-storage-present="false"', html)

    def test_explicit_snapshot_topology_overrides_inference(self):
        self.assertFalse(web_ui._primary_storage_present({"STATUS_PRIMARY_STORAGE_PRESENT": True}, {"primary_storage_present": False}))
        self.assertTrue(web_ui._primary_storage_present({"STATUS_PRIMARY_STORAGE_PRESENT": False}, {"primary_storage_present": True}))
        self.assertFalse(web_ui._primary_storage_present({"STATUS_PRIMARY_STORAGE_PRESENT": "false"}, {}))
        self.assertTrue(web_ui._primary_storage_present({"STATUS_PRIMARY_STORAGE_PRESENT": "true"}, {}))

    def test_storage_day_payload_exposes_topology_and_suppresses_primary_series(self):
        snap = _snapshot()
        cfg = {
            "STATUS_PRIMARY_STORAGE_PRESENT": False,
            "CROSS_CHARGE_ENABLED": False,
            "REST_SURPLUS_HARVEST_ENABLED": False,
            "MIN_SOC_PERCENT": 10,
            "MAX_SOC_PERCENT": 99,
            "NIGHT_DISCHARGE_STOP_SOC_PERCENT": 35,
        }
        web_ui._storage_day_cache.update({"key": "", "built_epoch": 0.0, "payload": None})
        with patch("web_ui.query_graph_points", return_value=([{
            "epoch_ms": int(time.time() * 1000),
            "soc": 61,
            "primary_soc": 82,
            "zendure_actual_power_w": 300,
            "primary_power_w": 800,
            "mode": "AUTO_CHARGE",
        }], {"db_status": "ok"})), patch("web_ui.query_measurement_date_range", return_value={}):
            payload = web_ui.build_storage_soc_day_payload(cfg, snap)
        self.assertFalse(payload["primary_storage_present"])
        self.assertTrue(all(point.get("primary_soc") is None for point in payload["points"]))
        self.assertTrue(all(point.get("primary_power_w") is None for point in payload["points"]))


class V12112Rc10PreviewTests(unittest.TestCase):
    def test_zendure_only_preview_uses_common_renderer_without_primary(self):
        payload = build_preview_status_payload("zendure_only", now_epoch=1_000_000)
        html = status_page_v2.render_status_page_v2({}, payload, analysis_available=False, analysis_port=8090)
        self.assertTrue(payload["preview"]["active"])
        self.assertFalse(payload["topology"]["primary_storage_present"])
        self.assertIn("UI-VORSCHAU", html)
        self.assertIn("keine Steuerwirkung", html)
        self.assertNotIn('data-card="primary"', html)
        self.assertNotIn("MQTT Diagnose", html)

    def test_dual_preview_renders_two_units_and_primary(self):
        payload = build_preview_status_payload("dual_zendure_primary", now_epoch=1_000_000)
        html = status_page_v2.render_status_page_v2({}, payload, analysis_available=False, analysis_port=8090)
        self.assertEqual(2, payload["topology"]["zendure_unit_count"])
        self.assertTrue(payload["topology"]["primary_storage_present"])
        self.assertIn('data-ring="zendure_unit_1"', html)
        self.assertIn('data-ring="zendure_unit_2"', html)
        self.assertIn('data-card="primary"', html)
        self.assertIn("Zendure-System", html)

    def test_preview_json_endpoints_are_live_and_topology_aware(self):
        a = build_preview_grid_payload("zendure_only", now_epoch=1000)
        b = build_preview_grid_payload("zendure_only", now_epoch=1010)
        self.assertEqual(48, len(a["points"]))
        self.assertNotEqual(a["points"][-1]["value"], b["points"][-1]["value"])
        single = build_preview_soc_payload("zendure_only", date="2026-07-22")
        dual = build_preview_soc_payload("dual_zendure_primary", date="2026-07-22")
        self.assertFalse(single["primary_storage_present"])
        self.assertEqual(1, single["zendure_unit_count"])
        self.assertTrue(dual["primary_storage_present"])
        self.assertEqual(2, dual["zendure_unit_count"])

    def test_preview_app_has_only_read_only_get_routes(self):
        app = create_preview_app()
        relevant = [route for route in app.routes if getattr(route, "path", "").startswith(("/status", "/grid", "/storage", "/health", "/ready")) or getattr(route, "path", "") == "/"]
        self.assertTrue(relevant)
        for route in relevant:
            self.assertTrue(set(getattr(route, "methods", set())).issubset({"GET", "HEAD"}))

    def test_shared_javascript_keeps_preview_scenario_and_hides_primary_graph_series(self):
        js = Path("static/status_v2.js").read_text(encoding="utf-8")
        self.assertIn("previewScenario", js)
        self.assertIn("apiUrl('/status-view-data')", js)
        self.assertIn("p.primary_storage_present!==false", js)
        self.assertIn("primaryPowerRow", js)

    def test_preview_service_is_installed_but_not_enabled_by_update_script(self):
        update = Path("tools/update_zendure_controller.sh").read_text(encoding="utf-8")
        unit = Path("systemd/zendure-status-preview.service").read_text(encoding="utf-8")
        self.assertIn("zendure-status-preview.service", update)
        self.assertNotIn("enable zendure-status-preview.service", update)
        self.assertIn("NoNewPrivileges=true", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertIn("CPUQuota=15%", unit)


if __name__ == "__main__":
    unittest.main()
