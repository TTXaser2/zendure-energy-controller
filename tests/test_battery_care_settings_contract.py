# SPDX-License-Identifier: AGPL-3.0-or-later
"""Battery Care Registry/Preview core validation and default-off migration."""
import json
from pathlib import Path
import unittest

from settings_registry import SETTINGS_BY_KEY, SurfaceState, PortabilityClass
from settings_validation import ValidationContext, ValidationSeverity, parse_candidate, validate_candidate


HERE = Path(__file__).resolve().parents[1]
CARE_KEYS = (
    'BATTERY_CARE_ENABLED', 'BATTERY_CARE_SEASON_START_MM_DD',
    'BATTERY_CARE_SEASON_END_MM_DD', 'BATTERY_CARE_RESERVE_SOC_PERCENT',
    'BATTERY_CARE_GRID_TRIGGER_SOC_PERCENT', 'BATTERY_CARE_EMERGENCY_SOC_PERCENT',
    'BATTERY_CARE_GRID_CHARGE_MAX_POWER_W',
)
BASE = {'MAX_SOC_PERCENT': 99, 'MAX_CHARGE_POWER_W': 2400, 'MIN_SOC_PERCENT': 10}
GOOD = dict(BASE, BATTERY_CARE_ENABLED=True,
            BATTERY_CARE_SEASON_START_MM_DD='11-01', BATTERY_CARE_SEASON_END_MM_DD='02-28',
            BATTERY_CARE_RESERVE_SOC_PERCENT=40,
            BATTERY_CARE_GRID_TRIGGER_SOC_PERCENT=30,
            BATTERY_CARE_EMERGENCY_SOC_PERCENT=20,
            BATTERY_CARE_GRID_CHARGE_MAX_POWER_W=250)


def codes(candidate, previous=None):
    return [(i.code, i.severity.value, i.blocking, dict(i.params)) for i in validate_candidate(candidate, ValidationContext(previous=previous)) if i.code.startswith('VAL-BC')]


class TestBatteryCareSettingsContract(unittest.TestCase):
    def test_all_seven_keys_are_visible_operational_settings(self):
        self.assertEqual(len(CARE_KEYS), 7)
        for key in CARE_KEYS:
            sp = SETTINGS_BY_KEY[key]
            self.assertEqual(sp.surface_state, SurfaceState.OPERATIONAL)
            self.assertEqual(sp.portability_class, PortabilityClass.PORTABLE_PROFILE)
            self.assertEqual(sp.category, 'Leistungsgrenzen & SOC-Schutz')
            self.assertEqual(sp.section, 'Battery Care – saisonaler Batterieschutz')
            self.assertTrue(len(sp.help.extended_help) >= 100)

    def test_new_install_and_missing_existing_values_are_safe(self):
        raw = json.loads((HERE / 'config.example.json').read_text())
        self.assertIs(raw['BATTERY_CARE_ENABLED'], False)
        for key in CARE_KEYS[1:]:
            self.assertIsNone(raw[key])
        self.assertEqual(codes(dict(BASE, BATTERY_CARE_ENABLED=False)), [])

    def test_activation_without_explicit_parameters_is_blocked(self):
        cs = codes(dict(BASE, BATTERY_CARE_ENABLED=True), previous=dict(BASE, BATTERY_CARE_ENABLED=False))
        self.assertTrue(any(c[0]=='VAL-BC-001' and c[2] for c in cs))
        self.assertTrue(any(c[0]=='VAL-BC-002' and not c[2] for c in cs))

    def test_all_valid_values_allow_commit_after_confirmation(self):
        cs = codes(GOOD, previous=dict(BASE, BATTERY_CARE_ENABLED=False))
        self.assertEqual([(c[0],c[1]) for c in cs], [('VAL-BC-002','confirm')])
        self.assertEqual(codes(GOOD, previous=GOOD), [])

    def test_hysteresis_errors(self):
        for updates in [dict(BATTERY_CARE_EMERGENCY_SOC_PERCENT=29),
                        dict(BATTERY_CARE_GRID_TRIGGER_SOC_PERCENT=39),
                        dict(BATTERY_CARE_RESERVE_SOC_PERCENT=100),
                        dict(BATTERY_CARE_RESERVE_SOC_PERCENT=None)]:
            self.assertTrue(any(c[0]=='VAL-BC-001' and c[2] for c in codes(dict(GOOD,**updates))))

    def test_cap_is_clamped_by_validation_not_silently(self):
        self.assertTrue(any(c[0]=='VAL-BC-001' for c in codes(dict(GOOD, MAX_CHARGE_POWER_W=200))))
        self.assertTrue(any(c[0]=='VAL-BC-001' for c in codes(dict(GOOD, BATTERY_CARE_GRID_CHARGE_MAX_POWER_W=0))))

    def test_calendar_cross_year_and_invalid_boundaries(self):
        self.assertFalse(any(c[0]=='VAL-BC-001' for c in codes(GOOD)))
        for value in ('02-29','02-30','13-01','2026-11-01','bad'):
            cs = codes(dict(GOOD, BATTERY_CARE_SEASON_START_MM_DD=value))
            self.assertTrue(any(c[0]=='VAL-BC-001' for c in cs))

    def test_schema_parse_rejects_unsafe_and_never_autofills(self):
        self.assertTrue(parse_candidate({'BATTERY_CARE_EMERGENCY_SOC_PERCENT': True}).issues)
        self.assertEqual(parse_candidate({'BATTERY_CARE_RESERVE_SOC_PERCENT': None}).known['BATTERY_CARE_RESERVE_SOC_PERCENT'],None)
        self.assertTrue(parse_candidate({'BATTERY_CARE_SEASON_START_MM_DD':'02-29'}).issues)

    def test_existing_legacy_s3_is_independent(self):
        for key in ('HARVEST_SEASON_MODE','HARVEST_SEASON_POLICY_ENABLED'):
            self.assertIn(key, SETTINGS_BY_KEY)
        self.assertEqual(SETTINGS_BY_KEY['BATTERY_CARE_ENABLED'].default_new_install,False)
        self.assertEqual(SETTINGS_BY_KEY['HARVEST_SEASON_POLICY_ENABLED'].default_new_install,False)


if __name__ == '__main__':
    unittest.main()
