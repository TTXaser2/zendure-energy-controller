"""V17.1.2: operational help coverage, safe control explanations, and no placeholders."""
import unittest
from settings_registry import iter_operational_settings
from settings_help import build_section_specs
from settings_help_v1712 import WHEN

class TestV1712OperationalHelp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings=list(iter_operational_settings())
        cls.by_key={x.key:x for x in cls.settings}

    def test_complete_unique_operational_inventory(self):
        self.assertEqual(len(self.settings),190)
        self.assertEqual(len(self.by_key),190)
        self.assertEqual(len(WHEN),113)
        self.assertEqual(set(WHEN),{x.key for x in self.settings if x.key in WHEN})

    def test_every_operational_setting_explains_when_it_acts(self):
        for item in self.settings:
            with self.subTest(item=item.key):
                h=item.help
                self.assertGreater(len(h.short_help.strip()),30)
                self.assertGreater(len(h.extended_help.strip()),80)
                self.assertGreater(len((h.when_help or '').strip()),75)
                self.assertFalse('Konfiguration für ' in h.short_help)

    def test_no_generic_dependency_slogans_for_operational_surface(self):
        shared=('Verknüpfte Einstellungen können Aktivierung',
                'Harvest nutzt mehrere Freigabeschwellen und Allokationswerte gemeinsam',
                'die unten genannten Beziehungen zeigen')
        for item in self.settings:
            if item.help.dependencies:
                with self.subTest(item=item.key):
                    self.assertGreater(len(item.help.dependency_help or ''),85)
                    for slogan in shared:
                        self.assertNotIn(slogan,item.help.dependency_help)

    def test_fast_capture_rates_are_seconds_not_cycle_steps(self):
        h=self.by_key['HARVEST_FAST_CAPTURE_MODE'].help
        self.assertIn('400 Watt pro Sekunde',h.extended_help)
        self.assertIn('100 Watt pro Sekunde',h.extended_help)
        self.assertIn('sofort',h.extended_help)
        self.assertIn('nicht garantiert',h.extended_help)
        self.assertIn('Aus lässt die normale Automatik unverändert',h.short_help)
        self.assertEqual(len(h.option_help),3)

    def test_normal_step_is_distinct_and_without_recommendation_to_increase(self):
        h=self.by_key['MAX_POWER_STEP_W'].help
        self.assertIn('nach der Glättung',h.extended_help)
        self.assertIn('in einem Regelzyklus',h.extended_help)
        self.assertIn('Fast Capture',h.extended_help)
        self.assertIn('keine generelle Empfehlung',h.extended_help)

    def test_all_74_section_purposes_remain_present(self):
        sections={(item.category,item.section) for item in self.settings}
        self.assertEqual(len(sections),74)
        rendered=build_section_specs(sorted(sections))
        self.assertEqual(len(rendered),74)
        for pair, spec in rendered.items():
            with self.subTest(section=pair):
                self.assertGreater(len(spec.help_text.strip()),40)
                self.assertNotIn('TODO',spec.help_text)

    def test_no_second_command_path_or_unsourced_claims(self):
        for key in ['SECOND_BATTERY_MODBUS_TEMPLATE','SECOND_BATTERY_SOURCE_PROFILE',
                    'ZENDURE_LOCAL_API_USE_FOR_TELEMETRY','GRID_METER_SOURCE',
                    'MEASUREMENT_LOG_MODE','ANALYSIS_MAX_ROWS','UI_MODE']:
            self.assertGreater(len(self.by_key[key].help.when_help),100, key)
            self.assertTrue(any(term in self.by_key[key].help.when_help.lower() for term in ('nicht','keine','nur','unverändert','ohne','bleibt','getrennt','ändert')), key)

if __name__ == '__main__':
    unittest.main()
