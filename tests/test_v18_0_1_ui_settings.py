"""V18.0.1 user-approved display-only and fail-closed Settings/Status contracts."""
import json
from pathlib import Path
import unittest

from config_manager import DEFAULT_CONFIG
from settings_registry import SETTINGS_BY_KEY, SurfaceState
from web_ui import build_status_view_payload
from tests.test_v16_2_0_status_ui_field_acceptance import _cfg, _snap

ROOT = Path(__file__).resolve().parents[1]


class V1801DisplayTests(unittest.TestCase):
    def test_display_ceiling_setting_operational_and_default_100(self):
        key = 'SECOND_BATTERY_DISPLAY_MAX_SOC_PERCENT'
        self.assertEqual(DEFAULT_CONFIG[key], 100)
        self.assertEqual(json.loads((ROOT/'config.example.json').read_text())[key], 100)
        spec = SETTINGS_BY_KEY[key]
        self.assertEqual(spec.surface_state, SurfaceState.OPERATIONAL)
        self.assertEqual(spec.minimum, 0)
        self.assertEqual(spec.maximum, 100)

    def test_display_ceiling_applies_only_to_primary_view(self):
        before = build_status_view_payload(_cfg(), _snap())
        after = build_status_view_payload(_cfg(SECOND_BATTERY_DISPLAY_MAX_SOC_PERCENT=80), _snap())
        self.assertEqual(before['primary']['soc_limit_text'], '100 % / 20 %')
        self.assertEqual(after['primary']['soc_limit_text'], '80 % / 20 %')
        self.assertEqual(after['primary']['remaining_text'], '20 % · 2,60 kWh')
        self.assertEqual(before['zendure'], after['zendure'])

    def test_real_upper_device_cap_is_not_overridden_upward(self):
        snap = _snap()
        snap.update(primary_storage_charge_upper_soc_percent=75,
                    primary_storage_charge_upper_soc_valid=True,
                    primary_storage_charge_upper_soc_fresh=True)
        payload = build_status_view_payload(_cfg(SECOND_BATTERY_DISPLAY_MAX_SOC_PERCENT=90), snap)
        self.assertEqual(payload['primary']['soc_limit_text'], '75 % / 20 %')

    def test_ui_only_key_absent_from_control_logic(self):
        key='SECOND_BATTERY_DISPLAY_MAX_SOC_PERCENT'
        for filename in ('controller_logic.py','cross_charge.py','battery_care_policy.py','battery_care_pv_allocation.py'):
            self.assertNotIn(key, (ROOT/filename).read_text())

    def test_js_fail_closed_and_date_local_only(self):
        js = (ROOT/'static/settings_v2.js').read_text()
        for key in ('validSettingsModel(next)', 'Erneut laden', 'CARE_SEASON_FORMAT_INVALID',
                    'careSeasonParse(el.value)', 'careSeasonDisplay(value)', 'inputmode="numeric"'):
            self.assertIn(key,js)
        self.assertIn("['reserve_soc','Nachtreserve']", (ROOT/'static/status_v2.js').read_text())
        self.assertIn('Nachtreserve ${fmtSoc(cfgSeg.reserve_soc)}', (ROOT/'static/status_v2.js').read_text())

if __name__=='__main__':
    unittest.main()
