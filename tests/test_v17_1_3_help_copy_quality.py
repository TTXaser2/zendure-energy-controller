import unittest

from settings_registry import iter_operational_settings

class HelpCopyQuality(unittest.TestCase):
    def test_all_31_toggle_inactive_behaviours_present(self):
        rows = [r for r in iter_operational_settings() if r.value_type.value == "bool"]
        self.assertEqual(len(rows),31)
        for row in rows:
            with self.subTest(key=row.key):
                self.assertGreater(len(row.help.effect_disable or ""),65)
                self.assertFalse((row.help.effect_disable or "").startswith("Konfiguration für"))
    def test_dropdown_labels_match_fast_capture_help(self):
        row = next(r for r in iter_operational_settings() if r.key == "HARVEST_FAST_CAPTURE_MODE")
        for code,label in row.options:
            self.assertIn(f"„{label}“",dict(row.help.option_help)[code])
        self.assertIn("voll ist",row.help.short_help)
        self.assertNotIn("Overlay 0",row.apply_text)
