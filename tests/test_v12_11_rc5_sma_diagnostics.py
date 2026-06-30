import unittest

from config_validator import validate_config_semantics
from sma_energy_meter import normalize_socket_mode, SmaEnergyMeterSnapshot
from state import ControllerState


class Rc5SmaSocketModeTests(unittest.TestCase):
    def test_default_socket_mode_is_rc3_compatible(self):
        self.assertEqual(normalize_socket_mode(None), "rc3_compatible")
        self.assertEqual(normalize_socket_mode("auto"), "rc3_compatible")
        self.assertEqual(normalize_socket_mode("reuseaddr_only"), "reuseaddr_only")
        self.assertEqual(normalize_socket_mode("bad-value"), "rc3_compatible")

    def test_invalid_socket_mode_is_config_error(self):
        cfg = {
            "GRID_METER_SOURCE": "shelly_http",
            "SHELLY_IP": "127.0.0.1",
            "SMA_ENERGY_METER_SOCKET_MODE": "invalid",
            "MQTT_BROKER": "127.0.0.1",
            "DEVICE_ID": "dev",
        }
        codes = {i.code for i in validate_config_semantics(cfg)}
        self.assertIn("SMA_SOCKET_MODE_INVALID", codes)

    def test_snapshot_contains_socket_and_gap_fields(self):
        snap = SmaEnergyMeterSnapshot()
        self.assertEqual(snap.configured_socket_mode, "rc3_compatible")
        self.assertFalse(snap.reuseport_enabled)
        self.assertEqual(snap.packet_rate_per_min, 0.0)

    def test_state_snapshot_exports_sma_diagnostics(self):
        state = ControllerState()
        state.sma_energy_meter_socket_mode = "rc3_compatible"
        state.sma_energy_meter_reuseport_enabled = True
        state.sma_energy_meter_packet_rate_per_min = 60.0
        exported = state.snapshot()
        self.assertEqual(exported["sma_energy_meter_socket_mode"], "rc3_compatible")
        self.assertTrue(exported["sma_energy_meter_reuseport_enabled"])
        self.assertEqual(exported["sma_energy_meter_packet_rate_per_min"], 60.0)


class Rc5DiagnosticPackageTests(unittest.TestCase):
    def test_export_script_collects_sma_diagnostics_summary(self):
        from pathlib import Path
        text = Path("tools/create_zec_analysis_package.sh").read_text(encoding="utf-8")
        self.assertIn("SMA_DIAGNOSTICS_SUMMARY.txt", text)
        self.assertIn("sma_runtime_events.txt", text)
        self.assertIn("SMA_DIAG", text)


if __name__ == "__main__":
    unittest.main()
