import unittest

from config_manager import CONFIG_SCHEMA
from tools.replay_report import cross_charge_table, high_soc_table


class V1281FixTests(unittest.TestCase):
    def test_cross_charge_badge_is_rendered_as_html_not_escaped(self):
        html = cross_charge_table({"cross_charge": {"rating": "red", "rating_reason": "kritisch"}})
        self.assertIn("<span class='badge bad'>rot</span>", html)
        self.assertNotIn("&lt;span", html)
        self.assertIn("<summary>info</summary>", html)

    def test_charge_acceptance_states_are_human_readable(self):
        html = high_soc_table({"charge_acceptance_states": {"ok": 4, "suspect": 2, "limited": 1, "not_accepting": 3}})
        self.assertIn("ok: 4", html)
        self.assertIn("Verdacht: 2", html)
        self.assertIn("nimmt nicht an: 3", html)
        self.assertNotIn("&quot;", html)

    def test_csv_backup_count_limit_is_20(self):
        self.assertEqual(CONFIG_SCHEMA["CSV_LOG_BACKUP_COUNT"]["max"], 20)


if __name__ == "__main__":
    unittest.main()
